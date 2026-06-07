"""Single-writer fold-in channel (ARCHITECTURE §5). Only the orchestrator writes the manifest;
a parallel `explainer` render (a separate process) can't. Instead each segment project reports
its stage completions into its own `.status.json`, and the orchestrator folds those into the
manifest under its single writer. The 2.0 spine renders segments inline so this isn't yet
exercised, but it's the mechanism the 2.2 parallel record/render loop builds on."""
import json
import time
from pathlib import Path

from . import manifest as mf


def report(seg_dir, stage, ok, metrics=None):
    """A segment process records a stage outcome to segments/<id>/.status.json (append-merge)."""
    p = Path(seg_dir) / ".status.json"
    data = json.loads(p.read_text()) if p.exists() else {"stages": {}}
    data["stages"][stage] = {"ok": bool(ok), "metrics": metrics or {},
                             "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    p.write_text(json.dumps(data, indent=2))
    return p


def collect(program):
    """Read every segment's .status.json. Returns {seg_id: {stages:{...}}} (missing -> absent)."""
    out = {}
    for sid in program.order:
        if program.is_interstitial(sid):
            continue
        p = program.project_dir(sid) / ".status.json"
        if p.exists():
            out[sid] = json.loads(p.read_text())
    return out


def fold_in(program, manifest):
    """Fold reported stage outcomes into the manifest (single-writer). A segment whose status
    file shows a successful render/mux is promoted to `rendered` if the manifest lags. Returns the
    set of segments updated."""
    updated = []
    reports = collect(program)
    for sid, rep in reports.items():
        stages = rep.get("stages", {})
        rendered = stages.get("render", {}).get("ok") or stages.get("mux", {}).get("ok")
        cur = manifest["segments"].get(sid, {}).get("status")
        if rendered and cur in ("planned", "scripted", "recorded"):
            mf.transition(program, manifest, sid, "rendered", force=True, write_now=False)
            updated.append(sid)
    if updated:
        mf.write(program, manifest)
    return updated
