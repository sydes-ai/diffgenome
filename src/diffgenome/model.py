"""Core, language-agnostic data model: the diffgenome event protocol and evidence types.

Two layers, deliberately kept apart:

1. **Observation** (`Execution` and its nodes): raw facts emitted by a capture adapter.
   Adapters differ completely per runtime (sys.monitoring, JVMTI, uprobes, eBPF, perf,
   V8 hooks...) but all emit exactly this. An adapter records *what happened* and never
   interprets it. Two capture **planes** feed it:

   - the *OS plane* (syscalls, sockets, files, processes): universal, gives physical
     boundaries and native call structure;
   - the *symbol plane* (logical calls inside the runtime): per-runtime, gives the
     program's own call structure.

2. **Interpretation** (`BoundaryResolution`, `Evidence`, `Edge`): conclusions drawn from
   observations. Every conclusion carries the rule and the observation(s) it came from,
   so provenance is never lost and a composed edge can never pass as an observed one.

Nothing in this module may mention a language, a test framework or a mocking library.
See docs/architecture.md for the reasoning behind each type.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

SymbolId = str
"""Symbol identity: ``<language>:<qualified name>``,
e.g. ``py:shop.pricing_service.PricingService.quote`` or ``go:db.Store.TransferTx``.
This is the key that lets fragments from different executions be joined, so both sides of
a seam must produce it identically.

