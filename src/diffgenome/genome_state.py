"""Genome checking and prediction over the stronger substrate (experiment 09).

Adds to `diffgenome.genome`:
- `Mechanics`: deterministic intra-procedural facts (decision sites, local def-use, control
  requirements, field stores) from `diffgenome.dependence`, keyed by site id;
- `Observations`: per execution, observed branch outcomes at sites and bucketed state on
  entry and exit (observed state deltas);
- `establish_state()`: status for decisions anchored at sites, transitions, procedures, and
  the new evidence kinds (branch / control / dataflow / delta / store). The checker remains
  the only authority on status;
- path conditions: an execution's branch vector over genome sites, with the site's source
  predicate attached;
- `predict_sequence()`: state-dependent prediction over a sequence of calls, where
  transitions change state and later decisions read it. Anything unestablished that a
  prediction needs stops it as indeterminate; nothing is skipped.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from diffgenome.genome import (
    HYPOTHESIS,
    OBSERVED,
    REJECTED,
    STATIC,
    SUPPORTED,
    VERIFIED,
    Decision,
    EvidenceRef,
    Genome,
    Item,
    Substrate,
    derive,
    eval_predicate,
)
from diffgenome.model import CallNode, Execution

RANK = {REJECTED: -1, HYPOTHESIS: 0, SUPPORTED: 1, VERIFIED: 2, STATIC: 2, OBSERVED: 3}


def _name_match(claimed: str, symbol: str) -> bool:
    """`ensure_backend` or `ModelManager.ensure_backend` matches
    `py:...ModelManager.ensure_backend`."""
    claimed = claimed.split(":", 1)[1] if claimed[:3] in ("go:", "py:", "js:") else claimed
    tail = symbol.split(":", 1)[-1]
    return tail == claimed or tail.endswith("." + claimed)


def _callee_match(claimed: str, callee: str) -> bool:
    """A claimed entity against a call expression (`self._backend.unload`)."""
    last = claimed.rsplit(".", 1)[-1]
    return callee in (claimed, last) or callee.endswith("." + last)


# --------------------------------------------------------------------------- boundary facts


def _d(canonical: str) -> str:
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


# Collectors digest values as sha256(canonical)[:16]; the canonical forms of "no value"
# (Python None, Go nil, JS null/undefined) and of booleans are known, so these facts are
# decidable from digests alone, without capturing any value.
NULL_DIGESTS = frozenset({_d("NoneType:None"), _d("nil"), _d("null"), _d("undefined")})
NULL_SHAPES = frozenset({"NoneType", "nil", "null", "undefined"})
BOOL_DIGESTS = {
    _d("bool:True"): True, _d("bool:False"): False,  # Python
    _d("bool:true"): True, _d("bool:false"): False,  # Go
    _d("boolean:true"): True, _d("boolean:false"): False,  # JS
}  # fmt: skip


def boundary_fact(node: Any, point: str, kind: str) -> Any:
    """An identity-level fact at a call boundary, or None when not decidable.

    point: "arg:<name>" | "result". kind:
      is_set                  the value is not null/none/nil
      changed_from:arg:<name> the value differs from that argument (digest inequality)
      size                    the collection's size (argument shapes carry it)
      bool                    a boolean, decoded from its digest"""
    if not isinstance(node, CallNode):
        return None
    args = {a: (shape, dg) for a, shape, dg in node.args}
    if point == "result":
        shape, dg = None, node.result
    elif point.startswith("arg:") and point[4:] in args:
        shape, dg = args[point[4:]]
    else:
        return None
    if kind == "is_set":
        if shape is not None:
            return shape.split("[", 1)[0] not in NULL_SHAPES
        return (dg not in NULL_DIGESTS) if dg else None
    if kind.startswith("changed_from:"):
        src = kind.split(":", 1)[1]
        if not src.startswith("arg:") or src[4:] not in args:
            return None
        other = args[src[4:]][1]
        return (dg != other) if dg and other else None
    if kind == "size":
        m = re.fullmatch(r"[^\[]*\[(\d+)\]", shape or "")
        return int(m.group(1)) if m else None
    if kind == "bool":
        return BOOL_DIGESTS.get(dg or "")
    return None


def _exit_point(kind: str, point: str) -> bool:
    """Result facts and change facts describe the call's exit; argument facts its entry."""
    return point == "result" or kind.startswith("changed_from:")


def exit_matches(claim: str, observed: str) -> bool | None:
    """A claimed exit (`returned`, `returned-error[:kind]`, `raised[:kind]`, `panic[:kind]`,
    `cancelled`; `completed` = `returned`) against a call's observed outcome (model.Outcome).
    A kind matches the observed identity exactly or as its dotted suffix. None if unknown."""
    if not observed or observed == "unknown":
        return None
    claim = claim.replace("returned_error", "returned-error")
    claim = "returned" if claim == "completed" else claim
    c_cat, _, c_kind = claim.partition(":")
    o_cat, _, o_kind = observed.partition(":")
    if c_cat != o_cat:
        return False
    if not c_kind:
        return True
    o_kind = o_kind.split(":", 1)[1] if o_kind[:3] in ("py:", "go:", "js:") else o_kind
    return o_kind == c_kind or o_kind.endswith("." + c_kind)


def _enclosing_call(ob: ExecObs, node_id: int, entity: str) -> Any:
    n: Any = ob.execution.nodes[node_id] if node_id < len(ob.execution.nodes) else None
    while n is not None:
        if isinstance(n, CallNode) and _name_match(entity, n.symbol):
            return n
        n = ob.execution.nodes[n.parent] if n.parent is not None else None
    return None


# --------------------------------------------------------------------------- mechanics


