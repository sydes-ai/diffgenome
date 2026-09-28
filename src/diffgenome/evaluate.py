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
from itertools import pairwise

from diffgenome.graph import BehavioralGraph, GraphEdge
from diffgenome.model import (
    CallNode,
    EvidenceKind,
    Execution,
    JoinStrength,
    NodeRef,
    Origin,
    SymbolId,
)

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


# --------------------------------------------------------------------------- path level


def execution_paths(
    executions: list[Execution], entry: SymbolId, origins: dict[SymbolId, Origin]
) -> set[tuple[str, ...]]:
    """Pre-order sequences of in-repo (symbol, outcome-kind) under `entry` in whole executions.
    One sequence per occurrence of the entry."""
    paths: set[tuple[str, ...]] = set()
    for ex in executions:
        kids: dict[int, list[CallNode]] = defaultdict(list)
        for n in ex.nodes:
            if isinstance(n, CallNode) and n.parent is not None:
                kids[n.parent].append(n)
        for n in ex.nodes:
            if isinstance(n, CallNode) and n.symbol == entry:
                seq: list[str] = []
                _walk_preorder(n, kids, origins, seq)
                paths.add(tuple(seq))
    return paths


def _walk_preorder(
    node: CallNode, kids: dict[int, list[CallNode]], origins: dict[SymbolId, Origin], seq: list[str]
) -> None:
    if origins.get(node.symbol) is Origin.REPO:
        seq.append(f"{node.symbol}:{node.outcome.split(':')[0]}")
    for k in kids.get(node.id, []):
        _walk_preorder(k, kids, origins, seq)


def composed_paths(graph: BehavioralGraph, entry: SymbolId, depth: int = 8) -> set[tuple[str, ...]]:
    """Pre-order sequences the reconstruction implies from `entry`: one per combination of
    composed alternatives, following the composition trees of every execution that ran the
    entry (observed children in order, composed seams expanded to each accepted fragment)."""
    corpus = graph.corpus
    if corpus is None:
        return set()
    from diffgenome.compose import Branch, compose
    from diffgenome.model import EvidenceKind as EK

    out: set[tuple[str, ...]] = set()
    for ex_id in graph.tests_by_symbol.get(entry, ()):
        comp = compose(corpus, ex_id, use_state=graph.use_state)

        def expand(branches: list[Branch], d: int) -> list[list[str]]:
            # siblings concatenate; alternatives for one caller→callee pair multiply
            seqs: list[list[str]] = [[]]
            groups: dict[tuple[str, str, int], list[Branch]] = defaultdict(list)
            order: list[tuple[str, str, int]] = []
            for i, b in enumerate(branches):
                # composed alternatives for one seam share a site; observed siblings are
                # distinct calls even when they have the same callee
                ev = b.edge.evidence
                key = (b.edge.caller, b.edge.callee, ev.site.node if ev.kind is EK.COMPOSED else -i)
                if key not in groups:
                    order.append(key)
                groups[key].append(b)
            for key in order:
                alts = groups[key]
                alt_seqs: list[list[str]] = []
                for b in alts:
                    kind = b.edge.evidence.kind
                    if (
                        kind in (EK.OBSERVED, EK.COMPOSED)
                        and graph.origin(b.edge.callee) is Origin.REPO
                    ):
                        outcome = "?"
                        ref = b.edge.evidence.fragment or b.edge.evidence.site
                        node = corpus.executions[ref.execution].nodes[ref.node]
                        if isinstance(node, CallNode):
                            outcome = node.outcome.split(":")[0]
                        head = [f"{b.edge.callee}:{outcome}"]
                        tails = expand(b.children, d + 1) if d < depth else [[]]
                        alt_seqs.extend(head + t for t in tails)
                    else:
                        alt_seqs.append([])
                # dedupe alternatives
                uniq = []
                for a in alt_seqs:
                    if a not in uniq:
                        uniq.append(a)
                seqs = [s_ + a for s_ in seqs for a in uniq]
            return seqs

        # find the entry branch(es) in the seed tree
        stack = list(comp.branches)
        while stack:
            b = stack.pop()
            if b.edge.callee == entry:
                site = b.edge.evidence.site
                node = corpus.executions[site.execution].nodes[site.node]
                outcome = node.outcome.split(":")[0] if isinstance(node, CallNode) else "?"
                for tail in expand(b.children, 1):
                    out.add(tuple([f"{entry}:{outcome}", *tail]))
            stack.extend(b.children)
    return out