**Provisional.** Sufficient for experiment 01; not assumed sufficient long term. Known
identity problems: source path vs module, defining type vs receiver type, overloads and
signatures, interfaces vs implementations, closures, generated functions, generics,
monorepos, dynamic runtimes. Whenever two components disagree about an identity, raise
``IdentityMismatch``: compositions must never be lost silently."""


class IdentityMismatch(Exception):
    """Two components produced incompatible identities for what should be one symbol."""


class Origin(Enum):
    REPO = "repo"  # defined in the repository's source roots
    TEST = "test"  # defined in the repository's test code (tests, fakes, helpers)
    EXTERNAL = "external"  # stdlib, runtime, third-party, or otherwise outside the repository
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


class Plane(Enum):
    OS = "os"  # kernel-visible: syscalls, sockets, files, processes, native symbols
    SYMBOL = "symbol"  # runtime-visible: the program's logical functions and calls


class Fidelity(Enum):
    COMPLETE = "complete"  # every event of this kind was recorded, in order
    SAMPLED = "sampled"  # periodic snapshots; presence is evidence, order and count are not


class Stimulus(Enum):
    """How execution was caused. It is only ever a way to *cause* execution, never how
    execution is *observed*."""

    EXISTING_TEST = "existing_test"
    GENERATED_PROBE = "generated_probe"  # disposable isolated unit probe (later experiment)
    DIRECT_CALL = "direct_call"  # harness invoked an entrypoint directly


@dataclass(frozen=True)
class Collector:
    """The capture adapter that produced a set of nodes, and what its output means."""

    name: str  # e.g. "py-sys-monitoring", "linux-ptrace-syscalls", "perf-sample"
    plane: Plane
    fidelity: Fidelity


class SubstitutionMechanism(Enum):
    """How the real implementation was kept out of the execution. Language-neutral: a mock
    object, a hand-written fake, a DI binding, a monkey-patched module attribute, an
    LD_PRELOAD interposer and a stubbed function pointer are all the same thing here."""

    MOCK_OBJECT = "mock_object"  # framework-generated stand-in (unittest.mock, gomock, jest.fn)
    FAKE = "fake"  # hand-written in-test implementation
    DI_BINDING = "di_binding"  # injector configured with a test implementation
    INTERPOSITION = "interposition"  # attribute/symbol replaced (patch, monkeypatch, LD_PRELOAD)
    STUB = "stub"  # function pointer/callback replaced
    UNKNOWN = "unknown"


ArgShapes = tuple[tuple[str, str, str], ...]
"""Bounded argument summary for seam matching: ``((name, shape, digest), ...)`` in
positional order, receiver excluded. ``shape`` is ``<type>`` or ``<type>[<size>]``.
``digest`` is a stable content digest of the value to a bounded depth (never the value
itself), or ``""`` when the collector could not summarize it. A stand-in call that only
exposes positional arguments names them ``arg0``, ``arg1``... Composition compares by
position: ``ARG_SHAPE`` compares types only; ``VALUE`` requires equal, non-empty digests
at every observed position. Sizes are value-level and never affect ``ARG_SHAPE``."""

Outcome = str
"""How a call ended: ``"returned"``, ``"raised:<symbol of the exception type>"``, or
``"unknown"`` when the collector could not observe it. Composition treats a returning seam
joined to a raising fragment (or vice versa) as an outcome conflict: the seed's
continuation after the stand-in assumed the other outcome, so the join is unsound."""


@dataclass(frozen=True)
class CallNode:
    """One logical call observed on the symbol plane. Nodes form a tree via ``parent``."""

    id: int  # unique within its execution
    parent: int | None  # None only for the execution's root (the stimulus itself)
    symbol: SymbolId
    collector: int  # index into Execution.collectors
    args: ArgShapes = ()
    thread: int = 0  # 0 is the stimulus thread; others numbered in order of first appearance
    outcome: Outcome = "unknown"
    result: str = ""  # digest of the returned value (same scheme as ArgShapes), "" if unavailable


@dataclass(frozen=True)
class SubstitutionNode:
    """Control left the production symbol space into a stand-in.

    Three separate facts are kept apart: what actually executed (``substitute``), what
    production component it stands in for (``claimed_target``), and how the two are related
    (``relation``). A stand-in is **not necessarily a leaf**: a framework mock usually is,
    but a hand-written fake, an in-memory repository, a DI test implementation or a proxy
    executes code of its own, and that code appears as children of this node."""

    id: int
    parent: int  # the real symbol-plane call that invoked the stand-in
    collector: int
    mechanism: SubstitutionMechanism
    substitute: SymbolId | None
    """What actually executed: the fake's class, the stub function, the mock's runtime type.
    None when the substitute has no meaningful symbol of its own."""
    claimed_target: SymbolId | None
    """What the stand-in *says* it replaces, read off the artefact itself (a spec class, a
    patch target string, a generated-mock interface). None when it says nothing. This is
    a fact about the artefact, not a resolution: interpretation happens downstream."""
    relation: str
    """The observable relationship between substitute and claimed target, e.g. "spec",
    "patch-target", "implements", "generated-from", "none". Lets the resolver weight the
    claim and lets a reader audit it."""
    path: tuple[str, ...] = ()
    """Member path invoked on the stand-in, e.g. ``("execute", "()", "fetchone")`` where
    ``"()"`` marks a call's return value."""
    args: ArgShapes = ()
    outcome: Outcome = "unknown"
    result: str = ""
    """Digest of what the stand-in returned. The seed's continuation after this node is
    conditioned on this value; a composed fragment that returned something else leaves
    that continuation unsupported by any execution."""


class OsEventKind(Enum):
    CONNECT = "connect"  # outbound socket connection attempt
    LISTEN = "listen"
    DNS = "dns"
    OPEN = "open"  # file open (path recorded; may be a local config file, see docs)
    EXEC = "exec"  # process image replaced
    SPAWN = "spawn"  # child process created
    OTHER = "other"


@dataclass(frozen=True)
class OsEventNode:
    """A kernel-visible event, attributed to the innermost symbol-plane call active at the
    time when attribution is possible, otherwise to the execution root."""

    id: int
    parent: int
    collector: int
    kind: OsEventKind
    target: str  # endpoint, path, or command as the kernel saw it
    outcome: str  # "ok", or the errno/reason it failed, e.g. "ENETUNREACH" inside the sandbox
    native_symbol: str | None = None  # calling native symbol when the OS plane could resolve it


Node = CallNode | SubstitutionNode | OsEventNode


@dataclass(frozen=True)
class Execution:
    """One stimulus applied to one process, and everything observed about it."""

    id: str  # stable, e.g. "<stimulus_ref>@<revision>"
    stimulus: Stimulus
    stimulus_ref: str  # test id, probe path, or entrypoint symbol
    outcome: str  # "passed" | "failed" | ...; only passing executions are composition sources
    revision: str | None  # VCS revision the trace was taken at, if known
    collectors: tuple[Collector, ...]
    symbols: tuple[Symbol, ...]  # every SymbolId referenced by nodes, with origin and location
    nodes: tuple[Node, ...]


