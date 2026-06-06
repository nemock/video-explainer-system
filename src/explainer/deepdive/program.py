"""Program — the directory + config contract for one deep-dive film (mirrors the engine's
`Project`). A program is an ordered list of segments; each non-interstitial segment is itself
an `explainer` project dir under segments/. Intent only — all timing is derived fresh via
ffprobe at assembly (ARCHITECTURE §4–§5)."""
import json
from dataclasses import dataclass
from pathlib import Path

from ..project import Project

# canonical full-film order (ARCHITECTURE §3); the demo program overrides `order` with a subset.
CANONICAL_ORDER = ["cold-open", "act-1", "fwf-sponsor", "act-2", "thebuild-sponsor", "act-3", "cta"]


@dataclass
class Program:
    dir: Path
    data: dict  # program.json

    @classmethod
    def load(cls, program_dir) -> "Program":
        d = Path(program_dir).resolve()
        return cls(d, json.loads((d / "program.json").read_text()))

    @property
    def slug(self): return self.data.get("slug", self.dir.name)
    @property
    def title(self): return self.data.get("title", self.slug)
    @property
    def fps(self): return int(self.data.get("fps", 30))
    @property
    def brand(self): return self.data.get("brand")
    @property
    def order(self): return self.data.get("order", CANONICAL_ORDER)
    @property
    def caption_style(self): return self.data.get("caption_style", "bottom-2line")

    @property
    def manifest_path(self): return self.dir / "program-manifest.json"
    @property
    def build_log(self): return self.dir / "build-log.jsonl"
    @property
    def segments_dir(self):
        p = self.dir / "segments"; p.mkdir(exist_ok=True); return p
    @property
    def master_dir(self):
        p = self.dir / "master"; p.mkdir(exist_ok=True); return p
    @property
    def scratch_dir(self):
        p = self.dir / "work"; p.mkdir(exist_ok=True); return p

    def segment(self, seg_id):
        """The manifest entry for a segment id (kind, status, and for interstitials registry_ref)."""
        return self.data.get("segments", {}).get(seg_id, {})

    def is_interstitial(self, seg_id):
        return self.segment(seg_id).get("kind") == "interstitial"

    def project_dir(self, seg_id) -> Path:
        """The explainer project dir backing a non-interstitial segment (segments/<id>/)."""
        return self.segments_dir / seg_id

    def as_project(self, seg_id) -> Project:
        return Project.load(self.project_dir(seg_id))
