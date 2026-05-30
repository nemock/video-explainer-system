"""Brand library (watermark logo + product image + CTA copy). Resolved by slug
with **local-first, then global** precedence:
  1. ./brand/<SLUG>/         (the content project you run /explainer from)
  2. $EXPLAINER_BRAND_DIR/<SLUG>/
  3. ~/.claude/explainer-brands/<SLUG>/   (shared library; define FFW, BRG once)

A brand folder has a brand.json + asset files:
  { "name": "...", "logo": "logo.png", "product": "book.png",
    "cta": { "headline": "...", "subkicker": "...", "url": "...", "spoken": "..." },
    "accent": "#hex" (optional theme tint), "watermark_corner": "bl|br",
    "talk_time": { "tag": "brg", "library": "/abs/path" (optional) } }

The optional `talk_time` block links the brand to a slice of the talk-time library
(the operator's curated takes/quotes/anecdotes). `tag` filters the library by brand;
`library` overrides the default path. Used by `explainer talktime` and the script-writing
skill to author narration in the operator's real voice. See talktime.py.
"""
import json, os, shutil
from pathlib import Path


def _candidates(slug):
    yield Path.cwd() / "brand" / slug
    env = os.environ.get("EXPLAINER_BRAND_DIR")
    if env:
        yield Path(env) / slug
    yield Path.home() / ".claude" / "explainer-brands" / slug


def resolve(slug):
    """Return (brand_dir, data) for the first candidate with a brand.json, else (None, None)."""
    for d in _candidates(slug):
        if (d / "brand.json").exists():
            return d, json.loads((d / "brand.json").read_text())
    return None, None


def copy_into(project_dir, brand_dir, data, slug):
    """Copy brand assets into <project>/brand/ and return a project-relative brand config
    (stored in project.json so the render is self-contained / portable)."""
    dest = Path(project_dir) / "brand"
    dest.mkdir(exist_ok=True)
    cfg = {"slug": slug, "name": data.get("name", slug), "cta": data.get("cta", {}),
           "watermark_corner": data.get("watermark_corner", "bl")}
    if data.get("accent"):
        cfg["accent"] = data["accent"]
    if data.get("lexicon"):
        cfg["lexicon"] = data["lexicon"]  # brand-specific pronunciations (e.g. domains)
    if data.get("talk_time"):
        cfg["talk_time"] = data["talk_time"]  # {tag, library?} — write the script in the operator's voice
    for key in ("logo", "product"):
        fn = data.get(key)
        if fn and (brand_dir / fn).exists():
            shutil.copy(brand_dir / fn, dest / fn)
            cfg[key] = f"brand/{fn}"
    return cfg
