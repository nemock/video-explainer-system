"""QA — motion/pacing check (PRD §8.2). Operates on the rendered video + timeline,
not just stills. Uses ffmpeg `freezedetect` to find held frames, intersects them
with the word timeline to flag visual dead air *during speech*, and analyzes shot
pacing (over-long shots, uniform cut rhythm). Non-fatal: reports warnings."""
import json, re, subprocess, statistics


def _freeze_spans(video_path, min_seconds=0.6, noise_db=-60):
    """Return [(start, end)] of frozen (static) video segments via ffmpeg."""
    cmd = ["ffmpeg", "-hide_banner", "-i", str(video_path),
           "-vf", f"freezedetect=n={noise_db}dB:d={min_seconds}",
           "-map", "0:v", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    spans, start = [], None
    for line in err.splitlines():
        m = re.search(r"freeze_start: ([\d.]+)", line)
        if m:
            start = float(m.group(1))
        m = re.search(r"freeze_end: ([\d.]+)", line)
        if m and start is not None:
            spans.append((start, float(m.group(1))))
            start = None
    return spans


def run(proj):
    timeline = json.loads((proj.work / "timeline.json").read_text())
    words = timeline.get("words", [])
    slides = timeline.get("slides", [])
    label = proj.aspect.replace(":", "x")
    video = proj.video_dir / f"explainer_{label}.mp4"

    warnings = []
    dead_air = []
    if video.exists():
        for (a, b) in _freeze_spans(video):
            speaking = any(w["start"] < b and w["end"] > a for w in words)  # narration overlaps freeze
            if speaking and (b - a) >= 0.6:
                dead_air.append({"start": round(a, 2), "end": round(b, 2), "seconds": round(b - a, 2)})
        if dead_air:
            total = round(sum(d["seconds"] for d in dead_air), 2)
            warnings.append(f"visual dead air during speech: {total}s across {len(dead_air)} span(s) "
                            f"(worst {max(d['seconds'] for d in dead_air)}s) — add motion or split the shot")
    else:
        warnings.append("no rendered video found — run render+mux before qa")

    # pacing: shot lengths
    durs = [round(s["end"] - s["start"], 2) for s in slides]
    longest = max(durs) if durs else 0
    if longest > 8.0:
        warnings.append(f"longest shot {longest}s (>8s) — consider splitting for retention")
    cv = (statistics.pstdev(durs) / statistics.mean(durs)) if len(durs) > 2 and statistics.mean(durs) else 1
    if len(durs) > 3 and cv < 0.15:
        warnings.append(f"uniform cut rhythm (cv={cv:.2f}) — vary shot lengths for energy")

    report = {"shots": len(slides), "shot_seconds": durs, "longest_shot_s": longest,
              "pacing_cv": round(cv, 3), "dead_air_during_speech": dead_air, "warnings": warnings}
    proj.write_json(proj.work / "qa.json", report)
    return {"warnings": warnings, "dead_air_spans": len(dead_air),
            "longest_shot_s": longest, "pacing_cv": round(cv, 3)}
