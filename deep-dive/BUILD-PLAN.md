# Deep-Dive — Phase 1 Build Plan (groundwork)

**Status:** Phase 1 kickoff. Design is frozen + consistency-reviewed (ARCHITECTURE.md, PRD.md; 7 PRs merged). This is the first *code* phase.
**Run from:** a session rooted at `/Volumes/Casima/claudeCode/explainer-system` (the engine repo). The `make_money/brain` cb vault and both CLIs (`cb`, `explainer`) resolve from there.
**Owner key:** 🤖 = Claude builds · 🧑 = Dave does (physical/creative).

Engine surface (confirmed): `src/explainer/themes.py` (themes), `deckbuild.py` + `assets/deck.css` + `assets/deck_engine.js` (slide system), `brand.py` (brand library: watermark/CTA/lexicon), `recorder.py` (teleprompter), `cli.py`. CLIs: `cb` (`~/.local/bin/cb`), `explainer` (`~/myenv/bin/explainer`).

---

## 1.0 — Orient 🤖 *(first, ~30 min)*
Read engine internals before changing anything: `themes.py`, `deckbuild.py`, `deck.css`, `deck_engine.js`, `brand.py`, `recorder.py`, `project.py`, the render/mux path. Confirm the local stack (Kokoro, torchaudio, Playwright, ffmpeg 8.1.1).
**Done when:** a short "engine map" note (how themes + brands + slide types plug in, where to add the FWF theme and McKinsey slide treatments).

## 1.1 — FWF theme 🤖
Add a real `fwf` theme to `themes.py` + `deck.css`/`deck_engine.js`: bg `#36185B` + grain/vignette, fg `#FFFFFF`/`#CCCCCC`, single accent indigo `#757BBD`, **Montserrat 800 Condensed**. FWF brand in `brand.py`: D-rocket logo (`…/FoundersWhoFinishMarketing/brand-assets/brg-logo-purple.png`), required CTA close frame, watermark. Adapt for 16:9 long-form readability (ALL-CAPS titles/labels; sentence case for dense body/data). Brand spec source of truth → `deep-dive/brand/brand.json` + `brand.md` (1.4).
**Done when:** `explainer scaffold throwaway --theme fwf --aspect 16:9` renders sample slides whose look matches the FWF kit; not the stock green/gold `founder` theme.

## 1.2 — McKinsey-grade slide system 🤖
Extend the deck slide types/treatments for **action ("so-what") titles**, one-message layout, disciplined data-viz (right chart, pre-highlighted insight in indigo, sourced), strong visual hierarchy, and **motion that paces the narration** (builds tied to forced-alignment timing). Reference the `mckinsey-presentations` skill's standards.
**Done when:** a sample deck demonstrates an action-title slide + a data-viz slide rendering cleanly with narration-paced builds.

## 1.3 — Wire + seed `make_money/brain` 🤖
Confirm `cb` operates on `/Volumes/Casima/claudeCode/make_money/brain/`. Seed from the byline library (`~/.claude/explainer-brands/dave-byline/`): the **6 audience archetypes** → `persona` nodes; the **4 named frameworks** → `concept` nodes; the **research-source roster** → `source` nodes. Define + document the deep-dive's `cb query` (library-first) and `cb intake` (promote) patterns.
**Done when:** `cb query` returns the personas/frameworks/sources; INDEX rebuilt (`cb maintain`); a documented promote/query recipe.

## 1.4 — FWF brand spec file 🤖
Write `deep-dive/brand/brand.json` + `brand.md` (palette, fonts, logo/book-cover paths, handle/home, voice profile, info-design standard), read at scaffold time so identity can't drift. *(Operator content — gitignored; not in the public repo.)*
**Done when:** the FWF theme/brand (1.1) reads from it.

## 1.5 — Music/audio layer recipe 🤖
Build the assembly-layer audio recipes (ffmpeg): per-segment **sidechain ducking** of an act bed under VO (~ −22 dB), **two-pass loudnorm to −14 LUFS / ≤ −1 dBTP**, sponsor-bed mix under interstitial audio, and the **seam LUFS-delta check**. Tracks already in `shared/music/` (registered in `LICENSES.md`).
**Done when:** a tested command set; sample VO + act bed mixed/ducked/normalized; seams level-matched.

## 1.6 — Face-cam interstitials 🧑→🤖 *(needs Dave)*
- 🤖 **first:** draft the **evergreen** interstitial scripts (FWF book; The Build — no price baked in; CTA) so Dave can record while 1.1–1.5 proceed.
- 🧑 **record:** FWF + The Build face-cam clips on iPad (landscape 16:9, 1080p+, good light, arm's-length). CTA: voice or face-cam (Dave's choice).
- 🤖 **composite + register:** branded-stage HTML (deep-purple bg + book cover/URL + rounded/shadowed window) + ffmpeg PiP inset (~80%), sponsor-bed mix, conform to master-format contract, register in `interstitial-registry.json` (mp4 + hash + ffprobe-format + verified offer facts).
**Done when:** 3 reusable, version-pinned interstitial MP4s exist + registered + contract-conformant.

---

## Tiny confirmations (defaults assumed; override anytime)
- Caption style: **1–2 line bottom** (long-form default). · Adobe Stock license tier: TBC (record in brand spec). · CTA: face-cam vs voice — Dave's call at 1.6.

## Sequencing
1.0 → then **1.1–1.5 in parallel** (all 🤖, independent) + 🤖 drafts 1.6 scripts → 🧑 records 1.6 → 🤖 composites/registers 1.6. Phase 1 done = FWF theme + McKinsey slides + seeded brain + brand spec + audio recipes + 3 registered interstitials. Then **Phase 2** (orchestrator + manifest + record loop + assembly).

## Guardrails (from the design — don't regress)
RAM-safe assembly (per-segment, concat demuxer + stream copy, no whole-film filtergraph); master-format contract + `-ac 2`; crash-safe manifest; **no Blotato IDs / personal IP in this PUBLIC repo** (operator specifics live in `~/.claude/explainer-brands/dave-byline/`); branch → PR → merge for commits.
