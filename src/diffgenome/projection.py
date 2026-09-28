"""Behavioral projection of the evidence graph: production behavior with evidence attached.

`graph.json` stays canonical. This module derives the human/product view: one behavioral
edge per production caller→callee pair (observed and composed evidence merged), tests and
probes as evidence annotations rather than branches, boundaries as leaves, and
declarations (symbols with no in-repo executable body) shown as what they are, not as
gaps. It also produces the change-centred JSON slice and the per-case metrics table.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from diffgenome.graph import BehavioralGraph
from diffgenome.model import EvidenceKind, JoinStrength, Origin, Stimulus, SymbolId

_BOUNDARY = {
    EvidenceKind.EXTERNAL_BOUNDARY: "external",
    EvidenceKind.OS_BOUNDARY: "os",
    EvidenceKind.UNRESOLVED_BOUNDARY: "unresolved",
    EvidenceKind.INTERNAL_GAP: "gap",
}


def _short(symbol: str) -> str:
    return symbol.split(":", 1)[-1]


@dataclass
class BehaviorEdge:
    """One production caller→callee relationship with all its evidence merged."""

    caller: SymbolId
    callee: SymbolId
    boundary: (
        str | None
    )  # None for production continuations; else external/os/unresolved/gap/declaration
    observed_executions: set[str] = field(default_factory=set)
    composed: Counter[str] = field(default_factory=Counter)  # grade -> distinct fragment shapes
    alternates: int = 0
    tests: set[str] = field(default_factory=set)
    probes: set[str] = field(default_factory=set)
    rules: set[str] = field(default_factory=set)
    ambiguous: bool = False  # more than one materially different continuation at one seam

    @property
    def glyph(self) -> str:
        if self.boundary:
            return {"external": "→ [external]", "os": "→ [os]", "unresolved": "→ [unresolved]",
                    "gap": "→ [gap]", "declaration": "→ [declaration]"}[self.boundary]  # fmt: skip
        return "→" if self.observed_executions else "⇢"

    @property
    def best_grade(self) -> str | None:
        if not self.composed:
            return None
        return max(self.composed, key=lambda g: JoinStrength[g].value)

    def evidence_line(self) -> str:
        bits = []
        if self.observed_executions:
            bits.append(f"observed {len(self.observed_executions)} exec")
        for grade in sorted(self.composed, key=lambda g: JoinStrength[g].value, reverse=True):
            bits.append(f"composed {grade} x{self.composed[grade]}")
        if self.alternates:
            bits.append(f"+{self.alternates} same-shape")
        if self.ambiguous:
            bits.append("AMBIGUOUS")
        if self.rules:
            bits.append("rule=" + "/".join(sorted(self.rules)))
        bits.append(f"tests {len(self.tests)}")
        if self.probes:
            bits.append(f"probes {len(self.probes)}")
        return " · ".join(bits)


def _is_probe(execution_id: str, graph: BehavioralGraph) -> bool:
    if graph.corpus is not None and execution_id in graph.corpus.executions:
        return graph.corpus.executions[execution_id].stimulus is Stimulus.GENERATED_PROBE
    return "diffgenome_probe" in execution_id


def _symbol_kind(graph: BehavioralGraph, symbol: SymbolId) -> str:
    s = graph.symbols.get(symbol)
    return getattr(s, "kind", "callable") if s else "callable"


def project(graph: BehavioralGraph) -> dict[tuple[SymbolId, SymbolId], BehaviorEdge]:
    """Merge the evidence graph into behavioral edges between production symbols (and
    boundary leaves). Test-origin callers are dropped as nodes and kept as evidence."""
    out: dict[tuple[SymbolId, SymbolId], BehaviorEdge] = {}
    for e in graph.edges.values():
        if graph.origin(e.caller) is Origin.TEST:
            continue  # tests are evidence on the callee's incoming edges, not behavior
        boundary = _BOUNDARY.get(e.kind)
        if e.kind is EvidenceKind.INTERNAL_GAP and _symbol_kind(graph, e.callee) == "declaration":
            boundary = "declaration"
        key = (e.caller, e.callee)
        be = out.get(key)
        if be is None:
            be = out[key] = BehaviorEdge(e.caller, e.callee, boundary)
        elif be.boundary and not boundary:
            be.boundary = None  # a real continuation exists; the boundary was one seed's view
        if e.kind is EvidenceKind.OBSERVED:
            be.observed_executions.update(e.executions)
        if e.kind is EvidenceKind.COMPOSED:
            per_site: dict[Any, int] = defaultdict(int)
            for ev in e.evidence:
                if ev.join:
                    be.composed[ev.join.name] += 1
                be.alternates += len(ev.alternates)
                per_site[ev.site] += 1
            if any(n > 1 for n in per_site.values()):
                be.ambiguous = True
        be.rules.update(e.rules)
        for x in e.executions:
            (be.probes if _is_probe(x, graph) else be.tests).add(x)
    # incoming evidence from tests: attach to the callee's production edges as tests
    return out


def _tests_reaching(graph: BehavioralGraph, symbol: SymbolId) -> set[str]:
    return set(graph.tests_by_symbol.get(symbol, ()))


def render_behavior_map(
    graph: BehavioralGraph,
    seeds: list[SymbolId],
    up: int = 3,
    down: int = 4,
    declarations: set[SymbolId] | None = None,
) -> str:
    edges = project(graph)
    out_by: dict[SymbolId, list[BehaviorEdge]] = defaultdict(list)
    inc_by: dict[SymbolId, list[BehaviorEdge]] = defaultdict(list)
    for be in edges.values():
        out_by[be.caller].append(be)
        inc_by[be.callee].append(be)
    lines: list[str] = [
        "legend: → observed continuation  ⇢ composed continuation (grade)  "
        "[external] outside the repo  [unresolved] stand-in without a resolution  "
        "[gap] internal continuation nobody has executed  "
        "[declaration] construction/declaration with no in-repo executable body",
        "",
    ]
    seen: set[tuple[str, str]] = set()

    def entry_evidence(sym: SymbolId) -> str:
        tests = sorted(t.split("@")[0] for t in _tests_reaching(graph, sym))
        probes = [t for t in tests if "diffgenome_probe" in t]
        tests = [t for t in tests if "diffgenome_probe" not in t]
        parts = []
        if tests:
            parts.append(
                f"tests {len(tests)}: " + ", ".join(tests[:3]) + (" …" if len(tests) > 3 else "")
            )
        if probes:
            parts.append(f"probes {len(probes)}")
        return "; ".join(parts) if parts else "no execution"

    def down_tree(sym: SymbolId, prefix: str, depth: int, path: frozenset[str]) -> None:
        kids = sorted(out_by.get(sym, []), key=lambda b: (b.boundary or "", b.callee))
        for i, be in enumerate(kids):
            last = i == len(kids) - 1
            branch = "└" if last else "├"
            cont = prefix + ("   " if last else "│  ")
            repeat = (be.caller, be.callee) in seen
            seen.add((be.caller, be.callee))
            grade = f" ({be.best_grade})" if not be.observed_executions and be.best_grade else ""
            lines.append(
                f"{prefix}{branch}{be.glyph} {_short(be.callee)}{grade}"
                + ("  (see above)" if repeat else "")
            )
            if not repeat:
                lines.append(f"{cont}   evidence: {be.evidence_line()}")
            if be.boundary is None and not repeat and depth < down and be.callee not in path:
                down_tree(be.callee, cont, depth + 1, path | {be.callee})

    def up_tree(sym: SymbolId, prefix: str, depth: int, path: frozenset[str]) -> None:
        parents = sorted(
            (b for b in inc_by.get(sym, []) if b.boundary is None), key=lambda b: b.caller
        )
        for i, be in enumerate(parents):
            last = i == len(parents) - 1
            branch = "└" if last else "├"
            cont = prefix + ("   " if last else "│  ")
            is_entry = not any(b.boundary is None for b in inc_by.get(be.caller, []))
            tag = "  [entrypoint]" if is_entry else ""
            grade = f" ({be.best_grade})" if not be.observed_executions and be.best_grade else ""
            lines.append(f"{prefix}{branch}{_short(be.caller)}{tag} {be.glyph}{grade} this")
            lines.append(f"{cont}   evidence: {be.evidence_line()}")
            if is_entry:
                lines.append(f"{cont}   reached by: {entry_evidence(be.caller)}")
            if depth < up and be.caller not in path:
                up_tree(be.caller, cont, depth + 1, path | {be.caller})

    for seed in seeds:
        if declarations and seed in declarations:
            lines.append(f"# {_short(seed)}   [changed declaration: no executable body of its own]")
            lines.append("")
            continue
        outs = graph.outcomes_by_symbol.get(seed, Counter())
        outcome_text = dict(outs) or "never executed"
        reached = entry_evidence(seed)
        lines.append(
            f"# {_short(seed)}   [changed; outcomes={outcome_text}; reached by: {reached}]"
        )
        lines.append("## reaches the change")
        if any(b.boundary is None for b in inc_by.get(seed, [])):
            up_tree(seed, "  ", 1, frozenset({seed}))
        else:
            lines.append(
                "  (no production caller observed or composed; only tests/probes call it directly)"
            )
        lines.append("## continues from the change")
        if out_by.get(seed):
            down_tree(seed, "  ", 1, frozenset({seed}))
        else:
            lines.append("  (no continuation observed)")
        lines.append("")
    return "\n".join(lines) + "\n"


def slice_json(graph: BehavioralGraph, seeds: list[SymbolId], up: int, down: int) -> dict[str, Any]:
    nb = graph.neighborhood(seeds, up=up, down=down)
    projected = project(graph)
    keys = {(e.caller, e.callee) for _, e in nb.edges.values()}
    return {
        "seeds": seeds,
        "behavioral_edges": [
            {
                "caller": be.caller,
                "callee": be.callee,
                "kind": "observed"
                if be.observed_executions
                else ("composed" if be.composed else be.boundary),
                "boundary": be.boundary,
                "best_join": be.best_grade,
                "composed_shapes_by_grade": dict(be.composed),
                "same_shape_alternates": be.alternates,
                "ambiguous": be.ambiguous,
                "rules": sorted(be.rules),
                "tests": sorted(t.split("@")[0] for t in be.tests),
                "probes": sorted(t.split("@")[0] for t in be.probes),
            }
            for (c, k), be in sorted(projected.items())
            if (c, k) in keys and graph.origin(c) is not Origin.TEST
        ],
        "metrics": nb.metrics().as_dict(),
    }


def case_metrics(
    graph: BehavioralGraph,
    seeds: list[SymbolId],
    up: int,
    down: int,
    attempts: list[Any],
    before: BehavioralGraph | None = None,
) -> dict[str, Any]:
    """The compact table every case study reports. `ratio` is structural coverage only."""
    nb = graph.neighborhood(seeds, up=up, down=down)
    projected = project(graph)
    keys = {(e.caller, e.callee) for _, e in nb.edges.values()}
    bes = [
        be
        for (c, k), be in projected.items()
        if (c, k) in keys and graph.origin(c) is not Origin.TEST
    ]
    joins: Counter[str] = Counter()
    for be in bes:
        if be.best_grade and not be.observed_executions:
            joins[be.best_grade] += 1
    sites = {ev.site for _, e in nb.edges.values() for ev in e.evidence}
    rejected = sum(1 for a in graph.attempts if not a.accepted and a.site in sites)
    m = nb.metrics()

    def counts(g: BehavioralGraph) -> dict[str, int]:
        n = g.neighborhood(seeds, up=up, down=down).metrics()
        return {"strong_joins": n.strong_joins, "weak_joins": n.weak_joins, "gaps": n.internal_gaps,
                "observed": n.observed, "composed": n.composed}  # fmt: skip

    return {
        "changed_symbols": len(seeds),
        "behavioral_symbols_in_neighborhood": len(
            {s for be in bes for s in (be.caller, be.callee) if graph.origin(s) is Origin.REPO}
        ),
        "observed_edges": sum(1 for be in bes if be.observed_executions and be.boundary is None),
        "composed_edges": sum(1 for be in bes if not be.observed_executions and be.composed),
        "joins": {g: joins.get(g, 0) for g in ("SYMBOL", "ARG_SHAPE", "VALUE", "STATE")},
        "rejected_joins": rejected,
        "ambiguous_joins": sum(1 for be in bes if be.ambiguous),
        "internal_gaps": sum(1 for be in bes if be.boundary == "gap"),
        "declarations_no_in_repo_body": sum(1 for be in bes if be.boundary == "declaration"),
        "unresolved_boundaries": sum(1 for be in bes if be.boundary == "unresolved"),
        "external_boundaries": sum(1 for be in bes if be.boundary == "external"),
        "existing_tests_contributing": len({t for be in bes for t in be.tests}),
        "probe_derived_edges": sum(1 for be in bes if be.probes),
        "llm_calls": len(attempts),
        "accepted_probes": sum(1 for a in attempts if a.verdict == "accepted"),
        "rejected_probes": sum(1 for a in attempts if a.verdict != "accepted"),
        "before_after": {"before": counts(before), "after": counts(graph)}
        if before is not None
        else None,
        "structural_coverage_ratio_NOT_correctness": round(m.ratio, 3),
    }
