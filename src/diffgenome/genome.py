"""Behavioral Genome IR (experimental, ``diffgenome-genome/0``).

A semantic layer above the evidence graph. The graph says what executed, what was
reconstructed and where knowledge stops; the genome says *why* paths differ: which inputs
and state feed which decisions, what each branch does, and which compact rules generate
the observed paths. An execution is a phenotype of the genome under one input/state.

Hard invariant: model output never becomes fact by itself. Every semantic item carries
``derived_by`` and ``evidence``, and its ``status`` is assigned here, deterministically,
by checking that evidence against the substrate (traces, graph, source):

    observed_fact  collected at runtime (entities, paths, decoded return values)
    static_fact    read from source text at a cited line
    hypothesis     proposed; its evidence does not (fully) check out, or none was cited
    supported      proposed; every cited reference checks out, but not both branches
                   of the rule are observed at runtime
    verified       supported, the predicate is present at the cited source line, and
                   every branch's outcome and consequence is observed in some execution
                   with no contradicting execution
    rejected       an observed execution contradicts it

Nothing here is a production API. It exists to test whether evidence + bounded model
abstraction yields a generative description of behavior.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from dataclasses import fields as dataclass_fields
from pathlib import Path
from typing import Any

from diffgenome.compose import Corpus
from diffgenome.model import CallNode, Execution, SubstitutionNode

FORMAT = "diffgenome-genome/0"
CHECKER_VERSION = "genome-check/0"

OBSERVED = "observed_fact"
STATIC = "static_fact"
HYPOTHESIS = "hypothesis"
SUPPORTED = "supported"
VERIFIED = "verified"
REJECTED = "rejected"


# --------------------------------------------------------------------------- substrate


def _digest(canonical: str) -> str:
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


# Collectors digest scalars as sha256 of a canonical form; a boolean result is decodable.
_BOOL_BY_DIGEST = {
    _digest("bool:true"): "true",  # Go collector canonical form
    _digest("bool:false"): "false",
}


@dataclass
class Step:
    """One direct child of a call in one execution, in order."""

    symbol: str  # callee, or "stand-in:<path>" for a substituted call
    outcome: str
    result: str | None  # decoded scalar ("true"/"false") when the digest is decodable
    children: list[Step] = field(default_factory=list)


@dataclass
class ExecutionPath:
    execution: str  # test id
    outcome: str  # passed / failed
    root: str  # the entity the path is rooted at
    steps: list[Step]

    def calls(self) -> list[str]:
        out: list[str] = []

        def walk(steps: list[Step]) -> None:
            for s in steps:
                out.append(s.symbol)
                walk(s.children)

        walk(self.steps)
        return out

    def result_of(self, symbol: str) -> str | None:
        def walk(steps: list[Step]) -> str | None:
            for s in steps:
                if s.symbol == symbol and s.result is not None:
                    return s.result
                r = walk(s.children)
                if r is not None:
                    return r
            return None

        return walk(self.steps)


def _short(symbol: str) -> str:
    """Language-neutral display name: drop the runtime prefix and package path."""
    name = symbol.split(":", 1)[1] if ":" in symbol else symbol
    return name.rsplit("/", 1)[-1]


def _node_step(ex: Execution, node: Any, depth: int) -> Step:
    if isinstance(node, SubstitutionNode):
        target = node.claimed_target or node.substitute or "?"
        path = ".".join(node.path)
        sym = "stand-in:" + (
            _short(target) if not path else _short(target).rsplit(".", 1)[0] + "." + path
        )
        return Step(sym, node.outcome, None)
    children: list[Step] = []
    if depth > 0:
        children = [
            _node_step(ex, k, depth - 1)
            for k in ex.nodes
            if getattr(k, "parent", None) == node.id and isinstance(k, CallNode | SubstitutionNode)
        ]
    return Step(_short(node.symbol), node.outcome, _BOOL_BY_DIGEST.get(node.result or ""), children)


def execution_paths(corpus: Corpus, root_symbol: str, depth: int = 2) -> list[ExecutionPath]:
    """Every execution that ran `root_symbol`, as its ordered call steps to `depth`."""
    out: list[ExecutionPath] = []
    for ex_id in sorted(corpus.executions):
        ex = corpus.executions[ex_id]
        roots = [n for n in ex.nodes if isinstance(n, CallNode) and n.symbol == root_symbol]
        if not roots:
            continue
        root = roots[0]
        steps = [
            _node_step(ex, k, depth - 1)
            for k in ex.nodes
            if getattr(k, "parent", None) == root.id and isinstance(k, CallNode | SubstitutionNode)
        ]
        out.append(ExecutionPath(ex.stimulus_ref, ex.outcome, _short(root_symbol), steps))
    return out


_IF = re.compile(r"^\s*(?:\}\s*else\s+)?if\s+(.+?)\s*\{\s*$")


def static_decision_sites(source_root: Path, files: list[str]) -> list[dict[str, Any]]:
    """Cheap, deterministic: every `if <cond> {` line in the given files. No semantics."""
    sites: list[dict[str, Any]] = []
    for rel in files:
        path = source_root / rel
        if not path.is_file():
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            m = _IF.match(line)
            if m:
                sites.append({"file": rel, "line": i, "condition": m.group(1)})
    return sites


# --------------------------------------------------------------------------- schema


@dataclass
class EvidenceRef:
    """A checkable claim about the substrate.

    kind="source":      file, line, text  (text must occur on that line)
    kind="execution":   test, calls (must occur, in order), absent (must not occur),
                        returns {symbol: value}  (decoded return value must match)
    kind="edge":        caller, callee (must be an observed edge in the graph)
    """

    kind: str
    file: str | None = None
    line: int | None = None
    text: str | None = None
    test: str | None = None
    calls: list[str] = field(default_factory=list)
    absent: list[str] = field(default_factory=list)
    returns: dict[str, str] = field(default_factory=dict)
    caller: str | None = None
    callee: str | None = None
    # mechanics / state kinds (see genome_state):
    #   kind="branch":   site, test, outcome     (the site evaluated to outcome in that test)
    #   kind="control":  site, outcome, callee   (static: callee is reached only under it)
    #   kind="dataflow": site, origin            (static: an operand of site originates there)
    #   kind="delta":    entity, fact, before, after, test (observed bucket change)
    #   kind="store":    entity, path            (static: entity writes that field)
    #   kind="boundary": entity, point, binding, value, test
    #                    (a call of entity in that test had that boundary fact, 5.1)
    #   kind="outcome":  entity, exit, test      (a call of entity in that test ended so)
    site: str | None = None
    outcome: bool | None = None
    origin: str | None = None
    entity: str | None = None
    fact: str | None = None
    before: str | None = None
    after: str | None = None
    path: str | None = None
    point: str | None = None  # "arg:<name>" | "result"
    binding: str | None = None  # is_set | changed_from:arg:<name> | size | bool
    value: Any = None
    exit: str | None = None  # returned | returned-error[:k] | raised[:k] | panic[:k] | cancelled
    # filled by the checker
    ok: bool | None = None
    why: str = ""
    # the reference could not be placed (e.g. a site id nothing knows): its failure is
    # missing support, not a contradiction by observation
    unanchored: bool = False


@dataclass
class Item:
    """Common envelope of every genome element."""

    id: str
    derived_by: str  # "collector" | "static-scan" | "llm:<model>"
    evidence: list[EvidenceRef] = field(default_factory=list)
    status: str = HYPOTHESIS
    status_reason: str = ""


@dataclass
class Entity(Item):
    symbol: str = ""
    role: str = ""  # entry | decision | effect | lookup | boundary | ...


@dataclass
class Variable(Item):
    name: str = ""  # e.g. request.amount, from_account.balance
    origin: str = ""  # request | state | derived | environment
    description: str = ""
    # machine-readable definition of a derived variable, in predicate syntax over other
    # variables (e.g. "from_account.balance >= request.amount"); None when not derived
    definition: str | None = None
    # binding to an observed state fact, e.g. {"fact": "self._backend", "kind": "is_set"};
    # kinds: is_set (bucket != none), bool (bool:true/false), sign (num:neg/zero/pos)
    observed_as: dict[str, str] | None = None


@dataclass
class DataDependency(Item):
    source: str = ""  # variable name
    sink: str = ""  # decision id or entity
    transform: str | None = None


@dataclass
class Branch:
    """What happens when a decision's predicate evaluates to `when`."""

    when: bool
    returns: str | None = None  # decoded return value of the deciding function, if any
    calls: list[str] = field(default_factory=list)  # entities reached, in order
    absent: list[str] = field(default_factory=list)  # entities never reached
    stops: bool = False  # the enclosing entry returns after this branch
    effect: str = ""  # human description
    # ordered steps for state-sequence prediction: "call:<entity>", "T:<transition id>",
    # "D:<decision id>"; when empty, `calls` is used
    steps: list[str] = field(default_factory=list)
    # how far `absent` reaches after the site is evaluated (genome_state):
    #   "episode" (default): until the next evaluation of the same site or the next call of
    #     the deciding function, and within a loop until control leaves the loop; the
    #     caller's continuation only when this branch exits the deciding function;
    #   "run": everything after, including deferred callbacks and later iterations
    absent_scope: str = "episode"
    # the exit this branch leads to: {"entity": <function>, "is": <exit>}; the entity may be
    # the deciding function or one enclosing it (an effect that surfaces later in the same
    # episode). Exits are the collector's categories (model.Outcome), never test results.
    outcome: dict[str, str] | None = None