class Mechanics:
    def __init__(self, functions: list[dict[str, Any]]) -> None:
        self.functions = functions
        self.sites: dict[str, dict[str, Any]] = {}
        for f in functions:
            for s in f["sites"]:
                self.sites[s["site"]] = {**s, "symbol": f["symbol"], "file": f["file"]}

    def function_of(self, site: str) -> dict[str, Any] | None:
        sym = self.sites.get(site, {}).get("symbol")
        return next((f for f in self.functions if f["symbol"] == sym), None)

    def functions_named(self, entity: str) -> list[dict[str, Any]]:
        return [f for f in self.functions if _name_match(entity, f["symbol"])]

    def site_at(self, file: str, line: int, entity: str | None = None) -> list[str]:
        """Sites whose condition spans `line` of `file`, preferring the entity's function."""
        hits = [
            s["site"]
            for s in self.sites.values()
            if s["file"] == file and s["span"] and s["span"][0] <= line <= s["span"][2]
        ]
        if entity:
            own = [h for h in hits if _name_match(entity, self.sites[h]["symbol"])]
            if own:
                return own
        return hits

    def reachable_under(self, site: str, outcome: bool, callee: str) -> bool | None:
        """In the site's function: can a call of `callee` run after the site takes
        `outcome`? A call qualifies when it lies after the site or inside its `outcome`
        branch, and none of its requirements conflicts with the site's own requirements
        plus (site, outcome). None when the function has no call after the site to judge."""
        fn = self.function_of(site)
        rec = self.sites.get(site)
        if fn is None or rec is None:
            return None
        ctx = {(s, o) for s, o in rec["requires"]} | {(site, outcome)}
        end_line = rec["span"][2] if rec.get("span") else rec["line"]
        candidates = []
        for c in fn["calls"]:
            if not _callee_match(callee, c["callee"]):
                continue
            req = {(s, o) for s, o in c["requires"]}
            if (
                c["line"] <= end_line
                and (site, outcome) not in req
                and (site, not outcome) not in req
            ):
                continue  # before the site: not a consequence of it
            candidates.append(req)
        if not candidates:
            return None
        return any(
            not any((s, not o) in ctx for s, o in req if o is not None) for req in candidates
        )

    def exits_under(self, site: str, outcome: bool) -> bool | None:
        rec = self.sites.get(site)
        if rec is None:
            return None
        return bool(rec["then_exits"] if outcome else rec["else_exits"])


# --------------------------------------------------------------------------- observations


@dataclass
class BranchEvent:
    site: str
    outcome: bool
    node: int
    seq: int
    symbol: str


@dataclass
class ExecObs:
    execution: Execution
    branches: list[BranchEvent] = field(default_factory=list)

    def children_of(self, node: int) -> dict[int, list[int]]:
        kids: dict[int, list[int]] = {}
        for n in self.execution.nodes:
            if n.parent is not None:
                kids.setdefault(n.parent, []).append(n.id)
        return kids

    def subtree_after(self, node: int, seq: int) -> list[str]:
        """Symbols of calls under `node` created at or after `seq`, then of calls under the
        node's caller created after `node` (the caller's continuation), in order."""
        kids = self.children_of(node)
        out: list[str] = []

        def walk(n: int, floor: int) -> None:
            for k in kids.get(n, []):
                if k >= floor:
                    nd = self.execution.nodes[k]
                    out.append(
                        getattr(nd, "symbol", None) or getattr(nd, "claimed_target", None) or ""
                    )
                    walk(k, 0)

        walk(node, seq)
        parent = self.execution.nodes[node].parent
        if parent is not None:
            walk(parent, node + 1)
        return out


class Observations:
    def __init__(self, executions: list[Execution]) -> None:
        self.by_test: dict[str, ExecObs] = {}
        for ex in executions:
            ob = ExecObs(ex)
            for b in ex.branches:
                sym = getattr(ex.nodes[b.node], "symbol", "") if b.node < len(ex.nodes) else ""
                ob.branches.append(BranchEvent(b.site, b.outcome, b.node, b.seq, sym))
            self.by_test[ex.stimulus_ref] = ob

    def get(self, test: str) -> ExecObs | None:
        if test in self.by_test:
            return self.by_test[test]
        hits = [
            v for k, v in self.by_test.items() if k.endswith("::" + test) or k.endswith("/" + test)
        ]
        return hits[0] if len(hits) == 1 else None

    def outcomes_at(self, site: str) -> dict[bool, list[str]]:
        out: dict[bool, list[str]] = {True: [], False: []}
        for test, ob in self.by_test.items():
            for b in ob.branches:
                if b.site == site and test not in out[b.outcome]:
                    out[b.outcome].append(test)
        return out


# --------------------------------------------------------------------------- checking


