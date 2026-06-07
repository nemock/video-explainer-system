"""Editorial rubric — the twice-gated checklist (ARCHITECTURE §8.5, PRD FR-13). A checklist
artifact in the manifest, not vibes. The *scoring* is Claude's judgment (the `/deepdive` skill
self-critiques against these prompts); this module defines the checklists, records the verdicts
into the manifest, runs the structural-variety guard, and computes assembly readiness.

Two gates:
  - PLAN (before recording): is this worth making, and is the plan sound?
  - FILM (before publish): does the assembled master hold up end-to-end?
"""
import json
from pathlib import Path

from . import manifest as mf

# Each item: a key + the question Claude must answer (pass/fail + a note). Kept terse on purpose —
# the skill expands them with the program's specifics.
PLAN_RUBRIC = [
    ("transformative_outcome", "Is the viewer's transformative outcome named (what they can DO after)? (D9)"),
    ("benefit_forward_headline", "Does the title sell the transformation, not the topic? (D9)"),
    ("hook_strength", "Does the cold open (10–20s) state the payoff/stakes + the primary open loop?"),
    ("open_loops", "Are there 2–3 planted open loops, each with a tagged payoff beat? (no danglers)"),
    ("act_balance", "Is the act balance within tolerance (default ~15/55/30), not extreme?"),
    ("mece_horizontal_logic", "Read alone, do the act/sub-segment titles tell the argument end-to-end?"),
    ("beat_variety", "Variety of devices/beats — not the same chart/structure repeated?"),
    ("why_watch_this", "Is there a crisp one-line reason to watch THIS over the alternatives?"),
]
FILM_RUBRIC = [
    ("retention_read", "Watched end-to-end: pacing holds, no stretch that loses the viewer?"),
    ("seam_check", "Act↔interstitial seams: voice/energy continuous, no jarring tonal break?"),
    ("callbacks_paid", "Every planted open loop is paid off (open-loop/payoff ledger clean)?"),
    ("no_dead_air", "No redundancy or dead air; every beat earns its time?"),
    ("sponsor_tease", "Pre-sponsor 'coming up after this' teases present where expected?"),
    ("packaging_present", "Title variants + thumbnail chosen?"),
]


def checklist(kind):
    items = PLAN_RUBRIC if kind == "plan" else FILM_RUBRIC
    return [{"key": k, "question": q, "pass": None, "note": ""} for k, q in items]


def record(program, manifest, kind, results, *, approved, notes=""):
    """Store a filled checklist + the verdict. `results` is the list of {key, pass, note} dicts.
    `approved` is the operator/skill's overall verdict (all material items pass)."""
    r = manifest.setdefault("rubric", {})
    r[f"{kind}_checklist"] = {"items": results, "notes": notes}
    r[f"{kind}_approved"] = bool(approved)
    mf.write(program, manifest)
    return r


def set_arc(program, manifest, *, hook_archetype, three_act_rhythm, payoff_type):
    """Record this film's structural fingerprint for the variety guard."""
    manifest.setdefault("rubric", {})["arc"] = {
        "hook_archetype": hook_archetype, "three_act_rhythm": three_act_rhythm,
        "payoff_type": payoff_type}
    mf.write(program, manifest)


def variety_check(program, *, last_n=5):
    """Structural-variety guard (§8.5): compare this program's arc against the last N sibling
    programs' arcs; warn on formulaic sameness. Sibling programs = other dirs alongside this one."""
    this_arc = (mf.load(program).get("rubric") or {}).get("arc")
    siblings = []
    parent = program.dir.parent
    for d in sorted(parent.glob("*"), reverse=True):
        if d == program.dir or not (d / "program-manifest.json").exists():
            continue
        try:
            arc = json.loads((d / "program-manifest.json").read_text()).get("rubric", {}).get("arc")
            if arc:
                siblings.append({"program": d.name, "arc": arc})
        except (json.JSONDecodeError, OSError):
            pass
        if len(siblings) >= last_n:
            break
    warnings = []
    if this_arc:
        for s in siblings:
            same = [k for k in ("hook_archetype", "three_act_rhythm", "payoff_type")
                    if s["arc"].get(k) and s["arc"][k] == this_arc.get(k)]
            if len(same) >= 2:
                warnings.append({"vs": s["program"], "repeats": same})
    return {"arc": this_arc, "compared": len(siblings), "warnings": warnings,
            "ok": not warnings}


def assembly_ready(manifest):
    """The 'assembly gates on approved' rule (§5/§8.5): the plan must be approved and every
    non-interstitial act segment must be `approved` (not merely rendered). Returns (ok, reasons)."""
    reasons = []
    if not (manifest.get("rubric") or {}).get("plan_approved"):
        reasons.append("plan rubric not approved (deepdive approve-plan)")
    for sid, seg in manifest["segments"].items():
        if seg.get("kind") != "interstitial" and seg.get("review_status") != "approved":
            reasons.append(f"segment '{sid}' not approved (status={seg.get('review_status')})")
    return (not reasons, reasons)


def content_plan_template(program):
    """The content-plan.md scaffold (throughline spine + open-loop ledger + rubric stubs). The
    skill fills it in; it's the human-readable companion to the manifest's rubric block (§8.2)."""
    return f"""# Content Plan — {program.title}

> The editorial spine for this deep-dive. Author this BEFORE recording. The manifest's `rubric`
> block is the machine-checkable companion; this file is where the argument lives.

## Transformative outcome (D9)
_What can the viewer DO after watching that they couldn't before? Teach toward THIS, not the topic._

## Benefit-forward title (working)
_Sells the transformation, not the topic. 3–5 variants get authored at packaging (2.5)._

## Throughline spine
- **Thesis:** _the one argument the whole film makes_
- **Why watch this:** _one line — why THIS over the alternatives_

## Open-loop / payoff ledger
| id | open loop (planted in…) | payoff beat (paid off in…) |
|----|-------------------------|----------------------------|
| L1 | cold-open               | act-3                      |
| L2 |                         |                            |

## Act structure (default ~15/55/30; warn only on extreme lopsidedness)
- **Cold open (10–20s):** _payoff/stakes + primary open loop_
- **Act I — ___** · sub-segments (idea boundaries, ~60–90s each):
  - sub-01: _idea_ → hand-off line: "_…_"
- **fwf-sponsor** (pre-sponsor tease at end of Act I: "_coming up…_")
- **Act II — ___** · sub-segments:
- **thebuild-sponsor**
- **Act III — ___** · sub-segments:
- **CTA**

## Shot list (Adobe Stock / screenshots to source)
_Search prompts for B-roll to review; downloaded assets enter the catalog with license + id._

## Structural-variety note
_Hook archetype / three-act rhythm / payoff type — set via `deepdive set-arc` so the variety
guard can compare against recent films._
"""
