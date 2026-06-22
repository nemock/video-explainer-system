"""Machine-global render lock — serializes the memory-heavy render+mux stage
(headless-Chrome frame capture + ffmpeg encode) across ALL explainer projects
and background routines on this Mac, so concurrent runs never collide and OOM /
SIGTERM each other (the #10-vs-CVG collision, 2026-06-21).

Two layers, both polled with a visible log line:

  1. An `fcntl.flock` on a FIXED machine-global lockfile. Every codebase that
     renders imports a copy of this module pointing at the SAME `LOCKFILE`, so
     they serialize across codebases (this v1 explainer-system — used by the CVG
     routine — AND explainer2). flock is released by the OS when the holder dies
     — even on SIGKILL — so a crashed render never deadlocks the queue.

  2. A process-presence guard. Even before taking the lock, wait while a FOREIGN
     render-capture browser is running. acquire() is called just before the
     render stage (our own capture browser hasn't launched yet), so any
     headless-Chrome capture process found is another project's render. This
     covers a render started by code that predates the lock and is a safety net.

Usage (in the media stage loop): acquire() before `render`, release() after `mux`.
"""
import fcntl, json, os, subprocess, time

LOCKFILE = "/tmp/explainer-render.lock"   # SHARED across codebases — do not change per-repo
POLL_SECS = 15
MAX_WAIT_SECS = 3 * 60 * 60               # 3h ceiling — wait long, but never forever


def _foreign_render_active():
    """True if a headless-Chrome render capture is already running. acquire() runs
    before our own capture browser launches, so any match is a foreign render."""
    try:
        r = subprocess.run(["pgrep", "-f", "chrome-headless-shell.*remote-debugging-pipe"],
                           capture_output=True, text=True)
        return bool(r.stdout.strip())
    except Exception:
        return False


def acquire(proj=None, label=None, log=print):
    """Block until the render engine is free, then return the held lock fd.
    Pass the result to release() after mux."""
    label = label or (os.path.basename(str(getattr(proj, "dir", ""))) or "render")
    fd = open(LOCKFILE, "a+")
    state = {"waited": 0, "announced": False}

    def _wait(why):
        if not state["announced"]:
            log(f"render-lock: engine busy ({why}) — queued, waiting for it to finish…")
            state["announced"] = True
        if state["waited"] >= MAX_WAIT_SECS:
            try: fd.close()
            except Exception: pass
            raise TimeoutError(f"render lock not acquired after {MAX_WAIT_SECS // 60} min ({why})")
        time.sleep(POLL_SECS)
        state["waited"] += POLL_SECS

    # layer 1: the cross-codebase flock
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError:
            try:
                fd.seek(0); held = fd.read().strip()
            except Exception:
                held = ""
            _wait(held or "another project holds the lock")

    # layer 2: wait out any foreign render that didn't take the lock
    while _foreign_render_active():
        _wait("another render is capturing frames")

    try:
        fd.seek(0); fd.truncate()
        fd.write(json.dumps({"pid": os.getpid(), "label": label, "since": time.strftime("%H:%M:%S")}))
        fd.flush()
    except Exception:
        pass
    if state["announced"]:
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
