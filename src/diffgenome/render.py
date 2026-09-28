"""Deterministic text rendering of a single `Execution` as a tree.

Glyphs: `→` observed call, `⊗` stand-in (with mechanism, claim and relation), `⚡` OS event,
`{tN}` a call on thread N. No composition happens here; see the composer for `⇢`.
"""

from __future__ import annotations

from collections import defaultdict

from diffgenome.compose import Branch, Composition
from diffgenome.model import (
    ArgShapes,
    CallNode,
    Edge,
    EvidenceKind,
    Execution,
    Node,
    OsEventNode,
    SubstitutionNode,
)


def fmt_outcome(outcome: str) -> str:
    return "" if outcome == "returned" else f"  !{outcome}"


def fmt_args(args: ArgShapes) -> str:
    return f"  ({', '.join(f'{n}={s}' for n, s in args)})" if args else ""


def _label(node: Node) -> str:
    if isinstance(node, CallNode):
        thread = f" {{t{node.thread}}}" if node.thread else ""
        return f"→ {node.symbol}{thread}{fmt_args(node.args)}{fmt_outcome(node.outcome)}"
    if isinstance(node, SubstitutionNode):
        path = ".".join(node.path) or "<call>"
        claim = f" claims={node.claimed_target}" if node.claimed_target else " claims=∅"
        args = fmt_args(node.args)
        return (
            f"⊗ {node.mechanism.value} .{path} substitute={node.substitute}"
            f"{claim} relation={node.relation}{args}{fmt_outcome(node.outcome)}"
        )
    if isinstance(node, OsEventNode):
        return f"⚡ {node.kind.value} {node.target} → {node.outcome}"
    raise TypeError(node)


def render_execution(execution: Execution) -> str:
    children: dict[int, list[Node]] = defaultdict(list)
    for node in execution.nodes:
        if node.parent is not None:
            children[node.parent].append(node)
    collectors = ", ".join(f"{c.name}: {c.fidelity.value}" for c in execution.collectors)
    lines = [f"{execution.stimulus_ref}  [{collectors}]  {execution.outcome}"]

    def walk(node_id: int, prefix: str) -> None:
        kids = children[node_id]
        for i, kid in enumerate(kids):
            last = i == len(kids) - 1
            lines.append(f"{prefix}{'└' if last else '├'}{_label(kid)}")
            walk(kid.id, prefix + ("   " if last else "│  "))

    walk(0, "")
    return "\n".join(lines) + "\n"


_GLYPH = {
    EvidenceKind.OBSERVED: "→ ",
    EvidenceKind.OBSERVED_SAMPLED: "→?",
    EvidenceKind.COMPOSED: "⇢ ",
    EvidenceKind.STATIC: "--→",
    EvidenceKind.INTERNAL_GAP: "→ [gap]",
    EvidenceKind.EXTERNAL_BOUNDARY: "→ [external]",
    EvidenceKind.OS_BOUNDARY: "→ [os]",
    EvidenceKind.UNRESOLVED_BOUNDARY: "→ [unresolved]",
}


def render_composition(composition: Composition) -> str:
    """Composed tree. Every non-observed edge prints its rule; composed edges print their
    join grade and the execution the continuation was borrowed from."""
    lines = [f"{composition.seed}  seed={composition.root}"]

    def label(edge: Edge) -> str:
        ev = edge.evidence
        tail = ""
        if ev.rule:
            tail += f"  rule={ev.rule}"
        if ev.kind is EvidenceKind.COMPOSED and ev.fragment and ev.join:
            tail += f"  join={ev.join.name.lower()}  fragment={ev.fragment.execution}"
        if ev.probe_derived:
            tail += "  probe-derived"
        return f"{_GLYPH[ev.kind]} {edge.callee}{tail}"

    def walk(branches: list[Branch], prefix: str) -> None:
        for i, b in enumerate(branches):
            last = i == len(branches) - 1
            lines.append(f"{prefix}{'└' if last else '├'}{label(b.edge)}")
            walk(b.children, prefix + ("   " if last else "│  "))

    walk(composition.branches, "")
    if composition.gaps:
        lines.append("gaps:")
        lines.extend(
            f"  {g.kind}: {g.target}  at {g.site.execution}#{g.site.node}" for g in composition.gaps
        )
    rejected = [a for a in composition.attempts if not a.accepted]
    if rejected:
        lines.append("rejected joins:")
        lines.extend(
            f"  {a.target}  {a.grade.name.lower() if a.grade else 'unsound'}"
            f"  fragment={a.fragment.execution}  {a.note}"
            for a in rejected
        )
    return "\n".join(lines) + "\n"
