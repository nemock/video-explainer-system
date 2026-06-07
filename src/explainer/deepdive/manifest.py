"""Crash-safe program-manifest (Phase 2.1 — hardened).

Intent/state only — never authoritative timing (derived fresh via ffprobe at assembly).
- Atomic writes (.tmp + fsync + os.replace) with a .bak of the prior good version.
- Append-only transition journal under .history/ (recoverable audit trail).
- State-machine edge validation (illegal transitions refused unless force=True).
- Single-writer: only the orchestrator writes the manifest; parallel renders report via
  per-segment status files (segstatus.py), folded in here.
- Heartbeat + owner-PID claim so a crashed working segment is detectable (dead PID -> failed).
- Reconcile-against-disk on resume: promote planned segments whose MP4 now exists, demote any
  >=rendered claim the disk can't support, fail stale claims. (ARCHITECTURE §5.)
"""
import json
import os
import shutil
import time
from pathlib import Path

SCHEMA_VERSION = "2.0"

# lifecycle order (for >= comparisons); interstitials use the parallel planned -> ready track.
STATUSES = ["planned", "scripted", "recorded", "rendered", "ready", "approved", "rejected",
            "assembled", "reviewed-film", "publishable", "published", "failed"]
RANK = {s: i for i, s in enumerate(["planned", "scripted", "recorded", "rendered", "approved",
                                    "assembled", "reviewed-film", "publishable", "published"])}

# legal transitions. Generous enough for the no-review spine (rendered -> assembled) while
# refusing nonsense (e.g. published -> planned). The strict "assembly gates on approved" rule
# is enforced by the orchestrator in 2.2 when the review gate exists.
LEGAL = {
    "planned": {"scripted", "recorded", "rendered", "ready", "failed"},
    "scripted": {"recorded", "rendered", "failed"},
    "recorded": {"rendered", "failed"},
    "rendered": {"approved", "rejected", "assembled", "failed"},
    "ready": {"assembled", "failed"},
    "approved": {"assembled", "rejected", "failed"},
    "rejected": {"planned", "scripted", "recorded", "rendered"},
    "assembled": {"reviewed-film", "rendered", "failed"},
    "reviewed-film": {"publishable", "assembled"},
    "publishable": {"published", "assembled"},
    "published": set(),
    "failed": {"planned", "scripted", "recorded", "rendered"},
}


def new_manifest(program) -> dict:
    """Initial manifest: every segment in `order` starts `planned`."""
    segs = {}
    for sid in program.order:
        kind = program.segment(sid).get("kind", "act")
        segs[sid] = {"kind": kind, "status": "planned", "review_status": None,
                     "review_notes": "", "source_hash": None, "owner_pid": None, "heartbeat": None}
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
                         f"(migration not implemented)")
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


def _journal(program, entry):
    """Append one transition to the append-only .history journal (best-effort, never blocks)."""
    hd = program.dir / ".history"
    hd.mkdir(exist_ok=True)
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **entry}
    with open(hd / "transitions.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def _entry(manifest, seg_id, sub=None):
    seg = manifest["segments"][seg_id]
    if sub is not None:
        return seg.setdefault("subsegments", {}).setdefault(sub, {"status": "planned"})
    return seg


def transition(program, manifest, seg_id, to, *, sub=None, review_status=None, notes=None,
               source_hash=None, force=False, write_now=True) -> dict:
    """Move a segment (or sub-segment) to `to`, validating the edge against LEGAL unless force.
    Journals every transition. Returns the manifest. Raises ValueError on an illegal edge."""
    if to not in STATUSES:
        raise ValueError(f"unknown status '{to}'")
    e = _entry(manifest, seg_id, sub)
    frm = e.get("status", "planned")
    legal = to in LEGAL.get(frm, set()) or to == frm
    if not legal and not force:
        raise ValueError(f"illegal transition {seg_id}{'/' + sub if sub else ''}: {frm} -> {to}")
    e["status"] = to
    if review_status is not None:
        e["review_status"] = review_status
    if notes is not None:
        e["review_notes"] = notes
    if source_hash is not None:
        e["source_hash"] = source_hash
    _journal(program, {"segment": seg_id, "sub": sub, "from": frm, "to": to,
                       "forced": bool(not legal and force), "notes": notes})
    if write_now:
        write(program, manifest)
    return manifest


def set_status(program, manifest, seg_id, status, **kw):
    """Back-compat unchecked setter (routes through a forced transition so it's still journaled)."""
    return transition(program, manifest, seg_id, status, force=True, **kw)


# --- claim / heartbeat (crash detection) --------------------------------------------------
def _pid_alive(pid):
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError):
        return False


