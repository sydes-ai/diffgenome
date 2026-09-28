import pytest

from diffgenome.model import Evidence, EvidenceKind, JoinStrength, NodeRef

SITE = NodeRef("tests/test_controller.py::test_place_order@abc123", 4)
FRAGMENT = NodeRef("tests/test_pricing_service.py::test_quote@abc123", 1)


def test_composed_evidence_requires_fragment_rule_and_join() -> None:
    ok = Evidence(
        EvidenceKind.COMPOSED, SITE, rule="spec-member", fragment=FRAGMENT, join=JoinStrength.SYMBOL
    )
    assert ok.fragment == FRAGMENT

    with pytest.raises(ValueError, match="fragment"):
        Evidence(EvidenceKind.COMPOSED, SITE, rule="spec-member", join=JoinStrength.SYMBOL)
    with pytest.raises(ValueError, match="rule"):
        Evidence(EvidenceKind.COMPOSED, SITE, fragment=FRAGMENT, join=JoinStrength.SYMBOL)
    with pytest.raises(ValueError, match="join"):
        Evidence(EvidenceKind.COMPOSED, SITE, rule="spec-member", fragment=FRAGMENT)


@pytest.mark.parametrize(
    "kind", [EvidenceKind.OBSERVED, EvidenceKind.OBSERVED_SAMPLED, EvidenceKind.OS_BOUNDARY]
)
def test_direct_observations_cannot_carry_derived_provenance(kind: EvidenceKind) -> None:
    Evidence(kind, SITE)

    with pytest.raises(ValueError, match="fragment"):
        Evidence(kind, SITE, fragment=FRAGMENT)
    with pytest.raises(ValueError, match="no rule"):
        Evidence(kind, SITE, rule="spec-member")
    with pytest.raises(ValueError, match="join"):
        Evidence(kind, SITE, join=JoinStrength.SYMBOL)


@pytest.mark.parametrize(
    "kind",
    [
        EvidenceKind.INTERNAL_GAP,
        EvidenceKind.EXTERNAL_BOUNDARY,
        EvidenceKind.UNRESOLVED_BOUNDARY,
        EvidenceKind.STATIC,
    ],
)
def test_derived_terminal_evidence_names_rule_and_has_no_fragment(kind: EvidenceKind) -> None:
    Evidence(kind, SITE, rule="spec-member")

    with pytest.raises(ValueError, match="rule"):
        Evidence(kind, SITE)
    with pytest.raises(ValueError, match="fragment"):
        Evidence(kind, SITE, rule="spec-member", fragment=FRAGMENT)


def test_probe_provenance_is_explicit_and_default_off() -> None:
    assert Evidence(EvidenceKind.OBSERVED, SITE).probe_derived is False
    assert Evidence(EvidenceKind.OBSERVED, SITE, probe_derived=True).probe_derived is True
