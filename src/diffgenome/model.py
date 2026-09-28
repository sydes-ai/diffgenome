"""Core, language-agnostic data model.

Two layers, deliberately kept apart:

1. **Observation** (`TestExecution`, `CallNode`, `MockTarget`): raw facts emitted by a
   language-specific tracer. A tracer records *what happened* and never interprets it.
   Any collector (Python today; Java/Go/Rust later) must be able to emit exactly this.

2. **Interpretation** (`MockResolution`, `Evidence`, `Edge`): conclusions drawn from
   observations. Every conclusion carries the rule and the observation(s) it came from,
   so provenance is never lost and a stitched edge can never pass as an observed one.

See docs/architecture.md for the reasoning behind each type.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

SymbolId = str
"""Canonical symbol identity: ``<language>:<qualified name>``,
e.g. ``py:shop.pricing_service.PricingService.quote``. Stable across runs of the
same revision; this is the key that lets fragments from different tests be joined."""


class Origin(Enum):
    REPO = "repo"  # defined in the repository's source roots
    TEST = "test"  # defined in the repository's test code (test functions, fakes, helpers)
    EXTERNAL = "external"  # stdlib, third-party, or otherwise outside the repository
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SourceLocation:
    path: str  # repository-relative for REPO/TEST symbols
    line: int


@dataclass(frozen=True)
class Symbol:
    id: SymbolId
    origin: Origin
    location: SourceLocation | None = None


# --------------------------------------------------------------------------- observation


class ExecutionKind(Enum):
    EXISTING_TEST = "existing_test"
    GENERATED_PROBE = "generated_probe"  # experiment 2+; recorded so probes never masquerade


@dataclass(frozen=True)
class MockTarget:
    """What the tracer can say, factually, about a mock object at a call site."""

    spec: str | None
    """Qualified name of the object the root mock was specced from (``spec=``/autospec/
    patch original), or None for a spec-less mock. A fact read off the mock, not a guess."""
    path: tuple[str, ...]
    """Attribute path from the root mock, e.g. ``("execute", "()", "fetchone")``
    where ``"()"`` marks a call's return value."""
    member: str | None
    """Qualified name of the definition ``path`` names on ``spec``, looked up statically
    through the MRO at trace time (so an inherited method resolves to the base class that
    defines it). None if ``path`` crosses a return value or names no definition."""
    member_file: str | None
    """Source file of ``member`` (or of ``spec`` when ``member`` is None); None for C code."""


@dataclass(frozen=True)
class CallNode:
    """One call observed in one execution. Nodes form a tree via ``parent``."""

    id: int  # unique within its execution
    parent: int | None  # None only for the execution's root (the test function)
    symbol: SymbolId  # real callee; for mock calls, a synthetic ``mock:<spec or ?>.<path>`` id
    mock: MockTarget | None = None  # set iff the callee was a mock; mock calls are leaves
    args: str | None = None  # bounded summary of argument shapes, for later contract checks


@dataclass(frozen=True)
class TestExecution:
    test_id: str  # e.g. pytest node id
    kind: ExecutionKind
    outcome: str  # "passed" | "failed" | ...; only passing executions are stitch sources
    revision: str | None  # VCS revision the trace was taken at, if known
    nodes: tuple[CallNode, ...]


# ------------------------------------------------------------------------ interpretation


class MockClass(Enum):
    INTERNAL = "internal"  # stands in for code in this repository: a continuation point
    EXTERNAL = "external"  # stands in for something outside the repository: terminal
    UNRESOLVED = "unresolved"  # not enough evidence to decide: terminal, reported, never guessed


@dataclass(frozen=True)
class MockResolution:
    classification: MockClass
    target: SymbolId | None  # the real symbol the mock represents, when known
    rule: str  # which deterministic rule decided this, e.g. "spec-class", "no-spec"


class EvidenceKind(Enum):
    OBSERVED = "observed"  # caller really called callee within a single execution
    STITCHED = "stitched"  # call hit an internal mock; callee's continuation is another execution
    INTERNAL_GAP = "internal_gap"  # call hit an internal mock; no execution of the real target yet
    EXTERNAL_BOUNDARY = "external_boundary"  # call hit an external mock; exploration stops
    UNRESOLVED_MOCK = "unresolved_mock"  # call hit a mock we could not classify
    # Reserved, not produced yet: STATIC ("statically possible"), from static analysis.


_MOCK_DERIVED = {
    EvidenceKind.STITCHED,
    EvidenceKind.INTERNAL_GAP,
    EvidenceKind.EXTERNAL_BOUNDARY,
    EvidenceKind.UNRESOLVED_MOCK,
}


@dataclass(frozen=True)
class NodeRef:
    test_id: str
    node: int


@dataclass(frozen=True)
class Evidence:
    """Why we believe an edge exists. Invariants are enforced at construction."""

    kind: EvidenceKind
    site: NodeRef
    """The observed call node that grounds this evidence. For mock-derived kinds this is
    the mock call itself: the *call* was observed even when the continuation was not."""
    rule: str | None = None  # mock-resolution rule; required for every mock-derived kind
    fragment: NodeRef | None = None
    """STITCHED only: the root of the continuation, i.e. a real call to the target symbol
    in some (usually different) execution."""

    def __post_init__(self) -> None:
        if self.kind in _MOCK_DERIVED and self.rule is None:
            raise ValueError(f"{self.kind.value} evidence must name its resolution rule")
        if self.kind is EvidenceKind.OBSERVED and self.rule is not None:
            raise ValueError("observed evidence is not derived from a mock resolution")
        if (self.kind is EvidenceKind.STITCHED) != (self.fragment is not None):
            raise ValueError("a fragment is required for, and only for, stitched evidence")


@dataclass(frozen=True)
class Edge:
    caller: SymbolId
    callee: SymbolId
    evidence: Evidence
