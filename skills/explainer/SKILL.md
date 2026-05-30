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
explainer scaffold "<slug>" --title "<title>" [--aspect 9:16] [--theme midnight] [--brand FFW] [--voice-source operator]
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
Write acronyms **naturally** ("MCP", "AI", "GPT-4") — the pronunciation lexicon speaks them
as letters/words while captions still show the acronym. Add a `<project>/lexicon.json`
(`{"token": "spoken form"}`) for any term the default lexicon misses. Spell out numbers you
want read a certain way (e.g. "ninety seven million").

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

#### 4a. talk-time READ — write the script in the operator's real voice
When the brand carries a `talk_time` tag (BRG→`brg`, FFW→`fwf`), don't write generic AI
prose — ground the script in the operator's **own** documented takes, stories, and quotes.
This is independent of *who speaks* (Kokoro or operator VO): it shapes the **words**.

Surface the relevant material (read-only — never writes, never fabricates):
```
explainer talktime --brand <SLUG> [--topics "ai,vc,fda"]
```
It parses the talk-time library's `INDEX.md`, filters entries by the brand tag (+ optional
topic keywords), and prints candidate **quotes / positions / anecdotes / topics** with
absolute paths. Then:
1. **Read** the candidate files you'll draw on (Read tool, the printed abspaths).
2. **Quote VERBATIM** from `quotes.md` — use the exact one-liners as spoken lines.
3. **ADAPT freely** from `positions/` and `anecdotes/` — paraphrase the reasoning/story into
   tight script prose.
4. **NEVER fabricate** a take, stat, or story not in the library. If the library is thin on
   the topic, say so and write only what the source material supports (or narrow the angle).
5. Watch the per-entry brand tags + any `⚠` notes in INDEX.md (e.g. "overused — rotate",
   NDA cautions) — honor them.

Use `--topics` to narrow to the deck's subject; omit it to see everything tagged for the
brand. This applies to both the daily (Kokoro) and weekly (operator VO) tiers.

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

Decks include a subtle drifting **ambient glow** by default (keeps motion alive between word
highlights → near-zero dead air). It roughly **doubles render time** (compositing the glow
layer); set `"ambient": false` in `project.json` for ~2× faster renders when speed matters.

### 7. Report
Tell the user the output dir and the key artifacts:
- `deck/index.html` (standalone, openable deck)
- `video/explainer_9x16.mp4`
- `captions/captions.srt` / `.vtt`
- `manifest.json` (`ready_for_post`, AI-disclosure, per-platform captions)
Spot-check one rendered frame in `work/frames/` to confirm layout/legibility before declaring done.

## Aspects, platforms & length
- `--aspect 9:16|16:9|4:5|1:1`, or render **several at once** with `--aspects "9:16,1:1"`
  (one project → one MP4 per aspect; layout is robust across aspects).
