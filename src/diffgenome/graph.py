"""Repository-level behavioral graph: every execution's evidence merged, nothing flattened.

Built by composing from every execution as a seed and merging the resulting edges by
(caller, callee, kind). An edge keeps every piece of evidence that supports it, so a
reader can always get back to the executions, seams and fragments behind it. Language-
agnostic: it consumes the protocol and the composer's output only.
"""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from diffgenome.compose import Composition, Corpus, Gap, JoinAttempt, compose
from diffgenome.model import (
    CallNode,
    Evidence,
    EvidenceKind,
    JoinStrength,
    NodeRef,
    Origin,
    Symbol,
    SymbolId,
)

_TERMINAL = {
    EvidenceKind.EXTERNAL_BOUNDARY,
    EvidenceKind.OS_BOUNDARY,
    EvidenceKind.UNRESOLVED_BOUNDARY,
    EvidenceKind.INTERNAL_GAP,
}
_TRAVERSABLE = {EvidenceKind.OBSERVED, EvidenceKind.OBSERVED_SAMPLED, EvidenceKind.COMPOSED}


@dataclass
class GraphEdge:
    caller: SymbolId
    callee: SymbolId
    kind: EvidenceKind
    evidence: list[Evidence] = field(default_factory=list)
    executions: set[str] = field(default_factory=set)  # executions whose observations support it
    rules: set[str] = field(default_factory=set)
    joins: Counter[JoinStrength] = field(default_factory=Counter)  # composed only
    probe_derived: bool = False

    @property
    def best_join(self) -> JoinStrength | None:
        return max(self.joins, key=lambda j: j.value) if self.joins else None

    @property
    def strong(self) -> bool:
        """Observed, or composed at VALUE or better. The bar the north star counts."""
        if self.kind is EvidenceKind.OBSERVED:
            return True
        best = self.best_join
        return self.kind is EvidenceKind.COMPOSED and best is not None and best.value >= 3

    def add(self, ev: Evidence) -> None:
        key = (ev.site, ev.fragment)
        if any((e.site, e.fragment) == key for e in self.evidence):
            return
        self.evidence.append(ev)
        self.executions.add(ev.site.execution)
        if ev.fragment:
            self.executions.add(ev.fragment.execution)
            self.executions.update(a.execution for a in ev.alternates)
        if ev.rule:
            self.rules.add(ev.rule)
        if ev.join:
            self.joins[ev.join] += 1
        self.probe_derived = self.probe_derived or ev.probe_derived


