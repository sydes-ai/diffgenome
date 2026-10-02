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

import ast
import dataclasses
import hashlib
import inspect
import io
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from types import CodeType, ModuleType
from typing import Any
from unittest import mock

from diffgenome.model import (
    ArgShapes,
    BranchObs,
    CallNode,
    Collector,
    Fidelity,
    Node,
    Origin,
    OsEventKind,
    OsEventNode,
    Plane,
    SourceLocation,
    StateFacts,
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
# Captured at import: targets patch builtins.open (mock_open) during tests, and site maps
# are built lazily on the capture path.
_READ_SOURCE = io.open
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


_STATE_WIDTH = 16


#: frames from a monitoring callback's body to the monitored frame: the callback itself, then
#: the re-entrancy guard (`Tracer._guarded`) that sys.monitoring actually calls
_MONITORED = 2


def own_dict(obj: Any) -> dict[str, Any] | None:
    """`obj.__dict__` without running target code: a plain `getattr` falls through to a
    class's `__getattr__` when there is no instance dict (Baserow's lazy queryset proxy then
    built a queryset, which the tracer inspected again, until RecursionError)."""
    try:
        d = object.__getattribute__(obj, "__dict__")
    except Exception:
        return None
    return d if isinstance(d, dict) else None


def bucket(value: Any) -> tuple[str, str] | None:
    """Language-neutral low-cardinality bucket of a value, or None when the value is not
    branch-relevant enough to summarize (free-form objects, callables). Returns
    (bucket, digest) where digest is filled only for public identifiers (enum members,
    type names). Scalars are never stored: only their bucket."""
    import enum

    if value is None:
        return "none", ""
    if isinstance(value, bool):
        return f"bool:{'true' if value else 'false'}", ""
    if isinstance(value, enum.Enum):
        return f"enum:{value.name}", digest_value(value.name)
    if isinstance(value, int | float):
        return ("num:zero" if value == 0 else "num:pos" if value > 0 else "num:neg"), ""
    if isinstance(value, str | bytes):
        return ("str:empty" if not value else "str:nonempty"), ""
    if isinstance(value, list | tuple | set | frozenset | dict):
        n = len(value)
        return ("coll:empty" if n == 0 else "coll:one" if n == 1 else "coll:many"), ""
    if isinstance(value, mock.NonCallableMock):
        spec = getattr(value, "_spec_class", None)
        return f"obj:stand-in{':' + spec.__qualname__ if spec else ''}", ""
    if callable(value) and not isinstance(value, type):
        return None
    name = type(value).__qualname__
    return f"obj:{name}", digest_value(name)


def state_facts(
    receiver: Any, code: CodeType | None, module_globals: dict[str, Any] | None
) -> StateFacts:
    """Receiver fields (first _STATE_WIDTH) and module globals the code reads, bucketed."""
    facts: list[tuple[str, str, str]] = []
    if receiver is not None and not isinstance(receiver, mock.NonCallableMock):
        facts.append(
            (
                "self:type",
                f"obj:{type(receiver).__qualname__}",
                digest_value(type(receiver).__qualname__),
            )
        )
        d = own_dict(receiver)
        if isinstance(d, dict):
            for name, value in list(d.items())[:_STATE_WIDTH]:
                b = bucket(value)
                if b is not None:
                    facts.append((f"self.{name}", b[0], b[1]))
    if code is not None and module_globals:
        names = code.co_names[: _STATE_WIDTH * 2]
        for name in names:
            if name in module_globals and not name.startswith("__"):
                value = module_globals[name]
                if isinstance(value, ModuleType | type):
                    # state read through an imported module or a class attribute:
                    # settings.STRICT, ModelManager._instance. Own namespace only.
                    for attr in names:
                        if attr != name and attr in vars(value):
                            inner = vars(value)[attr]
                            if isinstance(
                                inner, type | ModuleType | property | classmethod | staticmethod
                            ) or callable(inner):
                                continue
                            b = bucket(inner)
                            if b is not None:
                                facts.append((f"global.{name}.{attr}", b[0], b[1]))
                    continue
                if callable(value):
                    continue
                own = own_dict(value)
                if isinstance(own, dict) and not isinstance(value, mock.NonCallableMock):
                    # a global object (settings, config): the attributes this code reads
                    # through it, from its own instance dict only (no descriptors run)
                    for attr in names:
                        if attr != name and attr in own:
                            inner = own[attr]
                            if isinstance(inner, type | ModuleType) or callable(inner):
                                continue
                            b = bucket(inner)
                            if b is not None:
                                facts.append((f"global.{name}.{attr}", b[0], b[1]))
                b = bucket(value)
                if b is not None:
                    facts.append((f"global.{name}", b[0], b[1]))
    return tuple(facts[: _STATE_WIDTH * 2])


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


Pos = tuple[int, int]  # (line, 1-based byte column)


@dataclass(frozen=True)
class _IfSite:
    site: str
    test: tuple[Pos, Pos]  # [start, end) of the condition
    body: tuple[Pos, Pos]  # [start, end) of the then-block


def if_sites(source: str, rel_path: str) -> list[_IfSite]:
    """Every `if` statement's condition and then-block span in original source."""
    from diffgenome.sites import site_id

    out: list[_IfSite] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.If) or node.test.end_lineno is None:
            continue
        t = node.test
        span = (t.lineno, t.col_offset + 1, t.end_lineno or t.lineno, (t.end_col_offset or 0) + 1)
        first, last = node.body[0], node.body[-1]
        out.append(
            _IfSite(
                site_id(rel_path, span),
                ((span[0], span[1]), (span[2], span[3])),
                (
                    (first.lineno, first.col_offset + 1),
                    (last.end_lineno or last.lineno, (last.end_col_offset or 0) + 1),
                ),
            )
        )
    return out


