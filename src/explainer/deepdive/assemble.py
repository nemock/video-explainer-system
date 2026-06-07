"""Assembler — RAM-safe master render (ARCHITECTURE §12). Per segment: preflight vs CONTRACT →
two-pass-loudnorm + conform to disk → concat demuxer + stream copy (NEVER a whole-film
filtergraph) → ffprobe-exact caption stitch + chapters → master-integrity validation.

Each segment is already its own finished MP4 (an `explainer` project's mux output, or a
registered interstitial). Nothing here re-renders frames; it conforms + concatenates."""
import json
import shutil
import subprocess
from pathlib import Path

from . import actbed, audio, buildlog, captions, chapters, conform, interstitials, manifest as mf, rubric


def _sources(program, manifest):
    """Ordered list of {id, kind, src(Path), srt(Path|None), title}. Raises on a missing/unverified
    segment so assembly never silently drops a beat."""
    out = []
    for sid in program.order:
        seg = manifest["segments"][sid]
        title = program.segment(sid).get("title", sid)
        if seg.get("kind") == "interstitial":
            v = interstitials.verify(program, seg.get("registry_ref"), fps=program.fps)
            if not v.get("ok"):
                raise RuntimeError(f"interstitial '{sid}' failed verify: {v}")
            out.append({"id": sid, "kind": "interstitial", "src": Path(v["path"]), "srt": None,
                        "title": title, "placeholder": v.get("placeholder")})
        else:
            src = program.project_dir(sid) / "video" / "explainer_16x9.mp4"
            if not src.exists():
                raise RuntimeError(f"segment '{sid}' not rendered: {src} missing")
            srt = program.project_dir(sid) / "captions" / "captions.srt"
            out.append({"id": sid, "kind": "act", "src": src, "srt": srt if srt.exists() else None,
                        "title": title})
    return out


def preflight(program, *, check_only=False):
    """ffprobe every source vs CONTRACT; return a conformance table. With check_only, this is the
    `--check` command (caller exits non-zero on any mismatch)."""
    manifest = mf.load(program)
    rows = []
    for s in _sources(program, manifest):
        c = conform.check(s["src"], fps=program.fps)
        rows.append({"id": s["id"], "kind": s["kind"], "conformant": c["ok"],
                     "diffs": c["diffs"], "duration_s": round(c["duration"], 3),
                     "src": str(s["src"])})
    return {"ok": all(r["conformant"] for r in rows), "fps": program.fps, "segments": rows}


def _disk_guard(program, sources):
    """Estimate scratch (sum of source sizes x 1.6 for conformed copies + master) and refuse if
    free space on the program's volume is short."""
    need = int(sum(Path(s["src"]).stat().st_size for s in sources) * 1.6)
    free = shutil.disk_usage(program.dir).free
    return {"need_bytes": need, "free_bytes": free, "ok": free > need + (200 << 20)}


def _audio_stream_dur(mp4):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                        "-show_entries", "stream=duration", "-of", "csv=p=0", str(mp4)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def validate_master(program, master, conformed, cap_report, chapter_list):
    """Master-integrity (§12.6): duration == Σ conformed (±1 frame); audio present + continuous
    (audio stream dur ≈ master dur); last caption ≤ master; chapters monotonic, first 0, in-bounds;
    seam ΔLUFS ≤ 1.0 LU. Returns {ok, checks:{...}}."""
    frame = 1.0 / program.fps
    mdur = conform.probe(master)["format"]["duration"]
    sum_dur = sum(conform.probe(c)["format"]["duration"] for c in conformed)
    adur = _audio_stream_dur(master)
    seam = audio.seam_lufs_check(conformed, max_delta=1.0)
    starts = [c["start_s"] for c in chapter_list]
    checks = {
        "duration_match": {"ok": abs(mdur - sum_dur) <= frame + 0.05,
                           "master_s": round(mdur, 3), "sum_conformed_s": round(sum_dur, 3)},
        "audio_continuous": {"ok": adur is not None and abs(adur - mdur) <= 0.5,
                             "audio_stream_s": adur, "master_s": round(mdur, 3)},
        "captions_in_bounds": {"ok": cap_report["last_end_s"] <= mdur + 0.05,
                               "last_caption_s": cap_report["last_end_s"]},
        "chapters_monotonic": {"ok": starts == sorted(starts) and (not starts or starts[0] == 0.0)
                               and all(s < mdur for s in starts), "starts": starts},
        "seams_level_matched": {"ok": seam["ok"], "seams": seam["seams"]},
    }
    return {"ok": all(c["ok"] for c in checks.values()), "checks": checks}


