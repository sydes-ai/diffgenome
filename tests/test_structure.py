"""Experiment 10 v3: observed execution structure (occurrences, skeleton) and the checks built
on it. A synthetic importer: it scans, then per item expands (a helper frame outside the
vocabulary sits between), maybe calls a hook inside the expansion, decides, maybe defers;
then finishes."""

from __future__ import annotations

from typing import Any

from diffgenome.genome import REJECTED, SUPPORTED, VERIFIED, genome_from_proposals
from diffgenome.genome_state import (
    Observations,
    compare_sequence,
    predict_sequence,
    procedure_structure_claims,
)
from diffgenome.model import BranchObs, CallNode, Execution, Stimulus
from diffgenome.structure import ROOT, build_skeleton, occurrences, placement_problems

VOCAB = ["m.importer", "m.expand", "m.hook", "m.add", "m.finish"]
SCAN, DEFER, EMPTY, HOOKED = "br:scan", "br:defer", "br:empty", "br:hooked"


def _ex(name: str) -> Execution:
    nodes = (
        CallNode(0, None, "py:test", 0),
        CallNode(1, 0, "py:m.importer", 0, outcome="returned"),
        CallNode(2, 1, "py:m.helper", 0),  # outside the vocabulary: looked through
        CallNode(3, 2, "py:m.expand", 0),
        CallNode(4, 3, "py:m.hook", 0),
        CallNode(5, 1, "py:m.add", 0),
        CallNode(6, 1, "py:m.expand", 0),
        CallNode(7, 1, "py:m.finish", 0),
    )
    branches = (
        BranchObs(SCAN, True, 1, 2),
        BranchObs(EMPTY, False, 3, 4),
        BranchObs(HOOKED, True, 4, 5),
        BranchObs(DEFER, True, 1, 5),
        BranchObs(EMPTY, True, 6, 7),
        BranchObs(DEFER, False, 1, 7),
    )
    return Execution(
        name, Stimulus.EXISTING_TEST, name, "passed", None, (), (), nodes, branches=branches
    )


def test_occurrences_nest_by_nearest_modeled_caller_and_order_events_by_time() -> None:
    occ = occurrences(_ex("t/a"), VOCAB)
    assert {o.entity for o in occ.values()} == set(VOCAB)
    assert occ[3].parent == 1 and occ[3].ancestors == ["m.importer"]  # helper looked through
    assert (occ[3].ordinal, occ[6].ordinal) == (0, 1)  # repeated calls stay distinct
    assert occ[4].parent == 3 and occ[1].parent is None
    fams = [f for _, f, _ in occ[1].events]
    assert fams == [
        f"site:{SCAN}", "m.expand", f"site:{DEFER}", "m.add", "m.expand", f"site:{DEFER}",
        "m.finish",
    ]  # fmt: skip
    assert occ[1].outcome == "returned"


def test_skeleton_phases_regions_and_placement() -> None:
    sk = build_skeleton([_ex("t/a"), _ex("t/b")], VOCAB)
    assert sk.parents["m.expand"] == {"m.importer": 2}
    assert sk.parents["m.importer"] == {ROOT: 2}
    assert sk.always_during("m.hook", "m.expand") and sk.always_during("m.expand", "m.importer")
    assert sk.strictly_before("m.importer", f"site:{SCAN}", "m.expand")
    assert sk.strictly_before("m.importer", "m.expand", "m.finish")
    (region,) = sk.regions["m.importer"]
    assert region["head"] == "m.expand"
    assert set(region["members"]) == {"m.expand", f"site:{DEFER}", "m.add"}
    assert (f"site:{DEFER}", "m.add") in region["within"]
    assert sk.site_owner[DEFER] == {"m.importer": 4}


def _tree(*occ: tuple[str, int | None, list[tuple[str, str]]]) -> list[dict[str, Any]]:
    return [{"entity": e, "parent": p, "events": ev} for e, p, ev in occ]


