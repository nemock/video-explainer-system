#!/usr/bin/env python3
"""Phase 0 — NARRATE stage.
Kokoro TTS per segment -> concatenated narration.wav (loudness-normalized to -14 LUFS).
Emits segments.json with per-segment [start,end] times (slide boundaries).

Run: myenv/bin/python3 phase0/synth.py
"""
import json, time, subprocess, sys
from pathlib import Path
import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
WORK.mkdir(exist_ok=True)
SR = 24000          # Kokoro output sample rate
GAP = 0.18          # seconds of silence between segments

def main():
    script = json.loads((HERE / "script.json").read_text())
    from kokoro import KPipeline
    t0 = time.time()
    pipe = KPipeline(lang_code="a")  # American English
    load_s = time.time() - t0

    gap = np.zeros(int(SR * GAP), dtype=np.float32)
    full = []
    segs = []
    cursor = 0.0
    synth_s = 0.0
    for seg in script["segments"]:
        ts = time.time()
        chunks = []
        for _, _, audio in pipe(seg["text"], voice=script["voice"], speed=1):
            a = audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio)
            chunks.append(a.astype(np.float32))
        synth_s += time.time() - ts
        seg_audio = np.concatenate(chunks) if chunks else np.zeros(1, np.float32)
        dur = len(seg_audio) / SR
        segs.append({"id": seg["id"], "slide": seg["slide"], "text": seg["text"],
                     "start": round(cursor, 4), "end": round(cursor + dur, 4)})
        full.append(seg_audio); full.append(gap)
        cursor += dur + GAP

    narration = np.concatenate(full)
    raw = WORK / "narration_raw.wav"
    sf.write(raw, narration, SR)

    # loudness normalization to broadcast/social target (-14 LUFS) via ffmpeg
    out = WORK / "narration.wav"
    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", str(raw),
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), str(out)]
    subprocess.run(cmd, check=True, capture_output=True)

    total_dur = len(narration) / SR
    (WORK / "segments.json").write_text(json.dumps(
        {"sample_rate": SR, "duration": round(total_dur, 4), "segments": segs}, indent=2))

    rtf = synth_s / total_dur if total_dur else 0
    metrics = {"kokoro_load_s": round(load_s, 2), "synth_s": round(synth_s, 2),
               "audio_duration_s": round(total_dur, 2), "rtf": round(rtf, 3)}
    (WORK / "metrics_synth.json").write_text(json.dumps(metrics, indent=2))
    print("NARRATE ok:", json.dumps(metrics))
    for s in segs:
        print(f"  seg{s['id']} [{s['start']:6.2f}-{s['end']:6.2f}] {s['slide']:6} | {s['text']}")

if __name__ == "__main__":
    sys.exit(main())