def run(program, *, dry_run=False, allow_unapproved=False):
    """Assemble the master. dry_run → print the ordered plan + chapter/caption preview + total,
    no encode. By design assembly GATES on approval (plan rubric + every act segment approved);
    pass allow_unapproved to bypass (the automated spine/demo does). Returns the assembly report."""
    manifest = mf.load(program)
    mf.reconcile(program, manifest)
    if not dry_run and not allow_unapproved:
        ok, reasons = rubric.assembly_ready(manifest)
        if not ok:
            raise RuntimeError("assembly gate (not approved): " + "; ".join(reasons)
                               + "  [override with --allow-unapproved]")
    sources = _sources(program, manifest)

    if dry_run:
        rows = [{"id": s["id"], "kind": s["kind"],
                 "duration_s": round(conform.probe(s["src"])["format"]["duration"], 3),
                 "has_captions": bool(s["srt"]), "title": s["title"]} for s in sources]
        total = round(sum(r["duration_s"] for r in rows), 3)
        return {"dry_run": True, "order": rows, "total_s": total,
                "chapters_preview": [{"ts": chapters._ts(o), "title": r["title"]}
                                     for o, r in zip(_cumulative([r["duration_s"] for r in rows]), rows)]}

    guard = _disk_guard(program, sources)
    if not guard["ok"]:
        raise RuntimeError(f"disk-budget guard: need ~{guard['need_bytes'] >> 20}MB, "
                           f"free {guard['free_bytes'] >> 20}MB on {program.dir}")

    # conform (+ loudnorm) every source to disk, in order
    cdir = program.scratch_dir / "conformed"
    if cdir.exists():
        shutil.rmtree(cdir)
    cdir.mkdir(parents=True)
    bed = actbed.resolve(program)  # optional act-bed underscore (program.json music.act_bed)
    bed_dir = program.scratch_dir / "actbed"
    conformed, actions = [], []
    for i, s in enumerate(sources):
        src = s["src"]
        # act segments get the optional music bed ducked under the VO; interstitials keep their
        # own sponsor bed; loudnorm (in conform) then level-matches every seam.
        if bed and s["kind"] == "act":
            bedded = bed_dir / f"{i:02d}_{s['id']}_bed.mp4"
            with buildlog.timed(program, "act-bed", s["id"]):
                actbed.mix_under(bed, src, bedded)
            src = bedded
        dst = cdir / f"{i:02d}_{s['id']}.mp4"
        with buildlog.timed(program, "conform", s["id"]):
            actions.append(conform.conform_segment(src, dst, fps=program.fps, loudnorm=True))
        conformed.append(dst)

    # concat demuxer + stream copy (RAM-safe; conformed are CONTRACT-identical so -c copy is valid)
    listfile = program.scratch_dir / "concat.txt"
    listfile.write_text("".join(f"file '{c.resolve()}'\n" for c in conformed))
    master = program.master_dir / "deepdive_16x9.mp4"
    with buildlog.timed(program, "concat"):
        r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat",
                            "-safe", "0", "-i", str(listfile), "-c", "copy", "-movflags", "+faststart",
                            str(master)], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("concat failed:\n" + r.stderr[-1500:])

    # caption stitch + chapters (ffprobe-exact offsets off the CONFORMED segments)
    cap = captions.stitch(conformed, [s["srt"] for s in sources],
                          program.master_dir / "captions.srt", program.master_dir / "captions.vtt")
    chap = chapters.build(conformed, [s["title"] for s in sources], program.master_dir / "chapters.txt")
    validation = validate_master(program, master, conformed, cap, chap)

    report = {"master": str(master), "segments": len(sources),
              "conform_actions": [a["action"] for a in actions],
              "captions": cap, "chapters": chap, "validation": validation,
              "duration_s": validation["checks"]["duration_match"]["master_s"]}
    # reconcile (run above) has promoted rendered/ready segments; mark them assembled (journaled).
    if validation["ok"]:
        for s in sources:
            st = manifest["segments"][s["id"]]["status"]
            if st in ("rendered", "ready", "approved"):
                mf.transition(program, manifest, s["id"], "assembled", force=True, write_now=False)
    manifest["assembly"] = {"status": "assembled" if validation["ok"] else "failed",
                            "master": str(master), "validated": validation["ok"], "report": report}
    mf.write(program, manifest)
    buildlog.emit(program, stage="assemble", exit=0 if validation["ok"] else 2,
                  message=f"master {report['duration_s']}s, validated={validation['ok']}")
    return report


def _cumulative(durs):
    out, acc = [], 0.0
    for d in durs:
        out.append(acc)
        acc += d
    return out
