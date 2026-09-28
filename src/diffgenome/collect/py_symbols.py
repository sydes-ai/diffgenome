"""Python source adapter: static symbol index over a repository's files.

Maps source lines to `SymbolId`s with the *same naming scheme the tracer uses* (module from
path under the roots, dotted qualname), extracts a symbol's source text for probe context,
and lists test files that import a module. Language-specific by nature; it lives beside
the collector and is used through `diffgenome.change.SymbolIndex`.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from diffgenome.model import SymbolId

_EXCLUDED = {"site-packages", "dist-packages", "node_modules", "__pycache__"}


@dataclass(frozen=True)
class Definition:
    symbol: SymbolId
    path: str  # repository-relative
    start: int
    end: int
    kind: str  # "function" | "class"
    is_async: bool = False


class PythonSymbolIndex:
    def __init__(self, repo_root: Path, source_roots: list[Path], test_roots: list[Path]) -> None:
        self.repo_root = repo_root.resolve()
        self.source_roots = [p.resolve() for p in source_roots]
        self.test_roots = [p.resolve() for p in test_roots]
        self._defs: dict[str, list[Definition]] = {}

    # ------------------------------------------------------------------ naming (mirrors tracer)

    def module_for(self, path: Path) -> str | None:
        path = path.resolve()
        if any(p in _EXCLUDED or p.startswith(".") for p in path.parts[1:]):
            return None
        for roots, is_test in ((self.test_roots, True), (self.source_roots, False)):
            for root in roots:
                try:
                    rel = path.relative_to(root)
                except ValueError:
                    continue
                parts = list(rel.with_suffix("").parts)
                if parts and parts[-1] == "__init__":
                    parts.pop()
                prefix = root.relative_to(self.repo_root).parts if is_test else ()
                return ".".join((*prefix, *parts))
        return None

    # ------------------------------------------------------------------ definitions

    def definitions(self, rel_path: str) -> list[Definition]:
        if rel_path in self._defs:
            return self._defs[rel_path]
        file = self.repo_root / rel_path
        module = self.module_for(file)
        out: list[Definition] = []
        if module is not None and file.suffix == ".py":
            try:
                tree = ast.parse(file.read_text(encoding="utf-8"))
            except (SyntaxError, OSError, UnicodeDecodeError):
                tree = None
            if tree is not None:
                self._collect(tree.body, module, [], rel_path, out)
        self._defs[rel_path] = out
        return out

    def _collect(
        self, body: list[ast.stmt], module: str, scope: list[str], rel: str, out: list[Definition]
    ) -> None:
        for node in body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                qual = ".".join([*scope, node.name])
                out.append(
                    Definition(
                        f"py:{module}.{qual}",
                        rel,
                        node.lineno,
                        node.end_lineno or node.lineno,
                        "function",
                        isinstance(node, ast.AsyncFunctionDef),
                    )
                )
                self._collect(node.body, module, [*scope, node.name, "<locals>"], rel, out)
            elif isinstance(node, ast.ClassDef):
                qual = ".".join([*scope, node.name])
                out.append(
                    Definition(
                        f"py:{module}.{qual}",
                        rel,
                        node.lineno,
                        node.end_lineno or node.lineno,
                        "class",
                    )
                )
                self._collect(node.body, module, [*scope, node.name], rel, out)

    def symbols_at(self, rel_path: str, lines: set[int]) -> list[Definition]:
        """Innermost function definitions covering any of the lines (classes only when a
        changed line belongs to no function, e.g. a class attribute)."""
        defs = self.definitions(rel_path)
        hits: dict[SymbolId, Definition] = {}
        for line in lines:
            covering = [d for d in defs if d.start <= line <= d.end]
            funcs = [d for d in covering if d.kind == "function"]
            pick = (
                max(funcs, key=lambda d: d.start)
                if funcs
                else (max(covering, key=lambda d: d.start) if covering else None)
            )
            if pick:
                hits[pick.symbol] = pick
        return sorted(hits.values(), key=lambda d: (d.path, d.start))

    def find(self, symbol: SymbolId) -> Definition | None:
        rel = self.path_for(symbol)
        if rel is None:
            return None
        for d in self.definitions(rel):
            if d.symbol == symbol:
                return d
        return None

    def path_for(self, symbol: SymbolId) -> str | None:
        """Best-effort inverse of the naming scheme: longest module prefix that is a file."""
        name = symbol.split(":", 1)[1]
        parts = name.split(".")
        for i in range(len(parts), 0, -1):
            candidate = "/".join(parts[:i])
            for roots, is_test in ((self.test_roots, True), (self.source_roots, False)):
                for root in roots:
                    base = root
                    rel_prefix = root.relative_to(self.repo_root).parts if is_test else ()
                    cand_parts = parts[:i]
                    if is_test:
                        if tuple(cand_parts[: len(rel_prefix)]) != tuple(rel_prefix):
                            continue
                        cand_parts = cand_parts[len(rel_prefix) :]
                        candidate = "/".join(cand_parts)
                    for suffix in (".py", "/__init__.py"):
                        file = base / (candidate + suffix)
                        if file.is_file():
                            return str(file.resolve().relative_to(self.repo_root))
        return None

    def source(self, symbol: SymbolId, context: int = 0) -> str | None:
        d = self.find(symbol)
        if d is None:
            return None
        lines = (self.repo_root / d.path).read_text(encoding="utf-8").splitlines()
        lo, hi = max(0, d.start - 1 - context), min(len(lines), d.end + context)
        return "\n".join(f"{i + 1:5d}  {lines[i]}" for i in range(lo, hi))

    def enclosing_class(self, symbol: SymbolId) -> Definition | None:
        d = self.find(symbol)
        if d is None:
            return None
        classes = [
            c for c in self.definitions(d.path)
            if c.kind == "class" and c.start <= d.start and c.end >= d.end and c.symbol != d.symbol
        ]  # fmt: skip
        return max(classes, key=lambda c: c.start) if classes else None

    def return_type_of(self, symbol: SymbolId) -> SymbolId | None:
        d = self.find(symbol)
        if d is None or d.kind != "function":
            return None
        try:
            tree = ast.parse((self.repo_root / d.path).read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            return None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.lineno == d.start:
                ann = node.returns
                if ann is None:
                    return None
                name = ast.unparse(ann)
                if name.startswith("Optional[") and name.endswith("]"):
                    name = name[len("Optional[") : -1]
                if name.endswith(" | None"):
                    name = name[: -len(" | None")]
                cls = name.split(".")[-1]
                if not cls.isidentifier():
                    return None
                candidates = [
                    x
                    for x in self.all_definitions()
                    if x.kind == "class" and x.symbol.endswith("." + cls)
                ]
                return candidates[0].symbol if len(candidates) == 1 else None
        return None

    def all_definitions(self) -> list[Definition]:
        if not getattr(self, "_all", None):
            out: list[Definition] = []
            for root in self.source_roots:
                for f in sorted(root.rglob("*.py")):
                    try:
                        rel = str(f.resolve().relative_to(self.repo_root))
                    except ValueError:
                        continue
                    out.extend(self.definitions(rel))
            self._all = out
        return self._all

    def module_of(self, symbol: SymbolId) -> str | None:
        """Dotted module of a symbol: the longest prefix of its qualified name that is a file."""
        rel = self.path_for(symbol)
        return self.module_for(self.repo_root / rel) if rel else None

    def tests_importing(self, module: str, limit: int = 3) -> list[str]:
        """Test files that import the module (or its package), by name. Shallow and cheap."""
        hits: list[str] = []
        needles = {module, module.rsplit(".", 1)[0]}
        for root in self.test_roots:
            for file in sorted(root.rglob("test_*.py")):
                try:
                    text = file.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                if any(f"from {n} import" in text or f"import {n}" in text for n in needles):
                    hits.append(str(file.resolve().relative_to(self.repo_root)))
                if len(hits) >= limit:
                    return hits
        return hits
