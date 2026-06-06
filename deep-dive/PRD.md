# Deep-Dive Video Generator — Product Requirements Document (PRD, v2)

**Status:** Draft for review
**Revision:** v2 — incorporates the council review (2026-06-04/05) and four locked product decisions.
**Companion doc:** [`ARCHITECTURE.md`](ARCHITECTURE.md)
**Lives in:** `/Volumes/Casima/claudeCode/explainer-system/deep-dive/` (a capability of the explainer system)
**Owner:** Dave Saunders

---

## 1. Summary

A higher-level video generator for **long-form (20+ minute) deep-dive, tutorial-style videos** for the **Founders Who Finish (FWF)** founder/builder audience, built on top of the existing `explainer` rendering engine. Deep-dives are **human-narrated by the operator**, structured as a **three-act "play"** with self-sponsor breaks between acts, and assembled from independently-recorded segments so the operator records **interactively, sub-segment by sub-segment, instead of in one marathon session**.

The product's job: take a topic (or inspire one from a content-planning document), research it (library-first), draft a three-act script in the operator's voice with a designed retention spine, walk the operator through staged voiceover recording and review, build a highly graphical 16:9 film with McKinsey-grade information design blending web screenshots and branded visuals, splice in reusable operator-voiced interstitials and CTA, publish to the operator's YouTube channel via Blotato, and promote it with short native snippets across X, TikTok, Instagram, and Threads.

> **Concrete FWF instance values** (Blotato account/channel IDs, sponsor specifics, theme, music) live in a **private brand config** at `~/.claude/explainer-brands/dave-byline/deep-dive-instance-config.md` — deliberately kept out of this public repo.

> **Where this lives / scope:** the deep-dive generator is a **brand-parameterized capability of the explainer system** (`explainer-system/`), not a single-brand routine. Its **primary instance is Founders Who Finish (FWF)** — the operator's own videos (and The Build) — while other content projects (e.g. CIRCUMVENT/CVG) *may* also consume it. The FWF specifics below (theme, channel, sponsors) are one brand config, not system-wide assumptions.

---

## 2. Locked decisions (v2)