# ------------------------------------------------------------------------ interpretation


class BoundaryClass(Enum):
    INTERNAL = "internal"  # stands in for code in this repository: a continuation point
    EXTERNAL = "external"  # stands in for something outside the repository: terminal
    UNRESOLVED = "unresolved"  # not enough evidence to decide: terminal, reported, never guessed


@dataclass(frozen=True)
class BoundaryResolution:
    classification: BoundaryClass
    target: SymbolId | None  # the real symbol the stand-in represents, when known
    rule: str  # which deterministic rule decided this


class JoinStrength(Enum):
    """How a composed seam was matched. Each level implies the ones before it."""

    SYMBOL = 1  # same SymbolId on both sides
    ARG_SHAPE = 2  # and argument arity/types compatible
    VALUE = 3  # and argument values at the seam compatible
    STATE = 4  # and relevant reachable state at the seam compatible


class EvidenceKind(Enum):
    OBSERVED = "observed"  # complete trace: caller called callee, same execution
    OBSERVED_SAMPLED = "observed_sampled"  # sampled: callee seen under caller; order/count unknown
    COMPOSED = "composed"  # call hit an internal stand-in; continuation is another execution
    STATIC = "static"  # statically possible, never executed (reserved; not produced yet)
    INTERNAL_GAP = "internal_gap"  # internal stand-in, no execution of the real target yet
    EXTERNAL_BOUNDARY = "external_boundary"  # semantic boundary: stand-in for outside code
    OS_BOUNDARY = "os_boundary"  # physical boundary: the process tried to leave via the kernel
    UNRESOLVED_BOUNDARY = "unresolved_boundary"  # stand-in we could not classify


_RULE_REQUIRED = {
    EvidenceKind.COMPOSED,
    EvidenceKind.STATIC,
    EvidenceKind.INTERNAL_GAP,
    EvidenceKind.EXTERNAL_BOUNDARY,
    EvidenceKind.UNRESOLVED_BOUNDARY,
}
_RULE_FORBIDDEN = {EvidenceKind.OBSERVED, EvidenceKind.OBSERVED_SAMPLED, EvidenceKind.OS_BOUNDARY}


@dataclass(frozen=True)
class NodeRef:
    execution: str
    node: int


@dataclass(frozen=True)
class Evidence:
    """Why we believe an edge exists. Invariants are enforced at construction so that
    evidence can never be silently upgraded."""

    kind: EvidenceKind
    site: NodeRef
    """The observed node that grounds this evidence. For boundary and composed kinds this is
    the substitution or OS event itself: the *call into it* was observed even when the
    continuation was not."""
    rule: str | None = None
    """Resolution or analysis rule. Required for anything derived (composed, static,
    boundaries); forbidden for direct observations, which have no rule to cite."""
    fragment: NodeRef | None = None
    """COMPOSED only: the root of the borrowed continuation, a real call to the target in
    some (usually different) execution."""
    join: JoinStrength | None = None
    """COMPOSED only: how strongly the seam was matched."""
    probe_derived: bool = False
    """True if any execution this evidence cites was a generated probe rather than an
    existing test. Set by whoever builds the evidence and knows the executions."""

    def __post_init__(self) -> None:
        if self.kind in _RULE_REQUIRED and self.rule is None:
            raise ValueError(f"{self.kind.value} evidence must name its rule")
        if self.kind in _RULE_FORBIDDEN and self.rule is not None:
            raise ValueError(f"{self.kind.value} evidence is a direct observation and has no rule")
        composed = self.kind is EvidenceKind.COMPOSED
        if composed != (self.fragment is not None):
            raise ValueError("a fragment is required for, and only for, composed evidence")
        if composed != (self.join is not None):
            raise ValueError("a join strength is required for, and only for, composed evidence")


@dataclass(frozen=True)
class Edge:
    caller: SymbolId
    callee: SymbolId
    evidence: Evidence