def claim(program, manifest, seg_id):
    """Mark this process as the owner of a segment's in-flight work (+ heartbeat timestamp)."""
    seg = manifest["segments"][seg_id]
    seg["owner_pid"] = os.getpid()
    seg["heartbeat"] = time.time()
    return write(program, manifest)


def release(program, manifest, seg_id):
    seg = manifest["segments"][seg_id]
    seg["owner_pid"] = None
    seg["heartbeat"] = None
    return write(program, manifest)


def _source_hash(mp4: Path):
    if not mp4 or not Path(mp4).exists():
        return None
    st = Path(mp4).stat()
    return f"{int(st.st_mtime)}:{st.st_size}"


def segment_mp4(program, seg_id, manifest):
    """The MP4 backing a segment: registry path for interstitials, engine output otherwise."""
    seg = manifest["segments"][seg_id]
    if seg.get("kind") == "interstitial":
        from . import interstitials
        return interstitials.resolve_path(program, seg.get("registry_ref"))
    return program.project_dir(seg_id) / "video" / "explainer_16x9.mp4"


def reconcile(program, manifest) -> dict:
    """Validate manifest against disk (resume safety). Bidirectional:
      - a `planned`/`scripted`/`recorded` segment whose MP4 exists is PROMOTED (rendered, or
        `ready` for interstitials) — work the manifest didn't record;
      - a `>= rendered` claim whose MP4 is missing is DEMOTED to `planned`;
      - a segment with a dead owner_pid mid-work is marked `failed` (crashed).
    Returns a drift report; writes the manifest iff anything changed."""
    drift, changed = [], False
    for sid, seg in manifest["segments"].items():
        mp4 = segment_mp4(program, sid, manifest)
        present = bool(mp4 and Path(mp4).exists())
        rank = RANK.get(seg["status"], 0)
        # crash detection: owner claimed but PID dead and not in a terminal/assembled state
        if seg.get("owner_pid") and not _pid_alive(seg["owner_pid"]) and seg["status"] not in (
                "assembled", "published", "publishable", "reviewed-film", "failed"):
            drift.append({"segment": sid, "issue": "stale-claim", "owner_pid": seg["owner_pid"]})
            seg["status"], seg["owner_pid"], seg["heartbeat"], changed = "failed", None, None, True
            _journal(program, {"segment": sid, "from": seg["status"], "to": "failed", "reason": "stale-claim"})
        elif rank >= RANK["rendered"] and not present:
            drift.append({"segment": sid, "issue": "missing-mp4", "claimed": seg["status"], "mp4": str(mp4)})
            seg["status"], seg["source_hash"], changed = "planned", None, True
            _journal(program, {"segment": sid, "from": drift[-1]["claimed"], "to": "planned", "reason": "missing-mp4"})
        elif rank < RANK["rendered"] and present:
            promote = "ready" if seg.get("kind") == "interstitial" else "rendered"
            drift.append({"segment": sid, "issue": "promote", "from": seg["status"], "to": promote})
            seg["status"], seg["source_hash"], changed = promote, _source_hash(Path(mp4)), True
            _journal(program, {"segment": sid, "from": drift[-1]["from"], "to": promote, "reason": "mp4-present"})
        elif present:
            h = _source_hash(Path(mp4))
            if seg.get("source_hash") != h:
                seg["source_hash"], changed = h, True
    if changed:
        write(program, manifest)
    return {"drift": drift, "ok": not drift}
