"""Machine-global render lock + detached render launcher — serializes the
memory-heavy render+mux stage (headless-Chrome frame capture + ffmpeg encode)
across ALL explainer projects and background routines on this Mac, and launches
renders DETACHED from the calling Claude session so app-suspension can't kill
them mid-encode.

Two concerns, two mechanisms:

1. SERIALIZE — an `fcntl.flock` on a FIXED machine-global lockfile. Every
   codebase that renders imports a copy of this module pointing at the SAME
   `LOCKFILE`, so they serialize across codebases (explainer2 AND v1
   explainer-system, which the CVG routine uses). flock is released by the OS
   when the holder dies — even on SIGKILL — so a crashed render never deadlocks
   the queue. acquire() polls non-blocking so the wait is visible in run.log.

2. SURVIVE — `launch_detached()` runs `media` in its own session
   (`start_new_session=True`, the portable macOS `setsid`) under `caffeinate`,
   so suspending/closing the Claude app leaves the render running. This — not
   the lock — is what kept killing #10/#36/medtech (the render was a child of
   the session). caffeinate blocks OS idle-sleep but NOT task termination.

NOTE: an earlier version also sniffed for a "foreign render" via `pgrep
chrome-headless-shell` — that false-positived on persistent MCP headless
browsers (LinkedIn/patchright) and deadlocked the queue. Removed 2026-06-21.
The cooperative flock is sufficient now that both codebases hold it.

Usage:
  - media stage loop: acquire() before `render`, release() after `mux`.
  - to start a render that survives the session: `<cli> render <proj>`
    (cmd_render → launch_detached). `<cli> render-status` → status().
"""
import fcntl, json, os, subprocess, sys, time

LOCKFILE = "/tmp/explainer-render.lock"   # SHARED across codebases — do not change per-repo
POLL_SECS = 15
MAX_WAIT_SECS = 3 * 60 * 60               # 3h ceiling — wait long, but never forever
DEFAULT_STAGES = "render,mux,manifest,qa" # what a detached `render` runs (deck/narrate/align cached)


def acquire(proj=None, label=None, log=print):
    """Block until the render engine is free, then return the held lock fd.
    Pass the result to release() after mux."""
    label = label or (os.path.basename(str(getattr(proj, "dir", ""))) or "render")
    fd = open(LOCKFILE, "a+")
    waited, announced = 0, False
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError:
            try:
                fd.seek(0); held = fd.read().strip()
            except Exception:
                held = ""
            if not announced:
                log(f"render-lock: engine busy ({held or 'another project'}) — queued, waiting…")
                announced = True
            if waited >= MAX_WAIT_SECS:
                try: fd.close()
                except Exception: pass
                raise TimeoutError(f"render lock not acquired after {MAX_WAIT_SECS // 60} min ({held})")
            time.sleep(POLL_SECS); waited += POLL_SECS
    try:
        fd.seek(0); fd.truncate()
        fd.write(json.dumps({"pid": os.getpid(), "label": label, "since": time.strftime("%H:%M:%S")}))
        fd.flush()
    except Exception:
        pass
    if announced:
        log("render-lock: engine free — acquired, starting render")
    return fd


def release(fd):
    if fd is None:
        return
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        fd.close()  # closing the fd also releases the flock
    except Exception:
        pass


# ---- detached launch + status -------------------------------------------------

def _media_pid_for(project_dir):
    """pid of a live `media` python process for this project dir, or None
    (idempotency guard so we never double-encode the same project)."""
    base = os.path.basename(os.path.normpath(project_dir))
    try:
        out = subprocess.run(["pgrep", "-f", f"cli media .*{base}"],
                             capture_output=True, text=True)
    except Exception:
        return None
    me = os.getpid()
    for tok in out.stdout.split():
        try:
            pid = int(tok)
        except ValueError:
            continue
        if pid != me:
            return pid
    return None


