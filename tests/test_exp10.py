"""Experiment 10 (case A, Baserow #6069) repairs, on a synthetic importer of the same shape:
nested functions with closure scope, comprehension scope, the mechanics frontier,
runtime-only sites (unanchored, not contradicting), episode-scoped absence, coverage of
every observed site of the change, and top-level calls the genome does not model."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from diffgenome.dependence import analyze_all
from diffgenome.frontends.python_ir import lower_functions
from diffgenome.genome import HYPOTHESIS, REJECTED, SUPPORTED, Substrate, genome_from_proposals
from diffgenome.genome_state import (
    Mechanics,
    Observations,
    StateSubstrate,
    change_sites,
    compare_sequence,
    establish_state,
    predict_sequence,
)
from diffgenome.model import BranchObs, CallNode, Execution, Stimulus
from diffgenome.mvp import mechanics_frontier

SRC = """
def importer(items, sink):
    by_name = {f.name: f for f in items}
    pending = []

    def expand(deps):
        if not deps:
            return deps
        return {lookup(d, sink) for d in deps}

    for it in items:
        deps = expand(it.deps)
        if deps:
            pending.append(it)
        else:
            build(it, by_name)
    finish(pending)
"""


def _facts() -> dict[str, dict[str, Any]]:
    return {f["symbol"]: f for f in analyze_all(lower_functions(SRC, "m.py", "m"))}


def _site(pred: str) -> str:
    return next(s for s in Mechanics(list(_facts().values())).sites.values() if s["pred"] == pred)[
        "site"
    ]


def test_nested_function_is_lowered_with_closure_scope() -> None:
    f = _facts()
    assert set(f) == {"py:m.importer", "py:m.importer.<locals>.expand"}
    outer, inner = f["py:m.importer"], f["py:m.importer.<locals>.expand"]
    assert outer["unknown"] == []  # the nested def is a local definition, not opaque
    assert [s["pred"] for s in inner["sites"]] == ["not deps"]
    lookup = next(c for c in inner["calls"] if c["callee"] == "lookup")
    # `d` is the comprehension's element; `sink` is read from the enclosing function
    assert lookup["arg_origins"][1] == ["closure:sink"]
    assert not any("global:d" in o for a in lookup["arg_origins"] for o in a)
    # comprehension targets are not globals of the enclosing function
    build = next(c for c in outer["calls"] if c["callee"] == "build")
    assert not any(o.startswith("global:f") for a in build["arg_origins"] for o in a)


# ---- a run: item 1 has no deps (built now), item 2 has deps (deferred, built by finish)


def _run(test: str = "t/run") -> Execution:
    nd, dp = _site("not deps"), _site("deps")
    nodes = (
        CallNode(0, None, "py:test", 0),
        CallNode(1, 0, "py:m.importer", 0),
        CallNode(2, 1, "py:m.importer.<locals>.expand", 0),
        CallNode(3, 1, "py:m.build", 0),
        CallNode(4, 1, "py:m.importer.<locals>.expand", 0),
        CallNode(5, 4, "py:m.lookup", 0),
        CallNode(6, 1, "py:m.finish", 0),
        CallNode(7, 6, "py:m.build", 0),  # the deferred build
    )
    branches = (
        BranchObs(nd, True, 2, 3),
        BranchObs(dp, False, 1, 3),
        BranchObs(nd, False, 4, 5),
        BranchObs(dp, True, 1, 6),
    )
    return Execution(
        test, Stimulus.EXISTING_TEST, test, "passed", None, (), (), nodes, branches=branches
    )


def _decision(did: str, entity: str, site: str, pred: str, **branches: Any) -> dict[str, Any]:
    return {
        "id": did,
        "entity": entity,
        "site": site,
        "predicate": pred,
        "true_branch": branches.get("t", {}),
        "false_branch": branches.get("f", {}),
        "evidence": [{"kind": "source", "file": "m.py", "line": 7, "text": "if not deps:"}],
    }


def _establish(tmp_path: Path, decisions: list[dict[str, Any]], mech: Mechanics | None = None):  # type: ignore[no-untyped-def]
    (tmp_path / "m.py").write_text(SRC)
    obs = Observations([_run()])
    sub = StateSubstrate(
        Substrate([], set(), tmp_path, set()), mech or Mechanics(list(_facts().values())), obs
    )
    return establish_state(genome_from_proposals({"decisions": decisions}, {}, "m"), sub)


def test_absence_is_judged_per_episode_not_over_the_rest_of_the_run(tmp_path: Path) -> None:
    nd, dp = _site("not deps"), _site("deps")
    ok = [
        # deferred now: not built in this iteration (finish builds it later)
        _decision("defer", "importer", dp, "has_deps", t={"absent": ["build"]}),
        # empty deps: expand returns before any lookup (a later iteration looks up)
        _decision("empty", "expand", nd, "!has_deps", t={"absent": ["lookup"]}),
    ]
    g = _establish(tmp_path, ok)
    assert [d.status for d in g.decisions] == [SUPPORTED, SUPPORTED], [
        d.status_reason for d in g.decisions
    ]
    # the same claims over the whole run are contradicted, as before
    run_scope = [{**d, "true_branch": {**d["true_branch"], "absent_scope": "run"}} for d in ok]
    g = _establish(tmp_path, run_scope)
    assert [d.status for d in g.decisions] == [REJECTED, REJECTED]
    # a wrong claim inside the episode is still caught: built right away when deps is empty
    wrong = [_decision("defer", "importer", dp, "has_deps", f={"absent": ["build"]})]
    assert _establish(tmp_path, wrong).decisions[0].status == REJECTED


def test_runtime_only_site_is_unanchored_not_contradicted(tmp_path: Path) -> None:
    nd = _site("not deps")
    outer_only = Mechanics([_facts()["py:m.importer"]])  # the nested function not lowered
    d = _decision("empty", "expand", nd, "!has_deps", t={"absent": ["lookup"]})
    d["evidence"].append({"kind": "branch", "site": nd, "test": "t/run", "outcome": True})
    g = _establish(tmp_path, [d], outer_only)
    assert g.decisions[0].status == SUPPORTED
    assert "observed at runtime, no static facts" in g.decisions[0].status_reason
    # a site nobody knows: the evidence does not check out, but nothing contradicts it
    d2 = _decision("x", "expand", nd, "!has_deps")
    d2["evidence"] = [
        {"kind": "branch", "site": "br:000000000000", "test": "t/run", "outcome": True}
    ]
    g = _establish(tmp_path, [d2], outer_only)
    assert g.decisions[0].status == HYPOTHESIS


def test_every_observed_site_of_the_change_is_scored() -> None:
    mech = Mechanics(list(_facts().values()))
    obs = Observations([_run()])
    required = change_sites(mech, obs, ["py:m.importer"])
    assert required == {_site("not deps"), _site("deps")}  # the nested function's too
    g = genome_from_proposals(
        {
            "decisions": [_decision("defer", "importer", _site("deps"), "has_deps")],
            "procedures": [{"id": "P", "entity": "importer", "steps": ["D:defer"]}],
        },
        {},
        "m",
    )
    for it in (*g.decisions, *g.procedures):
        it.status = SUPPORTED
    sc = {"calls": [{"entity": "importer", "facts": {"has_deps": False}}]}
    r = compare_sequence(g, predict_sequence(g, sc), obs.get("t/run"), {_site("deps")}, required)
    assert r["uncovered_sites"] == [_site("not deps")]
    assert r["indeterminate"] and not r["match"]


def test_unmodeled_top_level_call_is_skipped_unless_it_has_decisions() -> None:
    g = genome_from_proposals(
        {
            "decisions": [_decision("defer", "importer", _site("deps"), "has_deps")],
            "procedures": [{"id": "P", "entity": "expand", "steps": []}],
        },
        {},
        "m",
    )
    for it in (*g.decisions, *g.procedures):
        it.status = SUPPORTED
    p = predict_sequence(g, {"calls": [{"entity": "setup"}, {"entity": "expand"}]})
    assert p.indeterminate is None and ("call", "setup") in p.events
    p = predict_sequence(g, {"calls": [{"entity": "importer"}]})
    assert p.indeterminate and "has decisions" in p.indeterminate


def test_mechanics_frontier_is_the_changed_code_direct_callees() -> None:
    front = mechanics_frontier([_run()], ["py:m.importer"])
    # direct callees of the changed function and of its nested function; not build's
    # callee under finish (two calls away)
    assert front == {"py:m.importer.<locals>.expand", "py:m.build", "py:m.lookup", "py:m.finish"}
