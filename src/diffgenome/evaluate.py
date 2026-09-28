"""Ground-truth evaluation: how right is a reconstructed graph when a whole execution exists?

Ground truth is a set of complete executions (e.g. in-process end-to-end tests) that the
reconstruction was NOT allowed to consume. Both sides are reduced to in-repo caller→callee
edges with callee outcomes; the reconstruction is the graph's downstream neighborhood of
the entry symbols. Precision asks whether claimed edges really happen; recall asks how much
of what happens was claimed. Provenance explains claims; this module judges them.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from diffgenome.graph import BehavioralGraph, GraphEdge
from diffgenome.model import CallNode, EvidenceKind, Execution, JoinStrength, Origin, SymbolId

Edge = tuple[SymbolId, SymbolId]


@dataclass
class GroundTruth:
    edges: set[Edge]
    outcomes: dict[Edge, set[str]]  # callee outcome kinds ("returned"/"raised") seen per edge
    symbols: set[SymbolId]
    executions: int


def ground_truth_from(
    executions: list[Execution], entries: list[SymbolId], origins: dict[SymbolId, Origin]
) -> GroundTruth:
    """In-repo edges reachable from the entry symbols inside the given executions."""
    edges: set[Edge] = set()
    outcomes: dict[Edge, set[str]] = defaultdict(set)
    symbols: set[SymbolId] = set()

    def under_entry(n: CallNode, by_id: dict[int, object]) -> bool:
        cur = n
        while cur.parent is not None:
            p = by_id[cur.parent]
            if not isinstance(p, CallNode):
                return False
            if p.symbol in entries:
                return True
            cur = p
        return False

    for ex in executions:
        by_id: dict[int, object] = {n.id: n for n in ex.nodes}
        for n in ex.nodes:
            if not isinstance(n, CallNode) or n.parent is None:
                continue
            p = by_id[n.parent]
            if not isinstance(p, CallNode):
                continue
            if origins.get(p.symbol) is not Origin.REPO or origins.get(n.symbol) is not Origin.REPO:
                continue
            if p.symbol in entries or under_entry(p, by_id):
                e = (p.symbol, n.symbol)
                edges.add(e)
                outcomes[e].add(n.outcome.split(":")[0])
                symbols.update(e)
    return GroundTruth(edges, dict(outcomes), symbols, len(executions))


@dataclass
class Evaluation:
    entries: list[SymbolId]
    gt_edges: int
    claimed_edges: int
    true_positive: int
    false_positive: int  # claimed, not in ground truth
    false_negative: int  # in ground truth, not claimed
    precision: float
    recall: float
    by_kind: dict[str, dict[str, int]]  # kind -> {claimed, true}
    by_join: dict[str, dict[str, int]]  # join -> {claimed, true}
    probe_derived: dict[str, int]  # {claimed, true}
    false_composed: list[Edge]
    missing: list[Edge]
    missing_explained: dict[str, list[Edge]]  # "gap"/"unresolved"/"absent" -> edges
    outcome_conflicts: list[tuple[Edge, str, str]]  # (edge, reconstructed outcomes, gt outcomes)
    alternates_total: int
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "entries": self.entries,
            "ground_truth_edges": self.gt_edges,
            "claimed_edges": self.claimed_edges,
            "true_positive": self.true_positive,
            "false_positive": self.false_positive,
            "false_negative": self.false_negative,
            "precision": round(self.precision, 3),
            "recall": round(self.recall, 3),
            "by_evidence_kind": self.by_kind,
            "by_join_strength": self.by_join,
            "probe_derived": self.probe_derived,
            "false_composed_continuations": [list(e) for e in self.false_composed],
            "missing_continuations": [list(e) for e in self.missing],
            "missing_explained": {
                k: [list(e) for e in v] for k, v in self.missing_explained.items()
            },
            "outcome_conflicts": [[list(e), r, g] for e, r, g in self.outcome_conflicts],
            "alternate_fragments_total": self.alternates_total,
            "notes": self.notes,
        }


def _reconstructed(
    graph: BehavioralGraph, entries: list[SymbolId], depth: int
) -> dict[Edge, GraphEdge]:
    """Downstream neighborhood restricted to in-repo symbol pairs, best edge per pair
    (OBSERVED wins over COMPOSED)."""
    nb = graph.neighborhood(entries, up=0, down=depth)
    best: dict[Edge, GraphEdge] = {}
    for _, e in nb.edges.values():
        if e.kind not in (EvidenceKind.OBSERVED, EvidenceKind.COMPOSED):
            continue
        if graph.origin(e.caller) is not Origin.REPO or graph.origin(e.callee) is not Origin.REPO:
            continue
        key = (e.caller, e.callee)
        if key not in best or (
            e.kind is EvidenceKind.OBSERVED and best[key].kind is not EvidenceKind.OBSERVED
        ):
            best[key] = e
    return best


def evaluate(
    graph: BehavioralGraph, gt: GroundTruth, entries: list[SymbolId], depth: int = 6
) -> Evaluation:
    claimed = _reconstructed(graph, entries, depth)
    tp = {e for e in claimed if e in gt.edges}
    fp = {e for e in claimed if e not in gt.edges}
    fn = {e for e in gt.edges if e not in claimed}
    by_kind: dict[str, Counter[str]] = defaultdict(Counter)
    by_join: dict[str, Counter[str]] = defaultdict(Counter)
    probe: Counter[str] = Counter()
    for e, ge in claimed.items():
        by_kind[ge.kind.value]["claimed"] += 1
        by_kind[ge.kind.value]["true"] += e in gt.edges
        if ge.kind is EvidenceKind.COMPOSED:
            j = ge.best_join.name if ge.best_join else "NONE"
            by_join[j]["claimed"] += 1
            by_join[j]["true"] += e in gt.edges
        if ge.probe_derived:
            probe["claimed"] += 1
            probe["true"] += e in gt.edges
    # where did the missing edges stop in the reconstruction?
    explained: dict[str, list[Edge]] = {"gap": [], "unresolved": [], "absent": []}
    for e in sorted(fn):
        kinds = {x.kind for x in graph.out.get(e[0], [])}
        if any(
            x.kind is EvidenceKind.INTERNAL_GAP and x.callee == e[1]
            for x in graph.out.get(e[0], [])
        ):
            explained["gap"].append(e)
        elif EvidenceKind.UNRESOLVED_BOUNDARY in kinds:
            explained["unresolved"].append(e)
        else:
            explained["absent"].append(e)
    conflicts: list[tuple[Edge, str, str]] = []
    for e in sorted(tp):
        recon = set(graph.outcomes_by_symbol.get(e[1], Counter()).keys())
        truth = gt.outcomes.get(e, set())
        if recon and truth and not (recon & truth):
            conflicts.append((e, ",".join(sorted(recon)), ",".join(sorted(truth))))
    alternates = sum(len(ev.alternates) for ge in claimed.values() for ev in ge.evidence)
    precision = len(tp) / len(claimed) if claimed else 0.0
    recall = len(tp) / len(gt.edges) if gt.edges else 0.0
    return Evaluation(
        entries,
        len(gt.edges),
        len(claimed),
        len(tp),
        len(fp),
        len(fn),
        precision,
        recall,
        {k: dict(v) for k, v in by_kind.items()},
        {k: dict(v) for k, v in by_join.items()},
        dict(probe),
        sorted(e for e in fp if claimed[e].kind is EvidenceKind.COMPOSED),
        sorted(fn),
        explained,
        conflicts,
        alternates,
    )


def _row(label: str, v: dict[str, int]) -> str:
    c, t = v.get("claimed", 0), v.get("true", 0)
    return f"| {label} | {c} | {t} | {t / c:.3f} |" if c else f"| {label} | 0 | 0 | - |"


@dataclass
class SeamGrade:
    grade: str
    seams: int
    consistent: int  # continuation claims no edge the whole execution did not take
    matching: int  # continuation is exactly the whole execution's continuation
    outcome_ok: int


def seam_precision(
    graph: BehavioralGraph, corpus_graph_edges: dict[str, set[Edge]], gt: GroundTruth
) -> list[SeamGrade]:
    """Join-lattice test at the seam level. For every accepted join whose target is on a
    ground-truth path: the borrowed fragment's first-level continuation (target → callees
    inside the fragment execution) is compared with the ground truth's continuation from
    that target. `corpus_graph_edges` maps execution id -> in-repo (caller, callee) edges
    observed in that execution."""
    per: dict[str, list[tuple[bool, bool, bool]]] = defaultdict(list)
    gt_out: dict[SymbolId, set[SymbolId]] = defaultdict(set)
    for a, b in gt.edges:
        gt_out[a].add(b)
    gt_targets = {b for _, b in gt.edges} | {a for a, _ in gt.edges}
    for att in graph.attempts:
        if not att.accepted or att.grade is None or att.target not in gt_targets:
            continue
        frag_edges = {
            e for e in corpus_graph_edges.get(att.fragment.execution, set()) if e[0] == att.target
        }
        claimed_next = {b for _, b in frag_edges}
        # Continuations the fragment reaches through its own seams count too: composed
        # edges out of the target whose evidence site lies in this fragment's execution.
        for ge in graph.out.get(att.target, []):
            if ge.kind is EvidenceKind.COMPOSED and any(
                ev.site.execution == att.fragment.execution for ev in ge.evidence
            ):
                claimed_next.add(ge.callee)
        truth_next = gt_out.get(att.target, set())
        consistent = claimed_next <= truth_next
        matching = claimed_next == truth_next
        frag_outcome = graph.outcomes_by_symbol.get(att.target, Counter())
        truth_outcomes = (
            set().union(
                *(
                    gt.outcomes.get((a, att.target), set())
                    for a in gt_out
                    if att.target in gt_out[a]
                )
            )
            if any(att.target in v for v in gt_out.values())
            else set()
        )
        outcome_ok = (not truth_outcomes) or bool(set(frag_outcome) & truth_outcomes)
        per[att.grade.name].append((consistent, matching, outcome_ok))
    out = []
    for grade in ("SYMBOL", "ARG_SHAPE", "VALUE", "STATE"):
        rows = per.get(grade, [])
        if rows:
            out.append(
                SeamGrade(
                    grade,
                    len(rows),
                    sum(r[0] for r in rows),
                    sum(r[1] for r in rows),
                    sum(r[2] for r in rows),
                )
            )
    return out


def render_seams(grades: list[SeamGrade]) -> str:
    lines = ["| join grade | seams | consistent | matching | outcome ok |", "|---|---|---|---|---|"]
    for g in grades:
        lines.append(
            f"| {g.grade} | {g.seams} | {g.consistent} ({g.consistent / g.seams:.2f}) "
            f"| {g.matching} ({g.matching / g.seams:.2f}) | {g.outcome_ok} |"
        )
    return "\n".join(lines) + "\n"


def render_evaluation(ev: Evaluation) -> str:
    lines = [
        "# Ground-truth evaluation",
        f"entries: {', '.join(s.split(':', 1)[1] for s in ev.entries)}",
        f"ground-truth in-repo edges: {ev.gt_edges}   claimed: {ev.claimed_edges}   "
        f"true: {ev.true_positive}   false: {ev.false_positive}   missing: {ev.false_negative}",
        f"edge precision: {ev.precision:.3f}   edge recall: {ev.recall:.3f}",
        "",
        "| evidence | claimed | true | precision |",
        "|---|---|---|---|",
    ]
    for k, v in sorted(ev.by_kind.items()):
        lines.append(_row(k, v))
    if ev.by_join:
        lines += [
            "",
            "| join strength (composed) | claimed | true | precision |",
            "|---|---|---|---|",
        ]
        for k, v in sorted(
            ev.by_join.items(),
            key=lambda kv: JoinStrength[kv[0]].value if kv[0] in JoinStrength.__members__ else 0,
        ):
            lines.append(_row(k, v))
    if ev.probe_derived:
        c, t = ev.probe_derived.get("claimed", 0), ev.probe_derived.get("true", 0)
        lines += [
            "",
            f"probe-derived edges: claimed {c}, true {t}, precision {t / c:.3f}" if c else "",
        ]
    if ev.false_composed:
        lines += ["", "false composed continuations:"] + [
            f"  {a.split(':', 1)[1]} ⇢ {b.split(':', 1)[1]}" for a, b in ev.false_composed
        ]
    if ev.missing:
        lines += ["", "missing continuations (ground truth not claimed):"]
        for k, es in ev.missing_explained.items():
            for a, b in es:
                lines.append(f"  [{k}] {a.split(':', 1)[1]} → {b.split(':', 1)[1]}")
    if ev.outcome_conflicts:
        lines += ["", "outcome conflicts (reconstructed vs ground truth):"] + [
            f"  {a.split(':', 1)[1]} → {b.split(':', 1)[1]}: {r} vs {g}"
            for (a, b), r, g in ev.outcome_conflicts
        ]
    lines += ["", f"alternate fragments carried on claimed edges: {ev.alternates_total}"]
    lines += [f"note: {n}" for n in ev.notes]
    return "\n".join(lines) + "\n"