class StateSubstrate(Substrate):
    """Substrate with mechanics and observations; checks the new evidence kinds."""

    def __init__(self, base: Substrate, mech: Mechanics, obs: Observations) -> None:
        super().__init__(
            list(base.paths.values()), base.observed_edges, base.source_root, base.decision_sites
        )
        self.mech = mech
        self.obs = obs
        # sites evaluated at runtime; a site may be observed without static facts (a file or
        # nested function the front end did not lower): it exists, but is not anchored
        self.runtime_sites = {b.site for ob in obs.by_test.values() for b in ob.branches}

    def site_exists(self, site: str | None) -> bool:
        return bool(site) and (site in self.mech.sites or site in self.runtime_sites)

    def check(self, ref: EvidenceRef) -> None:
        k = ref.kind
        if k == "branch":
            ob = self.obs.get(ref.test or "")
            if ob is None:
                ref.ok, ref.why = False, f"no execution {ref.test!r}"
            elif not self.site_exists(ref.site):
                # nothing knows this site: missing support, not an observed contradiction
                ref.ok, ref.why, ref.unanchored = False, f"unknown site {ref.site}", True
            else:
                ref.ok = any(b.site == ref.site and b.outcome == ref.outcome for b in ob.branches)
                ref.why = "" if ref.ok else f"{ref.site} never evaluated to {ref.outcome} there"
            return
        if k == "control":
            r = self.mech.reachable_under(ref.site or "", bool(ref.outcome), ref.callee or "")
            ref.ok = r is True and (
                self.mech.reachable_under(ref.site or "", not ref.outcome, ref.callee or "")
                is False
            )
            ref.why = (
                "" if ref.ok else f"{ref.callee} is not controlled by {ref.site}={ref.outcome}"
            )
            return
        if k == "dataflow":
            rec = self.mech.sites.get(ref.site or "") or {}
            ref.ok = bool(rec) and any(
                (ref.origin or "") in o for op in rec.get("operands", []) for o in op["origins"]
            )
            ref.why = "" if ref.ok else f"no operand of {ref.site} originates at {ref.origin}"
            return
        if k == "boundary":
            ob = self.obs.get(ref.test or "")
            if ob is None:
                ref.ok, ref.why = False, f"no execution {ref.test!r}"
                return
            ref.ok = any(
                isinstance(n, CallNode)
                and _name_match(ref.entity or "", n.symbol)
                and boundary_fact(n, ref.point or "", ref.binding or "is_set") == ref.value
                for n in ob.execution.nodes
            )
            ref.why = (
                ""
                if ref.ok
                else f"no {ref.entity} call with {ref.point} {ref.binding} = {ref.value!r}"
            )
            return
        if k == "outcome":
            ob = self.obs.get(ref.test or "")
            if ob is None:
                ref.ok, ref.why = False, f"no execution {ref.test!r}"
                return
            ref.ok = any(
                isinstance(n, CallNode)
                and _name_match(ref.entity or "", n.symbol)
                and exit_matches(ref.exit or "", n.outcome) is True
                for n in ob.execution.nodes
            )
            ref.why = "" if ref.ok else f"no {ref.entity} call ending {ref.exit}"
            return
        if k == "store":
            ref.ok = any(
                any(st["path"] == ref.path for st in f["stores"])
                for f in self.mech.functions_named(ref.entity or "")
            )
            ref.why = "" if ref.ok else f"{ref.entity} has no store of {ref.path}"
            return
        if k == "delta":
            ob = self.obs.get(ref.test or "")
            if ob is None:
                ref.ok, ref.why = False, f"no execution {ref.test!r}"
                return
            ref.ok = False
            for n in ob.execution.nodes:
                if (
                    isinstance(n, CallNode)
                    and _name_match(ref.entity or "", n.symbol)
                    and n.state_after
                ):
                    before = {a: b for a, b, _ in n.state}
                    after = {a: b for a, b, _ in n.state_after}
                    if (
                        before.get(ref.fact or "") == ref.before
                        and after.get(ref.fact or "") == ref.after
                    ):
                        ref.ok = True
                        break
            ref.why = (
                "" if ref.ok else f"no {ref.entity} call with {ref.fact}: {ref.before}→{ref.after}"
            )
            return
        super().check(ref)


def _link_site(d: Decision, sub: StateSubstrate) -> tuple[str | None, str]:
    if d.site:
        if d.site in sub.mech.sites:
            return d.site, "given"
        if d.site in sub.runtime_sites:
            return d.site, "given; observed at runtime, no static facts"
        return None, f"unknown site {d.site}"
    cited = {
        s
        for r in d.evidence
        if r.kind == "source" and r.ok and r.file and r.line
        for s in sub.mech.site_at(r.file, r.line)
    }
    own = {s for s in cited if _name_match(d.entity, sub.mech.sites[s]["symbol"])}
    uniq = sorted(own or cited)  # the decision's own function first
    if len(uniq) == 1:
        return uniq[0], "linked by the only cited `if` line"
    return None, "no unique cited decision site" if not uniq else f"cites {len(uniq)} sites"


def _static_consistent(d: Decision, site: str, sub: StateSubstrate) -> list[str]:
    """Claimed consequences vs the site's static control facts. Only calls that exist in the
    site's function and lie after it are judged; 'stops' is not checked statically, since
    whether a genome-level step follows is not a local property."""
    problems: list[str] = []
    if site not in sub.mech.sites:
        return problems  # no static facts to be consistent with
    for b in (d.true_branch, d.false_branch):
        for c in b.calls:
            if _name_match(c, sub.mech.sites[site]["symbol"]):
                continue  # the deciding function itself
            if sub.mech.reachable_under(site, b.when, c) is False:
                problems.append(f"{c} unreachable when {site}={b.when}")
        for a in b.absent:
            if sub.mech.reachable_under(site, b.when, a) is True:
                problems.append(f"{a} reachable when {site}={b.when}")
    return problems


def _symbol(n: Any) -> str:
    return getattr(n, "symbol", None) or getattr(n, "claimed_target", None) or ""


def episode_calls(ob: ExecObs, ev: BranchEvent, mech: Mechanics) -> list[str]:
    """Calls that belong to the episode a branch evaluation decides, in order.

    Node ids and branch `seq` share one clock, so every bound is a time cut:
    - inside the deciding call: everything after the evaluation, up to the next evaluation
      of the same site in that call (the next loop iteration) and, when the site lies in a
      loop, up to the first direct call that the static facts place outside every loop
      (control has left the loop);
    - the caller's continuation only when the taken branch leaves the deciding function
      (static exit facts), up to the next call of the same function or the next
      evaluation of the site anywhere.
    Deferred callbacks and later iterations are therefore outside the episode; claims about
    them need `absent_scope: "run"`."""
    nodes = ob.execution.nodes
    kids = ob.children_of(ev.node)  # the whole parent -> children map
    later = [
        b.seq for b in ob.branches if b.site == ev.site and b.node == ev.node and b.seq > ev.seq
    ]
    end: int | None = min(later) if later else None
    rec = mech.sites.get(ev.site)
    fn = mech.function_of(ev.site)
    if rec is not None and fn is not None and any(r[0] == "?loop" for r in rec["requires"]):
        for k in kids.get(ev.node, []):
            if k < ev.seq or (end is not None and k >= end):
                continue
            tail = _symbol(nodes[k]).split(":", 1)[-1]
            matches = [c for c in fn["calls"] if _callee_match(tail, c["callee"])]
            if matches and all(not any(r[0] == "?loop" for r in c["requires"]) for c in matches):
                end = k
                break
    out: list[str] = []

    def walk(tree: dict[int, list[int]], n: int, floor: int, ceil: int | None) -> None:
        for k in tree.get(n, []):
            if k >= floor and (ceil is None or k < ceil):
                out.append(_symbol(nodes[k]))
                walk(tree, k, 0, ceil)

    walk(kids, ev.node, ev.seq, end)
    parent = nodes[ev.node].parent if ev.node < len(nodes) else None
    if end is None and parent is not None and mech.exits_under(ev.site, ev.outcome):
        me = _symbol(nodes[ev.node])
        nxt = [b.seq for b in ob.branches if b.site == ev.site and b.seq > ev.seq]
        stop: int | None = min(nxt) if nxt else None
        for k in kids.get(parent, []):
            if k <= ev.node:
                continue
            if (stop is not None and k >= stop) or _symbol(nodes[k]) == me:
                break
            out.append(_symbol(nodes[k]))
            walk(kids, k, 0, stop)
    return out


