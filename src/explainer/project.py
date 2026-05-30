"""Project directory contract + path helpers (PRD §9 subset for Phase 1)."""
import json
from pathlib import Path
from dataclasses import dataclass

ASPECTS = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "4:5":  (1080, 1350),
    "1:1":  (1080, 1080),
}


@dataclass
class Project:
    dir: Path
    data: dict

    @classmethod
    def load(cls, project_dir) -> "Project":
        d = Path(project_dir).resolve()
        data = json.loads((d / "project.json").read_text())
        return cls(d, data)

    # inputs (Claude-authored)
    @property
    def project_json(self): return self.dir / "project.json"
    @property
    def script_json(self): return self.dir / "script.json"
    @property
    def deck_json(self): return self.dir / "deck.json"

    # work / outputs
    @property
    def work(self):
        p = self.dir / "work"; p.mkdir(exist_ok=True); return p
    @property
    def frames(self):
        p = self.work / "frames"; p.mkdir(parents=True, exist_ok=True); return p
    @property
    def deck_dir(self):
        p = self.dir / "deck"; p.mkdir(exist_ok=True); return p
    @property
    def captions_dir(self):
        p = self.dir / "captions"; p.mkdir(exist_ok=True); return p
    @property
    def video_dir(self):
        p = self.dir / "video"; p.mkdir(exist_ok=True); return p

    # config
    @property
    def aspect(self): return self.data.get("aspect", "9:16")
    @property
    def aspects(self):
        """All aspects to render (multi-aspect); defaults to the primary."""
        return self.data.get("aspects") or [self.aspect]
    @property
    def size(self):
        if "width" in self.data and "height" in self.data:
            return self.data["width"], self.data["height"]
        return ASPECTS[self.aspect]
    def size_for(self, aspect): return ASPECTS[aspect]
    def frames_dir(self, label):
        p = self.work / f"frames_{label}"; p.mkdir(parents=True, exist_ok=True); return p
    @property
    def safe_bottom(self): return float(self.data.get("safe_bottom", 0.14))
    @property
    def min_length(self): return self.data.get("min_length")
    @property
    def fps(self): return int(self.data.get("fps", 30))
    @property
    def voice(self): return self.data.get("voice", "af_heart")
    @property
    def theme(self):
        from . import themes
        return themes.resolve(self.data.get("theme"))

    def write_json(self, rel_or_path, obj):
        p = rel_or_path if isinstance(rel_or_path, Path) else self.dir / rel_or_path
        p.write_text(json.dumps(obj, indent=2))
        return p