def launch_detached(project_dir, only=None, log=print):
    """Start `media --only <stages>` in its own session under caffeinate, so it
    outlives the calling Claude session. Returns a small status dict. The flock
    in cmd_media still serializes it against any other render."""
    only = only or DEFAULT_STAGES
    project_dir = os.path.abspath(project_dir)
    base = os.path.basename(project_dir)
    existing = _media_pid_for(project_dir)
    if existing:
        log(f"render: already running for {base} (pid {existing}) — not relaunching")
        return {"status": "already_running", "pid": existing, "project": base}
    work = os.path.join(project_dir, "work")
    os.makedirs(work, exist_ok=True)
    # structured progress lands in run.log (cmd_media writes it); raw child
    # stdout/stderr go to render.out so the two don't interleave/duplicate.
    with open(os.path.join(work, "run.log"), "a") as rl:
        rl.write(f"{time.strftime('%H:%M:%S')} render: detached launch (--only {only})\n")
    outf = open(os.path.join(work, "render.out"), "a")
    pkg = __name__.rsplit(".", 1)[0]          # "explainer2" or "explainer"
    cmd = ["caffeinate", "-i", sys.executable, "-m", f"{pkg}.cli",
           "media", project_dir, "--only", only]
    p = subprocess.Popen(cmd, stdout=outf, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True,
                         env=os.environ.copy())
    log(f"render: launched DETACHED for {base} (pid {p.pid}) — survives session suspension; "
        f"watch {os.path.join('work', 'run.log')}")
    return {"status": "launched", "pid": p.pid, "project": base, "only": only,
            "out": os.path.join(work, "render.out")}


def _holder():
    """Current lockfile holder note + whether that pid is actually alive."""
    try:
        with open(LOCKFILE) as f:
            data = json.loads(f.read() or "{}")
    except Exception:
        return None
    pid = data.get("pid")
    alive = False
    if pid:
        try:
            os.kill(int(pid), 0); alive = True
        except Exception:
            alive = False
    data["alive"] = alive
    return data


def _running_media():
    """[{pid, etime, dir, project}] for each live media render (deduped per project)."""
    try:
        out = subprocess.run(["ps", "-ax", "-o", "pid=,etime=,command="],
                             capture_output=True, text=True)
    except Exception:
        return []
    seen, rows = set(), []
    for line in out.stdout.splitlines():
        if "cli media" not in line or "pgrep" in line:
            continue
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        pid, etime, cmd = parts
        toks = cmd.split()
        if toks and "caffeinate" in toks[0]:   # keep the python proc, drop its caffeinate wrapper
            continue
        pdir = ""
        if "media" in toks:
            i = toks.index("media")
            if i + 1 < len(toks):
                pdir = toks[i + 1]
        base = os.path.basename(pdir.rstrip("/")) if pdir else "?"
        if base in seen:
            continue
        seen.add(base)
        rows.append({"pid": int(pid), "etime": etime, "dir": pdir, "project": base})
    return rows


def _last_log(project_dir):
    try:
        with open(os.path.join(project_dir, "work", "run.log")) as f:
            tail = [l.strip() for l in f if l.strip()]
        return tail[-1] if tail else "(no log)"
    except Exception:
        return "(no log)"


def status():
    """Human-readable render-queue view: who holds the lock + every live render."""
    h = _holder()
    if h and h.get("alive"):
        head = f"LOCK held by: {h.get('label', '?')} (pid {h['pid']}, since {h.get('since', '?')})"
    elif h and h.get("pid"):
        head = f"LOCK free (stale note: {h.get('label', '?')}, pid {h['pid']} not alive)"
    else:
        head = "LOCK free"
    procs = _running_media()
    lines = [head]
    if procs:
        lines.append(f"{len(procs)} render(s) live:")
        for p in procs:
            lines.append(f"  • {p['project']} (pid {p['pid']}, up {p['etime']}) — {_last_log(p['dir'])}")
    else:
        lines.append("no renders running")
    return "\n".join(lines)
