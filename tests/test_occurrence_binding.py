"""Per-occurrence fact binding for a repeated region (docs/design-occurrence-binding.md), on
the synthetic importer of tests/test_structure.py: two repetitions inside one importer call,
the first with dependencies (hook runs, deferred), the second without (imported now)."""

from __future__ import annotations

import copy
from typing import Any

from diffgenome.genome import REJECTED, SUPPORTED, VERIFIED, genome_from_proposals
from diffgenome.genome_state import (
    Observations,
    compare_sequence,
    predict_sequence,
    procedure_structure_claims,
)
from diffgenome.structure import build_skeleton
from tests.test_structure import DEFER, EMPTY, SCAN, VOCAB, _ex

SITES = {SCAN, EMPTY, DEFER}


def _proposals() -> dict[str, Any]:
    return {
        "variables": [{"id": "V1", "name": "deps_present"}, {"id": "V2", "name": "deferred"}],
        "decisions": [
            {"id": "d_scan", "entity": "m.importer", "site": SCAN, "predicate": "scan"},
            {
                "id": "d_empty",
                "entity": "m.expand",
                "site": EMPTY,
                "predicate": "!deps_present",
                "true_branch": {"stops": True},
                "false_branch": {"calls": ["m.hook"]},
            },
            {
                "id": "d_defer",
                "entity": "m.importer",
                "site": DEFER,
                "predicate": "deferred",
                "true_branch": {"calls": ["m.add"]},
            },
        ],
        "regions": [
            {
                "id": "R",
                "entity": "m.importer",
                "head": "m.expand",
                "steps": ["call:m.expand", "D:d_defer"],
            },
        ],
        "procedures": [
            {"id": "P", "entity": "m.importer", "steps": ["D:d_scan", "R:R", "call:m.finish"]},
            {"id": "PE", "entity": "m.expand", "steps": ["D:d_empty"]},
        ],
    }


def _scenario(items: list[dict[str, Any]] | None) -> dict[str, Any]:
    call: dict[str, Any] = {"entity": "m.importer", "facts": {"scan": True}}
    if items is not None:
        call["occurrences"] = {"R": items}
    return {"calls": [call]}


CORRECT = [
    {"facts": {"deps_present": True, "deferred": True}},
    {"facts": {"deps_present": False, "deferred": False}},
]


def _run(proposals: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    g = genome_from_proposals(proposals, {}, "m")
    for it in (*g.decisions, *g.procedures, *g.regions):
        it.status = SUPPORTED
    sk = build_skeleton([_ex("t/a"), _ex("t/b")], VOCAB)
    ob = Observations([_ex("t/a")]).get("t/a")
    pred = predict_sequence(g, scenario)
    r = compare_sequence(g, pred, ob, SITES, skeleton=sk, scenario=scenario)
    r["_state"] = pred.state
    return r


def test_one_body_with_per_occurrence_facts_predicts_the_observed_repetitions() -> None:
    r = _run(_proposals(), _scenario(CORRECT))
    assert r["match"], r
    assert r["occurrence_checks"]["confirmed"] == 4 and r["occurrence_checks"]["contradicted"] == 0
    # occurrence facts do not leak out of their occurrence
    assert "deps_present" not in r["_state"] and "deferred" not in r["_state"]


def test_permuted_occurrence_facts_are_caught_not_predicted() -> None:
    r = _run(_proposals(), _scenario(list(reversed(CORRECT))))
    assert not r["match"]
    assert r["indeterminate"] and r["indeterminate"].startswith("occurrence facts contradicted")
    assert r["occurrence_checks"]["contradicted"] == 4


def test_wrong_count_and_missing_occurrences() -> None:
    r = _run(_proposals(), _scenario([*CORRECT, CORRECT[0]]))
    assert r["indeterminate"] and "3 occurrence(s) supplied, 2 observed" in r["indeterminate"]
    r = _run(_proposals(), _scenario(None))
    assert r["indeterminate"] == "occurrence facts not supplied for region R"


def test_region_structure_claims() -> None:
    sk = build_skeleton([_ex("t/a"), _ex("t/b")], VOCAB)
    claims = procedure_structure_claims(genome_from_proposals(_proposals(), {}, "m"), sk)
    by = {c["claim"]: c["status"] for c in claims}
    assert by["region R: repetitions of m.importer start with m.expand"] == VERIFIED
    assert by["m.expand before site:br:defer in one repetition of R"] == VERIFIED
    assert by["site:br:scan before m.expand in m.importer"] == VERIFIED  # placed by its head
    bad = copy.deepcopy(_proposals())
    bad["regions"][0]["head"] = "m.finish"  # observed once per importer call: not a region
    by = {
        c["claim"]: c["status"]
        for c in procedure_structure_claims(genome_from_proposals(bad, {}, "m"), sk)
    }
    assert by["region R: repetitions of m.importer start with m.finish"] == REJECTED


def test_inverted_predicate_is_contested_at_the_occurrences() -> None:
    """With per-occurrence facts, a decision over input facts has something to disagree
    with: its predicate on an occurrence's supplied facts vs the outcome observed there. A
    disagreement cannot be pinned on the predicate or the fact, so the decision is demoted
    (contested), and predictions that need it stop."""
    from pathlib import Path

    from diffgenome.genome import HYPOTHESIS, Substrate
    from diffgenome.genome_state import Mechanics, StateSubstrate, establish_state

    bad = copy.deepcopy(_proposals())
    bad["decisions"][2]["predicate"] = "!deferred"  # d_defer inverted
    for d in bad["decisions"]:
        d["evidence"] = [{"kind": "branch", "site": d["site"], "test": "t/a", "outcome": True}]
    obs = Observations([_ex("t/a"), _ex("t/b")])
    sub = StateSubstrate(Substrate([], set(), Path("."), set()), Mechanics([]), obs)
    g = establish_state(
        genome_from_proposals(bad, {}, "m"),
        sub,
        scenarios={"t/a": _scenario(CORRECT), "t/b": _scenario(CORRECT)},
    )
    d_defer = next(d for d in g.decisions if d.id == "d_defer")
    assert d_defer.status == HYPOTHESIS and d_defer.status_reason.startswith("contested")
    d_scan = next(d for d in g.decisions if d.id == "d_scan")
    assert d_scan.status != HYPOTHESIS


def test_a_transition_inside_a_region_body_persists_after_the_occurrence() -> None:
    """Regression (V-F2): only the occurrence's supplied facts are local; what the body's
    transitions set (a match found in one repetition) is its effect and persists."""
    p = _proposals()
    p["transitions"] = [{"id": "T_found", "entity": "m.importer", "when": "deferred",
                         "sets": {"any_deferred": "true"}}]  # fmt: skip
    p["regions"][0]["steps"] = ["call:m.expand", "D:d_defer", "T:T_found"]
    g = genome_from_proposals(p, {}, "m")
    for it in (*g.decisions, *g.procedures, *g.regions, *g.transitions):
        it.status = SUPPORTED
    pred = predict_sequence(g, _scenario(CORRECT))
    assert pred.state.get("any_deferred") is True
    assert "deferred" not in pred.state  # the supplied fact itself stays local
