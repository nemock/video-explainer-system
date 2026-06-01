# Visual device catalog

The deck engine renders a set of **slide types** ("visual devices"). Each is data-driven
(authored in `deck.json`), animated deterministically by `renderAt(t)` (no CSS animation),
and styled from the active theme's tokens (`--accent`, `--accent2`, `--bg`, `--fg`).

**The point of this catalog:** *vary the device to the message.* A deck that uses the same
bar chart twice reads as templated. Pick the device that proves the specific point, and
don't repeat a data device within one deck unless the data genuinely calls for it.

Every slide may also set `kicker` (small label above), `subkicker` (line below), and
`transition` (`rise` · `fade` · `pop` · `slide`) — vary the transition across slides too.

---

## Narrative devices

### `hook`
Open with the payoff. Bold claim / question / surprising line.
```json
{ "id": "s1", "type": "hook", "kicker": "founder tip",
  "headline": "You're not behind — you're not shipping", "accent": ["not shipping"] }
```

### `statement`
A single tight assertion. The workhorse. `accent`/`accent2` highlight words.
```json
{ "id": "s2", "type": "statement", "headline": "Your first version should embarrass you",
  "accent2": ["embarrass you"] }
```

### `payoff`
The closing takeaway. Like `statement` but framed as the resolution + optional `subkicker`.
```json
{ "id": "s9", "type": "payoff", "headline": "Ship it this week",
  "accent": ["this week"], "subkicker": "build · ship · learn" }
```

### `quote`
A pull-quote — **use verbatim quotes here** (e.g. talk-time `quotes.md` one-liners).
```json
{ "id": "s5", "type": "quote",
  "quote": "An idea has no intrinsic value. Execution is the scarce commodity.",
  "attribution": "Dave Saunders" }
```

### `reframe`
Strike the wrong word, swap in the right one. Best device for a myth→reality flip at the
word level. A line draws across `strike`; `after` rises in. Keep all three parts short.
```json
{ "id": "s3", "type": "reframe", "kicker": "the flip",
  "before": "It's not about", "strike": "luck", "after": "timing" }
```

### `highlight`
A marker sweep wipes across the key phrase mid-dwell — emphasis without a layout change.
`mark` lists the words to highlight (matched like `accent`). Keep the headline short.
```json
{ "id": "s4", "type": "highlight",
  "headline": "Execution is the scarce commodity", "mark": ["scarce", "commodity"] }
```

### `build`
A `statement` whose words assemble one at a time — kinetic energy on a plain assertion.
`accent`/`accent2` color words as usual.
```json
{ "id": "s2", "type": "build",
  "headline": "Your first version should embarrass you", "accent2": ["embarrass", "you"] }
```

### `punch`
A single-word slam, maximum size — for a beat. One short `word`. Pops in by default.
`kind` (`good`/`bad`) tints it accent/accent2; omit for plain.
```json
{ "id": "s7", "type": "punch", "word": "Ship.", "kind": "good" }
```

### `list`
A plain numbered list, revealed one item per beat. Lighter than `steps` (no process
semantic, no `text` sub-line) — use for "3 reasons / things / truths".
```json
{ "id": "s6", "type": "list", "kicker": "3 hard truths",
  "items": ["No one is coming to save you", "Taste compounds", "Boring wins"] }
```

### `define`
A term and its definition. The `term` lands big; the `definition` fades in under it.
```json
{ "id": "s4", "type": "define", "term": "Default alive",
  "definition": "Profitable on current trajectory, before raising more" }
```

---

## Data devices

Pick by **what you want to prove** (the McKinsey rule: simplest device that proves it).

### `stat` — one big number
When a *single* metric tells the story. The number counts up from 0. Highest impact; let it
breathe. `value` accepts `"90%"`, `"$2.5M"`, `"10,000"`, `"3x"`, `"12mo"` (count-up parses
the numeric core, keeps the prefix/suffix).
```json
{ "id": "s2", "type": "stat", "kicker": "the stakes",
  "value": "90%", "label": "of startups fail — most of them quietly" }
```

### `statgrid` — 2–4 KPIs
A small set of related numbers, revealed in a staggered grid. Each counts up.
```json
{ "id": "s3", "type": "statgrid", "kicker": "by the numbers",
  "stats": [ { "value": "$0", "label": "spent on ads" }, { "value": "3", "label": "founders" },
             { "value": "12mo", "label": "to first revenue" }, { "value": "10k", "label": "users" } ] }
```

