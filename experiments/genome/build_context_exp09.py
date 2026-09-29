# ruff: noqa: E501
"""Experiment 09 bundle: deterministic mechanics + observed state/branch event logs.

usage: build_context_exp09.py <run-dir> <repo> <out-dir>
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from diffgenome.model import CallNode, SubstitutionNode
from diffgenome.serialize import execution_from_json

MODULE = "api.src.inference.model_manager"
SRC = "api/src/inference/model_manager.py"
TESTS = "api/tests/test_model_unload.py"
TEST_LINES = (1, 311)  # the ModelManager unit tests; endpoint tests are out of scope
HOLDOUT = [
    "test_generate_lazy_reinit_when_backend_none",
    "test_load_model_does_not_schedule_idle_unload_during_active_request",
    "test_unload_when_already_none_is_noop",
    "test_generate_schedules_idle_unload_when_enabled",
]
NOT_SCORED = ["test_ensure_backend_serializes_concurrent_reloads"]  # concurrency: deferred

INSTRUCTIONS = """\
# Task: propose the semantic layer of a Behavioral Genome for a stateful component

You are an abstraction engine. The component is `ModelManager` in Kokoro-FastAPI
(api/src/inference/model_manager.py): it loads, unloads and lazily re-initializes a model
backend, counts active requests, and schedules an idle-unload timer. Its behavior depends on
internal state and changes that state.

Deterministic machinery has ALREADY established the mechanics below. Do not re-derive them
and do not contradict them:
- every decision site (`if`) with a stable id `br:...`, its source predicate, the origins
  of its operands (local def-use), and the (site, outcome) pairs required to reach it;
- for every call and field store: which (site, outcome) pairs it requires;
- for the tests shown: the ordered event log of manager calls, the observed outcome of every
  decision site (T/F), and the bucketed state of the manager before and after each call
  (value-free buckets: none, obj:<Type>, obj:stand-in, num:zero/pos/neg, bool:true/false).

Your job is MEANING: name the state that matters, abstract the predicates, and give compact
rules that GENERATE the observed behavior, including behavior that depends on state set
by an earlier call. A machine will check everything you cite and assign status; you assign
none. Some tests' traces are withheld (listed below); you still see their source, and you
must write scenarios for them — they will be predicted from your genome and compared with
what actually executed.

Return ONLY one JSON object:

{
 "variables": [{"id", "name", "origin": "state|setting|input|derived", "description",
                "observed_as": {"fact": "<state fact name, e.g. self._backend or global.settings.model_auto_unload_timeout_seconds>",
                                "kind": "is_set|sign|bool"} | null,
                "definition": "<predicate over other variables>" | null,
                "evidence": [...]}],
 "decisions": [{"id", "entity": "<method, e.g. ModelManager.ensure_backend>", "site": "br:...",
                "inputs": [...], "predicate": "<over variable names>", "order": <int>,
                "true_branch":  {"steps": [...], "calls": [...], "absent": [...], "stops": bool, "effect": "..."},
                "false_branch": {...}, "evidence": [...]}],
 "transitions": [{"id", "entity": "<method>", "when": "<predicate or true>", "sets": {"<variable>": "<expr>"},
                  "state_before", "action", "state_after", "evidence": [...]}],
 "procedures": [{"id", "entity": "<method>", "steps": ["call:<method>", "T:<transition id>", "D:<decision id>", ...],
                 "evidence": [...]}],
 "rules": [{"id", "name", "inputs", "relevant_state", "condition", "consequences": [...], "decision": "<id>|null", "evidence": [...]}],
 "regimes": [{"id", "name", "facts": {...}, "members": ["<test name>"], "evidence": [...]}],
 "scenarios": {"<test name>": {"state": {<variable>: value}, "calls": [{"entity": "<method>", "facts": {<variable>: value}}]}},
 "unknowns": [{"what", "why"}]
}

Semantics used by the predictor:
- A call of an entity runs its procedure's steps in order. "call:X" records a call and, if X
  has a procedure, runs it; "T:id" applies a transition (if `when` holds, each variable in
  `sets` becomes the expression: literals true/false/none/integers, `var`, `!var`,
  `var + k`, `var - k`, `max(0, var - k)`); "D:id" evaluates a decision and runs the taken
  branch's `steps` (or, if empty, its `calls` as "call:" steps); a branch with `stops: true`
  ends the entity. Decisions evaluate `predicate` over the current variable values
  (booleans/integers; `!name`, comparisons, `&&`, `||`, no parentheses).