@dataclass
class Decision(Item):
    entity: str = ""  # where the predicate lives
    site: str | None = None  # decision-site id (diffgenome.sites) when known
    inputs: list[str] = field(default_factory=list)  # variable names
    predicate: str = (
        ""  # symbolic, over variable names, e.g. "request.amount > from_account.balance"
    )
    order: int = 0  # position along the entry's path (earlier decisions gate later ones)
    true_branch: Branch = field(default_factory=lambda: Branch(True))
    false_branch: Branch = field(default_factory=lambda: Branch(False))


@dataclass
class Effect(Item):
    kind: str = ""  # response | persistence | external | none
    target: str = ""
    condition: str = ""  # decision/rule ids that enable it


@dataclass
class Transition(Item):
    state_before: str = ""
    action: str = ""
    state_after: str = ""
    # machine-readable form: when `entity` runs and `when` holds, variables become `sets`
    # (expressions: literals, `var`, `!var`, `var + k`, `var - k`, `max(0, var - k)`)
    entity: str = ""
    when: str = "true"
    sets: dict[str, str] = field(default_factory=dict)


@dataclass
class Procedure(Item):
    """Ordered behavior of one entity: "call:<entity>", "T:<transition>", "D:<decision>"."""

    entity: str = ""
    steps: list[str] = field(default_factory=list)
    # the entity's exit when its steps complete without a stopping branch
    outcome: dict[str, str] | None = None


