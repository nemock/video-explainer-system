"""deepdive CLI — the long-form orchestrator surface (mirrors `explainer`). Phase 2.0 ships the
assembly spine: `new` (scaffold a program), `assemble` (conform + concat + caption/chapter +
validate), `status` (manifest-vs-disk). The record loop, gates, and editorial layer are 2.1+.
This CLI never calls an LLM — that's the `/deepdive` skill's job."""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .program import Program, CANONICAL_ORDER
from . import assemble, manifest as mf, doctor, orchestrator, gate as gate_mod, rubric, packaging


def _slug(s):
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")


def cmd_new(args):
    slug = _slug(args.slug)
    out = Path(args.outdir).resolve() / f"{date.today().isoformat()}_{slug}"
    out.mkdir(parents=True, exist_ok=True)
    segs = {}
    for sid in CANONICAL_ORDER:
        if sid.endswith("sponsor"):
            ref = "interstitial-fwf-book" if sid.startswith("fwf") else "interstitial-the-build"
            segs[sid] = {"kind": "interstitial", "registry_ref": ref, "title": sid}
        else:
            segs[sid] = {"kind": "act", "title": sid}
    program_json = {"slug": slug, "title": args.title or args.slug, "fps": args.fps,
                    "brand": "FFW", "aspect": "16:9", "order": CANONICAL_ORDER,
                    "segments": segs, "caption_style": "bottom-2line"}
    (out / "program.json").write_text(json.dumps(program_json, indent=2))
    prog = Program.load(out)
    mf.write(prog, mf.new_manifest(prog))
    print(json.dumps({"program_dir": str(out), "order": CANONICAL_ORDER,
                      "next": "render act segments as explainer projects under segments/<id>/, then `deepdive assemble`"},
                     indent=2))


def cmd_assemble(args):
    prog = Program.load(args.program_dir)
    if args.check:
        rep = assemble.preflight(prog, check_only=True)
        print(json.dumps(rep, indent=2))
        return 0 if rep["ok"] else 2
    try:
        rep = assemble.run(prog, dry_run=args.dry_run, allow_unapproved=args.allow_unapproved)
    except RuntimeError as e:
        print(json.dumps({"error": str(e)}, indent=2))
        return 2
    print(json.dumps(rep, indent=2))
    if rep.get("dry_run"):
        return 0
    return 0 if rep["validation"]["ok"] else 2


def cmd_plan(args):
    prog = Program.load(args.program_dir)
    p = prog.dir / "content-plan.md"
    if p.exists() and not args.force:
        print(json.dumps({"content_plan": str(p), "note": "exists — pass --force to overwrite"}))
        return 0
    p.write_text(rubric.content_plan_template(prog))
    print(json.dumps({"content_plan": str(p), "next": "author the spine, then `deepdive rubric <dir> plan`"}, indent=2))


def cmd_rubric(args):
    print(json.dumps({"kind": args.kind, "checklist": rubric.checklist(args.kind)}, indent=2))


def cmd_approve_plan(args):
    prog = Program.load(args.program_dir); m = mf.load(prog)
    rubric.record(prog, m, "plan", rubric.checklist("plan"), approved=True, notes=args.notes or "")
    print(json.dumps({"plan_approved": True, "variety": rubric.variety_check(prog)}, indent=2))


def cmd_approve_film(args):
    prog = Program.load(args.program_dir); m = mf.load(prog)
    rubric.record(prog, m, "film", rubric.checklist("film"), approved=True, notes=args.notes or "")
    print(json.dumps({"film_approved": True}, indent=2))


def cmd_set_arc(args):
    prog = Program.load(args.program_dir); m = mf.load(prog)
    rubric.set_arc(prog, m, hook_archetype=args.hook, three_act_rhythm=args.rhythm,
                   payoff_type=args.payoff)
    print(json.dumps({"arc": m["rubric"]["arc"], "variety": rubric.variety_check(prog)}, indent=2))


def cmd_thumbnail(args):
    prog = Program.load(args.program_dir)
    accent = [a.strip() for a in args.accent.split(",")] if args.accent else None
    out = args.out or (prog.dir / "packaging" / "thumbnail.png")
    rep = packaging.thumbnail(prog, args.text, out, accent=accent, logo=args.logo, selfie=args.selfie)
    print(json.dumps(rep, indent=2))


def cmd_package(args):
    prog = Program.load(args.program_dir)
    out = {}
    if args.titles:
        out.update(packaging.write_title_variants(prog, [t.strip() for t in args.titles.split("||")]))
    else:
        out.update(packaging.write_title_variants(prog, packaging.TITLE_TEMPLATE))
        out["note"] = "title-variants.md scaffolded with templates — author benefit-forward variants"
    if args.text:
        out.update(packaging.thumbnail(prog, args.text,
                                       prog.dir / "packaging" / "thumbnail.png",
                                       accent=[a.strip() for a in args.accent.split(",")] if args.accent else None,
                                       selfie=args.selfie))
    print(json.dumps(out, indent=2))


def cmd_status(args):
    rep = doctor.report(Program.load(args.program_dir))
    print(json.dumps({"program": rep["program"], "assembly": rep["assembly"],
                      "segments": [{"id": s["id"], "status": s["status"]} for s in rep["segments"]],
                      "drift_ok": rep["drift"]["ok"]}, indent=2))


def cmd_doctor(args):
    rep = doctor.report(Program.load(args.program_dir))
    print(json.dumps(rep, indent=2))
    return 0 if rep["drift"]["ok"] else 1


def cmd_build_segment(args):
    rep = orchestrator.build_segment(Program.load(args.program_dir), args.seg_id,
                                     run_gate=not args.no_gate)
    print(json.dumps(rep, indent=2))
    return 2 if rep.get("stopped") else 0


