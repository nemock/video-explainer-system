---
name: explainer
description: >-
  Turn a topic (or source document) into a visually dynamic HTML explainer deck
  and a narrated vertical video, end-to-end, using only local/free tools (Kokoro
  TTS, torchaudio forced alignment, Playwright, ffmpeg) plus this Claude session.
  Use when the user wants to "make an explainer video", "turn this into a Short/
  Reel/TikTok", "create an explainer deck", or "/explainer <topic>". Supports
  topic-only OR source-driven (ingest a PDF/URL and frame a real figure/screenshot);
  aspects 9:16, 16:9, 4:5; fixed theme. Generation only — it writes a labeled output
  dir + manifest.json; it does NOT post to social platforms.
---

# /explainer

Generate an explainer **deck + narrated 9:16 video** from a topic. You (Claude) do the
generation stages (research, scripting, deck authoring); a pure-Python pipeline does the
deterministic media stages (narrate → align → render → mux). No paid APIs.

## Architecture rule (do not violate)
You only author **structured JSON** (`script.json`, `deck.json`, optional `meta.json`) and
**wiki nodes**. You never write raw deck HTML — the deck engine renders from `deck.json`,
which preserves the determinism contract (PRD §8.6). The media pipeline makes **zero LLM
calls**; once the JSON exists, it renders unattended.

## Environment
- Package: `/Volumes/Casima/claudeCode/explainer-system` (run `explainer` from there).
- Interpreter: `/Users/davesaunders/myenv/bin/python3` (has Kokoro/torch/Playwright/ffmpeg).
- Console command (editable-installed into myenv): **`explainer`**. If unavailable, use
  `PYTHONPATH=/Volumes/Casima/claudeCode/explainer-system/src /Users/davesaunders/myenv/bin/python3 -m explainer.cli`.
- Shell discipline (CLAUDE.md): the `media` command is **synchronous — run it in the
  foreground and let it finish** (~50s for a ~20s video). No polling, no backgrounding.

## Steps

### 1. Intake
Parse the topic and any flags (default aspect 9:16, fps 30, voice `af_heart`). Unless the
user said `--yes`, briefly confirm: the **angle/hook**, target **length**, and **aspect**.
One cheap confirmation, then proceed.

### 2. Scaffold
```
explainer scaffold "<slug>" --title "<title>" [--aspect 9:16] [--fps 30] [--voice af_heart] [--theme midnight]
```
Themes (a *family* of looks — vary them across a channel, PRD §8.5): `midnight` (default,
cool dark), `paper` (light), `sunset` (warm dark), `forest` (green dark), `mono` (yellow on
near-black). Each carries a default motion personality.
This creates `outputs/<date>_<slug>/project.json` and prints the project dir. Use that dir
for everything below.

### 2b. Ingest source material (source-driven runs only)
If the user gave a PDF or URL, ingest it into `sources/` + `citations.json`:
```
explainer ingest <project_dir> --pdf <path> [--pages "1-3,5"]
explainer ingest <project_dir> --url <url> [--full-page]
```
This extracts text and renders framed screenshots/figures. To feature a **specific
figure** (not a whole page), it's fine to render a tight clip with PyMuPDF
(`page.get_pixmap(matrix=fitz.Matrix(3,3), clip=fitz.Rect(...))`) into `sources/`.
Read the extracted text to ground the script; reference an image in a `figure` slide (below).

### 3. Research (+ wiki)
- First **reuse** prior knowledge: read `wiki/INDEX.md` and any relevant `wiki/source-fact/*`
  nodes so you don't re-research what's already captured.
- Then use **WebSearch/WebFetch** to gather and *verify* current facts. Prefer primary sources.
- Capture what you learn as wiki nodes (provenance compounds across videos):
  ```
  explainer wiki source "<source title>" --root . --topic "<topic>" --ref "<url-or-path>"
  explainer wiki fact "<short fact name>" --root . --topic "<topic>" \
      --body "<the atomized claim>" --source "<source slug>" --confidence high
  ```
- Every claim that ends up on screen or in narration should trace to a fact you can cite.

