"""Static return-type resolution for `factory().member` stand-ins.

A stand-in whose path crosses a return value (``get_manager.().ensure_backend``) claims the
factory; what the factory returns was never observed. When the source declares the return
type unambiguously, the member on that type is the claim, entered with relation
``static-return-type`` so the resolver reports the rule and the evidence says so. Static
evidence, never observed; the composer still needs a real fragment to continue.
"""

from __future__ import annotations

import dataclasses

from diffgenome.model import Execution, Origin, SubstitutionNode, Symbol
from diffgenome.runtime import SymbolIndex


def apply_static_return_types(
    executions: list[Execution], index: SymbolIndex
) -> tuple[list[Execution], int]:
    resolved = 0
    out: list[Execution] = []
    cache: dict[str, str | None] = {}
    for ex in executions:
        symbols = dict((s.id, s) for s in ex.symbols)
        nodes = list(ex.nodes)
        changed = False
        for i, n in enumerate(nodes):
            if (
                not isinstance(n, SubstitutionNode)
                or n.claimed_target is None
                or "()" not in n.path
            ):
                continue
            # path: (factory, "()", member, ...) — only one hop through a return value
            try:
                k = n.path.index("()")
            except ValueError:
                continue
            if k + 1 >= len(n.path) or "()" in n.path[k + 1 :]:
                continue
            member = n.path[k + 1]
            if n.claimed_target not in cache:
                cache[n.claimed_target] = index.return_type_of(n.claimed_target)
            cls = cache[n.claimed_target]
            if cls is None:
                continue
            target = f"{cls}.{member}"
            d = index.find(target)
            if d is None:
                continue
            nodes[i] = dataclasses.replace(
                n,
                claimed_target=target,
                relation=f"static-return-type;{n.relation}",
                path=n.path[k + 1 :],
            )
            if target not in symbols:
                symbols[target] = Symbol(target, Origin.REPO, None)
            resolved += 1
            changed = True
        out.append(
            dataclasses.replace(
                ex, nodes=tuple(nodes), symbols=tuple(symbols[k] for k in sorted(symbols))
            )
            if changed
            else ex
        )
    return out, resolved
