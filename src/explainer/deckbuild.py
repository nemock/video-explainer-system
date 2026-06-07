"""DECK — build a standalone deck/index.html from deck.json + the fixed-theme
assets. Content is data-driven (the engine renders slide types); Claude authors
deck.json, never raw HTML, which keeps the determinism contract intact."""
import json
import shutil
from pathlib import Path

ASSETS = Path(__file__).parent / "assets"

# Bundled variable woff2 (assets/fonts/) per family. A theme opts in via a
# `fonts: {display, body}` field (see themes.py); families not listed here fall
# back to the system stack. Variable files cover the full weight range + italic.
FONT_FILES = {
    "Fraunces": [("normal", "fraunces-wght-normal.woff2"), ("italic", "fraunces-wght-italic.woff2")],
    "Inter": [("normal", "inter-wght-normal.woff2")],
    # Archivo variable carries BOTH a weight and a width axis (see FONT_STRETCH) so the FWF
    # theme can render a genuine condensed 800 via `font-stretch` in deck.css.
    "Archivo": [("normal", "archivo-wdth-wght-normal.woff2")],
}
FONT_STACK = {"Fraunces": "Georgia, serif", "Inter": "-apple-system, 'Helvetica Neue', Arial, sans-serif",
              "Archivo": "'Helvetica Neue', Arial, sans-serif"}
# Families with a usable width (wdth) axis: the @font-face must advertise the stretch range
# or browsers clamp to normal and `font-stretch`/condensed becomes a no-op.
FONT_STRETCH = {"Archivo": "62% 125%"}


def _font_css(theme, deck_dir):
    """Return CSS (@font-face rules + --font-display/--font-body vars) for a theme's
    `fonts` field, copying the needed woff2 into <deck>/fonts/. Empty string when the
    theme declares no fonts — so themes without `fonts` render exactly as before."""
    fonts = theme.get("fonts") or {}
    if not fonts:
        return ""
    faces, copied = [], set()
    for role in ("display", "body"):
        fam = fonts.get(role)
        for style, fn in FONT_FILES.get(fam, []):
            if fn in copied:
                continue
            src = ASSETS / "fonts" / fn
            if not src.exists():
                continue
            (deck_dir / "fonts").mkdir(parents=True, exist_ok=True)
            shutil.copy(src, deck_dir / "fonts" / fn)
            stretch = f"font-stretch:{FONT_STRETCH[fam]};" if fam in FONT_STRETCH else ""
            faces.append(f"@font-face{{font-family:'{fam}';font-weight:100 900;{stretch}"
                         f"font-style:{style};font-display:block;src:url('fonts/{fn}') format('woff2');}}")
            copied.add(fn)
    vars_ = []
    if fonts.get("display"):
        vars_.append(f"--font-display:'{fonts['display']}',{FONT_STACK.get(fonts['display'], 'serif')};")
    if fonts.get("body"):
        vars_.append(f"--font-body:'{fonts['body']}',{FONT_STACK.get(fonts['body'], 'sans-serif')};")
    out = "\n".join(faces)
    if vars_:
        out += f"\n:root{{{''.join(vars_)}}}"
    return out


def run(proj):
    deck = json.loads(proj.deck_json.read_text())
    # figure images are authored relative to the project root (e.g. "sources/x.png");
    # the deck lives one level down in deck/, so resolve to "../sources/x.png".
    for s in deck.get("slides", []):
        img = s.get("image")
        if s.get("type") == "figure" and img and not img.startswith(("/", "../", "http")):
            s["image"] = "../" + img
    theme = proj.theme
    # theme name drives a `data-theme` attr so a theme can carry CSS-scoped treatments
    # (e.g. fwf: condensed font + ALL-CAPS titles + grain/vignette) without touching others.
    theme_name = proj.data.get("theme") if isinstance(proj.data.get("theme"), str) else "custom"
    deck["motion"] = theme.get("motion", "rise")  # theme's default per-slide intro
    deck["safe_bottom"] = proj.safe_bottom         # platform safe-zone inset for captions
    # ambient drifting glow: project overrides theme default overrides global default (True).
    # fwf sets ambient:false (flat purple, vignette only — no drifting accent gradient).
    deck["ambient"] = bool(proj.data.get("ambient", theme.get("ambient", True)))
    # caption style: "window" (default, TikTok-style — only ~caption_window words shown at a
    # time) or "full" (legacy, whole-slide kinetic captions). Override per project via project.json.
    deck["caption_mode"] = proj.data.get("caption_mode", "window")
    deck["caption_window"] = int(proj.data.get("caption_window", 4))

    # branding: watermark on every slide + an auto-appended CTA end slide (assets are
    # project-relative, e.g. "brand/logo.png"; the deck lives one level down in deck/).
    brand = proj.brand or {}
    if brand:
        if brand.get("logo"):
            deck["watermark"] = "../" + brand["logo"]
            deck["watermark_corner"] = brand.get("watermark_corner", "bl")
        bc = {"name": brand.get("name", ""), "cta": brand.get("cta", {})}
        if brand.get("logo"):
            bc["logo"] = "../" + brand["logo"]
        if brand.get("product"):
            bc["product"] = "../" + brand["product"]
        deck["brand"] = bc
        if not any(s.get("id") == "cta" for s in deck.get("slides", [])):
            deck.setdefault("slides", []).append({"id": "cta", "type": "cta"})
    w, h = proj.size
    base = (ASSETS / "deck_base.html").read_text()
    css = (ASSETS / "deck.css").read_text()
    engine = (ASSETS / "deck_engine.js").read_text()
    fontcss = _font_css(theme, proj.deck_dir)

    html = (base
            .replace("{{TITLE}}", str(deck.get("title", proj.data.get("title", "Explainer"))))
            .replace("{{THEME}}", theme_name)
            .replace("{{BG}}", theme["bg"]).replace("{{FG}}", theme["fg"])
            .replace("{{ACCENT}}", theme["accent"]).replace("{{ACCENT2}}", theme["accent2"])
            .replace("{{W}}", str(w)).replace("{{H}}", str(h))
            .replace("{{FONTCSS}}", fontcss)
            .replace("{{CSS}}", css)
            .replace("{{DECK_JSON}}", json.dumps(deck))
            .replace("{{ENGINE}}", engine))
    out = proj.deck_dir / "index.html"
    out.write_text(html)
    return {"slides": len(deck.get("slides", [])), "deck_html": str(out.relative_to(proj.dir))}
