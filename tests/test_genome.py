# ruff: noqa: E501  (inline fixture data)
"""Behavioral Genome IR (experimental): statuses are assigned by evidence, never by the
proposer; prediction is sound when semantics are missing; comparison is exact."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from diffgenome.genome import (
    HYPOTHESIS,
    REJECTED,
    SUPPORTED,
    VERIFIED,
    ExecutionPath,
    Step,
    Substrate,
    compare,
    establish,
    genome_from_proposals,
    predict,
    vocabulary,
)

SRC = """package api
func (s *Server) pay(ctx C, a Account, amount int64) bool {
	if a.Balance < amount {
		fail(ctx)
		return false
	}
	return true
}
"""


def _paths() -> list[ExecutionPath]:
    ok = ExecutionPath(
        "T/ok",
        "passed",
        "handle",
        [Step("pay", "returned", "true"), Step("stand-in:store.Commit", "returned", None)],
    )
    low = ExecutionPath(
        "T/low",
        "passed",
        "handle",
        [Step("pay", "returned", "false", [Step("fail", "returned", None)])],
    )
    return [ok, low]


def _sub(tmp: Path) -> Substrate:
    (tmp / "pay.go").write_text(SRC)
    return Substrate(_paths(), {("handle", "pay")}, tmp, {("pay.go", 3)})


def _proposals(**over: object) -> dict[str, Any]:
    d8 = {
        "id": "D1", "entity": "pay", "inputs": ["account.balance", "request.amount"],
        "predicate": "!balance_ok", "order": 1,
        "true_branch": {"returns": "false", "calls": ["pay", "fail"], "absent": ["Commit"], "stops": True},
        "false_branch": {"returns": "true", "calls": ["pay", "Commit"], "stops": True},
        "evidence": [
            {"kind": "source", "file": "pay.go", "line": 3, "text": "if a.Balance < amount {"},
            {"kind": "execution", "test": "T/ok", "calls": ["pay", "Commit"], "returns": {"pay": "true"}},
        ],
    }  # fmt: skip
    d8.update(over)
    return {
        "variables": [
            {"id": "V1", "name": "balance_ok", "origin": "derived",
             "definition": "account.balance >= request.amount",
             "evidence": [{"kind": "source", "file": "pay.go", "line": 3, "text": "a.Balance < amount"}]},
        ],
        "decisions": [d8],
        "rules": [{"id": "R1", "name": "guard", "condition": "account.balance < request.amount",
                   "consequences": ["no commit"], "decision": "D1",
                   "evidence": [{"kind": "source", "file": "pay.go", "line": 3, "text": "if a.Balance < amount {"}]}],
    }  # fmt: skip


def _genome(tmp: Path, **over: object):  # type: ignore[no-untyped-def]
    g = genome_from_proposals(_proposals(**over), {"entry": "handle"}, "test-model")
    return establish(g, _sub(tmp))


def test_verified_needs_if_site_and_both_branches(tmp_path: Path) -> None:
    g = _genome(tmp_path)
    assert g.decisions[0].status == VERIFIED and g.rules[0].status == VERIFIED
    assert g.variables[0].status == SUPPORTED
    assert all(it.derived_by == "llm:test-model" for it in (*g.decisions, *g.rules, *g.variables))


def test_fabricated_citation_is_only_a_hypothesis(tmp_path: Path) -> None:
    g = _genome(
        tmp_path,
        evidence=[
            {"kind": "source", "file": "pay.go", "line": 3, "text": "if a.Balance <= amount {"}
        ],
    )
    assert g.decisions[0].status == HYPOTHESIS
    assert g.rules[0].status == SUPPORTED  # its own citation is real; it is just not verified


def test_contradicted_consequence_is_rejected(tmp_path: Path) -> None:
    g = _genome(
        tmp_path, true_branch={"returns": "false", "calls": ["pay", "Commit"], "stops": False}
    )
    assert g.decisions[0].status == REJECTED and g.rules[0].status == REJECTED
    assert "T/low" in g.decisions[0].status_reason


def test_prediction_is_generative_and_exact(tmp_path: Path) -> None:
    g = _genome(tmp_path)
    low = predict(g, {"account.balance": 9, "request.amount": 10})
    assert low.path == ["pay", "fail"] and low.absent == ["Commit"] and low.stopped_at == "D1"
    ok = predict(g, {"account.balance": 10, "request.amount": 10})
    assert ok.path == ["pay", "Commit"]
    paths = {p.execution: p for p in _paths()}
    assert compare(low, paths["T/low"], vocabulary(g))["exact"]
    assert compare(ok, paths["T/ok"], vocabulary(g))["exact"]
    assert not compare(ok, paths["T/low"], vocabulary(g))["match"]


def test_unestablished_decision_stops_prediction_instead_of_vanishing(tmp_path: Path) -> None:
    """A demoted guard must not be skipped: skipping would predict Commit on low balance."""
    g = _genome(tmp_path, evidence=[])
    assert g.decisions[0].status == HYPOTHESIS
    p = predict(g, {"account.balance": 9, "request.amount": 10})
    assert p.path == [] and p.indeterminate and "D1 is hypothesis" in p.indeterminate
    # and a prose-only definition derives nothing
    g2 = _genome(tmp_path)
    g2.variables[0].definition = None
    assert predict(g2, {"account.balance": 9, "request.amount": 10}).indeterminate


def test_rule_is_not_verified_beyond_its_decision(tmp_path: Path) -> None:
    props = _proposals()
    props["variables"].append({"id": "V2", "name": "request.currency_ok", "origin": "request",
                               "evidence": [{"kind": "source", "file": "pay.go", "line": 3, "text": "amount"}]})  # fmt: skip
    props["rules"][0]["condition"] = "account.balance < request.amount || !request.currency_ok"
    g = establish(genome_from_proposals(props, {}, "m"), _sub(tmp_path))
    assert g.decisions[0].status == VERIFIED
    assert g.rules[0].status == SUPPORTED and "request.currency_ok" in g.rules[0].status_reason


def test_boolean_literals_evaluate() -> None:
    from diffgenome.genome import eval_predicate

    assert eval_predicate("true", {}) is True and eval_predicate("!true", {}) is False
    assert eval_predicate("false || x", {"x": True}) is True