@dataclass
class PathEvaluation:
    entry: SymbolId
    truth_paths: int
    claimed_paths: int
    matched: int  # claimed sequences that equal a ground-truth sequence
    extra: list[tuple[str, ...]]  # claimed, not in truth (wrong composition or untaken alternative)
    missed: list[tuple[str, ...]]  # truth, not claimed
    outcome_mismatches: (
        int  # extra sequences whose symbol order matches a truth sequence but outcomes differ
    )


def evaluate_paths(
    graph: BehavioralGraph,
    gt_runs: list[Execution],
    entry: SymbolId,
    origins: dict[SymbolId, Origin],
) -> PathEvaluation:
    truth = execution_paths(gt_runs, entry, origins)
    claimed = composed_paths(graph, entry)
    matched = {p for p in claimed if p in truth}
    extra = sorted(p for p in claimed if p not in truth)
    missed = sorted(p for p in truth if p not in claimed)
    order_only = {tuple(x.rsplit(":", 1)[0] for x in p) for p in truth}
    outcome_mm = sum(1 for p in extra if tuple(x.rsplit(":", 1)[0] for x in p) in order_only)
    return PathEvaluation(entry, len(truth), len(claimed), len(matched), extra, missed, outcome_mm)


def path_scores(pe: PathEvaluation) -> tuple[float, float]:
    precision = pe.matched / pe.claimed_paths if pe.claimed_paths else 0.0
    recall = pe.matched / pe.truth_paths if pe.truth_paths else 0.0
    return precision, recall


