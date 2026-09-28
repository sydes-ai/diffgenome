"""Ambiguity report: seams with more than one materially different continuation, how the
join lattice ranked the candidates, and which candidates were rejected and why. Derived
from the evidence graph's composed edges and its full list of join attempts."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from diffgenome.graph import BehavioralGraph
from diffgenome.model import EvidenceKind, JoinStrength, NodeRef


def _short(s: str) -> str:
    return s.split(":", 1)[-1]


def ambiguous_seams(graph: BehavioralGraph) -> list[dict[str, Any]]:
    """One entry per (site, target) seam whose accepted continuations span more than one
    fragment shape, or that has rejected/unsound candidates. Candidates carry grade,
    note, acceptance and outcome compatibility from the join attempts."""
    attempts_by: dict[tuple[NodeRef, str], list[Any]] = defaultdict(list)
    for a in graph.attempts:
        attempts_by[(a.site, a.target)].append(a)
    shapes_by: dict[tuple[NodeRef, str], int] = defaultdict(int)
    alternates_by: dict[tuple[NodeRef, str], int] = defaultdict(int)
    callers: dict[tuple[NodeRef, str], str] = {}
    for e in graph.edges.values():
        if e.kind is not EvidenceKind.COMPOSED:
            continue
        for ev in e.evidence:
            key = (ev.site, e.callee)
            shapes_by[key] += 1
            alternates_by[key] += len(ev.alternates)
            callers[key] = e.caller
    out: list[dict[str, Any]] = []
    for key, atts in attempts_by.items():
        accepted = [a for a in atts if a.accepted]
        rejected = [a for a in atts if not a.accepted]
        distinct_shapes = shapes_by.get(key, 0)
        if distinct_shapes <= 1 and not rejected:
            continue
        grades: dict[str, int] = defaultdict(int)
        for a in accepted:
            grades[a.grade.name if a.grade else "unsound"] += 1
        out.append(
            {
                "caller": callers.get(key, "?"),
                "site": {"execution": key[0].execution, "node": key[0].node},
                "target": key[1],
                "distinct_shapes_accepted": distinct_shapes,
                "same_shape_alternates": alternates_by.get(key, 0),
                "accepted_by_grade": dict(grades),
                "best_grade": _best_grade([a.grade for a in accepted if a.grade]),
                "rejected": [
                    {
                        "fragment": a.fragment.execution.split("@")[0],
                        "grade": a.grade.name if a.grade else "unsound",
                        "note": a.note,
                        "result_compatible": a.result_compatible,
                    }
                    for a in rejected
                ],
                "accepted": [
                    {
                        "fragment": a.fragment.execution.split("@")[0],
                        "grade": a.grade.name if a.grade else "unsound",
                        "note": a.note,
                        "result_compatible": a.result_compatible,
                    }
                    for a in accepted
                ],
            }
        )
    out.sort(key=lambda x: (-x["distinct_shapes_accepted"], x["target"]))
    return out


def _best_grade(grades: list[JoinStrength]) -> str | None:
    return max(grades, key=lambda g: g.value).name if grades else None


def render_ambiguity(graph: BehavioralGraph, limit: int = 40) -> str:
    seams = ambiguous_seams(graph)
    lines = [
        "# Ambiguous and rejected compositions",
        f"seams with >1 accepted continuation shape or with rejected candidates: {len(seams)}",
        "",
    ]
    for s in seams[:limit]:
        lines.append(
            f"## {_short(s['caller'])} ⇢ {_short(s['target'])}   "
            f"[{s['distinct_shapes_accepted']} shapes accepted, "
            f"+{s['same_shape_alternates']} same-shape; best={s['best_grade']}; "
            f"by grade={s['accepted_by_grade']}]"
        )
        for a in s["accepted"][:6]:
            rc = (
                ""
                if a["result_compatible"] is None
                else f"  result_compatible={a['result_compatible']}"
            )
            lines.append(f"  accepted {a['grade']:9s} {a['fragment']}  {a['note']}{rc}")
        if len(s["accepted"]) > 6:
            lines.append(f"  … {len(s['accepted']) - 6} more accepted")
        for a in s["rejected"][:6]:
            lines.append(f"  REJECTED {a['grade']:9s} {a['fragment']}  {a['note']}")
        if len(s["rejected"]) > 6:
            lines.append(f"  … {len(s['rejected']) - 6} more rejected")
        lines.append("")
    grade_counts: dict[str, int] = defaultdict(int)
    for a in graph.attempts:
        grade_counts[
            (a.grade.name if a.grade else "unsound") + ("" if a.accepted else " rejected")
        ] += 1
    lines.append("## all join attempts by grade")
    for k in sorted(grade_counts, key=lambda k: (-grade_counts[k], k)):
        lines.append(f"  {k}: {grade_counts[k]}")
    return "\n".join(lines) + "\n"


_ = JoinStrength  # re-exported for callers that key by grade