### `progress` — a single proportion
"X% of …". A big % + a filling track. `value` accepts `0.73`, `73`, or `"73%"`.
```json
{ "id": "s4", "type": "progress", "kicker": "the gap",
  "value": "73%", "label": "never talk to a customer first" }
```

### `diagram` — bar comparison (2–N bars)
Compare a few quantities. `kind: "good"` (accent) vs `"bad"` (accent2); bars grow on reveal.
```json
{ "id": "s4", "type": "diagram", "kicker": "where the weeks go",
  "bars": [ { "label": "Polishing in private", "value": 0.9, "kind": "bad" },
            { "label": "Learning from users", "value": 0.2, "kind": "good" } ] }
```

### `compare` — A vs B
Two framed cards with a `vs` divider. Before/after, us/them, myth/reality. `kind` colors the
border (`good`/`bad`).
```json
{ "id": "s5", "type": "compare", "kicker": "the flip",
  "left":  { "title": "Before shipping", "value": "Guessing", "kind": "bad" },
  "right": { "title": "After shipping",  "value": "Learning", "kind": "good" } }
```

### `steps` — numbered process flow
2–5 sequential moves, revealed one at a time. Items are strings or `{title, text}`.
```json
{ "id": "s6", "type": "steps", "kicker": "the playbook",
  "steps": [ { "title": "Ship the smallest version" },
             { "title": "Watch what people actually do", "text": "not what they say" },
             { "title": "Cut what nobody uses" } ] }
```

### `pictograph` — icon array (waffle)
"N of M". A grid of cells, `filled` of `total` light up — concrete where a bare % is
abstract. `kind` colors the filled cells (`good`/`bad`). Best with total ≤ 20.
```json
{ "id": "s2", "type": "pictograph", "kicker": "the odds",
  "filled": 9, "total": 10, "label": "founders quit before they ship", "kind": "bad" }
```

### `trend` — a line that draws on
Change over time. A sparkline draws left→right with a travelling end dot + `end_label`.
`points` is a plain number array (raw values; auto-scaled). Use when the *shape* of the
change is the point.
```json
{ "id": "s3", "type": "trend", "kicker": "MRR",
  "points": [2, 3, 3, 5, 8, 13], "end_label": "$13k", "kind": "good" }
```

### `ring` — a proportion as an arc
A single "X%" as a sweeping gauge with the % in the center — a more dynamic alternative to
`progress`. `value` accepts `0.73`, `73`, or `"73%"`. (A gauge, not a pie comparison.)
```json
{ "id": "s4", "type": "ring", "kicker": "capacity",
  "value": "73%", "label": "of runway already spent", "kind": "bad" }
```

