"""The integration artifact: ``diffgenome-change/1``.

A bounded, deterministic, change-centred projection of the behavioral graph for consumers
such as Sydes. It is derived from the same graph as ``map.md`` and ``slice.json`` but
exposes no internal objects: symbols become nodes with stable ids and locations, evidence
becomes one edge per (caller, callee) with its evidence class, join grade, STATE status,
exit verdict and provenance, stand-in leaves become boundaries, and every join the composer
rejected on a seam in the neighborhood is listed with its reason. It is consumable without
the trace corpus. Nothing in it is a confidence score: the grades are the evidence.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

from diffgenome import __version__
from diffgenome.graph import BehavioralGraph, GraphEdge
from diffgenome.model import EvidenceKind, JoinStrength, Origin, Stimulus, SymbolId
from diffgenome.projection import case_metrics, project, render_behavior_map

FORMAT = "diffgenome-change/1"

# Evidence classes a consumer merges on. Observed and composed are runtime evidence of
# different standing; the rest are places where DiffGenome's knowledge stops.
EVIDENCE_OBSERVED = "observed"
EVIDENCE_COMPOSED = "composed"
EVIDENCE_EXTERNAL = "external"
EVIDENCE_UNRESOLVED = "unresolved"
EVIDENCE_GAP = "gap"
EVIDENCE_DECLARATION = "declaration"
EVIDENCE_OS = "os"


def _name(symbol: SymbolId) -> str:
    return symbol.split(":", 1)[1] if ":" in symbol else symbol


def _execution_label(execution_id: str) -> str:
    return execution_id.split("@")[0]


def _state_status(graph: BehavioralGraph, edge: GraphEdge) -> str:
    """STATE evidence status of a composed edge, from the join attempts behind it:
    ``matched`` (STATE grade reached), ``conflict-filtered`` (candidates were rejected on
    state; the accepted ones matched), ``unavailable`` (VALUE held but no state facts on a
    side), ``not_consulted`` (below VALUE, where STATE is never evaluated)."""
    if edge.kind is not EvidenceKind.COMPOSED:
        return "n/a"
    best = edge.best_join
    if best is JoinStrength.STATE:
        return "matched"
    sites = {ev.site for ev in edge.evidence}
    notes = [a.note for a in graph.attempts if a.site in sites and a.target == edge.callee]
    if best is JoinStrength.VALUE:
        if any("state unavailable" in n or "no common state" in n for n in notes):
            return "unavailable"
        return "unavailable"
    return "not_consulted"


def _exit_status(edge: GraphEdge) -> str | None:
    if edge.kind is not EvidenceKind.COMPOSED:
        return None
    verdicts = {ev.exit for ev in edge.evidence if ev.exit}
    if not verdicts:
        return None
    for v in ("same", "kind", "unknown"):
        if verdicts == {v}:
            return v
    return "mixed:" + "/".join(sorted(verdicts))


def build_change_artifact(
    graph: BehavioralGraph,
    seeds: list[SymbolId],
    *,
    up: int,
    down: int,
    change_spec: str,
    runtime: str,
    repo: str,
    revision: str | None,
    budget: dict[str, Any],
    probes: list[dict[str, Any]],
    notes: list[str],
    graph_before: BehavioralGraph | None = None,
) -> dict[str, Any]:
    """Build the artifact from a graph and the changed symbols. Deterministic for a
    given graph: every list is sorted, every set rendered as a sorted list."""
    nb = graph.neighborhood(seeds, up=up, down=down)
    projected = project(graph)
    keys = {(e.caller, e.callee) for _, e in nb.edges.values()}
    distance: dict[tuple[SymbolId, SymbolId], int] = {}
    for d, e in nb.edges.values():
        key = (e.caller, e.callee)
        distance[key] = min(d, distance.get(key, d))
    edges_by_key: dict[tuple[SymbolId, SymbolId], list[GraphEdge]] = defaultdict(list)
    for _, e in nb.edges.values():
        edges_by_key[(e.caller, e.callee)].append(e)

    # ---- nodes: every production symbol touched by the neighborhood, plus the seeds
    node_ids: set[SymbolId] = set(seeds)
    for (c, k), be in projected.items():
        if (c, k) in keys and graph.origin(c) is not Origin.TEST:
            node_ids.add(c)
            if be.boundary is None:
                node_ids.add(k)
    nodes = []
    for sid in sorted(node_ids):
        sym = graph.symbols.get(sid)
        nodes.append(
            {
                "id": sid,
                "name": _name(sid),
                "file": sym.location.path if sym and sym.location else None,
                "line": sym.location.line if sym and sym.location else None,
                "kind": sym.kind if sym else "callable",
                "origin": (sym.origin.value if sym else Origin.UNKNOWN.value),
                "changed": sid in seeds,
                "executed_by": len(graph.tests_by_symbol.get(sid, ())),
            }
        )

    # ---- edges and boundaries
    edges: list[dict[str, Any]] = []
    boundaries: list[dict[str, Any]] = []
    for (c, k), be in sorted(projected.items()):
        if (c, k) not in keys or graph.origin(c) is Origin.TEST:
            continue
        raw = edges_by_key[(c, k)]
        if be.boundary is not None:
            rules = sorted({r for e in raw for r in e.rules})
            boundaries.append(
                {
                    "caller": c,
                    "target": k,
                    "target_name": _name(k),
                    "kind": be.boundary,
                    "rules": rules,
                    "distance": distance[(c, k)],
                    "executions": sorted(_execution_label(x) for x in be.tests | be.probes),
                }
            )
            continue
        composed = [e for e in raw if e.kind is EvidenceKind.COMPOSED]
        observed = be.observed_executions
        evidence = EVIDENCE_OBSERVED if observed else EVIDENCE_COMPOSED
        best = be.best_grade
        state = "n/a"
        exit_ = None
        if composed:
            state = _state_status(graph, composed[0])
            exit_ = _exit_status(composed[0])
        edges.append(
            {
                "caller": c,
                "callee": k,
                "evidence": evidence,
                "distance": distance[(c, k)],
                "join": best if evidence == EVIDENCE_COMPOSED else None,
                "also_composed_at": best if evidence == EVIDENCE_OBSERVED and best else None,
                "state": state if evidence == EVIDENCE_COMPOSED else "n/a",
                "exit": exit_,
                "probe_derived": bool(be.probes) and not be.tests,
                "executions": sorted(_execution_label(x) for x in be.tests),
                "probes": sorted(_execution_label(x) for x in be.probes),
                "composed_shapes_by_grade": dict(sorted(be.composed.items())),
                "same_shape_alternates": be.alternates,
                "ambiguous": be.ambiguous,
                "rules": sorted(be.rules),
            }
        )

    # ---- executions contributing
    exec_ids = {
        x
        for be in projected.values()
        for x in (be.tests | be.probes)
        if (be.caller, be.callee) in keys
    }
    executions = []
    for x in sorted(exec_ids):
        stim = "generated_probe"
        if graph.corpus is not None and x in graph.corpus.executions:
            stim = graph.corpus.executions[x].stimulus.value
        elif "diffgenome_probe" not in x:
            stim = Stimulus.EXISTING_TEST.value
        executions.append({"id": _execution_label(x), "stimulus": stim})

    # ---- ambiguous seams and rejected candidates on neighborhood seams
    sites = {ev.site for _, e in nb.edges.values() for ev in e.evidence}
    site_caller: dict[Any, SymbolId] = {}
    for _, e in nb.edges.values():
        for ev in e.evidence:
            site_caller.setdefault(ev.site, e.caller)
    rejected: list[dict[str, Any]] = []
    by_seam: dict[tuple[SymbolId, SymbolId], Counter[str]] = defaultdict(Counter)
    accepted_by_seam: dict[tuple[SymbolId, SymbolId], set[str]] = defaultdict(set)
    for a in graph.attempts:
        if a.site not in sites:
            continue
        seam = (site_caller.get(a.site, "?"), a.target)
        if a.accepted:
            accepted_by_seam[seam].add(a.fragment.execution)
            continue
        reason = a.note.split(";")[0].strip()
        by_seam[seam][reason] += 1
        rejected.append(
            {
                "caller": seam[0],
                "target": a.target,
                "candidate": _execution_label(a.fragment.execution),
                "reason": reason,
            }
        )
    rejected.sort(key=lambda r: (r["caller"], r["target"], r["candidate"], r["reason"]))
    ambiguous_seams = [
        {
            "caller": c,
            "target": k,
            "accepted_candidates": len(accepted_by_seam.get((c, k), ())),
            "rejected_candidates": sum(by_seam.get((c, k), Counter()).values()),
            "rejection_reasons": dict(sorted(by_seam.get((c, k), Counter()).items())),
        }
        for (c, k) in sorted(set(by_seam) | {s for s, v in accepted_by_seam.items() if len(v) > 1})
    ]

    metrics = case_metrics(graph, seeds, up, down, [], graph_before)
    facts = {
        k: v
        for k, v in metrics.items()
        if k
        in (
            "observed_edges", "composed_edges", "joins", "rejected_joins", "ambiguous_joins",
            "internal_gaps", "declarations_no_in_repo_body", "unresolved_boundaries",
            "external_boundaries", "existing_tests_contributing", "probe_derived_edges",
            "structural_coverage_ratio_NOT_correctness",
        )
    }  # fmt: skip
    return {
        "format": FORMAT,
        "generated_by": f"diffgenome {__version__}",
        "generated_at": datetime.now(tz=UTC).isoformat(timespec="seconds"),
        "repository": {"root": repo, "runtime": runtime, "revision": revision or "checkout"},
        "change": {
            "spec": change_spec,
            "symbols": sorted(seeds),
            "symbols_never_executed": sorted(s for s in seeds if s not in graph.tests_by_symbol),
        },
        "neighborhood": {"up": up, "down": down, "symbols": len(node_ids)},
        "budget": budget,
        "nodes": nodes,
        "edges": edges,
        "boundaries": boundaries,
        "executions": executions,
        "ambiguous_seams": ambiguous_seams,
        "rejected_candidates": rejected[:200],
        "probes": probes,
        "facts": facts,
        "invariants": [
            "observed edges were seen in one execution; composed edges are reconstructed "
            "across a stand-in seam and are never presented as observed",
            "join grades are evidence classes, not a probability: "
            "SYMBOL < ARG_SHAPE < VALUE < STATE",
            "structural_coverage_ratio_NOT_correctness counts symbol pairs with evidence; "
            "it says nothing about whether the behavior is right",
            "boundaries are where DiffGenome's knowledge stops: external stays substituted, "
            "unresolved was not attributed, gap has no executing fragment",
        ],
        "notes": list(notes),
    }


def render_behavioral_map(graph: BehavioralGraph, seeds: list[SymbolId], up: int, down: int) -> str:
    return render_behavior_map(graph, seeds, up=up, down=down)


def dumps(artifact: dict[str, Any]) -> str:
    return json.dumps(artifact, indent=1, sort_keys=False) + "\n"
