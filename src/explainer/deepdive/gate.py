"""Alignment-confidence gate (ARCHITECTURE §6 / PRD §6.4).

MMS_FA (the aligner in media/align.py) emits NO per-word confidence — it force-aligns every
script token to *some* span. So a take that diverged from the script (an ad-lib, a dropped
phrase, a long silence where the operator lost their place) shows up not as a low score but as
the *geometry* of the spans: collapsed near-zero-width spans where tokens were forced onto sound
that wasn't there, a large interior gap where audio went silent, or dead air at the edges.

This gate reads `work/alignment.json` + `work/segments.json` (both already produced by the
narrate+align stages) and derives three checks. A failing take surfaces the EXACT timestamps so
the review pause can show the operator where it went wrong; the manual fix is to edit the
segment's `script.json` to match what was actually said and re-align. `rendered` requires a pass
for operator voice (TTS narration always passes — the narration IS the script). Thresholds are
overridable per program via `program.json` -> `gate`."""
import json

DEFAULTS = {
    "min_aligned_ratio": 0.90,   # fraction of tokens with a real (non-collapsed) span
    "min_span_s": 0.02,          # a span narrower than this is "degenerate" (token forced onto nothing)
    "max_inter_word_gap_s": 2.0, # an interior silence longer than this is a dropped phrase / lost place
    "max_edge_silence_s": 1.5,   # leading/trailing dead air
}


def evaluate(proj, thresholds=None):
    """Return {passed, aligned_ratio, max_gap_s, lead_silence_s, trail_silence_s, degenerate, failures}.
    `failures` carries exact timestamps for the review pause."""
    t = {**DEFAULTS, **(thresholds or {})}
    words = json.loads((proj.work / "alignment.json").read_text())["words"]
    dur = json.loads((proj.work / "segments.json").read_text()).get("duration")
    if not words:
        return {"passed": False, "aligned_ratio": 0.0, "failures": [{"type": "no-words"}]}

    degenerate = [w for w in words if (w["end"] - w["start"]) < t["min_span_s"]]
    aligned_ratio = round(1 - len(degenerate) / len(words), 4)

    gaps = [(round(words[i]["end"], 3), round(words[i + 1]["start"] - words[i]["end"], 3),
             words[i + 1]["word"]) for i in range(len(words) - 1)]
    max_gap = max((g[1] for g in gaps), default=0.0)
    big_gaps = [{"at_s": at, "gap_s": g, "before_word": w} for at, g, w in gaps
                if g > t["max_inter_word_gap_s"]]

    lead = round(words[0]["start"], 3)
    trail = round((dur - words[-1]["end"]), 3) if dur is not None else 0.0

    failures = []
    if aligned_ratio < t["min_aligned_ratio"]:
        failures.append({"type": "low-aligned-ratio", "aligned_ratio": aligned_ratio,
                         "threshold": t["min_aligned_ratio"],
                         "degenerate_at_s": [round(w["start"], 3) for w in degenerate[:20]]})
    failures += [{"type": "long-gap", **g} for g in big_gaps]
    if lead > t["max_edge_silence_s"]:
        failures.append({"type": "lead-silence", "seconds": lead})
    if trail > t["max_edge_silence_s"]:
        failures.append({"type": "trail-silence", "seconds": trail})

    return {"passed": not failures, "aligned_ratio": aligned_ratio, "max_gap_s": round(max_gap, 3),
            "lead_silence_s": lead, "trail_silence_s": trail,
            "degenerate": len(degenerate), "n_words": len(words), "failures": failures}