### `ranked` — horizontal top-N bars
3–5 ranked items with **long labels** (which vertical `diagram` can't hold). `value` is
0–1 (bar length); optional `display` shows a value at the bar end; `kind` colors a bar.
```json
{ "id": "s4", "type": "ranked", "kicker": "where the week goes",
  "bars": [ { "label": "Polishing in private", "value": 0.9, "display": "90%", "kind": "bad" },
            { "label": "Talking to users", "value": 0.2, "display": "20%", "kind": "good" } ] }
```

### `delta` — before → after
Two values joined by an arrow with a change badge — the quantitative cousin of `compare`.
`from`/`to` count up; optional `from_label`/`to_label`; `change` is the badge; `kind` colors `to`.
```json
{ "id": "s5", "type": "delta", "kicker": "12 months",
  "from": "$10k", "to": "$40k", "from_label": "Q1", "to_label": "Q4", "change": "+300%", "kind": "good" }
```

### `timeline` — dated milestones
A horizontal axis with 3–5 **dated** points, revealed left→right as the connector draws.
Distinct from `steps` (process, undated). Each event has a `date` + `label`.
```json
{ "id": "s6", "type": "timeline",
  "events": [ { "date": "Jan", "label": "Idea" }, { "date": "Apr", "label": "MVP" },
              { "date": "Sep", "label": "Revenue" } ] }
```

### `waterfall` — start → +/- contributors → end
"How we closed the gap." A start total, floating +/- step bars, an end total. + steps are
accent, − steps accent2; bars grow in sequence. The engine **auto-fits** the columns + label
sizes to the viewport, so any count renders on any aspect without colliding — but it stays the
**most dwell-sensitive** device: give it ≥ 5s. For readability still favor **≤ 4 steps** with
short labels (6–7 bars fit, but go small on 9:16). `value`s are absolute numbers (steps may be
negative).
```json
{ "id": "s5", "type": "waterfall", "kicker": "how we closed the gap",
  "start": { "label": "Q1", "value": 40 },
  "steps": [ { "label": "Churn", "value": -12, "kind": "bad" }, { "label": "New", "value": 30, "kind": "good" } ],
  "end": { "label": "Q2", "value": 58 } }
```

### `matrix` — 2×2 positioning quadrant
Two labeled axes, 2–4 plotted points. "Effort vs impact," "us vs them." **Dwell-sensitive:**
give it ≥ 5s. The plot is square and the engine **auto-fits** the point labels (sizes + wraps
them) to the viewport, so multi-word labels read on every aspect. Still keep to **≤ 4 points**
so the quadrant doesn't crowd. `x`/`y` are 0–1; `kind` colors a point.
```json
{ "id": "s5", "type": "matrix", "kicker": "where to focus",
  "x_axis": ["Low effort", "High effort"], "y_axis": ["Low impact", "High impact"],
  "points": [ { "label": "Polish", "x": 0.8, "y": 0.2, "kind": "bad" },
              { "label": "Ship", "x": 0.2, "y": 0.85, "kind": "good" } ] }
```

---

## Source device

### `figure`
Frame an ingested screenshot / paper figure (white card on the dark theme). `image` is
relative to the project root (e.g. `sources/x.png`).
```json
{ "id": "s4", "type": "figure", "kicker": "source: arXiv 2401.x",
  "image": "sources/fig1.png", "caption": "Throughput vs. batch size" }
```

---

## Brand device

### `cta`
Auto-appended from the brand (`--brand`); shows product image + logo + headline/subkicker/url
and auto-narrates `cta.spoken`. You normally don't author it. See the branding section of the
skill + `cta_library.json` for rotating variants.

---

## Choosing — quick guide

| You want to… | Device |
|---|---|
| Open / hook | `hook` |
| Assert one idea | `statement` |
| Assert one idea, with energy | `build` |
| Flip a myth to a reality | `reframe` |
| Emphasize a key phrase | `highlight` |
| Hit one hard beat | `punch` |
| Define a term | `define` |
| List a few points (no process) | `list` |
| Land one big number | `stat` |
| Land a proportion as an arc | `ring` |
| Show a few related numbers | `statgrid` |
| Show "X% of…" | `progress` |
| Show "N of M" concretely | `pictograph` |
| Show change over time | `trend` |
| Show a before → after value | `delta` |
| Compare a few quantities | `diagram` |
| Rank a few items (long labels) | `ranked` |
| Contrast two states/options | `compare` |
| Walk through a process | `steps` |
| Show dated milestones | `timeline` |
| Show start → +/- → end | `waterfall` |
| Position on two axes | `matrix` |
| Quote someone verbatim | `quote` |
| Show a real source figure | `figure` |
| Close | `payoff` |

**Anti-monotony:** the palette is large on purpose — *vary the device to the message.* Across
a 10–15 slide deck, aim to use **5+ distinct device types** and never repeat the same data
device twice unless the data genuinely demands it. Reaching for the same bar chart (or the same
text slide) twice reads as templated.

**Dwell budget:** most devices read in a 2–5s dwell. `waterfall` and `matrix` carry the most to
parse — the engine auto-fits their geometry to the aspect (no manual per-aspect tuning needed),
but they still want **≥ 5s** and the readability guidance in their entries above.

## Roadmap (not yet implemented)
- **section** — a chapter/act divider (big index + title) to break a long deck into parts.
- **fill** — a fill-in-the-blank reveal ("the best time to ship was ▁▁▁" → answer drops in).
- **checklist** — a do/don't tick-vs-cross variant (would likely be a `list` mode, not a new device).
- Pie charts: **intentionally excluded** (hard to read on a phone; McKinsey banned them). Single-
  series arcs are fine — see `ring`.
