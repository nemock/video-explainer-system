# video-explainer-system

A local-first **Claude Code skill** (`/explainer`) that turns a topic or source document into a **visually dynamic HTML explainer deck** and a **narrated MP4**, end-to-end — using only local/free tools plus a Claude subscription. No paid SaaS in the generation path.

Inspired by [`prajwal-y/video_explainer`](https://github.com/prajwal-y/video_explainer), but it drops ElevenLabs (→ [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M)) and Remotion/React (→ a plain HTML deck rendered via headless-Chrome frame capture + ffmpeg).

## Status

Planning. The design lives in **[PRD.md](PRD.md)** (v0.3, revised after a multi-perspective council review). Working conventions and standing rules are in **[CLAUDE.md](CLAUDE.md)**.

## What it does (target)

- Ingests a topic, PDF, URL, or screenshots; researches and verifies to deepen the content.
- Writes a voice-over script and synthesizes narration locally with Kokoro TTS.
- Aligns visuals to word-level timestamps and generates an animated, on-brand HTML deck.
- Renders platform-shaped MP4s (9:16 / 16:9 / 4:5 / 1:1) with kinetic captions.
- Maintains an **atomized knowledge wiki** that compounds sourced research across runs and captures the operator's personal voice.
- Writes a labeled output directory + a versioned, disclosure-compliant `manifest.json` for a downstream poster. **It does not post.**

## Design principles

- **Local & free** generation path; runs on Apple Silicon (Metal, no CUDA).
- **Generation/media split:** the LLM is confined to the generation stages; the media path (narrate → align → render → mux) is pure Python and runs unattended.
- **Generation only:** the boundary ends at a labeled output directory + manifest.

See [PRD.md](PRD.md) for the full architecture, pipeline, risks, and roadmap.
