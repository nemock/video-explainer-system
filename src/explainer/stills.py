"""STILLS — export one PNG per slide from the rendered deck, for repurposing/reference
(carousel re-use, thumbnails, decks, blog). Renders deck/index.html via Playwright and
drives renderAt(t) to each slide's *settled* moment (past the intro motion), then
screenshots. Read-only w.r.t. the pipeline; requires the deck + timeline, so run it
after `explainer media` (or at least the deck + align stages)."""
import json
from playwright.sync_api import sync_playwright


def run(proj, aspect=None):
    timeline = json.loads((proj.work / "timeline.json").read_text())
    slides = timeline["slides"]
    duration = timeline["duration"]
    aspect = aspect or proj.aspect
    w, h = proj.size_for(aspect)
    deck_url = (proj.deck_dir / "index.html").as_uri()
    out = proj.dir / "stills"
    out.mkdir(exist_ok=True)
    for f in out.glob("*.png"):
        f.unlink()

    written = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb", "--hide-scrollbars", "--disable-gpu"])
        page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        page.goto(deck_url)
        page.wait_for_function("window.__deckReady === true")
        page.evaluate("tl => { window.TIMELINE = tl; }", timeline)
        for i, s in enumerate(slides, 1):
            win = s["end"] - s["start"]
            # settle past the intro transition, before the next slide takes over
            t = s["start"] + min(win * 0.6, max(0.8, win - 0.2))
            t = max(s["start"], min(t, duration - 0.01))
            page.evaluate("t => window.renderAt(t)", t)
            name = f"slide_{i:02d}_{s['id']}.png"
            page.screenshot(path=str(out / name), clip={"x": 0, "y": 0, "width": w, "height": h})
            written.append(name)
        page.close()
        browser.close()

    return {"aspect": aspect, "count": len(written), "dir": "stills", "files": written}
