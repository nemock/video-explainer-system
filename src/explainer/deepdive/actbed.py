"""Act-bed ducking (ARCHITECTURE §11). An optional music underscore mixed UNDER the act
narration with sidechain ducking (~ −22 dB during speech, rising in the gaps) so the bed adds
energy without fighting the VO. Per-program, opt-in via `program.json` -> `music.act_bed`
("A" | "B" | a path | null). Interstitials carry their own sponsor bed and are NOT touched here.
Tracks must be registered in deep-dive/shared/music/LICENSES.md."""
import subprocess
from pathlib import Path

from . import audio, conform

# the two registered act beds (LICENSES.md). "A" = downtempo/chill, "B" = corporate.
ACT_BEDS = {
    "A": "deep-dive/shared/music/act-bed/alex-morgan-downtempo-chill-electronic-528322.mp3",
    "B": "deep-dive/shared/music/act-bed/alex-morgan-corporate-530945.mp3",
}


def resolve(program):
    """The act-bed track path for this program, or None. `music.act_bed` may be 'A'/'B', an
    explicit path, or absent. Returns an absolute Path resolved against the repo root."""
    sel = (program.data.get("music") or {}).get("act_bed")
    if not sel:
        return None
    rel = ACT_BEDS.get(sel, sel)
    p = Path(rel)
    if not p.is_absolute():
        for base in (Path.cwd(), program.dir.parents[2] if len(program.dir.parents) >= 3 else Path.cwd()):
            if (base / p).exists():
                return (base / p).resolve()
    return p if p.exists() else None


def mix_under(bed, src_mp4, dst_mp4, *, bed_floor_db=-22.0):
    """Duck `bed` under the narration of `src_mp4` and remux with the original video. The bed is
    looped to cover the segment; ducking + final loudnorm happen downstream in conform. Returns
    a report. RAM-trivial (streaming)."""
    dur = conform.probe(src_mp4)["format"]["duration"]
    work = Path(dst_mp4).parent
    work.mkdir(parents=True, exist_ok=True)
    bed_loop = work / (Path(dst_mp4).stem + "_bedloop.wav")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-stream_loop", "-1",
                    "-i", str(bed), "-t", f"{dur + 0.4:.2f}", str(bed_loop)], check=True)
    ducked = work / (Path(dst_mp4).stem + "_ducked.wav")
    audio.duck_under_vo(src_mp4, bed_loop, ducked, bed_floor_db=bed_floor_db)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src_mp4),
                        "-i", str(ducked), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-shortest", str(dst_mp4)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"act-bed remux failed for {src_mp4}:\n{r.stderr[-1200:]}")
    return {"src": str(src_mp4), "dst": str(dst_mp4), "bed": str(bed), "bed_floor_db": bed_floor_db}
