"""Crash-safe program-manifest (minimal 2.0 slice).

Intent/state only — never authoritative timing (that's derived fresh via ffprobe at assembly).
Atomic writes (.tmp + fsync + os.replace) with a .bak of the prior good version; read-only
`reconcile` demotes any segment whose claimed status the files on disk don't support. The full
`.history` journal + state-machine edge validation + single-writer fold-in land in Phase 2.1
(ARCHITECTURE §5)."""
import json
import os
import shutil
import time
from pathlib import Path

SCHEMA_VERSION = "2.0"

# lifecycle (full machine enforced in 2.1); 2.0 uses: planned -> rendered -> approved, + assembled.
STATUSES = ["planned", "scripted", "recorded", "rendered", "approved", "rejected",
            "assembled", "reviewed-film", "publishable", "published", "failed"]


def new_manifest(program) -> dict:
    """Initial manifest: every segment in `order` starts `planned`."""
    segs = {}
    for sid in program.order:
        kind = program.segment(sid).get("kind", "act")
        segs[sid] = {"kind": kind, "status": "planned", "review_status": None,
                     "review_notes": "", "source_hash": None}
        if kind == "interstitial":
            segs[sid]["registry_ref"] = program.segment(sid).get("registry_ref")
    return {"schema_version": SCHEMA_VERSION,
            "generator": {"tool": "deepdive"},
            "program": {"slug": program.slug, "title": program.title, "fps": program.fps},
            "order": list(program.order),
            "segments": segs,
            "assembly": {"status": "planned", "master": None, "validated": False, "report": None}}


def load(program) -> dict:
    p = program.manifest_path
    if not p.exists():
        return new_manifest(program)
    m = json.loads(p.read_text())
    if m.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"manifest schema_version {m.get('schema_version')} != {SCHEMA_VERSION} "
                         f"(migration not implemented in 2.0)")
    return m


def write(program, manifest) -> Path:
    """Atomic: write .tmp, fsync, copy prior good -> .bak, os.replace. Never partially-written."""
    path = program.manifest_path
    tmp = path.with_name(path.name + ".tmp")
    manifest["_written_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    data = json.dumps(manifest, indent=2)
    with open(tmp, "w") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    if path.exists():
        shutil.copy2(path, path.with_name(path.name + ".bak"))
    os.replace(tmp, path)
    return path


def _source_hash(mp4: Path):
    """Cheap content fingerprint (mtime+size) — full sha is interstitials.verify's job."""
    if not mp4.exists():
        return None
    st = mp4.stat()
    return f"{int(st.st_mtime)}:{st.st_size}"


def set_status(program, manifest, seg_id, status, *, review_status=None, notes=None, source_hash=None):
    seg = manifest["segments"][seg_id]
    seg["status"] = status
    if review_status is not None:
        seg["review_status"] = review_status
    if notes is not None:
        seg["review_notes"] = notes
    if source_hash is not None:
        seg["source_hash"] = source_hash
    return write(program, manifest)


def segment_mp4(program, seg_id, manifest):
    """The MP4 that backs a segment: registry path for interstitials, engine output otherwise."""
    seg = manifest["segments"][seg_id]
    if seg.get("kind") == "interstitial":
        from . import interstitials
        return interstitials.resolve_path(program, seg.get("registry_ref"))
    return program.project_dir(seg_id) / "video" / "explainer_16x9.mp4"


def reconcile(program, manifest) -> dict:
    """Validate manifest against disk: any segment claiming >= rendered whose MP4 is missing is
    demoted to planned. Returns a drift report. Read-only w.r.t. media; writes the manifest if
    anything changed."""
    order_idx = {s: i for i, s in enumerate(STATUSES)}
    drift, changed = [], False
    for sid, seg in manifest["segments"].items():
        if order_idx.get(seg["status"], 0) >= order_idx["rendered"]:
            mp4 = segment_mp4(program, sid, manifest)
            if not mp4 or not Path(mp4).exists():
                drift.append({"segment": sid, "claimed": seg["status"], "mp4": str(mp4), "issue": "missing"})
                seg["status"], seg["source_hash"], changed = "planned", None, True
            else:
                seg["source_hash"] = _source_hash(Path(mp4))
                changed = True
    if changed:
        write(program, manifest)
    return {"drift": drift, "ok": not drift}
