"""Experiment 01, part 2: composition across one internal boundary (criteria S5-S10).

Runs the collector on the fixture, then composes from the controller seed. Assertions are
structural, about evidence and provenance, not about rendering."""

from pathlib import Path

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

    # ARG_SHAPE cannot separate list[2] from list[0] (same type); VALUE can (exp 02).
    joins = {
        e.evidence.fragment.execution.split("::")[1].split("@")[0]: e.evidence.join
        for e in composed
        if e.evidence.fragment
    }
    assert joins == {
        "test_quote_empty_cart_is_free": JoinStrength.ARG_SHAPE,
        "test_quote_sums_repository_prices": JoinStrength.VALUE,
    }
    notes = {
        a.fragment.execution.split("::")[1].split("@")[0]: a.note for a in composition.attempts
    }
    assert notes["test_quote_empty_cart_is_free"].startswith("values differ: skus")
    assert notes["test_quote_sums_repository_prices"].startswith("state unavailable")


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
    strict = compose(corpus, seed_id(corpus), min_join=JoinStrength.STATE)
    assert not any(e.evidence.kind is EvidenceKind.COMPOSED for e in strict.edges())
    assert ("no-compatible-fragment", QUOTE) in {(g.kind, g.target) for g in strict.gaps}
    rejected = [a for a in strict.attempts if not a.accepted and a.target == QUOTE]
    assert len(rejected) == 2 and all(a.grade is not None for a in rejected)


def test_p10_value_join_selects_between_fragments(corpus: Corpus) -> None:
    """Experiment 02: at min_join=VALUE exactly one `quote` fragment composes, the one whose
    entry values equal the seed's stand-in call; ARG_SHAPE alone could not choose."""
    c = compose(corpus, seed_id(corpus), min_join=JoinStrength.VALUE)
    composed = [e for e in c.edges() if e.evidence.kind is EvidenceKind.COMPOSED]
    assert len(composed) == 1 and composed[0].evidence.join is JoinStrength.VALUE
    assert composed[0].evidence.fragment is not None
    assert "test_quote_sums_repository_prices" in composed[0].evidence.fragment.execution
    rejected = [a for a in c.attempts if not a.accepted]
    assert [(a.grade, a.note, a.result_compatible) for a in rejected] == [
        (JoinStrength.ARG_SHAPE, "values differ: skus; result differs: seed continued on it", False)
    ]
    # Result compatibility is reported alongside, independently of the grade.
    accepted = next(a for a in c.attempts if a.accepted)
    assert accepted.result_compatible is True  # both produced 2500, by the fixture's authoring


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
        rejected.note == "exit conflict: stand-in returned, fragment raised:py:builtins.ValueError"
    )
    assert by_fragment["test_place_order_returns_quoted_total"].grade is JoinStrength.VALUE
    unspecced = by_fragment["test_place_with_unspecced_mocks"]
    assert unspecced.accepted and unspecced.grade is JoinStrength.ARG_SHAPE
    assert unspecced.note.startswith("values differ: customer_id, skus")
    # P11: the fragment returned Order(..., 700); the stand-in returned Order(..., 4200).
    assert unspecced.result_compatible is False and "result differs" in unspecced.note

    composed = [(e.caller, e.callee) for e in c.edges() if e.evidence.kind is EvidenceKind.COMPOSED]
    assert composed.count(("py:shop.controller.OrderController.place_order", PLACE)) == 2
    assert composed.count((PLACE, QUOTE)) == 2  # second hop, reached through a borrowed fragment
    assert_seam_provenance(c, seed)
    assert not any(
        e.callee == PLACE and e.evidence.kind is EvidenceKind.INTERNAL_GAP for e in c.edges()
    )


def test_same_shape_fragments_merge_with_provenance_kept(tmp_path: Path) -> None:
    """Fragments with one behavior shape expand once; the others ride along as alternates.
    On Kokoro-FastAPI this took composition from 11,524 to 406 composed edges."""
    from tests.test_collector import trace

    root = tmp_path
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text("")
    (root / "pkg" / "svc.py").write_text(
        "class Repo:\n"
        "    def get(self, k): return k\n"
        "class Svc:\n"
        "    def __init__(self, repo): self.repo = repo\n"
        "    def run(self, k): return self.repo.get(k)\n"
        "def use(svc): return svc.run('x')\n"
    )
    (root / "tests").mkdir()
    (root / "tests" / "test_svc.py").write_text(
        "from unittest.mock import create_autospec\n"
        "from pkg.svc import Repo, Svc, use\n"
        "def test_seed():\n"
        "    svc = create_autospec(Svc, instance=True); svc.run.return_value = 'x'\n"
        "    assert use(svc) == 'x'\n"
        "def test_frag_a(): assert Svc(Repo()).run('x') == 'x'\n"
        "def test_frag_b(): assert Svc(Repo()).run('x') == 'x'\n"
        "def test_frag_c(): assert Svc(Repo()).run('y') == 'y'\n"
    )
    (root / "pytest.ini").write_text("[pytest]\npythonpath = .\n")
    corpus = build_corpus(list(trace(root, root / "out").values()))
    c = compose(corpus, next(i for i in corpus.executions if "test_seed" in i))

    composed = [e for e in c.edges() if e.evidence.kind is EvidenceKind.COMPOSED]
    assert len(composed) == 1  # three same-shape fragments, one branch
    ev = composed[0].evidence
    assert ev.join is JoinStrength.VALUE and ev.fragment is not None
    assert "test_frag_a" in ev.fragment.execution or "test_frag_b" in ev.fragment.execution
    cited = {ev.fragment.execution} | {a.execution for a in ev.alternates}
    assert {x.split("::")[1].split("@")[0] for x in cited} == {
        "test_frag_a",
        "test_frag_b",
        "test_frag_c",
    }
    grades = {a.fragment.execution.split("::")[1].split("@")[0]: a.grade for a in c.attempts}
    assert grades["test_frag_c"] is JoinStrength.ARG_SHAPE  # 'y' ≠ 'x': kept, ranked below


def test_type_conflicts_are_decisive_only_for_structural_kinds() -> None:
    """None vs dict is a different branch (unsound); *gin.Context vs context.backgroundCtx
    may both satisfy a declared interface (unverified, capped at ARG_SHAPE); a stand-in
    argument is a wildcard."""
    from diffgenome.compose import grade_seam
    from diffgenome.model import SubstitutionMechanism, SubstitutionNode

    def sub(*args: tuple[str, str, str]) -> SubstitutionNode:
        return SubstitutionNode(
            1, 0, 0, SubstitutionMechanism.FAKE, "x", None, "none", (), args, "returned", ""
        )

    def frag(*args: tuple[str, str, str]) -> CallNode:
        return CallNode(2, 0, "py:t", 0, args, 0, "returned", "")

    grade, note = grade_seam(sub(("a", "NoneType", "n")), frag(("a", "dict[2]", "d")))
    assert grade is None and "type conflict" in note
    grade, note = grade_seam(
        sub(("ctx", "*gin.Context", "")), frag(("ctx", "context.backgroundCtx", ""))
    )
    assert grade is JoinStrength.ARG_SHAPE and "unverified" in note
    grade, note = grade_seam(sub(("a", "stand-in", "")), frag(("a", "Repo", "")))
    assert grade is JoinStrength.ARG_SHAPE
    grade, _ = grade_seam(sub(("id", "int64", "h1")), frag(("id", "int64", "h1")))
    assert grade is JoinStrength.VALUE
