"""Atomized knowledge wiki (PRD §8.5) — minimal Phase 1: source + source-fact
nodes with provenance, plus a grep-able INDEX.md. Project-local under wiki/.
operator-take nodes + talk-time mirroring arrive in Phase 3."""
import re, json, hashlib
from datetime import date
from pathlib import Path

TYPES = {"source", "source-fact", "topic"}


def slugify(s, maxlen=48):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return (s[:maxlen]).strip("-") or "node"


def _wiki_dir(root):
    p = Path(root) / "wiki"
    p.mkdir(exist_ok=True)
    return p


def add_node(root, ntype, name, body, **frontmatter):
    if ntype not in TYPES:
        raise ValueError(f"unknown node type: {ntype}")
    wiki = _wiki_dir(root)
    sub = wiki / ntype
    sub.mkdir(exist_ok=True)
    slug = slugify(name)
    # disambiguate collisions deterministically by content hash
    h = hashlib.sha1((name + body).encode()).hexdigest()[:6]
    fname = f"{slug}-{h}.md"
    fm = {"name": slug, "type": ntype, "created": date.today().isoformat(), **frontmatter}
    lines = ["---"]
    for k, v in fm.items():
        lines.append(f"{k}: {json.dumps(v) if not isinstance(v, str) else v}")
    lines += ["---", "", body.strip(), ""]
    (sub / fname).write_text("\n".join(lines))
    rebuild_index(root)
    return str((sub / fname).relative_to(root))


def rebuild_index(root):
    wiki = _wiki_dir(root)
    rows = []
    for md in sorted(wiki.rglob("*.md")):
        if md.name == "INDEX.md":
            continue
        first = ""
        for line in md.read_text().splitlines():
            if line and not line.startswith("---") and ":" not in line[:12]:
                first = line.strip()
                break
        rows.append(f"- [{md.stem}]({md.relative_to(wiki)}) — {first[:90]}")
    (wiki / "INDEX.md").write_text("# Wiki index\n\n" + "\n".join(rows) + "\n")
    return len(rows)
