"""Orchestrator — drives one segment through the engine pipeline with the manifest lifecycle,
the alignment-confidence gate, and the single-writer status channel (ARCHITECTURE §6).

Each non-interstitial segment is its own `explainer` project (script.json + deck.json authored
by the operator / the `/deepdive` skill). `build_segment` runs narrate -> align -> GATE ->
render -> mux, transitioning planned->recorded->rendered and refusing to render an operator take
that fails the gate. `record_segment` is the operator path: it surfaces the prior segment's
hand-off line into the teleprompter, records, then builds. (The media stages are reused as-is;
nothing here re-implements the engine.)"""
import json

from .. import deckbuild
from ..media import synth, align, render, mux
from . import buildlog, gate, manifest as mf, segstatus


def handoff_context(program, seg_id):
    """The prior segment's closing line — surfaced into the teleprompter so multi-session takes
    stay tonally continuous (ARCHITECTURE §8.2). Returns {prior_id, closing_line} or None."""
    order = program.order
    if seg_id not in order:
        return None
    i = order.index(seg_id)
    for j in range(i - 1, -1, -1):
        prior = order[j]
        if program.is_interstitial(prior):
            continue
        sp = program.project_dir(prior) / "script.json"
        if sp.exists():
            segs = json.loads(sp.read_text()).get("segments", [])
            if segs:
                return {"prior_id": prior, "closing_line": segs[-1].get("text", "").strip()}
        break
    return None


def build_segment(program, seg_id, *, run_gate=True, render=True):
    """Run a segment's media pipeline with lifecycle + gate. Returns a report. If an OPERATOR take
    fails the alignment gate, render is blocked and the segment stays `recorded` for a re-record or
    a manual transcript correction (edit script.json + rebuild).

    `render=False` stops after the gate (narrate -> align -> GATE) — the fast path for the record
    sprint, so the operator powers through takes and the slow frame-capture render happens in a
    later batch (`build_segment` again with render=True, or `deepdive build-segment`)."""
    if program.is_interstitial(seg_id):
        raise ValueError(f"'{seg_id}' is an interstitial — assembled from the registry, not built")
    manifest = mf.load(program)
    proj = program.as_project(seg_id)
    mf.claim(program, manifest, seg_id)
    try:
        with buildlog.timed(program, "narrate", seg_id):
            synth.run(proj)
        segstatus.report(proj.dir, "narrate", True)
        mf.transition(program, manifest, seg_id, "recorded", force=True)

        with buildlog.timed(program, "align", seg_id):
            align.run(proj)
        segstatus.report(proj.dir, "align", True)

        g = gate.evaluate(proj, program.data.get("gate")) if run_gate else {"passed": True}
        manifest["segments"][seg_id]["gate"] = g
        mf.write(program, manifest)
        if not g["passed"] and proj.voice_source == "operator":
            segstatus.report(proj.dir, "gate", False, g)
            return {"seg": seg_id, "stopped": "alignment-gate", "status": "recorded", "gate": g}

        if not render:  # record-sprint fast path: gated but not yet rendered
            return {"seg": seg_id, "status": "recorded", "gate": g, "rendered": False}

        with buildlog.timed(program, "deck", seg_id):
            deckbuild.run(proj)
        with buildlog.timed(program, "render", seg_id):
            render.run(proj)
        with buildlog.timed(program, "mux", seg_id):
            mux.run(proj)
        segstatus.report(proj.dir, "render", True)
        segstatus.report(proj.dir, "mux", True)
        mf.transition(program, manifest, seg_id, "rendered", force=True)
        return {"seg": seg_id, "status": "rendered", "gate": g}
    finally:
        mf.release(program, manifest, seg_id)


def record_segment(program, seg_id, *, open_browser=True, render=True):
    """Operator path: surface the hand-off context, launch the teleprompter recorder, then build.
    Requires an operator at the machine — the recorder blocks until takes are captured. With
    `render=False` (the record sprint) it stops after the alignment gate so the next segment can be
    recorded immediately; render the batch afterward."""
    from .. import recorder
    proj = program.as_project(seg_id)
    ctx = handoff_context(program, seg_id)
    if ctx:
        print(f"[hand-off] continue the tone from '{ctx['prior_id']}', which closed on:\n"
              f"    “{ctx['closing_line']}”\n")
    recorder.run(proj, open_browser=open_browser)   # captures voiceover/seg_*.wav
    return build_segment(program, seg_id, render=render)


def review(program, seg_id, decision, *, notes=None):
    """Per-segment approve/reject gate (distinct from `rendered`). Assembly gates on `approved`."""
    if decision not in ("approve", "reject"):
        raise ValueError("decision must be 'approve' or 'reject'")
    manifest = mf.load(program)
    to = "approved" if decision == "approve" else "rejected"
    mf.transition(program, manifest, seg_id, to, review_status=to, notes=notes)
    return {"seg": seg_id, "status": to, "notes": notes}