@dataclass
class Region(Item):
    """A repeated region inside one entity (docs/design-occurrence-binding.md). Mechanics
    supply where it lives and what belongs to it (`head`: the observed family that starts
    each repetition); the scenario supplies each concrete occurrence's facts; `steps` is the
    one body every occurrence runs. A procedure places it with the step "R:<id>"."""

    entity: str = ""
    head: str = ""
    steps: list[str] = field(default_factory=list)


@dataclass
class Rule(Item):
    name: str = ""
    inputs: list[str] = field(default_factory=list)
    relevant_state: list[str] = field(default_factory=list)
    condition: str = ""
    consequences: list[str] = field(default_factory=list)
    decision: str | None = None  # the decision it summarizes, when there is one


@dataclass
class Regime(Item):
    """A behavioral equivalence class: executions the genome says behave alike."""

    name: str = ""
    facts: dict[str, Any] = field(default_factory=dict)  # input/state facts that define it
    members: list[str] = field(default_factory=list)  # tests in the class


@dataclass
class Genome:
    subject: dict[str, Any]
    entities: list[Entity] = field(default_factory=list)
    variables: list[Variable] = field(default_factory=list)
    data_dependencies: list[DataDependency] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    effects: list[Effect] = field(default_factory=list)
    transitions: list[Transition] = field(default_factory=list)
    procedures: list[Procedure] = field(default_factory=list)
    regions: list[Region] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)
    regimes: list[Regime] = field(default_factory=list)
    unknowns: list[dict[str, Any]] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        doc = asdict(self)
        return {"format": FORMAT, **doc}


# --------------------------------------------------------------------------- loading


def _ref(d: dict[str, Any]) -> EvidenceRef:
    keys = EvidenceRef.__dataclass_fields__
    return EvidenceRef(
        **{k: v for k, v in d.items() if k in keys and k not in ("ok", "why", "unanchored")}
    )


def _branch(d: dict[str, Any] | None, when: bool) -> Branch:
    d = d or {}
    return Branch(
        when=when,
        returns=d.get("returns"),
        calls=list(d.get("calls") or []),
        absent=list(d.get("absent") or []),
        stops=bool(d.get("stops")),
        effect=str(d.get("effect") or ""),
        steps=list(d.get("steps") or []),
        absent_scope=str(d.get("absent_scope") or "episode"),
        outcome=dict(d["outcome"]) if isinstance(d.get("outcome"), dict) else None,
    )


def _item_kwargs(d: dict[str, Any], cls: type, derived_by: str) -> dict[str, Any]:
    fields_ = {f.name for f in dataclass_fields(cls)}
    kw = {
        k: v
        for k, v in d.items()
        if k in fields_ and k not in ("evidence", "status", "status_reason", "derived_by")
    }
    kw["derived_by"] = derived_by
    kw["evidence"] = [_ref(e) for e in d.get("evidence") or []]
    return kw


