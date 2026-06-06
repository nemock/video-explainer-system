# Deep-Dive Video Generator — Architecture Document (v2, post-council)

**Status:** Draft for review (architecture only — no code yet)
**Revision:** v2 — incorporates the council review (2026-06-04/05) and four locked product decisions.
**Companion doc:** [`PRD.md`](PRD.md)
**Lives in:** `/Volumes/Casima/claudeCode/explainer-system/deep-dive/` — a higher-level capability of the **explainer system**, built on the same engine (`/Users/davesaunders/myenv/bin/explainer`) as the short-form explainers.

> **Where this lives / scope:** the deep-dive generator is a **capability of the explainer system**, **brand-parameterized**, not tied to any one show. Its **primary instance is the operator's own Founders Who Finish (FWF)** videos (and The Build); other content projects — e.g. CIRCUMVENT/CVG — *may* also consume it. Every brand specific below (FWF theme, channel, sponsors) is the **FWF brand config**, not an assumption baked into the system.
>
> **Private config & voice governance.** Concrete FWF instance values (Blotato account/channel IDs, sponsor specifics, theme tokens, music) and the byline voice/editorial library live **privately** at `~/.claude/explainer-brands/dave-byline/` — NOT in this public repo. See §8.0 and `deep-dive-instance-config.md` there.

---

## 1. Purpose & design philosophy

The deep-dive system targets **20+ minute, three-act, human-narrated tutorial videos** for the FWF founder/builder audience. Rather than stretch the single-project short-form model to 20 minutes (a marathon recording session, a fragile single forced-alignment pass, one multi-thousand-frame render), the deep-dive system is an **orchestrator over many small `explainer` projects** plus an **assembly layer** that stitches them into one master film.

**Core principle: a deep-dive is a *program* composed of independently-rendered *segments*.**

```
[Cold open] → Act I → [FWF sponsor] → Act II → [The Build sponsor] → Act III → [Like & Subscribe CTA]
```

Each act is its own `explainer` project (`--voice-source operator`), recorded and rendered independently. The two sponsor interstitials and the CTA are **reusable, version-pinned assets recorded once** (face-to-camera video for the sponsors per D6; voice for the CTA). A final ffmpeg **assembly pass** conforms every segment to a strict format contract, concatenates them, lays down music, normalizes loudness, stitches captions with frame-exact offsets, and emits the master 16:9 film plus chapters.

This delivers the four properties the operator asked for:

1. **Staged, interactive recording** — record one act (or sub-segment), review, continue later. No marathon.
2. **Highly graphical** — reuses the deck/slide engine plus `ingest --url`/`--pdf` for real screenshots and figures.
3. **Minimal recurring burden** — sponsors + CTA are recorded once and reused; only act content is recorded per video.
4. **Compounding library** — research, assets, subjects, and narrative arcs accumulate across every video (§10).

### 0.1 Locked product decisions (this revision)

