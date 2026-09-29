# ruff: noqa: E501
"""Experiment 10, case A, v4: the v3 bundle (Outcome, boundary bindings, observed execution
structure) plus REPEATED REGIONS WITH PER-OCCURRENCE FACTS (docs/design-occurrence-binding.md).
Relations, derived order and iteration remain unavailable. Withheld traces never inform it.

usage: build_context_exp10d.py <head-run> <base-run> <out-dir>
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import build_context_exp10b as v2
import build_context_exp10c as v3

FORMAT_REGIONS = """ "regions": [{"id", "entity": "<the enclosing function>", "head": "<the observed family that starts each repetition: a function name or site:br:...>",
              "steps": ["call:<entity>", "T:<transition id>", "D:<decision id>", ...], "evidence": [...]}],
 "procedures": [{"id", "entity", "steps": ["call:<entity>", "T:<transition id>", "D:<decision id>", "R:<region id>", ...],"""

SCENARIO_CALLS = """                               "calls": [{"entity": "<entity>", "facts": {<variable>: value},
                                          "occurrences": {"<region id>": [{"facts": {<variable>: value}}, ...]}}],"""

REGIONS = """**Repeated regions and occurrence facts.** Repeated region placement is supplied by mechanics.
Concrete occurrence facts are supplied by the scenario. Do not invent occurrence count, nesting
or order. A region (`regions`) is ONE body that runs once per occurrence of an OBSERVED repeated
region of its enclosing function (`entity`); its `head` must be the family that the observed
structure says starts every repetition, and its steps must follow the observed order inside one
repetition. The enclosing function's procedure places it with the step `"R:<region id>"`. The
genome never states how many times a region runs: a scenario's call of the enclosing function
supplies `occurrences: {"<region id>": [...]}`, one item per concrete occurrence in order, each
with that occurrence's facts (read them from the test's input; the k-th item is the k-th
repetition). For the shown tests the checker aligns your k-th item with the observed k-th
repetition and checks every fact it can observe there (boundary facts of the calls inside it,
and variables your atomic decisions `v` / `!v` bind from their observed outcomes); a
contradicted fact or a wrong count makes that prediction indeterminate.

**Not available** (deliberately): relation-valued variables, derived orders, iteration over
collections (loop variables, item identity across calls). If the behavior needs them, say so
precisely in `unknowns`; do not simulate them with per-instance variable names."""

PREDICTOR = """  with `stops: true` ends the entity (inside a region too: there is no `continue`). "R:id"
  runs region id once per occurrence the current scenario call supplies, in order: that
  occurrence's facts hold during its body only (they are restored afterwards; variables bound
  to receiver/global state persist); a region with no supplied occurrences stops the prediction.
  Predicates: booleans/integers, `!name`, comparisons, `&&`, `||`, no parentheses. A scenario
  lists every entry call, in order, with the facts that hold for that call and, for repeated
  regions inside it, per-occurrence facts."""


def patch() -> None:
    s = v2.INSTRUCTIONS
    old_proc = """ "procedures": [{"id", "entity", "steps": ["call:<entity>", "T:<transition id>", "D:<decision id>", ...],"""
    assert old_proc in s
    s = s.replace(old_proc, FORMAT_REGIONS)
    old_calls = """                               "calls": [{"entity": "<entity>", "facts": {<variable>: value}}],"""
    assert old_calls in s
    s = s.replace(old_calls, SCENARIO_CALLS)
    i = s.index("**Not available** (deliberately)")
    j = s.index("Semantics used by the predictor:")
    s = s[:i] + REGIONS + "\n\n" + s[j:]
    old_pred = s[s.index("  with `stops: true` ends the entity.") : s.index("- SCORING covers")]
    s = s.replace(old_pred, PREDICTOR + "\n")
    v2.INSTRUCTIONS = s
    v3.RULES = v3.RULES.replace(
        "The format has no loops: if you cannot\nexpress a repetition inside its enclosing function without violating these constraints, say\nso in `unknowns` rather than hoisting it.",
        "Express a repetition inside its enclosing function as a region (see Repeated regions and occurrence facts, above), never by hoisting it.",
    )
    assert "as a region (see" in v3.RULES
    v3.RULES = v3.RULES.replace("**Not available** (deliberately)", "**Not available**")


if __name__ == "__main__":
    patch()
    # v3.main injects RULES before the "Not available" paragraph and adds the structure section
    raise SystemExit(v3.main())
