"""HANDOFF — turn manifest.json into per-platform, blotato-ready post specs
(PRD §9 boundary: data mapping ONLY — this never posts). A poster (e.g. the
blotato-crosspost skill) reads handoff.json and does the upload + create_post."""
import json


def run(proj):
    m = json.loads((proj.dir / "manifest.json").read_text())
    videos = m.get("video", {})
    disclosure = m.get("ai_disclosure", {})

    posts = []
    for pp in m.get("per_platform", []):
        aspect = pp.get("aspect") or proj.aspect
        media_rel = videos.get(aspect) or (next(iter(videos.values())) if videos else None)
        media_abs = str((proj.dir / media_rel).resolve()) if media_rel else None
        tags = pp.get("hashtags", [])
        link = pp.get("link_placement", "none")
        # compose body: caption + hashtags inline unless the platform prefers a first comment
        text = pp.get("caption", "")
        if tags and link != "first_comment":
            text = text + "\n\n" + " ".join(tags)
        posts.append({
            "platform": pp.get("platform"),
            "title": pp.get("title"),                      # youtube needs a title; others ignore
            "text": text,
            "hashtags": tags,
            "first_comment": pp.get("first_comment"),
            "link_placement": link,
            "media_file": media_abs,                       # absolute local path for upload
            "aspect": aspect,
            "ai_label": disclosure.get("recommended_label"),  # poster should set the platform AI toggle
        })

    handoff = {
        "slug": m.get("slug"),
        "title": m.get("title"),
        "ready_for_post": m.get("status", {}).get("ready_for_post"),
        "ai_disclosure": disclosure,
        "posts": posts,
        "consumer": "blotato-crosspost (or any poster): upload media_file -> create_post per entry",
    }
    proj.write_json(proj.dir / "handoff.json", handoff)
    return {"posts": len(posts), "platforms": [p["platform"] for p in posts],
            "ready_for_post": handoff["ready_for_post"], "handoff": "handoff.json"}
