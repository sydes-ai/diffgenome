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
    assert all(s.args[0][:2] == ("arg0", "list[2]") for s in subs)  # single positional argument


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


def test_p12_unsummarizable_values_leave_digest_empty() -> None:
    """A digest is all-or-nothing: an object we cannot canonicalize yields "", never a
    partial digest that could make two different values look equal."""
    from diffgenome.collect.py_monitoring import digest_value

    class Opaque:
        pass

    assert digest_value("BOOK-001") == digest_value("BOOK-001") != digest_value("UNKNOWN")
    assert digest_value(["A", "B"]) != digest_value(["B", "A"])
    assert digest_value({"A", "B"}) == digest_value({"B", "A"})
    assert digest_value(Opaque()) == ""
    assert digest_value([1, Opaque()]) == ""
    assert digest_value(list(range(17))) == ""  # beyond the bounded width


def test_results_are_digested(fixture_traces: dict[str, Execution]) -> None:
    fragment = fixture_traces["test_quote_sums_repository_prices"]
    quote = calls(fragment)["py:shop.pricing_service.PricingService.quote"][0]
    seed = fixture_traces["test_place_order_returns_quoted_total"]
    stand_in = next(s for s in substitutions(seed) if s.path == ("quote",))
    assert quote.result and quote.result == stand_in.result  # both 2500
    raised = calls(fixture_traces["test_duplicate_skus_rejected"])
    assert raised["py:shop.order_service.OrderService.place"][0].result == ""


def test_patch_interposition_claims_the_original(tmp_path: Path) -> None:
    """`patch("pkg.svc.load")` replaces a module attribute with a spec-less mock. The
    patcher saved the original, so the stand-in's claim is a fact, not an inference."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "svc.py").write_text(
        "def load(key): return {'k': key}\n"
        "def run(key): return load(key)['k']\n"
        "def chain(key): return load(key).get('k')\n"
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_patch.py").write_text(
        "from unittest.mock import patch\n"
        "from pkg import svc\n"
        "def test_run():\n"
        "    with patch('pkg.svc.load') as load:\n"
        "        load.return_value = {'k': 'v'}\n"
        "        assert svc.run('a') == 'v'\n"
        "        assert svc.chain('a') == 'v'\n"
    )
    (tmp_path / "pytest.ini").write_text("[pytest]\npythonpath = .\n")
    ex = trace(tmp_path, tmp_path / "out")["test_run"]

    subs = substitutions(ex)
    assert [s.mechanism for s in subs] == [SubstitutionMechanism.INTERPOSITION] * 2
    assert {s.claimed_target for s in subs} == {"py:pkg.svc.load"}
    assert {s.relation for s in subs} == {"patch-target"}
    assert [s.path for s in subs] == [("load",), ("load",)]
    assert [s.args[0][:2] for s in subs] == [("arg0", "str"), ("arg0", "str")]
    run = calls(ex)["py:pkg.svc.run"][0]
    assert subs[0].parent == run.id
    assert {s.id: s.origin for s in ex.symbols}["py:pkg.svc.load"] is Origin.REPO


def test_generator_consumers_are_attributed_by_frame_ancestry(tmp_path: Path) -> None:
    """While a generator is suspended, calls made by its consumer belong to the consumer.
    A shadow stack parents them under the generator; frame ancestry does not."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "g.py").write_text(
        "def leaf(): return 1\n"
        "def gen():\n"
        "    yield leaf()\n"
        "    yield leaf()\n"
        "def other(): return leaf()\n"
        "def consumer():\n"
        "    return [other() for _ in gen()]\n"
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_g.py").write_text(
        "from pkg.g import consumer\ndef test_consumer(): assert consumer() == [1, 1]\n"
    )
    (tmp_path / "pytest.ini").write_text("[pytest]\npythonpath = .\n")
    ex = trace(tmp_path, tmp_path / "out")["test_consumer"]

    c = calls(ex)
    consumer = c["py:pkg.g.consumer"][0]
    gen = c["py:pkg.g.gen"][0]
    assert gen.parent == consumer.id
    assert all(o.parent == consumer.id for o in c["py:pkg.g.other"])
    assert {leaf.parent for leaf in c["py:pkg.g.leaf"]} == {
        gen.id,
        *(o.id for o in c["py:pkg.g.other"]),
    }
    diagnostics = dict(ex.diagnostics)
    assert int(diagnostics["attribution_disagreements"]) >= 2  # the shadow stack was wrong
    assert gen.outcome == "returned"


def test_observer_is_not_hijacked_by_target_patches(tmp_path: Path) -> None:
    """A target that patches os.path.join must not rename the collector's symbols. On
    Kokoro-FastAPI, pathlib inside the collector picked up the target's patch and named a
    function after the test's temp file, differently on every run."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "io.py").write_text(
        "import os\ndef where(name): return os.path.join('/base', name)\n"
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_io.py").write_text(
        "from unittest.mock import patch\n"
        "from pkg.io import where\n"
        "def test_where():\n"
        "    with patch('os.path.join', return_value='/tmp/hijacked/x.json'):\n"
        "        assert where('a') == '/tmp/hijacked/x.json'\n"
    )
    (tmp_path / "pytest.ini").write_text("[pytest]\npythonpath = .\n")
    ex = trace(tmp_path, tmp_path / "out")["test_where"]

    assert "py:pkg.io.where" in calls(ex)
    assert not any(s.id.startswith("py:/") or "hijacked" in s.id for s in ex.symbols)
    [sub] = substitutions(ex)
    assert sub.mechanism is SubstitutionMechanism.INTERPOSITION
    assert sub.claimed_target == "py:posixpath.join"
    assert {s.id: s.origin for s in ex.symbols}["py:posixpath.join"] is Origin.EXTERNAL
