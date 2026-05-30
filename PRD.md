# Product Requirements Document — **Explainer System**
### A local-first Claude Code skill that turns a topic or source document into a visually dynamic HTML explainer deck and a narrated video, end-to-end.

- **Status:** Draft **v0.3** — v0.2 (post-council) + operator-directed additions: atomized knowledge wiki, confirmed decisions (see §16 Changelog)
- **Author:** Dave Saunders (with Claude Code)
- **Date:** 2026-05-30
- **Working directory:** `/Volumes/Casima/claudeCode/explainer-system`
- **Target machine (verified):** Apple **M3 iMac, 16 GB unified memory, Metal (no CUDA)**

---

## 1. Summary

The Explainer System is a **Claude Code skill** (`/explainer`) that ingests a topic or a specific piece of source material (PDF, markdown, URL, or screenshots), performs additional research to deepen and verify the content, generates a **visually dynamic, graphical HTML slide deck**, writes a voice-over script, synthesizes narration **locally** with Kokoro TTS, and assembles everything into a **finished MP4** in multiple aspect ratios.

It is inspired by the architecture of [`prajwal-y/video_explainer`](https://github.com/prajwal-y/video_explainer) but deliberately diverges on two points:

1. **No paid SaaS in the generation path.** ElevenLabs → Kokoro (local). The LLM is the user's existing Claude subscription via Claude Code. No per-asset API spend.
2. **No Remotion / React requirement.** The renderable artifact is a **plain HTML/CSS deck** — a first-class, reusable output in its own right — rendered to video via a headless-browser frame-capture pipeline.

The skill's boundary is **content generation only.** It writes a clean, **labeled output directory** + a versioned `manifest.json` that a separate tool (e.g. the existing `blotato-crosspost` skill, with a small adapter) can pick up to post to LinkedIn, YouTube Shorts, TikTok, Instagram, and Threads. This tool does not post.

> **Reality check from the council (§16):** the target is an Apple-Silicon M3 with unified memory, not a CUDA GPU box. Kokoro is already installed and benchmarks ~6× faster than real time here; ffmpeg has VideoToolbox hardware encoders; but **WhisperX is not viable as the default aligner** on this machine and the render path is the real time-budget risk. v0.2 corrects all three.

---

## 2. Goals & non-goals

### Goals
- **G1 — End-to-end, one command.** `/explainer <topic-or-path>` → deck + video + manifest, with defined behavior on failure (not just the happy path).
- **G2 — Local & free generation.** Every step in the critical path runs on the M3 iMac or via the existing Claude subscription. No new paid subscriptions to produce a complete video.
- **G3 — Visually dynamic output.** Graphical, animated HTML slides — never bullet-points-over-stock-photo — with a specified **hook**, motion-per-scene, kinetic captions, and varied transitions.
- **G4 — Dual-purpose artifact.** The HTML deck is a real deliverable (presentable, shareable, embeddable), independent of the video.
- **G5 — Platform-shaped exports.** Per-platform presets carrying resolution, aspect (16:9, 9:16, **4:5**, 1:1) and **explicit safe-zone insets**.
- **G6 — Minimum-length targeting.** User can specify a minimum playback time; the tool **deepens content with sourced material** to meet it (never pads), within a bounded, terminating loop.
- **G7 — Clean, compliant handoff.** A labeled output directory + a **versioned manifest** carrying per-platform captions and **AI-disclosure/provenance** so a downstream poster publishes correctly and compliantly.

### Non-goals
- **N1 — Posting / scheduling to social platforms.** Out of scope (handoff only).
- **N2 — Photoreal AI video / talking-head avatars.** Graphical/motion-explainer, not generative video.
- **N3 — Real-time / interactive playback runtime.** Output is a deck + a rendered file.
- **N4 — Multi-user / hosted service.** Single-user, local CLI/skill.

---

## 3. Users & key scenarios

**Primary user:** a technically literate creator (the author) who wants to turn papers/articles/docs into engaging short and long explainers at near-zero marginal cost — **with a human in the loop**, not a fully unattended content farm (see R10).

- **S1 — Topic-only:** "Make a 90-second explainer on retrieval-augmented generation." Researches, structures, produces a vertical Short with a cold-open hook.
- **S2 — Source-driven (the differentiator demo):** "Turn this PDF into a 3-minute LinkedIn explainer; pull the figure on page 4 as a slide." Ingests, screenshots the figure, expands with research, produces 4:5/16:9. **This is the Phase 2 acceptance demo.**
- **S3 — Eligible-length targeting:** "TikTok needs ≥ 60s for Creator Rewards eligibility — make it ≥ 75s." Tool meets the floor by deepening content. (Length is *one* eligibility gate among follower/view/originality gates — see §15 note.)
- **S4 — Deck reuse:** User takes the generated HTML deck into a talk or embeds it in a blog post, ignoring the video entirely.

---

## 4. Reference architecture (what we keep from `video_explainer`)

The upstream pipeline's **stage decomposition** and its single most important insight are adopted; the implementations are swapped for local/Apple-Silicon-native tools.

> **Key insight preserved (every council lens endorsed this):** *audio is generated before the storyboard is finalized,* so visuals synchronize to **word-level timestamps** of the real narration. This makes broadcast-quality sync and kinetic captions cheap.

| Upstream (`video_explainer`) | Explainer System (local, M3) |
|---|---|
| Document ingestion (PyMuPDF, URL) | Same — PyMuPDF + readability + **source screenshots** |
| Script generation (Claude API) | Claude Code (subscription) — no API key |
| TTS: ElevenLabs / edge-tts | **Kokoro-82M** (Apache-2.0, local, already installed) |
| Scene = Remotion React component | **HTML/CSS slide** + deterministic JS animation |
| Word timestamps from TTS provider | **Apple-Silicon-native forced alignment** (not WhisperX — see §6) |
| Storyboard JSON | Timeline JSON keyed to word timestamps |
| Render: Remotion headless | **Headless-Chrome frame capture → ffmpeg (VideoToolbox)** |
| Music: MusicGen (PyTorch) | Vetted royalty-free local bed (default ON for 9:16, see §6/R5) |
| Refinement: 4-phase QA | Static-frame QA **+ motion/pacing QA** (§8) |
| Shorts: 1080×1920 | Multi-aspect export as a first-class feature |

---

## 5. Proposed pipeline

```
/explainer <topic | path | url>  [--min-length 75s] [--aspect 9:16] [--platform tiktok] ...

 1. INTAKE        Resolve input; detect type (topic / pdf / md / url / image set)
 2. INGEST        Extract text + figures; screenshot source pages/regions worth showing
 3. RESEARCH      Claude + WebSearch/WebFetch: expand, verify, find current facts, cite;
                  write atomized facts to the wiki + reuse prior ones (§8.5)
 4. OUTLINE       Narrative arc with a FRONT-LOADED hook (§8.1); pull operator takes + prior
                  facts from the wiki; assign an energy/cut-density curve per beat; size to --min-length (§7)
 5. SCRIPT        Per-scene voice-over + on-screen visual direction; optional operator voice
                  interview → operator-take nodes (§8.5)   ── [optional gate: review script]
 6. NARRATE       Kokoro TTS → per-scene WAV; loudness-normalized; concatenate w/ timing map
 7. ALIGN         Native forced alignment → word-level timestamps (alignment.json)
 8. DECK          Generate HTML/CSS deck: one section per scene, deterministic motion, themed;
                  embed source screenshots / generated diagrams (SVG/CSS); kinetic captions
 9. STORYBOARD    Timeline JSON: bind slide animations/reveals to word timestamps
10. RENDER        Headless-Chrome frame capture per aspect (fixed fps, virtual clock) → frames
11. MUX           ffmpeg (VideoToolbox): frames + narration (+ optional music bed) → MP4 per aspect;
                  loudnorm, bt709 color tags, embed C2PA credentials; emit captions.srt/.vtt
12. QA            Static-frame vision check + motion/pacing check + hook-strength check (≤1 re-render)
13. PACKAGE       Write labeled output dir + versioned manifest.json (§9); mark per-aspect status
```

**Architectural rule (from council):** stages **1–5 and the QA judgment in 12 are the only LLM-in-the-loop steps.** Stages 6–11 are **pure Python, no Claude calls**, so a finished storyboard renders to MP4 unattended without stalling on a model turn. QA re-render is capped at **one** iteration.

---

## 6. Local toolchain (the corrected "free stack")

**Target machine (verified by the council's feasibility agent):** Apple **M3, 8 cores (4P+4E), 16 GB unified memory, Metal — no CUDA, no discrete VRAM.** Budget against **unified memory**, not VRAM, and **serialize** the memory-heavy stages (don't run Kokoro + Chrome capture + ffmpeg concurrently).

| Capability | Tool | License | Status / note |
|---|---|---|---|
| LLM (research, script, deck code, QA judgment) | **Claude Code** (subscription) | — | Bounded to generation stages only (§5) |
| Web research | WebSearch / WebFetch | — | Current facts, source-finding, verification |
| PDF/text ingestion | PyMuPDF, readability-lxml | open | Text + figure extraction |
| Source screenshots | Playwright (URLs) / PyMuPDF raster (PDF) | open | **Playwright not yet installed** — add to setup |
| **Text-to-speech** | **Kokoro-82M** | Apache-2.0 | **Installed (0.9.4)**; benchmarked 53 s audio in 8.2 s (RTF ≈0.16×). Not a bottleneck. |
| Pronunciation control | misaki phoneme overrides + normalization lexicon | open | **Not SSML.** Maintain a jargon/acronym lexicon as a project asset (R3). |
| **Word-level timing** | **torchaudio `forced_align` (wav2vec2 CTC)** *or* openai-whisper/mlx-whisper word timestamps | BSD/MIT | **Apple-Silicon-native.** Narration text is known → true forced alignment, CPU/MPS. **Replaces WhisperX.** |
| **HTML→video render** | Headless Chrome frame capture + ffmpeg; **owned Playwright-capture path preferred** over niche HyperFrames (bus-factor, R6) | open | Isolated behind a narrow interface (timeline+deck+aspect → frames) |
| Diagrams | CSS/SVG, optional Mermaid, D3 (deterministic only) | open | Programmatic, animatable, on-brand |
| Background music | Vetted royalty-free local library | varies | **Default ON (low bed) for 9:16/platform presets; OFF for 16:9/deck.** Provenance recorded in manifest (R5). |
| Mux / encode | **ffmpeg 8.1** (`h264_videotoolbox`, `aac_at`) | LGPL/GPL | **Installed**, hardware-accelerated. Pin `loudnorm I=-14`, `bt709` tags. |
| Captions sidecar | SRT/VTT generated from `alignment.json` | — | Free accessibility + retention; referenced in manifest |

**Missing media-quality steps the council flagged (now required, §11 Phase 0/1):** (1) **bundle/register deck fonts** for headless Chrome or frames render in fallback fonts; (2) **ffmpeg `loudnorm` I=-14 TP=-1.5** on narration; (3) **explicit `bt709` color tags** (`-colorspace/-color_primaries/-color_trc bt709`, range decided) to avoid platform re-encode shifts; (4) **emit `captions.srt`/`.vtt`** and reference them in the manifest.

---

## 7. Minimum-length targeting (feature spec, G6)

When `--min-length N` is set:

1. **Estimate** spoken duration from word count (≈150 wpm baseline), refined after the first real Kokoro pass.
2. If under target, **deepen, don't pad.** Expansion moves, in priority order: concrete example/mini-case → "why it matters"/counterintuitive angle → historical/comparative aside → recap/payoff beat → expand a diagram into a step-by-step build.
3. **Depth-vs-padding gate (council):** each *added* beat must introduce **a new sourced claim or a distinct example** (tie to R7 citations), not restate an existing point. QA rejects verbal padding (restating/hedging/throat-clearing), not just audio silence.
4. **Re-estimate after real narration** (alignment gives true duration).
5. **Bounded loop (council):** at most **2 deepen-and-renarrate cycles**, then accept best-effort and record a `length_warning` in the manifest. Each cycle re-runs Kokoro+align (the expensive part), so the cap keeps cost predictable.
6. **Overshoot/trim policy:** symmetric ceiling at `--max-length` (default = min × 1.5). When over max after expansion, trim lowest-priority beats first (asides → recaps), never core or hook.

Platform presets bundle floors (e.g. `--platform tiktok-eligible-length` ⇒ min 60 s, 9:16, safe-area captions) as **user-chosen strategy**, not the tool's opinion.

---

## 8. Visual quality bar (G3) — expanded after council

"Visually dynamic" is the highest-risk requirement. The council's verdict: the template-library + static-frame-QA approach is a **competence floor, not a competitiveness ceiling**. The additions below close that gap.

### 8.1 The hook (first ~2 seconds) — now first-class
On vertical surfaces the opening decides reach. Requirements:
- A library of **5–8 hook archetypes** (bold claim, question, surprising stat, "you've been doing X wrong", visual reveal); the SCRIPT stage must select one.
- **Hard rule:** frames 0–15 carry large on-screen text **+ a motion element + the payoff**, with **no logo/title-card throat-clearing** ("In this video…").
- **Cold open** for 9:16 — skip the animated title slide; open on payoff or pattern-interrupt.
- **Hook strength is an explicit QA gate** (§5 stage 12), not a screenshot check.
- Optional `--hook-variants N`: re-render only the opening 2–4 s with different archetypes as separate manifest entries for cheap thumb-stop testing.

### 8.2 Motion, pacing & QA that sees motion
- **Per scene:** ≥1 motion element — never a static bullet list.
- **Motion/pacing QA (new):** operates on `timeline.json` and the rendered MP4 (sampled 2–4 fps), not just stills. Flags: held frame while narration continues ("visual dead air"), average shot length above a vertical-appropriate threshold (top Shorts cut every ~1.5–3 s), reveals slower than narration, uniform cut rhythm.
- **Energy curve:** OUTLINE/STORYBOARD assign target cut-density per beat (hot open → dense early → breathing-room mid → snappy close); pacing is designed, not an emergent byproduct of word counts.

### 8.3 Kinetic captions — specified, not "trivial"
A named template with its own motion timing: heavy sans weight, outline/shadow for legibility over any background, **per-word pop/scale-in with overshoot**, **active-word highlight** from theme tokens, and **platform safe-area anchoring** (above TikTok right-rail and bottom caption zones). "Word-synced" alone yields boring subtitles; the typographic treatment is the retention lever.

### 8.4 Transitions & continuity
A small **varied** set (cut, match-cut on a shared element, directional push tied to narrative movement) with rules for when each applies and an **anti-repetition constraint** (no identical transition more than N times consecutively — repetition is the strongest "templated" tell). Prefer morph/persist of shared elements over hard cuts for continuity.

### 8.5 Template *family*, not one look
Within-video consistency is right, but a daily channel from one theme + 7 templates produces a visually identical feed that reads as low-effort and depresses cold reach (and trips mass-production classifiers, R10). The library must be **a family of looks**: multiple theme presets (palette + type + motion personality), layout variants per template, topic-driven accents — selectable or rotated per video. **Phase 3 goal.**

### 8.6 Determinism by construction (render correctness)
All motion driven by **a single JS animation driver** advanced by **CDP virtual time** (`Emulation.setVirtualTimePolicy`); **raw CSS animations/transitions are forbidden on any captured element** (the compositor clock isn't cleanly steppable). Stub `Math.random` with a **seeded PRNG** at page init; intercept `Date.now`/`performance.now`. Templates are built deterministic-by-construction, not retrofitted (closes R9).

---

## 8.5 Atomized knowledge wiki (sourced content + operator voice)

A persistent, cross-run knowledge layer at the **project root (`wiki/`)**, separate from per-run `outputs/`. It does two jobs: (1) **avoid re-researching** — atomized sourced facts accumulate and are reused across videos, so the knowledge base compounds; (2) give the content a consistent **personal, human voice** by capturing the operator's own takes and reusing them.

**Storage model — hybrid (operator decision):**
- The **project-local wiki** holds sourced/topic content — portable with the skill, no external dependency.
- **Operator personal-voice takes ALSO append to the existing `talk-time` voice library**, so the operator's voice is captured once and reused across *all* their routines, not just this skill.
- *Integration point (rule 1/4): confirm the `talk-time` library's actual storage path/format before wiring the mirror — do not assume it.*

**Node types** (one fact per node; immutable sources; simple YAML frontmatter + provenance, echoing the machine's `atomize` pattern but self-contained):
- `source` — an ingested document/URL/screenshot; the immutable provenance root.
- `source-fact` — one atomized claim `derived_from` a `source`, carrying citation + confidence.
- `topic` — a subject hub linking related facts and takes.
- `operator-take` — the operator's opinion/angle/anecdote on a topic, captured via Q&A; adds human voice. Mirrored to the talk-time library.

Frontmatter: `name`, `type`, `topic`, `source`/`derived_from`, `confidence`, `created`. Body: the fact/take, linking related nodes by name.

**Retrieval — simplest first (rule 2):** a grep-able `wiki/INDEX.md` + topic-tagged filenames; lookup by topic/slug. **No embeddings/semantic search** until proven necessary — flagged as a possible later enhancement, not built now.

**When operator questions happen:** opt-in via `--interview` (or offered at the post-script checkpoint). The skill asks **1–3 *targeted*** questions only where a personal take would materially improve the piece (a stance, an anecdote, a contrarian angle) — it does **not** pester on every run. Answers become `operator-take` nodes locally **and** append to the talk-time library.

**Provenance integrity:** every `source-fact` traces to a `source`; min-length expansions (§7) prefer wiki-sourced facts over invention (ties to R7). Stale/low-confidence facts are surfaced, not silently reused.

---

## 9. Output contract (G4, G7)

```
outputs/<YYYY-MM-DD>_<slug>/
  manifest.json            # versioned, machine-readable (below)
  run.log                  # per-stage structured log; run ID
  logs/<stage>.stderr      # captured tool stderr per stage
  state.json               # per-stage success markers + input hashes (resumability)
  deck/
    index.html             # standalone, openable deck (reusable artifact)
    assets/                # css, js, fonts, images, screenshots, svg
  script/  script.md  narration.txt
  audio/   narration.wav   alignment.json
  captions/ captions.srt   captions.vtt
  storyboard/ timeline.json
  video/   explainer_9x16.mp4  explainer_16x9.mp4  explainer_4x5.mp4  ...
  thumbnails/ cover_9x16.png  ...
  sources/  <captured material, screenshots, citations.json>
  frames/  <TRANSIENT — deleted after successful mux unless --keep-frames>
```

### Manifest contract (versioned, two-sided)
`manifest.json` carries `schema_version` and is a **shared, versioned contract**, not a one-way dump. Fields:
- **Core:** title, summary, language, voice, durations, source citations.
- **Status (council):** `ready_for_post` (bool) + **per-aspect status map** — never silently mark a partial render ready; partial → `ready_for_post:false`. Plus `length_warning` if min-length unmet.
- **AI disclosure / provenance (now mandatory, council + EU AI Act Art. 50 from Aug 2026):** `ai_disclosure: { ai_generated_audio:true, ai_generated_visuals:true, recommended_label, c2pa_embedded:bool }`. **C2PA Content Credentials embedded in the MP4** during MUX (TikTok auto-reads C2PA; proactive labeling correlates with far lower removal rates). User-overridable for the meaningful-human-review exemption.
- **Per-platform object (council — a poster can't post well without these):** for each destination `{ title?, caption, hashtags[], first_comment?, mentions?, link_placement: 'body'|'first_comment'|'none', char_budget, primary_asset: 'video'|'carousel'|'text+clip', aspect }`. Caption variants tuned to each platform's fold length and hashtag cap.

**Boundary:** this tool's responsibility ends at writing this directory. A small **`blotato-crosspost` adapter that reads `manifest.json`** is an explicit Phase 5 deliverable — the current skill is conversational/carousel-oriented and has **no manifest ingest path**, so "zero manual fixup" is a *future* state, not a present one (council, high). Round-trip validated with a real blotato dry-run in Phase 5.

---

## 10. Interface (skill UX)

- **Invocation:** `/explainer <topic | file | url> [flags]`
- **Key flags:** `--min-length`, `--max-length`, `--aspect 16:9|9:16|4:5|1:1` (repeatable), `--platform <preset>`, `--voice <kokoro-voice>`, `--theme <name>`, `--music on|off`, `--source <path|url>`, `--deck-only`, `--hook-variants N`, `--interview` (opt-in operator voice Q&A → wiki + talk-time, §8.5), `--draft` (480p fast preview), `--yes` (skip gates for unattended), `--only-stage`/`--from-stage` (debug), `--keep-frames`.
- **Confirmation gates (council — clarified):** (1) cheap pre-render gate confirms arc, target length, aspect(s); (2) **optional post-SCRIPT / pre-NARRATE checkpoint** lets the user catch factual/tone issues while edits are still text-only and cheap (re-narration is the costly thing). Both opt-out via `--yes`; `--draft` short-circuits gate 1.
- **`--deck-only` contract (council):** skips NARRATE/ALIGN; deck reveal timing becomes **click-advance / self-advancing** rather than word-bound; `--min-length` is ignored (no spoken duration). Stated explicitly so the "first-class independent deck" claim (G4) is honest about what drives its motion.
- **Determinism / resumability:** see §12.

---

## 11. Build phases (roadmap)

- **Phase 0 — Spike (prove the seam) + gates.** Hand-written 3-slide HTML deck → Kokoro narration (loudnorm) → **native forced alignment** → frame capture (fixed fps, virtual clock) → ffmpeg VideoToolbox mux → SRT/VTT. **Validate as gates:** measured render-time budget per aspect; peak unified-memory under serialized stages; a jargon-heavy paragraph through the pronunciation lexicon; HyperFrames-vs-owned-Playwright decided on measured fps + maintenance risk. *No Claude generation yet.*
- **Phase 1 — Skill skeleton (9:16).** INTAKE→RESEARCH→SCRIPT→DECK→RENDER for one aspect, fixed theme, topic-only; hook archetypes + kinetic captions in from the start; **wiki: `source`/`source-fact` capture + reuse (§8.5)**.
- **Phase 2 — Source ingestion + screenshots.** PDF/URL ingestion, figure capture, citations. **Acceptance demo: one source-driven 16:9/4:5 run (S2)** — the ingestion differentiator must not lag just because 9:16 is the optimized aspect.
- **Phase 3 — Template *family* + motion/pacing QA loop.** Multi-theme/layout variation, transitions, self-inspection (static + motion); **wiki: operator `--interview` + talk-time voice-library sync (§8.5)**.
- **Phase 4 — Multi-aspect + per-platform presets (safe zones) + bounded min-length engine.**
- **Phase 5 — Manifest (AI-disclosure/C2PA) + blotato adapter + dry-run round-trip; optional music beat-sync.**

Each phase ends with a runnable artifact. Ship Phase 0–1 before investing in the template family.

---

## 12. Operations: dependencies, resumability, observability, testing (new — from Ops lens)

### 12.1 Dependency & environment
- Single environment manager — **`uv` with a checked-in lockfile** pinning exact versions of every Python dep **including torch**.
- **Playwright:** pinned package **+ explicit `playwright install chromium`** with the Chromium revision recorded.
- **ffmpeg:** pin the exact build (e.g. Homebrew formula version) and required encoders (`h264_videotoolbox`, `aac_at`/`libx264` fallback).
- **Model manifest:** Kokoro checkpoint + alignment-model versions with **SHA + source URL**; a one-time `setup` helper downloads and caches them to a known path.
- **Explicit Apple-Silicon/MPS execution path** stated, with CPU fallback. espeak-ng/phonemizer (Kokoro's system dep) called out as a cross-platform footgun to pin.

### 12.2 Resumability that is *correct*, not just asserted
File existence ≠ stage success (a killed render leaves a truncated MP4; an interrupted capture leaves a half-full frames dir). Therefore:
- **Per-stage success marker** written **only on fully-flushed completion**, carrying a **hash of that stage's inputs** (upstream artifacts + relevant flags).
- **Atomic writes:** stage writes to a temp path and **renames on success** — a killed stage never leaves a poisoned artifact.
- **Invalidation:** a stage is "complete" only if its marker exists **and** the input hash matches; otherwise it and **everything downstream** re-runs (editing the script invalidates narrate→align→storyboard→render).

### 12.3 Observability
- Every run gets a **run ID**; a structured `run.log` (stage, start/end, exit status, key params) plus per-stage `logs/<stage>.stderr` (ffmpeg/Chromium fail cryptically — capture their stderr).
- **`--only-stage` / `--from-stage`** so debugging stage 10 never requires re-running 1–9. Each Python helper is independently runnable by absolute path (also satisfies the CLAUDE.md shell-discipline rules).

### 12.4 Test strategy (non-deterministic pipeline)
No golden-file equality on the MP4. Instead, layered:
1. **Contract/schema tests** on every inter-stage JSON (highest leverage; pairs with input-hash invalidation).
2. **Deterministic unit tests** on fixed-input seams (given a fixed WAV → alignment shape/monotonicity; given timeline+frames → mux duration/stream layout; manifest schema validation).
3. **Invariant tests**, not exact match: video duration within tolerance of narration; frame count ≈ fps×duration; no dead-air gaps > N ms; every scene ≥1 motion element.
4. **One tiny end-to-end smoke fixture** (3 hardcoded slides, short script, draft res) using cached TTS/align fixtures rather than live model calls.

### 12.5 Concurrency & disk discipline
- **All parallelism lives inside synchronous Python helpers** (a worker pool over frame ranges/aspects that blocks until done and returns an exit code). The orchestrating skill calls **one synchronous command per render stage** — no shell backgrounding, no polling (honors CLAUDE.md).
- **Artifact lifecycle:** durable = `deck/ video/ manifest.json script/ sources/ captions/`; transient = `frames/`, per-scene WAV chunks. **Delete frame dirs after a successful mux** (`--keep-frames` to retain). Document approximate **disk-per-run** (a 90 s 1080p 30 fps capture ≈ ~2,700 PNGs *per aspect*).

---

## 13. Distribution & platform fit (expanded — from Distribution lens)

- **Per-platform preset table** (replaces the coarse 16:9/9:16 mapping) carrying resolution, aspect, and **explicit safe-zone insets** (top/bottom/sides). **4:5 is first-class** (highest in-feed engagement on LinkedIn and Instagram in 2026; 16:9 plays smaller and underperforms in-feed). Caption/kinetic-text placement is a function of the platform safe-zone, not a global center rule.
- **Threads fix:** not a 9:16-video clone of TikTok — it's text-first (native video ~5-min cap, weaker vertical reach). Its manifest entry should prefer **deck-as-carousel or text-hook + short clip**, with its own caption variant.
- **Deck-as-artifact** (LinkedIn document posts, blog embeds, talks) is arguably the **most defensible channel** — it sidesteps video-feed originality penalties entirely. Lean into it.

---

## 14. Risks & open questions

| # | Risk / question | Mitigation / note |
|---|---|---|
| R1 | **Render time** dominates on the 4P+4E M3 (no discrete GPU); ~30–150 ms/frame at 1080p. | Fix capture fps (24/30 default; 60 only for kinetic Shorts); render-time budget is a **Phase-0 gate**; parallel frame ranges inside one synchronous helper; `--draft` 480p. |
| R2 | **Visual quality** from generated HTML. | Template *family* + hook spec + **motion/pacing QA** (§8); freestyle HTML is the exception. |
| R3 | **Kokoro prosody** on jargon/acronyms. **Not** SSML-controllable. | Normalization + **misaki phoneme-override lexicon** as a maintained asset; validate in Phase 0. |
| R4 | **Aligner on Apple Silicon.** WhisperX/ctranslate2 has no Metal backend. | **Default to torchaudio `forced_align` / openai-/mlx-whisper word timestamps**; aeneas as line-level fallback. WhisperX dropped as default. |
| R5 | **Music licensing.** | Vetted royalty-free local library; **default ON (low bed) for 9:16**, OFF for 16:9/deck; provenance in manifest; optional **beat-sync** of reveals/cuts using the timestamp infra. |
| R6 | **Render engine:** HyperFrames (niche, bus-factor) vs **owned Playwright capture**. | Decide on measured fps **and maintenance risk**; lean to the owned path; isolate stage 10 behind a narrow interface so it's swappable. |
| R7 | **Factual accuracy** when expanding for min-length. | Research cites; QA claim-check; each added beat needs a **new sourced claim**, not invention. |
| R8 | **Scope creep toward posting.** | Hard boundary: write the labeled dir + manifest, stop. |
| R9 | **Animation determinism** under frame capture. | Single JS driver + **CDP virtual time + seeded RNG**; **forbid CSS animations on captured elements** (§8.6). |
| **R10** | **Mass-production / "inauthentic content" enforcement (NEW, high).** A template-driven auto-explainer factory with one voice + one look is the exact signature YouTube's 2025 "inauthentic content" policy and TikTok's synthetic-media enforcement target. | **Reframe from "headless factory" to low-volume, human-in-the-loop, high-variation.** Build genuine per-video variation (§8.5), cap recommended cadence per channel, lean on deck/long-form surfaces, add an **originality/effort self-check** to QA. |
| R11 | **LLM-in-the-loop fragility** (subscription rate limits / session interruptions stalling a render). | **Confine Claude to generation stages; media path is pure Python, zero Claude turns** (§5); cap QA re-render to 1. |
| R12 | **Dependency rot** across 4–6 fast-moving native deps. | §12.1 lockfile + model manifest + pinned ffmpeg/Chromium. |
| R13 | **Wiki provenance/staleness & talk-time coupling.** Reused facts can go stale; the talk-time library path/format is an assumed integration. | Every `source-fact` traces to a `source` with confidence; surface stale/low-confidence rather than reuse silently; **confirm talk-time storage before wiring** (don't assume) — §8.5. |

---

## 15. Success criteria

- A single `/explainer` invocation on a topic produces an openable HTML deck **and** a platform-correct MP4 with synced narration and kinetic captions, **with no paid API calls**, on the M3 iMac — and **defined behavior on failure**, not just the happy path.
- The deterministic media path (narrate→align→render→mux) runs **with zero Claude turns** once the storyboard exists.
- Output dir + **versioned manifest with AI-disclosure/C2PA and per-platform fields** is consumable by the Phase-5 blotato adapter, validated by a real dry-run.
- `--min-length` reliably hits the floor through **sourced depth**, in a bounded loop, never padding.
- The deck stands alone as a presentable artifact; re-running to tweak it requires **no re-narration** (correct, hash-based resumability).
- *(Strategy note, not a tool guarantee):* eligible length is **one** gate among follower/view/originality gates — the deepen-don't-pad engine is sold as a **watch-time/quality** mechanism, not a monetization unlock.

---

## 16. Council review — synthesis & changelog

A 5-lens council (local-tooling feasibility · visual quality/engagement · product scope/UX · distribution/platform fit · ops/maintainability) pressure-tested v0.1. Verdict: **architecture sound, the audio-before-visuals spine and artifact-on-disk staging are keepers — but v0.1 was written for the wrong machine, under-specified the render/determinism path, treated engagement as a rendering-quality problem, and asserted a manifest handoff its consumer can't parse.**

**Cross-cutting findings (multiple lenses agreed) → changes made:**
1. **Hardware/aligner mismatch** (feasibility): M3/16 GB/no-CUDA; WhisperX not viable → **§6/R4 rewritten** to native forced alignment; unified-memory budgeting + serialized stages.
2. **Manifest is one-sided & non-compliant** (product + distribution): blotato can't read it; no AI-disclosure → **§9 manifest rewritten** (versioned, per-aspect status, AI-disclosure/C2PA, per-platform object; blotato adapter is a Phase-5 deliverable).
3. **Engagement ≠ static-frame quality** (visual + distribution): hook unspecified, QA blind to motion → **§8.1–8.2 added** (hook archetypes + hard rule + hook/motion QA).
4. **Mass-production risk** (distribution + visual): one look/voice trips classifiers and bores feeds → **R10 added**, §8.5 template *family*, reframed strategy to human-in-the-loop.
5. **LLM-in-the-loop must be bounded** (feasibility + ops): → **§5 rule** media path is pure Python; QA capped at 1 re-render (R11).
6. **Resumability correctness** (ops): file existence ≠ done → **§12.2** state markers + input-hash invalidation + atomic rename.

**Conflicts & the chair's calls:**
- **Music default:** v0.1 said OFF (licensing). Visual lens argued ON for vertical (engagement/beat-sync). **Resolved: default ON (low bed) for 9:16/platform presets, OFF for 16:9/deck** — engagement evidence wins for the surfaces where it matters, licensing caution retained (R5).
- **First aspect:** 9:16-first (roadmap) vs the stronger source-driven 16:9 demo (S2). **Resolved: keep 9:16-first, but make a 16:9/4:5 source-driven run the Phase-2 acceptance demo** so the ingestion differentiator doesn't lag.
- **Render engine:** speed/ease (HyperFrames) vs maintenance/bus-factor (owned Playwright). **Resolved: lean owned-Playwright, decide on measured fps + maintenance, isolate behind a swappable interface** (R6).

**Also added from single high-value findings:** missing media steps (fonts, loudnorm, bt709, SRT/VTT — §6); bounded min-length loop + depth-vs-padding gate (§7); failure/degradation behavior (§9 status map, §10 gates); kinetic-caption + transition specs (§8.3–8.4); per-platform safe-zone table + Threads fix + 4:5 (§13); dependency/observability/test sections (§12).

---

### v0.3 additions (operator-directed, post-council)
- **Decisions confirmed:** music = ON-low-bed for 9:16 / OFF for 16:9+deck (R5); render engine = owned Playwright capture (R6); confirmation gates = pre-render **+** optional post-script checkpoint (§10).
- **Atomized knowledge wiki (§8.5, new):** a persistent project-local `wiki/` of typed, provenance-carrying nodes (`source` / `source-fact` / `topic` / `operator-take`) that compounds sourced research across runs and captures the operator's personal voice via opt-in `--interview`. **Hybrid storage:** wiki is project-local; `operator-take` nodes also mirror to the existing `talk-time` voice library (path/format to be confirmed before wiring — R13). Threaded into the pipeline at stages 3–5; rolled out in Phase 1 (facts) and Phase 3 (operator interview + talk-time sync).

---

## 17. Recommendation (how to build this)

**Build it as a Claude Code skill that orchestrates pinned Python helpers, in this order, with the generation/media split as the central architectural rule.** Concretely:

1. **Do Phase 0 first and treat its three measurements as go/no-go gates:** (a) end-to-end seam on the real M3 with native forced alignment (not WhisperX), (b) measured render-time-per-aspect budget, (c) peak unified-memory under serialized stages. If render time is unacceptable, that's known before any generation code exists.
2. **Lock the seams before the intelligence:** versioned inter-stage JSON schemas + hash-based resumability + the manifest contract are the load-bearing structure; build them in Phase 0–1, not retrofitted.
3. **Confine Claude to stages 1–5 + one QA pass; make 6–11 pure Python.** This is what makes unattended rendering possible on a subscription and keeps the pipeline testable.
4. **Treat the hook and the template *family* as product features, not polish** — they are the difference between "clean corporate motion-graphics" and content that survives and retains on vertical feeds.
5. **Ship 9:16 end-to-end first; prove source-ingestion on a 16:9/4:5 run in Phase 2.**
6. **Keep the boundary hard:** write the labeled dir + compliant manifest and stop; the blotato adapter is the only posting-side code, and it's a thin Phase-5 reader.

Net: the original instinct — local, free, HTML-native, Remotion-free — is sound and the upstream architecture is worth borrowing. v0.2 corrects the machine assumptions, hardens the render/determinism path, makes the manifest a real compliant contract, and elevates engagement (hook/motion/variation) from an afterthought to a spec. That's the version worth building.

---

*End of v0.3. The three prior open decisions (music, render engine, gate placement) are now confirmed. Remaining to confirm during build: the `talk-time` library storage path/format before wiring the wiki mirror (R13).*