@dataclass
class BehavioralGraph:
    """One repository-level graph. Built once from a corpus; serializable to JSON with all
    provenance and loadable back for queries without the corpus."""

    symbols: dict[SymbolId, Symbol]
    edges: dict[tuple[SymbolId, SymbolId, EvidenceKind], GraphEdge]
    out: dict[SymbolId, list[GraphEdge]]
    inc: dict[SymbolId, list[GraphEdge]]
    tests_by_symbol: dict[SymbolId, set[str]]  # executions in which the symbol really ran
    outcomes_by_symbol: dict[SymbolId, Counter[str]]
    gaps: list[Gap]
    attempts: list[JoinAttempt]  # every join attempt, accepted or not
    corpus: Corpus | None = None  # present when built from traces; None when loaded from JSON
    compositions: dict[str, Composition] = field(default_factory=dict)
    use_state: bool = True  # whether the STATE rung was consulted when this graph was built

    def origin(self, symbol: SymbolId) -> Origin:
        s = self.symbols.get(symbol)
        return s.origin if s else Origin.UNKNOWN

    # ------------------------------------------------------------------ materialization

    def to_json(self) -> dict[str, object]:
        def ev(e: Evidence) -> dict[str, object]:
            return {
                "kind": e.kind.value,
                "site": {"execution": e.site.execution, "node": e.site.node},
                "fragment": {"execution": e.fragment.execution, "node": e.fragment.node}
                if e.fragment
                else None,
                "alternates": [{"execution": a.execution, "node": a.node} for a in e.alternates],
                "join": e.join.name if e.join else None,
                "exit": e.exit,
                "rule": e.rule,
                "probe_derived": e.probe_derived,
            }

        return {
            "format": "diffgenome-graph/1",
            "symbols": [
                {
                    "id": s.id,
                    "origin": s.origin.value,
                    "location": {"path": s.location.path, "line": s.location.line}
                    if s.location
                    else None,
                    "kind": s.kind,
                    "executed_by": sorted(self.tests_by_symbol.get(s.id, ())),
                    "outcomes": dict(self.outcomes_by_symbol.get(s.id, Counter())),
                }
                for s in sorted(self.symbols.values(), key=lambda x: x.id)
            ],
            "edges": [
                {
                    "caller": e.caller,
                    "callee": e.callee,
                    "kind": e.kind.value,
                    "best_join": e.best_join.name if e.best_join else None,
                    "joins": {
                        j.name: n for j, n in sorted(e.joins.items(), key=lambda x: x[0].value)
                    },
                    "rules": sorted(e.rules),
                    "executions": sorted(e.executions),
                    "probe_derived": e.probe_derived,
                    "evidence": [ev(x) for x in e.evidence],
                }
                for e in sorted(
                    self.edges.values(), key=lambda x: (x.caller, x.callee, x.kind.value)
                )
            ],
            "gaps": [
                {
                    "site": {"execution": g.site.execution, "node": g.site.node},
                    "target": g.target,
                    "kind": g.kind,
                }
                for g in self.gaps
            ],
            "join_attempts": [
                {
                    "site": {"execution": a.site.execution, "node": a.site.node},
                    "fragment": {"execution": a.fragment.execution, "node": a.fragment.node},
                    "target": a.target,
                    "grade": a.grade.name if a.grade else None,
                    "accepted": a.accepted,
                    "note": a.note,
                    "result_compatible": a.result_compatible,
                    "exit": a.exit,
                }
                for a in self.attempts
            ],
        }

    @classmethod
    def from_json(cls, doc: dict[str, Any]) -> BehavioralGraph:
        from diffgenome.model import SourceLocation

        symbols: dict[SymbolId, Symbol] = {}
        tests: dict[SymbolId, set[str]] = {}
        outcomes: dict[SymbolId, Counter[str]] = {}
        for s in doc["symbols"]:
            loc = (
                SourceLocation(s["location"]["path"], s["location"]["line"])
                if s["location"]
                else None
            )
            symbols[s["id"]] = Symbol(s["id"], Origin(s["origin"]), loc, s.get("kind", "callable"))
            tests[s["id"]] = set(s["executed_by"])
            outcomes[s["id"]] = Counter(s["outcomes"])
        edges: dict[tuple[SymbolId, SymbolId, EvidenceKind], GraphEdge] = {}
        for e in doc["edges"]:
            kind = EvidenceKind(e["kind"])
            ge = GraphEdge(e["caller"], e["callee"], kind)
            for x in e["evidence"]:
                ge.add(
                    Evidence(
                        EvidenceKind(x["kind"]),
                        NodeRef(x["site"]["execution"], x["site"]["node"]),
                        rule=x["rule"],
                        fragment=NodeRef(x["fragment"]["execution"], x["fragment"]["node"])
                        if x["fragment"]
                        else None,
                        join=JoinStrength[x["join"]] if x["join"] else None,
                        alternates=tuple(
                            NodeRef(a["execution"], a["node"]) for a in x["alternates"]
                        ),
                        probe_derived=x["probe_derived"],
                    )
                )
            edges[(ge.caller, ge.callee, kind)] = ge
        out: dict[SymbolId, list[GraphEdge]] = defaultdict(list)
        inc: dict[SymbolId, list[GraphEdge]] = defaultdict(list)
        for ge in edges.values():
            out[ge.caller].append(ge)
            inc[ge.callee].append(ge)
        gaps = [
            Gap(NodeRef(g["site"]["execution"], g["site"]["node"]), g["target"], g["kind"])
            for g in doc["gaps"]
        ]
        attempts = [
            JoinAttempt(
                NodeRef(a["site"]["execution"], a["site"]["node"]),
                NodeRef(a["fragment"]["execution"], a["fragment"]["node"]),
                a["target"],
                JoinStrength[a["grade"]] if a["grade"] else None,
                a["accepted"],
                a["note"],
                a["result_compatible"],
                a.get("exit"),
            )
            for a in doc["join_attempts"]
        ]
        return cls(symbols, edges, dict(out), dict(inc), tests, outcomes, gaps, attempts)

    # ------------------------------------------------------------------ queries

    def inspect(self, symbol: SymbolId, depth: int = 3) -> Inspection:
        up = self._walk(symbol, depth, upstream=True)
        down = self._walk(symbol, depth, upstream=False)
        boundaries = [e for e in self.out.get(symbol, []) if e.kind in _TERMINAL]
        return Inspection(
            symbol=symbol,
            upstream=up,
            downstream=down,
            tests=sorted(self.tests_by_symbol.get(symbol, ())),
            boundaries=boundaries,
            gaps=[g for g in self.gaps if g.target == symbol],
            outcomes=self.outcomes_by_symbol.get(symbol, Counter()),
        )

    def _walk(self, start: SymbolId, depth: int, upstream: bool) -> list[tuple[int, GraphEdge]]:
        """Bounded BFS over traversable edges, returning (distance, edge). Terminal edges at
        the frontier are included at their distance so boundaries are visible."""
        index = self.inc if upstream else self.out
        seen: set[tuple[SymbolId, SymbolId, EvidenceKind]] = set()
        result: list[tuple[int, GraphEdge]] = []
        frontier: deque[tuple[SymbolId, int]] = deque([(start, 0)])
        visited = {start}
        while frontier:
            sym, d = frontier.popleft()
            if d >= depth:
                continue
            for e in index.get(sym, []):
                key = (e.caller, e.callee, e.kind)
                if key in seen:
                    continue
                seen.add(key)
                result.append((d + 1, e))
                nxt = e.caller if upstream else e.callee
                if e.kind in _TRAVERSABLE and nxt not in visited:
                    visited.add(nxt)
                    frontier.append((nxt, d + 1))
        return result

    def neighborhood(self, seeds: list[SymbolId], up: int = 3, down: int = 4) -> Neighborhood:
        edges: dict[tuple[SymbolId, SymbolId, EvidenceKind], tuple[int, GraphEdge]] = {}
        for s in seeds:
            for d, e in self._walk(s, up, upstream=True) + self._walk(s, down, upstream=False):
                key = (e.caller, e.callee, e.kind)
                if key not in edges or d < edges[key][0]:
                    edges[key] = (d, e)
        symbols = set(seeds)
        for _, e in edges.values():
            symbols.update((e.caller, e.callee))
        tests: set[str] = set()
        for s in symbols:
            tests.update(self.tests_by_symbol.get(s, ()))
        return Neighborhood(seeds, edges, symbols, tests, self)


