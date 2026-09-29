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
import itertools
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
    Variable,
    bindings_of,
    derive,
    eval_predicate,
)
from diffgenome.model import CallNode, Execution
from diffgenome.structure import (
    Skeleton,
    build_skeleton,
    occurrences,
    placement_problems,
    repetitions,
    resolve,
)

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


@dataclass(frozen=True)
class Identity:
    """An opaque value identity: the collector's digest of a boundary value. It is never
    decoded; predicates compare identities with == and != only."""

    digest: str

    def __repr__(self) -> str:
        return f"Identity(#{self.digest[:6]})"


_GO_INT_KINDS = frozenset(
    {"int", "int8", "int16", "int32", "int64", "uint", "uint8", "uint16", "uint32", "uint64"}
)


def literal_canonical(spec: dict[str, Any]) -> str | None:
    """The canonical form a runtime collector digests for one allowed source literal, or
    None. Allowed (design-value-identity.md, 3): bool, null, integers up to 64 bits, printable
    strings up to 64 characters without quotes or backslashes. Go and Python only."""
    lang, typ, value = spec.get("lang"), spec.get("type"), spec.get("value")
    if isinstance(value, str) and (
        len(value) > 64 or not value.isprintable() or '"' in value or "'" in value or "\\" in value
    ):
        return None
    is_int = isinstance(value, int) and not isinstance(value, bool) and abs(value) < 2**63
    if lang == "go":
        if typ == "string" and isinstance(value, str):
            return f'string:"{value}"'
        if typ in _GO_INT_KINDS and is_int:
            return f"{typ}:{value}"
        if typ == "bool" and isinstance(value, bool):
            return f"bool:{'true' if value else 'false'}"
        if typ == "nil":
            return "nil"
    if lang == "python":
        if typ == "str" and isinstance(value, str):
            return f"str:{value!r}"
        if typ == "int" and is_int:
            return f"int:{value!r}"
        if typ == "bool" and isinstance(value, bool):
            return f"bool:{value!r}"
        if typ in ("None", "NoneType"):
            return "NoneType:None"
    return None


def literal_in_source(spec: dict[str, Any], root: Any) -> bool:
    """The literal is written on the cited source line (the checker never guesses values)."""
    src = spec.get("source") or {}
    try:
        lines = (root / str(src.get("file", ""))).read_text(encoding="utf-8").splitlines()
        text = lines[int(src.get("line", 0)) - 1]
    except (OSError, ValueError, IndexError, TypeError):
        return False
    value = spec.get("value")
    if isinstance(value, str):
        return f'"{value}"' in text or f"'{value}'" in text
    if isinstance(value, bool):
        return re.search(r"\b(true|false|True|False)\b", text) is not None
    if isinstance(value, int):
        return re.search(rf"(?<![\w.]){value}(?![\w.])", text) is not None
    return re.search(r"\b(nil|None|null)\b", text) is not None


def boundary_fact(node: Any, point: str, kind: str, literal: dict[str, Any] | None = None) -> Any:
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
    if kind == "identity":
        return Identity(dg) if dg else None
    if kind == "equals_literal":
        canon = literal_canonical(literal or {})
        return (dg == _d(canon)) if canon and dg else None
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
    # identities may carry the runtime prefix on either side (Experiment 10, Case B: a claim
    # copied from an observed exit kept its `go:` and never matched the observation)
    o_kind = o_kind.split(":", 1)[1] if o_kind[:3] in ("py:", "go:", "js:") else o_kind
    c_kind = c_kind.split(":", 1)[1] if c_kind[:3] in ("py:", "go:", "js:") else c_kind
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
            v = eval_predicate(d.predicate, derive(g, _bind(g, facts, node, "entry", ob)))
            if v is None:
                continue
            name = test.split("/")[-1].split("::")[-1]
            (agree if v == ev.outcome else disagree).append(
                f"{name}: predicate {v} on observed state, site {ev.outcome}"
            )
    return agree, disagree


def _is_ancestor(ob: ExecObs, anc: int, node: int) -> bool:
    p = ob.execution.nodes[node].parent
    while p is not None:
        if p == anc:
            return True
        p = ob.execution.nodes[p].parent
    return False


def scoped_value(ob: ExecObs, b: dict[str, Any], before: int | None = None) -> tuple[Any, str]:
    """The value of a binding across one execution: the boundary's value in every occurrence
    of its entity (only those that ran before node `before`, when given: argument points of
    occurrences started earlier, result points of occurrences finished earlier). Returns
    (value, "") when all agree, (None, reason) when missing or ambiguous."""
    at = b.get("at") or {}
    entity, point = str(at.get("entity", "")), str(at.get("point", ""))
    kind = str(b.get("kind", "identity"))
    vals = []
    for n in ob.execution.nodes:
        if not (isinstance(n, CallNode) and _name_match(entity, n.symbol)):
            continue
        if before is not None:
            if n.id >= before:
                continue
            if _exit_point(kind, point) and _is_ancestor(ob, n.id, before):
                continue  # still running: its result is not known yet
        v = boundary_fact(n, point, kind, b.get("literal"))
        if v is not None:
            vals.append(v)
    if not vals:
        return None, "missing"
    if any(v != vals[0] for v in vals[1:]):
        return None, "ambiguous"
    return vals[0], ""


