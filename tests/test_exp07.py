"""Experiment 07: the STATE rung, the exit model, and the adversarial ground truth.

The fixture `exp07_state` has one target (`Processor.run`) whose continuation depends on
nothing in its arguments: only on receiver state (`enabled`), module state
(`settings.STRICT`) and a collaborator's state (`repo.closed`, which changes the exit).
Every fragment calls it with the same argument. VALUE-only composition must accept the wrong
continuations; STATE must reject exactly those and keep the right one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from diffgenome.collect.py_monitoring import bucket, state_facts
from diffgenome.compose import (
    Corpus,
    build_corpus,
    exit_compatibility,
    grade_seam,
    outcome_parts,
    state_compatibility,
)
from diffgenome.evaluate import (
    evaluate_paths,
    explain_paths,
    ground_truth_from,
    join_matrix,
    path_scores,
)
from diffgenome.graph import build_graph
from diffgenome.model import (
    CallNode,
    Execution,
    JoinStrength,
    Origin,
    SubstitutionMechanism,
    SubstitutionNode,
)
from tests.test_collector import REPO, trace

FIXTURE = REPO / "fixtures" / "exp07_state"
FLAG = False  # read by test_a2's nested function through the module_globals it is handed


class Cfg:
    _instance = None


RUN = "py:proc.processor.Processor.run"
EXECUTE = "py:proc.pipeline.Pipeline.execute"


@pytest.fixture(scope="module")
def traces(tmp_path_factory: pytest.TempPathFactory) -> tuple[list[Execution], list[Execution]]:
    recon = trace(FIXTURE, tmp_path_factory.mktemp("s7-recon"))
    truth = trace(FIXTURE, tmp_path_factory.mktemp("s7-gt"), "groundtruth", ["groundtruth"])
    return list(recon.values()), list(truth.values())


@pytest.fixture(scope="module")
def corpus(traces: tuple[list[Execution], list[Execution]]) -> Corpus:
    return build_corpus(traces[0])


# ------------------------------------------------------------------ A. state facts


def test_a1_buckets_are_value_free() -> None:
    assert bucket(None) == ("none", "")
    assert bucket(True) == ("bool:true", "") and bucket(0) == ("num:zero", "")
    assert bucket(-3) == ("num:neg", "") and bucket("") == ("str:empty", "")
    assert bucket([1, 2]) == ("coll:many", "") and bucket({}) == ("coll:empty", "")
    assert bucket(len) is None  # callables are behavior, not state
    # a secret is the same bucket as any other non-empty string: nothing of it is kept
    assert bucket("hunter2") == bucket("x")


def test_a2_state_facts_receiver_globals_and_class_attributes() -> None:
    class Thing:
        def __init__(self) -> None:
            self.enabled = True
            self.items: list[int] = []

        def run(self) -> None:
            if Cfg._instance is None and FLAG:
                pass

    g = {"Cfg": Cfg, "FLAG": False, "helper": len}
    facts = {n: b for n, b, _ in state_facts(Thing(), Thing.run.__code__, g)}
    assert facts["self:type"].endswith(".Thing")
    assert facts["self.enabled"] == "bool:true" and facts["self.items"] == "coll:empty"
    assert facts["global.FLAG"] == "bool:false"
    assert facts["global.Cfg._instance"] == "none"
    assert "global.helper" not in facts and "global.Cfg" not in facts


def test_a3_seam_and_fragments_expose_state(corpus: Corpus) -> None:
    seed = next(e for i, e in corpus.executions.items() if "test_execute_wraps" in i)
    seam = next(n for n in seed.nodes if isinstance(n, SubstitutionNode) and n.claimed_target)
    assert seam.claimed_target == RUN
    facts = {n: b for n, b, _ in seam.state}
    assert facts["self.enabled"] == "bool:true"
    assert facts["global.settings.STRICT"] == "bool:false"
    by_frag = {
        i.split("::")[-1].split("@")[0]: next(
            n for n in e.nodes if isinstance(n, CallNode) and n.symbol == RUN
        )
        for i, e in corpus.executions.items()
        if "test_processor" in i
    }
    assert {n: b for n, b, _ in by_frag["test_run_disabled_skips"].state}[
        "self.enabled"
    ] == "bool:false"
    assert {n: b for n, b, _ in by_frag["test_run_enabled_strict_audits"].state}[
        "global.settings.STRICT"
    ] == "bool:true"
    assert (
        by_frag["test_run_enabled_closed_repository_raises"].outcome
        == "raised:py:proc.repository.RepositoryClosed"
    )


# ------------------------------------------------------------------ B. exit model


def test_b1_exit_compatibility_is_category_then_identity() -> None:
    assert exit_compatibility("returned", "returned") == "same"
    assert exit_compatibility("raised:py:ValueError", "raised:py:ValueError") == "same"
    assert exit_compatibility("raised:py:ValueError", "raised:py:KeyError") is None
    assert exit_compatibility("raised:py:ValueError", "raised") == "kind"
    assert exit_compatibility("returned", "raised:py:ValueError") is None
    assert exit_compatibility("unknown", "returned") == "unknown"
    # Go: an error result and a panic are different categories, not two "raised"s
    assert (
        exit_compatibility("returned-error:go:*errors.errorString", "panic:go:runtime.errorString")
        is None
    )
    assert exit_compatibility("returned-error:go:*errors.errorString", "returned-error") == "kind"
    # what the old collector emitted: one "raised" category for errors and panics, so a
    # category-only comparison saw them agree; the categories now carry the distinction
    assert outcome_parts("raised:go:panic:runtime.errorString")[0] == "raised"
    assert outcome_parts("panic:go:runtime.errorString")[0] == "panic"
    assert outcome_parts("returned-error:go:*errors.errorString")[0] == "returned-error"


# ------------------------------------------------------------------ C. STATE rung


def test_c1_state_rung_verdicts(corpus: Corpus) -> None:
    seed = next(e for i, e in corpus.executions.items() if "test_execute_wraps" in i)
    seam = next(n for n in seed.nodes if isinstance(n, SubstitutionNode) and n.claimed_target)
    frags = {
        i.split("::")[-1].split("@")[0]: next(
            n for n in e.nodes if isinstance(n, CallNode) and n.symbol == RUN
        )
        for i, e in corpus.executions.items()
        if "test_processor" in i
    }
    assert state_compatibility(seam, frags["test_run_enabled_persists"])[0] == "match"
    assert state_compatibility(seam, frags["test_run_disabled_skips"])[0] == "conflict"
    assert state_compatibility(seam, frags["test_run_enabled_strict_audits"])[0] == "conflict"
    # VALUE-only: identical arguments, so every returning fragment is a VALUE join
    for name in (
        "test_run_enabled_persists",
        "test_run_disabled_skips",
        "test_run_enabled_strict_audits",
    ):
        assert grade_seam(seam, frags[name], use_state=False)[0] is JoinStrength.VALUE
    assert (
        grade_seam(seam, frags["test_run_enabled_persists"], use_state=True)[0]
        is JoinStrength.STATE
    )
    assert grade_seam(seam, frags["test_run_disabled_skips"], use_state=True)[0] is None
    # the raising fragment is rejected at the exit, before any entry rung
    g, note = grade_seam(seam, frags["test_run_enabled_closed_repository_raises"], use_state=False)
    assert g is None and note.startswith("exit conflict")


def test_c2_no_hidden_upgrade_without_facts() -> None:
    seam = SubstitutionNode(
        id=1,
        parent=0,
        collector=0,
        mechanism=SubstitutionMechanism.INTERPOSITION,
        substitute="s",
        claimed_target=RUN,
        relation="instance-attribute",
        path=("run",),
        args=(("a", "str", "x"),),
        outcome="returned",
    )
    frag = CallNode(
        id=1, parent=0, symbol=RUN, collector=0, args=(("a", "str", "x"),), outcome="returned"
    )
    g, note = grade_seam(seam, frag, use_state=True)
    assert g is JoinStrength.VALUE and "state unavailable" in note


# ------------------------------------------------------------------ D. adversarial ground truth


def test_d1_value_only_versus_state_on_the_same_corpus(
    traces: tuple[list[Execution], list[Execution]], corpus: Corpus
) -> None:
    recon, truth = traces
    origins = {s.id: s.origin for e in truth + recon for s in e.symbols}
    seed_truth = [e for e in truth if "enabled_end_to_end" in e.id]  # the seed's own condition
    value_only = build_graph(corpus, use_state=False)
    with_state = build_graph(corpus, use_state=True)

    pv = evaluate_paths(value_only, seed_truth, EXECUTE, origins)
    ps = evaluate_paths(with_state, seed_truth, EXECUTE, origins)
    assert (pv.claimed_paths, pv.matched, len(pv.extra)) == (3, 1, 2)
    assert (ps.claimed_paths, ps.matched, len(ps.extra), len(ps.missed)) == (1, 1, 0, 0)
    assert path_scores(pv)[0] == pytest.approx(1 / 3) and path_scores(pv)[1] == 1.0
    assert path_scores(ps) == (1.0, 1.0)
    # every extra path names the seam and the grade that admitted it
    assert all("admitted at seam" in x and "VALUE" in x for x in explain_paths(pv, value_only))

    # against every condition, STATE trades recall for precision and says why
    pall = evaluate_paths(with_state, truth, EXECUTE, origins)
    assert (pall.truth_paths, pall.claimed_paths, pall.matched, len(pall.missed)) == (3, 1, 1, 2)
    ex = explain_paths(pall, with_state)
    assert any("test_run_disabled_skips" in x and "self.enabled" in x for x in ex)
    assert any("test_run_enabled_strict_audits" in x and "settings.STRICT" in x for x in ex)


def test_d2_join_matrix_rows(
    traces: tuple[list[Execution], list[Execution]], corpus: Corpus
) -> None:
    recon, truth = traces
    origins = {s.id: s.origin for e in truth + recon for s in e.symbols}
    gt = ground_truth_from(truth, [EXECUTE], origins)
    g = build_graph(corpus, use_state=True)

    def repo_edges(ex: Execution) -> set[tuple[str, str]]:
        by_id = {n.id: n for n in ex.nodes}
        out = set()
        for n in ex.nodes:
            if isinstance(n, CallNode) and n.parent is not None:
                p = by_id[n.parent]
                if (
                    isinstance(p, CallNode)
                    and origins.get(p.symbol) is Origin.REPO
                    and origins.get(n.symbol) is Origin.REPO
                ):
                    out.add((p.symbol, n.symbol))
        return out

    rows = {
        r.fragment: r
        for r in join_matrix(
            g, {e.id: repo_edges(e) for e in recon}, gt, [repo_edges(e) for e in truth]
        )
    }
    assert {r.target for r in rows.values()} == {RUN}
    assert (
        rows["test_run_enabled_persists"].accepted
        and rows["test_run_enabled_persists"].state == "✓"
    )
    assert (
        not rows["test_run_disabled_skips"].accepted
        and rows["test_run_disabled_skips"].state == "✗"
    )
    assert rows["test_run_disabled_skips"].value == "✓"  # it reached VALUE; STATE rejected it
    assert rows["test_run_enabled_closed_repository_raises"].exit == "conflict"
    # truth: each fragment's continuation *is* one some whole execution took; the seam's
    # state decides which one applies here
    assert all(r.truth for r in rows.values())


def test_d3_state_condition_objective(corpus: Corpus) -> None:
    from diffgenome.probe import select_objectives

    only_wrong = build_corpus(
        [e for e in corpus.executions.values() if "persists" not in e.id and "closed" not in e.id]
    )
    g = build_graph(only_wrong)
    nb = g.neighborhood([RUN], up=3, down=4)
    (o,) = select_objectives(nb, g, 1)
    assert o.kind == "state_condition" and o.target == RUN
    text = o.describe()
    assert "self.enabled is bool:true" in text and "global.settings.STRICT is bool:false" in text
    assert "under that same state condition" in text


def test_fixture_is_read_only() -> None:
    assert not list(Path(FIXTURE).rglob("*.diffgenome*"))
