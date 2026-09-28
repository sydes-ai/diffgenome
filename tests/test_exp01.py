"""Experiment 01, part 2: composition across one internal boundary (criteria S5-S10).

Runs the collector on the fixture, then composes from the controller seed. Assertions are
structural, about evidence and provenance, not about rendering."""

import pytest

from diffgenome.compose import Branch, Composition, Corpus, build_corpus, compose
from diffgenome.model import (
    CallNode,
    Collector,
    EvidenceKind,
    Execution,
    Fidelity,
    IdentityMismatch,
    JoinStrength,
    Origin,
    Plane,
    SourceLocation,
    Stimulus,
    SubstitutionNode,
    Symbol,
)
from tests.test_collector import FIXTURE, trace

QUOTE = "py:shop.pricing_service.PricingService.quote"
PLACE = "py:shop.order_service.OrderService.place"
RESERVE = "py:shop.inventory_service.InventoryService.reserve"


@pytest.fixture(scope="module")
def corpus(tmp_path_factory: pytest.TempPathFactory) -> Corpus:
    return build_corpus(list(trace(FIXTURE, tmp_path_factory.mktemp("exp01")).values()))


def seed_id(corpus: Corpus) -> str:
    return next(i for i in corpus.executions if "test_place_order_returns" in i)


@pytest.fixture(scope="module")
def composition(corpus: Corpus) -> Composition:
    return compose(corpus, seed_id(corpus))


def test_s5_join_key_is_asserted_not_assumed(corpus: Corpus) -> None:
    seed = corpus.executions[seed_id(corpus)]
    claim = next(
        n.claimed_target
        for n in seed.nodes
        if isinstance(n, SubstitutionNode) and n.path == ("quote",)
    )
    assert claim == QUOTE
    assert QUOTE in corpus.fragments and len(corpus.fragments[QUOTE]) == 2
    assert corpus.symbols[QUOTE].origin is Origin.REPO
    assert corpus.symbols[QUOTE].location == SourceLocation("shop/pricing_service.py", 8)


def test_s6_classification_by_rule(composition: Composition, corpus: Corpus) -> None:
    by_callee = {(e.callee, e.evidence.kind): e.evidence.rule for e in composition.edges()}
    assert by_callee[(QUOTE, EvidenceKind.COMPOSED)] == "claim-member"
    assert by_callee[(RESERVE, EvidenceKind.INTERNAL_GAP)] == "claim-member"
    assert by_callee[("py:sqlite3.Connection.execute", EvidenceKind.EXTERNAL_BOUNDARY)] == (
        "claim-outside-repo"
    )
    assert (
        by_callee[("py:sqlite3.Connection.execute.().fetchone", EvidenceKind.EXTERNAL_BOUNDARY)]
        == "claim-outside-repo"
    )

    control = compose(corpus, next(i for i in corpus.executions if "unspecced" in i))
    unresolved = [e for e in control.edges() if e.evidence.kind is EvidenceKind.UNRESOLVED_BOUNDARY]
    assert len(unresolved) == 2 and all(e.evidence.rule == "no-claim" for e in unresolved)
    assert not any(e.evidence.kind is EvidenceKind.COMPOSED for e in control.edges())


def test_s7_composed_provenance(composition: Composition, corpus: Corpus) -> None:
    composed = [e for e in composition.edges() if e.evidence.kind is EvidenceKind.COMPOSED]
    assert [(e.caller, e.callee) for e in composed] == [(PLACE, QUOTE)] * 2

    seed = corpus.executions[seed_id(corpus)]
    site_node = seed.nodes[composed[0].evidence.site.node]
    assert isinstance(site_node, SubstitutionNode) and site_node.path == ("quote",)
    assert {e.evidence.site for e in composed} == {composed[0].evidence.site}

    fragments = {e.evidence.fragment for e in composed}
    assert {f.execution.split("::")[1].split("@")[0] for f in fragments if f} == {
        "test_quote_sums_repository_prices",
        "test_quote_empty_cart_is_free",
    }
    for f in fragments:
        assert f is not None
        node = corpus.executions[f.execution].nodes[f.node]
        assert isinstance(node, CallNode) and node.symbol == QUOTE

    # Observed, not predicted: both fragments grade ARG_SHAPE. list[2] and list[0] share a
    # type; the size that separates the two paths is value-level. See findings log.
    assert {e.evidence.join for e in composed} == {JoinStrength.ARG_SHAPE}
    notes = {
        a.fragment.execution.split("::")[1].split("@")[0]: a.note for a in composition.attempts
    }
    assert notes["test_quote_empty_cart_is_free"] == "size differs (value-level): list[2]~list[0]"
    assert notes["test_quote_sums_repository_prices"] == ""