- `--platform <tiktok|reels|shorts|threads|linkedin|youtube|square>` sets the aspect + a
  safe-zone bottom inset (captions clear the platform's UI chrome) and, where relevant, a
  default min length (e.g. tiktok ⇒ 60s).
- `--min-length <seconds>`: if the rendered narration is shorter, the manifest gets a
  `length_warning` and `ready_for_post:false`. **Meet it by deepening the script with a
  sourced beat (a new example / fact), never by padding** (PRD §7) — then re-render.

### 8. Validate + hand off (boundary stops here)
- `explainer validate <dir>` — confirm the manifest is a complete, consistent handoff
  contract (videos exist, captions present, per-platform aspects rendered, disclosure set).
- `explainer handoff <dir>` — emit `handoff.json`: per-platform **blotato-ready** post specs
  (absolute `media_file`, composed `text`, `title` for YouTube, `ai_label`). A poster (the
  `blotato-crosspost` skill) consumes it: upload `media_file` → `create_post` per entry.
  **This tool never posts.** The `ai_disclosure` block maps to the poster's AI toggle (e.g.
  TikTok's `isAiGenerated`) — keep it set so publishes are compliant.

### Optional: music bed
Set `"music": "<path>"` (and optionally `"music_gain": 0.16`) in `project.json` to mix a
low royalty-free bed under the narration (recommended for 9:16; off for 16:9/deck). No audio
ships with the tool — provide your own vetted, licensed track.

## Branding & call-to-action (`--brand <SLUG>`)
Pass a brand slug to stamp the video with a brand and a CTA. Resolution is **local-first
then global**: `./brand/<SLUG>/` (the content project you run from) → `$EXPLAINER_BRAND_DIR/`
→ `~/.claude/explainer-brands/<SLUG>/`. A brand folder holds `brand.json` + assets:
```json
{ "name": "Founders Who Finish",
  "logo": "logo.png",            // transparent PNG — small corner watermark on EVERY slide + larger on the CTA
  "product": "product.png",      // optional — e.g. a book cover, shown on the CTA slide
  "watermark_corner": "bl",      // bl | br
  "accent": "#5b8cff",           // optional — tints the theme accent to brand color
  "lexicon": { "davesaunders.net": "Dave Saunders dot net" },  // optional — brand-specific pronunciations
  "talk_time": { "tag": "brg" },  // optional — links the brand to its talk-time slice (see step 4a)
  "cta": { "headline": "Read the book.", "subkicker": "Out now",
           "url": "founderswhofinish.com",
           "spoken": "Grab my book, Founders Who Finish — link in bio." } }
```
When `--brand` is set: assets are copied into the output dir (self-contained), the **logo
watermarks every slide** in the safe-zone corner, and a **CTA end slide is auto-appended**
(product + larger logo + headline/subkicker/url) **with the `cta.spoken` line auto-narrated**
and synced. You don't author the CTA slide/segment — the pipeline adds them from the brand
(author your own `{"id":"cta","type":"cta"}` slide / `slide:"cta"` segment only to override).
The `url` is on-screen text only — the tool still never links out or posts.

## Voiceover mode — the operator's real voice (`--voice-source operator`)
For higher-production pieces, the narration can be **the operator reading the script**, instead of
Kokoro. The pipeline is audio-first, so a real recording aligns to the slides exactly like Kokoro
does. Be a **coach** through this loop — keep it seamless, no external apps:

1. **Scaffold** with `--voice-source operator` (everything else is the same).
2. **Author** script.json + deck.json as usual. Offer a quick **review checkpoint** — let the operator
   tweak the script *before* recording (re-recording is the costly step).
3. **Record (integrated).** Run **`explainer record <project_dir>`** — but launch it **in the
   background** so the conversation keeps moving. It opens a browser **teleprompter** that records the
   mic per segment (record / re-record / playback), saving straight into `voiceover/`. Tell the operator:
   *"Teleprompter's open — read each segment, re-record any you flub, then click Finish."* The command
   returns when they click **Finish**; its result lists `recorded` / `missing` segment ids.
4. **If any segment is `missing`,** tell them which and re-launch `record` (already-recorded segments
   stay ✓). Don't proceed until all are recorded.
5. **Render.** Run `explainer media <project_dir>` — the operator-narrate path assembles the clips,
   runs them through the local **audio-cleanup** skill (podcast-grade, −14 LUFS), aligns, and renders.
6. **Report** the finished video and ask *"what do you think?"*

The tool can also run **fully end-to-end** with Kokoro (`--voice-source kokoro`, default) — give it a
topic and it returns a finished video. Voiceover mode is the **interactive, co-built** tier.

## Out of scope (current phase)
Music *beat-sync*, operator `--interview` voice capture, **C2PA embedding** (needs c2patool +
a signing cert — disclosure is currently carried in the manifest + poster AI toggle), automatic
min-length deepening (you do it), layout *variants* within a template — later phases (see PRD).
Don't fake them.