@dataclass
class Inspection:
    symbol: SymbolId
    upstream: list[tuple[int, GraphEdge]]
    downstream: list[tuple[int, GraphEdge]]
    tests: list[str]
    boundaries: list[GraphEdge]
    gaps: list[Gap]
    outcomes: Counter[str]


@dataclass
class Metrics:
    observed: int
    composed: int
    strong_joins: int  # composed edges whose best join is VALUE or better
    weak_joins: int  # composed edges at SYMBOL / ARG_SHAPE only
    internal_gaps: int
    unresolved_boundaries: int
    external_boundaries: int
    os_boundaries: int
    unsound_attempts: int
    probe_derived_edges: int
    symbols: int
    tests: int

    @property
    def denominator(self) -> int:
        """Provisional: the seams we *know about* in the neighborhood. Observed and composed
        edges plus the places where knowledge stops inside the repository (gaps, weak
        joins, unresolved stand-ins). External and OS boundaries are terminal by design
        and are not counted as missing. This is not the true set of locally realizable
        behavior; it undercounts anything no execution has come near."""
        return self.observed + self.composed + self.internal_gaps + self.unresolved_boundaries

    @property
    def reconstructed(self) -> int:
        return self.observed + self.strong_joins

    @property
    def ratio(self) -> float:
        return self.reconstructed / self.denominator if self.denominator else 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "observed_edges": self.observed,
            "composed_edges": self.composed,
            "strong_joins": self.strong_joins,
            "weak_joins": self.weak_joins,
            "internal_gaps": self.internal_gaps,
            "unresolved_boundaries": self.unresolved_boundaries,
            "external_boundaries": self.external_boundaries,
            "os_boundaries": self.os_boundaries,
            "unsound_attempts": self.unsound_attempts,
            "probe_derived_edges": self.probe_derived_edges,
            "symbols": self.symbols,
            "tests": self.tests,
            "reconstructed": self.reconstructed,
            "denominator_provisional": self.denominator,
            "reconstruction_ratio_provisional": round(self.ratio, 3),
        }


