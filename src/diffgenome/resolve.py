"""Boundary resolution: classify a stand-in as internal / external / unresolved.

Ordered deterministic rules over facts only: the stand-in's claim and the claimed symbol's
recorded origin. No rule looks at names. The rule that fired is always returned.
"""

from __future__ import annotations

from diffgenome.model import (
    BoundaryClass,
    BoundaryResolution,
    Origin,
    SubstitutionNode,
    Symbol,
    SymbolId,
)


def resolve(sub: SubstitutionNode, symbols: dict[SymbolId, Symbol]) -> BoundaryResolution:
    claim = sub.claimed_target
    if claim is None:
        return BoundaryResolution(BoundaryClass.UNRESOLVED, None, "no-claim")
    symbol = symbols.get(claim)
    origin = symbol.origin if symbol else Origin.UNKNOWN
    if origin is Origin.TEST:
        return BoundaryResolution(BoundaryClass.UNRESOLVED, claim, "claim-in-tests")
    if origin is Origin.EXTERNAL:
        return BoundaryResolution(BoundaryClass.EXTERNAL, claim, "claim-outside-repo")
    if origin is Origin.UNKNOWN:
        return BoundaryResolution(BoundaryClass.UNRESOLVED, claim, "claim-unknown-origin")
    if "()" in sub.path:
        # The claim names the first member; what its *return value* is, nobody observed.
        return BoundaryResolution(BoundaryClass.UNRESOLVED, claim, "claim-return-chain")
    if sub.relation.startswith("static-return-type"):
        # Resolved through a declared return type: static evidence, said so on the edge.
        return BoundaryResolution(BoundaryClass.INTERNAL, claim, "static-return-type")
    return BoundaryResolution(BoundaryClass.INTERNAL, claim, "claim-member")
