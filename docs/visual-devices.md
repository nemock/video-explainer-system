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
| Land one big number | `stat` |
| Show a few related numbers | `statgrid` |
| Show "X% of…" | `progress` |
| Compare a few quantities | `diagram` |
| Contrast two states/options | `compare` |
| Walk through a process | `steps` |
| Quote someone verbatim | `quote` |
| Show a real source figure | `figure` |
| Close | `payoff` |

**Anti-monotony:** across a 10–15 slide deck, aim to use **4+ distinct device types**. Never
repeat the same data device (`diagram`/`stat`/`progress`) twice unless the data demands it.

## Roadmap (not yet implemented)
- **waterfall** — A→B with contributing +/- factors ("how we close the gap"). Deferred: needs
  >5s dwell to parse, marginal for short-form.
- **2×2 matrix** — positioning quadrant. Deferred: same dwell-time concern.
- Pie charts: **intentionally excluded** (hard to read on a phone; McKinsey banned them).
