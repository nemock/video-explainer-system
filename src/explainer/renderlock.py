"""Machine-global render lock — serializes the memory-heavy render+mux stage
(headless-Chrome frame capture + ffmpeg encode) across ALL explainer projects
and background routines on this Mac, so concurrent runs never collide and OOM /
SIGTERM each other (the #10-vs-CVG collision, 2026-06-21).

Mechanism: an `fcntl.flock` on a FIXED machine-global lockfile. Every codebase
that renders imports a copy of this module pointing at the SAME `LOCKFILE`, so
they serialize across codebases (this v1 explainer-system — used by the CVG
routine — AND explainer2). flock is released by the OS when the holder dies —
even on SIGKILL — so a crashed render never deadlocks the queue. acquire() polls
non-blocking so the wait is visible in run.log.

NOTE: an earlier version also sniffed for a "foreign render" via `pgrep
chrome-headless-shell` — that false-positived on persistent MCP headless
browsers (LinkedIn/patchright) and deadlocked the queue. Removed 2026-06-21.
The cooperative flock is sufficient now that both codebases hold it.

Usage (in the media stage loop): acquire() before `render`, release() after `mux`.
"""
import fcntl, json, os, time

LOCKFILE = "/tmp/explainer-render.lock"   # SHARED across codebases — do not change per-repo
POLL_SECS = 15
MAX_WAIT_SECS = 3 * 60 * 60               # 3h ceiling — wait long, but never forever


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