def _expr_text(v: Any) -> str:
    """Transition expressions are text; JSON literals are accepted and written as the
    expression language spells them (true/false/none/integers). Experiment 11, Case C: a
    proposal wrote `true` and `1` as JSON values and the checker crashed on them."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "none"
    return str(v)


def genome_from_proposals(proposals: dict[str, Any], subject: dict[str, Any], model: str) -> Genome:
    """Load model proposals into the schema. Everything starts as a hypothesis."""
    by = f"llm:{model}"
    g = Genome(subject=subject)
    for d in proposals.get("variables") or []:
        g.variables.append(Variable(**_item_kwargs(d, Variable, by)))
    for d in proposals.get("data_dependencies") or []:
        g.data_dependencies.append(DataDependency(**_item_kwargs(d, DataDependency, by)))
    for d in proposals.get("decisions") or []:
        kw = _item_kwargs(d, Decision, by)
        kw["true_branch"] = _branch(d.get("true_branch"), True)
        kw["false_branch"] = _branch(d.get("false_branch"), False)
        g.decisions.append(Decision(**kw))
    for d in proposals.get("effects") or []:
        g.effects.append(Effect(**_item_kwargs(d, Effect, by)))
    for d in proposals.get("transitions") or []:
        t = Transition(**_item_kwargs(d, Transition, by))
        t.sets = {k: _expr_text(v) for k, v in (t.sets or {}).items()}
        t.when = _expr_text(t.when) if t.when is not None else "true"
        g.transitions.append(t)
    for d in proposals.get("procedures") or []:
        g.procedures.append(Procedure(**_item_kwargs(d, Procedure, by)))
    for d in proposals.get("regions") or []:
        g.regions.append(Region(**_item_kwargs(d, Region, by)))
    for d in proposals.get("rules") or []:
        g.rules.append(Rule(**_item_kwargs(d, Rule, by)))
    for d in proposals.get("regimes") or []:
        g.regimes.append(Regime(**_item_kwargs(d, Regime, by)))
    g.unknowns = list(proposals.get("unknowns") or [])
    return g


# --------------------------------------------------------------------------- checking


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _subsequence(needle: list[str], hay: list[str]) -> bool:
    it = iter(hay)
    return all(any(_same(n, h) for h in it) for n in needle)


def _same(claimed: str, actual: str) -> bool:
    """A claimed entity name matches an observed step when it equals it or is its suffix
    after a `.` (`checkSufficientBalance` matches `api.Server.checkSufficientBalance`)."""
    claimed = claimed.split(":", 1)[1] if claimed.startswith(("go:", "py:", "js:")) else claimed
    return actual == claimed or actual.endswith("." + claimed) or actual.endswith(":" + claimed)


class Substrate:
    """What claims are checked against: execution paths, observed edges, source text."""

    def __init__(
        self,
        paths: list[ExecutionPath],
        observed_edges: set[tuple[str, str]],
        source_root: Path,
        decision_sites: set[tuple[str, int]] | None = None,
    ) -> None:
        self.paths = {p.execution: p for p in paths}
        self.observed_edges = observed_edges
        self.source_root = source_root
        # (file, line) of every `if` from static_decision_sites: the only source refs that
        # can anchor a decision's predicate for VERIFIED
        self.decision_sites = decision_sites or set()

    def path_for(self, test: str) -> ExecutionPath | None:
        if test in self.paths:
            return self.paths[test]
        hits = [
            p for k, p in self.paths.items() if k.endswith("/" + test) or k.endswith("::" + test)
        ]
        return hits[0] if len(hits) == 1 else None

    def check(self, ref: EvidenceRef) -> None:
        if ref.kind == "source":
            path = self.source_root / (ref.file or "")
            if not path.is_file() or not ref.line or not ref.text:
                ref.ok, ref.why = False, "source reference incomplete or file missing"
                return
            lines = path.read_text(encoding="utf-8").splitlines()
            if not 1 <= ref.line <= len(lines):
                ref.ok, ref.why = False, f"line {ref.line} out of range"
                return
            window = " ".join(lines[max(0, ref.line - 2) : ref.line + 1])  # ±1 line tolerance
            ref.ok = _norm(ref.text) in _norm(window)
            ref.why = "" if ref.ok else f"text not found near {ref.file}:{ref.line}"
            return
        if ref.kind == "execution":
            p = self.path_for(ref.test or "")
            if p is None:
                ref.ok, ref.why = False, f"no execution {ref.test!r} under the root"
                return
            calls = p.calls()
            problems = []
            if ref.calls and not _subsequence(ref.calls, calls):
                problems.append(f"calls {ref.calls} not observed in order")
            for a in ref.absent:
                if any(_same(a, c) for c in calls):
                    problems.append(f"{a} observed but claimed absent")
            for sym, val in ref.returns.items():
                actual = next(
                    (r for c in calls if _same(sym, c) for r in [p.result_of(c)] if r is not None),
                    None,
                )
                if actual != val:
                    problems.append(f"{sym} returned {actual!r}, claimed {val!r}")
            ref.ok = not problems
            ref.why = "; ".join(problems)
            return
        if ref.kind == "edge":
            ok = any(
                _same(ref.caller or "", c) and _same(ref.callee or "", k)
                for c, k in self.observed_edges
            )
            ref.ok, ref.why = ok, "" if ok else "no such observed edge"
            return
        ref.ok, ref.why = False, f"unknown evidence kind {ref.kind!r}"


def _branch_observed(sub: Substrate, entity: str, b: Branch) -> list[str]:
    """Executions whose path shows this branch: the deciding function returned `b.returns`
    (when given) and the branch's calls/absences hold. Uses decoded return values only."""
    hits = []
    for test, p in sub.paths.items():
        calls = p.calls()
        if not any(_same(entity, c) for c in calls):
            continue
        if b.returns is not None:
            actual = next(
                (p.result_of(c) for c in calls if _same(entity, c) and p.result_of(c)), None
            )
            if actual != b.returns:
                continue
        if b.calls and not _subsequence(b.calls, calls):
            continue
        if any(any(_same(a, c) for c in calls) for a in b.absent):
            continue
        hits.append(test)
    return hits