- Variables bound with `observed_as` are compared with the observed bucketed state
  (is_set: bucket != none; sign: num:zero/pos/neg as 0/positive/negative; bool).
- A scenario's `state` is the state the test establishes before its first manager call
  (including direct assignments like `manager._backend = MagicMock()` and settings set by
  monkeypatch); `calls` are the test's top-level manager calls and external events in
  order (e.g. an idle timer firing after `await asyncio.sleep(...)` is a call of
  `ModelManager._idle_unload_after`). The predicted decision outcomes must equal the
  observed outcomes at your decision sites, in order, and the predicted final values of
  bound variables must equal the observed final state.
- Use only the site ids given. Evidence ref kinds (JSON):
  {"kind":"source","file":"api/src/inference/model_manager.py","line":N,"text":"<exact text>"}
  {"kind":"branch","site":"br:...","test":"<shown test name>","outcome":true|false}
  {"kind":"control","site":"br:...","outcome":true|false,"callee":"<call expression or method>"}
  {"kind":"dataflow","site":"br:...","origin":"<e.g. param:self._backend>"}
  {"kind":"delta","entity":"<method>","fact":"self._backend","before":"obj:stand-in","after":"none","test":"<shown test name>"}
  {"kind":"store","entity":"<method>","path":"self._backend"}
  Cite only shown tests in evidence.
