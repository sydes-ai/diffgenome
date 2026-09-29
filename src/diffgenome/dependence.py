"""Conservative intra-procedural dependence and control facts over a neutral function IR.

Language front ends (Python via `ast`, Go via the instrumenter's `go/ast` walker) lower a
function to a small structured IR; this module is language-neutral. It establishes:

- **local def-use** by reaching definitions over structured code: every operand of every
  decision, argument of every call and value of every field store is resolved to its
  origins (`param:account.Balance`, `call:server.validAccount#0`, `global:settings.x`,
  `const`), or to `unknown:<reason>` when the analysis cannot follow it;
- **control requirements**: for every call, store, return and decision, the conjunction of
  (site, outcome) pairs that must hold to reach it. For structured code without goto or
  labelled break this is the transitive control dependence a post-dominator computation
  would give; early-exit guards (`if c { ...; return }`) make the rest of the block
  require `c = false`. Loops, exception handlers and constructs a front end marks opaque
  add an explicit unknown requirement instead of a guess;
- **decision order**: the pre-order position of every site, and which sites require which.

IR (JSON-able dicts). Function: {symbol, file, params, body}. Statements carry `k`, `line`
and, as applicable: `defs` (local names), `stores` (field/element paths written), `uses`
(paths read), `calls` ([{callee, args: [[paths]], line, addr: [locals whose address is
passed]}]), `site`/`span`/`pred`/`then`/`else` (if), `body` (loop, with, try), `handlers`,
`final` (try), `reason`/`blocks` (opaque). Kinds: assign, expr, if, return, raise, loop,
try, with, opaque, break.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

UNKNOWN = "UNKNOWN_DEPENDENCE"

Env = dict[str, frozenset[str]]
Req = tuple[tuple[str, bool | None], ...]  # (site, outcome); site "?reason" with None = unknown


@dataclass
class Facts:
    symbol: str
    file: str
    params: list[str]
    sites: list[dict[str, Any]] = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)
    stores: list[dict[str, Any]] = field(default_factory=list)
    returns: list[dict[str, Any]] = field(default_factory=list)
    unknown: list[dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "file": self.file,
            "params": self.params,
            "sites": self.sites,
            "calls": self.calls,
            "stores": self.stores,
            "returns": self.returns,
            "unknown": self.unknown,
        }


def _req(r: Req) -> list[list[Any]]:
    return [[s, o] for s, o in r]


class _Analyzer:
    def __init__(self, fn: dict[str, Any]) -> None:
        self.params = list(fn.get("params") or [])
        self.facts = Facts(fn["symbol"], fn["file"], self.params)
        self.order = 0

    # ---- origins

    def resolve(self, path: str, env: Env) -> frozenset[str]:
        if not path or path == "?":
            return frozenset({f"unknown:{UNKNOWN}:complex-expression"})
        base, _, rest = path.partition(".")
        suffix = f".{rest}" if rest else ""
        if base in env:
            out = set()
            for o in env[base]:
                if o.startswith(("unknown:", "const")):
                    out.add(o)
                else:
                    out.add(o + suffix)
            return frozenset(out)
        if base in self.params:
            return frozenset({f"param:{path}"})
        return frozenset({f"global:{path}"})

    def origins(self, paths: list[str], env: Env) -> list[str]:
        out: set[str] = set()
        for p in paths:
            out |= self.resolve(p, env)
        return sorted(out)

    # ---- walk

    def call_facts(self, calls: list[dict[str, Any]], env: Env, req: Req, line: int) -> Env:
        for c in calls:
            self.facts.calls.append(
                {
                    "callee": c.get("callee", "?"),
                    "line": c.get("line", line),
                    "requires": _req(req),
                    "arg_origins": [self.origins(a, env) for a in c.get("args") or []],
                }
            )
        # a local whose address is passed may be written by the callee
        new = dict(env)
        for c in calls:
            for local in c.get("addr") or []:
                new[local] = env.get(local, frozenset()) | {
                    f"unknown:{UNKNOWN}:address-passed-to:{c.get('callee', '?')}"
                }
        return new

    def assign(self, st: dict[str, Any], env: Env, req: Req) -> Env:
        env = self.call_facts(st.get("calls") or [], env, req, st["line"])
        calls = st.get("calls") or []
        defs = st.get("defs") or []
        value = set(self.origins(st.get("uses") or [], env))
        if len(calls) == 1 and st.get("value_is_call"):
            callee = calls[0].get("callee", "?")
            if len(defs) > 1:
                env = dict(env)
                for i, d in enumerate(defs):
                    if d != "_":  # Go's blank identifier holds a position, binds nothing
                        env[d] = frozenset({f"call:{callee}#{i}"})
                defs = []
            else:
                value = {f"call:{callee}"}
        elif calls:
            value |= {f"call:{c.get('callee', '?')}" for c in calls}
        if not value and not st.get("uses"):
            value = {"const"}
        new = dict(env)
        for d in defs:
            if d != "_":
                new[d] = frozenset(value)
        for s in st.get("stores") or []:
            self.facts.stores.append(
                {"path": s, "line": st["line"], "requires": _req(req), "origins": sorted(value)}
            )
        return new

    def block(self, stmts: list[dict[str, Any]], env: Env, req: Req) -> tuple[Env, bool]:
        for st in stmts:
            k = st.get("k")
            if k in ("assign", "expr"):
                env = self.assign(st, env, req)
            elif k in ("return", "raise"):
                env = self.call_facts(st.get("calls") or [], env, req, st["line"])
                if k == "return":
                    self.facts.returns.append(
                        {
                            "line": st["line"],
                            "requires": _req(req),
                            "origins": self.origins(st.get("uses") or [], env)
                            + [f"call:{c.get('callee', '?')}" for c in st.get("calls") or []],
                        }
                    )
                return env, True
            elif k == "break":
                return env, True  # leaves the enclosing loop body
            elif k == "if":
                env = self.call_facts(st.get("calls") or [], env, req, st["line"])
                site = st["site"]
                rec = {
                    "site": site,
                    "span": st.get("span"),
                    "pred": st.get("pred", ""),
                    "line": st["line"],
                    "order": self.order,
                    "requires": _req(req),
                    "operands": [
                        {"path": p, "origins": sorted(self.resolve(p, env))}
                        for p in st.get("uses") or []
                    ],
                    "operand_calls": [c.get("callee", "?") for c in st.get("calls") or []],
                }
                self.order += 1
                self.facts.sites.append(rec)
                t_env, t_exit = self.block(st.get("then") or [], dict(env), (*req, (site, True)))
                e_env, e_exit = self.block(st.get("else") or [], dict(env), (*req, (site, False)))
                rec["then_exits"], rec["else_exits"] = t_exit, e_exit
                if t_exit and e_exit:
                    return env, True
                if t_exit:
                    env, req = e_env, (*req, (site, False))
                elif e_exit:
                    env, req = t_env, (*req, (site, True))
                else:
                    env = _join(t_env, e_env)
            elif k == "loop":
                env = self.call_facts(st.get("calls") or [], env, req, st["line"])
                inner = dict(env)
                for d in st.get("defs") or []:
                    inner[d] = frozenset({f"unknown:{UNKNOWN}:loop-variable"})
                b_env, _ = self.block(st.get("body") or [], inner, (*req, ("?loop", None)))
                env = _join(env, _taint(b_env, env, "assigned-in-loop"))
            elif k == "with":
                env = self.call_facts(st.get("calls") or [], env, req, st["line"])
                env = dict(env)
                for d in st.get("defs") or []:
                    env[d] = frozenset(
                        {f"call:{c.get('callee', '?')}" for c in st.get("calls") or []}
                    ) or frozenset({"const"})
                env, exited = self.block(st.get("body") or [], env, req)
                if exited:
                    return env, True
            elif k == "try":
                b_env, _ = self.block(st.get("body") or [], dict(env), req)
                h_envs = [
                    self.block(h, dict(env), (*req, ("?exception-handler", None)))[0]
                    for h in st.get("handlers") or []
                ]
                env = _join(b_env, *h_envs) if h_envs else b_env
                env, _ = self.block(st.get("final") or [], env, req)
            else:  # opaque: switch/select/match/goto/nested defs
                self.facts.unknown.append({"line": st.get("line"), "reason": st.get("reason", k)})
                for blk in st.get("blocks") or []:
                    b_env, _ = self.block(blk, dict(env), (*req, (f"?{st.get('reason', k)}", None)))
                    env = _join(env, _taint(b_env, env, st.get("reason", "opaque")))
        return env, False


def _join(*envs: Env) -> Env:
    out: dict[str, frozenset[str]] = {}
    for e in envs:
        for k, v in e.items():
            out[k] = out.get(k, frozenset()) | v
    return out


def _taint(inner: Env, outer: Env, reason: str) -> Env:
    """Definitions made inside a loop or opaque region may or may not have happened."""
    out = dict(inner)
    for k, v in inner.items():
        if outer.get(k) != v:
            out[k] = v | {f"unknown:{UNKNOWN}:{reason}"}
    return out


def analyze(fn: dict[str, Any]) -> Facts:
    a = _Analyzer(fn)
    a.block(fn.get("body") or [], {}, ())
    return a.facts


def analyze_all(functions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [analyze(f).to_json() for f in functions]


def requirement_of(facts: dict[str, Any], callee_suffix: str) -> list[list[list[Any]]]:
    """The control requirements of every call in `facts` whose callee ends with the suffix."""
    return [
        c["requires"]
        for c in facts["calls"]
        if c["callee"] == callee_suffix or c["callee"].endswith("." + callee_suffix)
    ]
