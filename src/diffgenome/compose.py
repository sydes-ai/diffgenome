"""Composition: join independently observed execution fragments at internal boundaries.

Language-agnostic. Input is a corpus of `Execution`s; output is a tree of `Branch`es
rooted at one seed execution, where every branch carries an `Edge` with explicit
`Evidence`, plus the join attempts and gaps that the expansion produced. Fragments are
never flattened into paths: alternatives for one seam are sibling branches.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from diffgenome.model import (
    BoundaryClass,
    CallNode,
    Edge,
    Evidence,
    EvidenceKind,
    Execution,
    Fidelity,
    IdentityMismatch,
    JoinStrength,
    Node,
    NodeRef,
    Origin,
    OsEventNode,
    Stimulus,
    SubstitutionNode,
    Symbol,
    SymbolId,
)
from diffgenome.resolve import resolve


@dataclass
class Corpus:
    executions: dict[str, Execution]
    symbols: dict[SymbolId, Symbol]
    fragments: dict[SymbolId, list[NodeRef]]  # real calls by symbol, passing executions only
    children: dict[str, dict[int, list[Node]]]


def _merge_symbol(table: dict[SymbolId, Symbol], sym: Symbol, execution: str) -> None:
    have = table.get(sym.id)
    if have is None:
        table[sym.id] = sym
        return
    known = {have.origin, sym.origin} - {Origin.UNKNOWN}
    if len(known) > 1:
        raise IdentityMismatch(
            f"{sym.id}: origin {have.origin.value} vs {sym.origin.value} (in {execution})"
        )
    if have.location and sym.location and have.location != sym.location:
        raise IdentityMismatch(f"{sym.id}: {have.location} vs {sym.location} (in {execution})")
    if have.origin is Origin.UNKNOWN or (have.location is None and sym.location):
        table[sym.id] = Symbol(
            sym.id, sym.origin if have.origin is Origin.UNKNOWN else have.origin,
            have.location or sym.location,
        )  # fmt: skip


def build_corpus(executions: list[Execution]) -> Corpus:
    symbols: dict[SymbolId, Symbol] = {}
    fragments: dict[SymbolId, list[NodeRef]] = defaultdict(list)
    children: dict[str, dict[int, list[Node]]] = {}
    by_id: dict[str, Execution] = {}
    for ex in executions:
        if ex.id in by_id:
            raise ValueError(f"duplicate execution id {ex.id}")
        by_id[ex.id] = ex
        for sym in ex.symbols:
            _merge_symbol(symbols, sym, ex.id)
        kids: dict[int, list[Node]] = defaultdict(list)
        for node in ex.nodes:
            if node.parent is not None:
                kids[node.parent].append(node)
            if isinstance(node, CallNode) and node.id != 0 and ex.outcome == "passed":
                fragments[node.symbol].append(NodeRef(ex.id, node.id))
        children[ex.id] = kids
    return Corpus(by_id, symbols, dict(fragments), children)


@dataclass
class JoinAttempt:
    site: NodeRef
    fragment: NodeRef
    target: SymbolId
    grade: JoinStrength | None  # None: known unsound (outcome conflict), never composable
    accepted: bool
    note: str = ""
    result_compatible: bool | None = None
    """Whether the fragment returned what the stand-in returned (None: unknown). Entry
    compatibility (the grade) says the fragment could continue from the seam; result
    compatibility says the seed's continuation *after* the seam is supported. They are
    independent, and only the first is a join grade."""


@dataclass
class Gap:
    site: NodeRef
    target: SymbolId
    kind: str  # "no-fragment" | "no-compatible-fragment" | "cycle" | "depth"


@dataclass
class Branch:
    edge: Edge
    children: list[Branch] = field(default_factory=list)


@dataclass
class Composition:
    seed: str
    root: SymbolId
    branches: list[Branch]
    attempts: list[JoinAttempt]
    gaps: list[Gap]

    def edges(self) -> list[Edge]:
        out: list[Edge] = []

        def walk(bs: list[Branch]) -> None:
            for b in bs:
                out.append(b.edge)
                walk(b.children)

        walk(self.branches)
        return out


def _shape_type(shape: str) -> str:
    return shape.split("[", 1)[0]


def outcomes_compatible(site: SubstitutionNode, fragment: CallNode) -> bool | None:
    """None when either outcome is unknown. Returned-vs-raised is a conflict: the seed kept
    running on the assumption of the outcome the stand-in produced, and the fragment's
    continuation is the other one."""
    a, b = site.outcome, fragment.outcome
    if a == "unknown" or b == "unknown":
        return None
    return bool(a.startswith("raised") == b.startswith("raised"))


def grade_seam(site: SubstitutionNode, fragment: CallNode) -> tuple[JoinStrength | None, str]:
    """Grade a seam, or return ``None`` when it is known unsound (outcome conflict).

    ARG_SHAPE compares argument *types* by position. Sizes differ → still ARG_SHAPE, with
    a note: sizes are value-level and would need the VALUE join, which no collector
    supplies yet. A type conflict is evidence against the seam and is noted."""
    compatible = outcomes_compatible(site, fragment)
    if compatible is False:
        return None, f"outcome conflict: stand-in {site.outcome}, fragment {fragment.outcome}"
    notes = [] if compatible else ["outcome unknown on one side"]
    if not site.args or not fragment.args:
        return JoinStrength.SYMBOL, "; ".join([*notes, "no argument shapes on one side"])
    pairs = list(zip(site.args, fragment.args, strict=False))
    conflicts = [f"{a}≠{b}" for (_, a, _), (_, b, _) in pairs if _shape_type(a) != _shape_type(b)]
    if conflicts:
        return JoinStrength.SYMBOL, "; ".join([*notes, "type conflict: " + ", ".join(conflicts)])
    missing = [n for (_, _, da), (n, _, db) in pairs if not da or not db]
    if missing:
        notes.append("value unavailable: " + ", ".join(missing))
        return JoinStrength.ARG_SHAPE, "; ".join(notes)
    differ = [n for (_, _, da), (n, _, db) in pairs if da != db]
    if differ:
        notes.append("values differ: " + ", ".join(differ))
        return JoinStrength.ARG_SHAPE, "; ".join(notes)
    if compatible is None:
        return JoinStrength.ARG_SHAPE, "; ".join(notes)  # never VALUE with an unknown outcome
    return JoinStrength.VALUE, ""


def _node_symbol(node: Node) -> SymbolId:
    if isinstance(node, CallNode):
        return node.symbol
    if isinstance(node, SubstitutionNode):
        return node.substitute or node.claimed_target or "stand-in:?"
    return f"os:{node.kind.value}:{node.target}"


def _invoked(sub: SubstitutionNode, target: SymbolId | None) -> SymbolId:
    """What the stand-in call invoked, as an edge callee. The claim names the first member
    of the path; a longer path (a call on a return value) is appended so that
    ``execute`` and ``execute.().fetchone`` are distinct callees."""
    if target is None:
        return f"stand-in:{sub.substitute}.{'.'.join(sub.path)}"
    return target + "".join(f".{p}" for p in sub.path[1:])


def compose(
    corpus: Corpus,
    seed_id: str,
    min_join: JoinStrength = JoinStrength.SYMBOL,
    max_depth: int = 8,
) -> Composition:
    seed = corpus.executions[seed_id]
    attempts: list[JoinAttempt] = []
    gaps: list[Gap] = []

    def probe(*ids: str) -> bool:
        return any(corpus.executions[i].stimulus is Stimulus.GENERATED_PROBE for i in ids)

    def expand(ex: Execution, node_id: int, caller: SymbolId, on_path: frozenset[SymbolId],
               depth: int) -> list[Branch]:  # fmt: skip
        out: list[Branch] = []
        for child in corpus.children[ex.id].get(node_id, []):
            site = NodeRef(ex.id, child.id)
            if isinstance(child, CallNode):
                complete = ex.collectors[child.collector].fidelity is Fidelity.COMPLETE
                kind = EvidenceKind.OBSERVED if complete else EvidenceKind.OBSERVED_SAMPLED
                ev = Evidence(kind, site, probe_derived=probe(ex.id))
                out.append(Branch(Edge(caller, child.symbol, ev),
                                  expand(ex, child.id, child.symbol, on_path, depth)))  # fmt: skip
                continue
            if isinstance(child, OsEventNode):
                ev = Evidence(EvidenceKind.OS_BOUNDARY, site, probe_derived=probe(ex.id))
                out.append(Branch(Edge(caller, _node_symbol(child), ev)))
                continue
            res = resolve(child, corpus.symbols)
            executed = expand(ex, child.id, _node_symbol(child), on_path, depth)
            if res.classification is BoundaryClass.EXTERNAL:
                ev = Evidence(EvidenceKind.EXTERNAL_BOUNDARY, site, rule=res.rule,
                              probe_derived=probe(ex.id))  # fmt: skip
                out.append(Branch(Edge(caller, _invoked(child, res.target), ev), executed))
                continue
            if res.classification is BoundaryClass.UNRESOLVED:
                ev = Evidence(EvidenceKind.UNRESOLVED_BOUNDARY, site, rule=res.rule,
                              probe_derived=probe(ex.id))  # fmt: skip
                out.append(Branch(Edge(caller, _invoked(child, res.target), ev), executed))
                continue
            target = res.target
            assert target is not None
            frags = corpus.fragments.get(target, [])
            accepted_any = False
            for ref in frags:
                frag_ex = corpus.executions[ref.execution]
                frag_node = frag_ex.nodes[ref.node]
                assert isinstance(frag_node, CallNode)
                grade, note = grade_seam(child, frag_node)
                ok = grade is not None and grade.value >= min_join.value
                same_result = (
                    child.result == frag_node.result if child.result and frag_node.result else None
                )
                if same_result is False:
                    note = "; ".join(filter(None, [note, "result differs: seed continued on it"]))
                attempts.append(JoinAttempt(site, ref, target, grade, ok, note, same_result))
                if not ok or grade is None:
                    continue
                accepted_any = True
                ev = Evidence(EvidenceKind.COMPOSED, site, rule=res.rule, fragment=ref,
                              join=grade, probe_derived=probe(ex.id, ref.execution))  # fmt: skip
                if target in on_path:
                    gaps.append(Gap(site, target, "cycle"))
                    out.append(Branch(Edge(caller, target, ev), executed))
                elif depth >= max_depth:
                    gaps.append(Gap(site, target, "depth"))
                    out.append(Branch(Edge(caller, target, ev), executed))
                else:
                    kids = expand(frag_ex, frag_node.id, target, on_path | {target}, depth + 1)
                    out.append(Branch(Edge(caller, target, ev), executed + kids))
            if not accepted_any:
                gaps.append(
                    Gap(site, target, "no-fragment" if not frags else "no-compatible-fragment")
                )
                ev = Evidence(EvidenceKind.INTERNAL_GAP, site, rule=res.rule,
                              probe_derived=probe(ex.id))  # fmt: skip
                out.append(Branch(Edge(caller, target, ev), executed))
        return out

    root = seed.nodes[0]
    assert isinstance(root, CallNode)
    branches = expand(seed, 0, root.symbol, frozenset(), 0)
    return Composition(seed_id, root.symbol, branches, attempts, gaps)
