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
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from types import CodeType, ModuleType
from typing import Any
from unittest import mock

from diffgenome.model import (
    ArgShapes,
    CallNode,
    Collector,
    Fidelity,
    Node,
    Origin,
    OsEventKind,
    OsEventNode,
    Plane,
    SourceLocation,
    SubstitutionMechanism,
    SubstitutionNode,
    Symbol,
    SymbolId,
)

COLLECTOR = Collector("py-sys-monitoring", Plane.SYMBOL, Fidelity.COMPLETE)
EGRESS_GUARD = Collector("py-egress-guard", Plane.OS, Fidelity.COMPLETE)
"""Connect attempts seen from inside the runtime. Kernel-boundary facts (OS plane) observed
by a runtime hook rather than by the kernel; the collector name says so."""
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
        spec = getattr(value, "_spec_class", None)
        return f"stand-in:{spec.__qualname__}" if spec else "stand-in"
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
    attribution_disagreements: int = (
        0  # calls where a shadow stack would have chosen another parent
    )


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
    _frame_nodes: dict[int, int] = field(default_factory=dict, repr=False)  # id(frame) -> node
    _fake_wrappers: dict[int, int] = field(
        default_factory=dict, repr=False
    )  # call node -> sub node
    _root_code: CodeType | None = None
    _stack_repairs: int = 0
    _attribution_disagreements: int = 0
    _pending_mock_calls: dict[int, list[int]] = field(default_factory=dict, repr=False)
    _orig_mock_call: Any = None
    _patched: dict[int, tuple[Any, str, Any]] = field(default_factory=dict, repr=False)
    _orig_patch_enter: Any = None
    _orig_patch_exit: Any = None
    _egress_guard_installed: bool = False

    # ------------------------------------------------------------------ symbol naming

    def __post_init__(self) -> None:
        # Everything below runs on the capture path and must not touch os.path, pathlib or
        # inspect: those read patchable globals, and a target that patches os.path.join
        # renamed our symbols after its temp file (Kokoro-FastAPI, experiment 02).
        self._repo_prefix = str(self.repo_root).rstrip("/") + "/"
        self._root_prefixes = [(Origin.TEST, str(r).rstrip("/") + "/") for r in self.test_roots] + [
            (Origin.REPO, str(r).rstrip("/") + "/") for r in self.source_roots
        ]

    def _module_for(self, filename: str) -> tuple[Origin, str] | None:
        for origin, prefix in self._root_prefixes:
            if not filename.startswith(prefix):
                continue
            rel = filename[len(prefix) :]
            parts = rel.split("/")
            if any(part in _EXCLUDED_PARTS or part.startswith(".") for part in parts):
                return None
            if parts[-1].endswith(".py"):
                parts[-1] = parts[-1][:-3]
            if parts and parts[-1] == "__init__":
                parts.pop()
            if origin is Origin.TEST:
                parts = prefix[len(self._repo_prefix) :].rstrip("/").split("/") + parts
            return origin, ".".join(p for p in parts if p)
        return None

    def _relative(self, filename: str) -> str:
        return (
            filename[len(self._repo_prefix) :]
            if filename.startswith(self._repo_prefix)
            else filename
        )

    def scope_for(self, code: CodeType) -> _Scope | None:
        if code in self._scopes:
            return self._scopes[code]
        scope = None
        filename = code.co_filename
        if not filename.startswith("<"):
            named = self._module_for(filename)
            if named:
                origin, module = named
                qualname = code.co_qualname
                if qualname.rsplit(".", 1)[-1].startswith("<"):
                    # Anonymous code (<lambda>, <genexpr>, <listcomp>...) has no name of its
                    # own: two lambdas in one function share a qualname. Its identity is
                    # its definition site. Found as an IdentityMismatch on Kokoro-FastAPI.
                    qualname = f"{qualname}@{code.co_firstlineno}"
                scope = _Scope(
                    origin,
                    f"py:{module}.{qualname}",
                    SourceLocation(self._relative(filename), code.co_firstlineno),
                )
        self._scopes[code] = scope
        return scope

    def symbol_for_code(self, code: CodeType) -> SymbolId | None:
        scope = self.scope_for(code)
        return scope.symbol if scope else None

    def symbol_for_object(self, obj: Any) -> Symbol:
        """Identity of a class/function reached by *object*, not by frame, with the origin
        and location the collector can observe for it. Uses the same file-based naming as
        frames when the object has a code object or an in-scope module file; otherwise a
        module-based name, which is a second identity scheme (see exp 01 findings).
        Reads only attributes, never os.path/inspect (see __post_init__)."""
        code = getattr(obj, "__code__", None)
        if isinstance(code, CodeType) and (scope := self.scope_for(code)):
            return Symbol(scope.symbol, scope.origin, scope.location)
        if isinstance(obj, ModuleType):
            # A patched module attribute (patch("pkg.mod.torch")) claims the module itself.
            file = getattr(obj, "__file__", None)
            named = self._module_for(file) if isinstance(file, str) else None
            if named and isinstance(file, str):
                return Symbol(f"py:{named[1]}", named[0], SourceLocation(self._relative(file), 0))
            return Symbol(f"py:{obj.__name__}", Origin.EXTERNAL, None)
        qualname = getattr(obj, "__qualname__", type(obj).__qualname__)
        owner = getattr(obj, "__objclass__", None)
        module_name = getattr(obj, "__module__", None) or (owner.__module__ if owner else None)
        module = sys.modules.get(module_name) if module_name else None
        file = getattr(module, "__file__", None)
        if isinstance(file, str):
            named = self._module_for(file)
            if named:
                line = code.co_firstlineno if isinstance(code, CodeType) else 0
                loc = SourceLocation(self._relative(file), line)
                return Symbol(f"py:{named[1]}.{qualname}", named[0], loc)
        if module_name is None:
            return Symbol(f"py:{type(obj).__module__}.{qualname}", Origin.UNKNOWN, None)
        # A real object in this process whose module is absent or out of scope: external.
        # C-implemented members carry no __module__; their defining class does (exp 01).
        return Symbol(f"py:{module_name}.{qualname}", Origin.EXTERNAL, None)

    def _intern(self, symbol: SymbolId, origin: Origin, location: SourceLocation | None) -> None:
        if symbol not in self._symbols:
            self._symbols[symbol] = Symbol(symbol, origin, location)

    def _intern_symbol(self, symbol: Symbol) -> SymbolId:
        self._intern(symbol.id, symbol.origin, symbol.location)
        return symbol.id

    # ------------------------------------------------------------------ stand-ins

    def _describe_mock(
        self, m: Any, frame: Any = None
    ) -> tuple[SubstitutionMechanism, SymbolId | None, str, tuple[str, ...]]:
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
        patched = self._patched.get(id(root))
        if patched is not None:
            # Installed by unittest.mock.patch: the patcher saved the original, which is
            # exactly what the stand-in replaces. path[0] is the patched attribute.
            _, _, original = patched
            claim = None
            if original is not mock.DEFAULT:
                original = getattr(original, "__func__", getattr(original, "fget", original))
                if len(path) <= 1 and isinstance(original, type):
                    # Calling a patched *class* constructs it; the claim is its __init__
                    # when that is in-repo Python (same rule as spec'd class stand-ins).
                    init = _static_attr(original, "__init__")
                    if getattr(init, "__code__", None) is not None:
                        original = init
                claim = self._intern_symbol(self.symbol_for_object(original))
            return SubstitutionMechanism.INTERPOSITION, claim, "patch-target", tuple(path)
        spec = getattr(root, "_spec_class", None)
        if spec is None:
            bound = self._bound_attribute(root, frame)
            if bound is not None:
                # The root stand-in is stored as attribute `name` of a real object whose
                # class defines `name`: it replaced that member. Identity, not naming.
                _, name, bound_member = bound
                bound_member = getattr(
                    bound_member, "__func__", getattr(bound_member, "fget", bound_member)
                )
                claim = self._intern_symbol(self.symbol_for_object(bound_member))
                return (
                    SubstitutionMechanism.INTERPOSITION,
                    claim,
                    "instance-attribute",
                    (name, *path[1:]) if path and path[0] == name else (name, *path),
                )
            return SubstitutionMechanism.MOCK_OBJECT, None, "none", tuple(path)
        member: Any = None
        if path and path[0] != "()":
            member = _static_attr(spec, path[0])
            member = getattr(member, "__func__", getattr(member, "fget", member))
        elif not path and isinstance(spec, type):
            # Calling a stand-in for a class is constructing it: what really runs is the
            # class's own __init__ (when it has one in Python), so that is the claim.
            init = _static_attr(spec, "__init__")
            if getattr(init, "__code__", None) is not None:
                member = init
        target = self._intern_symbol(self.symbol_for_object(member if member is not None else spec))
        return SubstitutionMechanism.MOCK_OBJECT, target, "spec", tuple(path)

    def _bound_attribute(self, root: Any, frame: Any) -> tuple[type, str, Any] | None:
        """Find a real (non-mock) object among the caller's locals, `self` first, whose
        instance dict holds `root` under a name its class also defines. Bounded scan; reads
        only __dict__ so no descriptor or property runs."""
        if frame is None:
            return None
        locals_ = frame.f_locals
        candidates = [locals_[n] for n in ("self", "cls") if n in locals_]
        candidates += [v for k, v in list(locals_.items())[:_MAX_ARGS] if k not in ("self", "cls")]
        for obj in candidates:
            if isinstance(obj, mock.NonCallableMock | type(None) | int | str | float | bool):
                continue
            d = getattr(obj, "__dict__", None)
            if not isinstance(d, dict):
                continue
            for name, value in d.items():
                if value is root:
                    cls = obj if isinstance(obj, type) else type(obj)
                    member = _static_attr(cls, name)
                    if member is not None:
                        return cls, name, member
        return None

    def _record_substitution(
        self,
        parent: int,
        mechanism: SubstitutionMechanism,
        callable_: Any,
        args: ArgShapes,
        frame: Any = None,
    ) -> int:
        if isinstance(callable_, mock.NonCallableMock):
            substitute = f"py:{type(callable_).__module__}.{type(callable_).__qualname__}"
            mechanism, claimed, relation, path = self._describe_mock(callable_, frame)
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

    # ------------------------------------------------------------------ attribution

    def _thread(self) -> int:
        ident = threading.get_ident()
        if ident not in self._threads:
            self._threads[ident] = len(self._threads)
            self._stacks[ident] = []
        return ident

    def _ancestor_node(self, frame: Any) -> int:
        """Node of the nearest in-scope frame on the real call stack above `frame`, or the
        root. Correct under generators and coroutines, where a shadow stack is not: a
        suspended frame is not an ancestor of what runs while it is suspended."""
        f = frame.f_back
        while f is not None:
            node = self._frame_nodes.get(id(f))
            if node is not None:
                return node
            f = f.f_back
        return 0

    def _shadow_parent(self, ident: int) -> int:
        stack = self._stacks[ident]
        return stack[-1][1] if stack else 0

    # ------------------------------------------------------------------ callbacks

    def _on_start(self, code: CodeType, _offset: int) -> Any:
        scope = self.scope_for(code)
        if scope is None:
            return _DISABLE
        ident = self._thread()
        frame = sys._getframe(1)
        stack = self._stacks[ident]
        if (
            code is self._root_code
            and self._threads[ident] == 0
            and 0 not in self._frame_nodes.values()
        ):
            self._frame_nodes[id(frame)] = 0
            stack.append((code, 0))
            return None
        names = code.co_varnames[: code.co_argcount + code.co_kwonlyargcount][:_MAX_ARGS]
        args: ArgShapes = tuple(
            (n, summarize_value(frame.f_locals[n]), digest_value(frame.f_locals[n]))
            for n in names
            if n not in ("self", "cls") and n in frame.f_locals
        )
        parent = self._ancestor_node(frame)
        if parent != self._shadow_parent(ident):
            self._attribution_disagreements += 1
        parent_symbol = getattr(self._nodes[parent], "symbol", None)
        parent_origin = self._symbols[parent_symbol].origin if parent_symbol else Origin.UNKNOWN
        sub_id = None
        if scope.origin is Origin.TEST and parent_origin is Origin.REPO:
            # Production code called into test-defined code: a fake/stub that executes.
            mechanism = (
                SubstitutionMechanism.FAKE
                if "." in code.co_qualname
                else SubstitutionMechanism.STUB
            )
            sub_id = self._record_substitution(parent, mechanism, _CodeHolder(code), args)
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
        self._frame_nodes[id(frame)] = node.id
        if sub_id is not None:
            self._fake_wrappers[node.id] = sub_id
        stack.append((code, node.id))
        return None

    def _set_outcome(self, node_id: int, outcome: str, result: str = "") -> None:
        node = self._nodes[node_id]
        assert not isinstance(node, OsEventNode)
        self._nodes[node_id] = dataclasses.replace(node, outcome=outcome, result=result)

    def _finish(self, code: CodeType, outcome: str, result: str = "") -> None:
        frame = sys._getframe(2)
        node_id = self._frame_nodes.pop(id(frame), None)
        if node_id:
            self._set_outcome(node_id, outcome, result)
            wrapper = self._fake_wrappers.pop(node_id, None)
            if wrapper is not None:
                self._set_outcome(wrapper, outcome, result)
        # Shadow stack, kept only to measure how often it would have misattributed.
        stack = self._stacks.get(threading.get_ident())
        if not stack:
            return
        if stack[-1][0] is not code:
            self._stack_repairs += 1
            while stack and stack[-1][0] is not code:
                stack.pop()
        if stack:
            stack.pop()

    # PY_RETURN/PY_UNWIND cannot be disabled per location (CPython raises), so
    # out-of-scope returns are simply ignored; PY_START's DISABLE keeps the cost down.
    def _on_return(self, code: CodeType, _offset: int, value: object) -> Any:
        if self.scope_for(code) is not None:
            self._finish(code, "returned", digest_value(value))
        return None

    def _on_unwind(self, code: CodeType, _offset: int, exc: BaseException) -> Any:
        if self.scope_for(code) is not None:
            self._finish(code, "raised:" + self._intern_symbol(self.symbol_for_object(type(exc))))
        return None

    def _mock_call(self, m: Any, /, *args: Any, **kwargs: Any) -> Any:
        """Wraps unittest.mock's call path while tracing, so a stand-in call's arguments and
        outcome are observed rather than inferred. The CALL event already recorded the node."""
        pending = self._pending_mock_calls.get(threading.get_ident())
        node_id = pending.pop() if pending else None
        if node_id is not None:
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
        # create_autospec(function) returns a plain function wrapper whose `.mock` is the
        # mock; without this it was invisible to the tracer (found by ground truth, exp 05).
        if not isinstance(callable_, mock.NonCallableMock) and isinstance(
            getattr(callable_, "mock", None), mock.NonCallableMock
        ):
            inner = callable_.mock  # type: ignore[attr-defined]
            if id(callable_) in self._patched and id(inner) not in self._patched:
                self._patched[id(inner)] = self._patched[id(callable_)]
            callable_ = inner
        if isinstance(callable_, mock.NonCallableMock):
            args: ArgShapes = (
                () if arg0 is _MISSING else (("arg0", summarize_value(arg0), digest_value(arg0)),)
            )
            ident = self._thread()
            frame = sys._getframe(1)
            parent = self._frame_nodes.get(id(frame), self._ancestor_node(frame))
            node_id = self._record_substitution(
                parent, SubstitutionMechanism.MOCK_OBJECT, callable_, args, frame
            )
            self._pending_mock_calls.setdefault(ident, []).append(node_id)
        return None

    # ------------------------------------------------------------------ egress guard

    def install_egress_guard(self) -> None:
        """Refuse outbound connections and record each attempt as an OS-plane event. The
        sandbox is the enforcement layer; this makes attempts *evidence* attributed to the
        in-scope caller. Installed for the whole session."""
        import socket

        tracer = self

        def connect(sock: Any, address: Any) -> Any:
            target = address if isinstance(address, str) else ":".join(str(a) for a in address[:2])
            if tracer._orig_mock_call is not None:  # tracing a stimulus
                frame = sys._getframe(1)
                parent = tracer._frame_nodes.get(id(frame), tracer._ancestor_node(frame))
                tracer._nodes.append(
                    OsEventNode(
                        id=len(tracer._nodes),
                        parent=parent,
                        collector=1,
                        kind=OsEventKind.CONNECT,
                        target=target,
                        outcome="refused:egress-guard",
                    )
                )
            raise PermissionError(f"diffgenome egress guard: connect to {target} refused")

        socket.socket.connect = connect  # type: ignore[method-assign]
        self._egress_guard_installed = True

    # ------------------------------------------------------------------ patch registry

    def install_patch_hook(self) -> None:
        """Record what `unittest.mock.patch` installs, for the whole session: fixtures may
        enter patches before a test's call phase begins. A runtime-adapter detail."""
        if self._orig_patch_enter is not None:
            return
        patch_cls: Any = mock._patch
        tracer = self
        self._orig_patch_enter, self._orig_patch_exit = patch_cls.__enter__, patch_cls.__exit__

        def enter(patcher: Any) -> Any:
            new = tracer._orig_patch_enter(patcher)
            original = getattr(patcher, "temp_original", mock.DEFAULT)
            tracer._patched[id(new)] = (patcher.target, patcher.attribute, original)
            return new

        def exit_(patcher: Any, *exc_info: Any) -> Any:
            try:
                current = getattr(patcher.target, patcher.attribute, None)
                tracer._patched.pop(id(current), None)
            except Exception:
                pass
            return tracer._orig_patch_exit(patcher, *exc_info)

        patch_cls.__enter__, patch_cls.__exit__ = enter, exit_

    # ------------------------------------------------------------------ lifecycle

    def start(self, root_symbol: SymbolId, root_code: CodeType | None) -> None:
        m = sys.monitoring
        self._nodes.clear()
        self._symbols.clear()
        self._stacks.clear()
        self._threads.clear()
        self._frame_nodes.clear()
        self._fake_wrappers.clear()
        self._stack_repairs = 0
        self._attribution_disagreements = 0
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
            attribution_disagreements=self._attribution_disagreements,
        )


def _static_attr(cls: Any, name: str) -> Any:
    """Attribute lookup through the MRO without invoking descriptors or inspect."""
    for klass in getattr(cls, "__mro__", (cls,)):
        d = getattr(klass, "__dict__", {})
        if name in d:
            return d[name]
    return None


class _CodeHolder:
    """Lets `symbol_for_object` name a fake by its code object without a function object."""

    def __init__(self, code: CodeType) -> None:
        self.__code__ = code
        self.__qualname__ = code.co_qualname
