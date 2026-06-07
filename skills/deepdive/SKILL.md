---
name: deepdive
description: >-
  Produce a long-form (~20+ min, 16:9) operator-narrated deep-dive video — an orchestrated film
  of many small `explainer` segments (cold-open → Act I → sponsor → Act II → sponsor → Act III →
  CTA), assembled RAM-safely into one master with chapters + captions. Use when the user wants a
  "deep dive", "long-form explainer", "YouTube tutorial video", "20-minute video", or runs
  "/deepdive <topic>". Brand-parameterized (FWF-first). You author the plan + per-segment
  script/deck and drive the record/review loop; a pure-Python pipeline does narrate→align→render
  →mux per segment and conform→concat→validate for the master. Generation only — it writes a
  labeled program dir + crash-safe manifest; it NEVER posts to social platforms (that's Phase 3).
---

# /deepdive

Build a long-form deep-dive **film** from a topic. It composes MANY single-`explainer` projects
(one per ~60–90s sub-segment + the cold-open + CTA) plus pre-rendered sponsor interstitials, then
conforms and concatenates them into one master. You (Claude) own the **generation + editorial**
judgment; the `deepdive` and `explainer` CLIs own the deterministic media + assembly.

## Architecture rules (do not violate)
- You author **structured artifacts only**: `content-plan.md` (the editorial spine), and per
  segment a `script.json` + `deck.json` (same contract as `/explainer` — never raw HTML).
- The media path (narrate → align → render → mux) and the assembler (conform → concat → validate)
  make **zero LLM calls** — they run unattended and resumably.
- **Each sub-segment is its own `explainer` project** under `segments/<id>/`. The master is built
  by **conform → concat demuxer + stream copy**, never a whole-film filtergraph.
- **The manifest is the single source of truth** and is crash-safe — only ever mutate it through
  the `deepdive` CLI. Resume anytime; run `deepdive doctor <program>` to see state + next actions.
- **Generation only.** Stop at `master/` + manifest + packaging. Never post.

## Environment
- Run from the `explainer-system` repo. Console commands (editable-installed): **`deepdive`** and
  **`explainer`**. Media/assembly steps are **synchronous — run in the foreground, no polling**.
- **Brand:** `FFW` (Founders Who Finish) + `--theme fwf`. The brand carries a `talk_time` block →
  author in the operator's real voice (see `/explainer` step 4a).
- **Knowledge:** the shared `cb` vault at `make_money/brain/` — query it library-first before the
  web (see `deep-dive/BRAIN-RECIPE.md`); promote durable findings back on completion.
- Operator specifics (FWF instance config, voice library) live in `~/.claude/explainer-brands/
  dave-byline/` — read them; never copy that content into this public repo.

## Workflow

### 1. Initiate
Confirm the **topic + the transformative outcome** (what the viewer can DO after — D9), then:
```
deepdive new "<slug>" --title "<benefit-forward working title>"
```
Creates `deep-dive/programs/<date>_<slug>/` with `program.json` (a **skeleton** order
cold-open→act-1→fwf-sponsor→act-2→thebuild-sponsor→act-3→cta) + an initial manifest. The
`act-1/2/3` entries are placeholders you **expand into sub-segments** in step 4b — don't author
to them as-is.

### 2. Research (library-first)
Query the brain first (personas, the 4 named frameworks, the source roster), THEN the web for
what's missing — every on-screen/narrated claim must trace to a source. Per `deep-dive/
BRAIN-RECIPE.md`: `cb list-nodes` / `cb get-node` (or the `query` skill). Keep working notes in
`programs/<slug>/research/` (scratch — promoted to the brain only on completion).

### 3. Content plan (the editorial spine) — BEFORE recording
```
deepdive plan <program_dir>
```
Author the scaffolded `content-plan.md`: the **transformative outcome**, the **throughline
thesis + why-watch-this**, the **open-loop / payoff ledger** (2–3 loops, each with a tagged
payoff beat), the **act structure** (default ~15/55/30 — Act II carries the teaching; warn only
on extreme lopsidedness), idea-boundary **sub-segments** with explicit **hand-off lines**, the
**cold open** (10–20s: payoff/stakes + primary loop), **pre-sponsor teases**, and a **shot list**
(Adobe Stock search prompts to review). Record the film's archetype for the variety guard:
`deepdive set-arc` (or set `rubric.arc` via the manifest) — hook archetype / three-act rhythm /
payoff type.

### 4. Plan rubric gate (§8.5) — self-critique, then approve
```
deepdive rubric <program_dir> plan      # emits the checklist
```
Honestly evaluate each item (transformative outcome named, benefit-forward title, hook strength,
2–3 open loops with payoffs, act balance, MECE horizontal logic, beat variety, why-watch-this).
**Revise the plan until it passes.** Run the variety guard (warns if this arc repeats recent
films). Then:
```
deepdive approve-plan <program_dir> --notes "<what you checked>"
```
**Recording/assembly is gated on this** — the manifest refuses to assemble an unapproved plan.

### 4b. Expand the order into your sub-segments (the segment model — read this)
**`order` is a FLAT, ordered list of build/record units.** Each entry is either one `explainer`
project (a ~60–90s sub-segment, the cold-open, or the CTA) under `segments/<id>/`, **or** a
registered interstitial. There is **no nested "act → sub-segments" structure in the manifest** —
the assembler walks `order` top-to-bottom, conforms each entry's MP4, and concatenates them. The
record/align/gate/review loop also operates **per `order` entry**. So:

- **Acts are a grouping concept, not a manifest level.** Replace each `act-N` skeleton entry with
  that act's actual sub-segments, each its own `order` entry + `segments` def. Edit `program.json`
  directly (it's the intent file; `deepdive` reconciles the manifest from it):
  ```json
  "order": ["cold-open", "act1-sub01", "act1-sub02", "fwf-sponsor",
            "act2-sub01", "act2-sub02", "act2-sub03", "thebuild-sponsor",
            "act3-sub01", "act3-sub02", "cta"],
  "segments": {
    "cold-open":  { "kind": "act", "title": "Cold open",        "chapter": "Intro" },
    "act1-sub01": { "kind": "act", "title": "<sub-seg hook>",   "chapter": "Act I — <act title>" },
    "act1-sub02": { "kind": "act", "title": "<...>",            "chapter": "Act I — <act title>" },
    "fwf-sponsor":{ "kind": "interstitial", "registry_ref": "interstitial-fwf-book", "title": "Founders Who Finish" },
    "act2-sub01": { "kind": "act", "title": "<...>",            "chapter": "Act II — <act title>" }
    /* … */
  }
  ```
- **IDs are free-form** (use `act1-sub01`-style ids so order reads clearly). `kind` is `"act"`
  for your projects, `"interstitial"` for sponsors/CTA (with a `registry_ref`).
- **`chapter` groups sub-segments into ONE YouTube chapter.** Give every sub-segment of an act the
  **same `chapter` string** → the assembler collapses them into a single act-level chapter (without
  it, you'd get a chapter per 60–90s sub-segment). `title` stays per-segment (used as the chapter
  label only when `chapter` is absent).
- After editing `order`, run `deepdive doctor <dir>` — it reconciles the manifest to the new list.

### 5a. Author every sub-segment (scaffold + script/deck) — do this for ALL of them first
For each act/cta sub-segment in `order` (skip interstitials):
1. **Scaffold** it as an `explainer` project. **Act sub-segments use `--no-cta`** — it keeps the
   FWF watermark but suppresses the auto-appended book-CTA slide + spoken CTA tail (the `--brand`
   default adds one to *every* project, which is right for short-form Reels but would put a book CTA
   at the end of every 60–90s beat). The film's single CTA is the dedicated **closing `cta` segment**.
   ```
   explainer scaffold "<seg-id>" --theme fwf --aspect 16:9 --brand FFW --no-cta \
       --voice-source operator --outdir <program_dir>/segments
   ```
   then rename `segments/<date>_<seg-id>/` → `segments/<seg-id>/` to match the manifest id.
   *(The closing `cta` segment is the ONE place to keep the CTA: scaffold it `--brand FFW` WITHOUT
   `--no-cta`. Sponsor interstitials are pre-rendered and carry their own CTAs.)*
2. **Author** `script.json` + `deck.json` (the `/explainer` device catalog — favor McKinsey
   treatments: action `title` + `source` line on data-viz, `kind:"muted"` insight highlight,
   narration-paced `build`). Ground the words in the operator's voice via
   `explainer talktime --brand FFW --topics "<keywords>"` — quote verbatim, adapt, **never fabricate**.
3. Offer the operator a quick **script review** before any recording (re-recording is the costly step).

### 5b. Record sprint — YOU DRIVE THIS LOOP. Do NOT hand the operator a command list.
This is an interactive, **coached** loop: **you run every command; the operator only reads the
teleprompter and clicks Finish.** Walk them through the segments one at a time — never dump the
segment list + commands for them to run themselves. For each act/cta sub-segment, in `order`
(skip interstitials):

1. Launch the recorder in the **background** (so you stay responsive and aren't killed by a tool
   timeout while they read):
   ```
   deepdive record "<program_dir>" "<seg-id>" --gate-only
   ```
   `--gate-only` records → aligns → runs the **alignment gate** but **skips rendering**, so there's
   **no render wait between takes** — the operator powers straight through. It opens the teleprompter
   in their browser, pre-loaded with the prior segment's hand-off line for tonal continuity.
2. Say one short line: *"Recording **<title>** — read the teleprompter, hit **Finish** when done."*
   Then **wait** for the background command to complete (you'll be notified).
3. Read the **gate** result:
   - **Passed** → *"✓ clean take"* and **immediately launch the next segment** (auto-advance).
   - **Failed** → tell them exactly what it caught (the timestamps: an ad-lib, dropped phrase, or
     long pause) and **re-launch the recorder for the same segment**. If they changed the wording on
     purpose, edit that segment's `script.json` to match and re-run.
4. Repeat until every act/cta segment is recorded + gated. Resume anytime — `deepdive doctor` shows
   what's left.

### 5c. Render the recorded segments (batch, unattended)
After the sprint, render each recorded segment — the slow frame-capture step, no operator needed.
Run them **one at a time** (RAM-safe), in the background:
```
deepdive build-segment "<program_dir>" "<seg-id>"   # narrate(assemble clips) -> align -> gate -> render -> mux
```

### 5d. Review (approve/reject) — assembly gates on `approved`
Spot-check each rendered segment (a frame or a quick playback), then record the verdict:
```
deepdive review "<program_dir>" "<seg-id>" approve|reject --notes "<why>"
```

*(Fully-TTS draft/preview: scaffold WITHOUT `--voice-source operator`, skip 5b entirely, and run
`deepdive build-segment` per segment — the gate passes trivially since the narration is the script.)*

### 6. Sponsor + CTA interstitials
The FWF book / The Build / CTA interstitials are **pre-rendered, registered** MP4s
(`deep-dive/brand/interstitials/interstitial-registry.json`). The assembler verifies their
hash + format automatically. If they're still TTS placeholders, note that in the report; Dave
swaps in the face-cam composites later (then they're re-registered).

### 7. Assemble the master
```
deepdive assemble <program_dir> --check     # preflight conformance table (catches format drift)
deepdive assemble <program_dir>             # conform -> concat -> captions -> chapters -> validate
```
Gated on the approved plan + every act segment `approved`. Produces `master/deepdive_16x9.mp4`,
`captions.srt`/`.vtt`, `chapters.txt`, and a master-integrity report (duration, audio continuity,
caption bounds, monotonic chapters, level-matched seams). Use `--dry-run` for a cheap ordered
preview first.

### 8. Whole-film rubric gate (§8.5) — before publish
Watch the master end-to-end. Then:
```
deepdive rubric <program_dir> film      # retention read, seam check, callbacks paid, dead-air,
                                        # sponsor teases, packaging present
deepdive approve-film <program_dir> --notes "<what you checked>"
```

### 9. Boundary + promote
Report the master + chapters + captions + the manifest path. **Stop here — never post** (Phase 3
publishes via Blotato). On completion, **promote** durable research (sourced facts, a new named
framework, what-worked patterns, the produced piece) from `research/` into the brain via the
`atomize` / `intake` skills (`deep-dive/BRAIN-RECIPE.md`).

## Observability & resume
- `deepdive status <program_dir>` — concise state · `deepdive doctor <program_dir>` — full
  lifecycle checklist + manifest-vs-disk drift + concrete next actions.
- `build-log.jsonl` records every stage's timing + peak RAM; `.history/transitions.jsonl` is the
  audit trail. A crashed segment (dead owner PID) is auto-detected and re-surfaced by `doctor`.

## Out of scope (current phase)
Packaging automation (title variants + thumbnail composite) is landing in 2.5; YouTube publishing
+ the snippet promo engine are **Phase 3** (never in this skill). Cross-dissolve transitions, act-bed
ducking wiring, and stock B-roll compositing are later sub-phases — don't fake them; note them.
