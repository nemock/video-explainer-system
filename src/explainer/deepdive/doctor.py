"""Doctor — the everyday `deepdive doctor <program>` health check (ARCHITECTURE §16). Reconciles
the manifest against disk (read-only re: media), then renders the lifecycle as a checklist with a
concrete next-action list and any drift. This is how the operator (or the skill) decides what to
do next without reading raw JSON."""
from pathlib import Path

from . import manifest as mf

_RENDERED = mf.RANK["rendered"]


def _next_actions(manifest):
    actions, segs = [], manifest["segments"]
    for sid in manifest["order"]:
        st = segs[sid]["status"]
        if st in ("planned", "scripted"):
            actions.append(f"{sid}: author + render (or record, for an act)")
        elif st == "recorded":
            actions.append(f"{sid}: align + render")
        elif st == "rendered" and segs[sid].get("kind") != "interstitial":
            actions.append(f"{sid}: review (approve/reject)")
        elif st == "rejected":
            actions.append(f"{sid}: re-record / re-render")
        elif st == "failed":
            actions.append(f"{sid}: investigate failure, then retry")
    ranks = [mf.RANK.get(segs[s]["status"], 0) for s in manifest["order"]]
    asm = manifest["assembly"]["status"]
    rub = manifest.get("rubric") or {}
    if all(r >= _RENDERED for r in ranks) and asm in ("planned", "failed"):
        if not rub.get("plan_approved"):
            actions.append("PROGRAM: approve the plan rubric -> `deepdive approve-plan`")
        actions.append("PROGRAM: all segments ready -> `deepdive assemble`")
    if asm == "assembled" and not rub.get("film_approved"):
        actions.append("PROGRAM: watch the master, then `deepdive approve-film`")
    if asm == "assembled" and rub.get("film_approved"):
        actions.append("PROGRAM: publishable — hand off to Phase 3 (publish; not in this tool)")
    return actions


def report(program):
    manifest = mf.load(program)
    drift = mf.reconcile(program, manifest)
    rows = []
    for sid in manifest["order"]:
        s = manifest["segments"][sid]
        mp4 = mf.segment_mp4(program, sid, manifest)
        rows.append({"id": sid, "kind": s.get("kind"), "status": s["status"],
                     "review": s.get("review_status"),
                     "mp4_present": bool(mp4 and Path(mp4).exists()),
                     "owner_pid": s.get("owner_pid")})
    return {"program": manifest["program"]["slug"], "schema_version": manifest["schema_version"],
            "assembly": manifest["assembly"]["status"],
            "master": manifest["assembly"].get("master"),
            "validated": manifest["assembly"].get("validated"),
            "segments": rows, "drift": drift, "next_actions": _next_actions(manifest)}
