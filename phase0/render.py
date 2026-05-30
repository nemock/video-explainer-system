#!/usr/bin/env python3
"""Phase 0 — RENDER stage.
Owned Playwright frame-capture path: load the deterministic deck, drive it with
window.renderAt(t) per frame at a FIXED fps, screenshot each frame. No CSS
animation, no wall-clock dependence -> deterministic. This run measures the
render-time gate (ms/frame, total) and peak memory.

Run: myenv/bin/python3 phase0/render.py [fps_override]
"""
import json, time, sys, math, resource
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
FRAMES = WORK / "frames"

def main():
    script = json.loads((HERE / "script.json").read_text())
    timeline = json.loads((WORK / "timeline.json").read_text())
    W, H = script["width"], script["height"]
    fps = int(sys.argv[1]) if len(sys.argv) > 1 else script["fps"]
    duration = timeline["duration"]
    total = math.ceil(duration * fps)

    if FRAMES.exists():
        for f in FRAMES.glob("*.png"):
            f.unlink()
    FRAMES.mkdir(parents=True, exist_ok=True)

    deck_url = (HERE / "deck" / "index.html").as_uri()
    clip = {"x": 0, "y": 0, "width": W, "height": H}

    t_launch = time.time()
    cap_s = 0.0
    with sync_playwright() as p:
        browser = p.chromium.launch(args=[
            "--force-color-profile=srgb", "--hide-scrollbars", "--disable-gpu"])
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        # determinism guards (deck doesn't use them, but the real pipeline mandates this)
        page.add_init_script("Math.random = (function(){let s=42;return function(){"
                             "s=(s*1103515245+12345)&0x7fffffff;return s/0x7fffffff;};})();")
        page.goto(deck_url)
        page.wait_for_function("window.__deckReady === true")
        page.evaluate("tl => { window.TIMELINE = tl; }", timeline)
        launch_s = time.time() - t_launch

        for i in range(total):
            t = i / fps
            page.evaluate("t => window.renderAt(t)", t)
            ts = time.time()
            page.screenshot(path=str(FRAMES / f"f{i:05d}.png"), clip=clip)
            cap_s += time.time() - ts
        browser.close()

    peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)  # macOS: bytes
    metrics = {"fps": fps, "frames": total, "width": W, "height": H,
               "launch_s": round(launch_s, 2),
               "capture_s": round(cap_s, 2),
               "ms_per_frame": round(cap_s / total * 1000, 1),
               "render_x_realtime": round(cap_s / duration, 2),
               "peak_rss_mb_this_proc": round(peak_mb, 1)}
    (WORK / "metrics_render.json").write_text(json.dumps(metrics, indent=2))
    print("RENDER ok:", json.dumps(metrics))

if __name__ == "__main__":
    sys.exit(main())
