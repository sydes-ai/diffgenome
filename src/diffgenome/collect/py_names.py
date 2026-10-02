"""Names for Python definitions that share a qualified name.

Python gives the same `__qualname__` to every definition of a name in one scope: a property's
getter and setter (translate #6595/#6596: `pounit.target`; pdm #3886:
`Project.environment`), an `@overload` stub and its implementation, a function defined in
both branches of an `if`. Their code objects differ only by their first line. The tracer
and the static index must name them alike, so the rule lives here, computed from source:

- `@overload` stubs are not definitions (never executed): they are left out;
- the first definition (by line) keeps the qualified name;
- every later one is `qualname@<first line>`, where the first line is that of its first
  decorator, matching `code.co_firstlineno`.
"""

from __future__ import annotations

import ast

_COMPOUND = (
    ast.If, ast.Try, ast.TryStar, ast.With, ast.AsyncWith, ast.For, ast.AsyncFor, ast.While,
)  # fmt: skip


def is_overload(node: ast.AST) -> bool:
    """A `@typing.overload` stub: a type declaration replaced at runtime, never executed.
    It is not a definition of its own (falcon #2731 has 24 of them next to 11 functions)."""
    return isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and any(
        (isinstance(d, ast.Name) and d.id == "overload")
        or (isinstance(d, ast.Attribute) and d.attr == "overload")
        for d in node.decorator_list
    )


def first_line(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> int:
    return min([node.lineno, *(d.lineno for d in node.decorator_list)])


def walk_definitions(
    body: list[ast.stmt], scope: list[str]
) -> list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef, list[str]]]:
    """(qualname, node, scope) for every function and class definition, in source order,
    including those inside if/try/with/for/while/match blocks (same scope as the block)."""
    out: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef, list[str]]] = []
    for node in body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            out.append((".".join([*scope, node.name]), node, scope))
            out += walk_definitions(node.body, [*scope, node.name, "<locals>"])
        elif isinstance(node, ast.ClassDef):
            out.append((".".join([*scope, node.name]), node, scope))
            out += walk_definitions(node.body, [*scope, node.name])
        elif isinstance(node, _COMPOUND):
            for field in ("body", "orelse", "finalbody"):
                out += walk_definitions(getattr(node, field, None) or [], scope)
            for handler in getattr(node, "handlers", None) or []:
                out += walk_definitions(handler.body, scope)
        elif isinstance(node, ast.Match):
            for case in node.cases:
                out += walk_definitions(case.body, scope)
    return out


def redefined(tree: ast.Module) -> dict[str, list[int]]:
    """qualname -> sorted first lines, for qualnames defined more than once in the file."""
    lines: dict[str, list[int]] = {}
    for qual, node, _scope in walk_definitions(tree.body, []):
        if not is_overload(node):  # the implementation keeps the plain name
            lines.setdefault(qual, []).append(first_line(node))
    return {q: sorted(ls) for q, ls in lines.items() if len(ls) > 1}


def disambiguate(qualname: str, line: int, redefinitions: dict[str, list[int]]) -> str:
    lines = redefinitions.get(qualname)
    if not lines or line == lines[0] or line not in lines:
        return qualname
    return f"{qualname}@{line}"
