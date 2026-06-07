"""Observability — append-only build-log.jsonl (ARCHITECTURE §16). One JSON line per stage run:
stage / segment / start / end / duration / peak_rss / exit / message. The `timed` context
manager wraps a stage and captures wall time + peak child-process RSS (the data that later tunes
RAM-bounded concurrency). Best-effort; logging never breaks a build."""
import json
import resource
import sys
import time
from contextlib import contextmanager

# ru_maxrss is bytes on macOS, KiB on Linux.
_RSS_DIV = (1024 * 1024) if sys.platform == "darwin" else 1024


def _peak_child_rss_mb():
    return round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / _RSS_DIV, 1)


def emit(program, *, stage, segment=None, start=None, end=None, exit=0, peak_rss_mb=None, message=""):
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "stage": stage, "segment": segment,
             "start": start, "end": end,
             "duration_s": round(end - start, 3) if (start is not None and end is not None) else None,
             "exit": exit, "peak_rss_mb": peak_rss_mb, "message": message}
    try:
        with open(program.build_log, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass
    return entry


@contextmanager
def timed(program, stage, segment=None):
    """`with timed(program, 'conform', seg_id): ...` — emits a build-log entry on exit (incl. on error)."""
    start, code, msg = time.time(), 0, ""
    try:
        yield
    except Exception as e:
        code, msg = 1, f"{type(e).__name__}: {e}"
        raise
    finally:
        emit(program, stage=stage, segment=segment, start=start, end=time.time(),
             exit=code, peak_rss_mb=_peak_child_rss_mb(), message=msg)