def _observed_contradictions(d: Decision, site: str, sub: StateSubstrate) -> list[str]:
    bad = []
    for test, ob in sub.obs.by_test.items():
        for ev in ob.branches:
            if ev.site != site:
                continue
            b = d.true_branch if ev.outcome else d.false_branch
            if b.outcome and b.outcome.get("entity") and b.outcome.get("is"):
                call = _enclosing_call(ob, ev.node, b.outcome["entity"])
                ok = exit_matches(b.outcome["is"], call.outcome) if call is not None else None
                if ok is False:
                    bad.append(
                        f"{test}: {b.outcome['entity']} ended {call.outcome}, "
                        f"not {b.outcome['is']}, after {site}={ev.outcome}"
                    )
            if not b.absent:
                continue
            after = (
                ob.subtree_after(ev.node, ev.seq)
                if b.absent_scope == "run"
                else episode_calls(ob, ev, sub.mech)
            )
            for a in b.absent:
                if any(_name_match(a, s) for s in after if s):
                    bad.append(f"{test}: {a} ran after {site}={ev.outcome}")
    return sorted(set(bad))


def _execution_constants(ob: ExecObs) -> dict[str, str]:
    """Global facts holding a single bucket throughout the execution."""
    seen: dict[str, set[str]] = {}
    for m in ob.execution.nodes:
        if isinstance(m, CallNode):
            for a, b, _ in (*m.state, *m.state_after):
                if a.startswith("global."):
                    seen.setdefault(a, set()).add(b)
    return {a: next(iter(bs)) for a, bs in seen.items() if len(bs) == 1}


def _local_agreement(
    g: Genome, d: Decision, site: str, sub: StateSubstrate, out_of_scope: set[str]
) -> tuple[list[str], list[str]]:
    """Assumes the state at the site equals the call's entry state except for fields the
    function itself stores before the site. Interleaved tasks (another coroutine running
    across an await) break that assumption, so executions outside the genome's sequential
    scope are excluded."""
    rec = sub.mech.sites.get(site)
    if rec is None:
        # without static facts it is unknown which fields the function writes before the
        # site, so the entry state cannot stand in for the state at the site
        return [], []
    fn = sub.mech.function_of(site) or {"stores": []}
    stored_before = {st["path"] for st in fn["stores"] if st["line"] < rec["line"]}
    agree: list[str] = []
    disagree: list[str] = []
    for test, ob in sub.obs.by_test.items():
        if test in out_of_scope or test.split("::")[-1] in out_of_scope:
            continue
        constants = _execution_constants(ob)
        for ev in ob.branches:
            if ev.site != site:
                continue
            node = ob.execution.nodes[ev.node]
            if not isinstance(node, CallNode):
                continue
            facts = {**constants, **{a: b for a, b, _ in node.state if a not in stored_before}}
            v = eval_predicate(d.predicate, derive(g, _bind(g, facts, node, "entry")))
            if v is None:
                continue
            name = test.split("/")[-1].split("::")[-1]
            (agree if v == ev.outcome else disagree).append(
                f"{name}: predicate {v} on observed state, site {ev.outcome}"
            )
    return agree, disagree


def _bind(
    g: Genome, facts: dict[str, str], node: Any = None, phase: str = "entry"
) -> dict[str, Any]:
    """Observed buckets -> genome variable values, through each variable's binding. With a
    call node, variables bound at that entity's boundary (`observed_as.at`) are added:
    argument facts at "entry", result and change facts at "exit"."""
    out: dict[str, Any] = {}
    for v in g.variables:
        b = v.observed_as or {}
        at = b.get("at")
        if isinstance(at, dict):
            if node is None or not _name_match(str(at.get("entity", "")), node.symbol):
                continue
            point, kind = str(at.get("point", "")), str(b.get("kind", "is_set"))
            if _exit_point(kind, point) != (phase == "exit"):
                continue
            val = boundary_fact(node, point, kind)
            if val is not None:
                out[v.name] = val
            continue
        fact = b.get("fact")
        if not fact or fact not in facts:
            continue
        bucket = facts[fact]
        kind = b.get("kind", "is_set")
        if kind == "is_set":
            out[v.name] = bucket != "none"
        elif kind == "bool" and bucket.startswith("bool:"):
            out[v.name] = bucket == "bool:true"
        elif kind == "sign" and bucket.startswith("num:"):
            out[v.name] = {"num:zero": 0, "num:pos": 1, "num:neg": -1}[bucket]
    return out


def _abstract_equal(kind: str, predicted: Any, observed: Any) -> bool:
    if kind == "sign":
        sign = (
            (predicted > 0) - (predicted < 0) if isinstance(predicted, int | float) else predicted
        )
        return bool(sign == observed)
    return bool(predicted == observed)


def eval_expr(expr: str, env: dict[str, Any]) -> Any:
    """Tiny expression language for transitions. Returns None when not decidable."""
    e = expr.strip()
    if e in ("true", "True"):
        return True
    if e in ("false", "False"):
        return False
    if e in ("none", "None", "null"):
        return None
    if re.fullmatch(r"-?\d+", e):
        return int(e)
    m = re.fullmatch(r"max\(\s*0\s*,\s*([\w.]+)\s*-\s*(\d+)\s*\)", e)
    if m:
        v = env.get(m.group(1))
        return None if not isinstance(v, int) else max(0, v - int(m.group(2)))
    m = re.fullmatch(r"([\w.]+)\s*([+-])\s*(\d+)", e)
    if m:
        v = env.get(m.group(1))
        if not isinstance(v, int):
            return None
        return v + int(m.group(3)) if m.group(2) == "+" else v - int(m.group(3))
    if e.startswith("!"):
        v = env.get(e[1:].strip())
        return None if not isinstance(v, bool) else not v
    return env.get(e)


