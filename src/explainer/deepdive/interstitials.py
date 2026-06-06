"""Interstitial registry — resolve + integrity-verify the pre-rendered sponsor/CTA MP4s that
slot into the film. The registry (deep-dive/brand/interstitials/interstitial-registry.json) is
operator content; entries carry a sha256 + ffprobe_format. `verify` re-checks both the hash and
the format-vs-CONTRACT before a segment is allowed into assembly (ARCHITECTURE §12.7)."""
import hashlib
import json
from pathlib import Path

from . import conform

# default registry location (operator content, gitignored). Overridable via program.json.
DEFAULT_REGISTRY = Path("deep-dive/brand/interstitials/interstitial-registry.json")


def _registry_path(program):
    rp = program.data.get("interstitial_registry")
    p = Path(rp) if rp else DEFAULT_REGISTRY
    if not p.is_absolute():
        # resolve relative to repo root (two levels above the program dir is deep-dive/programs/..)
        for base in (Path.cwd(), program.dir.parents[2] if len(program.dir.parents) >= 3 else Path.cwd()):
            if (base / p).exists():
                return base / p
    return p


def load_registry(program) -> dict:
    p = _registry_path(program)
    return json.loads(p.read_text()).get("interstitials", {}) if p.exists() else {}


def resolve_path(program, registry_ref):
    """Absolute MP4 path for a registry entry, or None."""
    reg = load_registry(program)
    entry = reg.get(registry_ref)
    if not entry:
        return None
    base = _registry_path(program).parent
    return (base / entry["file"]).resolve()


def _sha256(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify(program, registry_ref, *, fps=30) -> dict:
    """Re-verify a registered interstitial: file exists, sha256 matches the registry, and the
    MP4 conforms to CONTRACT. Returns {ok, sha_match, format_ok, diffs, path}."""
    reg = load_registry(program)
    entry = reg.get(registry_ref)
    if not entry:
        return {"ok": False, "issue": f"no registry entry '{registry_ref}'"}
    path = resolve_path(program, registry_ref)
    if not path or not path.exists():
        return {"ok": False, "issue": "file missing", "path": str(path)}
    sha_match = (entry.get("sha256") == _sha256(path)) if entry.get("sha256") else None
    chk = conform.check(path, fps=fps)
    return {"ok": bool((sha_match in (True, None)) and chk["ok"]),
            "sha_match": sha_match, "format_ok": chk["ok"], "diffs": chk["diffs"],
            "path": str(path), "placeholder": "PLACEHOLDER" in str(entry.get("kind", ""))}
