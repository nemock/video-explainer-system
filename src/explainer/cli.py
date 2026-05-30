"""explainer CLI — scaffolds a project and runs the pure-Python media pipeline.
The LLM generation stages (research/script/deck authoring) are done by the
/explainer skill, NOT here. This CLI never calls an LLM (PRD §5)."""
import argparse, json, sys, time
from datetime import date
from pathlib import Path

from .project import Project, ASPECTS
from . import deckbuild, manifest, wiki
from .media import synth, align, render, mux

STAGES = [("narrate", synth.run), ("align", align.run), ("deck", deckbuild.run),
          ("render", render.run), ("mux", mux.run), ("manifest", manifest.run)]
STAGE_MAP = dict(STAGES)


def _log(proj, msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    with (proj.work / "run.log").open("a") as f:
        f.write(line + "\n")
    print(line)


def cmd_scaffold(args):
    w, h = ASPECTS[args.aspect]
    slug = wiki.slugify(args.slug)
    out = Path(args.outdir).resolve() / f"{date.today().isoformat()}_{slug}"
    out.mkdir(parents=True, exist_ok=True)
    proj = {"title": args.title or args.slug, "slug": slug, "aspect": args.aspect,
            "width": w, "height": h, "fps": args.fps, "voice": args.voice,
            "language": "en", "theme": {}}
    (out / "project.json").write_text(json.dumps(proj, indent=2))
    print(json.dumps({"project_dir": str(out), "project_json": str(out / "project.json"),
                      "next": "author script.json + deck.json, then `explainer media <dir>`"}, indent=2))


def cmd_media(args):
    proj = Project.load(args.project_dir)
    only = set(args.only.split(",")) if args.only else None
    results, t0 = {}, time.time()
    for name, fn in STAGES:
        if only and name not in only:
            continue
        ts = time.time()
        _log(proj, f"START {name}")
        try:
            results[name] = fn(proj)
        except Exception as e:
            _log(proj, f"FAIL  {name}: {type(e).__name__}: {e}")
            print(json.dumps({"failed_stage": name, "error": str(e)}))
            return 1
        _log(proj, f"OK    {name} ({time.time()-ts:.1f}s) {json.dumps(results[name])}")
    results["wall_clock_s"] = round(time.time() - t0, 2)
    proj.write_json(proj.work / "results.json", results)
    print("\n=== RESULTS ===")
    print(json.dumps(results, indent=2))
    return 0


def cmd_stage(args):
    proj = Project.load(args.project_dir)
    fn = STAGE_MAP[args.stage]
    print(json.dumps(fn(proj), indent=2))


def cmd_wiki(args):
    if args.kind == "source":
        path = wiki.add_node(args.root, "source", args.name, args.body or args.name,
                             topic=args.topic, ref=args.ref)
    else:
        path = wiki.add_node(args.root, "source-fact", args.name, args.body,
                             topic=args.topic, source=args.source,
                             confidence=args.confidence)
    print(json.dumps({"node": path}))


def main(argv=None):
    p = argparse.ArgumentParser(prog="explainer")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scaffold", help="create a project dir + project.json")
    s.add_argument("slug")
    s.add_argument("--title", default=None)
    s.add_argument("--outdir", default="outputs")
    s.add_argument("--aspect", default="9:16", choices=list(ASPECTS))
    s.add_argument("--fps", type=int, default=30)
    s.add_argument("--voice", default="af_heart")
    s.set_defaults(func=cmd_scaffold)

    m = sub.add_parser("media", help="run the pure-Python media pipeline on a project dir")
    m.add_argument("project_dir")
    m.add_argument("--only", default=None, help="comma list: narrate,align,deck,render,mux,manifest")
    m.set_defaults(func=cmd_media)

    for st in STAGE_MAP:
        sp = sub.add_parser(st, help=f"run only the {st} stage")
        sp.add_argument("project_dir")
        sp.set_defaults(func=cmd_stage, stage=st)

    wk = sub.add_parser("wiki", help="add a wiki node")
    wk.add_argument("kind", choices=["source", "fact"])
    wk.add_argument("name")
    wk.add_argument("--root", default=".")
    wk.add_argument("--topic", default="")
    wk.add_argument("--body", default="")
    wk.add_argument("--ref", default="")
    wk.add_argument("--source", default="")
    wk.add_argument("--confidence", default="medium")
    wk.set_defaults(func=cmd_wiki)

    args = p.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