def _bind(
    g: Genome,
    facts: dict[str, str],
    node: Any = None,
    phase: str = "entry",
    ob: ExecObs | None = None,
) -> dict[str, Any]:
    """Observed buckets -> genome variable values, through each variable's binding(s). With
    a call node, variables bound at that entity's boundary (`observed_as.at`) are added:
    argument facts at "entry", result and change facts at "exit". With the execution too,
    bindings of `scope: "execution"` at OTHER entities take the value those boundaries had
    earlier in the execution, when it is unique (design-value-identity.md, 2)."""
    out: dict[str, Any] = {}
    for v in g.variables:
        for b in bindings_of(v):
            if v.name in out:
                break
            at = b.get("at")
            if isinstance(at, dict):
                kind = str(b.get("kind", "is_set"))
                if kind == "equals_literal" and b.get("_literal_ok") is not True:
                    continue  # unchecked or not in source: never used
                point = str(at.get("point", ""))
                if node is not None and _name_match(str(at.get("entity", "")), node.symbol):
                    if _exit_point(kind, point) != (phase == "exit"):
                        continue
                    val = boundary_fact(node, point, kind, b.get("literal"))
                elif (
                    b.get("scope") == "execution"
                    and ob is not None
                    and node is not None
                    and phase == "entry"
                ):
                    val, _ = scoped_value(ob, b, before=node.id)
                else:
                    continue
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


def identity_claim(v: Variable, obs: Observations) -> tuple[str, str, int, int]:
    """Check a variable observed at >= 2 identity boundaries: every observation of it in one
    execution is the same value. Returns (status or "", reason, agreeing executions, distinct
    identities). Rejected on any execution where all sides are present and differ; verified
    when equal in >= 2 executions carrying >= 2 distinct identities (a contrast, so that a
    constant coincidence cannot verify it); supported when equal but vacuous; "" (unknown)
    when no execution shows every side."""
    sides = [b for b in bindings_of(v) if b.get("kind") == "identity"]
    agree: list[Any] = []
    bad: list[str] = []
    for test, ob in obs.by_test.items():
        vals = [scoped_value(ob, b)[0] for b in sides]
        if any(x is None for x in vals):
            continue
        if all(x == vals[0] for x in vals[1:]):
            agree.append(vals[0])
        else:
            bad.append(test.split("::")[-1])
    distinct = len(set(agree))
    if bad:
        return (
            REJECTED,
            f"identity contradicted: sides differ in {', '.join(bad[:3])}",
            len(agree),
            distinct,
        )
    if len(agree) >= 2 and distinct >= 2:
        return (
            VERIFIED,
            (
                f"identity verified: equal in {len(agree)} execution(s) carrying {distinct} "
                "distinct values"
            ),
            len(agree),
            distinct,
        )
    if agree:
        return (
            SUPPORTED,
            (
                f"identity observed in {len(agree)} execution(s) with {distinct} distinct "
                "value(s): no contrast, not verified"
            ),
            len(agree),
            distinct,
        )
    return "", "identity unknown: no execution shows every side", 0, 0


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


def genome_vocabulary(g: Genome) -> list[str]:
    """Every entity a genome names: procedures, decisions, transitions and called entities."""
    names = {p.entity for p in g.procedures} | {d.entity for d in g.decisions}
    names |= {t.entity for t in g.transitions} | {r.entity for r in g.regions}
    names |= {r.head for r in g.regions if r.head and not r.head.startswith("site:")}
    step_lists = (
        [p.steps for p in g.procedures]
        + [r.steps for r in g.regions]
        + [
            [*b.steps, *(f"call:{c}" for c in b.calls)]
            for d in g.decisions
            for b in (d.true_branch, d.false_branch)
        ]
    )
    for steps in step_lists:
        names |= {st[5:] for st in steps if st.startswith("call:")}
    return sorted(n for n in names if n)


def _reached(
    steps: list[str],
    decisions: dict[str, Decision],
    vocab: list[str],
    regions: dict[str, Any] | None = None,
) -> tuple[list[str], list[tuple[str, str]]]:
    """Calls and decision sites reached in a procedure's own body (its steps, its
    decisions' branches and the bodies of regions it places), without entering other
    entities' procedures."""
    calls: list[str] = []
    dsites: list[tuple[str, str]] = []
    seen: set[str] = set()
    stack = [list(steps)]
    while stack:
        for st in stack.pop():
            kind, _, ref = st.partition(":")
            if kind == "call":
                calls.append(resolve(vocab, ref))
            elif kind == "D" and ref in decisions and ref not in seen:
                seen.add(ref)
                d = decisions[ref]
                if d.site:
                    dsites.append((d.id, d.site))
                for br in (d.true_branch, d.false_branch):
                    stack.append(br.steps or [f"call:{c}" for c in br.calls])
            elif kind == "R" and regions and ref in regions and f"R:{ref}" not in seen:
                seen.add(f"R:{ref}")
                stack.append(list(regions[ref].steps))
    return calls, dsites


