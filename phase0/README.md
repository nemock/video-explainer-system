# Phase 0 — end-to-end seam spike

**Goal:** prove the local, free, Apple-Silicon stack works end-to-end *before* adding any
Claude generation, and measure the go/no-go gates (render time, peak memory). A hand-written
deck stands in for what Claude will generate later.

**Seam proven:** `script.json` → **Kokoro TTS** (+ ffmpeg loudnorm) → **torchaudio MMS_FA
forced alignment** (word timestamps) → deterministic **HTML deck** driven by `renderAt(t)` →
**Playwright frame capture** → **ffmpeg VideoToolbox mux** → `explainer_9x16.mp4` + SRT/VTT.

No paid APIs. No WhisperX. No Remotion. Runs entirely on the M3 iMac.

## Stages (each independently runnable, PRD §12.3)

| Script | Stage | Output |
|---|---|---|
| `synth.py` | NARRATE | `work/narration.wav` (−14 LUFS), `work/segments.json` |
| `align.py` | ALIGN | `work/alignment.json`, `work/timeline.json`, `work/captions.{srt,vtt}` |
| `render.py` | RENDER | `work/frames/*.png` |
| `mux.py` | MUX | `video/explainer_9x16.mp4` |
| `run.py` | orchestrator | `work/results.json` |
| `memprobe.py` | mem gate (aux) | `work/metrics_memory.json` |

Run all: `myenv/bin/python3 phase0/run.py`

## Measured results (Apple M3, 16 GB, Metal — no CUDA)

Subject: a 19.2-second 1080×1920 @30fps vertical explainer (4 slides, 42 words).

| Stage | Time | Note |
|---|---|---|
| Kokoro load | ~2.3 s | one-time per process |
| **Narration synth** | **3.6 s** for 19.2 s audio | **RTF ≈ 0.19 (~5× real-time)** — not a bottleneck |
| ffmpeg loudnorm | included | −14 LUFS / −1.5 dB TP |
| **Forced alignment (MMS_FA)** | **1.3 s** | 42 word timestamps; model cached (1.18 GB, one-time download) |
| **Frame capture (Playwright)** | **21.5 s** | **37 ms/frame · 1.12× real-time** · 576 frames |
| **Mux (VideoToolbox)** | **3.7 s** | 3.5 MB MP4, bt709 tagged, faststart |
| **Total wall-clock** | **44.4 s** | for a 19.2 s video |
| **Peak render-tree memory** | **~2.1 GB** | Chromium + Python; stages serialized ⇒ well under 16 GB |

### Gate verdicts
- ✅ **Render-time gate — PASS with large margin.** 1.12× real-time means a 60 s video renders
  in ~75 s and a 180 s video in ~3.7 min. The council's worst-case fear was 1–10 min *per
  minute* of video; actual is ~1.1× total. Capture (not TTS) is the dominant cost, as predicted.
- ✅ **Peak-memory gate — PASS.** ~2.1 GB peak for the render tree; the heaviest model (MMS_FA
  ~1.2 GB) loads in a different, serialized stage. Comfortable on 16 GB unified memory.
- ✅ **Native alignment on Apple Silicon — PASS.** `torchaudio.functional.forced_align` +
  the `MMS_FA` pipeline run on CPU/MPS with no CUDA dependency — the WhisperX replacement works.
- ✅ **Determinism — PASS.** All motion computed by `renderAt(t)`; zero CSS animations on
  captured elements; `Math.random` seeded at page init. Same input → same frames.
- ✅ **Word-level sync — PASS.** Kinetic captions highlight the active word against real
  narration timestamps (visible at e.g. `work/frames/f00270.png`).

## Decisions confirmed by the spike
- **Render engine = owned Playwright capture** (not HyperFrames). Simple, fast enough, fully
  under our control for the `renderAt(t)` determinism contract.
- **Aligner = torchaudio MMS_FA forced alignment** as the default (Apple-Silicon-native).
- **Encode = h264_videotoolbox + aac_at** (hardware) with bt709 tags + loudnorm.

## Known limitations / follow-ups (deliberately out of Phase 0 scope)
- Kokoro pronounces some acronyms naturally ("RAG" as a word); the misaki phoneme-override
  lexicon (PRD R3) is a Phase-1 asset, not built here. The script pre-spells "GPT four" etc.
- Peak memory measured via `ps` sampling, not a continuous profiler — directionally exact.
- Single aspect (9:16) only; multi-aspect + per-platform safe zones are Phase 4.
- `myenv` reused for the spike (it already has torch/Kokoro); Phase 1 moves to a project
  `uv` lockfile per PRD §12.1.
