# Deep-Dive — Brain query / promote recipe (Phase 1.3)

How the FWF deep-dive uses the shared `cb` knowledge vault. **Library-first**: every run
reads the brain before it touches the web, and promotes durable findings back when it ships.

- **Vault:** `/Volumes/Casima/claudeCode/make_money/brain/` (cb, `default` profile). Shared
  across FWF, MedTech Monday, Founder Tip Tuesday, the daily carousel, and the deep-dive.
- **Per-video staging (scratch):** `deep-dive/programs/<slug>/research/` — raw notes, this
  topic's competitor scan, downloaded stock/screenshots. Stays local; never the brain.
- **CLIs:** `cb` (`~/.local/bin/cb`). Node creation is by the `intake` / `atomize` skills
  (they write schema'd markdown); `cb` itself reads/validates/maintains.

## What's seeded (the library-first floor)
Anchored to `source-dave-byline-library` (provenance), from the byline editorial thesis +
research roster:
- **6 audience archetypes** → `persona` nodes (`entities/personas/`, namespace `audiences`,
  tag `archetype`): second-time-operator, quietly-profitable-operator, services-firm-owner,
  family-business-steward, senior-operator-crossroads, indie-builder.
- **4 named frameworks** → `concept` nodes (`concepts/`, namespace `frameworks`):
  order-of-operations-test, walk-away-condition, three-numbers, foundational-hire-signal.
- **16 research sources** → `source` nodes (`sources/`, namespace `research-roster`,
  `source_kind: citation`): Lenny's, First Round Review, Stratechery, Farnam Street, etc.

Re-seed (idempotent): `python3 ~/.claude/explainer-brands/dave-byline/seed_brain_byline.py`
then `cd <vault> && cb validate --fix && cb maintain repair`.

## QUERY pattern (library-first — before any web research)
1. **Frame the beat** (topic + which audience archetype it serves).
2. **Pull the relevant nodes first.** Prefer the **`query` skill** (staged retrieval, pillar
   auto-inject, typed-edge traversal, node-id citations). Raw equivalents:
   - `cb list-nodes --type persona` / `--type concept` / `--type source` → candidate ids.
   - `cb get-node <id>` → full frontmatter + body + both-direction edges for the chosen nodes.
3. **Author against the library.** Persona node = who the beat serves (pain/want/voice).
   Framework concepts = the named IP to lean on. Roster sources = where to research next.
4. **Cite the graph.** Reference node ids in the script's working notes so provenance is
   traceable and the editorial rubric (§8.5) can check claims.
5. **Only then go to the web** (WebSearch/WebFetch on the roster) for what the brain lacks —
   re-verify each roster source is reachable at the start of the run; flag/drop dormant ones.

## PROMOTE pattern (`intake` / `atomize` — when a video ships)
**Promote, not dump.** Scratch and drafts stay in `programs/<slug>/research/`; only knowledge
the *next* piece (any format) would reuse graduates to the brain:
- New **sourced facts** discovered during research → `fact` nodes (cite the roster `source`).
- A new **named framework** Dave coins → `concept` node (namespace `frameworks`).
- A rights-clean reusable **asset** or the produced piece itself → `source` node.
- A **what-worked** pattern (hook, structure, pacing that landed) → `pattern` node.
Use the **`atomize`** skill for documents (it lands an immutable source node + derived typed
nodes via `derived_from` edges) or **`intake`** for interactive capture. Then
`cb validate --fix && cb maintain repair` to wire inverse edges + rebuild `INDEX.md`.

## Guardrails
- The brain holds **durable, cross-format** knowledge; per-video scratch never enters it.
- Brain content is operator-specific and **gitignored** — it is not in the public engine repo.
- Confidence + `staleness_signal` are set on every node so `cb maintain decay` can age
  volatile facts; re-verify roster sources each run.