def agreement_from_facts(
    g: Genome, test_facts: dict[str, dict[str, Any]]
) -> dict[str, list[tuple[str, bool]]]:
    """Per decision: (test, predicate value) for every test whose independently stated input
    facts decide the decision's predicate. Used to check predicate semantics against the
    outcome actually observed at the decision's site in that test."""
    out: dict[str, list[tuple[str, bool]]] = {}
    for d in g.decisions:
        for test, facts in test_facts.items():
            v = eval_predicate(d.predicate, derive(g, facts))
            if v is not None:
                out.setdefault(d.id, []).append((test, v))
    return out


# evidence kinds that report what executed: a failure is an observed contradiction
_OBSERVED_KINDS = ("execution", "branch", "delta", "boundary", "outcome")


def establish_state(
    g: Genome,
    sub: StateSubstrate,
    agreement: dict[str, list[tuple[str, bool]]] | None = None,
    agreement_seq: dict[str, list[tuple[str, bool]]] | None = None,
    out_of_scope: set[str] | None = None,
) -> Genome:
    """Statuses over the stronger substrate. Same principle as `establish`: only evidence
    decides; decisions are verified through their site's observed outcomes and static
    control facts, transitions through observed state deltas."""
    items: list[Item] = [
        *g.variables, *g.data_dependencies, *g.decisions, *g.effects, *g.transitions,
        *g.procedures, *g.rules, *g.regimes,
    ]  # fmt: skip
    for it in items:
        for ref in it.evidence:
            sub.check(ref)
        failed = [r for r in it.evidence if not r.ok]
        if not it.evidence:
            it.status, it.status_reason = HYPOTHESIS, "no evidence cited"
        elif [r for r in failed if r.kind in _OBSERVED_KINDS and not r.unanchored]:
            it.status = REJECTED
            it.status_reason = "contradicted: " + "; ".join(
                r.why for r in failed if r.kind in _OBSERVED_KINDS and not r.unanchored
            )
        elif failed:
            it.status = HYPOTHESIS
            it.status_reason = "evidence does not check out: " + "; ".join(r.why for r in failed)
        else:
            it.status = SUPPORTED
            it.status_reason = (
                "every cited reference checks out ("
                + ", ".join(sorted({r.kind for r in it.evidence}))
                + ")"
            )
    # decisions: anchored at a site, both outcomes observed, statically consistent,
    # no observed contradiction, and not sharing the site with another decision
    anchors: dict[str, list[str]] = {}
    model_sited = {d.id for d in g.decisions if d.site}
    for d in g.decisions:
        if d.site and not sub.site_exists(d.site):
            d.status = HYPOTHESIS
            d.status_reason = f"names a decision site that does not exist: {d.site}"
            continue
        site, how = _link_site(d, sub)
        if site:
            d.site = d.site or site
            anchors.setdefault(site, []).append(d.id)
        d.status_reason += f"; site: {site or 'none'} ({how})"
    for d in g.decisions:
        if d.status != SUPPORTED:
            continue
        site = d.site if sub.site_exists(d.site) else None
        if site is None:
            d.status_reason += "; not verified: no decision site"
            continue
        anchored = site in sub.mech.sites
        if len(anchors.get(site, [])) > 1:
            others = ", ".join(x for x in anchors[site] if x != d.id)
            d.status_reason += (
                f"; not verified: site shared with {others} — the observable outcome decides "
                "only their disjunction"
            )
            continue
        seen = sub.obs.outcomes_at(site)
        problems = _static_consistent(d, site, sub)
        contradictions = _observed_contradictions(d, site, sub)
        # (1) LOCAL agreement: at every observed evaluation of the site, the predicate on the
        # call's observed entry state (plus execution-constant globals, minus fields the
        # function stores before the site) must give the observed outcome. Attributable to
        # this decision alone; a disagreement rejects a decision whose site the proposal named.
        local_agree, local_disagree = _local_agreement(g, d, site, sub, out_of_scope or set())
        # (2) scenario agreement (whole-genome replay, or stated test facts): informative but
        # not attributable to one decision; a disagreement only blocks verification.
        agree: list[str] = list(local_agree)
        disagree: list[str] = []
        for test, same in (agreement_seq or {}).get(d.id, []):
            (agree if same else disagree).append(
                f"{test.split('/')[-1].split('::')[-1]}: replayed outcome sequence "
                + ("matches" if same else "differs")
            )
        for test, value in (agreement or {}).get(d.id, []):
            ob = sub.obs.get(test)
            observed = {b.outcome for b in ob.branches if b.site == site} if ob else set()
            if not observed:
                continue
            (agree if observed == {value} else disagree).append(
                f"{test.split('/')[-1].split('::')[-1]}: predicate {value}, site {sorted(observed)}"
            )
        if local_disagree and d.id in model_sited:
            d.status = REJECTED
            d.status_reason = "contradicted at its own site by observed state: " + "; ".join(
                local_disagree[:3]
            )
            continue
        if local_disagree or disagree:
            d.status_reason += (
                "; not verified: predicate disagrees with observed outcomes: "
                + "; ".join((local_disagree + disagree)[:3])
            )
            continue
        if contradictions:
            d.status = REJECTED
            d.status_reason = "contradicted by observed branches: " + "; ".join(contradictions[:3])
        elif problems:
            d.status_reason += (
                "; not verified: inconsistent with static control facts: " + "; ".join(problems[:3])
            )
        elif not agree:
            d.status_reason += (
                "; not verified: neither the observed state at the site nor any stated input "
                "facts decide the predicate, so its meaning cannot be checked"
            )
        elif seen[True] and seen[False] and not anchored:
            d.status_reason += (
                f"; not verified: site {site} is observed both ways and the predicate agrees "
                f"{len(agree)} time(s), but it has no static facts (unanchored), so its "
                "consequences cannot be checked"
            )
        elif seen[True] and seen[False]:
            d.status = VERIFIED
            d.status_reason = (
                f"site {site} (`{sub.mech.sites[site]['pred']}`) observed true in "
                f"{len(seen[True])} and false in {len(seen[False])} execution(s); the predicate "
                f"agrees with the observed outcome {len(local_agree)} time(s) from observed "
                f"state and in {len(agree) - len(local_agree)} replayed/stated case(s), "
                "disagreeing in none; "
                "branch consequences consistent with static control facts; no contradiction"
            )
        else:
            missing = "true" if not seen[True] else "false"
            d.status_reason += f"; not verified: outcome {missing} never observed at {site}"
    # transitions: observed deltas at the entity's calls, through variable bindings. When
    # a procedure places the transition (T:id), it is checked where the genome says it
    # happens: the entity's procedure is run from the call's observed entry state, and the
    # transition is compared only if that run reaches it.
    kinds = {v.name: (v.observed_as or {}).get("kind", "is_set") for v in g.variables}
    placed = {st[2:] for p in g.procedures for st in p.steps if st.startswith("T:")}
    placed |= {
        st[2:]
        for d in g.decisions
        for b in (d.true_branch, d.false_branch)
        for st in b.steps
        if st.startswith("T:")
    }
    for t in g.transitions:
        if t.status == REJECTED or not t.entity or not t.sets:
            continue
        consistent: list[str] = []
        contradicting: list[str] = []
        for test, ob in sub.obs.by_test.items():
            # global facts that hold one value throughout the execution are known at every
            # call in it (a setting read in a nested call is the same setting)
            seen_globals: dict[str, set[str]] = {}
            for m in ob.execution.nodes:
                if isinstance(m, CallNode):
                    for a, b, _ in (*m.state, *m.state_after):
                        if a.startswith("global."):
                            seen_globals.setdefault(a, set()).add(b)
            constant = {a: next(iter(bs)) for a, bs in seen_globals.items() if len(bs) == 1}
            for n in ob.execution.nodes:
                if not (isinstance(n, CallNode) and _name_match(t.entity, n.symbol)):
                    continue
                before = _bind(g, {**constant, **{a: b for a, b, _ in n.state}}, n, "entry")
                after = _bind(g, {a: b for a, b, _ in n.state_after}, n, "exit")
                if not after:
                    continue
                replayed: dict[str, Any] | None = None
                if t.id in placed:
                    run = predict_sequence(
                        g, {"state": dict(before), "calls": [{"entity": t.entity}]}, "hypothesis"
                    )
                    if not any(e[0] == "set" and e[3] == t.id for e in run.events):
                        if run.indeterminate is None:
                            continue  # the genome says this call does not reach it
                        # the genome cannot decide the path from the entry state alone
                        # (decisions over unbound inputs): follow the path that executed
                        events, _, problem = replay_observed(g, t.entity, ob, n.id, dict(before))
                        sets = [e for e in events if e[0] == "set" and e[3] == t.id]
                        if problem is not None or not sets:
                            continue
                        replayed = {e[1]: e[2] for e in sets}
                elif eval_predicate(t.when, before) is not True:
                    continue
                for var, expr in t.sets.items():
                    if var not in after:
                        continue
                    if replayed is not None:
                        if var not in replayed:
                            continue
                        pred = replayed[var]
                    else:
                        pred = eval_expr(expr, before)
                    if pred is None and expr.strip() not in ("none", "None", "null"):
                        continue
                    if _abstract_equal(kinds.get(var, "is_set"), pred, after[var]):
                        consistent.append(test)
                    else:
                        contradicting.append(
                            f"{test}: {var} observed {after[var]!r}, predicted {pred!r}"
                        )
        if contradicting:
            t.status = REJECTED
            t.status_reason = "observed deltas contradict: " + "; ".join(contradicting[:3])
        elif consistent and t.status == SUPPORTED:
            t.status = VERIFIED
            t.status_reason = (
                f"observed deltas consistent in {len(set(consistent))} execution(s); "
                "none contradict"
                + (" (checked where the procedure applies it)" if t.id in placed else "")
            )
        elif not consistent:
            t.status_reason += "; not verified: no observed call of the entity with a bound delta"
    # procedure outcomes: where an observed call completes the procedure's path (replayed
    # along what executed, without a stopping branch), the named entity's exit must match
    for p in g.procedures:
        if not p.outcome or not p.outcome.get("is") or p.status == REJECTED:
            continue
        target = p.outcome.get("entity") or p.entity
        agreeing, disagreeing = 0, []
        for test, ob in sub.obs.by_test.items():
            for n in ob.execution.nodes:
                if not (isinstance(n, CallNode) and _name_match(p.entity, n.symbol)):
                    continue
                env = _bind(g, {a: b for a, b, _ in n.state}, n, "entry")
                _, stopped, problem = replay_observed(g, p.entity, ob, n.id, env)
                if stopped or problem is not None:
                    continue
                call = _enclosing_call(ob, n.id, target)
                ok = exit_matches(p.outcome["is"], call.outcome) if call is not None else None
                if ok is True:
                    agreeing += 1
                elif ok is False:
                    disagreeing.append(f"{test.split('::')[-1]}: {target} ended {call.outcome}")
        if disagreeing:
            p.status = REJECTED
            p.status_reason = f"observed exit contradicts outcome {p.outcome['is']}: " + "; ".join(
                disagreeing[:3]
            )
        elif agreeing:
            p.status_reason += f"; outcome {p.outcome['is']} observed in {agreeing} call(s)"
    return g


