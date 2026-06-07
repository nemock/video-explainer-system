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
from . import assemble, manifest as mf, interstitials


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
    rep = assemble.run(prog, dry_run=args.dry_run)
    print(json.dumps(rep, indent=2))
    if rep.get("dry_run"):
        return 0
    return 0 if rep["validation"]["ok"] else 2


def cmd_status(args):
    prog = Program.load(args.program_dir)
    manifest = mf.load(prog)
    drift = mf.reconcile(prog, manifest)
    rows = [{"id": sid, "kind": s.get("kind"), "status": s["status"],
             "review": s.get("review_status")} for sid, s in manifest["segments"].items()]
    print(json.dumps({"program": manifest["program"]["slug"],
                      "assembly": manifest["assembly"]["status"],
                      "segments": rows, "drift": drift}, indent=2))


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
    a.set_defaults(func=cmd_assemble)

    s = sub.add_parser("status", help="manifest-vs-disk status of a program")
    s.add_argument("program_dir")
    s.set_defaults(func=cmd_status)

    args = p.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
