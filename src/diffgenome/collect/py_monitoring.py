"""CPython symbol-plane collector on `sys.monitoring` (PEP 669, Python >= 3.12).

Complete-fidelity capture of in-scope logical calls, with stand-in calls attributed to the
in-scope function that made them. This module is allowed to know about CPython and
`unittest.mock`; what it emits is the language-neutral protocol only.

Scope: a code object is in scope when its file lies under a source root (`REPO`) or a
test root (`TEST`). Everything else (stdlib, site-packages, generated `<string>` code) is
out of scope and its events are disabled at the first hit, so it costs nothing afterwards.

Known limits (see docs/experiment-01.md): generators/coroutines are not modelled (a
stack repair is counted instead), `side_effect`/`wraps` bodies run inside the stand-in
call and are attributed to it, and only the first argument of a stand-in call is visible.
"""

from __future__ import annotations

import inspect
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from types import CodeType
from typing import Any
from unittest import mock

from diffgenome.model import (
    CallNode,
    Collector,
    Fidelity,
    Node,
    Origin,
    Plane,
    SourceLocation,
    SubstitutionMechanism,
    SubstitutionNode,
    Symbol,
    SymbolId,
)

COLLECTOR = Collector("py-sys-monitoring", Plane.SYMBOL, Fidelity.COMPLETE)
_TOOL_ID = 4  # sys.monitoring tool slot; coverage.py uses 2/3 by convention
_MISSING = sys.monitoring.MISSING
_DISABLE = sys.monitoring.DISABLE
_MAX_ARGS = 8
# Never repository code even when located under a source root: installed dependencies and
# hidden tool directories (.venv, .tox, .git...). "What counts as the repository" is a
# known open problem; this is the minimal rule that keeps dependencies out.
_EXCLUDED_PARTS = {"site-packages", "dist-packages", "node_modules", "__pycache__"}


def summarize_value(value: Any) -> str:
    """Bounded, deterministic shape of a value for seam matching. Never repr()s user data."""
    if value is None or isinstance(value, bool | int | float | str | bytes):
        return type(value).__name__
    if isinstance(value, mock.NonCallableMock):
        return "stand-in"
    if isinstance(value, list | tuple | set | frozenset | dict):
        return f"{type(value).__name__}[{len(value)}]"
    return type(value).__qualname__


@dataclass
class _Scope:
    origin: Origin
    symbol: SymbolId
    location: SourceLocation


@dataclass
class TraceResult:
    symbols: tuple[Symbol, ...]
    nodes: tuple[Node, ...]
    stack_repairs: int = 0  # returns that did not match the shadow-stack top


