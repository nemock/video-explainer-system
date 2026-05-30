#!/usr/bin/env python3
"""Phase 0 — ALIGN stage.
Native forced alignment (torchaudio MMS_FA) of narration.wav against the KNOWN
transcript -> word-level timestamps. Emits alignment.json, timeline.json, and
captions.srt/.vtt. This is the Apple-Silicon-native replacement for WhisperX.

Run: myenv/bin/python3 phase0/align.py
"""
import json, re, time, sys
from pathlib import Path
import torch, torchaudio

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"

def norm(tok: str) -> str:
    return re.sub(r"[^a-z]", "", tok.lower())

def srt_ts(t, sep=","):
    h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60); ms = int(round((t - int(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"

def main():
    script = json.loads((HERE / "script.json").read_text())
    segs = json.loads((WORK / "segments.json").read_text())["segments"]

    # build display<->normalized word pairs in transcript order, tagged by slide
    pairs = []  # (display, norm, slide)
    for seg in segs:
        for disp in seg["text"].split():
            n = norm(disp)
            if n:
                pairs.append((disp, n, seg["slide"]))
    transcript = [p[1] for p in pairs]

    device = "cpu"  # MMS_FA: CPU is reliable + fast for short clips; MPS is a later optimization
    bundle = torchaudio.pipelines.MMS_FA
    model = bundle.get_model().to(device)
    tokenizer = bundle.get_tokenizer()
    aligner = bundle.get_aligner()

    wav, sr = torchaudio.load(str(WORK / "narration.wav"))
    if wav.size(0) > 1:
        wav = wav.mean(0, keepdim=True)
    if sr != bundle.sample_rate:
        wav = torchaudio.functional.resample(wav, sr, bundle.sample_rate)
    sr = bundle.sample_rate

    t0 = time.time()
    with torch.inference_mode():
        emission, _ = model(wav.to(device))
        token_spans = aligner(emission[0], tokenizer(transcript))
    align_s = time.time() - t0

    num_frames = emission.size(1)
    ratio = wav.size(1) / num_frames  # samples per emission frame
    def t_of(frame): return float(frame) * ratio / sr

    words = []
    for (disp, n, slide), spans in zip(pairs, token_spans):
        words.append({"word": disp, "norm": n, "slide": slide,
                      "start": round(t_of(spans[0].start), 3),
                      "end": round(t_of(spans[-1].end), 3)})

    (WORK / "alignment.json").write_text(json.dumps(
        {"sample_rate": sr, "words": words}, indent=2))

    # contiguous slide windows so a slide is always on screen
    duration = json.loads((WORK / "segments.json").read_text())["duration"]
    slides = []
    for i, seg in enumerate(segs):
        start = seg["start"]
        end = segs[i + 1]["start"] if i + 1 < len(segs) else duration
        slides.append({"slide": seg["slide"], "start": round(start, 3), "end": round(end, 3)})

    (WORK / "timeline.json").write_text(json.dumps(
        {"fps": script["fps"], "duration": round(duration, 3),
         "slides": slides, "words": words}, indent=2))

    # captions: one cue per segment (subtitle granularity)
    srt, vtt = [], ["WEBVTT", ""]
    for i, seg in enumerate(segs):
        sw = [w for w in words if w["slide"] == seg["slide"]]
        if not sw:
            continue
        a, b = sw[0]["start"], sw[-1]["end"]
        srt.append(f"{i+1}\n{srt_ts(a)} --> {srt_ts(b)}\n{seg['text']}\n")
        vtt.append(f"{srt_ts(a,'.')} --> {srt_ts(b,'.')}\n{seg['text']}\n")
    (WORK / "captions.srt").write_text("\n".join(srt))
    (WORK / "captions.vtt").write_text("\n".join(vtt))

    metrics = {"align_s": round(align_s, 2), "words": len(words),
               "audio_s": round(duration, 2)}
    (WORK / "metrics_align.json").write_text(json.dumps(metrics, indent=2))
    print("ALIGN ok:", json.dumps(metrics))
    for w in words[:6]:
        print(f"  {w['start']:6.2f}-{w['end']:6.2f} {w['slide']:6} {w['word']}")
    print("  ...")

if __name__ == "__main__":
    sys.exit(main())
