"""Python front end: lower functions to the neutral IR of `diffgenome.dependence`.

Only what the conservative analysis needs. Anything else becomes an `opaque` statement
with a reason, never a silently dropped one.
"""

from __future__ import annotations

import ast
from typing import Any

from diffgenome.sites import site_id


def _path(e: ast.expr) -> str | None:
    """Dotted access path of a Name/Attribute chain, else None."""
    if isinstance(e, ast.Name):
        return e.id
    if isinstance(e, ast.Attribute):
        base = _path(e.value)
        return f"{base}.{e.attr}" if base else None
    return None


class _Expr(ast.NodeVisitor):
    """Collect maximal read paths and calls of one expression."""

    def __init__(self) -> None:
        self.uses: list[str] = []
        self.calls: list[dict[str, Any]] = []

    def visit_Attribute(self, node: ast.Attribute) -> None:
        p = _path(node)
        if p:
            self.uses.append(p)
        else:
            self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        self.uses.append(node.id)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute):
            recv = _path(func.value)
            if recv:
                self.uses.append(recv)
            else:
                self.visit(func.value)
        args = []
        for a in [*node.args, *(k.value for k in node.keywords)]:
            sub = _Expr()
            sub.visit(a)
            args.append(sub.uses or ["?"])
            self.uses.extend(sub.uses)
            self.calls.extend(sub.calls)
        self.calls.append({"callee": ast.unparse(func), "args": args, "line": node.lineno})

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return  # a nested function body is not this function's dataflow

    def _comprehension(
        self, node: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp
    ) -> None:
        """Comprehension targets are bound by the comprehension, not read from the
        enclosing scope: their reads are dropped; the iterables' reads remain."""
        bound = {
            n.id for g in node.generators for n in ast.walk(g.target) if isinstance(n, ast.Name)
        }
        inner = _Expr()
        for child in ast.iter_child_nodes(node):
            inner.visit(child)
        self.uses.extend(u for u in inner.uses if u.split(".", 1)[0] not in bound)
        for c in inner.calls:  # an argument that is a comprehension target is an element
            c["args"] = [
                [u for u in a if u.split(".", 1)[0] not in bound] or ["?"] for a in c["args"]
            ]
            self.calls.append(c)

    visit_ListComp = _comprehension
    visit_SetComp = _comprehension
    visit_DictComp = _comprehension
    visit_GeneratorExp = _comprehension


def _expr(e: ast.expr | None) -> tuple[list[str], list[dict[str, Any]]]:
    if e is None:
        return [], []
    v = _Expr()
    v.visit(e)
    return sorted(set(v.uses)), v.calls


def _targets(t: ast.expr) -> tuple[list[str], list[str]]:
    """(local defs, stored paths) of an assignment target."""
    if isinstance(t, ast.Name):
        return [t.id], []
    if isinstance(t, ast.Tuple | ast.List):
        defs: list[str] = []
        stores: list[str] = []
        for e in t.elts:
            d, s = _targets(e)
            defs += d
            stores += s
        return defs, stores
    if isinstance(t, ast.Attribute):
        return [], [_path(t) or "?"]
    if isinstance(t, ast.Subscript):
        return [], [(_path(t.value) or "?") + "[]"]
    if isinstance(t, ast.Starred):
        return _targets(t.value)
    return [], ["?"]


