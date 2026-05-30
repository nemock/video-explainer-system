"""NARRATE (operator voice) — assemble the operator's per-segment recordings, run them
through the local audio-cleanup (VocalEnhancer) skill, and emit the SAME narration.wav +
segments.json contract Kokoro produces, so align/render/mux are untouched (PRD §18)."""
import json, sys, subprocess, time
from pathlib import Path
import numpy as np
import soundfile as sf

GAP = 0.18  # silence between segments (seconds)
CLEAN = Path("/Volumes/Casima/claudeCode/VocalEnhancer/skills/audio-cleanup/scripts/clean_audio.py")


def seg_path(proj, seg_id):
    return proj.voiceover_dir / f"seg_{seg_id:03d}.wav"


def _load_mono(path, target_sr):
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    if sr != target_sr:
        import torch, torchaudio
        mono = torchaudio.functional.resample(torch.from_numpy(mono).unsqueeze(0), sr, target_sr).squeeze(0).numpy()
    return mono.astype(np.float32)


def _cleanup(raw, out, sr):
    tmp = out.with_name("narration_clean.wav")
    if CLEAN.exists():
        r = subprocess.run([sys.executable, str(CLEAN), str(raw), "--preset", "streaming",
                            "--output", str(tmp), "-q"], capture_output=True, text=True)
        if r.returncode == 0 and tmp.exists():
            # clean_audio can emit a very high sample rate; normalize to 48k mono for the encoder
            subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", str(tmp), "-ar", "48000", "-ac", "1", str(out)],
                           check=True, capture_output=True)
            tmp.unlink(missing_ok=True)
            return "audio-cleanup:streaming"
    # fallback if the VocalEnhancer skill isn't present: plain loudnorm to the same target
    subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", str(raw),
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-ac", "1", str(out)],
                   check=True, capture_output=True)
    return "loudnorm:fallback"


def run(proj):
    from .common import effective_segments
    script = json.loads(proj.script_json.read_text())
    segments = effective_segments(proj, script)

    missing = [s["id"] for s in segments if not seg_path(proj, s["id"]).exists()]
    if missing:
        raise FileNotFoundError(
            f"--voice operator: missing recordings for segment(s) {missing} in {proj.voiceover_dir}. "
            f"Run `explainer record {proj.dir.name}` to record them.")

    sr = sf.info(str(seg_path(proj, segments[0]["id"]))).samplerate
    gap = np.zeros(int(sr * GAP), dtype=np.float32)
    full, segs, cursor = [], [], 0.0
    for seg in segments:
        audio = _load_mono(seg_path(proj, seg["id"]), sr)
        dur = len(audio) / sr
        segs.append({"id": seg["id"], "slide": seg["slide"], "text": seg["text"],
                     "start": round(cursor, 4), "end": round(cursor + dur, 4)})
        full.append(audio); full.append(gap); cursor += dur + GAP

    narration = np.concatenate(full)
    raw = proj.work / "narration_raw.wav"
    sf.write(raw, narration, sr)
    t0 = time.time()
    method = _cleanup(raw, proj.work / "narration.wav", sr)  # cleanup preserves duration
    dur_total = len(narration) / sr

    proj.write_json(proj.work / "segments.json",
                    {"sample_rate": sr, "duration": round(dur_total, 4), "segments": segs})
    metrics = {"voice_source": "operator", "segments": len(segs),
               "audio_duration_s": round(dur_total, 2), "cleanup": method,
               "cleanup_s": round(time.time() - t0, 2)}
    proj.write_json(proj.work / "metrics_synth.json", metrics)
    return metrics
