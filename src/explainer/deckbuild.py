"""DECK — build a standalone deck/index.html from deck.json + the fixed-theme
assets. Content is data-driven (the engine renders slide types); Claude authors
deck.json, never raw HTML, which keeps the determinism contract intact."""
import json
from pathlib import Path

ASSETS = Path(__file__).parent / "assets"


def run(proj):
    deck = json.loads(proj.deck_json.read_text())
    # figure images are authored relative to the project root (e.g. "sources/x.png");
    # the deck lives one level down in deck/, so resolve to "../sources/x.png".
    for s in deck.get("slides", []):
        img = s.get("image")
        if s.get("type") == "figure" and img and not img.startswith(("/", "../", "http")):
            s["image"] = "../" + img
    theme = proj.theme
    deck["motion"] = theme.get("motion", "rise")  # theme's default per-slide intro
    deck["safe_bottom"] = proj.safe_bottom         # platform safe-zone inset for captions
    deck["ambient"] = bool(proj.data.get("ambient", True))  # drifting glow (set false for ~2x faster render)

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

    html = (base
            .replace("{{TITLE}}", str(deck.get("title", proj.data.get("title", "Explainer"))))
            .replace("{{BG}}", theme["bg"]).replace("{{FG}}", theme["fg"])
            .replace("{{ACCENT}}", theme["accent"]).replace("{{ACCENT2}}", theme["accent2"])
            .replace("{{W}}", str(w)).replace("{{H}}", str(h))
            .replace("{{CSS}}", css)
            .replace("{{DECK_JSON}}", json.dumps(deck))
            .replace("{{ENGINE}}", engine))
    out = proj.deck_dir / "index.html"
    out.write_text(html)
    return {"slides": len(deck.get("slides", [])), "deck_html": str(out.relative_to(proj.dir))}