def procedure_structure_claims(g: Genome, sk: Skeleton) -> list[dict[str, Any]]:
    """What each procedure claims about execution structure, judged against the observed
    skeleton (diffgenome.structure). Absence of observation never rejects: a call or
    decision on a path the tests never took is simply not established. Rejection needs
    positive evidence.
    - contains:  `call:B` reached in A's own steps (and its decisions' branches) claims B
                 runs during A. Rejected if the nesting is inverted: every observed A ran
                 during B. Verified if every observed B ran during A, in >= 2 executions;
                 supported if some did; otherwise not established.
    - evaluates: a decision reached in A's steps claims its site is evaluated during A.
                 Rejected if the site is evaluated in another function's own call and every
                 observed A ran during that function (the decider encloses A: its decisions
                 cannot be evaluated inside A). Verified if every evaluation was during A
                 (>= 2); supported if some; otherwise not established.
    - order:     consecutive steps x, y of A claim x before y. Verified when x precedes y in
                 every observed occurrence of A holding both (>= 2 executions), or inside
                 one repetition of a repeated region (>= 2 repetitions); rejected when the
                 opposite was observed; else supported. Counts are never claimed.
    Recursion (a function running during itself) is outside these rules."""
    vocab = sorted(set(genome_vocabulary(g)) | set(sk.seen))
    decisions = {d.id: d for d in g.decisions}
    region_items = {r.id: r for r in g.regions}
    claims: list[dict[str, Any]] = []

    def claim(p: Any, kind: str, what: str, status: str, why: str) -> None:
        claims.append(
            {"procedure": p.id, "entity": p.entity, "kind": kind, "claim": what,
             "status": status, "why": why}
        )  # fmt: skip

    for p in g.procedures:
        a = resolve(vocab, p.entity)
        calls, dsites = _reached(p.steps, decisions, vocab, region_items)
        for b in dict.fromkeys(calls):
            n = sk.seen.get(b, 0)
            inside = sk.inside_occ.get(b, {}).get(a, 0)
            what = f"{b} during {a}"
            if n == 0:
                claim(p, "contains", what, "unobserved", f"{b} never observed")
            elif b != a and sk.always_during(a, b):
                claim(p, "contains", what, REJECTED,
                      f"inverted: every observed {a} ran during {b}")  # fmt: skip
            elif inside == 0:
                claim(p, "contains", what, "not established",
                      f"{b} observed {n} time(s), never during {a}")  # fmt: skip
            elif inside == n and sk.ancestry.get(b, {}).get(a, 0) >= 2:
                claim(p, "contains", what, VERIFIED, f"all {n} observed")
            else:
                claim(p, "contains", what, SUPPORTED, f"{inside} of {n} observed")
        for did, site in dsites:
            during = sk.site_during.get(site)
            what = f"{did} ({site}) evaluated during {a}"
            if not during:
                claim(p, "evaluates", what, "unobserved", "site never evaluated")
                continue
            total = max(during.values())
            owners = [o for o in sk.site_owner.get(site, {}) if o != a]
            if a not in during and owners and all(sk.always_during(a, o) for o in owners):
                claim(p, "evaluates", what, REJECTED,
                      f"inverted: evaluated in {', '.join(owners)}, and every observed "
                      f"{a} ran during it")  # fmt: skip
            elif a not in during:
                claim(p, "evaluates", what, "not established",
                      f"evaluated {total} time(s), never during {a}")  # fmt: skip
            elif during[a] == total and total >= 2:
                claim(p, "evaluates", what, VERIFIED, f"all {total} evaluations")
            else:
                claim(p, "evaluates", what, SUPPORTED, f"{during[a]} of {total} evaluations")
        fams: list[str] = []
        for st in p.steps:
            kind, _, ref = st.partition(":")
            if kind == "call":
                fams.append(resolve(vocab, ref))
            elif kind == "D" and ref in decisions and decisions[ref].site:
                fams.append(f"site:{decisions[ref].site}")
            elif kind == "R" and ref in region_items:
                # a region is placed by its head
                fams.append(_region_head(region_items[ref], vocab))
        for x, y in itertools.pairwise(fams):
            if x == y:
                continue
            what = f"{x} before {y} in {a}"
            regions = [r for r in sk.regions.get(a, []) if r["head"] is not None]
            if sk.strictly_before(a, x, y):
                n_ex = sk.before[a][(x, y)][1]
                claim(p, "order", what, VERIFIED if n_ex >= 2 else SUPPORTED,
                      f"all of x before all of y in {n_ex} execution(s)")  # fmt: skip
            elif sk.strictly_before(a, y, x):
                claim(p, "order", what, REJECTED, "observed the other way round")
            elif any((x, y) in r["within"] for r in regions):
                n = max(r["within"].get((x, y), 0) for r in regions)
                claim(p, "order", what, VERIFIED if n >= 2 else SUPPORTED,
                      f"inside one repetition, {n} repetition(s)")  # fmt: skip
            elif any((y, x) in r["within"] for r in regions):
                claim(p, "order", what, REJECTED, "inside one repetition, observed reversed")
            else:
                claim(p, "order", what, SUPPORTED, "not established by observation")
    claims += _region_claims(g, sk, vocab, decisions)
    return claims


def _region_head(r: Any, vocab: list[str]) -> str:
    return r.head if r.head.startswith("site:") else resolve(vocab, r.head)


