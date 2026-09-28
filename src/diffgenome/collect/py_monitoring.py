"""CPython symbol-plane collector on `sys.monitoring` (PEP 669, Python >= 3.12).

Complete-fidelity capture of in-scope logical calls, with stand-in calls attributed to the
in-scope function that made them. This module is allowed to know about CPython and
`unittest.mock`; what it emits is the language-neutral protocol only.

Scope: a code object is in scope when its file lies under a source root (`REPO`) or a
test root (`TEST`). Everything else (stdlib, site-packages, generated `<string>` code) is
out of scope and its events are disabled at the first hit, so it costs nothing afterwards.

Known limits (see docs/experiment-01.md): generators/coroutines are not modelled (a
stack repair is counted instead), `side_effect`/`wraps` bodies run inside the stand-in
call and are attributed to it. A stand-in call's arguments and outcome are observed by
wrapping `unittest.mock`'s private `_mock_call` while tracing (a runtime-adapter detail,
restored on stop).
"""

from __future__ import annotations

import dataclasses
import hashlib
import inspect
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from types import CodeType
from typing import Any
from unittest import mock

from diffgenome.model import (
    ArgShapes,
    CallNode,
    Collector,
    Fidelity,
    Node,
    Origin,
    OsEventNode,
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


_DIGEST_DEPTH = 3
_DIGEST_WIDTH = 16  # elements/fields considered per container level


def _canonical(value: Any, depth: int) -> str | None:
    """Canonical string of a value to a bounded depth, or None when not summarizable.
    Anything None at any level makes the whole digest unavailable: a partial digest would
    let two different values look equal."""
    if value is None or isinstance(value, bool | int | str | bytes):
        return f"{type(value).__name__}:{value!r}"
    if isinstance(value, float):
        return f"float:{value.hex()}"
    if isinstance(value, mock.NonCallableMock) or depth == 0:
        return None
    if isinstance(value, list | tuple | set | frozenset):
        if len(value) > _DIGEST_WIDTH:
            return None
        parts: list[str] = []
        for v in value:
            c = _canonical(v, depth - 1)
            if c is None:
                return None
            parts.append(c)
        if isinstance(value, set | frozenset):
            parts.sort()
        return f"{type(value).__name__}[{','.join(parts)}]"
    if isinstance(value, dict):
        if len(value) > _DIGEST_WIDTH:
            return None
        items: list[str] = []
        for k, v in value.items():
            ck, cv = _canonical(k, depth - 1), _canonical(v, depth - 1)
            if ck is None or cv is None:
                return None
            items.append(f"{ck}={cv}")
        return f"dict{{{','.join(sorted(items))}}}"
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        fields: list[str] = []
        for f in dataclasses.fields(value)[:_DIGEST_WIDTH]:
            c = _canonical(getattr(value, f.name), depth - 1)
            if c is None:
                return None
            fields.append(f"{f.name}={c}")
        return f"{type(value).__qualname__}({','.join(fields)})"
    return None


def digest_value(value: Any) -> str:
    """Stable content digest of a value, or "" when unavailable. Uses sha256 (not hash())
    so digests agree across processes and runs. Short scalars are trivially reversible by
    brute force; the digest hides values from casual reading, not from an adversary."""
    canonical = _canonical(value, _DIGEST_DEPTH)
    return "" if canonical is None else hashlib.sha256(canonical.encode()).hexdigest()[:16]


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
    _pending_mock_calls: dict[int, list[int]] = field(default_factory=dict, repr=False)
    _orig_mock_call: Any = None

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

    def symbol_for_object(self, obj: Any) -> Symbol:
        """Identity of a class/function reached by *object*, not by frame, with the origin
        and location the collector can observe for it. Uses the same file-based naming as
        frames when the object has a code object or an in-scope source file; otherwise a
        module-based name, which is a second identity scheme (see exp 01 findings)."""
        code = getattr(obj, "__code__", None)
        if isinstance(code, CodeType) and (scope := self.scope_for(code)):
            return Symbol(scope.symbol, scope.origin, scope.location)
        try:
            file = inspect.getsourcefile(obj)
        except TypeError:
            file = None
        qualname = getattr(obj, "__qualname__", type(obj).__qualname__)
        if file:
            named = self._module_for(Path(file))
            if named:
                line = getattr(code, "co_firstlineno", None) if isinstance(code, CodeType) else None
                loc = SourceLocation(str(Path(file).relative_to(self.repo_root)), line or 0)
                return Symbol(f"py:{named[1]}.{qualname}", named[0], loc)
        # C-implemented members (method/getset descriptors) carry no __module__ of their
        # own; the defining class does. Falling back to type(obj).__module__ named
        # sqlite3.Connection.execute as "builtins": a wrong identity, caught in exp 01.
        owner = getattr(obj, "__objclass__", None)
        module = getattr(obj, "__module__", None) or (owner.__module__ if owner else None)
        if module is None:
            return Symbol(f"py:{type(obj).__module__}.{qualname}", Origin.UNKNOWN, None)
        # A real object in this process whose file is absent or out of scope: external.
        return Symbol(f"py:{module}.{qualname}", Origin.EXTERNAL, None)

    def _intern(self, symbol: SymbolId, origin: Origin, location: SourceLocation | None) -> None:
        if symbol not in self._symbols:
            self._symbols[symbol] = Symbol(symbol, origin, location)

    def _intern_symbol(self, symbol: Symbol) -> SymbolId:
        self._intern(symbol.id, symbol.origin, symbol.location)
        return symbol.id

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
        target = self._intern_symbol(self.symbol_for_object(member if member is not None else spec))
        return target, "spec", tuple(path)

    def _record_substitution(
        self, thread: int, mechanism: SubstitutionMechanism, callable_: Any, args: ArgShapes
    ) -> int:
        stack = self._stacks[thread]
        parent = stack[-1][1] if stack else 0
        if isinstance(callable_, mock.NonCallableMock):
            substitute = f"py:{type(callable_).__module__}.{type(callable_).__qualname__}"
            claimed, relation, path = self._describe_mock(callable_)
        else:
            substitute = self._intern_symbol(self.symbol_for_object(callable_))
            claimed, relation, path = None, "none", ()
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
        args: ArgShapes = tuple(
            (n, summarize_value(frame.f_locals[n]), digest_value(frame.f_locals[n]))
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
            args=args,
            thread=self._threads[ident],
        )
        self._nodes.append(node)
        stack.append((code, node.id))
        return None

    def _set_outcome(self, node_id: int, outcome: str, result: str = "") -> None:
        node = self._nodes[node_id]
        assert not isinstance(node, OsEventNode)
        self._nodes[node_id] = dataclasses.replace(node, outcome=outcome, result=result)

    def _pop(self, code: CodeType, outcome: str, result: str = "") -> None:
        stack = self._stacks.get(threading.get_ident())
        if not stack:
            return
        if stack[-1][0] is not code:
            self._stack_repairs += 1
            while stack and stack[-1][0] is not code:
                stack.pop()
            if not stack:
                return
        _, node_id = stack.pop()
        if node_id != 0:
            self._set_outcome(node_id, outcome, result)
        if stack and stack[-1][0] is None:  # the substitution wrapper of a fake ends too
            self._set_outcome(stack.pop()[1], outcome, result)

    # PY_RETURN/PY_UNWIND cannot be disabled per location (CPython raises), so
    # out-of-scope returns are simply ignored; PY_START's DISABLE keeps the cost down.
    def _on_return(self, code: CodeType, _offset: int, value: object) -> Any:
        if self.scope_for(code) is not None:
            self._pop(code, "returned", digest_value(value))
        return None

    def _on_unwind(self, code: CodeType, _offset: int, exc: BaseException) -> Any:
        if self.scope_for(code) is not None:
            self._pop(code, "raised:" + self._intern_symbol(self.symbol_for_object(type(exc))))
        return None

    def _mock_call(self, m: Any, /, *args: Any, **kwargs: Any) -> Any:
        """Wraps unittest.mock's call path while tracing, so a stand-in call's outcome is
        observed rather than inferred. The CALL event has already recorded the node."""
        pending = self._pending_mock_calls.get(threading.get_ident())
        node_id = pending.pop() if pending else None
        if node_id is not None:
            # The CALL event only exposes the first argument; here all of them are visible.
            shapes: ArgShapes = tuple(
                [
                    (f"arg{i}", summarize_value(a), digest_value(a))
                    for i, a in enumerate(args[:_MAX_ARGS])
                ]
                + [
                    (k, summarize_value(v), digest_value(v))
                    for k, v in list(kwargs.items())[:_MAX_ARGS]
                ]
            )
            node = self._nodes[node_id]
            assert isinstance(node, SubstitutionNode)
            self._nodes[node_id] = dataclasses.replace(node, args=shapes)
        try:
            result = self._orig_mock_call(m, *args, **kwargs)
        except BaseException as exc:
            if node_id is not None:
                self._set_outcome(
                    node_id, "raised:" + self._intern_symbol(self.symbol_for_object(type(exc)))
                )
            raise
        if node_id is not None:
            self._set_outcome(node_id, "returned", digest_value(result))
        return result

    def _on_call(self, code: CodeType, _offset: int, callable_: object, arg0: object) -> Any:
        if self.scope_for(code) is None:
            return _DISABLE
        if isinstance(callable_, mock.NonCallableMock):
            args: ArgShapes = (
                () if arg0 is _MISSING else (("arg0", summarize_value(arg0), digest_value(arg0)),)
            )
            ident = self._thread()
            node_id = self._record_substitution(
                ident, SubstitutionMechanism.MOCK_OBJECT, callable_, args
            )
            self._pending_mock_calls.setdefault(ident, []).append(node_id)
        return None

    # ------------------------------------------------------------------ lifecycle

    def start(self, root_symbol: SymbolId, root_code: CodeType | None) -> None:
        m = sys.monitoring
        self._nodes.clear()
        self._symbols.clear()
        self._stacks.clear()
        self._threads.clear()
        self._stack_repairs = 0
        self._pending_mock_calls.clear()
        self._root_code = root_code
        origin = Origin.TEST
        location = None
        if root_code is not None and (scope := self.scope_for(root_code)):
            origin, location = scope.origin, scope.location
        self._intern(root_symbol, origin, location)
        self._nodes.append(CallNode(0, None, root_symbol, 0, (), 0))
        self._thread()
        m.use_tool_id(_TOOL_ID, "diffgenome")
        m.register_callback(_TOOL_ID, m.events.PY_START, self._on_start)
        m.register_callback(_TOOL_ID, m.events.PY_RETURN, self._on_return)
        m.register_callback(_TOOL_ID, m.events.PY_UNWIND, self._on_unwind)
        m.register_callback(_TOOL_ID, m.events.CALL, self._on_call)
        mixin: Any = mock.CallableMixin  # private attribute, absent from typeshed
        self._orig_mock_call = mixin._mock_call
        tracer = self

        def _traced_mock_call(mock_self: Any, /, *args: Any, **kwargs: Any) -> Any:
            return tracer._mock_call(mock_self, *args, **kwargs)

        mixin._mock_call = _traced_mock_call
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
        if self._orig_mock_call is not None:
            mixin: Any = mock.CallableMixin
            mixin._mock_call = self._orig_mock_call
            self._orig_mock_call = None
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