| # | Decision |
|---|---|
| D1 | **Brand = Founders Who Finish**, fully decoupled from CIRCUMVENT — real FWF theme (purple/indigo/Montserrat), D-rocket + @davesaunders anchors. |
| D1a | **YouTube = the operator's personal channel + a new dedicated deep-dive series playlist** (account/playlist IDs in the private FWF config). **LinkedIn dropped.** |
| D2 | **Sponsor reads + CTA are operator-voiced, recorded once** (not TTS) — reusable, version-pinned. |
| D3 | **Promo = short native snippets (<2 min) on X + TikTok + Instagram + Threads** (Blotato), pointing to YouTube. Core to V1 (the film exceeds X's 2-min cap). Deep-dive itself stays 16:9 long-form. |
| D4 | **Knowledge library backend: spike `company-brain` (cb) vs bespoke** before committing. |
| D5 | **Deck/visual layer = McKinsey-grade information design**, adapted to FWF + motion (action titles, one-message slides, disciplined data-viz). Use the `mckinsey-presentations` skill's standards. |

---

## 3. Goals & non-goals

### Goals
- G1 — Polished **20+ minute, 16:9** deep-dives with **operator voiceover**, FWF-branded.
- G2 — **Staged, interactive recording**: a series of voiceover prompts recorded over one or more sessions, at ~60–90s sub-segment granularity, with per-sub-segment review/approve.
- G3 — **Three-act structure** with operator-voiced self-sponsor breaks at the seams: Act I → *Founders Who Finish* → Act II → *The Build* → Act III → like/subscribe.
- G4 — **Retention-engineered**: cold open, planted/paid-off open loops, re-hook cadence, pre-sponsor teases, whole-film review — not just structure.
- G5 — **Highly graphical**: web screenshots/images + branded graphics, with attribution + tracked rights.
- G6 — **Minimal recurring effort**: interstitials + CTA recorded once and reused; only act content per video.
- G7 — **Research-driven, sourced**, in the operator's authentic voice (talk-time), feeding a **compounding knowledge library**.
- G8 — **Publish to YouTube** (the operator's channel + a new series playlist) via Blotato; **promote via short native snippets** on X/TikTok/IG/Threads pointing at the real returned URL.
- G9 — **Resumable, crash-safe** builds across days; stop after any sub-segment, resume with no lost state.

### Non-goals
- N1 — The deep-dive itself is **16:9 long-form only**; no vertical *deliverable*. *(Derived 9:16 promo clips are a planned future module — D3/§Phase 3.5 — not part of the long-form deliverable.)*
- N2 — No fully-unattended generation. **Operator-in-the-loop** by design (human VO, per-sub-segment review, whole-film review).
- N3 — Not related to / not a replacement for the CIRCUMVENT short-form routine; entirely separate.
- N4 — **This phase delivers design docs only.** No code yet.

---

## 4. Users & use case

**Primary user:** Dave Saunders, recording deep-dive tutorials for the **FWF founder/builder** audience.

**Use case:** nuanced, teaching-first long-form where the value *is* the depth. The only hard CTA is "like & subscribe"; brand-building is handled gently by two between-act self-sponsor breaks for the operator's own properties (the *Founders Who Finish* book and *The Build* newsletter).

**Why staged recording matters:** ~3,000 spoken words is exhausting in one sitting. The operator records a sub-segment, sees it come together, and continues when ready.

---

## 5. Content & brand model

- **Format:** 16:9, 20+ minutes, three acts + mandatory cold open + reusable interstitials + CTA.
- **Brand:** **Founders Who Finish.** Build a **real FWF theme** (deep purple `#36185B` bg + vignette, white text, single indigo `#757BBD` accent, Montserrat 800 Condensed, D-rocket logo, required CTA close) from the validated kit (`make_money/brand_kits/FWF/brand-kit.md`); the stock `founder` theme (green/gold) is wrong. Single source of truth in `deep-dive/brand/`.
- **Information design (D5):** McKinsey-grade — **action/"so-what" slide titles**, one message per slide, MECE horizontal logic, disciplined data-viz, visual hierarchy — rendered as **dynamic animated** FWF slides whose builds pace the narration. Polished, consultant-grade productions (reference the `mckinsey-presentations` skill). The reel kit's ALL-CAPS-one-line rule is **adapted** for dense long-form readability (caps for titles/labels; sentence case allowed for body/data).
- **Voice:** the operator's recorded voice for acts **and** interstitials **and** CTA (D2). Scripts drafted via `talktime` (tag per-program, default `fwf`).
- **Hard CTA:** operator-voiced "hit like and subscribe." No funnel.
- **Soft CTAs (self-sponsor breaks):** soft first-person framing ("my book…"), bracketed by an operator-voiced bridge in/out of each break.

### Sponsor break specs

| Break | Placement | On-screen + spoken |
|---|---|---|
| **Founders Who Finish** | After Act I | Operator-voiced; book cover, one-line pitch, on-screen `davesaunders.net/book` |
| **The Build** | After Act II | Operator-voiced; pitch + on-screen `davesaunders.net/free-trial`. **Offer ($14.95 to start, then $79/mo, plus $1,500+ in free bonuses) lives in the YouTube description, NOT the immutable baked asset** (evergreen spoken copy only) |
| **Like & Subscribe CTA** | End of Act III | Operator-voiced, simple |

**Music (supplied + licensed, Pixabay):** sponsor-break audio logo = `breakzstudios-…-165192.mp3` (upbeat ukulele); optional act bed = `alex-morgan-downtempo-…-528322.mp3` or `alex-morgan-corporate-530945.mp3`. Registered in `shared/music/LICENSES.md`.

---

## 6. Functional requirements

### 6.1 Initiation & topic selection
- FR-1 — Initiate with (a) a named topic, or (b) a **content-planning document** the skill parses to propose candidates, cross-checked against `subjects/` (prefer fresh ground or deliberate follow-ons).
- FR-2 — Create a program directory and a **crash-safe `program-manifest.json`** (atomic writes, `schema_version`, `.bak` + journal, single-writer, reconcile-against-disk).

### 6.2 Research & knowledge library
- FR-3 — **Library-first**: query existing sources/facts/assets before new research.
- FR-4 — Web research (WebSearch/WebFetch); every claim a sourced `wiki fact` (no unsourced claims). Reddit/LinkedIn/Substack MCP for audience research.
- FR-5 — Draft scripts in the operator's voice via `talktime` (per-program tag).
- FR-6 — Produce a **visual shot list**: per beat, branded graphic or web asset, each with source + attribution + rights status.
- FR-7 — Maintain the **persistent knowledge library** (sources, facts, assets, subjects, arcs) with dedup-on-write (content hash for assets), `used_in[]` provenance, freshness/`as_of` decay, manifest + INDEX for retrieval.
- FR-8 — **Promote (not dump)**: a real `promote` step curates rights-clean material up on completion, writes the arc node, marks the subject published.
- FR-9 — **Backend decided by spike** (D4): host in a `cb` vault or bespoke store.

### 6.3 Content plan, retention & editorial
- FR-10 — Decompose into a balanced three-act arc (target ≈ I 15–20% / II 55–60% / III 20–25%); warn on lopsided plans.
- FR-11 — Author a **throughline spine** before recording: thesis, 2–3 open loops, explicit act-to-act callback/hand-off lines.
- FR-12 — **Retention layer**: mandatory cold open (payoff/stakes + primary loop); open-loop/payoff ledger with dangling-loop warnings; re-hook cadence (~every 90s); pre-sponsor teases.
- FR-13 — **Editorial rubric gated twice** — at plan approval and at whole-film review (hook, balance, payoff integrity, beat variety, redundancy/dead-air, sponsor tease, packaging). Skill self-critiques the plan.
- FR-14 — **Structural-variety guard**: warn when hook archetype / rhythm / payoff type repeats recent arcs.

### 6.4 Staged recording & review
- FR-15 — Record + render + review at **~60–90s sub-segment** granularity (the unit of re-record), boundaries on idea lines.
- FR-16 — Teleprompter prompt surfaces the **prior sub-segment's closing energy + hand-off line** for tonal continuity.
- FR-17 — **Alignment-confidence gate**: threshold alignment score / words-aligned ratio / max inter-word gap; failures surface exact timestamps; manual transcript-correction path for ad-libs; `rendered` requires passing it.
- FR-18 — **Approve/reject gate** distinct from `rendered`, per sub-segment, with `review_notes`; **assembly gates on `approved`**. Re-recording one sub-segment doesn't reset its neighbors. Record out of order; resume across sessions.

### 6.5 Visual aids
- FR-19 — Blend **auto-fetched web images/screenshots** (`ingest --url`/`--pdf`) with **branded graphics**.
- FR-20 — On-screen **attribution**; **rights status** tracked in the asset catalog and carried forward on reuse; flag doubtful-rights assets for approval.

### 6.6 Interstitials & CTA (operator-voiced, reusable)
- FR-21 — Record the two sponsor interstitials + CTA **once in the operator's voice** (D2), version-pinned, reused on every deep-dive.
- FR-22 — **Registry integrity**: per version store mp4 path, content hash, ffprobe format, structured offer facts + verified flag; assembly verifies existence + hash + format-contract conformance before concat; never mutate a published version in place.
- FR-23 — **Offer-figure indirection**: evergreen baked copy; live price/bonus in the description.
- FR-24 — Sponsor-break music under the interstitial voice for a consistent audio signature.

### 6.7 Audio & music
- FR-25 — Dedicated **sponsor-break music**; optional **act music bed** (per-program), mixed under voice with **per-segment** sidechain ducking.
- FR-26 — **Per-segment** two-pass loudnorm to **−14 LUFS / ≤ −1 dBTP** before concat (no full-length master audio pass).
- FR-27 — Never bake in unlicensed music (`shared/music/LICENSES.md`). Automated **seam LUFS-delta check** at act↔interstitial boundaries.

### 6.8 Assembly
- FR-28 — Enforce a **versioned master-format contract** (h264 High@L4.0, yuv420p, 1920×1080, SAR 1:1, CFR fps, bt709/tv, AAC-LC 48 kHz **stereo**, faststart); `assemble --check` preflight + per-segment conform re-encode on any mismatch.
- FR-29 — Concatenate via **concat demuxer + stream copy**; any forced re-encode is per-segment/streaming; never a whole-film filtergraph.
- FR-30 — Derive all timing from **ffprobe** on conformed segments; stitch captions by frame-exact offsets (no-caption interstitials still advance the accumulator).
- FR-31 — Emit **chapters** (forward-hook titles) and a **packaging step** (3–5 title variants + a purpose-built branded thumbnail, not a deck still); record chosen packaging in the arc node.
- FR-32 — **Master-integrity validation** (duration == Σ segments; last caption ≤ master; chapters monotonic; audio continuous across seams) + optional **dry-run assembly** + **disk-budget guard**.

### 6.9 Publishing
- FR-33 — Publish to **the operator's YouTube channel** + a **new dedicated deep-dive series playlist** (concrete account/playlist IDs in the private FWF config, not this repo; not the unrelated CIRCUMVENT channel), with chosen title, description (keyword-first hook + chapters + sourced links + live book/The Build offer figures + seeded pinned comment), packaged thumbnail.
- FR-34 — **LinkedIn dropped** (D1a) — 20-min native video underperforms there; revisit later if desired.
- FR-35 — **Hardened large-file upload**: master bitrate/size budget; just-in-time presigned URL; resumable PUT + timeouts; verify uploaded size before `create_post`; persistent **`ready-but-upload-failed`** state.
- FR-36 — **Synthetic-media disclosure is per-program with documented rationale**; verify YouTube's 2026 threshold rather than hard-coding `true` (operator-voiced acts + interstitials = minimal synthetic content).
- FR-37 — **End screens / cards / subscribe-watermark**: reserve CTA runtime as a canvas; set via Blotato if supported, else a manual checklist in `publish-log.md`.
- FR-38 — **Capture & persist the real returned YouTube URL**; never fabricate; re-verify accounts; ≤2× retry without duplicating.

### 6.10 Promo via short native snippets (D3 — core)
- FR-39 — From the master + per-segment captions + arc-tagged beats, generate **3–6 short snippets (<2 min, 9:16/1:1)** with windowed captions + FWF theme (`promo/snippets/`), each labeled with source timecode + angle.
- FR-40 — Post snippets **natively** via Blotato to **X, TikTok, Instagram, and Threads** (account IDs in the private FWF config), each pointing at the real YouTube URL — on X the link via **self-reply** (confirmed working) + optional takeaway thread; pin the anchor.
- FR-41 — Stagger snippets T+0/+1d/+3d/+7d/+14d, distinct angles, ~10am–1pm ET; optional chapter deep-link (`?t=`).
- FR-41a — *(Later)* a dedicated **YouTube Short** of the best snippet as top-of-funnel.

### 6.11 State, observability & ops
- FR-42 — `program-manifest.json` tracks every segment's lifecycle (incl. approve/reject + film-review states) and publish state; crash-safe and reconcilable.
- FR-43 — Append-only **`build-log.jsonl`** (stage/segment/timing/peak-RAM/exit) + a **`/deepdive status` (doctor)** command printing done/blocked/next-action + manifest-vs-disk drift; heartbeat/lock per stage.

### 6.12 Non-functional: memory discipline (hard constraint)
- NFR-1 — **RAM-friendly assembly/render.** Peak memory stays roughly flat regardless of length (prior failure: everything in RAM). Per-segment render already streams frames (`image2pipe`).
- NFR-2 — Master via **concat demuxer + stream copy**; segments conformed to one contract.
- NFR-3 — Re-encodes (transitions/music/loudness) **per-segment + streaming**; never a whole-film filtergraph; loudnorm per-segment so the master needs no full-length audio pass.
- NFR-4 — Frames/audio disk-backed + streamed; intermediates cleaned up; disk-budget guard.
- NFR-5 — Concurrency **RAM-bounded** (tuned from real `build-log` peak-RAM data), sequential fallback.

---

## 7. Skill invocation & flow

```
/deepdive | /deepdive <topic> | /deepdive --plan <doc> | /deepdive --resume <slug> | /deepdive status <slug>
```
Intake → library-first Research → 3-Act Plan + retention spine (rubric gate 1) → **sub-segment record→align(gate)→render→review(approve) loop** → ensure interstitials → Assemble (conform→concat→offsets→packaging→integrity) → **whole-film review (rubric gate 2)** → Publish (operator's YouTube channel) → cut snippets → schedule native promos (X/TikTok/IG/Threads). *(Full diagram: ARCHITECTURE §19.)*

---

## 8. Success criteria
- SC-1 — Operator produces a complete deep-dive recording **no more than a few ~90s sub-segments per sitting**; re-records are sub-segment-sized.
- SC-2 — Re-recording one sub-segment doesn't touch its neighbors; builds resume cleanly across days from a crash-safe manifest.
- SC-3 — Interstitials + CTA require **zero per-video recording** and stay consistent (operator voice).
- SC-4 — The published YouTube video has working **chapters**, a stitched caption track, a **packaged thumbnail/title**, and correct FWF branding.
- SC-5 — Master assembles at ~one-segment RAM cost regardless of length; assembly passes master-integrity validation.
- SC-6 — Audience retention is *designed*: cold open + ≥2 planted-and-paid-off open loops + pre-sponsor teases, verified at whole-film review.
- SC-7 — 3–6 short native snippets scheduled across X/TikTok/IG/Threads, each pointing at the **real** returned YouTube URL, distinct angles, pinned anchor on X.
- SC-8 — The knowledge library **compounds**: later videos demonstrably reuse prior sources/facts/assets (content-hash dedup); no duplicate research or re-captured approved assets.

---

## 9. Out of scope / future
- Multi-language narration; AI B-roll beyond the slide engine; audience-personalized cuts.
- LinkedIn long-form (dropped for now); a dedicated YouTube Short top-of-funnel (later).
- Full title/thumbnail A/B automation (YouTube native Test & Compare is a fast-follow).

---

## 10. Open questions for the operator

**Resolved this round:** YouTube = operator's channel + new series playlist · LinkedIn dropped · FWF theme = adapt the kit + McKinsey info-design · X self-reply confirmed, promo = native snippets on X/TikTok/IG/Threads · logo/book-cover asset paths known. *(Concrete IDs in the private FWF config.)*

**Resolved this round:** book URL `davesaunders.net/book` · The Build URL `davesaunders.net/free-trial` · The Build offer **$14.95 to start, then $79/mo, plus $1,500+ in free bonuses** (→ YouTube description, not baked) · music supplied + Pixabay-licensed (logo + two act beds) · **X Premium = yes**.

**Still needed:**
1. **Content-planning document** — the operator is still drafting it; its format/location is the last real input before a first build. *(This is the natural next handoff.)*
2. **Caption style** — confirm 1–2 line bottom default for long-form (will assume yes unless told otherwise).

**Build tasks (not questions):** the `cb`-vs-bespoke library spike (D4); confirm exact Pixabay source URLs in `shared/music/LICENSES.md`.

---

## 11. Phasing (proposed, for when build is approved)
- **Phase 0 (this deliverable):** Architecture + PRD (v2, post-council). ✅
- **Phase 1:** Resolve remaining open questions; **`cb`-vs-bespoke spike**; build the **FWF theme + McKinsey-grade info-design slide system** + brand spec; record + register the three operator-voiced interstitials; establish the music layer + licenses.
- **Phase 2:** Orchestrator + crash-safe manifest; sub-segment record→align(gate)→render→review loop; retention/editorial planning + rubric gates; assembly (format-contract conform + concat + ffprobe offsets + caption stitch + chapters + master-integrity); observability (`build-log`, `doctor`).
- **Phase 3:** YouTube publishing (operator's channel, new series playlist, hardened upload, packaging, end screens/cards) **+ the snippet promo engine** (3–6 <2-min native clips → X/TikTok/IG/Threads via Blotato, pointing at the captured YouTube URL).
- **Phase 4:** First real deep-dive end-to-end from the operator's content-planning document; refine from the run. *(Later: a dedicated YouTube Short top-of-funnel.)*
