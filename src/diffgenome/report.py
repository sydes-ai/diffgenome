"""Deterministic text and JSON reports for a change-centred run."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from typing import Any

from diffgenome.change import ChangeSet
from diffgenome.graph import BehavioralGraph, GraphEdge, Metrics, Neighborhood
from diffgenome.model import EvidenceKind
from diffgenome.probe import ProbeAttempt

_GLYPH = {
    EvidenceKind.OBSERVED: "→",
    EvidenceKind.OBSERVED_SAMPLED: "→?",
    EvidenceKind.COMPOSED: "⇢",
    EvidenceKind.INTERNAL_GAP: "→ [gap]",
    EvidenceKind.EXTERNAL_BOUNDARY: "→ [external]",
    EvidenceKind.OS_BOUNDARY: "→ [os]",
    EvidenceKind.UNRESOLVED_BOUNDARY: "→ [unresolved]",
    EvidenceKind.STATIC: "--→",
}


def _short(symbol: str) -> str:
    return symbol.split(":", 1)[-1]


def _edge_line(d: int, e: GraphEdge) -> str:
    tail = f"  tests={len(e.executions)}"
    if e.kind is EvidenceKind.COMPOSED and e.best_join:
        tail += f"  join={e.best_join.name.lower()}"
    if e.rules:
        tail += f"  rule={'/'.join(sorted(e.rules))}"
    if e.probe_derived:
        tail += "  probe-derived"
    return f"  d{d}  {_short(e.caller)} {_GLYPH[e.kind]} {_short(e.callee)}{tail}"


def render_neighborhood(nb: Neighborhood, graph: BehavioralGraph, title: str) -> str:
    lines = [f"## {title}", ""]
    seeds = set(nb.seeds)
    up = [(d, e) for d, e in nb.edges.values() if e.callee in seeds or e.caller not in seeds]
    down = [(d, e) for d, e in nb.edges.values()]
    # Partition by direction relative to the seeds using the walk that found them: an
    # edge whose callee is a seed or whose callee leads to a seed is upstream.
    traversable = (EvidenceKind.OBSERVED, EvidenceKind.COMPOSED)
    upstream = sorted(
        ((d, e) for d, e in up if e.kind in traversable and _leads_to(e, seeds, graph)),
        key=lambda x: (x[0], x[1].caller, x[1].callee),
    )
    downstream = sorted(
        ((d, e) for d, e in down if (d, e) not in upstream),
        key=lambda x: (x[0], x[1].caller, x[1].callee),
    )
    lines.append("### Upstream (what reaches the change)")
    lines.extend(_edge_line(d, e) for d, e in upstream[:60] or [])
    if not upstream:
        lines.append("  (nothing observed reaches the changed symbols)")
    lines.append("")
    lines.append("### Downstream (what continues from the change)")
    lines.extend(_edge_line(d, e) for d, e in downstream[:120])
    lines.append("")
    lines.append(f"### Tests establishing these paths ({len(nb.tests)})")
    lines.extend(f"  {t.split('@')[0]}" for t in sorted(nb.tests)[:40])
    if len(nb.tests) > 40:
        lines.append(f"  ... {len(nb.tests) - 40} more")
    return "\n".join(lines)


def _leads_to(e: GraphEdge, seeds: set[str], graph: BehavioralGraph, depth: int = 4) -> bool:
    frontier: list[str] = [e.callee]
    seen: set[str] = set()
    while frontier and depth:
        nxt: list[str] = []
        for s in frontier:
            if s in seeds:
                return True
            if s in seen:
                continue
            seen.add(s)
            nxt.extend(
                x.callee
                for x in graph.out.get(s, [])
                if x.kind in (EvidenceKind.OBSERVED, EvidenceKind.COMPOSED)
            )
        frontier, depth = nxt, depth - 1
    return any(s in seeds for s in frontier)


def render_metrics(before: Metrics, after: Metrics | None) -> str:
    rows = [
        ("observed edges", "observed"), ("composed edges", "composed"),
        ("strong joins (VALUE+)", "strong_joins"), ("weak joins", "weak_joins"),
        ("internal gaps", "internal_gaps"), ("unresolved boundaries", "unresolved_boundaries"),
        ("external boundaries", "external_boundaries"), ("os boundaries", "os_boundaries"),
        ("unsound attempts", "unsound_attempts"), ("probe-derived edges", "probe_derived_edges"),
        ("symbols", "symbols"), ("tests", "tests"),
    ]  # fmt: skip
    out = ["| metric | before | after |", "|---|---|---|"]
    for label, attr in rows:
        b = getattr(before, attr)
        a = getattr(after, attr) if after else "-"
        out.append(f"| {label} | {b} | {a} |")
    b = f"{before.reconstructed}/{before.denominator} = {before.ratio:.3f}"
    a = f"{after.reconstructed}/{after.denominator} = {after.ratio:.3f}" if after else "-"
    out.append(f"| reconstructed / provisional denominator | {b} | {a} |")
    return "\n".join(out)


def render_report(
    change: ChangeSet,
    graph_before: BehavioralGraph,
    nb_before: Neighborhood,
    attempts: list[ProbeAttempt],
    graph_after: BehavioralGraph | None,
    nb_after: Neighborhood | None,
    notes: list[str],
) -> str:
    m_before = nb_before.metrics()
    m_after = nb_after.metrics() if nb_after else None
    lines = ["# diffgenome behavioral impact report", ""]
    lines.append(f"Change: {change.description}")
    lines.append(f"Changed symbols ({len(change.symbols)}):")
    for s in change.symbols:
        n = len(graph_before.tests_by_symbol.get(s, ()))
        lines.append(
            f"  {_short(s)}  executed by {n} test(s)" + ("" if n else "  ← no existing execution")
        )
    if change.unmapped_paths:
        lines.append(
            f"Changed files with no mapped code symbol: {', '.join(change.unmapped_paths)}"
        )
    lines.append("")
    lines.append(
        render_neighborhood(nb_before, graph_before, "Behavioral neighborhood (before probes)")
    )
    lines.append("")
    lines.append("## Where knowledge stops (before probes)")
    for kind in (
        EvidenceKind.INTERNAL_GAP,
        EvidenceKind.UNRESOLVED_BOUNDARY,
        EvidenceKind.EXTERNAL_BOUNDARY,
    ):
        es = nb_before.edges_of(kind)
        if es:
            lines.append(f"### {kind.value} ({len(es)})")
            lines.extend(_edge_line(d, e) for d, e in es[:30])
    weak = [(d, e) for d, e in nb_before.edges_of(EvidenceKind.COMPOSED) if not e.strong]
    if weak:
        lines.append(f"### weak joins ({len(weak)})")
        lines.extend(_edge_line(d, e) for d, e in weak)
    lines.append("")
    lines.append("## Generated probes")
    if not attempts:
        lines.append("  (none attempted)")
    for a in attempts:
        o = a.objective
        lines.append(
            f"- objective: {o.kind} {_short(o.target)} (from {_short(o.caller)}, d{o.distance})"
        )
        lines.append(
            f"  attempt {a.attempt}: {a.verdict}" + (f"  model={a.draft.model}" if a.draft else "")
        )
        for r in a.reasons[:8]:
            lines.append(f"    - {r}")
        if a.learned:
            lines.append(f"  learned {len(a.learned)} observed edge(s):")
            lines.extend(f"    + {item}" for item in a.learned[:15])
    lines.append("")
    lines.append("## Before vs after")
    lines.append(render_metrics(m_before, m_after))
    lines.append("")
    lines.append(
        "Denominator is provisional: observed + composed edges + internal gaps + unresolved"
    )
    lines.append(
        "stand-ins inside the neighborhood, i.e. the seams we know about. It excludes behavior"
    )
    lines.append(
        "no execution has come near, and external/OS boundaries, which are terminal by design."
    )
    if nb_after and graph_after:
        lines.append("")
        lines.append("## Remaining after probes")
        for kind in (EvidenceKind.INTERNAL_GAP, EvidenceKind.UNRESOLVED_BOUNDARY):
            es = nb_after.edges_of(kind)
            lines.append(f"### {kind.value} ({len(es)})")
            lines.extend(_edge_line(d, e) for d, e in es[:30])
        weak_after = [(d, e) for d, e in nb_after.edges_of(EvidenceKind.COMPOSED) if not e.strong]
        lines.append(f"### weak joins ({len(weak_after)})")
        lines.extend(_edge_line(d, e) for d, e in weak_after)
    if notes:
        lines.append("")
        lines.append("## Notes")
        lines.extend(f"- {n}" for n in notes)
    return "\n".join(lines) + "\n"


def report_json(
    change: ChangeSet,
    nb_before: Neighborhood,
    attempts: list[ProbeAttempt],
    nb_after: Neighborhood | None,
    notes: list[str],
) -> str:
    def edges(nb: Neighborhood) -> list[dict[str, Any]]:
        return [
            {
                "distance": d,
                "caller": e.caller,
                "callee": e.callee,
                "kind": e.kind.value,
                "best_join": e.best_join.name if e.best_join else None,
                "rules": sorted(e.rules),
                "executions": sorted(e.executions),
                "probe_derived": e.probe_derived,
                "evidence": [
                    {
                        "kind": ev.kind.value,
                        "site": asdict(ev.site),
                        "fragment": asdict(ev.fragment) if ev.fragment else None,
                        "alternates": [asdict(a) for a in ev.alternates],
                        "join": ev.join.name if ev.join else None,
                        "rule": ev.rule,
                    }
                    for ev in e.evidence
                ],
            }
            for d, e in sorted(nb.edges.values(), key=lambda x: (x[0], x[1].caller, x[1].callee))
        ]

    doc: dict[str, Any] = {
        "change": {
            "description": change.description,
            "symbols": change.symbols,
            "unmapped_paths": change.unmapped_paths,
        },
        "before": {
            "metrics": nb_before.metrics().as_dict(),
            "edges": edges(nb_before),
            "tests": sorted(nb_before.tests),
        },
        "probes": [
            {
                "objective": {
                    "kind": a.objective.kind,
                    "target": a.objective.target,
                    "caller": a.objective.caller,
                    "distance": a.objective.distance,
                },
                "attempt": a.attempt,
                "model": a.draft.model if a.draft else None,
                "verdict": a.verdict,
                "reasons": a.reasons,
                "learned": a.learned,
                "executions": [e.id for e in a.executions],
            }
            for a in attempts
        ],
        "after": {
            "metrics": nb_after.metrics().as_dict(),
            "edges": edges(nb_after),
            "tests": sorted(nb_after.tests),
        }
        if nb_after
        else None,
        "notes": notes,
    }
    return json.dumps(doc, indent=1) + "\n"


# --------------------------------------------------------------------------- map slice


def _annotate(e: GraphEdge, graph: BehavioralGraph) -> str:
    bits = [e.kind.value]
    if e.kind is EvidenceKind.COMPOSED and e.best_join:
        bits.append(f"join={e.best_join.name.lower()}")
        alt = sum(len(ev.alternates) for ev in e.evidence)
        if alt:
            bits.append(f"+{alt} same-shape")
    if e.rules:
        bits.append("rule=" + "/".join(sorted(e.rules)))
    outs = graph.outcomes_by_symbol.get(e.callee)
    if outs and e.kind in (EvidenceKind.OBSERVED, EvidenceKind.COMPOSED):
        bits.append("outcomes=" + ",".join(f"{k}:{v}" for k, v in sorted(outs.items())))
    bits.append(f"tests={len(e.executions)}")
    if e.probe_derived:
        bits.append("probe-derived")
    return "  [" + " ".join(bits) + "]"


def render_map_slice(graph: BehavioralGraph, seeds: list[str], up: int = 3, down: int = 4) -> str:
    """Human-readable slice of the repo-level graph around the seeds: callers above,
    continuations below, every edge with its evidence. Deterministic. Cycles and repeats
    are cut with `(see above)`."""
    lines: list[str] = []
    seen_down: set[tuple[str, str, EvidenceKind]] = set()

    def down_tree(sym: str, prefix: str, depth: int, path: frozenset[str]) -> None:
        kids = sorted(graph.out.get(sym, []), key=lambda e: (e.kind.value, e.callee))
        for i, e in enumerate(kids):
            last = i == len(kids) - 1
            branch = "└" if last else "├"
            key = (e.caller, e.callee, e.kind)
            repeat = key in seen_down
            seen_down.add(key)
            label = f"{_GLYPH[e.kind]} {_short(e.callee)}"
            lines.append(
                f"{prefix}{branch}{label}{_annotate(e, graph)}"
                + ("  (see above)" if repeat else "")
            )
            traversable = e.kind in (EvidenceKind.OBSERVED, EvidenceKind.COMPOSED)
            if traversable and not repeat and depth < down and e.callee not in path:
                down_tree(
                    e.callee, prefix + ("   " if last else "│  "), depth + 1, path | {e.callee}
                )

    def up_tree(sym: str, prefix: str, depth: int, path: frozenset[str]) -> None:
        parents = sorted(
            (
                e
                for e in graph.inc.get(sym, [])
                if e.kind in (EvidenceKind.OBSERVED, EvidenceKind.COMPOSED)
            ),
            key=lambda e: (e.kind.value, e.caller),
        )
        for i, e in enumerate(parents):
            last = i == len(parents) - 1
            branch = "└" if last else "├"
            lines.append(
                f"{prefix}{branch}{_short(e.caller)} {_GLYPH[e.kind]}{_annotate(e, graph)}"
            )
            if depth < up and e.caller not in path:
                up_tree(e.caller, prefix + ("   " if last else "│  "), depth + 1, path | {e.caller})

    for seed in seeds:
        n_tests = len(graph.tests_by_symbol.get(seed, ()))
        outs = graph.outcomes_by_symbol.get(seed, Counter())
        origin = graph.origin(seed).value
        lines.append(
            f"# {_short(seed)}  [origin={origin} executed_by={n_tests} outcomes={dict(outs)}]"
        )
        lines.append("## upstream (who reaches it; each line is `caller →/⇢ this`)")
        if graph.inc.get(seed):
            up_tree(seed, "  ", 1, frozenset({seed}))
        else:
            lines.append("  (no observed or composed caller)")
        lines.append("## downstream (what continues from it)")
        if graph.out.get(seed):
            down_tree(seed, "  ", 1, frozenset({seed}))
        else:
            lines.append("  (no observed continuation)")
        lines.append("")
    legend = (
        "legend: → observed  ⇢ composed (join=symbol|arg_shape|value)  → [gap] internal gap  "
        "→ [unresolved] stand-in not resolved  → [external] outside the repository  "
        "→ [os] kernel boundary\n"
    )
    return legend + "\n" + "\n".join(lines)