### 4. Author script.json + deck.json
Pick a **hook archetype** for slide 1 (bold claim · question · surprising stat · "you've
been doing X wrong" · visual reveal). The first slide must front-load the payoff — no
title-card throat-clearing.

`script.json` — narration per slide (the `slide` field is the slide id, matched in deck.json):
```json
{ "segments": [
  { "id": 0, "slide": "s1", "text": "<hook line — spoken>" },
  { "id": 1, "slide": "s2", "text": "<...>" }
] }
```
Spell tricky tokens phonetically for Kokoro (e.g. "GPT four", not "GPT-4"); acronyms like
"RAG" are read as words.

`deck.json` — one slide per id, fixed-theme slide **types**:
```json
{ "title": "<deck title>", "slides": [
  { "id": "s1", "type": "hook", "kicker": "<small label>", "headline": "<text>", "accent": ["word"] },
  { "id": "s2", "type": "statement", "headline": "<text>", "accent2": ["word"] },
  { "id": "s3", "type": "diagram", "kicker": "<label>",
    "bars": [ { "label": "<a>", "value": 0.9, "kind": "good" },
              { "label": "<b>", "value": 0.3, "kind": "bad" } ] },
  { "id": "s4", "type": "figure", "kicker": "<source attribution>",
    "image": "sources/<file>.png", "caption": "<one-line description of the figure>" },
  { "id": "s5", "type": "payoff", "headline": "<text>", "accent": ["word"], "subkicker": "<a · b · c>" }
] }
```
`figure` slides frame an ingested screenshot/figure (white card on the dark theme); the
`image` path is relative to the project root (e.g. `sources/x.png`). Use them to feature
real source material on source-driven runs.

Each slide may set `"transition"` (`rise` · `fade` · `pop` · `slide`) to override the
theme's default intro motion. **Vary it** across slides — don't repeat the same transition
on every slide (the §8.4 anti-repetition rule); repetition reads as "templated".
Rules: every slide has motion by construction; `accent`/`accent2` highlight words by the
theme colors; keep headlines tight (they auto-shrink past ~60 chars). Keep `id`s identical
across the two files. Aim for 4–6 slides for a ~20–40s Short.

### 5. (optional) meta.json for the manifest
Author `meta.json` with a summary + per-platform captions so the downstream poster has what
it needs (this tool still does NOT post):
```json
{ "summary": "<1-2 sentences>",
  "per_platform": [
    { "platform": "tiktok", "caption": "<hook-first caption>", "hashtags": ["#ai","#rag"],
      "link_placement": "none", "primary_asset": "video", "aspect": "9:16" }
  ],
  "sources": ["<url>", "<url>"] }
```

### 6. Render (pure-Python, synchronous)
```
explainer media outputs/<date>_<slug>
```
Runs narrate → align → deck → render → mux → manifest → **qa** and writes `results.json`. If
a stage fails, it prints `failed_stage`; re-run a single stage with `explainer <stage> <dir>`.

The **qa** stage (motion/pacing) reports warnings in `work/qa.json`: *visual dead air during
speech* (held frames while narrating — add motion or split the shot), over-long shots, and
uniform cut rhythm. Read the warnings; if dead air is high, tighten pacing or split slides
and re-render. Warnings are advisory, not fatal.

### 7. Report
Tell the user the output dir and the key artifacts:
- `deck/index.html` (standalone, openable deck)
- `video/explainer_9x16.mp4`
- `captions/captions.srt` / `.vtt`
- `manifest.json` (`ready_for_post`, AI-disclosure, per-platform captions)
Spot-check one rendered frame in `work/frames/` to confirm layout/legibility before declaring done.

## Aspects
Scaffold with `--aspect 9:16` (Shorts/TikTok/Reels), `16:9` (YouTube/LinkedIn), or `4:5`
(in-feed). The deck sizing is short-side based, so all aspects render consistently. Pick the
aspect to match the target platform; one project renders one aspect (multi-aspect from one
project is Phase 4).

## Out of scope (current phase)
Music + beat-sync, operator `--interview` voice capture, C2PA embedding, per-platform
safe-zone insets, simultaneous multi-aspect — these are later phases (see PRD). Don't fake them.
