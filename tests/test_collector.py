"""The CPython collector, exercised end to end on the exp01 fixture and on a synthetic fake.

These pin the observed behaviors that experiment 01 relies on (S4, S5, S12) so that a
regression is a failed test, not a re-discovered anecdote."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from diffgenome.model import (
    CallNode,
    Execution,
    Origin,
    SubstitutionMechanism,
    SubstitutionNode,
)
from diffgenome.serialize import execution_from_json, execution_to_json

REPO = Path(__file__).parent.parent
FIXTURE = REPO / "fixtures" / "exp01_shop"


def trace(target: Path, out: Path, test_root: str = "tests") -> dict[str, Execution]:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(REPO / "src")}
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
            "-p", "diffgenome.collect.pytest_plugin",
            "--diffgenome-out", str(out),
            "--diffgenome-source-root", ".",
            "--diffgenome-test-root", test_root,
        ],
        cwd=target, env=env, capture_output=True, text=True,
    )  # fmt: skip
    assert result.returncode == 0, result.stdout + result.stderr
    executions = [execution_from_json(f.read_text()) for f in sorted(out.glob("*.json"))]
    return {e.stimulus_ref.split("::")[-1]: e for e in executions}


@pytest.fixture(scope="module")
def fixture_traces(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Execution]:
    return trace(FIXTURE, tmp_path_factory.mktemp("fx"))


def calls(execution: Execution) -> dict[str, list[CallNode]]:
    out: dict[str, list[CallNode]] = {}
    for n in execution.nodes:
        if isinstance(n, CallNode):
            out.setdefault(n.symbol, []).append(n)
    return out


def substitutions(execution: Execution) -> list[SubstitutionNode]:
    return [n for n in execution.nodes if isinstance(n, SubstitutionNode)]


def test_s4_observed_chain_and_standin_attribution(fixture_traces: dict[str, Execution]) -> None:
    ex = fixture_traces["test_place_order_returns_quoted_total"]
    c = calls(ex)
    place_order = c["py:shop.controller.OrderController.place_order"][0]
    place = c["py:shop.order_service.OrderService.place"][0]
    validate = c["py:shop.order_service._validate"][0]
    assert place.parent == place_order.id and validate.parent == place.id

    subs = substitutions(ex)
    assert [s.parent for s in subs] == [place.id, place.id]
    assert [s.path for s in subs] == [("reserve",), ("quote",)]
    assert all(s.mechanism is SubstitutionMechanism.MOCK_OBJECT for s in subs)
    assert all(s.args == (("arg0", "list[2]"),) for s in subs)  # single positional argument


def test_s5_join_key_agrees_between_claim_and_frame(fixture_traces: dict[str, Execution]) -> None:
    seed = fixture_traces["test_place_order_returns_quoted_total"]
    fragment = fixture_traces["test_quote_sums_repository_prices"]
    claim = next(s for s in substitutions(seed) if s.path == ("quote",)).claimed_target
    real = calls(fragment)["py:shop.pricing_service.PricingService.quote"][0]
    assert claim == real.symbol
    assert {s.id: s.origin for s in fragment.symbols}[real.symbol] is Origin.REPO


def test_external_claim_names_the_defining_module(fixture_traces: dict[str, Execution]) -> None:
    ex = fixture_traces["test_quote_sums_repository_prices"]
    subs = substitutions(ex)
    assert {s.claimed_target for s in subs} == {"py:sqlite3.Connection.execute"}
    assert {s.path for s in subs} == {("execute",), ("execute", "()", "fetchone")}
    assert all(s.relation == "spec" for s in subs)


def test_claimless_standins_claim_nothing(fixture_traces: dict[str, Execution]) -> None:
    subs = substitutions(fixture_traces["test_place_with_unspecced_mocks"])
    assert len(subs) == 2
    assert all(s.claimed_target is None and s.relation == "none" for s in subs)


def test_s12_determinism(tmp_path: Path) -> None:
    a = trace(FIXTURE, tmp_path / "a")
    b = trace(FIXTURE, tmp_path / "b")
    assert {k: execution_to_json(v) for k, v in a.items()} == {
        k: execution_to_json(v) for k, v in b.items()
    }


def test_fake_is_a_substitution_that_executes(tmp_path: Path) -> None:
    """Item 2 of the guardrails: a hand-written fake is a stand-in *and* runs code."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "svc.py").write_text(
        "class Service:\n"
        "    def __init__(self, repo): self.repo = repo\n"
        "    def run(self): return self.repo.save(1)\n"
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_fake.py").write_text(
        "from pkg.svc import Service\n"
        "def _helper(x): return x + 1\n"
        "class FakeRepo:\n"
        "    def save(self, x): return _helper(x)\n"
        "def test_run(): assert Service(FakeRepo()).run() == 2\n"
    )
    (tmp_path / "pytest.ini").write_text("[pytest]\npythonpath = .\n")
    ex = trace(tmp_path, tmp_path / "out")["test_run"]

    [fake] = substitutions(ex)
    assert fake.mechanism is SubstitutionMechanism.FAKE
    assert fake.substitute == "py:tests.test_fake.FakeRepo.save"
    assert fake.claimed_target is None
    run = calls(ex)["py:pkg.svc.Service.run"][0]
    assert fake.parent == run.id
    save = calls(ex)["py:tests.test_fake.FakeRepo.save"][0]
    helper = calls(ex)["py:tests.test_fake._helper"][0]
    assert save.parent == fake.id and helper.parent == save.id  # not a leaf


def test_outcomes_are_observed_for_calls_and_standins(fixture_traces: dict[str, Execution]) -> None:
    raised = fixture_traces["test_duplicate_skus_rejected"]
    c = calls(raised)
    assert c["py:shop.order_service._validate"][0].outcome == "raised:py:builtins.ValueError"
    assert (
        c["py:shop.order_service.OrderService.place"][0].outcome == "raised:py:builtins.ValueError"
    )
    assert c["py:shop.order_service.OrderService.__init__"][0].outcome == "returned"

    seed = fixture_traces["test_place_order_returns_quoted_total"]
    assert {s.outcome for s in substitutions(seed)} == {"returned"}
