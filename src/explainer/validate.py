"""VALIDATE — check that an output dir's manifest is a complete, consumable handoff
contract (PRD §9) before a downstream poster touches it. Read-only."""
import json


def run(proj):
    issues = []
    mp = proj.dir / "manifest.json"
    if not mp.exists():
        return {"ok": False, "issues": ["manifest.json missing — run `explainer media` first"]}
    m = json.loads(mp.read_text())

    if not m.get("schema_version"):
        issues.append("missing schema_version")
    if not m.get("ai_disclosure"):
        issues.append("missing ai_disclosure block")
    if not (proj.dir / "deck" / "index.html").exists():
        issues.append("deck/index.html missing")

    vids = m.get("video", {})
    if not vids:
        issues.append("no video outputs in manifest")
    for asp, rel in vids.items():
        if not (proj.dir / rel).exists():
            issues.append(f"video file missing on disk: {rel}")
    for kind in ("srt", "vtt"):
        rel = m.get("captions", {}).get(kind)
        if rel and not (proj.dir / rel).exists():
            issues.append(f"caption file missing: {rel}")

    for pp in m.get("per_platform", []):
        plat = pp.get("platform", "?")
        asp = pp.get("aspect")
        if asp and asp not in vids:
            issues.append(f"per_platform '{plat}' wants aspect {asp} which was not rendered")
        if not pp.get("caption"):
            issues.append(f"per_platform '{plat}' has no caption")

    status = m.get("status", {})
    if status.get("ready_for_post") and issues:
        issues.append("ready_for_post=true but the above issues exist — inconsistent")

    ok = not issues
    proj.write_json(proj.work / "validate.json", {"ok": ok, "issues": issues})
    return {"ok": ok, "issues": issues}
