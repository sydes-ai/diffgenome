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
    if (
        have.origin is Origin.UNKNOWN
        or (have.location is None and sym.location)
        or (have.kind == "callable" and sym.kind != "callable")
    ):
        table[sym.id] = Symbol(
            sym.id, sym.origin if have.origin is Origin.UNKNOWN else have.origin,
            have.location or sym.location,
            sym.kind if sym.kind != "callable" else have.kind,
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
    grade: JoinStrength | None  # None: known unsound (exit/type/state conflict), never composable
    accepted: bool
    note: str = ""
    result_compatible: bool | None = None
    exit: str | None = None  # exit compatibility: same | kind | unknown | None (conflict)
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


_STRUCTURAL = (
    "NoneType", "null", "undefined", "nil", "int", "float", "str", "bool", "bytes", "number",
    "string", "boolean", "bigint", "list", "tuple", "dict", "set", "frozenset", "array", "object",
    "int8", "int16", "int32", "int64", "uint", "uint8", "uint16", "uint32", "uint64", "float32",
    "float64", "[]", "map[",
)  # fmt: skip


def _is_structural(shape: str) -> bool:
    """Primitive, None/nil or container shapes: their kind is the whole story. Anything else
    is an object whose relationship to another object type (interface, subclass, duck
    typing) the collector cannot see."""
    t = _shape_type(shape)
    for k in _STRUCTURAL:
        if t == k or t.startswith(k + "[") or (k.endswith("[") and t.startswith(k)):
            return True
    return t.startswith("[]")


def _types_compatible(a: str, b: str) -> str | None:
    """None when compatible; "conflict" for a decisive structural mismatch (None vs dict is a
    different branch); "object" when two object types differ but may be related (a
    *gin.Context where a context.Context is declared), which is unverified, not wrong.
    A stand-in argument compares as the type it stands in for; a spec-less stand-in is a
    wildcard."""
    ta, tb = _shape_type(a), _shape_type(b)
    if ta == tb:
        return None
    for x, y in ((ta, tb), (tb, ta)):
        if x == "stand-in":
            return None
        if x.startswith("stand-in:") and x[len("stand-in:") :] == y:
            return None
    if _is_structural(ta) or _is_structural(tb):
        return "conflict"
    return "object"


def fragment_shape(corpus: Corpus, ref: NodeRef) -> tuple[object, ...]:
    """Structural signature of a fragment subtree: symbols, kinds, outcomes, claims and
    paths, but not argument values. Fragments with one shape are one behavior path and
    are expanded once; their provenance is kept together (Evidence.alternates)."""
    ex = corpus.executions[ref.execution]

    def walk(node_id: int) -> tuple[object, ...]:
        parts: list[object] = []
        for k in corpus.children[ex.id].get(node_id, []):
            if isinstance(k, CallNode):
                parts.append(("c", k.symbol, k.outcome.split(":")[0], walk(k.id)))
            elif isinstance(k, SubstitutionNode):
                parts.append(("s", k.mechanism.value, k.claimed_target, k.path, walk(k.id)))
            else:
                parts.append(("o", k.kind.value, k.target))
        return tuple(parts)

    root = ex.nodes[ref.node]
    assert isinstance(root, CallNode)
    return (root.symbol, root.outcome.split(":")[0], walk(ref.node))


def outcome_parts(outcome: str) -> tuple[str, str | None]:
    """``category`` and ``identity`` of an Outcome string (see model.Outcome)."""
    cat, _, ident = outcome.partition(":")
    return cat, (ident or None)


def exit_compatibility(site_outcome: str, fragment_outcome: str) -> str | None:
    """EXIT half of join validity. ``same``: categories and known identities agree;
    ``kind``: categories agree and an identity is unknown; ``unknown``: an outcome was not
    observed; None: conflict (different categories, or same category with two different
    known identities: an error-returning seam is not a panicking fragment, and a seam that
    caught ValueError is not a fragment that raised KeyError)."""
    ca, ia = outcome_parts(site_outcome)
    cb, ib = outcome_parts(fragment_outcome)
    if ca == "unknown" or cb == "unknown":
        return "unknown"
    if ca != cb:
        return None
    if ia and ib:
        return "same" if ia == ib else None
    return "same" if (ia is None and ib is None) else "kind"


def outcomes_compatible(site: SubstitutionNode, fragment: CallNode) -> bool | None:
    """Legacy view of exit compatibility: None when unknown, False on conflict."""
    e = exit_compatibility(site.outcome, fragment.outcome)
    return None if e == "unknown" else e is not None


def state_compatibility(site: SubstitutionNode, fragment: CallNode) -> tuple[str, str]:
    """STATE rung. Facts are compared by name over the names both sides observed.
    Returns (verdict, note): ``match`` (>=1 fact compared, all equal), ``conflict`` (a
    compared bucket differs: a different branch condition), ``unavailable`` (no common
    facts, or no facts on a side)."""
    a = {name: (bucket, digest) for name, bucket, digest in site.state}
    b = {name: (bucket, digest) for name, bucket, digest in fragment.state}
    common = sorted(set(a) & set(b))
    if not common:
        return (
            "unavailable",
            "state unavailable on one side" if not a or not b else "no common state facts",
        )
    differ = [n for n in common if a[n] != b[n]]
    if differ:
        return "conflict", "state conflict: " + ", ".join(
            f"{n} {a[n][0]}≠{b[n][0]}" for n in differ
        )
    return "match", f"state matched on {len(common)} fact(s): " + ", ".join(common[:6])


def grade_seam(
    site: SubstitutionNode, fragment: CallNode, use_state: bool = True
) -> tuple[JoinStrength | None, str]:
    """ENTRY grade of a seam, or ``None`` when the join is known unsound (exit conflict,
    decisive argument-kind conflict, or state conflict). Exit compatibility is computed
    separately by `exit_compatibility`; `use_state=False` ignores state facts entirely
    (the VALUE-only baseline of experiment 07)."""
    exit_ = exit_compatibility(site.outcome, fragment.outcome)
    if exit_ is None:
        return None, f"exit conflict: stand-in {site.outcome}, fragment {fragment.outcome}"
    compatible: bool | None = None if exit_ == "unknown" else True
    notes = [] if compatible else ["outcome unknown on one side"]
    if not site.args and not fragment.args:
        # No arguments on either side: argument compatibility holds vacuously. Entry
        # compatibility then rests entirely on receiver state, which is the STATE rung.
        if compatible is None:
            return JoinStrength.ARG_SHAPE, "; ".join([*notes, "no arguments"])
        if not use_state:
            return JoinStrength.VALUE, "no arguments"
        verdict, snote = state_compatibility(site, fragment)
        if verdict == "conflict":
            return None, "no arguments; " + snote
        if verdict == "match":
            return JoinStrength.STATE, "no arguments; " + snote
        return JoinStrength.VALUE, "no arguments; " + snote
    if not site.args or not fragment.args:
        return JoinStrength.SYMBOL, "; ".join([*notes, "arity differs: arguments on one side only"])
    pairs = list(zip(site.args, fragment.args, strict=False))
    verdicts = [(n, a, b, _types_compatible(a, b)) for (n, a, _), (_, b, _) in pairs]
    conflicts = [f"{a}≠{b}" for _, a, b, v in verdicts if v == "conflict"]
    if conflicts:
        # A decisive argument-kind conflict is evidence against the seam, not a weak match:
        # the fragment was entered with different kinds of values (Kokoro: None vs dict).
        return None, "; ".join([*notes, "type conflict: " + ", ".join(conflicts)])
    unverified = [f"{n}: {a} vs {b}" for n, a, b, v in verdicts if v == "object"]
    if unverified:
        notes.append("object types differ, relationship unverified: " + ", ".join(unverified))
        return JoinStrength.ARG_SHAPE, "; ".join(notes)
    wild = [n for n, a, b, _ in verdicts if _shape_type(a) != _shape_type(b)]
    if wild:
        notes.append("stand-in argument, type unverified: " + ", ".join(wild))
        return JoinStrength.ARG_SHAPE, "; ".join(notes)
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
    if not use_state:
        return JoinStrength.VALUE, "; ".join(notes)
    verdict, snote = state_compatibility(site, fragment)
    if verdict == "conflict":
        return None, snote
    if verdict == "match":
        return JoinStrength.STATE, snote
    return JoinStrength.VALUE, "; ".join([*notes, snote])


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
        return "stand-in:" + ".".join(filter(None, [sub.substitute or "?", *sub.path]))
    return target + "".join(f".{p}" for p in sub.path[1:])


def compose(
    corpus: Corpus,
    seed_id: str,
    min_join: JoinStrength = JoinStrength.SYMBOL,
    max_depth: int = 8,
    use_state: bool = True,
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
            groups: dict[
                tuple[object, ...], list[tuple[NodeRef, JoinStrength, str, bool | None]]
            ] = {}
            for ref in frags:
                frag_ex = corpus.executions[ref.execution]
                frag_node = frag_ex.nodes[ref.node]
                assert isinstance(frag_node, CallNode)
                grade, note = grade_seam(child, frag_node, use_state)
                exit_ = exit_compatibility(child.outcome, frag_node.outcome)
                ok = grade is not None and grade.value >= min_join.value
                same_result = (
                    child.result == frag_node.result if child.result and frag_node.result else None
                )
                if same_result is False:
                    note = "; ".join(filter(None, [note, "result differs: seed continued on it"]))
                attempts.append(JoinAttempt(site, ref, target, grade, ok, note, same_result, exit_))
                if ok and grade is not None:
                    groups.setdefault(fragment_shape(corpus, ref), []).append(
                        (ref, grade, note, same_result)
                    )
            for members in groups.values():
                # One branch per distinct behavior path; the best-graded member represents
                # it and the others are kept as alternates, so no provenance is lost.
                members.sort(key=lambda m: (-m[1].value, m[0].execution, m[0].node))
                ref, grade, _, _ = members[0]
                accepted_any = True
                frag_outcome = corpus.executions[ref.execution].nodes[ref.node].outcome
                ev = Evidence(
                    EvidenceKind.COMPOSED,
                    site,
                    rule=res.rule,
                    fragment=ref,
                    join=grade,
                    probe_derived=probe(ex.id, ref.execution),
                    alternates=tuple(m[0] for m in members[1:]),
                    exit=exit_compatibility(child.outcome, frag_outcome),
                )
                frag_ex = corpus.executions[ref.execution]
                if target in on_path:
                    gaps.append(Gap(site, target, "cycle"))
                    out.append(Branch(Edge(caller, target, ev), executed))
                elif depth >= max_depth:
                    gaps.append(Gap(site, target, "depth"))
                    out.append(Branch(Edge(caller, target, ev), executed))
                else:
                    kids = expand(frag_ex, ref.node, target, on_path | {target}, depth + 1)
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