class _Lower:
    def __init__(self, rel_path: str) -> None:
        self.rel = rel_path

    def block(self, stmts: list[ast.stmt]) -> list[dict[str, Any]]:
        out = []
        for s in stmts:
            out.extend(self.stmt(s))
        return out

    def stmt(self, s: ast.stmt) -> list[dict[str, Any]]:
        line = s.lineno
        if isinstance(s, ast.Assign | ast.AnnAssign | ast.AugAssign):
            targets = s.targets if isinstance(s, ast.Assign) else [s.target]
            value = s.value
            uses, calls = _expr(value)
            defs: list[str] = []
            stores: list[str] = []
            for t in targets:
                d, st = _targets(t)
                defs += d
                stores += st
            if isinstance(s, ast.AugAssign):
                uses = sorted(set(uses) | set(defs) | {p for p in stores if p != "?"})
            unwrapped = value.value if isinstance(value, ast.Await) else value
            return [
                {
                    "k": "assign", "line": line, "defs": defs, "stores": stores, "uses": uses,
                    "calls": calls, "value_is_call": isinstance(unwrapped, ast.Call),
                }
            ]  # fmt: skip
        if isinstance(s, ast.Expr):
            uses, calls = _expr(s.value)
            return [{"k": "expr", "line": line, "uses": uses, "calls": calls}]
        if isinstance(s, ast.If):
            t = s.test
            span = (
                t.lineno,
                t.col_offset + 1,
                t.end_lineno or t.lineno,
                (t.end_col_offset or 0) + 1,
            )
            uses, calls = _expr(t)
            return [
                {
                    "k": "if", "line": line, "site": site_id(self.rel, span), "span": list(span),
                    "pred": ast.unparse(t), "uses": uses, "calls": calls,
                    "then": self.block(s.body), "else": self.block(s.orelse),
                }
            ]  # fmt: skip
        if isinstance(s, ast.Return | ast.Raise):
            e = s.value if isinstance(s, ast.Return) else s.exc
            uses, calls = _expr(e)
            return [
                {
                    "k": "return" if isinstance(s, ast.Return) else "raise",
                    "line": line,
                    "uses": uses,
                    "calls": calls,
                }
            ]
        if isinstance(s, ast.For | ast.AsyncFor | ast.While):
            it = s.iter if isinstance(s, ast.For | ast.AsyncFor) else s.test
            uses, calls = _expr(it)
            defs = _targets(s.target)[0] if isinstance(s, ast.For | ast.AsyncFor) else []
            return [
                {"k": "loop", "line": line, "uses": uses, "calls": calls, "defs": defs,
                 "body": self.block(s.body + s.orelse)}
            ]  # fmt: skip
        if isinstance(s, ast.With | ast.AsyncWith):
            w_uses: list[str] = []
            w_calls: list[dict[str, Any]] = []
            w_defs: list[str] = []
            for item in s.items:
                u, c = _expr(item.context_expr)
                w_uses += u
                w_calls += c
                if item.optional_vars is not None:
                    w_defs += _targets(item.optional_vars)[0]
            return [
                {
                    "k": "with",
                    "line": line,
                    "uses": w_uses,
                    "calls": w_calls,
                    "defs": w_defs,
                    "body": self.block(s.body),
                }
            ]
        if isinstance(s, ast.Try | ast.TryStar):
            handlers = [self.block(h.body) for h in s.handlers]
            return [
                {"k": "try", "line": line, "body": self.block(s.body + s.orelse),
                 "handlers": handlers, "final": self.block(s.finalbody)}
            ]  # fmt: skip
        if isinstance(s, ast.Break | ast.Continue):
            return [{"k": "break", "line": line}]
        if isinstance(s, ast.Pass | ast.Global | ast.Nonlocal | ast.Import | ast.ImportFrom):
            return []
        if isinstance(s, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            # A nested definition binds a local name; its body is lowered as a function of
            # its own (`lower_functions`), not as this function's dataflow. Decorators and
            # default values are evaluated here.
            d_uses: list[str] = []
            d_calls: list[dict[str, Any]] = []
            evaluated = list(s.decorator_list)
            if not isinstance(s, ast.ClassDef):
                evaluated += [*s.args.defaults, *(d for d in s.args.kw_defaults if d)]
            for e in evaluated:
                u, c = _expr(e)
                d_uses += u
                d_calls += c
            return [
                {"k": "assign", "line": line, "defs": [s.name], "stores": [],
                 "uses": sorted(set(d_uses)), "calls": d_calls, "value_is_call": False}
            ]  # fmt: skip
        if isinstance(s, ast.Assert):
            uses, calls = _expr(s.test)
            return [{"k": "expr", "line": line, "uses": uses, "calls": calls}]
        if isinstance(s, ast.Match):
            return [
                {
                    "k": "opaque",
                    "line": line,
                    "reason": "match",
                    "blocks": [self.block(c.body) for c in s.cases],
                }
            ]
        return [{"k": "opaque", "line": line, "reason": type(s).__name__}]


def _params(n: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    a = n.args
    params = [x.arg for x in [*a.posonlyargs, *a.args, *a.kwonlyargs]]
    return params + [x.arg for x in (a.vararg, a.kwarg) if x is not None]


def _bound_names(n: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Names bound in a function's own scope: parameters, assignment/loop/with/except
    targets, imports and nested definitions. Nested function bodies are not entered."""
    names = set(_params(n))

    def walk(node: ast.AST) -> None:
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                names.add(ch.name)
                continue  # its body is another scope
            if isinstance(ch, ast.Lambda):
                continue
            if isinstance(ch, ast.Name) and isinstance(ch.ctx, ast.Store):
                names.add(ch.id)
            elif isinstance(ch, ast.ExceptHandler) and ch.name:
                names.add(ch.name)
            elif isinstance(ch, ast.alias):
                names.add((ch.asname or ch.name).split(".")[0])
            walk(ch)

    for st in n.body:
        if isinstance(st, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(st.name)
        else:
            walk(st)
    return names


def lower_functions(
    source: str, rel_path: str, module: str, qualnames: list[str] | None = None
) -> list[dict[str, Any]]:
    """Lower every function (or the given qualnames) of one Python file, including nested
    functions. Symbols use the collector's naming: `py:<module>.<qualname>`, where a nested
    function's qualname is `<outer>.<locals>.<name>` (Python's `co_qualname`). A nested
    function's `closure` lists the names bound by its enclosing functions; reads of them
    resolve to `closure:<name>` rather than `global:<name>`."""
    tree = ast.parse(source)
    out: list[dict[str, Any]] = []

    def visit(body: list[ast.stmt], prefix: str, closure: set[str]) -> None:
        for n in body:
            if isinstance(n, ast.ClassDef):
                # a class body is not an enclosing scope for its methods
                visit(n.body, f"{prefix}{n.name}.", closure)
            elif isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef):
                q = f"{prefix}{n.name}"
                if qualnames is None or q in qualnames:
                    fn: dict[str, Any] = {
                        "symbol": f"py:{module}.{q}", "file": rel_path, "params": _params(n),
                        "body": _Lower(rel_path).block(n.body),
                    }  # fmt: skip
                    if closure:
                        fn["closure"] = sorted(closure - set(_params(n)))
                    out.append(fn)
                visit(n.body, f"{q}.<locals>.", closure | _bound_names(n))
            elif isinstance(
                n,
                ast.If
                | ast.For
                | ast.AsyncFor
                | ast.While
                | ast.With
                | ast.AsyncWith
                | ast.Try
                | ast.TryStar,
            ):
                # definitions nested in compound statements (module-level `if TYPE_CHECKING:`
                # or inside a function body) belong to the same scope
                for blk in _blocks(n):
                    visit(blk, prefix, closure)

    visit(tree.body, "", set())
    return out


def _blocks(n: ast.stmt) -> list[list[ast.stmt]]:
    out: list[list[ast.stmt]] = []
    for attr in ("body", "orelse", "finalbody"):
        blk = getattr(n, attr, None)
        if blk:
            out.append(blk)
    for h in getattr(n, "handlers", []) or []:
        out.append(h.body)
    return out