# --------------------------------------------------------------------------- path conditions


def path_condition(ob: ExecObs, sites: set[str], mech: Mechanics) -> list[dict[str, Any]]:
    """The observed branch vector over `sites`, in order, with each site's predicate. An
    observed fact; a symbolic reading requires the predicate to be representable."""
    return [
        {
            "site": b.site,
            "outcome": b.outcome,
            "pred": mech.sites.get(b.site, {}).get("pred"),
            "in": b.symbol,
        }
        for b in ob.branches
        if b.site in sites
    ]


def regimes(obs: Observations, sites: set[str]) -> dict[tuple[tuple[str, bool], ...], list[str]]:
    """Executions grouped by identical branch vectors over `sites`."""
    out: dict[tuple[tuple[str, bool], ...], list[str]] = {}
    for test, ob in obs.by_test.items():
        key = tuple((b.site, b.outcome) for b in ob.branches if b.site in sites)
        out.setdefault(key, []).append(test)
    return out


# --------------------------------------------------------------------------- sequence prediction


@dataclass
class SeqPrediction:
    events: list[tuple[Any, ...]] = field(
        default_factory=list
    )  # ("call", e) | ("branch", site, v) | ("set", var, val)
    state: dict[str, Any] = field(default_factory=dict)
    indeterminate: str | None = None


