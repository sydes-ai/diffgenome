"""Experiment 09 substrate: stable decision-site identity, runtime branch outcomes, local
def-use and control requirements, observed state deltas, and the state-genome checker."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from diffgenome.collect.py_monitoring import if_sites
from diffgenome.dependence import analyze_all
from diffgenome.frontends.python_ir import lower_functions
from diffgenome.genome import HYPOTHESIS, REJECTED, VERIFIED, Substrate, genome_from_proposals
from diffgenome.genome_state import (
    Mechanics,
    Observations,
    StateSubstrate,
    establish_state,
    predict_sequence,
)
from diffgenome.model import BranchObs, CallNode, Execution, Stimulus
from diffgenome.sites import site_id
from tests.test_collector import REPO, trace

SRC = """
class Meter:
    def __init__(self):
        self.count = 0
        self.open = False

    def tick(self, amount, limit):
        n = amount
        if not self.open:
            return "closed"
        if n > limit:
            raise ValueError("too much")
        self.count = self.count + n
        for i in range(n):
            helper(i)
        return self.count

    def toggle(self):
        self.open = not self.open
"""


def _facts() -> dict[str, dict[str, Any]]:
    fns = lower_functions(SRC, "m.py", "m")
    return {f["symbol"].rsplit(".", 1)[-1]: f for f in analyze_all(fns)}


def test_local_def_use_and_control_requirements() -> None:
    tick = _facts()["tick"]
    closed, limit = tick["sites"]
    assert closed["pred"] == "not self.open"
    assert closed["operands"] == [{"path": "self.open", "origins": ["param:self.open"]}]
    # n := amount, so the second decision depends on the parameter through a local
    assert {o["path"]: o["origins"] for o in limit["operands"]} == {
        "limit": ["param:limit"],
        "n": ["param:amount"],
    }
    # early-exit guards: everything after them requires both to be false
    assert limit["requires"] == [[closed["site"], False]]
    store = tick["stores"][0]
    assert store["path"] == "self.count" and store["requires"] == [
        [closed["site"], False],
        [limit["site"], False],
    ]
    # the loop body is control dependent on an unknown (loop) condition, said so explicitly
    helper = next(c for c in tick["calls"] if c["callee"] == "helper")
    assert ["?loop", None] in helper["requires"]
    assert any("UNKNOWN_DEPENDENCE:loop-variable" in o for o in helper["arg_origins"][0])


def test_site_identity_is_the_same_statically_and_at_runtime() -> None:
    static = {s["site"] for f in _facts().values() for s in f["sites"]}
    runtime = {s.site for s in if_sites(SRC, "m.py")}
    assert static == runtime and len(static) == 2
    assert site_id("m.py", (9, 12, 9, 25)) in static  # `not self.open`, 1-based columns


@pytest.fixture(scope="module")
def exp07(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Execution]:
    return trace(REPO / "fixtures" / "exp07_state", tmp_path_factory.mktemp("br"))


def test_python_branch_outcomes_and_state_deltas(exp07: dict[str, Execution]) -> None:
    src = (REPO / "fixtures/exp07_state/proc/processor.py").read_text()
    sites = {
        s.site: src.splitlines()[s.test[0][0] - 1].strip()
        for s in if_sites(src, "proc/processor.py")
    }
    disabled = exp07["test_run_disabled_skips"]
    got = [(sites[b.site], b.outcome) for b in disabled.branches if b.site in sites]
    assert got == [("if not self.enabled:", True)]  # the condition's value, not the jump direction
    strict = exp07["test_run_enabled_strict_audits"]
    assert [(sites[b.site], b.outcome) for b in strict.branches if b.site in sites] == [
        ("if not self.enabled:", False),
        # the false outcome leaves validate() through its implicit `return None`, which the
        # compiler places at the condition: it was dropped before 0.1.9 (wemake #3810)
        ("if not item:", False),
        ("if settings.STRICT:", True),
    ]
    run = next(
        n for n in strict.nodes if isinstance(n, CallNode) and n.symbol.endswith("Processor.run")
    )
    before, after = (
        dict((a, b) for a, b, _ in run.state),
        dict((a, b) for a, b, _ in run.state_after),
    )
    assert (before["self.seen"], after["self.seen"]) == ("num:zero", "num:pos")
    assert before["global.settings.STRICT"] == "bool:true"
    # a branch is ordered against the calls around it
    assert all(b.seq <= len(strict.nodes) for b in strict.branches)


# ---- the state-genome checker and predictor on a synthetic counter


def _mech() -> Mechanics:
    return Mechanics(analyze_all(lower_functions(SRC, "m.py", "m")))


def _exec(test: str, open_: bool, outcome: bool) -> Execution:
    mech = _mech()
    closed = next(s for s in mech.sites.values() if s["pred"] == "not self.open")["site"]
    root = CallNode(0, None, "py:test", 0)
    tick = CallNode(
        1,
        0,
        "py:m.Meter.tick",
        0,
        state=(("self.open", f"bool:{str(open_).lower()}", ""), ("self.count", "num:zero", "")),
        state_after=(
            ("self.open", f"bool:{str(open_).lower()}", ""),
            ("self.count", "num:zero" if not open_ else "num:pos", ""),
        ),
    )
    return Execution(
        test,
        Stimulus.EXISTING_TEST,
        test,
        "passed",
        None,
        (),
        (),
        (root, tick),
        branches=(BranchObs(closed, outcome, 1, 2),),
    )


def _proposals(**over: Any) -> dict[str, Any]:
    mech = _mech()
    closed = next(s for s in mech.sites.values() if s["pred"] == "not self.open")["site"]
    d = {
        "id": "D",
        "entity": "Meter.tick",
        "site": closed,
        "predicate": "!is_open",
        "order": 0,
        "true_branch": {"steps": [], "stops": True},
        "false_branch": {"steps": ["T:T1"], "stops": False},
        "evidence": [{"kind": "source", "file": "m.py", "line": 9, "text": "if not self.open:"}],
    }
    d.update(over)
    return {
        "variables": [
            {
                "id": "V1",
                "name": "is_open",
                "origin": "state",
                "observed_as": {"fact": "self.open", "kind": "bool"},
                "evidence": [{"kind": "source", "file": "m.py", "line": 9, "text": "self.open"}],
            },
            {
                "id": "V2",
                "name": "count",
                "origin": "state",
                "observed_as": {"fact": "self.count", "kind": "sign"},
                "evidence": [{"kind": "source", "file": "m.py", "line": 13, "text": "self.count"}],
            },
        ],
        "decisions": [d],
        "transitions": [
            {
                "id": "T1",
                "entity": "Meter.tick",
                "when": "true",
                "sets": {"count": "count + 1"},
                "evidence": [{"kind": "store", "entity": "Meter.tick", "path": "self.count"}],
            },
            {
                "id": "T2",
                "entity": "Meter.toggle",
                "when": "true",
                "sets": {"is_open": "!is_open"},
                "evidence": [{"kind": "store", "entity": "Meter.toggle", "path": "self.open"}],
            },
        ],
        "procedures": [
            {
                "id": "P1",
                "entity": "Meter.tick",
                "steps": ["D:D"],
                "evidence": [
                    {"kind": "source", "file": "m.py", "line": 9, "text": "if not self.open:"}
                ],
            },
            {
                "id": "P2",
                "entity": "Meter.toggle",
                "steps": ["T:T2"],
                "evidence": [
                    {
                        "kind": "source",
                        "file": "m.py",
                        "line": 19,
                        "text": "self.open = not self.open",
                    }
                ],
            },
        ],
    }


def _establish(tmp_path: Path, proposals: dict[str, Any]):  # type: ignore[no-untyped-def]
    (tmp_path / "m.py").write_text(SRC)
    obs = Observations([_exec("t/open", True, False), _exec("t/closed", False, True)])
    sub = StateSubstrate(Substrate([], set(), tmp_path, set()), _mech(), obs)
    return establish_state(genome_from_proposals(proposals, {}, "m"), sub)


def test_decision_verified_by_local_agreement_and_transition_by_delta(tmp_path: Path) -> None:
    g = _establish(tmp_path, _proposals())
    assert g.decisions[0].status == VERIFIED, g.decisions[0].status_reason
    assert "observed state" in g.decisions[0].status_reason
    t1 = next(t for t in g.transitions if t.id == "T1")
    assert t1.status == VERIFIED and "where the procedure applies it" in t1.status_reason


def test_inverted_decision_rejected_at_its_own_site(tmp_path: Path) -> None:
    g = _establish(tmp_path, _proposals(predicate="is_open"))
    assert g.decisions[0].status == REJECTED and "observed state" in g.decisions[0].status_reason


def test_fabricated_site_is_a_hypothesis(tmp_path: Path) -> None:
    g = _establish(tmp_path, _proposals(site="br:000000000000"))
    assert g.decisions[0].status == HYPOTHESIS


def test_state_sequence_prediction_and_missing_transition(tmp_path: Path) -> None:
    g = _establish(tmp_path, _proposals())
    for it in (*g.procedures, *g.transitions):
        it.status = VERIFIED
    # closed meter: tick stops; toggle opens it; the next tick counts
    pred = predict_sequence(
        g,
        {
            "state": {"is_open": False, "count": 0},
            "calls": [
                {"entity": "Meter.tick"},
                {"entity": "Meter.toggle"},
                {"entity": "Meter.tick"},
            ],
        },
    )
    assert [e[2] for e in pred.events if e[0] == "branch"] == [True, False]
    assert pred.state == {"is_open": True, "count": 1}
    # without the toggle's transition the later behavior is not predictable, and says so
    g.transitions = [t for t in g.transitions if t.id != "T2"]
    pred = predict_sequence(
        g,
        {
            "state": {"is_open": False, "count": 0},
            "calls": [
                {"entity": "Meter.tick"},
                {"entity": "Meter.toggle"},
                {"entity": "Meter.tick"},
            ],
        },
    )
    assert pred.indeterminate and "T2" in pred.indeterminate


def test_runtime_site_ids_are_repository_relative_under_a_nested_source_root(
    tmp_path: Path,
) -> None:
    """Experiment 10 (Baserow, F2): with the source root below the repository root
    (backend/src), runtime site ids must hash the repository-relative path, as the static
    front end does. The plugin used the first source root as the repository root."""
    import subprocess
    import sys

    from diffgenome.serialize import execution_from_json
    from diffgenome.sites import site_id

    repo = tmp_path / "repo"
    (repo / "backend/src/pkg").mkdir(parents=True)
    (repo / "backend/tests").mkdir(parents=True)
    (repo / "backend/src/pkg/__init__.py").write_text("")
    (repo / "backend/src/pkg/mod.py").write_text(
        "def f(x):\n    if x > 1:\n        return 1\n    return 0\n"
    )
    (repo / "backend/tests/test_m.py").write_text(
        "from pkg.mod import f\n\n\ndef test_f():\n    assert f(2) == 1\n"
    )
    src_dir = Path(__file__).resolve().parents[1] / "src"
    out = tmp_path / "out"
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "-p", "diffgenome.collect.pytest_plugin", "--diffgenome-out", str(out),
         "--diffgenome-repo-root", ".", "--diffgenome-source-root", "backend/src",
         "--diffgenome-test-root", "backend/tests", "backend/tests"],
        cwd=repo, capture_output=True, text=True,
        env={"PYTHONPATH": f"backend/src:{src_dir}", "PATH": "/usr/bin:/bin"},
    )  # fmt: skip
    assert r.returncode == 0, r.stdout + r.stderr
    ex = execution_from_json(next(out.glob("*.json")).read_text())
    expected = site_id("backend/src/pkg/mod.py", (2, 8, 2, 13))
    assert [(b.site, b.outcome) for b in ex.branches] == [(expected, True)]
