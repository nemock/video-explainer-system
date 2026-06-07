#!/usr/bin/env python3
"""Deep-Dive audio assembly recipes (Phase 1.5) — pure ffmpeg/ffprobe, zero Claude calls.

The four assembly-layer audio operations the deep-dive needs, as tested, parameterized
functions the Phase-2 assembler imports (no whole-film filtergraph; per-segment, RAM-safe):

  1. duck_under_vo()      — sidechain-duck an act bed (or sponsor bed) UNDER a voiceover,
                            target ~ -22 dB during speech; bed rises in the gaps.
  2. two_pass_loudnorm()  — measure (pass 1) then correct (pass 2) to -14 LUFS / <= -1 dBTP.
  3. measure_loudness()   — integrated LUFS / true-peak / LRA for any clip (ffmpeg loudnorm json).
  4. seam_lufs_check()    — assert consecutive segments are level-matched (|dLUFS| <= 1.0).

CLI:  python3 audio_recipes.py duck   --vo vo.wav --bed bed.mp3 --out mix.wav [--duck-db 22]
      python3 audio_recipes.py norm   --in mix.wav --out final.wav [--i -14 --tp -1]
      python3 audio_recipes.py measure --in clip.wav
      python3 audio_recipes.py seam   seg1.wav seg2.wav seg3.wav [--max-delta 1.0]
      python3 audio_recipes.py demo   --vo vo.wav --bed bed.mp3 --outdir /tmp/auddemo
"""
import argparse, json, subprocess, sys
from pathlib import Path

SR = 48000  # assembly works at 48k stereo (master-format contract; -ac 2)


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def measure_loudness(path):
    """Integrated loudness of `path` via ffmpeg loudnorm's analysis (pass 1).
    Returns {input_i, input_tp, input_lra, input_thresh} in LUFS/dBTP/LU."""
    r = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
              "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json",
              "-f", "null", "-"])
    txt = r.stderr
    start = txt.rfind("{")
    data = json.loads(txt[start:txt.rfind("}") + 1])
    return {k: float(data[k]) for k in ("input_i", "input_tp", "input_lra", "input_thresh")} | {
        "target_offset": float(data.get("target_offset", 0.0))}


def duck_under_vo(vo, bed, out, duck_db=22.0, bed_floor_db=-20.0,
                  attack=20.0, release=320.0, threshold=0.035, ratio=14.0):
    """Mix `bed` under `vo` with sidechain ducking. The bed sits at ~`bed_floor_db` in the
    gaps and ducks ~`duck_db` below the VO while speech plays (the VO keys the compressor).
    Used for BOTH the act bed under the act VO and the sponsor bed under an interstitial read.

    Inputs are conformed to 48k stereo; output is 48k stereo. `bed_floor_db` is the static
    pre-attenuation that sets the gaps level; the sidechain adds the dynamic duck on top.
    `duck_db` documents the intended speech-time separation (verify with measure_loudness)."""
    # makeup stays at 1 (no gain) so the duck only attenuates; release long enough to avoid pumping.
    fc = (
        f"[1:a]aresample={SR},aformat=channel_layouts=stereo,asplit=2[vo][key];"
        f"[0:a]aresample={SR},aformat=channel_layouts=stereo,volume={bed_floor_db}dB[bedlvl];"
        f"[bedlvl][key]sidechaincompress=threshold={threshold}:ratio={ratio}:"
        f"attack={attack}:release={release}:makeup=1:level_sc=1[duck];"
        f"[vo][duck]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[mix]"
    )
    r = _run(["ffmpeg", "-hide_banner", "-y", "-i", str(bed), "-i", str(vo),
              "-filter_complex", fc, "-map", "[mix]", "-ar", str(SR), "-ac", "2", str(out)])
    if r.returncode != 0:
        raise RuntimeError("duck_under_vo failed:\n" + r.stderr[-1500:])
    return {"out": str(out), "duck_db_target": duck_db, "bed_floor_db": bed_floor_db}


def two_pass_loudnorm(src, out, I=-14.0, TP=-1.0, LRA=11.0):
    """Two-pass EBU R128 normalize to `I` LUFS / `TP` dBTP. Pass 1 measures, pass 2 applies
    the linear correction (linear=true keeps it transparent when the source is already close).
    This is the FINAL loudness gate for a deep-dive's assembled audio (-14 LUFS / <= -1 dBTP)."""
    r = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src),
              "-af", f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json", "-f", "null", "-"])
    j = r.stderr
    m = json.loads(j[j.rfind("{"):j.rfind("}") + 1])
    af = (f"loudnorm=I={I}:TP={TP}:LRA={LRA}:"
          f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
          f"offset={m['target_offset']}:linear=true:print_format=summary")
    r2 = _run(["ffmpeg", "-hide_banner", "-y", "-i", str(src), "-af", af,
               "-ar", str(SR), "-ac", "2", str(out)])
    if r2.returncode != 0:
        raise RuntimeError("two_pass_loudnorm pass2 failed:\n" + r2.stderr[-1500:])
    return {"out": str(out), "measured_in": m, "target": {"I": I, "TP": TP, "LRA": LRA}}