@dataclass
class Tracer:
    """One tracer per process. `start()`/`stop()` bracket a single stimulus."""

    repo_root: Path
    source_roots: tuple[Path, ...]
    test_roots: tuple[Path, ...]
    _scopes: dict[CodeType, _Scope | None] = field(default_factory=dict, repr=False)
    _symbols: dict[SymbolId, Symbol] = field(default_factory=dict, repr=False)
    _nodes: list[Node] = field(default_factory=list, repr=False)
    _stacks: dict[int, list[tuple[CodeType | None, int]]] = field(default_factory=dict, repr=False)
    _threads: dict[int, int] = field(default_factory=dict, repr=False)
    _root_code: CodeType | None = None
    _stack_repairs: int = 0

    # ------------------------------------------------------------------ symbol naming

    def _module_for(self, path: Path) -> tuple[Origin, str] | None:
        if any(part in _EXCLUDED_PARTS or part.startswith(".") for part in path.parts[1:]):
            return None
        for origin, roots in ((Origin.TEST, self.test_roots), (Origin.REPO, self.source_roots)):
            for root in roots:
                try:
                    rel = path.relative_to(root)
                except ValueError:
                    continue
                parts = list(rel.with_suffix("").parts)
                if parts and parts[-1] == "__init__":
                    parts.pop()
                prefix = root.relative_to(self.repo_root).parts if origin is Origin.TEST else ()
                return origin, ".".join((*prefix, *parts))
        return None

    def scope_for(self, code: CodeType) -> _Scope | None:
        if code in self._scopes:
            return self._scopes[code]
        scope = None
        filename = code.co_filename
        if not filename.startswith("<"):
            named = self._module_for(Path(filename))
            if named:
                origin, module = named
                scope = _Scope(
                    origin,
                    f"py:{module}.{code.co_qualname}",
                    SourceLocation(
                        str(Path(filename).relative_to(self.repo_root)), code.co_firstlineno
                    ),
                )
        self._scopes[code] = scope
        return scope

    def symbol_for_code(self, code: CodeType) -> SymbolId | None:
        scope = self.scope_for(code)
        return scope.symbol if scope else None

    def symbol_for_object(self, obj: Any) -> SymbolId:
        """Identity of a class/function reached by *object*, not by frame. Uses the same
        file-based naming as frames when the object's file is in scope, so the two routes
        must agree; that agreement is exactly what experiment 01 criterion S5 checks."""
        code = getattr(obj, "__code__", None)
        if isinstance(code, CodeType):
            sym = self.symbol_for_code(code)
            if sym:
                return sym
        try:
            file = inspect.getsourcefile(obj)
        except TypeError:
            file = None
        qualname = getattr(obj, "__qualname__", type(obj).__qualname__)
        if file:
            named = self._module_for(Path(file))
            if named:
                return f"py:{named[1]}.{qualname}"
        # C-implemented members (method/getset descriptors) carry no __module__ of their
        # own; the defining class does. Falling back to type(obj).__module__ named
        # sqlite3.Connection.execute as "builtins": a wrong identity, caught in exp 01.
        owner = getattr(obj, "__objclass__", None)
        module = (
            getattr(obj, "__module__", None)
            or (owner.__module__ if owner is not None else None)
            or type(obj).__module__
        )
        return f"py:{module}.{qualname}"

    def _intern(self, symbol: SymbolId, origin: Origin, location: SourceLocation | None) -> None:
        if symbol not in self._symbols:
            self._symbols[symbol] = Symbol(symbol, origin, location)

    # ------------------------------------------------------------------ stand-ins

    def _describe_mock(self, m: Any) -> tuple[SymbolId | None, str, tuple[str, ...]]:
        path: list[str] = []
        root = m
        while True:
            name = root._mock_name or root._mock_new_name
            if name:
                path.append(name)
            parent = root._mock_parent or root._mock_new_parent
            if parent is None:
                break
            root = parent
        path.reverse()
        spec = getattr(root, "_spec_class", None)
        if spec is None:
            return None, "none", tuple(path)
        member: Any = None
        if path and path[0] != "()":
            member = inspect.getattr_static(spec, path[0], None)
            member = getattr(member, "__func__", getattr(member, "fget", member))
        target = self.symbol_for_object(member if member is not None else spec)
        return target, "spec", tuple(path)

    def _record_substitution(
        self, thread: int, mechanism: SubstitutionMechanism, callable_: Any, args: str | None
    ) -> int:
        stack = self._stacks[thread]
        parent = stack[-1][1] if stack else 0
        if isinstance(callable_, mock.NonCallableMock):
            substitute = f"py:{type(callable_).__module__}.{type(callable_).__qualname__}"
            claimed, relation, path = self._describe_mock(callable_)
        else:
            substitute, claimed, relation, path = (
                self.symbol_for_object(callable_),
                None,
                "none",
                (),
            )
        if claimed:
            origin = Origin.REPO if claimed in self._symbols else Origin.UNKNOWN
            self._intern(claimed, origin, None)
        node = SubstitutionNode(
            id=len(self._nodes),
            parent=parent,
            collector=0,
            mechanism=mechanism,
            substitute=substitute,
            claimed_target=claimed,
            relation=relation,
            path=path,
            args=args,
        )
        self._nodes.append(node)
        return node.id

    # ------------------------------------------------------------------ callbacks

    def _thread(self) -> int:
        ident = threading.get_ident()
        if ident not in self._threads:
            self._threads[ident] = len(self._threads)
            self._stacks[ident] = []
        return ident

    def _on_start(self, code: CodeType, _offset: int) -> Any:
        scope = self.scope_for(code)
        if scope is None:
            return _DISABLE
        ident = self._thread()
        stack = self._stacks[ident]
        if not stack and code is self._root_code and self._threads[ident] == 0:
            stack.append((code, 0))
            return None
        frame = sys._getframe(1)
        names = code.co_varnames[: code.co_argcount + code.co_kwonlyargcount][:_MAX_ARGS]
        args = ", ".join(
            f"{n}={summarize_value(frame.f_locals[n])}"
            for n in names
            if n not in ("self", "cls") and n in frame.f_locals
        )
        parent = stack[-1][1] if stack else 0
        parent_symbol = getattr(self._nodes[parent], "symbol", None)
        parent_origin = self._symbols[parent_symbol].origin if parent_symbol else Origin.UNKNOWN
        if scope.origin is Origin.TEST and parent_origin is Origin.REPO:
            # Production code called into test-defined code: a fake/stub that executes.
            mechanism = (
                SubstitutionMechanism.FAKE
                if "." in code.co_qualname
                else SubstitutionMechanism.STUB
            )
            sub_id = self._record_substitution(ident, mechanism, _CodeHolder(code), args)
            stack.append((None, sub_id))
            parent = sub_id
        self._intern(scope.symbol, scope.origin, scope.location)
        node = CallNode(
            id=len(self._nodes),
            parent=parent,
            symbol=scope.symbol,
            collector=0,
            args=args or None,
            thread=self._threads[ident],
        )
        self._nodes.append(node)
        stack.append((code, node.id))
        return None

    def _on_return(self, code: CodeType, _offset: int, _value: object) -> Any:
        # PY_RETURN/PY_UNWIND cannot be disabled per location (CPython raises), so
        # out-of-scope returns are simply ignored; PY_START's DISABLE keeps the cost down.
        if self.scope_for(code) is None:
            return None
        stack = self._stacks.get(threading.get_ident())
        if not stack:
            return None
        if stack[-1][0] is not code:
            self._stack_repairs += 1
            while stack and stack[-1][0] is not code:
                stack.pop()
            if not stack:
                return None
        stack.pop()
        if stack and stack[-1][0] is None:  # the substitution wrapper of a fake
            stack.pop()
        return None

    def _on_call(self, code: CodeType, _offset: int, callable_: object, arg0: object) -> Any:
        if self.scope_for(code) is None:
            return _DISABLE
        if isinstance(callable_, mock.NonCallableMock):
            args = None if arg0 is _MISSING else f"arg0={summarize_value(arg0)}"
            self._record_substitution(
                self._thread(), SubstitutionMechanism.MOCK_OBJECT, callable_, args
            )
        return None

    # ------------------------------------------------------------------ lifecycle

    def start(self, root_symbol: SymbolId, root_code: CodeType | None) -> None:
        m = sys.monitoring
        self._nodes.clear()
        self._symbols.clear()
        self._stacks.clear()
        self._threads.clear()
        self._stack_repairs = 0
        self._root_code = root_code
        origin = Origin.TEST
        location = None
        if root_code is not None and (scope := self.scope_for(root_code)):
            origin, location = scope.origin, scope.location
        self._intern(root_symbol, origin, location)
        self._nodes.append(CallNode(0, None, root_symbol, 0, None, 0))
        self._thread()
        m.use_tool_id(_TOOL_ID, "diffgenome")
        m.register_callback(_TOOL_ID, m.events.PY_START, self._on_start)
        m.register_callback(_TOOL_ID, m.events.PY_RETURN, self._on_return)
        m.register_callback(_TOOL_ID, m.events.PY_UNWIND, self._on_return)
        m.register_callback(_TOOL_ID, m.events.CALL, self._on_call)
        m.restart_events()
        m.set_events(
            _TOOL_ID, m.events.PY_START | m.events.PY_RETURN | m.events.PY_UNWIND | m.events.CALL
        )

    def stop(self) -> TraceResult:
        m = sys.monitoring
        m.set_events(_TOOL_ID, 0)
        for ev in (m.events.PY_START, m.events.PY_RETURN, m.events.PY_UNWIND, m.events.CALL):
            m.register_callback(_TOOL_ID, ev, None)
        m.free_tool_id(_TOOL_ID)
        return TraceResult(
            symbols=tuple(self._symbols[k] for k in sorted(self._symbols)),
            nodes=tuple(self._nodes),
            stack_repairs=self._stack_repairs,
        )


class _CodeHolder:
    """Lets `symbol_for_object` name a fake by its code object without a function object."""

    def __init__(self, code: CodeType) -> None:
        self.__code__ = code
        self.__qualname__ = code.co_qualname