def _inside(p: Pos, span: tuple[Pos, Pos]) -> bool:
    return span[0] <= p < span[1]


@dataclass
class TraceResult:
    symbols: tuple[Symbol, ...]
    nodes: tuple[Node, ...]
    stack_repairs: int = 0  # returns that did not match the shadow-stack top
    attribution_disagreements: int = (
        0  # calls where a shadow stack would have chosen another parent
    )
    branches: tuple[BranchObs, ...] = ()


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
    _busy: set[int] = field(default_factory=set, repr=False)  # threads inside a callback
    _threads: dict[int, int] = field(default_factory=dict, repr=False)
    _frame_nodes: dict[int, int] = field(default_factory=dict, repr=False)  # id(frame) -> node
    _fake_wrappers: dict[int, int] = field(
        default_factory=dict, repr=False
    )  # call node -> sub node
    _root_code: CodeType | None = None
    _import_phase: bool = False
    _stack_repairs: int = 0
    _attribution_disagreements: int = 0
    _pending_mock_calls: dict[int, list[int]] = field(default_factory=dict, repr=False)
    _orig_mock_call: Any = None
    _patched: dict[int, tuple[Any, str, Any]] = field(default_factory=dict, repr=False)
    _orig_patch_enter: Any = None
    _orig_patch_exit: Any = None
    _egress_guard_installed: bool = False
    _branches: list[BranchObs] = field(default_factory=list, repr=False)
    _file_sites: dict[str, list[_IfSite]] = field(default_factory=dict, repr=False)
    _positions: dict[CodeType, list[Any]] = field(default_factory=dict, repr=False)

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

    def _intern(
        self,
        symbol: SymbolId,
        origin: Origin,
        location: SourceLocation | None,
        kind: str = "callable",
    ) -> None:
        if symbol not in self._symbols or (
            kind != "callable" and self._symbols[symbol].kind == "callable"
        ):
            self._symbols[symbol] = Symbol(symbol, origin, location, kind)

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
                    else:
                        sym = self.symbol_for_object(original)
                        self._intern(sym.id, sym.origin, sym.location, "declaration")
                        return (
                            SubstitutionMechanism.INTERPOSITION,
                            sym.id,
                            "patch-target",
                            tuple(path),
                        )
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
            else:
                # No in-repo constructor body: the claim is a declaration, not a gap.
                sym = self.symbol_for_object(spec)
                self._intern(sym.id, sym.origin, sym.location, "declaration")
                return SubstitutionMechanism.MOCK_OBJECT, sym.id, "spec", tuple(path)
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
            d = own_dict(obj)
            if not isinstance(d, dict):
                continue
            for name, value in d.items():
                if value is root:
                    cls = obj if isinstance(obj, type) else type(obj)
                    member = _static_attr(cls, name)
                    if member is not None:
                        return cls, name, member
        return None

    def _seam_state(self, callable_: Any, frame: Any, relation: str) -> StateFacts:
        """State the real target would see at this seam, when the seed exposes it."""
        if frame is None:
            return ()
        root = callable_
        while isinstance(root, mock.NonCallableMock) and (
            root._mock_parent or root._mock_new_parent
        ):
            root = root._mock_parent or root._mock_new_parent
        if relation == "instance-attribute":
            bound = self._bound_attribute(root, frame)
            if bound is not None:
                obj = None
                for cand in list(frame.f_locals.values())[: _MAX_ARGS + 2]:
                    d = own_dict(cand)
                    if isinstance(d, dict) and any(v is root for v in d.values()):
                        obj = cand
                        break
                member = bound[2]
                func = getattr(member, "__func__", getattr(member, "fget", member))
                code = getattr(func, "__code__", None)
                return state_facts(obj, code, getattr(func, "__globals__", None))
        if relation == "patch-target":
            patched = self._patched.get(id(root))
            if patched is not None:
                target_obj, _, original = patched
                if (
                    isinstance(target_obj, ModuleType)
                    and getattr(original, "__code__", None) is not None
                ):
                    # the original's own globals: a function patched where it was imported
                    # still reads state from the module that defined it
                    return state_facts(
                        None, original.__code__, getattr(original, "__globals__", vars(target_obj))
                    )
                if not isinstance(target_obj, type | ModuleType):
                    func = getattr(original, "__func__", getattr(original, "fget", original))
                    return state_facts(
                        target_obj,
                        getattr(func, "__code__", None),
                        getattr(func, "__globals__", None),
                    )
        return ()

    def _record_substitution(
        self,
        parent: int,
        mechanism: SubstitutionMechanism,
        callable_: Any,
        args: ArgShapes,
        frame: Any = None,
    ) -> int:
        state: StateFacts = ()
        if isinstance(callable_, mock.NonCallableMock):
            substitute = f"py:{type(callable_).__module__}.{type(callable_).__qualname__}"
            mechanism, claimed, relation, path = self._describe_mock(callable_, frame)
            state = self._seam_state(callable_, frame, relation)
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
            state=state,
        )
        self._nodes.append(node)
        return node.id

    # ------------------------------------------------------------------ attribution

    def _guarded(self, callback: Any) -> Any:
        """Events raised by code the tracer itself runs while inspecting a frame (a property,
        `__getattr__`, `__repr__` of a target object) are not the program's behavior: they are
        ignored instead of being traced and inspected again."""
        busy: set[int] = self._busy

        def guarded(*args: Any) -> Any:
            ident = threading.get_ident()
            if ident in busy:
                return None
            busy.add(ident)
            try:
                return callback(*args)
            finally:
                busy.discard(ident)

        return guarded

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
        if self._import_phase and not code.co_flags & inspect.CO_OPTIMIZED:
            # import time (pytest_launch): module and class bodies define things, they are not
            # calls; functions they call attach to the nearest traced frame, the import root
            return _DISABLE
        scope = self.scope_for(code)
        if scope is None:
            return _DISABLE
        ident = self._thread()
        frame = sys._getframe(_MONITORED)
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
            recv = (
                frame.f_locals.get("self")
                if code.co_argcount and code.co_varnames[0] == "self"
                else None
            )
            if recv is not None:
                sub = self._nodes[sub_id]
                assert isinstance(sub, SubstitutionNode)
                self._nodes[sub_id] = dataclasses.replace(sub, state=state_facts(recv, None, None))
            parent = sub_id
        self._intern(scope.symbol, scope.origin, scope.location)
        receiver = (
            frame.f_locals.get("self")
            if code.co_argcount and code.co_varnames[0] == "self"
            else None
        )
        node = CallNode(
            id=len(self._nodes),
            parent=parent,
            symbol=scope.symbol,
            collector=0,
            args=args,
            thread=self._threads[ident],
            state=state_facts(receiver, code, frame.f_globals),
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
        frame = sys._getframe(_MONITORED + 1)
        node_id = self._frame_nodes.pop(id(frame), None)
        if node_id:
            self._set_outcome(node_id, outcome, result)
            node = self._nodes[node_id]
            if isinstance(node, CallNode):
                receiver = (
                    frame.f_locals.get("self")
                    if code.co_argcount and code.co_varnames[0] == "self"
                    else None
                )
                # the same bounded, value-free view as on entry: an observed delta, not a
                # complete write set (nested mutations can be invisible to it)
                self._nodes[node_id] = dataclasses.replace(
                    node, state_after=state_facts(receiver, code, frame.f_globals)
                )
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

    def _sites_for(self, filename: str) -> list[_IfSite]:
        sites = self._file_sites.get(filename)
        if sites is None:
            try:
                with _READ_SOURCE(filename, encoding="utf-8") as fh:
                    sites = if_sites(fh.read(), self._relative(filename))
            except (OSError, SyntaxError, ValueError):
                sites = []
            self._file_sites[filename] = sites
        return sites

    def _on_branch(self, code: CodeType, offset: int, destination: int) -> Any:
        """A conditional jump in production code. Mapped to the `if` whose condition
        contains the jump instruction; the outcome is whether control goes into that
        if's then-block. Jumps that stay inside the condition (short-circuit operands)
        are not decisions and are ignored; jumps of anything that is not an `if`
        condition are disabled at that location."""
        scope = self.scope_for(code)
        if scope is None or scope.origin is not Origin.REPO:
            return _DISABLE
        positions = self._positions.get(code)
        if positions is None:
            positions = self._positions[code] = list(code.co_positions())
        try:
            line, _eline, col, _ecol = positions[offset // 2]
            dline, _deline, dcol, _decol = positions[destination // 2]
        except IndexError:
            return None
        if line is None or col is None:
            return None
        here = (line, col + 1)
        match = None
        for site in self._sites_for(code.co_filename):
            if _inside(here, site.test) and (
                match is None or site.test[0] >= match.test[0]  # innermost
            ):
                match = site
        if match is None:
            return _DISABLE
        if dline is None or dcol is None:
            return None
        there = (dline, dcol + 1)
        if _inside(there, match.test):
            return None  # short-circuit inside the condition
        outcome = _inside(there, match.body)
        node = self._frame_nodes.get(id(sys._getframe(_MONITORED)), 0)
        self._branches.append(BranchObs(match.site, outcome, node, len(self._nodes)))
        return None

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
            frame = sys._getframe(_MONITORED)
            parent = self._frame_nodes.get(id(frame), self._ancestor_node(frame))
            node_id = self._record_substitution(
                parent, SubstitutionMechanism.MOCK_OBJECT, callable_, args, frame
            )
            self._pending_mock_calls.setdefault(ident, []).append(node_id)
        return None

    # ------------------------------------------------------------------ egress guard

    def install_egress_guard(self, allow_loopback: bool = False) -> None:
        """Refuse outbound connections and record each attempt as an OS-plane event. The
        sandbox is the enforcement layer; this makes attempts *evidence* attributed to the
        in-scope caller. With `allow_loopback` (the sandbox allows it too), connections to
        loopback addresses go through: tests talking to servers they started themselves.
        Installed for the whole session."""
        import ipaddress
        import socket

        tracer = self
        original = socket.socket.connect

        def loopback(address: Any) -> bool:
            if isinstance(address, str) or not address:
                return False
            host = str(address[0])
            if host == "localhost":
                return True
            try:
                return ipaddress.ip_address(host.split("%")[0]).is_loopback
            except ValueError:
                return False

        def connect(sock: Any, address: Any) -> Any:
            if allow_loopback and loopback(address):
                return original(sock, address)
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
        self._import_phase = root_code is None and root_symbol == "py:<import>"
        origin = Origin.TEST
        location = None
        if root_code is not None and (scope := self.scope_for(root_code)):
            origin, location = scope.origin, scope.location
        self._intern(root_symbol, origin, location)
        self._nodes.append(CallNode(0, None, root_symbol, 0, (), 0))
        self._thread()
        m.use_tool_id(_TOOL_ID, "diffgenome")
        m.register_callback(_TOOL_ID, m.events.PY_START, self._guarded(self._on_start))
        m.register_callback(_TOOL_ID, m.events.PY_RETURN, self._guarded(self._on_return))
        m.register_callback(_TOOL_ID, m.events.PY_UNWIND, self._guarded(self._on_unwind))
        m.register_callback(_TOOL_ID, m.events.CALL, self._guarded(self._on_call))
        m.register_callback(_TOOL_ID, m.events.BRANCH, self._guarded(self._on_branch))
        self._branches.clear()
        mixin: Any = mock.CallableMixin  # private attribute, absent from typeshed
        self._orig_mock_call = mixin._mock_call
        tracer = self

        def _traced_mock_call(mock_self: Any, /, *args: Any, **kwargs: Any) -> Any:
            return tracer._mock_call(mock_self, *args, **kwargs)

        mixin._mock_call = _traced_mock_call
        m.restart_events()
        m.set_events(
            _TOOL_ID,
            m.events.PY_START
            | m.events.PY_RETURN
            | m.events.PY_UNWIND
            | m.events.CALL
            | m.events.BRANCH,
        )

    def stop(self) -> TraceResult:
        m = sys.monitoring
        m.set_events(_TOOL_ID, 0)
        for ev in (
            m.events.PY_START,
            m.events.PY_RETURN,
            m.events.PY_UNWIND,
            m.events.CALL,
            m.events.BRANCH,
        ):
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
            branches=tuple(self._branches),
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