def cmd_record(args):
    rep = orchestrator.record_segment(Program.load(args.program_dir), args.seg_id,
                                      open_browser=not args.no_open)
    print(json.dumps(rep, indent=2))
    return 2 if rep.get("stopped") else 0


def cmd_gate(args):
    prog = Program.load(args.program_dir)
    rep = gate_mod.evaluate(prog.as_project(args.seg_id), prog.data.get("gate"))
    print(json.dumps(rep, indent=2))
    return 0 if rep["passed"] else 2


def cmd_review(args):
    rep = orchestrator.review(Program.load(args.program_dir), args.seg_id, args.decision,
                              notes=args.notes)
    print(json.dumps(rep, indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(prog="deepdive", description="Deep-dive long-form orchestrator/assembler.")
    sub = p.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("new", help="scaffold a program dir + program.json + manifest")
    n.add_argument("slug")
    n.add_argument("--title", default=None)
    n.add_argument("--outdir", default="deep-dive/programs")
    n.add_argument("--fps", type=int, default=30)
    n.set_defaults(func=cmd_new)

    a = sub.add_parser("assemble", help="conform + concat + caption/chapter + validate -> master")
    a.add_argument("program_dir")
    a.add_argument("--check", action="store_true", help="preflight conformance table only")
    a.add_argument("--dry-run", action="store_true", help="ordered plan + chapter preview, no encode")
    a.add_argument("--allow-unapproved", action="store_true",
                   help="bypass the plan/segment approval gate (automated spine/demo runs)")
    a.set_defaults(func=cmd_assemble)

    pl = sub.add_parser("plan", help="scaffold content-plan.md (throughline spine + open-loop ledger)")
    pl.add_argument("program_dir")
    pl.add_argument("--force", action="store_true")
    pl.set_defaults(func=cmd_plan)

    ru = sub.add_parser("rubric", help="emit a rubric checklist (plan|film) for self-critique")
    ru.add_argument("program_dir")
    ru.add_argument("kind", choices=["plan", "film"])
    ru.set_defaults(func=cmd_rubric)

    ap = sub.add_parser("approve-plan", help="record plan-rubric approval (gates recording/assembly)")
    ap.add_argument("program_dir")
    ap.add_argument("--notes", default=None)
    ap.set_defaults(func=cmd_approve_plan)

    af = sub.add_parser("approve-film", help="record whole-film rubric approval (gates publish)")
    af.add_argument("program_dir")
    af.add_argument("--notes", default=None)
    af.set_defaults(func=cmd_approve_film)

    sa = sub.add_parser("set-arc", help="record the film's archetype for the structural-variety guard")
    sa.add_argument("program_dir")
    sa.add_argument("--hook", required=True, help="hook archetype (e.g. surprising-stat, bold-claim)")
    sa.add_argument("--rhythm", required=True, help="three-act rhythm (e.g. problem-insight-playbook)")
    sa.add_argument("--payoff", required=True, help="payoff type (e.g. transformation, reveal, system)")
    sa.set_defaults(func=cmd_set_arc)

    th = sub.add_parser("thumbnail", help="render the FWF 1280x720 thumbnail composite")
    th.add_argument("program_dir")
    th.add_argument("--text", required=True, help="3–5-word keyword line")
    th.add_argument("--accent", default=None, help="comma list of words to render in indigo")
    th.add_argument("--logo", default=None, help="logo PNG (default: the program brand's logo)")
    th.add_argument("--selfie", default=None, help="optional operator selfie PNG (bottom-right)")
    th.add_argument("--out", default=None)
    th.set_defaults(func=cmd_thumbnail)

    pk = sub.add_parser("package", help="title-variants.md (+ thumbnail with --text)")
    pk.add_argument("program_dir")
    pk.add_argument("--titles", default=None, help="'||'-separated benefit-forward title variants")
    pk.add_argument("--text", default=None, help="thumbnail keyword line (renders the thumbnail too)")
    pk.add_argument("--accent", default=None)
    pk.add_argument("--selfie", default=None)
    pk.set_defaults(func=cmd_package)

    s = sub.add_parser("status", help="concise manifest-vs-disk status of a program")
    s.add_argument("program_dir")
    s.set_defaults(func=cmd_status)

    dr = sub.add_parser("doctor", help="full health check: lifecycle checklist + drift + next actions")
    dr.add_argument("program_dir")
    dr.set_defaults(func=cmd_doctor)

    bs = sub.add_parser("build-segment", help="run a segment: narrate -> align -> gate -> render -> mux")
    bs.add_argument("program_dir")
    bs.add_argument("seg_id")
    bs.add_argument("--no-gate", action="store_true", help="skip the alignment-confidence gate")
    bs.set_defaults(func=cmd_build_segment)

    rc = sub.add_parser("record", help="operator path: teleprompter (w/ hand-off context) -> build")
    rc.add_argument("program_dir")
    rc.add_argument("seg_id")
    rc.add_argument("--no-open", action="store_true", help="don't auto-open the recorder browser")
    rc.set_defaults(func=cmd_record)

    g = sub.add_parser("gate", help="run the alignment-confidence gate on a built segment")
    g.add_argument("program_dir")
    g.add_argument("seg_id")
    g.set_defaults(func=cmd_gate)

    rv = sub.add_parser("review", help="approve/reject a rendered segment (assembly gates on approved)")
    rv.add_argument("program_dir")
    rv.add_argument("seg_id")
    rv.add_argument("decision", choices=["approve", "reject"])
    rv.add_argument("--notes", default=None)
    rv.set_defaults(func=cmd_review)

    args = p.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
