"""Step 2 (design sections 5.1 and 5.5): boundary bindings and Outcome.

A synthetic hook returns a value when its input is known and None otherwise; an entry
calls it. The pre-change-style control (the hook implies nothing) must be rejected by
identity-level facts at the hook's boundary alone, and outcomes are read from observed
call exits, never from test results."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any

from diffgenome.dependence import analyze_all
from diffgenome.frontends.python_ir import lower_functions
from diffgenome.genome import REJECTED, SUPPORTED, VERIFIED, Substrate, genome_from_proposals
from diffgenome.genome_state import (
    Mechanics,
    Observations,
    StateSubstrate,
    boundary_fact,
    compare_sequence,
    establish_state,
    exit_matches,
    predict_sequence,
)
from diffgenome.model import BranchObs, CallNode, Execution, Stimulus

SRC = """
def hook(ref, targets):
    if ref not in targets:
        return None
    return (targets[ref], ref)


def load(items):
    run(items)
"""


def _d(c: str) -> str:
    return hashlib.sha256(c.encode()).hexdigest()[:16]


NONE = _d("NoneType:None")


def _mech() -> Mechanics:
    return Mechanics(analyze_all(lower_functions(SRC, "m.py", "m")))


def _site() -> str:
    return next(iter(_mech().sites))


def _run(load_exit: str = "returned") -> Execution:
    site = _site()
    nodes = (
        CallNode(0, None, "py:test", 0),
        CallNode(1, 0, "py:m.load", 0, (("items", "list[2]", _d("x")),), outcome=load_exit),
        CallNode(
            2,
            1,
            "py:m.hook",
            0,
            (("ref", "str", _d("str:'a'")), ("targets", "dict[1]", "")),
            outcome="returned",
            result=_d("tuple[...]"),
        ),
        CallNode(
            3,
            1,
            "py:m.hook",
            0,
            (("ref", "str", _d("str:'b'")), ("targets", "dict[1]", "")),
            outcome="returned",
            result=NONE,
        ),
    )
    branches = (BranchObs(site, False, 2, 3), BranchObs(site, True, 3, 4))
    return Execution(
        "t/run", Stimulus.EXISTING_TEST, "t/run", "passed", None, (), (), nodes, branches=branches
    )


def _src(line: int, text: str) -> dict[str, Any]:
    return {"kind": "source", "file": "m.py", "line": line, "text": text}


def _proposals() -> dict[str, Any]:
    return {
        "variables": [
            {"id": "V_known", "name": "known", "origin": "input", "evidence": [_src(3, "ref")]},
            {
                "id": "V_impl",
                "name": "implied",
                "origin": "derived",
                "observed_as": {"at": {"entity": "hook", "point": "result"}, "kind": "is_set"},
                "evidence": [_src(5, "return")],
            },
        ],
        "decisions": [
            {
                "id": "D",
                "entity": "hook",
                "site": _site(),
                "predicate": "!known",
                "true_branch": {"stops": True},
                "false_branch": {"steps": ["T:T1"]},
                "evidence": [_src(3, "if ref not in targets:")],
            }
        ],
        "transitions": [
            {
                "id": "T1",
                "entity": "hook",
                "when": "known",
                "sets": {"implied": "true"},
                "evidence": [_src(5, "return (targets[ref], ref)")],
            }
        ],
        "procedures": [
            {"id": "P", "entity": "hook", "steps": ["D:D"], "evidence": [_src(3, "if ref")]}
        ],
    }


def _establish(tmp_path: Path, proposals: dict[str, Any], run: Execution | None = None):  # type: ignore[no-untyped-def]
    (tmp_path / "m.py").write_text(SRC)
    sub = StateSubstrate(
        Substrate([], set(), tmp_path, set()), _mech(), Observations([run or _run()])
    )
    return establish_state(genome_from_proposals(proposals, {}, "m"), sub)


def test_boundary_facts_are_decided_from_shapes_and_digests() -> None:
    ex = _run()
    set_hook, none_hook = ex.nodes[2], ex.nodes[3]
    assert boundary_fact(set_hook, "result", "is_set") is True
    assert boundary_fact(none_hook, "result", "is_set") is False
    assert boundary_fact(set_hook, "arg:targets", "size") == 1
    assert boundary_fact(set_hook, "result", "changed_from:arg:ref") is True
    assert boundary_fact(set_hook, "arg:targets", "is_set") is True  # no digest, but a shape
    assert boundary_fact(set_hook, "arg:missing", "is_set") is None
    go_nil = CallNode(9, None, "go:x", 0, (("v", "nil", ""),))
    assert boundary_fact(go_nil, "arg:v", "is_set") is False


def test_exit_matching_uses_the_collector_taxonomy() -> None:
    assert exit_matches("raised:DataError", "raised:py:django.db.utils.DataError") is True
    assert exit_matches("raised:django.db.utils.DataError", "raised:py:django.db.utils.DataError")
    assert exit_matches("completed", "returned") is True
    assert exit_matches("returned_error", "returned-error:go:*errors.errorString") is True
    assert exit_matches("returned", "raised:py:ValueError") is False
    assert exit_matches("raised:KeyError", "raised:py:builtins.ValueError") is False
    assert exit_matches("returned", "unknown") is None


def test_transition_is_verified_at_the_boundary_along_the_observed_path(tmp_path: Path) -> None:
    g = _establish(tmp_path, _proposals())
    t1 = g.transitions[0]
    # `known` is an unbound input, so the entry state cannot decide the path; the replay
    # follows the observed outcome of the site (false = known) and reaches T1
    assert t1.status == VERIFIED, t1.status_reason


def test_pre_change_style_control_is_rejected_by_boundary_facts(tmp_path: Path) -> None:
    c2 = copy.deepcopy(_proposals())
    c2["transitions"][0]["sets"] = {"implied": "false"}  # "the reference implies nothing"
    t1 = _establish(tmp_path, c2).transitions[0]
    assert t1.status == REJECTED and "observed True, predicted False" in t1.status_reason


def test_branch_and_procedure_outcomes_are_checked_against_observed_exits(
    tmp_path: Path,
) -> None:
    p = _proposals()
    p["decisions"][0]["true_branch"]["outcome"] = {"entity": "load", "is": "raised:ValueError"}
    assert _establish(tmp_path, p).decisions[0].status == REJECTED
    p["decisions"][0]["true_branch"]["outcome"] = {"entity": "load", "is": "returned"}
    assert _establish(tmp_path, p).decisions[0].status == SUPPORTED
    q = _proposals()
    q["procedures"][0]["outcome"] = {"is": "returned"}
    proc = _establish(tmp_path, q).procedures[0]
    assert proc.status == SUPPORTED and "observed in 1 call" in proc.status_reason
    q["procedures"][0]["outcome"] = {"is": "raised:KeyError"}
    assert _establish(tmp_path, q).procedures[0].status == REJECTED


def test_boundary_and_outcome_evidence(tmp_path: Path) -> None:
    p = _proposals()
    p["variables"][1]["evidence"] = [
        {"kind": "boundary", "entity": "hook", "point": "result", "binding": "is_set",
         "value": True, "test": "t/run"},
        {"kind": "outcome", "entity": "load", "exit": "raised:DataError", "test": "t/run"},
    ]  # fmt: skip
    v = _establish(tmp_path, p, _run("raised:py:django.db.utils.DataError")).variables[1]
    assert v.status == SUPPORTED, v.status_reason
    v = _establish(tmp_path, p).variables[1]  # load returned: the outcome ref fails
    assert v.status == REJECTED


def test_predicted_outcomes_are_compared_per_entity() -> None:
    p = _proposals()
    p["procedures"][0]["outcome"] = {"is": "returned"}
    g = genome_from_proposals(p, {}, "m")
    for it in (*g.decisions, *g.transitions, *g.procedures):
        it.status = SUPPORTED
    sc = {"calls": [{"entity": "hook", "facts": {"known": True}},
                    {"entity": "hook", "facts": {"known": False}}]}  # fmt: skip
    ob = Observations([_run()]).get("t/run")
    r = compare_sequence(g, predict_sequence(g, sc), ob, {_site()})
    assert r["match"] and r["outcome_diff"] == {}
    g.procedures[0].outcome = {"is": "raised:KeyError"}
    r = compare_sequence(g, predict_sequence(g, sc), ob, {_site()})
    assert not r["match"] and "hook" in r["outcome_diff"]
