"""Chapters — YouTube `chapters.txt` from segment boundaries, timed by the ffprobe-exact
duration of each conformed segment. Titles are forward-hooks supplied by the caller (the
editorial layer in 2.3), not bare "Act II" (ARCHITECTURE §12.5)."""
from . import conform


def _ts(seconds):
    s = int(round(seconds))
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def build(conformed, titles, out_txt):
    """conformed: ordered conformed-segment MP4 paths. titles: parallel chapter titles.
    Consecutive segments sharing the same title collapse into ONE chapter (so an act split into
    several ~60–90s sub-segments yields one act-level YouTube chapter, not one per sub-segment —
    set the same `chapter` on those segments). Writes chapters.txt (first is 0:00); returns
    [{start_s, title}]."""
    chapters, offset, last = [], 0.0, object()
    for mp4, title in zip(conformed, titles):
        if title != last:                       # emit a chapter only when the title changes
            chapters.append({"start_s": round(offset, 3), "title": title, "ts": _ts(offset)})
            last = title
        offset += conform.probe(mp4)["format"]["duration"]
    open(out_txt, "w").write("\n".join(f"{c['ts']} {c['title']}" for c in chapters) + "\n")
    return chapters
