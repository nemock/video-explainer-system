"""PACKAGE — write the versioned manifest.json (PRD §9). Deterministic parts are
filled here; Claude-authored summary / per-platform captions / sources are merged
from an optional meta.json the skill writes. Handles multi-aspect + min-length."""
import json
from . import __version__


def run(proj):
    meta = {}
    if (proj.dir / "meta.json").exists():
        meta = json.loads((proj.dir / "meta.json").read_text())
    mux = {}
    if (proj.work / "metrics_mux.json").exists():
        mux = json.loads((proj.work / "metrics_mux.json").read_text()).get("aspects", {})

    video, per_aspect, duration = {}, {}, None
    for aspect in proj.aspects:
        label = aspect.replace(":", "x")
        rel = f"video/explainer_{label}.mp4"
        if (proj.dir / rel).exists():
            video[aspect] = rel
            per_aspect[aspect] = "ok"
            duration = mux.get(aspect, {}).get("duration_s", duration)
        else:
            per_aspect[aspect] = "missing"

    ready = bool(video) and all(v == "ok" for v in per_aspect.values())
    length_warning = None
    if proj.min_length and duration and duration < proj.min_length:
        length_warning = f"duration {duration}s is under min_length {proj.min_length}s — deepen the script"
        ready = False

    manifest = {
        "schema_version": "0.1",
        "generator": {"tool": "explainer-system", "version": __version__},
        "title": proj.data.get("title", meta.get("title", "Explainer")),
        "summary": meta.get("summary", ""),
        "slug": proj.data.get("slug", proj.dir.name),
        "language": proj.data.get("language", "en"),
        "voice": proj.voice,
        "aspects": proj.aspects,
        "duration_s": duration,
        "deck": "deck/index.html",
        "video": video,
        "captions": {"srt": "captions/captions.srt", "vtt": "captions/captions.vtt"},
        "status": {"ready_for_post": ready, "per_aspect": per_aspect, "length_warning": length_warning},
        "ai_disclosure": {
            "ai_generated_audio": True, "ai_generated_visuals": True,
            "recommended_label": "creator-disclosed", "c2pa_embedded": False,
        },
        "per_platform": meta.get("per_platform", []),
        "sources": meta.get("sources", []),
    }
    proj.write_json(proj.dir / "manifest.json", manifest)
    return {"manifest": "manifest.json", "ready_for_post": ready,
            "aspects": proj.aspects, "length_warning": length_warning}