def test_s8_no_laundering(composition: Composition, corpus: Corpus) -> None:
    for edge in composition.edges():
        ev = edge.evidence
        assert ev.probe_derived is False
        site_ex = corpus.executions[ev.site.execution]
        site = site_ex.nodes[ev.site.node]
        if ev.kind is EvidenceKind.OBSERVED:
            assert isinstance(site, CallNode) and site.symbol == edge.callee
            assert site.parent is not None
            parent = site_ex.nodes[site.parent]
            assert isinstance(parent, CallNode) and parent.symbol == edge.caller
            assert site_ex.collectors[site.collector].fidelity is Fidelity.COMPLETE
        else:
            assert isinstance(site, SubstitutionNode)

    # Everything below a seam cites that seam's fragment execution, up to the next seam.
    assert_seam_provenance(composition, seed_id(corpus))


def assert_seam_provenance(composition: Composition, seed: str) -> None:
    stack = list(composition.branches)
    while stack:
        b = stack.pop()
        if b.edge.evidence.kind is EvidenceKind.COMPOSED:
            frag = b.edge.evidence.fragment
            assert frag is not None and frag.execution != seed
            for below in _until_next_seam(b):
                assert below.edge.evidence.site.execution == frag.execution
        stack.extend(b.children)


def _until_next_seam(branch: Branch) -> list[Branch]:
    out: list[Branch] = []
    stack = list(branch.children)
    while stack:
        b = stack.pop()
        out.append(b)
        if b.edge.evidence.kind is not EvidenceKind.COMPOSED:
            stack.extend(b.children)
    return out


def test_s9_boundaries_terminate(composition: Composition) -> None:
    terminal = {
        EvidenceKind.EXTERNAL_BOUNDARY,
        EvidenceKind.UNRESOLVED_BOUNDARY,
        EvidenceKind.INTERNAL_GAP,
        EvidenceKind.OS_BOUNDARY,
    }
    stack = list(composition.branches)
    while stack:
        b = stack.pop()
        if b.edge.evidence.kind in terminal:
            assert b.children == []
        stack.extend(b.children)


def test_s10_gap_reported_as_probe_candidate(composition: Composition) -> None:
    assert [(g.kind, g.target) for g in composition.gaps] == [("no-fragment", RESERVE)]


def test_weak_joins_are_recorded_not_dropped(corpus: Corpus) -> None:
    strict = compose(corpus, seed_id(corpus), min_join=JoinStrength.VALUE)
    assert not any(e.evidence.kind is EvidenceKind.COMPOSED for e in strict.edges())
    assert ("no-compatible-fragment", QUOTE) in {(g.kind, g.target) for g in strict.gaps}
    rejected = [a for a in strict.attempts if not a.accepted and a.target == QUOTE]
    assert len(rejected) == 2 and all(a.grade is JoinStrength.ARG_SHAPE for a in rejected)


def test_identity_mismatch_is_loud() -> None:
    def ex(i: str, location: SourceLocation) -> Execution:
        return Execution(
            id=i,
            stimulus=Stimulus.EXISTING_TEST,
            stimulus_ref=i,
            outcome="passed",
            revision=None,
            collectors=(Collector("x", Plane.SYMBOL, Fidelity.COMPLETE),),
            symbols=(Symbol("py:a.f", Origin.REPO, location),),
            nodes=(CallNode(0, None, "py:t", 0), CallNode(1, 0, "py:a.f", 0)),
        )

    with pytest.raises(IdentityMismatch, match=r"py:a\.f"):
        build_corpus([ex("1", SourceLocation("a.py", 1)), ex("2", SourceLocation("b/a.py", 1))])


def test_p9_outcome_conflict_is_unsound_and_recursion_is_provenanced(corpus: Corpus) -> None:
    """A stand-in that returned must not be joined to a fragment that raised, at any
    threshold; the remaining fragments compose and expansion continues through them."""
    seed = next(i for i in corpus.executions if "order_service_stand_in" in i)
    c = compose(corpus, seed)

    by_fragment = {
        a.fragment.execution.split("::")[1].split("@")[0]: a
        for a in c.attempts
        if a.target == PLACE
    }
    rejected = by_fragment["test_duplicate_skus_rejected"]
    assert rejected.grade is None and rejected.accepted is False
    assert (
        rejected.note
        == "outcome conflict: stand-in returned, fragment raised:py:builtins.ValueError"
    )
    assert by_fragment["test_place_order_returns_quoted_total"].accepted
    assert by_fragment["test_place_with_unspecced_mocks"].accepted
    assert by_fragment["test_place_with_unspecced_mocks"].note == (
        "size differs (value-level): list[2]~list[1]"
    )

    composed = [(e.caller, e.callee) for e in c.edges() if e.evidence.kind is EvidenceKind.COMPOSED]
    assert composed.count(("py:shop.controller.OrderController.place_order", PLACE)) == 2
    assert composed.count((PLACE, QUOTE)) == 2  # second hop, reached through a borrowed fragment
    assert_seam_provenance(c, seed)
    assert not any(
        e.callee == PLACE and e.evidence.kind is EvidenceKind.INTERNAL_GAP for e in c.edges()
    )
