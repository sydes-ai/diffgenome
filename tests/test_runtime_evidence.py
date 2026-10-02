"""The `diffgenome-runtime/1` contract: observed facts about changed functions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from diffgenome.change import ChangedRange, ChangeSet
from diffgenome.model import (
    BranchObs,
    CallNode,
    Collector,
    Execution,
    Fidelity,
    Origin,
    Plane,
    SourceLocation,
    Stimulus,
    SubstitutionMechanism,
    SubstitutionNode,
    Symbol,
)
from diffgenome.runtime_evidence import FORMAT, build_runtime_evidence


@dataclass
class _Def:
    symbol: str
    path: str
    start: int
    end: int
    kind: str


class _Index:
    defs: ClassVar[dict[str, _Def]] = {
        "py:app.handler": _Def("py:app.handler", "app.py", 1, 5, "function"),
        "py:app.service": _Def("py:app.service", "app.py", 10, 20, "function"),
        "py:app.unused": _Def("py:app.unused", "app.py", 30, 35, "function"),
        "py:app.Model": _Def("py:app.Model", "app.py", 40, 50, "class"),
        "py:tests.test_x": _Def("py:tests.test_x", "tests/test_x.py", 1, 9, "function"),
    }

    def find(self, s: str) -> _Def | None:
        return self.defs.get(s)

    def is_test(self, s: str) -> bool:
        return s.startswith("py:tests.")


def _ex(ref: str, outcome_of_service: str, branch: bool, mock: bool) -> Execution:
    nodes: list = [
        CallNode(0, None, "py:tests.test_x", 0, outcome="returned"),
        CallNode(1, 0, "py:app.handler", 0, outcome="returned"),
        CallNode(2, 1, "py:app.deco.<locals>.wrapper", 0, outcome="returned"),
        CallNode(
            3, 2, "py:app.service", 0, args=(("amount", "int", "ab"),), outcome=outcome_of_service
        ),
    ]
    if mock:
        nodes.append(
            SubstitutionNode(4, 3, 0, SubstitutionMechanism.MOCK_OBJECT, None, "py:db.save", "attr")
        )
    syms = tuple(
        Symbol(
            s, Origin.TEST if s.startswith("py:tests") else Origin.REPO, SourceLocation("app.py", 1)
        )
        for s in (
            "py:tests.test_x",
            "py:app.handler",
            "py:app.deco.<locals>.wrapper",
            "py:app.service",
        )
    )
    return Execution(
        id=ref,
        stimulus=Stimulus.EXISTING_TEST,
        stimulus_ref=ref,
        outcome="passed",
        revision=None,
        collectors=(Collector("py", Plane.SYMBOL, Fidelity.COMPLETE),),
        symbols=syms,
        nodes=tuple(nodes),
        branches=(BranchObs("br:1", branch, 3, 1),),
    )


def _change() -> ChangeSet:
    return ChangeSet(
        "test",
        [ChangedRange("app.py", frozenset({3, 12, 31, 41}))],
        ["py:app.handler", "py:app.service", "py:app.unused", "py:app.Model", "py:tests.test_x"],
        [],
    )


MECH = [{"symbol": "py:app.service", "sites": [{"site": "br:1", "line": 12, "pred": "amount > 0"}]}]


def test_contract_reports_execution_tests_exits_shapes_and_edges() -> None:
    execs = [_ex("t::a", "returned", True, False), _ex("t::b", "raised:py:ValueError", True, True)]
    r = build_runtime_evidence(execs, _change(), _Index(), MECH, [], test_scope="tests/")
    assert r["format"] == FORMAT and r["universe"]["executions"] == 2
    assert r["universe"]["test_scope"] == "tests/"
    fns = {f["symbol"]: f for f in r["changed_functions"]}
    # classes and test code are not changed functions
    assert set(fns) == {"py:app.handler", "py:app.service", "py:app.unused"}
    svc = fns["py:app.service"]
    assert svc["executed"] and svc["calls"] == 2 and svc["tests"] == ["t::a", "t::b"]
    assert svc["exits"] == {"returned": 1, "raised:py:ValueError": 1}
    assert svc["arg_shapes"] == [[["amount", "int"]]]
    assert svc["origin"] == "repo"
    assert (
        next(e for e in r["edges"] if e["caller"]["symbol"] == "py:tests.test_x")["caller"][
            "origin"
        ]
        == "test"
    )
    # the decorator wrapper is looked through: handler is the real caller
    assert [c["symbol"] for c in svc["callers"]] == ["py:app.handler"]
    assert {(e["caller"]["symbol"], e["callee"]["symbol"]) for e in r["edges"]} == {
        ("py:tests.test_x", "py:app.handler"),
        ("py:app.handler", "py:app.service"),
    }
    assert svc["stand_ins"] == {"py:db.save": 1}
    assert svc["changed_sites"] == [
        {"site": "br:1", "line": 12, "predicate": "amount > 0", "true": 2, "false": 0}
    ]


def test_gaps_are_observable_kinds_only() -> None:
    r = build_runtime_evidence([_ex("t::a", "returned", True, True)], _change(), _Index(), MECH, [])
    kinds = {(g["kind"], g["symbol"]) for g in r["gaps"]}
    assert ("function_not_executed", "py:app.unused") in kinds
    assert ("branch_outcome_not_observed", "py:app.service") in kinds
    assert ("stand_in_reached", "py:app.service") in kinds
    missing = next(g for g in r["gaps"] if g["kind"] == "branch_outcome_not_observed")
    assert missing["outcome"] == "false" and missing["line"] == 12
    assert "values (only type shapes and opaque fingerprints are recorded)" in r["not_reported"]


def test_no_executions_means_every_changed_function_not_executed() -> None:
    r = build_runtime_evidence([], _change(), _Index(), MECH, [])
    assert all(not f["executed"] for f in r["changed_functions"])
    assert {g["kind"] for g in r["gaps"]} == {"function_not_executed"}


def test_import_time_calls_count_as_executed_but_credit_no_test() -> None:
    """requests._check_cryptography runs when the package is imported (conftest, collection):
    executed, flagged ran_at_import, and never attributed to a test."""
    imp = Execution(
        id="imp",
        stimulus=Stimulus.EXISTING_TEST,
        stimulus_ref="py:<import>",
        outcome="passed",
        revision=None,
        collectors=(Collector("py", Plane.SYMBOL, Fidelity.COMPLETE),),
        symbols=(),
        nodes=(CallNode(0, None, "py:<import>", 0), CallNode(1, 0, "py:app.unused", 0)),
        branches=(),
    )
    r = build_runtime_evidence(
        [_ex("t::a", "returned", True, False), imp], _change(), _Index(), MECH, []
    )
    fns = {f["symbol"]: f for f in r["changed_functions"]}
    assert fns["py:app.unused"]["executed"] and fns["py:app.unused"]["ran_at_import"]
    assert fns["py:app.unused"]["tests"] == [] and fns["py:app.service"]["ran_at_import"] is False
    assert r["universe"]["executions"] == 1 and [t["id"] for t in r["universe"]["tests"]] == [
        "t::a"
    ]
    assert not any(g["kind"] == "function_not_executed" for g in r["gaps"])