def render_paths(pe: PathEvaluation) -> str:
    def fmt(p: tuple[str, ...]) -> str:
        return " → ".join(
            x.split(":", 1)[1].split(":")[0].split(".")[-1] + ("!" if x.endswith(":raised") else "")
            for x in p
        )

    pp, pr = path_scores(pe)
    lines = [
        f"### path-level: {pe.entry.split(':', 1)[1]}",
        f"ground-truth sequences {pe.truth_paths}, claimed {pe.claimed_paths}, "
        f"matched {pe.matched}, extra {len(pe.extra)} (of which outcome-only mismatches "
        f"{pe.outcome_mismatches}), missed {len(pe.missed)}",
        f"path precision {pp:.3f}   path recall {pr:.3f}",
    ]
    for p in pe.extra[:8]:
        lines.append(f"  extra:  {fmt(p)}")
    for p in pe.missed[:8]:
        lines.append(f"  missed: {fmt(p)}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- join matrix


@dataclass
class MatrixRow:
    caller: SymbolId
    target: SymbolId
    fragment: str
    symbol: str  # "✓" reached, "✗" failed at this rung, "·" not evaluated
    arg_shape: str
    value: str
    state: str  # ✓ | ✗ (conflict) | n/a (no facts to compare) | · (not evaluated / disabled)
    exit: str  # same | kind | unknown | conflict
    truth: bool | None  # the fragment's continuation equals a ground-truth execution's
    accepted: bool
    note: str


def join_matrix(
    graph: BehavioralGraph,
    corpus_graph_edges: dict[str, set[Edge]],
    gt: GroundTruth,
    truth_per_exec: list[set[Edge]] | None = None,
) -> list[MatrixRow]:
    """One row per (seam, candidate fragment) for seams whose target is on a ground-truth
    path: which rungs the candidate reached, its exit verdict, whether its first-level
    continuation is one some ground-truth execution actually took from that target, and
    whether the composer accepted it. Rung marks are derived from the grade and the
    rejection note, so a rejected candidate still shows how far it got."""
    gt_out: dict[SymbolId, set[SymbolId]] = defaultdict(set)
    for a, b in gt.edges:
        gt_out[a].add(b)
    truth_sets: dict[SymbolId, list[set[SymbolId]]] = defaultdict(list)
    for edges in truth_per_exec or []:
        outs: dict[SymbolId, set[SymbolId]] = defaultdict(set)
        for a, b in edges:
            outs[a].add(b)
        for a, nxt in outs.items():
            truth_sets[a].append(nxt)
    targets = {b for _, b in gt.edges} | {a for a, _ in gt.edges}
    callers: dict[tuple[NodeRef, str], str] = {}
    for e in graph.edges.values():
        for ev in e.evidence:
            callers[(ev.site, e.callee)] = e.caller
    rows: list[MatrixRow] = []
    for att in graph.attempts:
        if att.target not in targets:
            continue
        frag_next = {
            b for a, b in corpus_graph_edges.get(att.fragment.execution, set()) if a == att.target
        }
        truth: bool | None
        if truth_sets.get(att.target):
            truth = frag_next in truth_sets[att.target]
        elif att.target in gt_out:
            truth = frag_next == gt_out[att.target]
        else:
            truth = None
        g = att.grade.value if att.grade else 0
        note = att.note
        exit_ = att.exit if att.exit else "conflict"
        sym = arg = val = state = "·"
        if att.grade is not None:
            sym = "✓"
            arg = "✓" if g >= 2 else "✗"
            val = "✓" if g >= 3 else ("·" if g < 2 else "✗")
            if g >= 4:
                state = "✓"
            elif g == 3:
                state = "n/a" if ("state unavailable" in note or "no common" in note) else "·"
        elif "state conflict" in note:
            sym = arg = val = "✓"
            state = "✗"
        elif "type conflict" in note:
            sym, arg = "✓", "✗"
        elif "exit conflict" in note:
            sym = "✓"
        rows.append(
            MatrixRow(
                callers.get((att.site, att.target), "?"),
                att.target,
                att.fragment.execution.split("::")[-1].split("@")[0],
                sym,
                arg,
                val,
                state,
                exit_,
                truth,
                att.accepted,
                note,
            )
        )
    rows.sort(key=lambda r: (r.caller, r.target, r.fragment))
    return rows


def render_matrix(rows: list[MatrixRow]) -> str:
    def yn(b: bool) -> str:
        return "✓" if b else "✗"

    lines = [
        "| seam | candidate fragment | SYMBOL | ARG_SHAPE | VALUE | STATE | EXIT "
        "| truth | accepted |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        seam = f"{r.caller.split('.')[-1]} ⇢ {r.target.split('.')[-1]}"
        truth = "?" if r.truth is None else yn(r.truth)
        lines.append(
            f"| {seam} | {r.fragment} | {r.symbol} | {r.arg_shape} | {r.value} "
            f"| {r.state} | {r.exit} | {truth} | {yn(r.accepted)} |"
        )
    return "\n".join(lines) + "\n"


def explain_paths(pe: PathEvaluation, graph: BehavioralGraph) -> list[str]:
    """For each extra path, which seam and join grade admitted it; for each missed path,
    what evidence was absent."""
    out: list[str] = []
    for p in pe.extra:
        # the first symbol whose edge from its predecessor is composed is the admitting seam
        found = False
        for a, b in pairwise(p):
            ca, cb = a.rsplit(":", 1)[0], b.rsplit(":", 1)[0]
            e = graph.edges.get((ca, cb, EvidenceKind.COMPOSED))
            if e is not None:
                grades = sorted({ev.join.name for ev in e.evidence if ev.join})
                out.append(
                    f"extra {_fmt_path(p)}: admitted at seam {ca.split('.')[-1]} ⇢ "
                    f"{cb.split('.')[-1]} with join {'/'.join(grades)}"
                )
                found = True
                break
        if not found:
            out.append(
                f"extra {_fmt_path(p)}: all edges observed in some execution "
                "(a real path the ground truth did not take)"
            )
    for p in pe.missed:
        syms = {x.rsplit(":", 1)[0] for x in p}
        reasons: list[str] = []
        # a rejected candidate whose target lies on the path: cite the rejection
        seen: set[str] = set()
        for att in graph.attempts:
            if att.accepted or att.target not in syms:
                continue
            if graph.corpus is not None:
                # only candidates that actually contain the missed continuation
                frag_syms = {
                    n.symbol
                    for n in graph.corpus.executions[att.fragment.execution].nodes
                    if isinstance(n, CallNode)
                }
                after = list(p)[[x.rsplit(":", 1)[0] for x in p].index(att.target) + 1 :]
                if not all(x.rsplit(":", 1)[0] in frag_syms for x in after):
                    continue
            head = att.note.split(";")[0]
            key = f"{att.target}|{head}"
            if key in seen:
                continue
            seen.add(key)
            reasons.append(
                f"candidate {att.fragment.execution.split('::')[-1].split('@')[0]} at "
                f"⇢ {att.target.split('.')[-1]} rejected: {head}"
            )
        unreached = [
            x.split(".")[-1] for x in syms if x not in graph.inc and x != p[0].rsplit(":", 1)[0]
        ]
        if unreached:
            reasons.append("no evidence reaches " + ", ".join(sorted(unreached)))
        if not reasons:
            reasons.append("the seed corpus never observed the entry under this exit path")
        out.append(f"missed {_fmt_path(p)}: " + "; ".join(reasons))
    return out


def _fmt_path(p: tuple[str, ...]) -> str:
    return " → ".join(
        x.rsplit(":", 1)[0].split(".")[-1] + ("!" if x.endswith(":raised") else "") for x in p
    )
