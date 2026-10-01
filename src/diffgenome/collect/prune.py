"""Keep only the part of a test's call tree that bears on the change.

A single test can record millions of calls (Baserow: one row-history test wrote a 162 MB
trace), and everything downstream (graph, neighborhood, report, runtime evidence) pays for
every node. Given the changed symbols (the focus), a trace keeps:

- the stimulus root;
- every call to a focus symbol, and all its ancestors back to the root (the observed chain:
  callers, entry points, edges);
- what happens directly below a focus call: descendants up to `depth` levels, and always the
  first non-wrapper level (stand-ins, raises and callees are attributed through closures,
  lambdas and decorator wrappers);
- branch observations made inside kept calls.

Everything else is unrelated to the change for the runtime-evidence contract and is dropped.
Node ids are renumbered densely, in their original order, since consumers index nodes by id.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import replace
from typing import Any

from diffgenome.model import BranchObs, CallNode

DEFAULT_DEPTH = 2
_WRAPPER_MARKERS = ("<locals>", "<lambda>", "<anon>")


def _is_wrapper(node: Any) -> bool:
    return isinstance(node, CallNode) and any(m in node.symbol for m in _WRAPPER_MARKERS)


def prune_to_focus(
    nodes: Sequence[Any],
    branches: Iterable[BranchObs],
    focus: set[str],
    depth: int = DEFAULT_DEPTH,
) -> tuple[tuple[Any, ...], tuple[BranchObs, ...], int]:
    """(kept nodes, kept branches, number of nodes dropped)."""
    by_id = {n.id: n for n in nodes}
    children: dict[int, list[Any]] = defaultdict(list)
    keep: set[int] = set()
    for n in nodes:
        if n.parent is None:
            keep.add(n.id)
        else:
            children[n.parent].append(n)

    for n in nodes:
        if not (isinstance(n, CallNode) and n.symbol in focus):
            continue
        p: int | None = n.id
        while p is not None and p not in keep:  # the chain back to the root
            keep.add(p)
            p = by_id[p].parent
        keep.add(n.id)
        # below the focus call: `depth` levels, and through wrappers to the first real level
        stack = [(c, 1, True) for c in children.get(n.id, ())]
        while stack:
            c, d, via_wrappers = stack.pop()
            if d > depth and not via_wrappers:
                continue
            keep.add(c.id)
            wrapper = _is_wrapper(c)
            for g in children.get(c.id, ()):
                stack.append((g, d + 1, via_wrappers and wrapper))

    if len(keep) == len(by_id):
        return tuple(nodes), tuple(branches), 0
    new_id = {old: i for i, old in enumerate(sorted(keep))}
    kept_nodes = tuple(
        replace(
            n, id=new_id[n.id], parent=None if n.parent is None else new_id[n.parent]
        )
        for n in sorted((by_id[i] for i in keep), key=lambda n: n.id)
    )
    kept_branches = tuple(replace(b, node=new_id[b.node]) for b in branches if b.node in new_id)
    return kept_nodes, kept_branches, len(by_id) - len(keep)
