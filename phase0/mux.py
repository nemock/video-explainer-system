#!/usr/bin/env python3
"""Phase 0 — MUX stage.
ffmpeg (VideoToolbox hardware encode): frames + normalized narration -> MP4,
with bt709 color tags and faststart. Emits video/explainer_9x16.mp4.

Run: myenv/bin/python3 phase0/mux.py
"""
import json, time, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
OUT = HERE / "video"

def main():
    script = json.loads((HERE / "script.json").read_text())
    fps = json.loads((WORK / "metrics_render.json").read_text())["fps"]
    OUT.mkdir(exist_ok=True)
    out = OUT / "explainer_9x16.mp4"

    cmd = [
        "ffmpeg", "-hide_banner", "-y",
        "-framerate", str(fps), "-i", str(WORK / "frames" / "f%05d.png"),
        "-i", str(WORK / "narration.wav"),
        "-c:v", "h264_videotoolbox", "-b:v", "8M",
        "-pix_fmt", "yuv420p",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-color_range", "tv",
        "-c:a", "aac_at", "-b:a", "192k",
        "-movflags", "+faststart", "-shortest",
        str(out),
    ]
    t0 = time.time()
    subprocess.run(cmd, check=True, capture_output=True)
    mux_s = time.time() - t0

    probe = subprocess.run(
        ["ffprobe", "-hide_banner", "-v", "error", "-show_entries",
         "format=duration,size:stream=codec_name,width,height", "-of", "json", str(out)],
        capture_output=True, text=True)
    info = json.loads(probe.stdout) if probe.stdout else {}
    dur = float(info.get("format", {}).get("duration", 0))
    size_mb = int(info.get("format", {}).get("size", 0)) / (1024 * 1024)

    metrics = {"mux_s": round(mux_s, 2), "out_mp4": str(out.relative_to(HERE)),
               "duration_s": round(dur, 2), "size_mb": round(size_mb, 2)}
    (WORK / "metrics_mux.json").write_text(json.dumps(metrics, indent=2))
    print("MUX ok:", json.dumps(metrics))

if __name__ == "__main__":
    sys.exit(main())
