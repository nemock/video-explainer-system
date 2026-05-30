"""MUX — ffmpeg VideoToolbox hardware encode: frames + normalized narration -> MP4
with bt709 color tags and faststart."""
import json, time, subprocess


def run(proj):
    fps = proj.fps
    label = proj.aspect.replace(":", "x")
    out = proj.video_dir / f"explainer_{label}.mp4"
    cmd = ["ffmpeg", "-hide_banner", "-y",
           "-framerate", str(fps), "-i", str(proj.frames / "f%05d.png"),
           "-i", str(proj.work / "narration.wav"),
           "-c:v", "h264_videotoolbox", "-b:v", "8M", "-pix_fmt", "yuv420p",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
           "-color_range", "tv", "-c:a", "aac_at", "-b:a", "192k",
           "-movflags", "+faststart", "-shortest", str(out)]
    t0 = time.time()
    subprocess.run(cmd, check=True, capture_output=True)
    mux_s = time.time() - t0

    probe = subprocess.run(
        ["ffprobe", "-hide_banner", "-v", "error", "-show_entries",
         "format=duration,size", "-of", "json", str(out)],
        capture_output=True, text=True)
    info = json.loads(probe.stdout) if probe.stdout else {}
    dur = float(info.get("format", {}).get("duration", 0))
    size_mb = int(info.get("format", {}).get("size", 0)) / (1024 * 1024)
    metrics = {"mux_s": round(mux_s, 2), "out_mp4": str(out.relative_to(proj.dir)),
               "duration_s": round(dur, 2), "size_mb": round(size_mb, 2)}
    proj.write_json(proj.work / "metrics_mux.json", metrics)
    return metrics
