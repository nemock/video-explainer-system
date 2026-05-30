"""talk-time READ (PRD §18.5) — surface the operator's real takes so the script can be
written in their own voice, instead of generic AI prose.

This is a **read-only** locator over the talk-time library
(`/Volumes/Casima/claudeCode/make_money/talk_time/`): it parses INDEX.md, filters the
curated entries (anecdotes / positions / topics / quotes) by **brand tag** (+ optional
topic keywords), and prints the matching files with absolute paths so the script-writing
skill can Read the ones it wants. It never writes, never calls an LLM, and never
fabricates — selection + authoring stay with the operator/skill.

Library precedence for the path:
  1. --library <path>
  2. the brand's talk_time.library (brand.json)
  3. DEFAULT_LIBRARY
"""
import re
from pathlib import Path

DEFAULT_LIBRARY = Path("/Volumes/Casima/claudeCode/make_money/talk_time")

# Sections of INDEX.md we write *from*. Raw sessions / legend / structure are excluded:
# raw transcripts are inputs to /talk-time, not source material for a script.
READ_SECTIONS = {"Anecdotes", "Positions", "Topics", "Quotes"}

_ENTRY = re.compile(r"^- \[(?P<title>[^\]]+)\]\((?P<path>[^)]+)\)\s*[—-]\s*(?P<rest>.+)$")


def _parse_index(text):
    """Yield {section, title, path, tags, desc} for each content entry in INDEX.md."""
    section = None
    for line in text.splitlines():
        h = re.match(r"^###\s+(.+?)\s*$", line)
        if h:
            section = h.group(1).strip()
            continue
        if section not in READ_SECTIONS:
            continue
        m = _ENTRY.match(line.strip())
        if not m:
            continue
        rest = m.group("rest")
        # rest is "tag, tag, tag — description"; the tag list is the part before the
        # first em-dash. (Descriptions may themselves contain em-dashes, so split once.)
        if "—" in rest:
            tag_part, desc = rest.split("—", 1)
        else:
            tag_part, desc = rest, ""
        tags = [t.strip().lower() for t in tag_part.split(",") if t.strip()]
        yield {"section": section, "title": m.group("title").strip(),
               "path": m.group("path").strip(), "tags": tags, "desc": desc.strip()}


def find(library=None, tag=None, topics=None):
    """Return matching entries (list of dicts with an added absolute `abspath`)."""
    lib = Path(library) if library else DEFAULT_LIBRARY
    index = lib / "INDEX.md"
    if not index.exists():
        raise FileNotFoundError(f"talk-time INDEX.md not found at {index}")
    tag = tag.lower() if tag else None
    # Word-boundary patterns so short keywords ("ai", "vc") match whole tokens, not
    # substrings buried in unrelated words ("said", "service").
    pats = [re.compile(r"(?<![a-z0-9])" + re.escape(k.strip().lower()) + r"(?![a-z0-9])")
            for k in topics if k.strip()] if topics else []
    out = []
    for e in _parse_index(index.read_text()):
        if tag and tag not in e["tags"]:
            continue
        if pats:
            hay = f"{e['title']} {e['desc']} {' '.join(e['tags'])}".lower()
            if not any(p.search(hay) for p in pats):
                continue
        # quotes.md entries carry a #anchor; the file is the part before '#'.
        rel = e["path"].split("#", 1)[0]
        e["abspath"] = str((lib / rel).resolve())
        out.append(e)
    return out


def run(library=None, tag=None, topics=None):
    """CLI entry: print a candidate list grouped by section + the authoring rules."""
    lib = Path(library) if library else DEFAULT_LIBRARY
    hits = find(library=library, tag=tag, topics=topics)
    lines = [f"talk-time library: {lib}",
             f"filter: tag={tag or '(any)'}  topics={','.join(topics) if topics else '(any)'}",
             f"{len(hits)} candidate(s)\n"]
    for sec in ("Quotes", "Positions", "Anecdotes", "Topics"):
        group = [e for e in hits if e["section"] == sec]
        if not group:
            continue
        lines.append(f"## {sec}")
        for e in group:
            anchor = "#" + e["path"].split("#", 1)[1] if "#" in e["path"] else ""
            lines.append(f"  • {e['title']}  [{', '.join(e['tags'])}]")
            lines.append(f"    {e['abspath']}{anchor}")
            if e["desc"]:
                lines.append(f"    {e['desc']}")
        lines.append("")
    lines += [
        "RULES (talk-time READ — PRD §18.5):",
        "  • Quote VERBATIM from quotes.md (use the exact one-liners).",
        "  • ADAPT freely from positions/ and anecdotes/ (paraphrase into script prose).",
        "  • NEVER fabricate a take, story, or stat not present in the library.",
        "  • Read the candidate files above, then write the script grounded in them.",
    ]
    return "\n".join(lines)