def predict_sequence(
    g: Genome, scenario: dict[str, Any], min_status: str = SUPPORTED, max_depth: int = 12
) -> SeqPrediction:
    """Predict a sequence of calls under an initial state. Each call runs the entity's
    procedure (or, without one, its decisions in order); transitions change the state that
    later decisions read. Unestablished items that are needed stop the prediction."""
    decisions = {d.id: d for d in g.decisions}
    transitions = {t.id: t for t in g.transitions}
    procedures = {p.entity: p for p in g.procedures}
    pred = SeqPrediction(state=dict(scenario.get("state") or {}))

    def usable(it: Item) -> bool:
        return RANK.get(it.status, 0) >= RANK[min_status]

    def entity_key(e: str) -> str | None:
        for k in procedures:
            if k == e or k.endswith("." + e) or e.endswith("." + k):
                return k
        return None

    def run_steps(steps: list[str], env: dict[str, Any], depth: int) -> bool:
        """Returns True if the enclosing entity stops."""
        for st in steps:
            if pred.indeterminate:
                return True
            kind, _, ref = st.partition(":")
            if kind == "call":
                pred.events.append(("call", ref))
                key = entity_key(ref)
                if key is not None:
                    run_entity(key, env, depth + 1)
            elif kind == "T":
                t = transitions.get(ref)
                if t is None or not usable(t):
                    pred.indeterminate = (
                        f"transition {ref} is {'missing' if t is None else t.status}"
                    )
                    return True
                w = eval_predicate(t.when, derive(g, env))
                if w is None:
                    pred.indeterminate = f"{ref}: `{t.when}` needs facts it was not given"
                    return True
                if w:
                    for var, expr in t.sets.items():
                        val = eval_expr(expr, env)
                        if val is None and expr.strip() not in ("none", "None", "null"):
                            pred.indeterminate = f"{ref}: cannot evaluate {var} := {expr}"
                            return True
                        env[var] = val
                        pred.events.append(("set", var, val, ref))
            elif kind == "D":
                d = decisions.get(ref)
                if d is None or not usable(d):
                    pred.indeterminate = f"decision {ref} is {'missing' if d is None else d.status}"
                    return True
                v = eval_predicate(d.predicate, derive(g, env))
                if v is None:
                    pred.indeterminate = f"{ref}: `{d.predicate}` needs facts it was not given"
                    return True
                if d.site:
                    pred.events.append(("branch", d.site, v))
                b = d.true_branch if v else d.false_branch
                if b.outcome and b.outcome.get("is"):
                    pred.events.append(
                        ("outcome", b.outcome.get("entity") or d.entity, b.outcome["is"])
                    )
                inner = b.steps or [f"call:{c}" for c in b.calls]
                if run_steps(inner, env, depth) or b.stops:
                    return True
            else:
                pred.indeterminate = f"unknown step {st!r}"
                return True
        return False

    def run_entity(key: str, env: dict[str, Any], depth: int) -> None:
        if depth > max_depth:
            pred.indeterminate = f"depth limit at {key}"
            return
        p = procedures[key]
        if not usable(p):
            pred.indeterminate = f"procedure {p.id} ({key}) is {p.status}"
            return
        stopped = run_steps(p.steps, env, depth)
        if not stopped and not pred.indeterminate and p.outcome and p.outcome.get("is"):
            pred.events.append(("outcome", p.outcome.get("entity") or p.entity, p.outcome["is"]))

    env = pred.state
    for call in scenario.get("calls") or []:
        env.update(call.get("facts") or {})
        e = call["entity"]
        pred.events.append(("call", e))
        key = entity_key(e)
        if key is None:
            # an entity the genome says nothing about is a call with no modeled behavior;
            # one the genome has decisions for but no procedure cannot be predicted
            if any(
                d.entity == e or d.entity.endswith("." + e) or e.endswith("." + d.entity)
                for d in g.decisions
            ):
                pred.indeterminate = f"no procedure for {e}, which has decisions"
                break
            continue
        run_entity(key, env, 0)
        if pred.indeterminate:
            break
    return pred


