"""RENDER — owned Playwright frame-capture path. One viewport-driven deck rendered
at each requested aspect (PRD §G5). Drives renderAt(t) per frame at fixed fps.
Deterministic."""
import json, time, math
from playwright.sync_api import sync_playwright


def run(proj):
    timeline = json.loads((proj.work / "timeline.json").read_text())
    fps = proj.fps
    duration = timeline["duration"]
    total = math.ceil(duration * fps)
    deck_url = (proj.deck_dir / "index.html").as_uri()

    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb", "--hide-scrollbars", "--disable-gpu"])
        for aspect in proj.aspects:
            w, h = proj.size_for(aspect)
            label = aspect.replace(":", "x")
            fdir = proj.frames_dir(label)
            for f in fdir.glob("*.png"):
                f.unlink()
            page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
            page.goto(deck_url)
            page.wait_for_function("window.__deckReady === true")
            page.evaluate("tl => { window.TIMELINE = tl; }", timeline)
            cap_s, t_launch = 0.0, time.time()
            for i in range(total):
                page.evaluate("t => window.renderAt(t)", i / fps)
                ts = time.time()
                page.screenshot(path=str(fdir / f"f{i:05d}.png"), clip={"x": 0, "y": 0, "width": w, "height": h})
                cap_s += time.time() - ts
            page.close()
            results[aspect] = {"frames": total, "width": w, "height": h,
                               "capture_s": round(cap_s, 2),
                               "ms_per_frame": round(cap_s / total * 1000, 1) if total else 0,
                               "render_x_realtime": round(cap_s / duration, 2) if duration else 0}
        browser.close()

    proj.write_json(proj.work / "metrics_render.json", {"fps": fps, "aspects": results})
    return {"aspects": list(results), **{f"{a}_xRT": results[a]["render_x_realtime"] for a in results}}