def _region_claims(
    g: Genome, sk: Skeleton, vocab: list[str], decisions: dict[str, Decision]
) -> list[dict[str, Any]]:
    """A region claims (kind `region`) that its head starts every repetition of an observed
    repeated region of its enclosing entity; its body's consecutive steps are order claims
    inside ONE repetition; its calls and decisions run during the enclosing entity."""
    out: list[dict[str, Any]] = []

    def claim(r: Any, kind: str, what: str, status: str, why: str) -> None:
        out.append(
            {"procedure": r.id, "entity": r.entity, "kind": kind, "claim": what,
             "status": status, "why": why}
        )  # fmt: skip

    for r in g.regions:
        a = resolve(vocab, r.entity)
        head = _region_head(r, vocab)
        observed = [x for x in sk.regions.get(a, []) if x["head"] == head]
        what = f"region {r.id}: repetitions of {a} start with {head}"
        if observed:
            n_ex = sk.ancestry.get(head, {}).get(a, 0) if not head.startswith("site:") else 2
            claim(r, "region", what, VERIFIED if n_ex >= 2 else SUPPORTED,
                  f"observed repeated region {observed[0]['members']}")  # fmt: skip
        elif head in sk.families.get(a, {}) and sk.families[a][head][1] <= 1:
            claim(r, "region", what, REJECTED, f"{head} is observed in {a} but never repeated")
        else:
            claim(
                r,
                "region",
                what,
                "unobserved",
                f"no observed repeated region of {a} with that head",
            )
        within = observed[0]["within"] if observed else {}
        fams: list[str] = []
        for st in r.steps:
            kind, _, ref = st.partition(":")
            if kind == "call":
                fams.append(resolve(vocab, ref))
            elif kind == "D" and ref in decisions and decisions[ref].site:
                fams.append(f"site:{decisions[ref].site}")
        for x, y in itertools.pairwise(fams):
            if x == y:
                continue
            w = f"{x} before {y} in one repetition of {r.id}"
            if (x, y) in within:
                claim(r, "order", w, VERIFIED if within[(x, y)] >= 2 else SUPPORTED,
                      f"{within[(x, y)]} repetition(s)")  # fmt: skip
            elif (y, x) in within:
                claim(r, "order", w, REJECTED, "inside one repetition, observed reversed")
            else:
                claim(r, "order", w, SUPPORTED, "not established by observation")
        calls, dsites = _reached(r.steps, decisions, vocab)
        for b in dict.fromkeys(calls):
            if sk.seen.get(b, 0) and b != a and sk.always_during(a, b):
                claim(r, "contains", f"{b} during {a}", REJECTED,
                      f"inverted: every observed {a} ran during {b}")  # fmt: skip
            elif sk.inside_occ.get(b, {}).get(a, 0):
                claim(
                    r,
                    "contains",
                    f"{b} during {a}",
                    VERIFIED,
                    "observed during the enclosing entity",
                )
        for did, site in dsites:
            during = sk.site_during.get(site) or {}
            owners = [o for o in sk.site_owner.get(site, {}) if o != a]
            if (
                during
                and a not in during
                and owners
                and all(sk.always_during(a, o) for o in owners)
            ):
                claim(r, "evaluates", f"{did} ({site}) evaluated during {a}", REJECTED,
                      "inverted: the deciding function encloses the region's entity")  # fmt: skip
    return out


# evidence kinds that report what executed: a failure is an observed contradiction
_OBSERVED_KINDS = ("execution", "branch", "delta", "boundary", "outcome")