def _contradictions(sub: Substrate, entity: str, b: Branch) -> list[str]:
    """Executions where the deciding function returned this branch's value but the branch's
    claimed consequences did not happen."""
    if b.returns is None:
        return []
    bad = []
    for test, p in sub.paths.items():
        calls = p.calls()
        if not any(_same(entity, c) for c in calls):
            continue
        actual = next((p.result_of(c) for c in calls if _same(entity, c) and p.result_of(c)), None)
        if actual != b.returns:
            continue
        if (b.calls and not _subsequence(b.calls, calls)) or any(
            any(_same(a, c) for c in calls) for a in b.absent
        ):
            bad.append(test)
    return bad


def establish(g: Genome, sub: Substrate) -> Genome:
    """Assign every item's status from its evidence. Deterministic; the model has no say."""
    items: list[Item] = [
        *g.variables, *g.data_dependencies, *g.decisions, *g.effects, *g.transitions,
        *g.rules, *g.regimes,
    ]  # fmt: skip
    for it in items:
        for ref in it.evidence:
            sub.check(ref)
        if not it.evidence:
            it.status, it.status_reason = HYPOTHESIS, "no evidence cited"
            continue
        failed = [r for r in it.evidence if not r.ok]
        contradicting = [r for r in failed if r.kind == "execution"]
        if contradicting:
            it.status = REJECTED
            it.status_reason = "contradicted by execution: " + "; ".join(
                f"{r.test}: {r.why}" for r in contradicting
            )
            continue
        if failed:
            it.status = HYPOTHESIS
            it.status_reason = "evidence does not check out: " + "; ".join(r.why for r in failed)
            continue
        kinds = {r.kind for r in it.evidence}
        it.status = SUPPORTED
        it.status_reason = "every cited reference checks out (" + ", ".join(sorted(kinds)) + ")"
    # decisions (and rules that summarize them) can reach VERIFIED
    by_id = {d.id: d for d in g.decisions}
    for d in g.decisions:
        if d.status != SUPPORTED:
            continue
        has_source = any(
            r.kind == "source" and r.ok and (r.file, r.line) in sub.decision_sites
            for r in d.evidence
        )
        t_hits = _branch_observed(sub, d.entity, d.true_branch)
        f_hits = _branch_observed(sub, d.entity, d.false_branch)
        bad = _contradictions(sub, d.entity, d.true_branch) + _contradictions(
            sub, d.entity, d.false_branch
        )
        if bad:
            d.status, d.status_reason = (
                REJECTED,
                "branch consequence contradicted in " + ", ".join(bad),
            )
        elif has_source and t_hits and f_hits:
            d.status = VERIFIED
            d.status_reason = (
                "cites an `if` site; true branch observed in "
                f"{len(t_hits)} execution(s), false branch in {len(f_hits)}; no contradiction"
            )
        else:
            missing = [n for n, h in (("true", t_hits), ("false", f_hits)) if not h]
            d.status_reason += "; not verified: " + (
                "no cited `if` site anchors the predicate"
                if not has_source
                else f"{'/'.join(missing)} branch not observed with a decodable outcome"
            )
    variables = sorted({v.name for v in g.variables}, key=len, reverse=True)
    for r in g.rules:
        dec = by_id.get(r.decision or "")
        mentioned = {v for v in variables if v in r.condition}
        beyond = sorted(mentioned - set(dec.inputs)) if dec is not None else []
        if r.status == SUPPORTED and dec is not None and dec.status == VERIFIED and not beyond:
            r.status = VERIFIED
            r.status_reason = f"summarizes verified decision {dec.id}"
        elif r.status == SUPPORTED and dec is not None and dec.status == VERIFIED:
            r.status_reason = (
                f"summarizes verified decision {dec.id}, but its condition also uses "
                f"{', '.join(beyond)}, which that decision does not decide"
            )
        elif dec is not None and dec.status == REJECTED:
            r.status, r.status_reason = REJECTED, f"summarizes rejected decision {dec.id}"
    return g


