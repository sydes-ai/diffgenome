"""Runtime evidence about a change: the stable contract consumers depend on.

`diffgenome-runtime/1` reports only facts the collectors observed while the repository's own
tests ran against the change, plus the static decision sites needed to place branch outcomes on
changed lines. No model and no genome are involved. A consumer (Sydes) reads this section of the
change artifact; it never needs the trace files, the mechanics file or DiffGenome internals.

Per changed function (a changed symbol whose definition is a function):
  executed / not executed (including at import or test collection: `ran_at_import`, which no
  test is credited with), number of calls, the exact tests (subtests included) that ran it,
  exits observed (returned, returned-error, raised:<type>, ...), exceptions raised by calls made
  inside it, distinct argument type shapes, its nearest observed callers, the stand-ins (mocks,
  fakes) it reached, and the outcomes observed at every decision site on a changed line.
Edges: observed caller -> callee pairs on the call chains that reached changed functions, with
  closures, lambdas and decorator wrappers looked through, each end located (file, line).
  The caller is the innermost instrumented frame active when the callee was entered. That is
  not by itself proof of a direct call: uninstrumented code (a framework, a library) running in
  between is invisible. An edge or caller carries `relation` only when its relationship was
  positively classified; a missing `relation` means unspecified (legacy), never "direct" and
  never "within". The one value today:
    "through_external": the caller invoked external code (`via`: symbol, origin, owner,
    member, arg_shapes, exits) and the callee was entered while that invocation was active.
    The external code is never itself reported as a caller; it did not necessarily call the
    callee. Recorded only by collectors that keep external bridges (Node, behind
    DIFFGENOME_EXTERNAL_BRIDGES).
Boundaries: where observation stopped (external, unresolved stand-in).
Gaps: changed functions no test executed, changed-line decision outcomes never observed, and
  stand-ins reached directly from changed code. Coverage is never inferred: only these
  observable kinds are reported.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from typing import Any

from diffgenome.change import ChangeSet
from diffgenome.model import CallNode, Execution, SubstitutionNode
from diffgenome.runtime import SymbolIndex

FORMAT = "diffgenome-runtime/1"
from diffgenome.collect.import_phase import IMPORT_REF  # noqa: E402  (no pytest import)

MAX_TESTS = 200
MAX_SHAPES = 5
MAX_CALLERS = 12
MAX_EDGE_TESTS = 5
_WRAPPER_MARKERS = ("<locals>", "<lambda>", "<anon>")
_JS_BRIDGE_PREFIX = "js:external:"


def _is_wrapper(symbol: str) -> bool:
    return any(m in symbol for m in _WRAPPER_MARKERS)


def _bridge_parts(symbol: str) -> tuple[str | None, str | None]:
    """Owner and member of an external bridge symbol. The Node runtime writes
    `js:external:<Owner>.<member>` with a dot-free owner (a class name), so the first dot
    separates them; any other symbol shape yields (None, None) rather than a guess."""
    if not symbol.startswith(_JS_BRIDGE_PREFIX):
        return None, None
    owner, dot, member = symbol[len(_JS_BRIDGE_PREFIX) :].partition(".")
    return (owner, member) if dot and owner and member else (None, None)


def _changed_functions(change: ChangeSet, index: SymbolIndex) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for s in change.symbols:
        d = index.find(s)
        # application code only: changed tests (and closures inside them) are stimuli, not
        # behavior under change
        if d is not None and d.kind == "function" and not index.is_test(s):
            out[s] = {"file": d.path, "line": d.start, "end": d.end}
    return out


def _changed_lines(change: ChangeSet) -> dict[str, set[int]]:
    lines: dict[str, set[int]] = defaultdict(set)
    for r in change.ranges:
        lines[r.path].update(r.lines)
    return lines


def build_runtime_evidence(
    executions: Iterable[Execution],
    change: ChangeSet,
    index: SymbolIndex,
    mechanics_functions: list[dict[str, Any]] | None = None,
    boundaries: list[dict[str, Any]] | None = None,
    test_scope: str | None = None,
    stopped_early: str | None = None,
) -> dict[str, Any]:
    """`test_scope` names what was run (e.g. a test directory or package): every "not
    executed" statement is relative to it. `stopped_early` says why the run ended before
    all of it ran (a sandbox limit): "not executed" then also covers "not reached"."""
    execs = list(executions)
    changed = _changed_functions(change, index)
    lines = _changed_lines(change)
    mech = {f["symbol"]: f for f in mechanics_functions or []}

    calls: Counter[str] = Counter()
    tests: dict[str, set[str]] = defaultdict(set)
    exits: dict[str, Counter[str]] = defaultdict(Counter)
    raised_inside: dict[str, Counter[str]] = defaultdict(Counter)
    shapes: dict[str, Counter[tuple[tuple[str, str], ...]]] = defaultdict(Counter)
    # a caller is keyed with the external bridge it was reached through (None: legacy)
    callers: dict[str, Counter[tuple[str, str | None]]] = defaultdict(Counter)
    caller_tests: dict[tuple[str, str, str | None], set[str]] = defaultdict(set)
    # what each bridge was seen as, per relationship: argument shapes and exits
    via_shapes: dict[tuple[str, ...], Counter[tuple[str, ...]]] = defaultdict(Counter)
    via_exits: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    stand_ins: dict[str, Counter[str]] = defaultdict(Counter)
    site_out: dict[str, Counter[bool]] = defaultdict(Counter)
    edges: dict[tuple[str, str, str | None], set[str]] = defaultdict(set)
    edge_count: Counter[tuple[str, str, str | None]] = Counter()
    locations: dict[str, tuple[str, int] | None] = {}
    origins: dict[str, str] = {}
    universe = []

    import_calls: Counter[str] = Counter()
    for ex in execs:
        if ex.stimulus_ref == IMPORT_REF:
            # import and collection time (pytest_launch): executed, but by no test
            for n in ex.nodes:
                if isinstance(n, CallNode) and n.symbol in changed:
                    import_calls[n.symbol] += 1
            continue
        universe.append(ex.stimulus_ref)
        for symbol_rec in ex.symbols:
            origins.setdefault(symbol_rec.id, symbol_rec.origin.value)
            if symbol_rec.location is not None:
                locations.setdefault(
                    symbol_rec.id, (symbol_rec.location.path, symbol_rec.location.line)
                )
        nodes = {n.id: n for n in ex.nodes}

        def is_bridge(n: Any) -> bool:
            # an external call node kept because repo/test code ran inside it
            return isinstance(n, CallNode) and origins.get(n.symbol) == "external"

        def parent_via(n: Any, nodes: dict[int, Any] = nodes) -> tuple[CallNode | None, Any]:
            """The real caller, looking through wrappers and an external bridge, and the
            bridge it was reached through (None when there was none)."""
            via = None
            p = nodes.get(n.parent) if n.parent is not None else None
            while isinstance(p, CallNode) and (_is_wrapper(p.symbol) or is_bridge(p)):
                if via is None and is_bridge(p):
                    via = p
                p = nodes.get(p.parent) if p.parent is not None else None
            return (p if isinstance(p, CallNode) else None), via

        def real_parent(n: Any) -> CallNode | None:
            return parent_via(n)[0]

        def note_via(key: tuple[str, ...], via: CallNode) -> None:
            via_shapes[key][tuple(a[1] for a in via.args)] += 1
            via_exits[key][str(via.outcome)] += 1

        for n in ex.nodes:
            if isinstance(n, SubstitutionNode):
                p = real_parent(n)
                if p is not None and p.symbol in changed:
                    target = n.claimed_target or n.substitute or "?"
                    stand_ins[p.symbol][str(target)] += 1
                continue
            if not isinstance(n, CallNode) or is_bridge(n):
                continue  # a bridge is reported as `via` on what it reached, never by itself
            p, via = parent_via(n)
            if (
                p is not None
                and p.symbol in changed
                and str(n.outcome).startswith(("raised", "panic", "returned-error"))
            ):
                raised_inside[p.symbol][str(n.outcome)] += 1
            if n.symbol not in changed:
                continue
            calls[n.symbol] += 1
            tests[n.symbol].add(ex.stimulus_ref)
            exits[n.symbol][str(n.outcome)] += 1
            shapes[n.symbol][tuple((a[0], a[1]) for a in n.args)] += 1
            if p is not None:
                vs = via.symbol if via is not None else None
                callers[n.symbol][(p.symbol, vs)] += 1
                caller_tests[(n.symbol, p.symbol, vs)].add(ex.stimulus_ref)
                if via is not None:
                    note_via(("caller", n.symbol, p.symbol, via.symbol), via)
            # the observed chain into this changed call, wrappers (and bridges) looked through
            child: Any = n
            while True:
                parent, edge_via = parent_via(child)
                if parent is None:
                    break
                ev_sym = edge_via.symbol if edge_via is not None else None
                key = (parent.symbol, child.symbol, ev_sym)
                if key[0] != key[1]:
                    edges[key].add(ex.stimulus_ref)
                    edge_count[key] += 1
                    if edge_via is not None:
                        note_via(("edge", *key[:2], edge_via.symbol), edge_via)
                child = parent
        for b in ex.branches:
            site_out[b.site][b.outcome] += 1

    outcomes = {ex.stimulus_ref: ex.outcome for ex in execs if ex.stimulus_ref != IMPORT_REF}

    def loc(symbol: str) -> dict[str, Any]:
        """Where a symbol is defined, and its origin (repo, test, ...) as observed."""
        where = locations.get(symbol)
        d = index.find(symbol)
        origin = "test" if index.is_test(symbol) else origins.get(symbol, "unknown")
        if d is not None:
            return {"symbol": symbol, "file": d.path, "line": d.start, "origin": origin}
        return {
            "symbol": symbol,
            "file": where[0] if where else None,
            "line": where[1] if where else None,
            "origin": origin,
        }

    def related(
        entry: dict[str, Any], kind: str, a: str, b: str, via: str | None
    ) -> dict[str, Any]:
        """`entry` unchanged when no bridge was crossed; else with relation and via."""
        if via is None:
            return entry
        owner, member = _bridge_parts(via)
        key = (kind, a, b, via)
        return {
            **entry,
            "relation": "through_external",
            "via": {
                "symbol": via,
                "origin": origins.get(via, "external"),
                "owner": owner,
                "member": member,
                "arg_shapes": [list(s) for s, _ in via_shapes[key].most_common(MAX_SHAPES)],
                "exits": dict(via_exits[key]),
            },
        }

    functions = []
    gaps: list[dict[str, Any]] = []
    for sym, info in sorted(changed.items()):
        f = mech.get(sym)
        cl = lines.get(info["file"], set())
        sites = [
            {
                "site": s["site"],
                "line": s["line"],
                "predicate": s["pred"],
                "true": site_out[s["site"]].get(True, 0),
                "false": site_out[s["site"]].get(False, 0),
            }
            for s in (f["sites"] if f else [])
            if s["line"] in cl
        ]
        executed = calls[sym] > 0 or import_calls[sym] > 0
        functions.append(
            {
                **loc(sym),
                "executed": executed,
                "calls": calls[sym],
                "tests": sorted(tests[sym])[:MAX_TESTS],
                "tests_total": len(tests[sym]),
                "ran_at_import": import_calls[sym] > 0,
                "exits": dict(exits[sym]),
                "raised_inside": dict(raised_inside[sym]),
                "arg_shapes": [
                    [list(a) for a in shape] for shape, _ in shapes[sym].most_common(MAX_SHAPES)
                ],
                "callers": [
                    related(
                        {**loc(c), "calls": k, "tests": len(caller_tests[(sym, c, v)])},
                        "caller", sym, c, v,
                    )
                    for (c, v), k in callers[sym].most_common(MAX_CALLERS)
                ],
                "stand_ins": dict(stand_ins[sym]),
                "changed_sites": sites,
            }
        )
        if not executed:
            gaps.append({"kind": "function_not_executed", **loc(sym)})
            continue
        for s in sites:
            missing = [o for o, k in (("true", s["true"]), ("false", s["false"])) if k == 0]
            if len(missing) == 2:
                gaps.append(
                    {
                        "kind": "branch_not_evaluated",
                        **loc(sym),
                        "line": s["line"],
                        "predicate": s["predicate"],
                    }
                )
            elif missing:
                gaps.append(
                    {
                        "kind": "branch_outcome_not_observed",
                        **loc(sym),
                        "line": s["line"],
                        "predicate": s["predicate"],
                        "outcome": missing[0],
                    }
                )
        for target, k in stand_ins[sym].items():
            gaps.append({"kind": "stand_in_reached", **loc(sym), "target": target, "calls": k})

    return {
        "format": FORMAT,
        "universe": {
            "test_scope": test_scope,
            "stopped_early": stopped_early,
            "executions": len(universe),
            "passed": sum(1 for o in outcomes.values() if o == "passed"),
            # skipped tests are not failures (falcon #2731 counted 90 skips as failed)
            "failed": sum(1 for o in outcomes.values() if o not in ("passed", "skipped")),
            "skipped": sum(1 for o in outcomes.values() if o == "skipped"),
            # tracer callbacks that failed and were contained (the program was not affected,
            # but the observation is incomplete where they happened)
            "tracer_errors": sum(
                int(v) for ex in execs for k, v in ex.diagnostics if k == "tracer_errors"
            ),
            # Python child processes the tests started: code they ran was not observed, so
            # "not executed" may be wrong for it (glances #3770 starts its server this way)
            "untraced_python_subprocesses": sum(
                int(v) for ex in execs for k, v in ex.diagnostics if k == "python_subprocesses"
            ),
            "tests": [{"id": t, "outcome": outcomes[t]} for t in sorted(outcomes)][:2000],
        },
        "changed_functions": functions,
        "edges": [
            related(
                {
                    "caller": loc(a),
                    "callee": loc(b),
                    "executions": edge_count[(a, b, v)],
                    "tests": sorted(edges[(a, b, v)])[:MAX_EDGE_TESTS],
                    "tests_total": len(edges[(a, b, v)]),
                },
                "edge", a, b, v,
            )
            for (a, b, v) in sorted(edges, key=lambda k: (k[0], k[1], k[2] or ""))
        ],
        "boundaries": [
            {
                "kind": b.get("kind"),
                "caller": b.get("caller"),
                "target": b.get("target"),
                "tests": len(b.get("executions") or []),
            }
            for b in boundaries or []
        ],
        "gaps": gaps,
        "not_reported": [
            "values (only type shapes and opaque fingerprints are recorded)",
            "except-handler coverage (handlers are not decision sites)",
            "per-line coverage",
        ],
    }