def test_placement_problems_flag_hoisting_wrong_function_and_reversed_order() -> None:
    sk = build_skeleton([_ex("t/a"), _ex("t/b")], VOCAB)
    ok = _tree(
        ("m.importer", None, [("branch", f"site:{SCAN}"), ("call", "m.expand"),
                              ("branch", f"site:{DEFER}"), ("call", "m.finish")]),
        ("m.expand", 0, [("branch", f"site:{EMPTY}")]),
        ("m.finish", 0, []),
    )  # fmt: skip
    assert placement_problems(ok, sk) == []
    hoisted = _tree(("m.importer", None, []), ("m.expand", None, []))
    assert any("outside every modeled caller" in p for p in placement_problems(hoisted, sk))
    wrong_fn = _tree(("m.importer", None, [("call", "m.expand")]),
                     ("m.expand", 0, [("branch", f"site:{DEFER}")]))  # fmt: skip
    assert any("never evaluated there" in p for p in placement_problems(wrong_fn, sk))
    reversed_ = _tree(("m.importer", None, [("call", "m.finish"), ("branch", f"site:{SCAN}")]))
    assert any("observed after" in p for p in placement_problems(reversed_, sk))
    in_repetition = _tree(
        ("m.importer", None, [("call", "m.expand"), ("call", "m.add"), ("branch", f"site:{DEFER}")])
    )
    assert any("one repetition" in p for p in placement_problems(in_repetition, sk))


def _genome(procedures: list[dict[str, Any]]) -> Any:
    rows = (
        ("d_scan", "m.importer", SCAN, "x"),
        ("d_defer", "m.importer", DEFER, "y"),
        ("d_empty", "m.expand", EMPTY, "z"),
    )
    decisions = [{"id": d, "entity": e, "site": s, "predicate": v} for d, e, s, v in rows]
    return genome_from_proposals({"decisions": decisions, "procedures": procedures}, {}, "m")


def test_structure_claims_reject_only_on_positive_evidence() -> None:
    sk = build_skeleton([_ex("t/a"), _ex("t/b")], VOCAB)
    status = {
        c["claim"]: c["status"]
        for c in procedure_structure_claims(
            _genome(
                [
                    {"id": "P1", "entity": "m.importer",
                     "steps": ["D:d_scan", "call:m.expand", "call:m.finish"]},
                    {"id": "P2", "entity": "m.expand",
                     "steps": ["D:d_empty", "D:d_defer", "call:m.importer", "call:m.never"]},
                    {"id": "P3", "entity": "m.finish", "steps": ["call:m.hook"]},
                    {"id": "P4", "entity": "m.importer", "steps": ["call:m.finish", "D:d_scan"]},
                ]
            ),
            sk,
        )
    }  # fmt: skip
    assert status["m.expand during m.importer"] == VERIFIED
    assert status["site:br:scan before m.expand in m.importer"] == VERIFIED
    # a decision of the function that encloses expand, placed inside expand: inverted
    assert status["d_defer (br:defer) evaluated during m.expand"] == REJECTED
    assert status["m.importer during m.expand"] == REJECTED  # nesting inverted
    assert status["m.never during m.expand"] == "unobserved"
    # absence is not a contradiction: hook never ran during finish, nothing inverted
    assert status["m.hook during m.finish"] == "not established"
    assert status["m.finish before site:br:scan in m.importer"] == REJECTED


def test_a_hoisted_scenario_is_indeterminate_not_wrong() -> None:
    sk = build_skeleton([_ex("t/a"), _ex("t/b")], VOCAB)
    g = _genome(
        [
            {"id": "P0", "entity": "m.importer", "steps": ["D:d_scan"]},
            {"id": "P", "entity": "m.expand", "steps": ["D:d_empty"]},
        ]
    )
    for it in (*g.decisions, *g.procedures):
        it.status = SUPPORTED
    # expand is hoisted out of importer, where every observed expand ran
    sc = {
        "calls": [
            {"entity": "m.importer", "facts": {"x": True}},
            {"entity": "m.expand", "facts": {"z": True}},
        ]
    }
    ob = Observations([_ex("t/a")]).get("t/a")
    r = compare_sequence(g, predict_sequence(g, sc), ob, {EMPTY}, skeleton=sk)
    assert r["indeterminate"] and r["indeterminate"].startswith("placement")
    assert not r["match"]


def test_a_family_never_observed_repeating_is_not_predicted_repeating() -> None:
    sk = build_skeleton([_ex("t/a"), _ex("t/b")], VOCAB)
    twice = _tree(("m.importer", None, [("call", "m.finish"), ("call", "m.finish")]))
    assert any("never observed repeating" in p for p in placement_problems(twice, sk))
    # a member of a repeated region may repeat: its count follows the supplied occurrences
    region_member = _tree(("m.importer", None, [("call", "m.expand"), ("call", "m.expand")]))
    assert not any("never observed repeating" in p for p in placement_problems(region_member, sk))