# --------------------------------------------------------------------------- generation


def _eval_atom(atom: str, facts: dict[str, Any]) -> bool | None:
    """Evaluate `a OP b` or `name` / `!name` over facts. None when a fact is missing."""
    atom = atom.strip()
    m = re.match(r"^(.+?)\s*(<=|>=|==|!=|<|>)\s*(.+)$", atom)
    if m:
        a, op, b = (x.strip() for x in m.groups())
        va = facts.get(a, _num(a))
        vb = facts.get(b, _num(b))
        if va is None or vb is None:
            rel = facts.get(atom)
            return bool(rel) if rel is not None else None
        result: bool = {
            "<": va < vb,
            ">": va > vb,
            "<=": va <= vb,
            ">=": va >= vb,
            "==": va == vb,
            "!=": va != vb,
        }[op]
        return result
    neg = atom.startswith("!")
    name = atom[1:].strip() if neg else atom
    if name in ("true", "True", "false", "False"):
        return (name in ("true", "True")) != neg
    if name not in facts:
        return None
    return (not bool(facts[name])) if neg else bool(facts[name])


def _num(s: str) -> Any:
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return None


def eval_predicate(predicate: str, facts: dict[str, Any]) -> bool | None:
    """Conjunctions/disjunctions of atoms (`&&`, `||`, no parentheses). Three-valued."""
    ors = [p for p in re.split(r"\s*\|\|\s*", predicate) if p]
    any_unknown = False
    for disj in ors:
        vals = [_eval_atom(a, facts) for a in re.split(r"\s*&&\s*", disj) if a]
        if all(v is True for v in vals):
            return True
        if any(v is None for v in vals) and not any(v is False for v in vals):
            any_unknown = True
    return None if any_unknown else False


@dataclass
class Prediction:
    facts: dict[str, Any]
    fired: list[tuple[str, bool | None]]  # decision id, value
    path: list[str]  # predicted entities reached, in order
    absent: list[str]
    stopped_at: str | None
    indeterminate: str | None = None


def derive(g: Genome, facts: dict[str, Any]) -> dict[str, Any]:
    """Complete `facts` with derived variables whose machine-readable definition is
    decidable from the given facts. A prose-only definition derives nothing."""
    out = dict(facts)
    for _ in range(len(g.variables) + 1):
        changed = False
        for v in g.variables:
            if v.definition and v.name not in out:
                val = eval_predicate(v.definition, out)
                if val is not None:
                    out[v.name] = val
                    changed = True
        if not changed:
            break
    return out


def predict(g: Genome, facts: dict[str, Any], min_status: str = SUPPORTED) -> Prediction:
    """Walk decisions in path order. Each decision's branch contributes its calls; a
    stopping branch ends the path.

    Soundness: a decision whose status is below `min_status` (or rejected) is NOT skipped.
    The decision site exists in the code; only its semantics are unestablished, so the
    prediction stops there as indeterminate. Skipping it would silently predict the path
    as if the guard did not exist."""
    rank = {REJECTED: -1, HYPOTHESIS: 0, SUPPORTED: 1, VERIFIED: 2, STATIC: 2, OBSERVED: 3}
    facts = derive(g, facts)
    fired: list[tuple[str, bool | None]] = []
    path: list[str] = []
    absent: list[str] = []
    for d in sorted(g.decisions, key=lambda d: d.order):
        if rank.get(d.status, 0) < rank[min_status]:
            return Prediction(
                facts, fired, path, absent, None,
                f"{d.id} is {d.status}: its semantics are not established at >= {min_status}",
            )  # fmt: skip
        v = eval_predicate(d.predicate, facts)
        fired.append((d.id, v))
        if v is None:
            return Prediction(
                facts, fired, path, absent, None, f"{d.id}: predicate needs facts it was not given"
            )
        b = d.true_branch if v else d.false_branch
        path.extend(b.calls)  # each branch lists the calls it makes, once, in order
        absent.extend(a for a in b.absent if a not in absent)
        if b.stops:
            return Prediction(facts, fired, path, absent, d.id)
    return Prediction(facts, fired, path, absent, None)


