---
name: explainer
description: >-
  Turn a topic (or source document) into a visually dynamic HTML explainer deck
  and a narrated vertical video, end-to-end, using only local/free tools (Kokoro
  TTS, torchaudio forced alignment, Playwright, ffmpeg) plus this Claude session.
  Use when the user wants to "make an explainer video", "turn this into a Short/
  Reel/TikTok", "create an explainer deck", or "/explainer <topic>". Phase 1:
  topic-only, 9:16, fixed theme. Generation only — it writes a labeled output dir
  + manifest.json; it does NOT post to social platforms.
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
explainer scaffold "<slug>" --title "<title>" [--aspect 9:16] [--fps 30] [--voice af_heart]
```
This creates `outputs/<date>_<slug>/project.json` and prints the project dir. Use that dir
for everything below.

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
  { "id": "s4", "type": "payoff", "headline": "<text>", "accent": ["word"], "subkicker": "<a · b · c>" }
] }
```
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
Runs narrate → align → deck → render → mux → manifest and writes `results.json`. If a stage
fails, it prints `failed_stage`; re-run a single stage with `explainer <stage> <dir>`.

### 7. Report
Tell the user the output dir and the key artifacts:
- `deck/index.html` (standalone, openable deck)
- `video/explainer_9x16.mp4`
- `captions/captions.srt` / `.vtt`
- `manifest.json` (`ready_for_post`, AI-disclosure, per-platform captions)
Spot-check one rendered frame in `work/frames/` to confirm layout/legibility before declaring done.

## Out of scope (Phase 1)
Multi-aspect, source-PDF ingestion + screenshots, template *family*/themes, music, operator
`--interview` voice capture, C2PA embedding — these are later phases (see PRD). Don't fake them.
