"""Master-format CONTRACT + ffprobe preflight + per-segment streaming conform.

The single source of truth for what every segment MUST look like before it can be
concat-demuxer'd into the master (ARCHITECTURE §12.1–12.2). Independently rendered segments
(non-deterministic HW encoder) and stereo interstitials vs mono VO are reconciled HERE — the
engine is never touched. `CONTRACT` is consumed by this module, `assemble.validate_master`,
and `interstitials.verify`."""
import json
import subprocess
from pathlib import Path

# fps is per-program (default 30); everything else is fixed. h264 High@L4.0 / yuv420p /
# 1920x1080 / SAR 1:1 / CFR / bt709 tv / AAC-LC 48k STEREO / faststart.
CONTRACT = {
    "video": {"codec_name": "h264", "profile": "High", "level": 40,
              "width": 1920, "height": 1080, "pix_fmt": "yuv420p",
              "sample_aspect_ratio": "1:1"},          # r_frame_rate checked against program fps
    "audio": {"codec_name": "aac", "channels": 2, "sample_rate": "48000"},
}
# color is set on conform but not gated (tagging, not a concat blocker); kept consistent.
COLOR = {"colorspace": "bt709", "color_primaries": "bt709", "color_trc": "bt709", "color_range": "tv"}


def probe(mp4):
    """Return {video:{...}, audio:{...}, format:{duration}} for an MP4 via ffprobe (JSON)."""
    out = {"video": {}, "audio": {}, "format": {}}
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=index,codec_type,codec_name,profile,level,width,height,"
         "pix_fmt,sample_aspect_ratio,r_frame_rate,avg_frame_rate,channels,sample_rate",
         "-of", "json", str(mp4)], capture_output=True, text=True)
    data = json.loads(r.stdout or "{}")
    out["format"]["duration"] = float(data.get("format", {}).get("duration", 0.0))
    for s in data.get("streams", []):
        if s.get("codec_type") == "video" and not out["video"]:
            out["video"] = s
        elif s.get("codec_type") == "audio" and not out["audio"]:
            out["audio"] = s
    return out


def check(mp4, fps=30):
    """Compare an MP4 against CONTRACT. Returns {ok, video_ok, audio_ok, diffs:[(field, got, want)]}.
    video_ok/audio_ok drive whether conform_segment re-encodes the video, the audio, or both."""
    p = probe(mp4)
    v, a = p["video"], p["audio"]
    vdiffs, adiffs = [], []
    for k, want in CONTRACT["video"].items():
        got = v.get(k)
        if k == "level":
            try:
                if int(got) != want:
                    vdiffs.append((k, got, want))
            except (TypeError, ValueError):
                vdiffs.append((k, got, want))
        elif k == "sample_aspect_ratio":
            # absent / "0:1" / "" all mean square pixels == 1:1 (encoders omit SAR when 1:1).
            if got not in (None, "", "1:1", "0:1"):
                vdiffs.append((k, got, want))
        elif str(got) != str(want):
            vdiffs.append((k, got, want))
    want_fps = f"{fps}/1"
    if str(v.get("r_frame_rate")) != want_fps:
        vdiffs.append(("r_frame_rate", v.get("r_frame_rate"), want_fps))
    for k, want in CONTRACT["audio"].items():
        if str(a.get(k)) != str(want):
            adiffs.append((k, a.get(k), want))
    return {"ok": not vdiffs and not adiffs, "video_ok": not vdiffs, "audio_ok": not adiffs,
            "diffs": [("video", *d) for d in vdiffs] + [("audio", *d) for d in adiffs],
            "duration": p["format"]["duration"]}


def _loudnorm_af(src, I=-14.0, TP=-1.0, LRA=11.0):
    """Two-pass loudnorm audio filter for `src`: measure (pass 1) then return the linear-correction
    `loudnorm=...` filter string (pass 2 runs inside the conform encode). So every conformed segment
    lands at exactly I LUFS / TP dBTP and the master's seams are level-matched by construction."""
    from . import audio
    m = audio.measure_loudness(src)
    return (f"loudnorm=I={I}:TP={TP}:LRA={LRA}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
            f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
            f"offset={m['target_offset']}:linear=true")


def conform_segment(src, dst, fps=30, loudnorm=True):
    """Re-encode `src` to a CONTRACT-exact `dst`. Video re-encoded with libx264 (deterministic,
    unlike the HW encoder) only when the video stream is off-contract; otherwise the video is
    stream-copied and only the audio is fixed (the common case: mono VO -> stereo). Audio always
    lands AAC 48k stereo, two-pass-loudnorm'd to -14 LUFS / -1 dBTP when `loudnorm`. RAM-trivial."""
    c = check(src, fps=fps)
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src)]
    if c["video_ok"]:
        cmd += ["-c:v", "copy"]
        action = "audio-only"
    else:
        cmd += ["-c:v", "libx264", "-profile:v", "high", "-level", "4.0", "-pix_fmt", "yuv420p",
                "-vf", (f"scale=1920:1080:force_original_aspect_ratio=decrease,"
                        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}"),
                "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                "-color_range", "tv", "-x264-params", "keyint=120:scenecut=0"]
        action = "full"
    if loudnorm:
        cmd += ["-af", _loudnorm_af(src)]
    cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"conform_segment failed for {src}:\n{r.stderr[-1500:]}")
    return {"src": str(src), "dst": str(dst), "action": action,
            "was_conformant": c["ok"], "diffs": c["diffs"]}