def compare(
    pred: Prediction, observed: ExecutionPath, vocabulary: set[str] | None = None
) -> dict[str, Any]:
    """Strict comparison of a predicted path with what executed:
    - every predicted entity occurs, in the predicted order (subsequence);
    - no entity predicted absent occurs;
    - `unpredicted`: entities of the genome's own vocabulary that executed but the
      prediction did not mention (reported; a match requires none)."""
    calls = observed.calls()
    reached = [c for c in pred.path if any(_same(c, o) for o in calls)]
    missing = [c for c in pred.path if c not in reached]
    in_order = _subsequence(pred.path, calls)
    wrongly_present = [a for a in pred.absent if any(_same(a, o) for o in calls)]
    unpredicted = sorted(
        {v for v in (vocabulary or set()) if any(_same(v, o) for o in calls)} - set(pred.path)
    )
    # multiplicity: how many times each vocabulary entity ran vs. was predicted
    count_mismatch = {
        v: (sum(1 for c in pred.path if c == v), sum(1 for o in calls if _same(v, o)))
        for v in (vocabulary or set())
        if sum(1 for c in pred.path if c == v) != sum(1 for o in calls if _same(v, o))
    }
    return {
        "execution": observed.execution,
        "predicted_path": pred.path,
        "predicted_absent": pred.absent,
        "observed_calls": [c.rsplit(".", 1)[-1] for c in calls],
        "stopped_at": pred.stopped_at,
        "indeterminate": pred.indeterminate,
        "missing": missing,
        "out_of_order": not in_order and not missing,
        "wrongly_present": wrongly_present,
        "unpredicted": unpredicted,
        "count_mismatch": count_mismatch,
        "match": pred.indeterminate is None
        and not missing
        and in_order
        and not wrongly_present
        and not unpredicted,
        "exact": pred.indeterminate is None
        and not missing
        and in_order
        and not wrongly_present
        and not unpredicted
        and not count_mismatch,
    }


def vocabulary(g: Genome) -> set[str]:
    """Every entity name the genome's decisions mention in a branch."""
    out: set[str] = set()
    for d in g.decisions:
        for b in (d.true_branch, d.false_branch):
            out.update(b.calls)
            out.update(b.absent)
    return out


def dumps(g: Genome) -> str:
    return json.dumps(g.to_json(), indent=1, sort_keys=False) + "\n"


# --------------------------------------------------------------------------- rendering

_BADGE = {
    OBSERVED: "observed",
    STATIC: "static",
    HYPOTHESIS: "HYPOTHESIS",
    SUPPORTED: "supported",
    VERIFIED: "VERIFIED",
    REJECTED: "REJECTED",
}


def _ev_line(r: EvidenceRef) -> str:
    mark = "✓" if r.ok else "✗"
    if r.kind == "source":
        return f"{mark} source {r.file}:{r.line} `{(r.text or '').strip()[:70]}`"
    if r.kind == "execution":
        bits = []
        if r.calls:
            bits.append("calls " + " → ".join(r.calls))
        if r.absent:
            bits.append("never " + ", ".join(r.absent))
        if r.returns:
            bits.append(", ".join(f"{k}={v}" for k, v in r.returns.items()))
        return f"{mark} execution {r.test}: " + "; ".join(bits)
    return f"{mark} {r.kind} {r.caller} → {r.callee}"