@dataclass
class Neighborhood:
    seeds: list[SymbolId]
    edges: dict[tuple[SymbolId, SymbolId, EvidenceKind], tuple[int, GraphEdge]]
    symbols: set[SymbolId]
    tests: set[str]
    graph: BehavioralGraph

    def edges_of(self, kind: EvidenceKind) -> list[tuple[int, GraphEdge]]:
        return sorted(
            ((d, e) for d, e in self.edges.values() if e.kind is kind),
            key=lambda x: (x[0], x[1].caller, x[1].callee),
        )

    def metrics(self) -> Metrics:
        es = [e for _, e in self.edges.values()]
        composed = [e for e in es if e.kind is EvidenceKind.COMPOSED]
        strong = sum(1 for e in composed if e.strong)
        sites = {ev.site for e in es for ev in e.evidence}
        unsound = sum(1 for a in self.graph.attempts if a.grade is None and a.site in sites)
        return Metrics(
            observed=sum(1 for e in es if e.kind is EvidenceKind.OBSERVED),
            composed=len(composed),
            strong_joins=strong,
            weak_joins=len(composed) - strong,
            internal_gaps=sum(1 for e in es if e.kind is EvidenceKind.INTERNAL_GAP),
            unresolved_boundaries=sum(1 for e in es if e.kind is EvidenceKind.UNRESOLVED_BOUNDARY),
            external_boundaries=sum(1 for e in es if e.kind is EvidenceKind.EXTERNAL_BOUNDARY),
            os_boundaries=sum(1 for e in es if e.kind is EvidenceKind.OS_BOUNDARY),
            unsound_attempts=unsound,
            probe_derived_edges=sum(1 for e in es if e.probe_derived),
            symbols=len(self.symbols),
            tests=len(self.tests),
        )


def build_graph(
    corpus: Corpus, min_join: JoinStrength = JoinStrength.SYMBOL, use_state: bool = True
) -> BehavioralGraph:
    edges: dict[tuple[SymbolId, SymbolId, EvidenceKind], GraphEdge] = {}
    gaps: list[Gap] = []
    attempts: list[JoinAttempt] = []
    compositions: dict[str, Composition] = {}
    seen_gaps: set[tuple[NodeRef, SymbolId, str]] = set()
    seen_attempts: set[tuple[NodeRef, NodeRef]] = set()
    for ex_id in corpus.executions:
        c = compose(corpus, ex_id, min_join=min_join, use_state=use_state)
        compositions[ex_id] = c
        for edge in c.edges():
            key = (edge.caller, edge.callee, edge.evidence.kind)
            edges.setdefault(key, GraphEdge(*key)).add(edge.evidence)
        for g in c.gaps:
            k = (g.site, g.target, g.kind)
            if k not in seen_gaps:
                seen_gaps.add(k)
                gaps.append(g)
        for a in c.attempts:
            k2 = (a.site, a.fragment)
            if k2 not in seen_attempts:
                seen_attempts.add(k2)
                attempts.append(a)
    out: dict[SymbolId, list[GraphEdge]] = defaultdict(list)
    inc: dict[SymbolId, list[GraphEdge]] = defaultdict(list)
    for e in edges.values():
        out[e.caller].append(e)
        inc[e.callee].append(e)
    tests_by_symbol: dict[SymbolId, set[str]] = defaultdict(set)
    outcomes: dict[SymbolId, Counter[str]] = defaultdict(Counter)
    for ex in corpus.executions.values():
        for n in ex.nodes:
            if isinstance(n, CallNode) and n.id != 0:
                tests_by_symbol[n.symbol].add(ex.id)
                outcomes[n.symbol][n.outcome.split(":")[0]] += 1
    return BehavioralGraph(
        dict(corpus.symbols), edges, dict(out), dict(inc), dict(tests_by_symbol), dict(outcomes),
        gaps, attempts, corpus, compositions,
        use_state=use_state,
    )  # fmt: skip