| # | Decision | Consequence |
|---|---|---|
| D1 | **Brand-parameterized; FWF is the primary instance** (not a CIRCUMVENT default) | Real FWF theme (purple/indigo/Montserrat), D-rocket + @davesaunders identity anchors (§17); brand config is swappable |
| D1a | **YouTube = the operator's personal channel + a NEW dedicated deep-dive series playlist** (account/playlist IDs in the private FWF config) | **LinkedIn dropped** for now (§13) |
| D2 | **Sponsor reads + CTA are operator-recorded, recorded once** (not TTS) | Kills the human→synthetic seam; near-eliminates synthetic-media exposure; version-pinned (§7). **Sponsors upgraded to face-cam video by D6.** |
| D3 | **Promo = short native snippets (<2 min) on X + TikTok + Instagram + Threads** (Blotato), pointing back to YouTube | The 20-min film exceeds X's 2-min cap, so the snippet/repurposing module is **core, not deferred** — it is the promo engine (§14). YouTube-Shorts top-of-funnel remains a later add. |
| D4 | **Central library = the shared `make_money/brain` cb vault** (resolved) | One content brain across FWF / personal / deep-dives / MedTech Monday / Founder Tip Tuesday / carousels. Per-video `research/` staging promotes up via `cb intake`. Not the cb *code* repo, not client vaults (§10) |
| D5 | **Deck/visual layer follows McKinsey-grade information-design**, adapted to FWF + motion | Action/"so-what" slide titles, one-message-per-slide, MECE structure, disciplined data-viz and visual hierarchy — rendered as dynamic animated FWF slides (§8.6, §17). Leverage the `mckinsey-presentations` skill's standards. |
| D6 | **Sponsor interstitials = iPad face-to-camera video**, composited ~80% (PiP) on the FWF branded background | Dave's real face adds authenticity; still recorded once + version-pinned. ffmpeg compositing, no new tools (§12.7). CTA optionally face-cam too. |
| D7 | **Adobe Stock** (operator subscription) is a licensed visual source — photo **and video** B-roll | The shot-list step proposes search prompts to review; downloaded assets are recorded in the brain (`source` node + `_attachments`) with the Adobe Stock license + asset ID (§8.1, §9, §10.1). |
| D8 | **YouTube competitive research at project start** — study the top-performing videos on the topic | WebSearch finds them; `yt-dlp` pulls title/description/view-count/**auto-transcript** (no video download). Reverse-engineer what's working → informs angle, title/thumbnail packaging, and gaps to beat. Stored as `source` nodes (web-snapshot/skill-output) in the brain (§10.1). |
| D9 | **Teach toward a transformative outcome, not for its own sake** | Every deep-dive declares the **viewer transformation/benefit** up front; the headline sells that benefit, not the topic. A required editorial element (§8.2, §8.5). |
| D10 | **Custom YouTube thumbnail**, generated per best practices | Default = an on-brand **composite** (FWF template + 3–5-word high-impact keyword text + operator selfie in a corner) — deterministic, no AI needed. Optional AI hero via the operator's Google "nano banana"/Gemini API or an interactive Gemini handoff. Uploaded as Blotato custom thumbnail (§12.5). |

---

## 2. What is reused vs. what is new

### Reused unchanged (the `explainer` engine)

| Capability | Subcommand | Role |
|---|---|---|
| Project scaffold | `scaffold --voice-source operator --aspect 16:9` | One project per act / interstitial |
| Human voiceover capture | `record` (browser teleprompter) | Operator records each act + the reusable interstitials |
| Narration + alignment | `narrate`, `align` | Word-level timing of recorded audio |
| Deck build / frame render / mux | `deck`, `render`, `mux` | JSON slides → streamed frames → segment MP4 |
| Manifest / QA | `manifest`, `qa`, `validate` | Per-segment readiness |
| Source ingestion | `ingest --url` / `--pdf` / `--full-page` | Web screenshots + PDF figures |
| Per-slide stills | `stills` | Thumbnail + clip source |
| Fact capture | `wiki source` / `wiki fact` | Local research-staging nodes; promoted to the brain via `cb intake` (§10) |
| Voice library | `talktime --tag fwf` | Draft scripts in the operator's voice |
| Blotato hand-off | `handoff` | Per-platform post spec (extended, §13) |

### New (this system's responsibilities)

- **Program orchestration & crash-safe state** (§5) — the `program-manifest.json` state machine: atomic writes, schema version, single-writer, intent-only, reconcile-against-disk.
- **Three-act content planning + retention/editorial layer** (§8) — throughline spine, open-loop/payoff ledger, editorial rubric, act-balance.
- **Operator-recorded interstitial library** (§7) — FWF + The Build sponsors (face-cam video, D6) + CTA — recorded once, version-pinned, integrity-checked.
- **Knowledge brain** (§10) — the shared `make_money/brain` cb vault; deep-dives promote into it and query from it (cross-format reuse).
- **Audio & music layer** (§11) — sponsor-break music, optional act bed, per-segment ducking + loudness.
- **Assembly / master render** (§12) — format-contract conform, concat, ffprobe-derived offsets, seam QA, master-integrity validation, packaging.
- **Long-form publishing** (§13) — FWF channel, hardened large-file upload, chapters, end screens/cards/playlists.
- **X promo (+ planned repurposing)** (§14).
- **Observability & ops** (§16) — build log, `status`/`doctor` command.

The engine has **no** concat/assemble/music/program command — those are net-new here.

---

## 3. The compositional model

A **segment** is the atomic unit: one `explainer` project rendering to one MP4 with captions + manifest. Kinds:

- **Act segment** — operator-narrated content. Acts are **split into ~60–90s sub-segments** that are the unit of recording, review, and re-record (§6) — a bad sentence re-shoots one sub-segment, not a 5-minute act. Sub-segment boundaries fall on **idea boundaries** (each a named teaching unit), so the alignment-reliability limit and pacing structure coincide (§8.4).
- **Interstitial segment** — a reusable, version-pinned operator-recorded asset: **face-to-camera video** for the FWF + The Build sponsors (D6, §7), voice (or face-cam) for the CTA.
- **Bumper (optional)** — short branded transition/chapter card; if used, every divider carries a forward-hook ("Act II — the part everyone gets wrong"), never a bare "Act II" exit ramp (§8.5).

A **program** is an ordered segment list plus global config (FWF brand, music, publish targets). Canonical order:

```
cold-open → act-1 → fwf-sponsor → act-2 → thebuild-sponsor → act-3 → cta
```

The **cold open is mandatory** (§8.5): a 10–20s hook stating the payoff/stakes and planting the primary open loop.

**Three acts is the default — and a deliberate fit.** The two internal seams (Act I→II and II→III) map 1:1 to the two sponsor properties (the FWF book after Act I, The Build after Act II), and it matches the proven play/infomercial 3-act arc. Act count is a **per-project parameter**, but 3 is the default *because* of that 2-sponsor fit — deviating means rethinking sponsor placement (there are only two sponsor properties). **Total length is not a hard constraint** — it follows the content (20+ min typical, ~24 min common). Balance profile in §8.4 (default narrative-weighted ~5 / ~13 / ~6).

**Acts ≠ sub-segments.** The viewer experiences exactly 3 acts. Each act is merely *recorded* in ~60–90s **sub-segments** — purely a production/alignment mechanic (§6) — that concatenate seamlessly into one continuous act. Sub-segments are invisible in the final film.

**Why per-segment projects:** bounded forced-alignment length, bounded render size, single-segment failure blast radius, naturally staged recording, and reusable interstitials.

---

## 4. Directory & artifact layout

**Repo-source vs operator-content split.** This dev repo (`explainer-system/`) tracks **only source** — the design docs here, and later the orchestrator code. **Operator content stays out of git** (matching the repo's existing `.gitignore` for `wiki/`, `outputs/`, brand assets). So `brand/`, `shared/` (interstitials + music), and `programs/` are operator-content (gitignored in-place, or rooted in the operator brand dir). The **central knowledge brain is a separate cb vault** — `make_money/brain` (§10) — **not under `deep-dive/` at all**. Only `ARCHITECTURE.md`/`PRD.md` (and future code) are committed.

```
deep-dive/
├── ARCHITECTURE.md  ·  PRD.md              # ← committed (source)
│   ── everything below is operator-content, NOT committed ──
├── brand/                                  # FWF brand spec (§17): theme tokens, logo/D-rocket, fonts, handle/home, voice profile
│   (no local wiki — the central knowledge brain is the shared cb vault make_money/brain, §10)
├── shared/
│   ├── interstitials/                      # operator-recorded (face-cam video, D6), version-pinned (§7)
│   │   ├── fwf-sponsor/ · thebuild-sponsor/ · like-subscribe-cta/
│   │   └── interstitial-registry.json      # version → {mp4, hash, ffprobe-format, offer-facts, verified}
│   └── music/ (sponsor logo · act-bed/ · LICENSES.md)   # supplied tracks live here (or in the operator brand dir)
└── programs/
    └── 2026-06-1x_<slug>/
        ├── program-manifest.json           # crash-safe state machine (§5)
        ├── program-manifest.json.bak  ·  .history/   # backups + transition journal
        ├── build-log.jsonl                 # append-only observability (§16)
        ├── content-plan.md                 # throughline spine, open-loops, rubric, shot list (§8)
        ├── research/                        # staging area; durable nodes promoted to the central brain on completion (§10.3)
        ├── segments/  (cold-open/ act-1/ … each an explainer project; acts hold sub-segments)
        ├── promo/  (x-promos.json · clip_16x9.mp4 · [future] shorts/)
        ├── packaging/ (title-variants.md · thumbnail.png + concepts)
        ├── master/ (deepdive_16x9.mp4 · captions.srt/.vtt · chapters.txt)
        └── publish/ (handoff.json · publish-log.md)
```

---

## 5. Program manifest & state machine (crash-safe)

`program-manifest.json` is the single source of truth for a resumable, multi-day, multi-session build. The council flagged the original as a data-loss path; v2 hardens it.

**Crash-safety & integrity:**
- **Atomic writes** — write to `.tmp`, `fsync`, `os.replace`; keep a `.bak` of the prior good version and an append-only transition journal in `.history/` so a corrupt write is reconstructable.
- **`schema_version`** top-level field + an explicit migration/validation path (tooling migrates or refuses older versions).
- **Single-writer** — only the orchestrator writes the manifest. Parallel segment renders report status by writing their **own per-segment status file**, which the orchestrator folds in (no concurrent clobbering).
- **Intent-only** — the manifest stores **status/intent**, never authoritative timing. All durations/offsets/fps/sample-rate are **derived fresh via ffprobe at assembly** (§12.3) and cached with a content hash (mtime+size or sha) of the source MP4, so a re-recorded act can't silently desync captions/chapters.
- **Reconcile-against-disk** — on startup/resume, validate the manifest parses and matches reality (does `segments/act-1/` actually hold a valid MP4 if status says `rendered`?); demote any status the artifacts don't support and flag drift (`doctor`, §16).

**Segment lifecycle** (forward *and* reject paths):

```
planned → scripted → recorded → rendered → reviewed(approved | rejected) → [program] assembled → reviewed-film → publishable → published
                                    └── failed (crash/QA) ──┐
rejected / failed → (re-record or re-render the affected sub-segment) ──┘
```

- `rendered` ≠ done. Assembly gates on **`approved`** (§6), not merely "an MP4 exists."
- A `review_status` + `review_notes` field per segment (and per sub-segment) captures the operator's verdict.
- Crashes transition into `failed` via heartbeat/lock detection (an owner-PID-dead stage is unambiguously "crashed mid-stage," not ambiguously "in progress").

---

## 6. Staged interactive recording workflow

The heart of the operator experience — never one 20-minute take, and never re-shoot a whole act for one sentence.

```
For each act, for each ~60–90s sub-segment:
  1. Author the sub-segment: script + deck slides (script in operator voice via `talktime`; slides per the shot list).
  2. Scaffold the sub-segment project (--voice-source operator --aspect 16:9, FWF brand).
  3. RECORD: `explainer record` teleprompter shows just this sub-segment; the prompt also surfaces the
     CLOSING ENERGY/TONE of the previous sub-segment and the designed hand-off line, so multi-session
     takes stay tonally continuous (§8.2).
  4. narrate + align → ALIGNMENT-CONFIDENCE GATE: threshold words-aligned ratio / max inter-word gap.
     If it fails (ad-lib, dropped phrase, long silence), surface the exact timestamps in the review pause;
     a manual transcript-correction path handles intentional ad-libs. 'rendered' requires passing this gate.
  5. deck → render → mux → qa  → sub-segment MP4 + captions
  6. REVIEW: operator approves/rejects this ~90s sub-segment (auto-flagged low-confidence takes first);
     a 'jump-to-cut' index from the alignment data lets them spot-check rather than watch end-to-end.
  7. Mark approved/rejected + notes in the manifest. PAUSE. Continue now or in a later session.
```

Because each sub-segment is independent, the operator can re-record one sub-segment without touching its neighbors, record out of order, and resume across days — all driven by the manifest. **Whole-film review** (§8.3) is a separate, later gate after assembly.

---

## 7. Operator-recorded interstitial library (recorded once, reused)

Three reusable assets under `shared/interstitials/`, each recorded **once** (face-to-camera video for the two sponsors per D6; voice — or optionally face-cam — for the CTA), rendered to a pinned MP4, and registered with integrity metadata. They are **not** rebuilt per video.

| Asset | Placement | Content | Length |
|---|---|---|---|
| `fwf-sponsor` | After Act I | "…my book **Founders Who Finish**" — book cover, one-line pitch, on-screen **`davesaunders.net/book`** | 12–20s |
| `thebuild-sponsor` | After Act II | "**The Build**" — pitch + on-screen **`davesaunders.net/free-trial`**; **price stays in the description, not the baked asset** (see below) | 15–25s |
| `like-subscribe-cta` | End of Act III | "If this helped, hit like and subscribe." In the operator's voice | 6–10s |

URLs: book = `http://davesaunders.net/book` · The Build = `https://davesaunders.net/free-trial`. **The Build offer = $14.95 to start, then $79/month, plus over $1,500 in free bonuses** — this goes in the **YouTube description**, not the spoken/on-screen interstitial (evergreen copy only, e.g. "start your free trial — link below"), so an offer change never strands an immutable master.

**Recording format (D6 — face-to-camera video).** The two sponsor interstitials are **real video of Dave talking to camera**, recorded on his **iPad** and **composited at ~80% onto the FWF branded background** (PiP), rather than voice-over-graphics. His face on screen is the authenticity move. They are still **recorded once, version-pinned, and reused** (the build-once model is unchanged — just video now). The CTA can optionally be face-cam too, or stay operator-voiced. Compositing recipe + tooling in §12.7. iPad clips conform to the master-format contract (§12.1) like any other segment.

**Self-sponsor framing:** because these are the operator's *own* properties, use a soft first-person frame ("Quick aside — if you want the deeper playbook, my book…") rather than third-party "brought to you by," and let the act script carry a one-line spoken **bridge into and out of** each break so the operator's voice brackets the interstitial.

**Offer-figure indirection (brand-trust + immutability):** do **not** bake a specific price/bonus ("$14.96 / $1,500") into the spoken+on-screen asset — published masters are immutable and an evergreen wrong price is a trust/advertising-accuracy hazard across dozens of videos. The asset speaks evergreen copy ("a special offer for viewers — link below"); the exact figure lives in the **YouTube description / landing page**, editable without re-rendering.

**Registry integrity** (`interstitial-registry.json`): per version, store `{mp4_path, content_hash, ffprobe_format (res/fps/sample-rate/codec/channels), offer_facts (structured + verified flag), created}`. At assembly, verify the pinned MP4 **exists, matches its hash, and conforms to the master-format contract** (§12.1) before concat; fail loudly and early otherwise. Never mutate a published version in place — only add new versions. Re-render when the format contract changes (e.g. after an OS/ffmpeg upgrade) so a stale encode never enters a `-c copy` concat.

**Sponsor-break music** (operator-supplied, licensed) is mixed under each interstitial's voice for a recognizable audio signature (§11).

---

## 8. Research, content planning & the retention/editorial layer

The council's central editorial finding: the original design optimized production and ignored **retention** — the hardest part of 20-min video. v2 makes retention and editorial quality first-class.

### 8.0 Voice & editorial governance (inherited from the byline library)
The deep-dive is a **new format under Dave's byline**, so it inherits the existing byline governance rather than reinventing it. That library lives privately at `~/.claude/explainer-brands/dave-byline/`:
- **`editorial_thesis.md` (Part I)** — the brand thesis, the anti-"startup theater" stance, the **6 audience archetypes** (these *are* the deep-dive's audience), and **4 named frameworks** (order-of-operations test, walk-away condition, the three numbers, foundational-hire signal) — reusable brand-level IP a deep-dive can build a teaching arc around. The deep-dive must write its **own Part II** (format application) inheriting Part I unchanged.
- **`voice_brand.md` + a new deep-dive format voice file** — stance, opening cadence ("open in the action"), rhetorical moves. `talktime --tag fwf` surfaces the same takes; the deep-dive voice file inherits `voice_brand.md` (it does not duplicate it).
- **`content_workbook.md` story bank** — Dave's verified real anecdotes (Toxic Investor, Boondoggle Trips, Bell Labs/Apple AirPort, etc.) are reusable scar/vulnerability material for act narration; the words-to-avoid list and 11-point arc inform script drafting.
- **`research_sources.md`** — the curated source roster feeds **library-first research** (§8.1) and topic discovery.
- **`humanizer` skill is prose ground-truth.** Every script bound for the voiceover runs through `humanizer`; for this **spoken** format, run humanizer on the script as written, then a separate **spoken-cadence pass** (never pre-shorten before humanizer, never skip it). This is a hard step in the script stage (§6/§8.2).

### 8.1 Research (library-first)
0. **Library-first lookup** — before new research, query the brain (§10) for existing sources/facts/assets and prior topic coverage (produced-piece `source` nodes by topic) — reuse, avoid repetition, surface rights-clean assets we already own.
1. **Topic intake** — direct topic, or read the **content guide** (byline `editorial_thesis.md` + The Build theme calendar + `research_sources.md`, in the byline library) and propose candidates, cross-checked against the brain's covered topics.
2. **Research** — WebSearch/WebFetch; every claim becomes a sourced fact in the local `research/` staging (no unsourced claims). Reddit/LinkedIn/Substack MCP for audience/primary research. **Promote** reusable, rights-clean sources/facts/assets into the brain (§10.3).
2b. **YouTube competitive scan (D8)** — find the **top-performing videos on the topic** (WebSearch), then `yt-dlp --skip-download` to pull each one's **title, description, view count, and auto-transcript** (no video download). Analyze for *why they worked*: title/thumbnail patterns, hook structure, angle, what they cover vs skip, comment themes. Output = a short "what's working / gaps to beat" brief that informs the angle, the **transformative-outcome framing** (§8.2), and the **packaging** (§12.5). Captured as `source` nodes (web-snapshot/skill-output, §10.1) so the intel compounds across videos. *(Learn from winners; don't clone — differentiate on the operator's scar-tested, framework-driven angle.)*
3. **Voice** — `talktime --tag fwf` (tag is a **per-program parameter**, multi-tag allowed) surfaces the operator's authentic takes so scripts are personal, not narrated Wikipedia.
4. **Visual shot list** — per beat, choose the visual from three sources: (a) **branded graphic** (stat/compare/diagram/steps), (b) **web asset** (`ingest --url`/`--pdf`, editorial + attribution), or (c) **Adobe Stock** photo/video B-roll (D7). For (c), the planner emits **suggested Adobe Stock search prompts** (keywords + intended beat + photo-vs-video) as a reviewable list; Dave searches `stock.adobe.com`, downloads acceptable assets (his subscription = properly licensed), and they're recorded in the brain (`source` node + `_attachments`, §10.1) with the Adobe Stock license + asset ID. Every shot-list entry records source, intended slide, attribution, and rights status.

### 8.2 Transformative outcome + throughline spine (authored before any recording)
**Transformative outcome first (D9).** Before structure, name the **transformation**: what can the viewer *do, decide, or see differently* after watching that they couldn't before? Deep-dives teach toward an **outcome**, not for teaching's sake — the value is the change in the viewer, and the **headline sells that benefit**, not the topic. (E.g. not "What is a pitch deck" but "build the right company by pressure-testing it on ten slides before you waste a year.") The competitive scan (§8.1.2b) and the byline thesis (§8.0: practical, framework-driven, forward motion) both feed this. Record the transformation + the one-line benefit promise at the top of `content-plan.md`; the cold open and headline derive from it.

**Throughline spine.**
A `content-plan.md` spine: the one-sentence **thesis**; **2–3 open loops** (questions/promises planted in Act I); and the explicit **callback/hand-off line** that closes each act/sub-segment and opens the next — so seams between independently-recorded acts are *designed*, not emergent. Each act's recording prompt references the prior sub-segment's closing energy + hand-off line (§6.3).

### 8.3 Retention mechanics
- **Mandatory cold open** (10–20s) stating payoff/stakes + the primary open loop; ideally auto-cut from the genuinely strongest tagged line across acts.
- **Open-loop / payoff ledger** — every planted loop has an id and a **tagged payoff beat**; the planner warns on dangling loops (set up, never paid off — the most common long-form failure).
- **Re-hook cadence** — a mini-hook/open loop at least every ~90s of act time.
- **Pre-sponsor tease** — a "coming up after this" line authored into the act so the break is a cliffhanger, not an exit ramp.
- **Whole-film review gate** — a manifest state (`assembled → reviewed-film → publishable`) where the operator watches the master end-to-end for pacing, seams, and broken callbacks before publish.

### 8.4 Act balance & sub-segmenting (editorial, not just technical)
**Act-balance is a per-project choice, defaulting to narrative-weighting** — **Act I ~15–20% (setup) · Act II ~55–60% (the teaching bulk) · Act III ~20–25% (payoff)**, i.e. roughly **~5 / ~13 / ~6 min** on a ~24-min piece. The two sponsor breaks fall at the **natural narrative seams** (after the short setup, then after the long core) — breaks at story pauses, which is the point of the act structure, not at arbitrary time marks. Even-ish thirds (~8/8/8) stays available for a more infomercial cadence. **Total length is not a hard constraint** — it follows the content (20+ min typical). Warn only on *extreme* lopsidedness, not on the chosen profile. Sub-segment boundaries fall on **idea boundaries** (named teaching units) — satisfying the ≤~6-min alignment limit *and* pacing at once. Record intended per-act durations; flag at render when actuals diverge materially from the chosen profile.

### 8.5 Editorial rubric (gated twice)
A checklist artifact in the manifest, not vibes:
- **At plan approval (before recording):** **transformative outcome named + benefit-forward headline (D9)**, hook strength, open-loop count, act-balance, payoff clarity, beat variety, "why watch this." The skill self-critiques the plan and reports weak acts.
- **At whole-film review (before publish):** retention-risk read-through, seam check (incl. act↔interstitial voice/energy), redundancy/dead-air, sponsor-tease present, packaging present.
- **Structural-variety guard:** compare the proposed arc's hook archetype / three-act rhythm / payoff type against the last N published arcs; warn on formulaic sameness (counterbalancing the library's reuse bias).

### 8.6 Information design — McKinsey-grade, FWF-branded, in motion (D5)
The deck/visual layer aims for **polished, consultant-grade information design** (we're not consultants, but McKinsey's slide standards are the proven craft), adapted to the FWF brand and rendered as **dynamic animated** slides — not static bullet dumps. Principles, applied per slide and enforced at the editorial rubric (§8.5):
- **Action / "so-what" titles** — every slide's headline states the *takeaway*, not the topic ("Renewable diesel cuts lifecycle emissions up to 86%", not "Emissions"). The title is the message; the visual proves it.
- **One message per slide** — a single idea, supported; no kitchen-sink slides.
- **MECE structure & horizontal logic** — the sequence of slide titles, read alone, should tell the argument end-to-end.
- **Disciplined data-viz** — the right chart for the comparison, minimal chart-junk, the insight pre-highlighted (the one bar/number that matters in indigo), sourced.
- **Visual hierarchy & restraint** — clear focal point, generous whitespace (within the deep-purple field), the single indigo accent doing the emphasis work (per the FWF kit).
- **Motion serves comprehension** — builds/reveals pace the narration (one point appears as it's spoken), not decoration; ties to the forced-alignment timing the engine already produces.
These map onto (and extend) the engine's slide types (statement/steps/stat/statgrid/compare/diagram/figure/quote); the planner picks the type that best carries each beat's *so-what*. Use the **`mckinsey-presentations` skill** as the standards reference when authoring decks.

---

## 9. Visual aids module

Three visual sources, blended: **branded graphics** (stat/compare/diagram/steps), **auto-fetched web images/screenshots** (`ingest --url`/`--pdf`, `figure` slides; editorial use + on-screen attribution), and **licensed Adobe Stock** photo **and video** B-roll (D7 — operator subscription; the shot list proposes search prompts to review/download, §8.1). **Rights status + license** are tracked on each asset's brain record (`source` node + `_attachments`, §10.1) and carried forward on reuse; flag doubtful-rights web assets for approval, prefer official sources or branded re-draws. **Stock video B-roll** is composited via the framing layer (§12.7) — as a full-frame cutaway, a background behind branded text, or an inset — bringing real motion into the otherwise slide-driven film.

---

## 10. Central knowledge brain (shared, cross-format)

**Decision (D4 — resolved): the central library is the existing `make_money/brain` company-brain (cb) vault** (`/Volumes/Casima/claudeCode/make_money/brain/`) — not a bespoke store, not a new vault. It is the **shared content-generation brain** for *all* of Dave's content: Founders Who Finish, Dave personally, deep-dive videos, MedTech Monday, Founder Tip Tuesday, the daily carousel/short-form, and future formats. Deep-dives both **contribute to** and **draw from** it, so research compounds across every format.

Explicitly **not** used: `company-brain-vault/` (the cb *code* project) and `AiM_Wiki/` or other client/company vaults (kept isolated — no personal/brand content bleeds in, no client content bleeds out).

### 10.1 Mapping onto the cb schema (default profile — no custom types)
The deep-dive's knowledge maps directly onto the vault's existing node types (`make_money/brain/_system/NODE-TYPES.md`):
- **`source`** — researched material with synthesis: web pages/papers, and **YouTube competitor videos** (source_kind web-snapshot / skill-output: title, channel, views, transcript synthesis, "what worked"). Provenance anchor.
- **`fact`** — verified atomic claims; confidence + `as_of` decay on volatile metrics (cb handles this).
- **`concept`** — defined terms / mental models, incl. Dave's **named frameworks** (order-of-operations test, walk-away condition, the three numbers, foundational-hire signal).
- **`pattern`** — observed regularities: **what makes a title/thumbnail/hook work** (from the §8.1.2b competitive scan) and reusable **narrative-arc shapes**.
- **`persona`** — the **6 audience archetypes** from `editorial_thesis.md`.
- **`playbook` / `question` / `hypothesis`** — procedures, open unknowns, bets.
- **Produced pieces** (a published deep-dive, carousel, MedTech Monday, etc.) → a **`source`** node, source_kind `skill-output` + `producing_skill`, tagged by topic — so "what have we covered, from what angle?" is a query, and evergreen/derivative reuse is explicit.
- **Assets** (screenshots, Adobe Stock photo/video, face-cam) → `_attachments/` + a `source` node carrying **license, attribution, rights_status, stock_asset_id** — the rights record travels with the asset; reuse is auditable against the subscription.
- **Narrative-arc record** (hook archetype, `open_loops`/`payoffs`, act beats, chosen packaging, `structure_tags`) → stored on the produced-piece `source` node and/or a `pattern` node. *(Referred to elsewhere in this doc as "the arc node/record.")*

### 10.2 Tooling (cb — already in use here)
`cb intake` / `atomize` (research → typed nodes), `cb query` (staged retrieval, auto-injected pillars, citations), `cb maintain` (repair, **confidence decay**, dedup, rebuild INDEX), `cb visualize` (graph viewer). This is exactly the dedup/decay/maintenance/query machinery we'd otherwise rebuild — we get it for free, battle-tested in your setup.

### 10.3 Per-video staging → promotion
Each program keeps working research in `deep-dive/programs/<slug>/research/` (plain files — raw notes, this topic's competitor scan, downloaded stock/screenshots). On completion, a **promotion step** curates the *durable, reusable* material **up into `make_money/brain`** via `cb intake` (sourced facts, frameworks, rights-clean assets, the produced-piece source node, what-worked patterns). **Promote, not dump:** scratch and drafts stay in the program folder; only knowledge the *next* piece (any format) would reuse graduates to the brain.

### 10.4 Why this compounds (the payoff)
One topic researched once feeds many outputs over time — a deep-dive, a re-angled deep-dive, a Founder-Tip-Tuesday short, a daily carousel, a newsletter beat. Because every format reads/writes the same brain, **evergreen research is reused and re-angled instead of re-done**, and "we already covered X — here's the angle, the assets, the sources" is a query, not a memory.

---

## 11. Audio & music layer

`explainer mux` overlays **voice only**; music + final loudness are an **assembly-layer** concern (ffmpeg), applied **per-segment** so the master stays a stream copy (§12).

| Role | Source (in `shared/music/`, registered in `LICENSES.md`) | Mixing |
|---|---|---|
| Act / interstitial voice | operator recording (in each segment MP4) | base track |
| **Sponsor-break audio logo** | `breakzstudios-happy-kids-ukulele-…-165192.mp3` (upbeat ukulele logo, Pixabay) | under the FWF + The Build interstitial voice — the sponsor sonic signature |
| **Optional act bed** | `act-bed/alex-morgan-downtempo-chill-electronic-528322.mp3` **or** `act-bed/alex-morgan-corporate-530945.mp3` (Pixabay) | under act voice ~ −22 dB with **sidechain ducking**, **per-segment**; operator picks A/B/none per program (`music.act_bed`) |

All three tracks are **Pixabay Content License** (royalty-free, commercial OK, no attribution required); see `shared/music/LICENSES.md` (exact source URLs to be confirmed). **Loudness:** normalize **per-segment** to **−14 LUFS integrated, ≤ −1 dBTP** with measured two-pass `loudnorm` *before* concat, so the master inherits level-matched audio and needs **no full-length audio pass** (resolves the §12 RAM rule). **Never bake in an unregistered track.** An automated **seam LUFS-delta check** runs at each act↔interstitial boundary (§12.6).

---

## 12. Assembly & master render

Once all act sub-segments are **approved** and interstitials are **ready + integrity-verified**, assembly runs. The council corrected several original claims; v2 is grounded in the real engine (which already **streams PNG frames via `image2pipe`** — no on-disk frame set — and muxes `-c:v copy`, so per-segment render is already RAM-flat).

### 12.1 Master-format contract (enforced)
A versioned contract: **h264 High@L4.0, yuv420p, 1920×1080, SAR 1:1, CFR fps, bt709/tv, AAC-LC 48 kHz stereo (`-ac 2`), faststart.** Because segments are rendered independently (and via the **non-deterministic** `h264_videotoolbox` hardware encoder, at different times/versions), uniformity cannot be assumed.

### 12.2 Preflight conform
`assemble --check` ffprobes every segment + interstitial and prints a conformance table (codec/profile/SAR/pixfmt/fps/channels/sample-rate vs contract) as a fast read-only check. Any mismatch → a cheap **per-segment streaming conform re-encode** (disk-backed) before concat. *(Mono act VO + stereo interstitial is the canonical trap `-ac 2` everywhere prevents.)*

### 12.3 Concat (RAM-safe)
- **Concat demuxer + stream copy** (`-f concat -c copy`) — a remux, near-zero RAM/CPU. **Never** the concat *filter* (`-filter_complex`) across the whole film (the classic blowup).
- Any forced re-encode (cross-dissolve transitions) is **per-segment/pairwise and streaming**, written to disk, then stream-copy concatenated — never one whole-film filtergraph.
- All timing is **derived from ffprobe** on the conformed segments, accumulated in ms/frames.

### 12.4 Captions
Each segment's SRT/VTT (from forced alignment) is offset by the **ffprobe-measured exact duration** of the conformed segment (not rounded manifest values) and concatenated into one master sidecar. No-caption interstitials still **advance the offset accumulator**. Long-form caption style defaults to **1–2 line bottom captions** (a manifest field), not the short-form windowed style.

### 12.5 Chapters & packaging
- **Chapters** from segment boundaries → `chapters.txt` (YouTube format); chapter titles are **forward-hooks**, not bare "Act II."
- **Packaging step (informed by the §8.1.2b competitive scan):** generate 3–5 **benefit-forward title variants** (D9 — sell the transformation, against what the top videos use) + a **custom thumbnail (D10)**. Default thumbnail = an on-brand **composite** via the framing layer (§12.7): FWF template + **3–5-word high-impact keyword text** + the **operator's selfie in a corner** (background optionally removed via `rembg`), 1280×720 — deterministic, repeatable, no AI needed. Optional AI hero/background via the operator's Google **"nano banana"/Gemini** API, or an **interactive Gemini handoff** (the skill writes the prompt + says which images to drop in; operator generates, drags the result back). The `image` skill is also available. Operator picks; chosen packaging recorded in the arc node; uploaded as the **Blotato custom thumbnail**. One title variant seeds the X hook copy.

### 12.6 Validation (master integrity)
Assert: master duration == Σ conformed segment durations (within tolerance); last caption end ≤ master duration; chapters monotonic + in-bounds; **audio present and continuous across every seam** (detect silence-drops at concat points); seam LUFS-delta within threshold. A **dry-run assembly** (chapter list + caption stitch + low-res proxy concat) lets the operator verify ordering/timing cheaply before the expensive final encode. A **disk-budget guard** estimates scratch up front and checks free space on `/Volumes/Casima` rather than failing a long build at ENOSPC.

Output: `master/deepdive_16x9.mp4` + captions + chapters + chosen packaging.

### 12.7 Compositing & framing layer (ffmpeg)
Confirmed locally available: **ffmpeg 8.1.1** (Homebrew) with all needed filters — `scale`, `pad`, `overlay`, `geq` (rounded-corner alpha masks), `boxblur` (drop shadows), `chromakey`/`colorkey`/`despill` (green screen), `colorchannelmixer`, `scale2ref`. PiP and framed composites need **no new tooling**.

**Talking-head PiP (sponsor interstitials, D6).** Dave's iPad face-to-camera clip scaled to ~80% and laid on the FWF branded background. Recommended build:
1. Render the **branded stage** in the existing HTML/Playwright deck — deep-purple bg + vignette, book cover / URL / evergreen offer text (or lower-third), and a defined **window region** with rounded border + soft shadow where the face goes.
2. ffmpeg: scale the iPad clip to the window, apply rounded corners (alpha mask) + drop shadow, `overlay` at the window position over the branded stage, keep his audio. Conform to the master-format contract (§12.1).
Reuses the deck engine for branding + ffmpeg for the inset — on-brand, and RAM-trivial (short segment, per-segment streaming per §12.3).

**Background options.** The 80% PiP window needs **no background removal** (his whole iPad frame sits in the window). For a *cutout* look (real room replaced entirely): shoot against a **green screen** → ffmpeg `chromakey`+`despill` (available now), or AI video matting (**Robust Video Matting** / `rembg` / `backgroundremover`, installable via `brew`/`pip`) for no-green-screen. Optional, later.

**Stock video B-roll (§9).** Same layer composites licensed Adobe Stock footage: full-frame cutaways, backgrounds behind branded text (overlaid from the deck), or insets. **iPad recording guidance:** landscape 16:9, 1080p+, good light, ~arm's-length framing for the window crop.

**Heavier editing.** No NLE is required for the automated pipeline; `Shotcut`/`Kdenlive` (brew casks) are available if a manual pass is ever wanted. The automated path stays **ffmpeg + the HTML deck**.

---

## 13. Publishing (Blotato → YouTube)

The 20-min master publishes 16:9 to **YouTube only** (LinkedIn dropped, D1a — 20-min native video underperforms there; the operator opted out). Reuses the proven Blotato pattern, hardened for long-form.

- **Channel (D1a):** the operator's personal YouTube channel (Blotato account ID in the private FWF instance config) — into a **new dedicated deep-dive series playlist**, created once and kept separate from any existing short-content playlist. (Not the unrelated CIRCUMVENT channel.)
- **Hardened large-file upload:** a 20–30 min master is ~1.2–1.5 GB. Budget the master bitrate/size to a known ceiling (a CRF master encode of the concat result rather than copying through high-bitrate segments); request the presigned URL **immediately before** upload (minimize TTL burn); use `curl` with `--connect-timeout/--max-time` and resumable `-C -` where supported; **verify uploaded object size** via `get_post_status`/`source_status` before `create_post`. On retry-exhaustion, persist a **`ready-but-upload-failed`** state so a failed upload never forces a re-render.
- **YouTube post:** title (chosen variant), description = **outcome-promise hook (keyword-first 2 lines) + chapters + sourced links (from the brain's sources) + the live offer figures for the book/The Build + seeded pinned comment**; `playlistIds` = the new series playlist (+ subject-derived series later); thumbnail = the packaged asset.
- **Synthetic-media disclosure:** now **per-program with documented rationale**. With operator-narrated acts and **face-cam** interstitials (D2/D6) there's no synthetic voice or likeness — the only AI element is assisted graphics; **verify YouTube's 2026 threshold** — likely no realistic-synthetic-voice disclosure required — rather than hard-coding `true` and paying an unneeded discoverability tax. Disclose honestly if actually required.
- **End screens / cards / subscribe-watermark:** reserve the CTA segment's runtime (≥20s, mostly static) as an end-screen canvas. Investigate whether Blotato exposes end-screen/card config; if not, emit a **manual checklist** in `publish-log.md` rather than silently dropping these long-form session-time tools.
- **Integrity:** re-verify account IDs via `blotato_list_accounts`; **capture and persist the real returned YouTube URL** before scheduling promos; **never fabricate a URL**; ≤2× retry on transient media-fetch errors without duplicating.

---

## 14. Promo via short native snippets (the distribution engine)

The full 16:9 master is too long for the short-video feeds (X caps at ~2 min), so promotion runs on **short native snippets (<2 min)** cut from the deep-dive and posted **natively** — not as links — to **X, TikTok, Instagram, and Threads** via existing Blotato connectors (X, TikTok, Instagram, Threads — account IDs in the private FWF config), each driving back to the YouTube video. This is **core to V1**, not deferred — it's how the long-form gets discovered.

### 14.1 Snippet generation
- From the master + per-segment captions + the arc node's tagged hook/stat/payoff beats, auto-propose **3–6 snippets** (each a self-contained 20–110s moment: the hook, a surprising stat, a "who this is for," a quotable payoff).
- Re-render each snippet **9:16** (and/or 1:1) with the engine's **windowed/TikTok caption** style and the FWF theme — the engine already renders these aspects natively.
- Snippets are derived assets of the program (`promo/snippets/`), each labeled with its source timecode and angle.

### 14.2 Multi-platform native posting (Blotato)
- **X:** native snippet video + hook copy; the **YouTube link goes in a self-reply** (Blotato self-reply is confirmed working in existing routines), optionally a 2–3 tweet takeaway thread ending in the link. Pin the anchor.
- **TikTok / Instagram (reel) / Threads:** native snippet + caption; link in caption/first-comment/bio per platform norm.
- **Cadence:** stagger snippets across the days after go-live (T+0 within ~3h, then +1d/+3d/+7d/+14d), each a different snippet/angle; ~10am–1pm ET. Optional chapter deep-link (`?t=`) where the platform allows.
- All snippets point at the **real captured YouTube URL** (§13); never fabricated.

### 14.3 Later add (top-of-funnel)
A dedicated **YouTube Shorts** cut of the best snippet (Shorts→long-form is a strong subscriber-acquisition path) is a natural extension once the snippet engine exists. The V1 data model (per-segment captions, tagged beats, arc nodes, 9:16 render) already supports it.

*2026 reach context (link penalties, native-clip preference): [posteverywhere](https://posteverywhere.ai/blog/how-the-x-twitter-algorithm-works), [Sprout Social](https://sproutsocial.com/insights/twitter-algorithm/), [vidorange](https://vidorange.com/blog/promote-your-youtube-video).*

---

## 15. Captions, chapters & accessibility
Per-segment captions are free from forced alignment; the master sidecar is the offset-stitched result (§12.4). Chapters (§12.5) are appended to the YouTube description. Long-form caption style = 1–2 line bottom (manifest field).

---

## 16. Observability & operations
- **`build-log.jsonl`** (append-only, per program): `{stage, segment, start, end, duration, peak_rss, exit, message}` — diagnostics for failures (incl. OOM) and real data to tune the RAM-bound concurrency cap (§12).
- **`/deepdive status <slug>` (a.k.a. `doctor`):** prints the manifest as a readable "done / blocked / next action" checklist + any manifest-vs-disk drift; the most-used day-to-day command.
- **Heartbeat/lock per stage** so an interrupted stage is detectable as "crashed mid-stage."
- **Program template/clone:** scaffold a new deep-dive from a prior arc's structure so the arc library feeds future planning.

---

## 17. FWF brand spec
A single source of truth at `deep-dive/brand/` (`brand.json` + `brand.md`) read at scaffold time so identity can't drift and a re-brand is one edit. Derived from the validated FWF kit (`make_money/brand_kits/FWF/brand-kit.md`):

- **Background:** deep purple `#36185B`, subtle grain + soft radial vignette. No gradients except the vignette — the flat purple is the signature.
- **Text:** white `#FFFFFF` primary, light gray `#CCCCCC` secondary. *(Reel kit mandates ALL-CAPS one-idea-per-line; for long-form we **adapt** — ALL-CAPS for action titles/labels, sentence case allowed for dense body/data so a 16:9 tutorial slide stays readable per §8.6.)*
- **Accent:** indigo `#757BBD` — the **only** accent; one emphasis word per title, number pills, dividers, logo glow, CTA pill. No second accent; no success-green / warning-red (out of brand).
- **Type:** **Montserrat**, weight 800, Condensed cut. No serifs.
- **Logo (D-rocket, Dave's personal mark):** default `…/FoundersWhoFinishMarketing/brand-assets/brg-logo-purple.png` (lighter purple, reads on the deep-purple bg); centered on cover/CTA with an indigo glow; never recolor/stretch.
- **Book cover:** `…/brand-assets/Founders Who Finish book cover Mockups/` (paperback-on-table/bed for "buy" closes); site shot `davesaunders.net_book.png`. **Headshot** available for author-led frames (use sparingly).
- **Required CTA close frame:** D-rocket + glow · `FOR FOUNDERS WHO` (white) `FINISH` (indigo) · `davesaunders.net` · `@davesaunders` (gray). Clean, uncrowded.
- **Identity anchors:** D-rocket, **@davesaunders**, **davesaunders.net** on watermark + CTA.
- **Info-design standard (D5):** McKinsey-grade action titles, one-message slides, disciplined data-viz, motion-serves-comprehension (§8.6) — the FWF *look* carrying consultant-grade *structure*.
- **Voice profile:** operator's recorded voice for acts + interstitials + CTA (D2); `talktime --tag fwf` default (per-program override).
- **NOT BRG:** never use cream `#F5F0EB`, teal `#0D7377`, navy `#1B2B4B` (the Base Reality Group palette).
- **Seam check:** assembly flags hard cuts between mismatched-palette segments (drift guard).

---

## 18. Risks & open questions

| # | Risk | Mitigation |
|---|---|---|
| 1 | Forced-alignment drift on human takes | ≤~6-min sub-segments; **alignment-confidence gate** + manual transcript path; `approved` requires passing it (§6) |
| 2 | RAM exhaustion at assembly (prior failure) | Frames already streamed; **per-segment** loudnorm/ducking/conform; **concat demuxer + stream copy**; no whole-film filtergraph; RAM-bounded parallelism; disk-budget guard (§12) |
| 3 | Format incompatibility breaking `-c copy` | **Enforced master-format contract** + ffprobe preflight conform; `-ac 2` everywhere; integrity validation (§12) |
| 4 | Manifest / catalog corruption | Atomic writes + `.bak` + journal + `schema_version`; single-writer; reconcile-against-disk (§5) |
| 5 | Partial/truncated artifacts mistaken for good | Write `.partial` → validate (ffprobe duration/moov) → flip status atomically; re-validate on resume (§5, §6) |
| 6 | Large-master upload failure | Size budget; just-in-time presigned URL; resumable PUT; verify size; resumable `ready-but-upload-failed` state (§13) |
| 7 | Library rot (dupes/stale/orphans) | Handled by **`cb maintain`** (dedup, confidence decay, rebuild-index) on the shared `make_money/brain` vault; curated promotion (not dump); per-video scratch stays in the program folder (§10) |
| 8 | Weak retention / disjointed acts | Retention layer + throughline spine + whole-film review gate + editorial rubric (§8) |
| 9 | Stale/wrong offer in immutable masters | **Offer-figure indirection** — evergreen baked copy, live figure in description (§7) |
| **OQ** | **Remaining open questions** | Minor config: Adobe Stock license tier, CTA face-cam vs voice, caption-style default (assume 1–2 line bottom); confirm exact Pixabay source URLs. *(Resolved: **content guide PROVIDED** — editorial thesis + The Build content workbook + research-source roster, in the byline library; central brain = `make_money/brain`; YouTube = operator's channel + new playlist; LinkedIn dropped; FWF theme = adapt kit + McKinsey; X self-reply + Premium ✓; promo = native snippets X/TikTok/IG/Threads; book + The Build URLs + offer in description; music supplied + licensed.)* |

---

## 19. End-to-end flow

```
/deepdive (| <topic> | --plan <doc> | --resume <slug>)
  1. INTAKE       topic direct or from the content guide (cross-checked vs the brain's covered topics)
  2. RESEARCH     library-first → WebSearch → sourced facts; talktime voice; shot list → promote to brain
  3. PLAN         throughline spine + open-loops/payoffs + act-balance + editorial rubric (gate 1) → manifest
  4. RECORD LOOP  per ~90s sub-segment: record → align(gate) → render → REVIEW(approve/reject+notes) → pause
  5. INTERSTITIALS ensure FWF/The Build/CTA are recorded-once + integrity-verified (reused)
  6. ASSEMBLE     preflight conform → per-segment loudnorm/music → concat -c copy → ffprobe offsets
                  → captions + chapters + packaging → master-integrity validation (dry-run available)
  7. FILM REVIEW  operator watches master end-to-end (editorial rubric gate 2) → publishable
  8. PUBLISH      Blotato: hardened upload → operator's YouTube channel (+chapters / new series playlist / packaging)
                  capture real URL → publish-log.md   (LinkedIn dropped)
  9. PROMOTE      cut 3–6 short (<2min) 9:16 snippets → post natively to X / TikTok / Instagram / Threads
                  (Blotato), each → YouTube URL (X link via self-reply); staggered angles, pinned anchor
 [later]          dedicated YouTube Short of the best snippet as top-of-funnel
```

Every stage is checkpointed in the crash-safe manifest; the only hand-recorded work per video is the act sub-segments; sponsors, CTA, and reused library assets carry the rest.