def render_markdown(g: Genome, evaluation: dict[str, Any] | None = None) -> str:
    L: list[str] = []
    subj = g.subject
    title = f"{subj.get('repo')} {subj.get('change')}"
    L.append(f"# Behavioral Genome — {title} (`{FORMAT}`, experimental)")
    L.append("")
    L.append(
        f"Entry `{subj.get('entry')}`. Semantic items proposed by "
        f"`{g.provenance.get('model')}` from a bounded context bundle "
        f"(sha `{g.provenance.get('context_bundle_sha')}`); every status below was assigned "
        "by the deterministic checker, not by the model. Statuses: observed · static · "
        "HYPOTHESIS · supported (all citations check out) · VERIFIED (cites an `if` site "
        "and both branches observed, no contradiction) · REJECTED (contradicted by an "
        "execution)."
    )
    L.append("")
    L.append("## Entities (collector facts)")
    L.append("")
    for e in g.entities:
        L.append(f"- `{_short(e.symbol)}` — {e.role} · {e.status_reason}")
    L.append("")
    L.append("## Variables")
    L.append("")
    for v in g.variables:
        defn = f" := `{v.definition}`" if v.definition else ""
        bound = (
            f" ↔ observed `{v.observed_as.get('fact')}` ({v.observed_as.get('kind')})"
            if v.observed_as
            else ""
        )
        L.append(f"- `{v.name}` ({v.origin}){defn}{bound} — {_BADGE[v.status]}")
    L.append("")
    L.append("## Data dependencies")
    L.append("")
    for dd in g.data_dependencies:
        t = f" ({dd.transform})" if dd.transform else ""
        L.append(f"- `{dd.source}` → {dd.sink}{t} — {_BADGE[dd.status]}")
    L.append("")
    L.append("## Decisions, in path order")
    L.append("")
    for dec in sorted(g.decisions, key=lambda x: x.order):
        where = f" site `{dec.site}`" if dec.site else ""
        L.append(
            f"### {dec.id} · `{dec.predicate}` at `{dec.entity}`{where} — {_BADGE[dec.status]}"
        )
        L.append("")
        for b in (dec.true_branch, dec.false_branch):
            ret = f" returns {b.returns};" if b.returns else ""
            calls = " → ".join(b.calls) if b.calls else "(no call)"
            never = f"; never {', '.join(b.absent)}" if b.absent else ""
            stop = " **stop**" if b.stops else " continue"
            L.append(f"- {'TRUE ' if b.when else 'FALSE'}:{ret} {calls}{never};{stop} — {b.effect}")
        L.append(f"- status: {dec.status_reason}")
        for ref in dec.evidence:
            L.append(f"  - {_ev_line(ref)}")
        L.append("")
    L.append("## Behavioral rules")
    L.append("")
    for r in g.rules:
        L.append(f"- **{r.id} {r.name}** — {_BADGE[r.status]}")
        L.append(f"  - when `{r.condition}`")
        L.append(f"  - then {'; '.join(r.consequences)}")
        if r.decision:
            L.append(f"  - summarizes {r.decision}; {r.status_reason}")
    L.append("")
    L.append("## Regimes (behavioral equivalence classes)")
    L.append("")
    for rg in g.regimes:
        members = ", ".join(m.split("/")[-1] for m in rg.members)
        L.append(f"- **{rg.name}** — {len(rg.members)} test(s): {members} — {_BADGE[rg.status]}")
    L.append("")
    if g.transitions:
        L.append("## State transitions")
        L.append("")
        for tr in g.transitions:
            sets = ", ".join(f"`{k} := {v}`" for k, v in tr.sets.items())
            when = f" when `{tr.when}`" if tr.when and tr.when != "true" else ""
            L.append(
                f"- **{tr.id}** `{tr.entity}`{when}: {sets or tr.action} — {_BADGE[tr.status]}"
            )
        L.append("")
    if g.procedures:
        L.append("## Procedures (composition)")
        L.append("")
        for pr in g.procedures:
            L.append(f"- `{pr.entity}`: {' → '.join(pr.steps)} — {_BADGE[pr.status]}")
        L.append("")
    if g.effects:
        L.append("## Effects")
        L.append("")
        for ef in g.effects:
            L.append(f"- {ef.kind} `{ef.target}` when {ef.condition} — {_BADGE[ef.status]}")
        L.append("")
    if g.unknowns:
        L.append("## Unknown / incomplete (as stated by the model)")
        L.append("")
        for u in g.unknowns:
            L.append(f"- {u.get('what')}: {u.get('why')}")
        L.append("")
    if evaluation:
        L.append("## Generative check")
        L.append("")
        for name, sc in evaluation.get("scenarios", {}).items():
            got = sc["indeterminate"] or (
                " → ".join(sc["path"])
                + (f"; never {', '.join(sc['absent'])}" if sc["absent"] else "")
                + (f"; stops at {sc['stopped_at']}" if sc["stopped_at"] else "")
            )
            L.append(f"- **{name}**: {got}")
        per = evaluation.get("per_test", [])
        exact = sum(1 for r in per if r.get("exact"))
        held = [r for r in per if r.get("withheld")]
        L.append("")
        L.append(
            f"Per-test phenotype prediction (test facts → genome → predicted path, compared with "
            f"what executed, order- and count-exact): {exact}/{len(per)}; on the executions "
            f"withheld from the model: {sum(1 for r in held if r.get('exact'))}/{len(held)}."
        )
        L.append("")
    return "\n".join(L).rstrip() + "\n"
