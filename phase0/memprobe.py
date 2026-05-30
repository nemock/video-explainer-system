#!/usr/bin/env python3
"""Phase 0 — peak-memory gate probe (auxiliary, not a pipeline stage).
Launches the RENDER stage and samples the resident memory of the Python +
Chromium process tree to estimate peak unified-memory pressure on the 16GB M3.
Uses `ps` (no extra deps). A Python poll loop is fine here (not a shell loop).

Run: myenv/bin/python3 phase0/memprobe.py
"""
import subprocess, sys, time, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
MATCH = ("Chromium", "chrome", "headless", "render.py", "playwright")

def tree_rss_mb():
    out = subprocess.run(["ps", "-axo", "rss=,command="], capture_output=True, text=True).stdout
    total = 0
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        rss, _, cmd = line.partition(" ")
        try:
            kb = int(rss)
        except ValueError:
            continue
        if any(m in cmd for m in MATCH):
            total += kb
    return total / 1024.0  # MB

def main():
    proc = subprocess.Popen([PY, str(HERE / "render.py")],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    peak = 0.0
    while proc.poll() is None:
        peak = max(peak, tree_rss_mb())
        time.sleep(0.4)
    res = {"peak_render_tree_rss_mb": round(peak, 1)}
    (HERE / "work" / "metrics_memory.json").write_text(json.dumps(res, indent=2))
    print("MEMORY (render tree peak):", json.dumps(res))

if __name__ == "__main__":
    sys.exit(main())
