"""RENDER — owned Playwright frame-capture path. Load the built deck, drive it
with renderAt(t) per frame at a fixed fps, screenshot each frame. Deterministic."""
import json, time, math
from playwright.sync_api import sync_playwright


def run(proj):
    timeline = json.loads((proj.work / "timeline.json").read_text())
    w, h = proj.size
    fps = proj.fps
    duration = timeline["duration"]
    total = math.ceil(duration * fps)

    for f in proj.frames.glob("*.png"):
        f.unlink()
    deck_url = (proj.deck_dir / "index.html").as_uri()
    clip = {"x": 0, "y": 0, "width": w, "height": h}

    cap_s = 0.0
    t_launch = time.time()
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb", "--hide-scrollbars", "--disable-gpu"])
        page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        page.goto(deck_url)
        page.wait_for_function("window.__deckReady === true")
        page.evaluate("tl => { window.TIMELINE = tl; }", timeline)
        launch_s = time.time() - t_launch
        for i in range(total):
            page.evaluate("t => window.renderAt(t)", i / fps)
            ts = time.time()
            page.screenshot(path=str(proj.frames / f"f{i:05d}.png"), clip=clip)
            cap_s += time.time() - ts
        browser.close()

    metrics = {"fps": fps, "frames": total, "width": w, "height": h,
               "launch_s": round(launch_s, 2), "capture_s": round(cap_s, 2),
               "ms_per_frame": round(cap_s / total * 1000, 1) if total else 0,
               "render_x_realtime": round(cap_s / duration, 2) if duration else 0}
    proj.write_json(proj.work / "metrics_render.json", metrics)
    return metrics
