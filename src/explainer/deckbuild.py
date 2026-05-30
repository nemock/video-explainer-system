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
