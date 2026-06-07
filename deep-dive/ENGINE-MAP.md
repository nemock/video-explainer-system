# Deep-Dive — Engine Map (Phase 1.0 Orient)

How the existing explainer engine plugs together, and exactly where the Phase 1
FWF theme + McKinsey slide treatments attach. Written before touching code so the
extension points are explicit. Source of truth for code is the files cited below.

## Render pipeline (where Claude stops, where Python runs)
`scaffold` (cli.py) → writes `project.json` → Claude authors `script.json` + `deck.json`
→ `explainer media` runs the pure-Python stages: `narrate (synth)` → `align` →
`deck (deckbuild)` → `render` → `mux` → `manifest` → `qa`. The deck is built **once**
into `deck/index.html`; the renderer drives `window.renderAt(t)` per frame under CDP
virtual time. No Claude calls in the media path.

## 1. Themes — `src/explainer/themes.py`
- `THEMES` dict, keyed by name. Each theme: `bg`, `fg`, `accent`, `accent2`, `motion`
  (`rise|fade|pop|slide` — the default per-slide intro), and optional
  `fonts: {display, body}`.
- `resolve(spec)` merges over `DEFAULT="midnight"`; accepts a name, an override dict, or None.
- Existing themes: midnight, paper, sunset, forest, mono, medtech, **founder** (the BRG
  FTT forest/brass identity, with `fonts: {Fraunces, Inter}`).
- **FWF attaches here:** add a `"fwf"` entry — `bg #36185B`, `fg #FFFFFF`, `accent #757BBD`,
  `accent2` (FWF has no second accent — set it to the accent or a near-tone so nothing
  off-brand leaks), `motion "fade"`, `fonts: {display: Montserrat, body: Montserrat}`.

## 2. Theme → CSS flow — `deckbuild.py` + `deck_base.html`
- `deckbuild.run(proj)` reads `deck.json`, injects `proj.theme` values by **string
  substitution** into `deck_base.html`: `{{BG}} {{FG}} {{ACCENT}} {{ACCENT2}}` become a
  `:root` block of `--bg/--fg/--accent/--accent2`. `deck.css` consumes them as `var(--…)`.
- Neutral hairlines derive from `--fg` via `color-mix` (so they invert on light themes).
- Fonts: `_font_css(theme, deck_dir)` emits `@font-face` + `--font-display/--font-body`
  **only if** the theme declares `fonts`, copying the needed woff2 from `assets/fonts/`
  into `<deck>/fonts/`. Driven by two tables: `FONT_FILES` (family → woff2 list) and
  `FONT_STACK` (family → fallback stack).
- **FWF attaches here:** register Montserrat in `FONT_FILES` + `FONT_STACK` and drop the
  woff2 into `assets/fonts/`. `.headline`/display classes already bind `--font-display`.

## 3. Slide system — `deck_engine.js` (build loop) + `deck.css` (layout) + `renderAt(t)` (motion)
Three coordinated edit points per slide type:
1. **Build loop** (`DECK.slides.forEach`, ~L76–248): `else if (s.type === 'X')` builds the
   slide's HTML from its data fields. New treatment = new branch here.
2. **CSS** (`deck.css`): classes for that type. **No CSS animation/transition on captured
   elements** — layout/static styling only. Theme vars + `--hair/--hair-strong`.
3. **`renderAt(t)`** (~L301–501): `else if (rt === 'X')` computes the visual state at time
   `t` (opacity/transform/width/count-up) using `easeOut`, `countUp`, staggered offsets.
- Determinism: `Math.random` is reseeded (LCG, seed 42) at the top; same input → same frames.
- Existing types (reusable for McKinsey work): headline, build, highlight, reframe, punch,
  define, list, quote, stat, statgrid, progress, ring, diagram, ranked, trend, delta,
  timeline, waterfall, matrix, compare, steps, pictograph, figure, cta.
- **Captions:** kinetic, windowed (`caption_mode: window`, ~4 words) above the safe zone.
- **Motion-pacing:** the build loop currently keys animation to **slide-window time**
  (`win.start/win.end` from `TIMELINE.slides`) and per-element stagger constants. Word-level
  timestamps exist in `TIMELINE.words` (used only by captions today). **McKinsey
  "builds tied to forced-alignment timing" attaches by letting a slide's reveal beats read
  `TIMELINE.words` for the active slide** instead of fixed offsets — the data is already
  present; no new stage needed.
- **Action ("so-what") titles + one-message layout** are largely an *authoring* convention
  (the `headline`/`build` types already render a single dominant line) plus a CSS hierarchy
  pass for 16:9 (titles ALL-CAPS, a top-anchored title slot, sentence-case dense body).
  A dedicated `source`/citation slot (small, bottom-corner) is the one genuinely new bit
  of chrome for "sourced" data-viz.

## 4. Brand — `brand.py`
- A brand = a folder with `brand.json` (+ asset files + optional `cta_library.json`),
  resolved by **slug** with local-first precedence: `./brand/<slug>/` →
  `$EXPLAINER_BRAND_DIR/<slug>/` → `~/.claude/explainer-brands/<slug>/`.
- `brand.json` fields: `name`, `logo`, `product`, `cta{headline,subkicker,url,spoken}`,
  optional `accent` (overrides theme accent in `project.theme`), `watermark_corner`,
  `lexicon`, `talk_time{tag,library}`.
- `copy_into(...)` copies assets into `<project>/brand/` and writes a project-relative
  brand config into `project.json` (self-contained render). CTA can be picked by variant
  from `cta_library.json` via `--cta`.
- `deckbuild.run` turns that into a persistent watermark (every slide) + an auto-appended
  `cta` end slide.
- **Existing related brand:** `~/.claude/explainer-brands/FFW/` ("Founders Who Finish",
  accent `#7b5bff`, white-D logo) — an earlier short-form brand. The deep-dive FWF brand is
  a *distinct, more precise* spec (bg `#36185B`, accent `#757BBD`, `brg-logo-purple.png`,
  Montserrat). Decision needed: new slug vs. upgrade FFW (see BUILD-PLAN 1.4 / open question).

## 5. CLI — `cli.py`
- `explainer scaffold <slug> --title --outdir --aspect {9:16,16:9,4:5,1:1} --platform
  --theme <name> --brand <slug> --cta <variant> --aspects --fps --voice --voice-source
  --min-length`. `--theme` choices come from `themes.THEMES`, so a new `fwf` theme is
  selectable as soon as it's added. Writes the project dir + `project.json`, prints next steps.
- The **1.1 done-when** test runs through here:
  `explainer scaffold throwaway --theme fwf --aspect 16:9` then author a sample `deck.json`
  + render.

## Open questions surfaced to the operator (before code)
1. **Montserrat "condensed":** Google Montserrat (and its variable woff2) has **no width
   axis**, so `font-stretch: condensed` is a no-op. To get the condensed look we either
   (a) bundle standard Montserrat variable @800 and approximate condensed with tight
   tracking + a horizontal `scaleX(~0.88)` on display lines, or (b) source a genuinely
   condensed face. The brand kit itself flags "verify it actually renders compressed."
2. **FWF brand-folder location/slug:** BUILD-PLAN 1.4 says the source of truth is
   `deep-dive/brand/brand.json` (gitignored), but the engine resolves brands by
   `<slug>/brand.json`. Need to pick the slug + install path (deep-dive/brand/FWF via
   `$EXPLAINER_BRAND_DIR`, or `~/.claude/explainer-brands/FWF/`).
