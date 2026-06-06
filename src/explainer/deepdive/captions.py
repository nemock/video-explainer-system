"""Caption stitch — concatenate each segment's SRT into one master sidecar, offsetting every
cue by the ffprobe-EXACT duration of the *conformed* segment (accumulated in ms, never rounded
manifest values). No-caption interstitials still advance the accumulator (ARCHITECTURE §12.4)."""
import re

from . import conform

_CUE = re.compile(
    r"(\d+)\s*\n(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})[^\n]*\n(.*?)(?=\n\s*\n|\Z)",
    re.DOTALL)


def parse_srt(text):
    """Return [(start_ms, end_ms, text), ...] from SRT (or VTT-ish) content."""
    cues = []
    for m in _CUE.finditer(text):
        sh, sm, ss, sms, eh, em, es, ems = (int(m.group(i)) for i in range(2, 10))
        start = ((sh * 60 + sm) * 60 + ss) * 1000 + sms
        end = ((eh * 60 + em) * 60 + es) * 1000 + ems
        cues.append((start, end, m.group(10).strip("\n")))
    return cues


def _ts(ms, sep):
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def stitch(conformed, srts, out_srt, out_vtt):
    """conformed: ordered conformed-segment MP4 paths. srts: parallel list of SRT paths or None.
    Writes the master SRT + VTT; returns {cues, last_end_s, total_offset_s}."""
    all_cues, offset_ms = [], 0
    for mp4, srt in zip(conformed, srts):
        if srt:
            for s, e, txt in parse_srt(open(srt).read()):
                all_cues.append((s + offset_ms, e + offset_ms, txt))
        offset_ms += int(round(conform.probe(mp4)["format"]["duration"] * 1000))

    srt_lines, vtt_lines = [], ["WEBVTT", ""]
    for i, (s, e, txt) in enumerate(all_cues, 1):
        srt_lines += [str(i), f"{_ts(s, ',')} --> {_ts(e, ',')}", txt, ""]
        vtt_lines += [f"{_ts(s, '.')} --> {_ts(e, '.')}", txt, ""]
    open(out_srt, "w").write("\n".join(srt_lines))
    open(out_vtt, "w").write("\n".join(vtt_lines))
    return {"cues": len(all_cues),
            "last_end_s": round(all_cues[-1][1] / 1000, 3) if all_cues else 0.0,
            "total_offset_s": round(offset_ms / 1000, 3)}
