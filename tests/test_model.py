import pytest

from diffgenome.model import Evidence, EvidenceKind, NodeRef

SITE = NodeRef("tests/test_controller.py::test_place_order", 4)
FRAGMENT = NodeRef("tests/test_pricing_service.py::test_quote", 1)


def test_stitched_evidence_requires_fragment_and_rule() -> None:
    ok = Evidence(EvidenceKind.STITCHED, SITE, rule="spec-class", fragment=FRAGMENT)
    assert ok.fragment == FRAGMENT

    with pytest.raises(ValueError, match="fragment"):
        Evidence(EvidenceKind.STITCHED, SITE, rule="spec-class")
    with pytest.raises(ValueError, match="rule"):
        Evidence(EvidenceKind.STITCHED, SITE, fragment=FRAGMENT)


def test_observed_evidence_cannot_carry_stitch_provenance() -> None:
    Evidence(EvidenceKind.OBSERVED, SITE)

    with pytest.raises(ValueError, match="fragment"):
        Evidence(EvidenceKind.OBSERVED, SITE, fragment=FRAGMENT)
    with pytest.raises(ValueError, match="mock resolution"):
        Evidence(EvidenceKind.OBSERVED, SITE, rule="spec-class")


@pytest.mark.parametrize(
    "kind",
    [EvidenceKind.INTERNAL_GAP, EvidenceKind.EXTERNAL_BOUNDARY, EvidenceKind.UNRESOLVED_MOCK],
)
def test_boundary_evidence_names_rule_and_has_no_fragment(kind: EvidenceKind) -> None:
    Evidence(kind, SITE, rule="spec-class")

    with pytest.raises(ValueError):
        Evidence(kind, SITE)
    with pytest.raises(ValueError):
        Evidence(kind, SITE, rule="spec-class", fragment=FRAGMENT)
