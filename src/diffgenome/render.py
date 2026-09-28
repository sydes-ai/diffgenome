"""Deterministic text rendering of a single `Execution` as a tree.

Glyphs: `→` observed call, `⊗` stand-in (with mechanism, claim and relation), `⚡` OS event,
`{tN}` a call on thread N. No composition happens here; see the composer for `⇢`.
"""

from __future__ import annotations

from collections import defaultdict

from diffgenome.model import CallNode, Execution, Node, OsEventNode, SubstitutionNode


def _label(node: Node) -> str:
    if isinstance(node, CallNode):
        thread = f" {{t{node.thread}}}" if node.thread else ""
        args = f"  ({node.args})" if node.args else ""
        return f"→ {node.symbol}{thread}{args}"
    if isinstance(node, SubstitutionNode):
        path = ".".join(node.path) or "<call>"
        claim = f" claims={node.claimed_target}" if node.claimed_target else " claims=∅"
        args = f"  ({node.args})" if node.args else ""
        return (
            f"⊗ {node.mechanism.value} .{path} substitute={node.substitute}"
            f"{claim} relation={node.relation}{args}"
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
