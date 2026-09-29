"""Observed execution structure: occurrences and a generalized skeleton (Experiment 10, v3).

Call nesting and chronology are runtime facts, not semantics, so a proposer should not be
free to invent them. This module derives them deterministically, relative to a vocabulary
(the entity names a genome uses), from the existing event protocol: node ids are creation
order, parents precede children, and a branch observation names its call node and a `seq`
on the same clock. No collector change is needed.

Two objects, kept apart:

- **Occurrence graph** (evidence, one execution). Every observed call of a vocabulary
  entity is an occurrence: its id is the call node id; its parent is the nearest ancestor
  call that is also a vocabulary entity (other frames are looked through; None = no modeled
  ancestor); its ordinal counts earlier siblings of the same entity under the same parent;
  its events are its child occurrences and the branch evaluations made in its own call, in
  time order; its outcome is the call's exit. The runtime records no call-site ids, so
  repeated calls are keyed by (parent occurrence, entity, ordinal).

- **Skeleton** (deterministic abstraction over the shown executions). Per entity: which
  vocabulary entities were observed as its *ancestors* and whether it was observed with no
  modeled ancestor (ROOT), with support. Per parent entity: pairwise precedence among the
  event families of its occurrences (child entities, and its own decision sites as
  `site:<id>`): `x ≺ y` when, in every occurrence where both occur, every x precedes every y;
  families that interleave in some occurrence are recorded as interleaved (a repeated
  region). Nothing is said about why a region repeats or how often.

Checks built on these (used by `genome_state`):
- a predicted occurrence of B under P (or at the top of a scenario) that no observed
  occurrence of B supports is a placement problem: B was never observed during P (or B was
  never observed without a modeled ancestor);
- a predicted order x-then-y inside an occurrence of A, where `y ≺ x` held in every shown
  occurrence of A with both, is an order problem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from diffgenome.model import CallNode, Execution, SubstitutionNode

ROOT = "<root>"


def _tail(symbol: str) -> str:
    return symbol.split(":", 1)[1] if symbol[:3] in ("go:", "py:", "js:") else symbol


def _matches(claimed: str, symbol: str) -> bool:
    t, c = _tail(symbol), _tail(claimed)
    return t == c or t.endswith("." + c)


def canonical(vocab: list[str], symbol: str) -> str | None:
    """The vocabulary name an observed symbol belongs to; the longest match wins."""
    hits = [v for v in vocab if _matches(v, symbol)]
    return max(hits, key=len) if hits else None


def _node_symbol(n: Any) -> str:
    if isinstance(n, CallNode):
        return n.symbol
    if isinstance(n, SubstitutionNode):
        return n.claimed_target or ""
    return ""


@dataclass
class Occurrence:
    id: int  # the call node id
    entity: str  # vocabulary name
    parent: int | None  # parent occurrence id (nearest modeled ancestor), None at the top
    ancestors: list[str]  # vocabulary entities of every modeled ancestor, nearest first
    ordinal: int  # earlier siblings of the same entity under the same parent
    first: int
    last: int  # the occurrence covers node ids / branch seqs in [first, last]
    events: list[tuple[str, str, Any]] = field(default_factory=list)
    # ("call", <entity>, <child occurrence id>) | ("branch", "site:<id>", <outcome>)
    outcome: str = "unknown"


def occurrences(ex: Execution, vocab: list[str]) -> dict[int, Occurrence]:
    nodes = ex.nodes
    name: dict[int, str] = {}
    for n in nodes:
        c = canonical(vocab, _node_symbol(n))
        if c is not None:
            name[n.id] = c
    last = {n.id: n.id for n in nodes}
    for n in reversed(nodes):  # a subtree's last id, children before parents
        if n.parent is not None:
            last[n.parent] = max(last[n.parent], last[n.id])
    out: dict[int, Occurrence] = {}
    counts: dict[tuple[int | None, str], int] = {}
    for n in nodes:  # ids are creation order: parents come first
        if n.id not in name:
            continue
        p = n.parent
        chain: list[int] = []
        while p is not None:
            if p in name:
                chain.append(p)
            p = nodes[p].parent
        parent = chain[0] if chain else None
        k = (parent, name[n.id])
        ordinal = counts.get(k, 0)
        counts[k] = ordinal + 1
        occ = Occurrence(
            n.id, name[n.id], parent, [name[a] for a in chain], ordinal, n.id, last[n.id],
            outcome=getattr(n, "outcome", "unknown"),
        )  # fmt: skip
        out[n.id] = occ
    # events in time order: a child occurrence at its node id; a branch, which belongs to
    # the occurrence of its own call node, at its seq (a branch at seq s precedes node s)
    times: dict[int, list[tuple[int, int, tuple[str, str, Any]]]] = {o: [] for o in out}
    for occ in out.values():
        if occ.parent is not None:
            times[occ.parent].append((occ.id, 1, ("call", occ.entity, occ.id)))
    for b in ex.branches:
        if b.node in out:
            times[b.node].append((b.seq, 0, ("branch", f"site:{b.site}", b.outcome)))
    for oid, evs in times.items():
        out[oid].events = [e for _, _, e in sorted(evs, key=lambda t: (t[0], t[1]))]
    return out


@dataclass
class Skeleton:
    """Deterministic structure over several executions (see module doc)."""

    executions: int = 0
    # entity -> {ancestor entity | ROOT: number of executions where observed so}
    ancestry: dict[str, dict[str, int]] = field(default_factory=dict)
    # entity -> {nearest modeled parent | ROOT: executions}
    parents: dict[str, dict[str, int]] = field(default_factory=dict)
    # parent entity -> {(x, y): [occurrences with both, executions with both]} where x ≺ y
    before: dict[str, dict[tuple[str, str], list[int]]] = field(default_factory=dict)
    # parent entity -> pairs that interleave in at least one occurrence
    interleaved: dict[str, set[frozenset[str]]] = field(default_factory=dict)
    # parent entity -> family -> [occurrences containing it, max count in one occurrence]
    families: dict[str, dict[str, list[int]]] = field(default_factory=dict)
    # entity -> number of occurrences observed
    seen: dict[str, int] = field(default_factory=dict)
    # entity -> occurrences of it observed with each modeled ancestor (any depth)
    inside_occ: dict[str, dict[str, int]] = field(default_factory=dict)
    # site -> {entity | ROOT: evaluations}: the occurrence evaluating it and its ancestors
    site_during: dict[str, dict[str, int]] = field(default_factory=dict)
    # site -> {entity: evaluations}: the occurrence evaluating it in its own call
    site_owner: dict[str, dict[str, int]] = field(default_factory=dict)
    # parent entity -> repeated regions: {"members": [...], "head": family | None,
    #   "within": {(x, y): segments} (x before y inside one repetition), "max_repeats": n}
    regions: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def observed_inside(self, entity: str, parent: str) -> bool:
        """Some observed occurrence of `entity` ran during an occurrence of `parent`
        (`parent` among its modeled ancestors, any depth); ROOT: with no modeled ancestor."""
        return self.ancestry.get(entity, {}).get(parent, 0) > 0

    def always_during(self, entity: str, enclosing: str) -> bool:
        """Every observed occurrence of `entity` ran during `enclosing` (and there is one)."""
        n = self.seen.get(entity, 0)
        return n > 0 and self.inside_occ.get(entity, {}).get(enclosing, 0) == n

    def strictly_before(self, parent: str, x: str, y: str) -> bool:
        """x ≺ y in every shown occurrence of `parent` containing both (and at least one)."""
        return (x, y) in self.before.get(parent, {}) and frozenset((x, y)) not in (
            self.interleaved.get(parent, set())
        )


def build_skeleton(executions: list[Execution], vocab: list[str]) -> Skeleton:
    sk = Skeleton(executions=len(executions))
    for ex in executions:
        occs = occurrences(ex, vocab)
        anc_seen: dict[str, set[str]] = {}
        par_seen: dict[str, set[str]] = {}
        pair_exec: dict[str, set[tuple[str, str]]] = {}
        for o in occs.values():
            sk.seen[o.entity] = sk.seen.get(o.entity, 0) + 1
            io = sk.inside_occ.setdefault(o.entity, {})
            for a in set(o.ancestors) or {ROOT}:
                io[a] = io.get(a, 0) + 1
            for kind, fam, _ in o.events:
                if kind == "branch":
                    so = sk.site_owner.setdefault(fam[5:], {})
                    so[o.entity] = so.get(o.entity, 0) + 1
                    sd = sk.site_during.setdefault(fam[5:], {})
                    for a in {o.entity, *o.ancestors}:
                        sd[a] = sd.get(a, 0) + 1
            anc_seen.setdefault(o.entity, set()).update(o.ancestors or [ROOT])
            par_seen.setdefault(o.entity, set()).add(
                occs[o.parent].entity if o.parent is not None else ROOT
            )
            positions: dict[str, list[int]] = {}
            for i, (_, fam, _) in enumerate(o.events):
                positions.setdefault(fam, []).append(i)
            fams = sk.families.setdefault(o.entity, {})
            for fam, pos in positions.items():
                rec = fams.setdefault(fam, [0, 0])
                rec[0] += 1
                rec[1] = max(rec[1], len(pos))
            names = sorted(positions)
            for i, x in enumerate(names):
                for y in names[i + 1 :]:
                    px, py = positions[x], positions[y]
                    if max(px) < min(py):
                        key = (x, y)
                    elif max(py) < min(px):
                        key = (y, x)
                    else:
                        sk.interleaved.setdefault(o.entity, set()).add(frozenset((x, y)))
                        continue
                    rec2 = sk.before.setdefault(o.entity, {}).setdefault(key, [0, 0])
                    rec2[0] += 1
                    pair_exec.setdefault(o.entity, set()).add(key)
        for e, s in anc_seen.items():
            for a in s:
                sk.ancestry.setdefault(e, {})[a] = sk.ancestry.setdefault(e, {}).get(a, 0) + 1
        for e, s in par_seen.items():
            for p in s:
                sk.parents.setdefault(e, {})[p] = sk.parents.setdefault(e, {}).get(p, 0) + 1
        for parent, keys in pair_exec.items():
            for key in keys:
                sk.before[parent][key][1] += 1
    # a pair observed in both orders (in different occurrences) is not an order
    for parent, pairs in sk.before.items():
        for x, y in list(pairs):
            if (y, x) in pairs:
                sk.interleaved.setdefault(parent, set()).add(frozenset((x, y)))
    all_occs = [occurrences(ex, vocab) for ex in executions]
    for parent, pairs_i in sk.interleaved.items():
        for members in _components(pairs_i):
            sk.regions.setdefault(parent, []).append(
                _segment(parent, members, [o for occs in all_occs for o in occs.values()])
            )
    return sk


def _components(pairs: set[frozenset[str]]) -> list[list[str]]:
    """Families connected by interleaving: one repeated region each."""
    adj: dict[str, set[str]] = {}
    for pair in pairs:
        a, b = sorted(pair)
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    seen: set[str] = set()
    out: list[list[str]] = []
    for start in sorted(adj):
        if start in seen:
            continue
        comp, stack = [], [start]
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            comp.append(x)
            stack.extend(adj[x] - seen)
        out.append(sorted(comp))
    return out


def _segment(parent: str, members: list[str], occs: list[Occurrence]) -> dict[str, Any]:
    """A repeated region's head is a member that starts every repetition: in every
    occurrence of `parent`, the region's events begin with it and, between consecutive
    heads, every other member appears at most once. With a head, the order of members
    inside one repetition is recorded (x before y in every segment holding both). Without
    one, only membership is known."""
    mine = [o for o in occs if o.entity == parent]
    seqs = [[f for _, f, _ in o.events if f in members] for o in mine]
    seqs = [q for q in seqs if q]

    def segments(head: str, seq: list[str]) -> list[list[str]] | None:
        if seq[0] != head:
            return None
        segs: list[list[str]] = []
        for f in seq:
            if f == head:
                segs.append([f])
            elif f in segs[-1]:
                return None
            else:
                segs[-1].append(f)
        return segs

    for head in members:
        split = [segments(head, q) for q in seqs]
        if not seqs or any(sp is None for sp in split):
            continue
        segs = [seg for sp in split for seg in sp or []]
        within: dict[tuple[str, str], int] = {}
        bad: set[tuple[str, str]] = set()
        for seg in segs:
            for i, x in enumerate(seg):
                for y in seg[i + 1 :]:
                    within[(x, y)] = within.get((x, y), 0) + 1
                    bad.add((y, x))
        return {
            "members": members,
            "head": head,
            "within": {k: v for k, v in within.items() if k not in bad},
            "max_repeats": max(len(sp or []) for sp in split),
        }
    return {"members": members, "head": None, "within": {}, "max_repeats": None}


def _within_problems(e: str, fams: list[str], sk: Skeleton) -> list[str]:
    out: list[str] = []
    for region in sk.regions.get(e, []):
        head, members = region["head"], region["members"]
        if head is None:
            continue
        segs: list[list[str]] = []
        for f in fams:
            if f not in members:
                continue
            if f == head or not segs:
                segs.append([f])
            else:
                segs[-1].append(f)
        for seg in segs:
            for i, x in enumerate(seg):
                for y in seg[i + 1 :]:
                    if x != y and (y, x) in region["within"]:
                        out.append(
                            f"inside {e}, one repetition: {x} predicted before {y}, observed after"
                        )
    return out


def placement_problems(pred_occurrences: list[dict[str, Any]], sk: Skeleton) -> list[str]:
    """Problems of a predicted occurrence tree against the skeleton. Each predicted
    occurrence: {"entity", "parent": index | None, "events": [(kind, family), ...]}.
    Only entities the skeleton has observed are judged; nothing unobserved is assumed."""
    problems: list[str] = []
    for occ in pred_occurrences:
        e = occ["entity"]
        if sk.seen.get(e, 0) == 0:
            continue
        parent = pred_occurrences[occ["parent"]]["entity"] if occ["parent"] is not None else ROOT
        if not sk.observed_inside(e, parent):
            where = "outside every modeled caller" if parent == ROOT else f"during {parent}"
            problems.append(f"{e} placed {where}, never observed so")
        for kind, fam in occ["events"]:
            during = sk.site_during.get(fam[5:]) if kind == "branch" else None
            if during is not None and e not in during:
                problems.append(f"{fam} predicted during {e}, never evaluated there")
        fams = [f for _, f in occ["events"]]
        for i, x in enumerate(fams):
            for y in fams[i + 1 :]:
                if x != y and sk.strictly_before(e, y, x):
                    problems.append(f"inside {e}: {x} predicted before {y}, observed after")
        problems += _within_problems(e, fams, sk)
    return sorted(set(problems))


def render(sk: Skeleton, focus: list[str] | None = None) -> str:
    """Text for a proposer: containment and phase order, with support."""
    lines = [f"(from {sk.executions} shown execution(s))"]
    for e in sorted(sk.parents):
        if focus and e not in focus:
            continue
        par = ", ".join(f"{p} (in {n} exec)" for p, n in sorted(sk.parents[e].items()))
        anc = ", ".join(f"{a} (in {n} exec)" for a, n in sorted(sk.ancestry.get(e, {}).items()))
        lines.append(f"- {e}: {sk.seen.get(e, 0)} occurrence(s)")
        lines.append(f"    nearest modeled caller: {par}")
        lines.append(f"    runs during: {anc}")
    for parent in sorted(sk.families):
        if focus and parent not in focus:
            continue
        fams = sk.families[parent]
        if len(fams) < 2:
            continue
        lines.append(f"\ninside {parent}:")
        for fam, (n_occ, max_n) in sorted(fams.items()):
            rep = f"repeated (up to {max_n} in one occurrence)" if max_n > 1 else "once"
            lines.append(f"  family {fam}: in {n_occ} occurrence(s), {rep}")
        for (x, y), (n_occ, n_ex) in sorted(sk.before.get(parent, {}).items()):
            if sk.strictly_before(parent, x, y):
                lines.append(f"  {x} BEFORE {y}  (all of the first before all of the second;")
                lines.append(f"      {n_occ} occurrence(s), {n_ex} execution(s))")
        for region in sk.regions.get(parent, []):
            lines.append(f"  REPEATED REGION: {', '.join(region['members'])}")
            if region["head"] is None:
                lines.append("    (no member starts every repetition: only membership is known)")
                continue
            lines.append(
                f"    each repetition starts with {region['head']} "
                f"(up to {region['max_repeats']} repetitions in one occurrence); inside one:"
            )
            for (x, y), n in sorted(region["within"].items()):
                lines.append(f"      {x} BEFORE {y}  ({n} repetition(s))")
    return "\n".join(lines)


def resolve(vocab: list[str], name: str) -> str:
    """A genome/scenario entity name to the vocabulary name it denotes (itself if none)."""
    hits = [v for v in vocab if v == name or v.endswith("." + name) or name.endswith("." + v)]
    return max(hits, key=len) if hits else name
