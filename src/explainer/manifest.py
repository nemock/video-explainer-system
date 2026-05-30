"""PACKAGE — write the versioned manifest.json (PRD §9). The deterministic parts
are filled here; Claude-authored summary / per-platform captions / sources are
merged from an optional meta.json the skill writes."""
import json
from . import __version__


def run(proj):
    meta = {}
    meta_path = proj.dir / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())

    mux = {}
    mux_path = proj.work / "metrics_mux.json"
    if mux_path.exists():
        mux = json.loads(mux_path.read_text())

    label = proj.aspect.replace(":", "x")
    video_rel = f"video/explainer_{label}.mp4"
    has_video = (proj.dir / video_rel).exists()

    manifest = {
        "schema_version": "0.1",
        "generator": {"tool": "explainer-system", "version": __version__},
        "title": proj.data.get("title", meta.get("title", "Explainer")),
        "summary": meta.get("summary", ""),
        "slug": proj.data.get("slug", proj.dir.name),
        "language": proj.data.get("language", "en"),
        "voice": proj.voice,
        "aspect": proj.aspect,
        "duration_s": mux.get("duration_s"),
        "deck": "deck/index.html",
        "video": {proj.aspect: video_rel} if has_video else {},
        "captions": {"srt": "captions/captions.srt", "vtt": "captions/captions.vtt"},
        "status": {
            "ready_for_post": bool(has_video),
            "per_aspect": {proj.aspect: "ok" if has_video else "missing"},
        },
        # this content is AI-scripted + AI-narrated (Kokoro): disclose by default.
        "ai_disclosure": {
            "ai_generated_audio": True,
            "ai_generated_visuals": True,
            "recommended_label": "creator-disclosed",
            "c2pa_embedded": False,  # C2PA embedding is a later phase
        },
        "per_platform": meta.get("per_platform", []),
        "sources": meta.get("sources", []),
    }
    proj.write_json(proj.dir / "manifest.json", manifest)
    return {"manifest": "manifest.json", "ready_for_post": manifest["status"]["ready_for_post"]}