- Prefer few, generative rules. Be honest in `unknowns` about what the evidence cannot settle.
"""


def main() -> int:
    run, repo, out = (Path(a) for a in sys.argv[1:4])
    out.mkdir(parents=True, exist_ok=True)
    mech = json.loads((run / "mechanics.json").read_text())["functions"]
    mm = [f for f in mech if f["symbol"].startswith(f"py:{MODULE}.")]
    site_pred = {s["site"]: s["pred"] for f in mm for s in f["sites"]}
    parts = [INSTRUCTIONS]
    lines = []
    for f in mm:
        name = f["symbol"].split(f"{MODULE}.", 1)[1]
        if not (f["sites"] or f["stores"]):
            lines.append(f"### {name}\n(no decision site, no field store)\n")
            continue
        lines.append(f"### {name}")
        for s in f["sites"]:
            ops = "; ".join(f"{o['path']} ← {', '.join(o['origins'])}" for o in s["operands"])
            req = (
                " & ".join(
                    f"{r[0]}={'T' if r[1] else 'F'}" if r[1] is not None else r[0]
                    for r in s["requires"]
                )
                or "—"
            )
            lines.append(
                f"- site {s['site']} line {s['line']}: `{s['pred']}` | operands: {ops} | requires: {req} | then-block exits: {s['then_exits']}, else-block exits: {s['else_exits']}"
            )
        for c in f["calls"]:
            req = (
                " & ".join(
                    f"{r[0]}={'T' if r[1] else 'F'}" if r[1] is not None else r[0]
                    for r in c["requires"]
                )
                or "—"
            )
            lines.append(f"- call `{c['callee']}` line {c['line']} requires: {req}")
        for st in f["stores"]:
            req = (
                " & ".join(
                    f"{r[0]}={'T' if r[1] else 'F'}" if r[1] is not None else r[0]
                    for r in st["requires"]
                )
                or "—"
            )
            lines.append(
                f"- store `{st['path']}` ← {', '.join(st['origins'])} line {st['line']} requires: {req}"
            )
        lines.append("")
    parts.append("## Mechanics (deterministic, intra-procedural)\n\n" + "\n".join(lines))

    logs = []
    shown, held = [], []
    for fpath in sorted((run / "traces-existing").glob("*.json")):
        ex = execution_from_json(fpath.read_text())
        test = ex.stimulus_ref.split("::")[-1]
        if (
            not ex.stimulus_ref.startswith(TESTS)
            or not test.startswith("test_")
            or "endpoint" in test
        ):
            continue
        if test in HOLDOUT:
            held.append(test)
            continue
        shown.append(test)
        out_lines = [f"### {test}" + ("  (not scored: concurrency)" if test in NOT_SCORED else "")]

        # chronological: nodes by creation order, branches by their seq, depth = number
        # of manager ancestors (non-manager frames are looked through)
        def mgr_depth(nid: int, ex=ex) -> int:  # type: ignore[no-untyped-def]
            d, p = 0, ex.nodes[nid].parent
            while p is not None:
                pn = ex.nodes[p]
                if isinstance(pn, CallNode) and pn.symbol.startswith(f"py:{MODULE}."):
                    d += 1
                p = pn.parent
            return d

        events = [(n.id, 1, n) for n in ex.nodes] + [(b.seq, 0, b) for b in ex.branches]
        for _, kind, obj in sorted(events, key=lambda e: (e[0], e[1])):
            if kind == 0:
                if obj.site in site_pred:
                    d = mgr_depth(obj.node) + (
                        1
                        if isinstance(ex.nodes[obj.node], CallNode)
                        and ex.nodes[obj.node].symbol.startswith(f"py:{MODULE}.")
                        else 0
                    )
                    out_lines.append(
                        f"{'  ' * d}branch {obj.site} `{site_pred[obj.site][:70]}` = {'T' if obj.outcome else 'F'}"
                    )
                continue
            c = obj
            pad = "  " * mgr_depth(c.id)
            if isinstance(c, CallNode) and c.symbol.startswith(f"py:{MODULE}."):
                nm = c.symbol.split(f"{MODULE}.", 1)[1]
                before = {a: b for a, b, _ in c.state}
                after = {a: b for a, b, _ in c.state_after}
                delta = [
                    f"{k}: {before.get(k, '∅')}→{after[k]}"
                    for k in after
                    if before.get(k) != after[k] and k.startswith(("self.", "global."))
                ]
                st = [
                    f"{k}={v}"
                    for k, v in sorted(before.items())
                    if k
                    in (
                        "self._backend",
                        "self._active_requests",
                        "self._idle_unload_task",
                        "self._last_used_at",
                    )
                    or k.startswith("global.settings.")
                ]
                out_lines.append(
                    f"{pad}call {nm}  [{c.outcome.split(':')[0]}]  state-in: {', '.join(st) or '—'}"
                    + (f"  Δ {'; '.join(delta)}" if delta else "")
                )
            elif (
                isinstance(c, SubstitutionNode) and c.claimed_target and MODULE in c.claimed_target
            ):
                out_lines.append(
                    f"{pad}call {c.claimed_target.split(MODULE + '.', 1)[1]} (stand-in, not executed)  [{c.outcome.split(':')[0]}]"
                )
        logs.append("\n".join(out_lines))
    parts.append(
        "## Observed event logs (shown tests)\n\nManager calls in chronological order, indented by manager call depth, each decision site's observed "
        "outcome where it was evaluated, the manager's bucketed state on entry, and the observed state deltas (Δ) on exit. "
        "Calls into non-manager code are looked through.\n\n```\n"
        + "\n\n".join(logs)
        + "\n```\n\nWithheld (observed, not shown): "
        + ", ".join(held)
        + "\n"
    )
    src = (repo / SRC).read_text().splitlines()
    parts.append(
        f"## Source: {SRC}\n\n```python\n"
        + "\n".join(f"{i:4d}  {ln}" for i, ln in enumerate(src, 1))
        + "\n```\n"
    )
    tsrc = (repo / TESTS).read_text().splitlines()[TEST_LINES[0] - 1 : TEST_LINES[1]]
    parts.append(
        f"## Source: {TESTS} (lines {TEST_LINES[0]}-{TEST_LINES[1]})\n\n```python\n"
        + "\n".join(f"{i:4d}  {ln}" for i, ln in enumerate(tsrc, TEST_LINES[0]))
        + "\n```\n"
    )
    bundle = "\n".join(parts)
    (out / "context-bundle.md").write_text(bundle)
    digest = hashlib.sha256(bundle.encode()).hexdigest()[:16]
    (out / "context-bundle.sha").write_text(digest + "\n")
    (out / "holdout.json").write_text(
        json.dumps({"holdout": held, "shown": shown, "not_scored": NOT_SCORED}, indent=1) + "\n"
    )
    print(
        f"bundle {len(bundle)} chars, {bundle.count(chr(10))} lines, sha {digest}; shown {len(shown)}, withheld {len(held)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