def seam_lufs_check(segment_paths, max_delta=1.0):
    """Measure each assembled segment's integrated LUFS and report the level delta at every
    seam (segment N -> N+1). Seams with |delta| > max_delta are flagged — they would be an
    audible loudness jump at the cut. Returns a report dict; `ok` is False if any seam fails."""
    levels = [{"path": str(p), "lufs": round(measure_loudness(p)["input_i"], 2)} for p in segment_paths]
    seams = []
    for a, b in zip(levels, levels[1:]):
        d = round(b["lufs"] - a["lufs"], 2)
        seams.append({"from": Path(a["path"]).name, "to": Path(b["path"]).name,
                      "delta_lu": d, "ok": abs(d) <= max_delta})
    return {"ok": all(s["ok"] for s in seams), "max_delta": max_delta,
            "levels": levels, "seams": seams}


def _demo(vo, bed, outdir):
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    mix = outdir / "act_bed_ducked.wav"
    final = outdir / "act_bed_ducked_norm.wav"
    print("VO loudness     :", measure_loudness(vo))
    print("bed loudness    :", measure_loudness(bed))
    duck_under_vo(vo, bed, mix)
    print("ducked mix      :", measure_loudness(mix))
    two_pass_loudnorm(mix, final)
    print("final (2-pass)  :", measure_loudness(final))
    # bed-only ducked, to verify the speech-time separation vs the VO
    bedonly = outdir / "bed_only_ducked.wav"
    fc = (f"[1:a]aresample={SR},aformat=channel_layouts=stereo[key];"
          f"[0:a]aresample={SR},aformat=channel_layouts=stereo,volume=-20dB[bedlvl];"
          f"[bedlvl][key]sidechaincompress=threshold=0.035:ratio=14:attack=20:release=320:makeup=1[duck]")
    _run(["ffmpeg", "-hide_banner", "-y", "-i", str(bed), "-i", str(vo),
          "-filter_complex", fc, "-map", "[duck]", "-ar", str(SR), "-ac", "2", str(bedonly)])
    print("bed-only ducked :", measure_loudness(bedonly))
    return {"mix": str(mix), "final": str(final), "bed_only": str(bedonly)}


def main(argv=None):
    p = argparse.ArgumentParser(description="Deep-dive audio assembly recipes (ffmpeg).")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("duck"); d.add_argument("--vo", required=True); d.add_argument("--bed", required=True)
    d.add_argument("--out", required=True); d.add_argument("--duck-db", type=float, default=22.0)
    d.add_argument("--bed-floor-db", type=float, default=-20.0)
    n = sub.add_parser("norm"); n.add_argument("--in", dest="src", required=True); n.add_argument("--out", required=True)
    n.add_argument("--i", type=float, default=-14.0); n.add_argument("--tp", type=float, default=-1.0)
    me = sub.add_parser("measure"); me.add_argument("--in", dest="src", required=True)
    se = sub.add_parser("seam"); se.add_argument("paths", nargs="+"); se.add_argument("--max-delta", type=float, default=1.0)
    de = sub.add_parser("demo"); de.add_argument("--vo", required=True); de.add_argument("--bed", required=True)
    de.add_argument("--outdir", required=True)
    a = p.parse_args(argv)
    if a.cmd == "duck":
        print(json.dumps(duck_under_vo(a.vo, a.bed, a.out, duck_db=a.duck_db, bed_floor_db=a.bed_floor_db), indent=2))
    elif a.cmd == "norm":
        print(json.dumps(two_pass_loudnorm(a.src, a.out, I=a.i, TP=a.tp), indent=2))
    elif a.cmd == "measure":
        print(json.dumps(measure_loudness(a.src), indent=2))
    elif a.cmd == "seam":
        print(json.dumps(seam_lufs_check(a.paths, max_delta=a.max_delta), indent=2))
    elif a.cmd == "demo":
        print(json.dumps(_demo(a.vo, a.bed, a.outdir), indent=2))


if __name__ == "__main__":
    sys.exit(main())
