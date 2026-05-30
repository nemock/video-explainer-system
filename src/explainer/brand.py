"""Brand library (watermark logo + product image + CTA copy). Resolved by slug
with **local-first, then global** precedence:
  1. ./brand/<SLUG>/         (the content project you run /explainer from)
  2. $EXPLAINER_BRAND_DIR/<SLUG>/
  3. ~/.claude/explainer-brands/<SLUG>/   (shared library; define your brands once)

A brand folder has a brand.json + asset files:
  { "name": "...", "logo": "logo.png", "product": "book.png",
    "cta": { "headline": "...", "subkicker": "...", "url": "...", "spoken": "..." },
    "accent": "#hex" (optional theme tint), "watermark_corner": "bl|br",
    "talk_time": { "tag": "<brand-tag>", "library": "/abs/path/to/library" (optional) } }

The optional `talk_time` block links the brand to a slice of the talk-time library
(the operator's curated takes/quotes/anecdotes). `tag` filters the library by brand;
`library` overrides the default path. Used by `explainer talktime` and the script-writing
skill to author narration in the operator's real voice. See talktime.py.

A brand folder MAY also hold a hand-editable `cta_library.json` of CTA variants:
  { "default": "book",
    "variants": {
      "book":       { "headline": "...", "subkicker": "...", "url": "...",
                      "product": "book.png" (optional), "spoken": "..." },
      "newsletter": { "headline": "...", ... } } }
Scaffold with `--cta <variant>` to pick one (falls back to the library `default`, then to
brand.json `cta`). Lets the operator maintain rotating CTAs by hand without code changes.
"""
import json, os, shutil
from pathlib import Path


def load_cta_library(brand_dir):
    """Return the brand's cta_library.json (or {} if none)."""
    p = Path(brand_dir) / "cta_library.json"
    return json.loads(p.read_text()) if p.exists() else {}


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


def copy_into(project_dir, brand_dir, data, slug, cta_variant=None):
    """Copy brand assets into <project>/brand/ and return a project-relative brand config
    (stored in project.json so the render is self-contained / portable).

    CTA resolution: a `--cta <variant>` (or the cta_library `default`) selects a variant
    from cta_library.json — its copy + its own `product` image; otherwise brand.json `cta`
    and `product` are used."""
    dest = Path(project_dir) / "brand"
    dest.mkdir(exist_ok=True)

    cta = dict(data.get("cta", {}))
    product = data.get("product")
    cta_note = None
    lib = load_cta_library(brand_dir)
    variants = lib.get("variants", {})
    chosen = cta_variant or lib.get("default")
    if chosen and chosen in variants:
        v = variants[chosen]
        cta = {k: v[k] for k in ("headline", "subkicker", "url", "spoken") if k in v}
        product = v.get("product", None)  # variant owns its product (book cover vs none)
        cta_note = chosen
    elif cta_variant:
        cta_note = f"{cta_variant} (NOT FOUND in cta_library.json — used brand.json cta)"

    cfg = {"slug": slug, "name": data.get("name", slug), "cta": cta,
           "watermark_corner": data.get("watermark_corner", "bl")}
    if cta_note:
        cfg["cta_variant"] = cta_note
    if data.get("accent"):
        cfg["accent"] = data["accent"]
    if data.get("lexicon"):
        cfg["lexicon"] = data["lexicon"]  # brand-specific pronunciations (e.g. domains)
    if data.get("talk_time"):
        cfg["talk_time"] = data["talk_time"]  # {tag, library?} — write the script in the operator's voice
    for key, fn in (("logo", data.get("logo")), ("product", product)):
        if fn and (brand_dir / fn).exists():
            shutil.copy(brand_dir / fn, dest / fn)
            cfg[key] = f"brand/{fn}"
    return cfg