def replay_observed(
    g: Genome, entity: str, ob: ExecObs, node_id: int, env: dict[str, Any], depth: int = 0
) -> tuple[list[tuple[Any, ...]], bool, str | None]:
    """Run an entity's procedure for ONE observed call, guided by what executed.

    Each decision takes the outcomes observed at its site in that call (in order). A
    decision whose predicate is atomic (`v` or `!v`) binds v accordingly. A `call:X` step
    descends into the next observed call of X beneath this one. Transitions apply when their
    `when` holds in the resulting environment. Nothing is guessed: a missing observation or
    an undecidable `when` ends the replay with a problem.

    Returns (events, stopped, problem). Events: ("branch", site, v), ("set", var, value,
    transition id, node), ("outcome", entity, exit, node)."""
    procedures = {p.entity: p for p in g.procedures}
    decisions = {d.id: d for d in g.decisions}
    transitions = {t.id: t for t in g.transitions}

    def key_of(e: str) -> str | None:
        return next(
            (k for k in procedures if k == e or k.endswith("." + e) or e.endswith("." + k)), None
        )

    key = key_of(entity)
    if key is None:
        return [], False, f"no procedure for {entity}"
    nodes = ob.execution.nodes
    kids = ob.children_of(node_id)
    pending: dict[str, list[bool]] = {}
    for b in ob.branches:
        if b.node == node_id:
            pending.setdefault(b.site, []).append(b.outcome)

    def subtree(n: int) -> list[int]:
        out: list[int] = []
        stack = list(reversed(kids.get(n, [])))
        while stack:
            k = stack.pop()
            out.append(k)
            stack.extend(reversed(kids.get(k, [])))
        return out

    below = sorted(subtree(node_id))
    cursor = -1
    events: list[tuple[Any, ...]] = []

    def run(steps: list[str]) -> tuple[bool, str | None]:
        nonlocal cursor
        for st in steps:
            kind, _, ref = st.partition(":")
            if kind == "call":
                nxt = next(
                    (
                        k
                        for k in below
                        if k > cursor
                        and isinstance(nodes[k], CallNode)
                        and _name_match(ref, _symbol(nodes[k]))
                    ),
                    None,
                )
                if nxt is None:
                    return False, f"{ref} was not observed under this call"
                inner = subtree(nxt)
                cursor = max([nxt, *inner])
                if key_of(ref) is not None and depth < 12:
                    ev, _, prob = replay_observed(g, ref, ob, nxt, env, depth + 1)
                    events.extend(ev)
                    if prob is not None:
                        return False, prob
            elif kind == "D":
                d = decisions.get(ref)
                if d is None or not d.site:
                    return False, f"decision {ref} is missing or has no site"
                queue = pending.get(d.site) or []
                if not queue:
                    return False, f"{ref}: no observed evaluation of {d.site} in this call"
                v = queue.pop(0)
                events.append(("branch", d.site, v))
                m = re.fullmatch(r"\s*(!?)\s*([\w.]+)\s*", d.predicate)
                if m and m.group(2) not in ("true", "false"):
                    env[m.group(2)] = (not v) if m.group(1) else v
                b = d.true_branch if v else d.false_branch
                if b.outcome and b.outcome.get("is"):
                    events.append(
                        ("outcome", b.outcome.get("entity") or d.entity, b.outcome["is"], node_id)
                    )
                stopped, prob = run(b.steps or [f"call:{c}" for c in b.calls])
                if prob is not None:
                    return stopped, prob
                if stopped or b.stops:
                    return True, None
            elif kind == "T":
                t = transitions.get(ref)
                if t is None:
                    return False, f"transition {ref} is missing"
                w = eval_predicate(t.when, derive(g, env))
                if w is None:
                    return False, f"{ref}: `{t.when}` is undecidable on the observed path"
                if w:
                    for var, expr in t.sets.items():
                        val = eval_expr(expr, env)
                        if val is None and expr.strip() not in ("none", "None", "null"):
                            return False, f"{ref}: cannot evaluate {var} := {expr}"
                        env[var] = val
                        events.append(("set", var, val, ref, node_id))
            else:
                return False, f"unknown step {st!r}"
        return False, None

    p = procedures[key]
    stopped, problem = run(p.steps)
    if not stopped and problem is None and p.outcome and p.outcome.get("is"):
        events.append(("outcome", p.outcome.get("entity") or p.entity, p.outcome["is"], node_id))
    return events, stopped, problem


def change_sites(mech: Mechanics, obs: Observations, symbols: list[str]) -> set[str]:
    """Every decision site of the given functions and of functions nested in them: their
    static sites, plus sites observed at runtime inside calls of them. A genome is scored
    on all of these, not only on the sites it chooses to cover."""
    tails = [s.split(":", 1)[-1] for s in symbols]

    def mine(sym: str) -> bool:
        t = sym.split(":", 1)[-1]
        return any(t == x or t.startswith(x + ".<locals>.") for x in tails)

    out = {sid for sid, rec in mech.sites.items() if mine(rec["symbol"])}
    for ob in obs.by_test.values():
        out |= {b.site for b in ob.branches if mine(b.symbol)}
    return out


def compare_sequence(
    g: Genome,
    pred: SeqPrediction,
    ob: ExecObs,
    sites: set[str],
    required_sites: set[str] | None = None,
) -> dict[str, Any]:
    """Predicted branch events vs the observed branch vector over the genome's sites (exact,
    in order), and the predicted final state vs the last observed exit state of each bound
    variable. With `required_sites` (e.g. `change_sites`), an observed evaluation of a
    required site that no decision covers makes the prediction incomplete: indeterminate,
    never a match."""
    uncovered = sorted(
        {b.site for b in ob.branches if required_sites and b.site in required_sites} - sites
    )
    observed_vec = [(b.site, b.outcome) for b in ob.branches if b.site in sites]
    predicted_vec = [(e[1], e[2]) for e in pred.events if e[0] == "branch"]
    last: dict[str, str] = {}
    for n in ob.execution.nodes:
        if isinstance(n, CallNode) and n.state_after:
            last.update({a: b for a, b, _ in n.state_after if a.startswith(("self.", "global."))})
    observed_state = _bind(g, last)
    kinds = {v.name: (v.observed_as or {}).get("kind", "is_set") for v in g.variables}
    state_diff = {
        k: (pred.state.get(k), v)
        for k, v in observed_state.items()
        if k in pred.state and not _abstract_equal(kinds.get(k, "is_set"), pred.state[k], v)
    }
    # predicted exits, per entity, against the exits of that entity's observed calls: every
    # observed call must match a predicted exit and every predicted exit an observed call
    predicted_exits: dict[str, list[str]] = {}
    for e in pred.events:
        if e[0] == "outcome":
            predicted_exits.setdefault(e[1], []).append(e[2])
    outcome_diff: dict[str, Any] = {}
    for ent, claims in predicted_exits.items():
        seen = [
            n.outcome
            for n in ob.execution.nodes
            if isinstance(n, CallNode) and _name_match(ent, n.symbol)
        ]
        unmatched_obs = [o for o in seen if not any(exit_matches(c, o) for c in claims)]
        unmatched_pred = [c for c in claims if not any(exit_matches(c, o) for o in seen)]
        if unmatched_obs or unmatched_pred:
            outcome_diff[ent] = {"predicted": sorted(set(claims)), "observed": sorted(set(seen))}
    indeterminate = pred.indeterminate or (
        f"no decision covers observed site(s) {', '.join(uncovered)}" if uncovered else None
    )
    return {
        "execution": ob.execution.stimulus_ref,
        "indeterminate": indeterminate,
        "uncovered_sites": uncovered,
        "predicted_branches": predicted_vec,
        "observed_branches": observed_vec,
        "branches_exact": indeterminate is None and predicted_vec == observed_vec,
        "state_checked": sorted(k for k in observed_state if k in pred.state),
        "state_diff": state_diff,
        "outcome_diff": outcome_diff,
        "match": indeterminate is None
        and predicted_vec == observed_vec
        and not state_diff
        and not outcome_diff,
    }
