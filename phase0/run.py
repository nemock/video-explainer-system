#!/usr/bin/env python3
"""Phase 0 — orchestrator. Runs the four stages in order and aggregates metrics.
Each stage is a standalone, independently-runnable Python helper (PRD §12.3).

Run: myenv/bin/python3 phase0/run.py
"""
import json, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
STAGES = ["synth.py", "align.py", "render.py", "mux.py"]

def main():
    t0 = time.time()
    for stage in STAGES:
        print(f"\n=== {stage} ===")
        r = subprocess.run([PY, str(HERE / stage)])
        if r.returncode != 0:
            print(f"STAGE FAILED: {stage}")
            return r.returncode
    wall = time.time() - t0

    work = HERE / "work"
    agg = {}
    for m in ["metrics_synth", "metrics_align", "metrics_render", "metrics_mux"]:
        p = work / f"{m}.json"
        if p.exists():
            agg[m.replace("metrics_", "")] = json.loads(p.read_text())
    agg["wall_clock_s"] = round(wall, 2)
    (work / "results.json").write_text(json.dumps(agg, indent=2))
    print("\n=== RESULTS ===")
    print(json.dumps(agg, indent=2))

if __name__ == "__main__":
    sys.exit(main())
