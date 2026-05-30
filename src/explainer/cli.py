"""explainer CLI — scaffolds a project and runs the pure-Python media pipeline.
The LLM generation stages (research/script/deck authoring) are done by the
/explainer skill, NOT here. This CLI never calls an LLM (PRD §5)."""
import argparse, json, sys, time
from datetime import date
from pathlib import Path

from .project import Project, ASPECTS
from . import deckbuild, manifest, wiki, ingest, themes, qa, presets, validate, handoff, brand
from .media import synth, align, render, mux

STAGES = [("narrate", synth.run), ("align", align.run), ("deck", deckbuild.run),
          ("render", render.run), ("mux", mux.run), ("manifest", manifest.run),
          ("qa", qa.run)]
STAGE_MAP = dict(STAGES)


def _log(proj, msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    with (proj.work / "run.log").open("a") as f:
        f.write(line + "\n")
    print(line)


def cmd_scaffold(args):
    aspect, safe_bottom, min_length = args.aspect, 0.14, args.min_length
    aspects = [a.strip() for a in args.aspects.split(",")] if args.aspects else None
    if args.platform:
        pre = presets.resolve(args.platform)
        if pre:
            aspect = pre["aspect"]
            safe_bottom = pre.get("safe_bottom", 0.14)
            if pre.get("min_length") and not min_length:
                min_length = pre["min_length"]
    if not aspects:
        aspects = [aspect]
    primary = aspects[0]
    w, h = ASPECTS[primary]
    slug = wiki.slugify(args.slug)
    out = Path(args.outdir).resolve() / f"{date.today().isoformat()}_{slug}"
    out.mkdir(parents=True, exist_ok=True)
    proj = {"title": args.title or args.slug, "slug": slug, "aspect": primary,
            "aspects": aspects, "width": w, "height": h, "fps": args.fps,
            "voice": args.voice, "voice_source": args.voice_source,
            "language": "en", "theme": args.theme, "safe_bottom": safe_bottom}
    if min_length:
        proj["min_length"] = min_length
    brand_note = None
    if args.brand:
        bdir, bdata = brand.resolve(args.brand)
        if bdir:
            proj["brand"] = brand.copy_into(out, bdir, bdata, args.brand)
            brand_note = f"brand '{args.brand}' ({proj['brand']['name']}) — watermark + CTA auto-added"
        else:
            brand_note = f"brand '{args.brand}' NOT FOUND in ./brand/ or ~/.claude/explainer-brands/ — skipped"
    (out / "project.json").write_text(json.dumps(proj, indent=2))
    print(json.dumps({"project_dir": str(out), "aspects": aspects, "brand": brand_note,
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


def cmd_ingest(args):
    proj = Project.load(args.project_dir)
    if args.pdf:
        print(json.dumps(ingest.ingest_pdf(proj, args.pdf, pages=args.pages), indent=2))
    elif args.url:
        print(json.dumps(ingest.ingest_url(proj, args.url, full_page=args.full_page), indent=2))
    else:
        print("provide --pdf <path> or --url <url>")
        return 1


def cmd_validate(args):
    print(json.dumps(validate.run(Project.load(args.project_dir)), indent=2))


def cmd_handoff(args):
    print(json.dumps(handoff.run(Project.load(args.project_dir)), indent=2))


def cmd_record(args):
    from . import recorder
    print(json.dumps(recorder.run(Project.load(args.project_dir), open_browser=not args.no_open), indent=2))


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
    s.add_argument("--voice", default="af_heart", help="Kokoro voice (when voice-source=kokoro)")
    s.add_argument("--voice-source", default="kokoro", choices=["kokoro", "operator"], dest="voice_source",
                   help="kokoro = local TTS; operator = your recorded voiceover (`explainer record`)")
    s.add_argument("--theme", default="midnight", choices=list(themes.THEMES))
    s.add_argument("--platform", default=None, choices=list(presets.PLATFORMS),
                   help="sets aspect + safe-zone (+ min length) from a platform preset")
    s.add_argument("--aspects", default=None, help="comma list to render simultaneously, e.g. '9:16,1:1'")
    s.add_argument("--min-length", type=int, default=None, dest="min_length",
                   help="minimum playback seconds (sets manifest length_warning if unmet)")
    s.add_argument("--brand", default=None,
                   help="brand slug (e.g. FFW); adds watermark + auto CTA end slide from the brand library")
    s.set_defaults(func=cmd_scaffold)

    m = sub.add_parser("media", help="run the pure-Python media pipeline on a project dir")
    m.add_argument("project_dir")
    m.add_argument("--only", default=None, help="comma list: narrate,align,deck,render,mux,manifest")
    m.set_defaults(func=cmd_media)

    for st in STAGE_MAP:
        sp = sub.add_parser(st, help=f"run only the {st} stage")
        sp.add_argument("project_dir")
        sp.set_defaults(func=cmd_stage, stage=st)

    ing = sub.add_parser("ingest", help="ingest source material (PDF/URL) into sources/")
    ing.add_argument("project_dir")
    ing.add_argument("--pdf", default=None, help="path to a PDF to ingest")
    ing.add_argument("--url", default=None, help="URL to screenshot + extract")
    ing.add_argument("--pages", default=None, help="PDF pages to render, e.g. '1-3,5' (default first 4)")
    ing.add_argument("--full-page", action="store_true", help="full-page URL screenshot")
    ing.set_defaults(func=cmd_ingest)

    rc = sub.add_parser("record", help="launch the integrated voiceover recorder (browser teleprompter)")
    rc.add_argument("project_dir")
    rc.add_argument("--no-open", action="store_true", help="don't auto-open the browser")
    rc.set_defaults(func=cmd_record)

    va = sub.add_parser("validate", help="check the manifest is a complete handoff contract")
    va.add_argument("project_dir")
    va.set_defaults(func=cmd_validate)

    ho = sub.add_parser("handoff", help="emit per-platform blotato-ready post specs from the manifest")
    ho.add_argument("project_dir")
    ho.set_defaults(func=cmd_handoff)

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