def establish_state(
    g: Genome,
    sub: StateSubstrate,
    agreement: dict[str, list[tuple[str, bool]]] | None = None,
    agreement_seq: dict[str, list[tuple[str, bool]]] | None = None,
    out_of_scope: set[str] | None = None,
    scenarios: dict[str, dict[str, Any]] | None = None,
) -> Genome:
    """Statuses over the stronger substrate. Same principle as `establish`: only evidence
    decides; decisions are verified through their site's observed outcomes and static
    control facts, transitions through observed state deltas."""
    items: list[Item] = [
        *g.variables, *g.data_dependencies, *g.decisions, *g.effects, *g.transitions,
        *g.procedures, *g.regions, *g.rules, *g.regimes,
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
    # literal bindings: usable only when the literal is allowed and written on its cited line
    for v in g.variables:
        for bd in bindings_of(v):
            if bd.get("kind") != "equals_literal":
                continue
            lit = bd.get("literal") or {}
            lit_ok = literal_canonical(lit) is not None and literal_in_source(lit, sub.source_root)
            bd["_literal_ok"] = lit_ok
            if not lit_ok and v.status != REJECTED:
                v.status = HYPOTHESIS
                v.status_reason = (
                    f"literal {lit.get('value')!r} is not an allowed literal written on "
                    f"{(lit.get('source') or {}).get('file')}:"
                    f"{(lit.get('source') or {}).get('line')}"
                )
    # identity claims: a variable observed at >= 2 identity boundaries. The proposal names
    # the correspondence; the equality itself is observed (digests), never assumed.
    for v in g.variables:
        if sum(1 for b in bindings_of(v) if bd.get("kind") == "identity") < 2:
            continue
        status, why, _, _ = identity_claim(v, sub.obs)
        if v.status == REJECTED or (
            v.status == HYPOTHESIS and not v.status_reason.startswith("no evidence cited")
        ):
            v.status_reason += f"; {why}"  # its citations failed: identity does not rescue it
        elif status:
            v.status, v.status_reason = status, why
        else:
            v.status_reason += f"; {why}"
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
            d.contradicted = True
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
    # occurrence agreement (regions only): at each shown occurrence where a decision's site
    # was evaluated, its predicate on that occurrence's supplied facts must give the observed
    # outcome. A disagreement cannot be attributed to the predicate or to the supplied fact,
    # so the decision is CONTESTED: demoted to hypothesis (predictions that need it stop),
    # never rejected. Agreement everywhere counts as support for verification.
    if scenarios and g.regions:
        sk_occ = build_skeleton(
            [ob.execution for ob in sub.obs.by_test.values()], genome_vocabulary(g)
        )
        per: dict[str, list[tuple[str, int, bool]]] = {}
        for test, sc in scenarios.items():
            ob = sub.obs.get(test)
            if ob is None:
                continue
            for did, found in occurrence_agreement(g, sc, ob, sk_occ).items():
                per.setdefault(did, []).extend((test, i, same) for i, same in found)
        for d in g.decisions:
            rows = per.get(d.id, [])
            bad = [r for r in rows if not r[2]]
            if bad and d.status in (SUPPORTED, VERIFIED):
                d.status = HYPOTHESIS
                d.status_reason = (
                    "contested: predicate disagrees with the observed outcome at "
                    + ("; ".join(f"{t.split('::')[-1]}[{i}]" for t, i, _ in bad[:3]))
                    + " given the supplied occurrence facts"
                )
            elif rows and d.status == SUPPORTED:
                d.status_reason += (
                    f"; agrees with the observed outcome at {len(rows)} occurrence evaluation(s)"
                )
    # transitions: observed deltas at the entity's calls, through variable bindings. When
    # a procedure places the transition (T:id), it is checked where the genome says it
    # happens: the entity's procedure is run from the call's observed entry state, and the
    # transition is compared only if that run reaches it.
    kinds = {
        v.name: (bindings_of(v)[0].get("kind", "is_set") if bindings_of(v) else "is_set")
        for v in g.variables
    }
    step_lists = [p.steps for p in g.procedures] + [r.steps for r in g.regions]
    placed = {st[2:] for steps in step_lists for st in steps if st.startswith("T:")}
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
                before = _bind(g, {**constant, **{a: b for a, b, _ in n.state}}, n, "entry", ob)
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
    # execution structure: where a procedure places calls and decisions, and their order,
    # judged against the skeleton of the observed executions
    sk = build_skeleton([ob.execution for ob in sub.obs.by_test.values()], genome_vocabulary(g))
    owners_by_id: dict[str, Item] = {q.id: q for q in (*g.procedures, *g.regions)}
    for c in procedure_structure_claims(g, sk):
        owner = owners_by_id[c["procedure"]]
        if c["status"] == REJECTED and owner.status != REJECTED:
            owner.status = REJECTED
            owner.status_reason = f"structure contradicted: {c['claim']}: {c['why']}"
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
    # the predicted occurrence tree: {"entity", "parent": index | None,
    # "events": [("call", entity) | ("branch", "site:<id>")]} (see diffgenome.structure)
    occurrences: list[dict[str, Any]] = field(default_factory=list)


def predict_sequence(
    g: Genome, scenario: dict[str, Any], min_status: str = SUPPORTED, max_depth: int = 12
) -> SeqPrediction:
    """Predict a sequence of calls under an initial state. Each call runs the entity's
    procedure (or, without one, its decisions in order); transitions change the state that
    later decisions read. Unestablished items that are needed stop the prediction."""
    decisions = {d.id: d for d in g.decisions}
    transitions = {t.id: t for t in g.transitions}
    procedures = {p.entity: p for p in g.procedures}
    regions = {r.id: r for r in g.regions}
    # occurrence facts are local to one occurrence; state-bound variables persist
    state_vars = {v.name for v in g.variables if any(b.get("fact") for b in bindings_of(v))}
    ctx: list[dict[str, Any]] = []  # the scenario item whose occurrences a region reads
    pred = SeqPrediction(state=dict(scenario.get("state") or {}))

    def usable(it: Item) -> bool:
        # eligibility: a supported item contradicted on a shown execution may not drive a
        # prediction; diagnostics that ask for hypothesis-level prediction still use it
        if it.contradicted and it.status != VERIFIED and min_status != HYPOTHESIS:
            return False
        return RANK.get(it.status, 0) >= RANK[min_status]

    def entity_key(e: str) -> str | None:
        for k in procedures:
            if k == e or k.endswith("." + e) or e.endswith("." + k):
                return k
        return None

    def new_occurrence(entity: str, parent: int | None) -> int:
        pred.occurrences.append({"entity": entity, "parent": parent, "events": []})
        if parent is not None:
            pred.occurrences[parent]["events"].append(("call", entity))
        return len(pred.occurrences) - 1

    def run_steps(steps: list[str], env: dict[str, Any], depth: int, occ: int) -> bool:
        """Returns True if the enclosing entity stops."""
        for st in steps:
            if pred.indeterminate:
                return True
            kind, _, ref = st.partition(":")
            if kind == "call":
                pred.events.append(("call", ref))
                key = entity_key(ref)
                child = new_occurrence(key or ref, occ)
                if key is not None:
                    run_entity(key, env, depth + 1, child)
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
            elif kind == "R":
                r = regions.get(ref)
                if r is None or not usable(r):
                    pred.indeterminate = f"region {ref} is {'missing' if r is None else r.status}"
                    return True
                items = (ctx[-1].get("occurrences") or {}).get(ref) if ctx else None
                if items is None:
                    pred.indeterminate = f"occurrence facts not supplied for region {ref}"
                    return True
                for k, item in enumerate(items):
                    before = dict(env)
                    env.update(item.get("facts") or {})
                    pred.events.append(("occurrence", ref, k))
                    ctx.append(item)
                    stopped = run_steps(r.steps, env, depth, occ)
                    ctx.pop()
                    for var in list(env):
                        if var in state_vars:
                            continue
                        if var in before:
                            env[var] = before[var]
                        else:
                            del env[var]
                    if stopped:  # `stops` ends the enclosing entity; there is no `continue`
                        return True
            elif kind == "D":
                d = decisions.get(ref)
                if d is None or not usable(d):
                    why = (
                        "missing"
                        if d is None
                        else (
                            f"{d.status}, contradicted on a shown execution"
                            if d.contradicted and d.status != VERIFIED
                            else d.status
                        )
                    )
                    pred.indeterminate = f"decision {ref} is {why}"
                    return True
                v = eval_predicate(d.predicate, derive(g, env))
                if v is None:
                    pred.indeterminate = f"{ref}: `{d.predicate}` needs facts it was not given"
                    return True
                if d.site:
                    pred.events.append(("branch", d.site, v))
                    pred.occurrences[occ]["events"].append(("branch", f"site:{d.site}"))
                b = d.true_branch if v else d.false_branch
                if b.outcome and b.outcome.get("is"):
                    pred.events.append(
                        ("outcome", b.outcome.get("entity") or d.entity, b.outcome["is"])
                    )
                inner = b.steps  # `calls` are descriptive (design-value-identity.md, 4)
                if run_steps(inner, env, depth, occ) or b.stops:
                    return True
            else:
                pred.indeterminate = f"unknown step {st!r}"
                return True
        return False

    def run_entity(key: str, env: dict[str, Any], depth: int, occ: int) -> None:
        if depth > max_depth:
            pred.indeterminate = f"depth limit at {key}"
            return
        p = procedures[key]
        if not usable(p):
            pred.indeterminate = f"procedure {p.id} ({key}) is {p.status}"
            return
        stopped = run_steps(p.steps, env, depth, occ)
        if not stopped and not pred.indeterminate and p.outcome and p.outcome.get("is"):
            pred.events.append(("outcome", p.outcome.get("entity") or p.entity, p.outcome["is"]))

    env = pred.state
    for call in scenario.get("calls") or []:
        env.update(call.get("facts") or {})
        e = call["entity"]
        pred.events.append(("call", e))
        key = entity_key(e)
        top = new_occurrence(key or e, None)
        ctx[:] = [call]
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
        run_entity(key, env, 0, top)
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
                stopped, prob = run(b.steps)
                if prob is not None:
                    return stopped, prob
                if stopped or b.stops:
                    return True, None
            elif kind == "R":
                return False, f"region {ref}: repetitions are not replayed"
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


def _occurrence_values(
    g: Genome,
    body: list[str],
    rep: dict[str, Any],
    occs: dict[int, Any],
    ob: ExecObs,
    vocab: list[str],
) -> dict[str, Any]:
    """What one observed repetition shows about the genome's variables: boundary facts of
    the calls inside it (boundary-bound variables), and the variables that atomic decisions
    reached from the region body (`v` / `!v`) bind from their outcomes in it."""
    out: dict[str, Any] = {}
    nodes = ob.execution.nodes
    inside = [occs[i] for i in rep["occurrences"]]
    for v in g.variables:
        for b in bindings_of(v):
            at = b.get("at")
            if not isinstance(at, dict) or v.name in out:
                continue
            if b.get("kind") == "equals_literal" and b.get("_literal_ok") is not True:
                continue
            target = resolve(vocab, str(at.get("entity", "")))
            vals = [
                boundary_fact(
                    nodes[o.id],
                    str(at.get("point", "")),
                    str(b.get("kind", "is_set")),
                    b.get("literal"),
                )
                for o in inside
                if o.entity == target
            ]
            vals = [x for x in vals if x is not None]
            if vals and all(x == vals[0] for x in vals[1:]):
                out[v.name] = vals[0]
    procedures = {p.entity: p for p in g.procedures}
    decisions = {d.id: d for d in g.decisions}
    first: dict[str, bool] = {}
    for site, outcome in rep["branches"]:
        first.setdefault(site, outcome)
    seen: set[str] = set()
    stack = [list(body)]
    while stack:
        for st in stack.pop():
            kind, _, ref = st.partition(":")
            if kind == "call":
                keys = [k for k in procedures if k == ref or k.endswith("." + ref)]
                keys += [k for k in procedures if ref.endswith("." + k)]
                key = keys[0] if keys else None
                if key is not None and key not in seen:
                    seen.add(key)
                    stack.append(list(procedures[key].steps))
            elif kind == "D" and ref in decisions and ref not in seen:
                seen.add(ref)
                d = decisions[ref]
                m = re.fullmatch(r"\s*(!?)\s*([\w.]+)\s*", d.predicate)
                if d.site in first and m and m.group(2) not in ("true", "false"):
                    out.setdefault(m.group(2), (not first[d.site]) if m.group(1) else first[d.site])
                for br in (d.true_branch, d.false_branch):
                    stack.append(br.steps)
    return out


def check_scenario_call_facts(
    g: Genome, scenario: dict[str, Any], ob: ExecObs
) -> list[dict[str, Any]]:
    """Facts a scenario states for one of its calls, for variables bound at that call's own
    boundary or within the execution (scope "execution"), compared with the aligned observed
    call (the k-th call of that entity). Identity variables carry labels, never decoded: the
    label pattern must equal the identity pattern (same label iff same identity)."""
    out: list[dict[str, Any]] = []
    pairs: list[tuple[str, Any, Any]] = []
    counts: dict[str, int] = {}
    kinds = {
        v.name: (bindings_of(v)[0].get("kind", "is_set") if bindings_of(v) else "is_set")
        for v in g.variables
    }
    for call in scenario.get("calls") or []:
        e = call["entity"]
        k = counts.get(e, 0)
        counts[e] = k + 1
        facts = call.get("facts") or {}
        if not facts:
            continue
        nodes = [
            n for n in ob.execution.nodes if isinstance(n, CallNode) and _name_match(e, n.symbol)
        ]
        if k >= len(nodes):
            continue
        n = nodes[k]
        seen = {
            **_bind(g, {a: b for a, b, _ in n.state}, n, "entry", ob),
            **_bind(g, {a: b for a, b, _ in n.state_after}, n, "exit", ob),
        }
        for var, val in facts.items():
            if var not in seen:
                continue
            if isinstance(seen[var], Identity):
                pairs.append((var, val, seen[var]))
                continue
            same = _abstract_equal(kinds.get(var, "is_set"), val, seen[var])
            out.append(
                {"call": e, "fact": var, "supplied": val, "observed": seen[var],
                 "status": "confirmed" if same else "contradicted"}
            )  # fmt: skip
    for i, (va, la, ia) in enumerate(pairs):
        for vb, lb, ib in pairs[i + 1 :]:
            consistent = (la == lb) == (ia == ib)
            out.append(
                {"fact": f"{va}={la!r} vs {vb}={lb!r}",
                 "status": "confirmed" if consistent else "contradicted",
                 "why": "" if consistent else (
                     "labels equal but identities differ" if la == lb
                     else "labels differ but identities are equal")}
            )  # fmt: skip
    return out


def check_scenario_occurrences(
    g: Genome, scenario: dict[str, Any], ob: ExecObs, sk: Skeleton
) -> list[dict[str, Any]]:
    """Align a scenario's supplied region occurrences with the observed repetitions (the
    k-th supplied occurrence with the k-th observed repetition of that region, inside the
    matching observed call) and check each supplied fact. Statuses: confirmed, contradicted,
    unobservable. A supplied count that differs from the observed count is contradicted."""
    vocab = sorted(set(genome_vocabulary(g)) | set(sk.seen))
    occs = occurrences(ob.execution, vocab)
    regions = {r.id: r for r in g.regions}
    out: list[dict[str, Any]] = []
    seen_calls: dict[str, int] = {}
    for call in scenario.get("calls") or []:
        e = resolve(vocab, call["entity"])
        k = seen_calls.get(e, 0)
        seen_calls[e] = k + 1
        supplied = call.get("occurrences") or {}
        if not supplied:
            continue
        cands = sorted((o for o in occs.values() if o.entity == e), key=lambda o: o.id)
        if k >= len(cands):
            out.append(
                {"call": e, "status": "contradicted", "why": f"no observed call #{k} of {e}"}
            )
            continue
        for rid, items in supplied.items():
            r = regions.get(rid)
            if r is None:
                continue
            head = _region_head(r, vocab)
            observed = [
                x for x in sk.regions.get(resolve(vocab, r.entity), []) if x["head"] == head
            ]
            if not observed:
                out.append({"region": rid, "status": "unobservable", "why": "no observed region"})
                continue
            # the region lives in its own entity: the scenario call's occurrence itself, or
            # the one occurrence of that entity running during it
            r_entity = resolve(vocab, r.entity)
            call_occ = cands[k]
            homes = [
                o
                for o in occs.values()
                if o.entity == r_entity
                and (o.id == call_occ.id or call_occ.entity in o.ancestors)
                and call_occ.first <= o.id <= call_occ.last
            ]
            if len(homes) != 1:
                out.append(
                    {"region": rid, "status": "unobservable",
                     "why": f"{len(homes)} occurrence(s) of {r_entity} in this call"}
                )  # fmt: skip
                continue
            reps = repetitions(occs, homes[0].id, observed[0]["members"], head)
            if len(reps) != len(items):
                out.append(
                    {"region": rid, "status": "contradicted",
                     "why": f"{len(items)} occurrence(s) supplied, {len(reps)} observed"}
                )  # fmt: skip
            for i, (item, rep) in enumerate(zip(items, reps, strict=False)):
                seen_vals = _occurrence_values(g, r.steps, rep, occs, ob, vocab)
                for var, val in (item.get("facts") or {}).items():
                    if var not in seen_vals:
                        status = "unobservable"
                    elif seen_vals[var] == val:
                        status = "confirmed"
                    else:
                        status = "contradicted"
                    out.append(
                        {"region": rid, "occurrence": i, "fact": var, "supplied": val,
                         "observed": seen_vals.get(var), "status": status}
                    )  # fmt: skip
    return out


def occurrence_agreement(
    g: Genome, scenario: dict[str, Any], ob: ExecObs, sk: Skeleton
) -> dict[str, list[tuple[int, bool]]]:
    """Per decision: at every evaluation of its site inside an aligned occurrence of a
    region, (occurrence ordinal, whether its predicate on that occurrence's supplied facts,
    plus the scenario call's facts, gives the observed outcome). Only meaningful where the
    checker can see the execution (shown tests)."""
    vocab = sorted(set(genome_vocabulary(g)) | set(sk.seen))
    occs = occurrences(ob.execution, vocab)
    regions = {r.id: r for r in g.regions}
    decisions = [d for d in g.decisions if d.site]
    out: dict[str, list[tuple[int, bool]]] = {}
    seen_calls: dict[str, int] = {}
    for call in scenario.get("calls") or []:
        e = resolve(vocab, call["entity"])
        k = seen_calls.get(e, 0)
        seen_calls[e] = k + 1
        cands = sorted((o for o in occs.values() if o.entity == e), key=lambda o: o.id)
        if k >= len(cands):
            continue
        call_occ = cands[k]
        for rid, items in (call.get("occurrences") or {}).items():
            r = regions.get(rid)
            if r is None:
                continue
            head = _region_head(r, vocab)
            observed = [
                x for x in sk.regions.get(resolve(vocab, r.entity), []) if x["head"] == head
            ]
            homes = [
                o for o in occs.values()
                if o.entity == resolve(vocab, r.entity)
                and (o.id == call_occ.id or call_occ.entity in o.ancestors)
                and call_occ.first <= o.id <= call_occ.last
            ]  # fmt: skip
            if not observed or len(homes) != 1:
                continue
            reps = repetitions(occs, homes[0].id, observed[0]["members"], head)
            if len(reps) != len(items):
                continue
            for i, (item, rp) in enumerate(zip(items, reps, strict=True)):
                env = derive(g, {**(call.get("facts") or {}), **(item.get("facts") or {})})
                for d in decisions:
                    outcomes = [v for site, v in rp["branches"] if site == d.site]
                    if not outcomes:
                        continue
                    val = eval_predicate(d.predicate, env)
                    if val is None:
                        continue
                    out.setdefault(d.id, []).extend((i, val == o) for o in outcomes)
    return out


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
    skeleton: Skeleton | None = None,
    scenario: dict[str, Any] | None = None,
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
    kinds = {
        v.name: (bindings_of(v)[0].get("kind", "is_set") if bindings_of(v) else "is_set")
        for v in g.variables
    }
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
    # observed execution structure: a prediction that places a call or a decision where it
    # was never observed (hoisted out of a modeled caller, or evaluated in the wrong call)
    # predicts a structure the evidence does not have: indeterminate, never a guess
    placement: list[str] = []
    if skeleton is not None:
        vocab = sorted(skeleton.seen)
        tree = [{**o, "entity": resolve(vocab, o["entity"])} for o in pred.occurrences]
        placement = placement_problems(tree, skeleton)
    # supplied occurrence facts, where the checker can see the execution: a scenario that is
    # wrong about its own input cannot support a prediction
    occ_checks: list[dict[str, Any]] = []
    if skeleton is not None and scenario is not None:
        occ_checks = check_scenario_call_facts(g, scenario, ob)
        if g.regions:
            occ_checks += check_scenario_occurrences(g, scenario, ob, skeleton)
    contradicted = [c for c in occ_checks if c["status"] == "contradicted"]
    indeterminate = (
        pred.indeterminate
        or (f"no decision covers observed site(s) {', '.join(uncovered)}" if uncovered else None)
        or (f"placement: {'; '.join(placement[:3])}" if placement else None)
        or (
            "occurrence facts contradicted: "
            + "; ".join(
                f"{c.get('region')}[{c.get('occurrence', '?')}] {c.get('fact', '')} "
                f"{c.get('why', '')}".strip()
                for c in contradicted[:3]
            )
            if contradicted
            else None
        )
    )
    return {
        "execution": ob.execution.stimulus_ref,
        "indeterminate": indeterminate,
        "uncovered_sites": uncovered,
        "placement_problems": placement,
        "occurrence_checks": {
            st: sum(1 for c in occ_checks if c["status"] == st)
            for st in ("confirmed", "contradicted", "unobservable")
        },
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
