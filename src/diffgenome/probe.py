"""Map-driven probe generation: pick a deficit, ask for one probe, run it confined, verify.

Language-neutral above the `SourceContext` adapter (which reads Python source) and the
runner command (pytest). The verdict on a probe comes from its trace, never from the model:
it passed, it executed the intended target as a real call, it attempted no egress, and it
changed the map.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from diffgenome.compose import Corpus, build_corpus
from diffgenome.graph import BehavioralGraph, GraphEdge, Metrics, Neighborhood, build_graph
from diffgenome.llm import ProbeDraft, ProbeRequest, ProbeWriter
from diffgenome.model import (
    ArgShapes,
    CallNode,
    EvidenceKind,
    Execution,
    JoinStrength,
    NodeRef,
    Origin,
    OsEventNode,
    Stimulus,
    SubstitutionNode,
    SymbolId,
)
from diffgenome.runtime import RuntimeAdapter, SymbolIndex
from diffgenome.sandbox import Workspace

CONSTRAINTS = """- The probe is a unit-level stimulus, not an integration test.
- Real in-repo code must execute; genuine external dependencies (network, model/weight
  files, GPU, subprocesses, real filesystem outside tmp_path, clocks/timers) stay substituted.
- Never contact a real service. The environment has no network; an attempt fails the probe.
- No long sleeps, no background threads left running, no writes outside tmp_path.
- One test function is enough. Make it deterministic.
- Do not modify repository files; the probe is a new file only."""


@dataclass
class ProbeObjective:
    kind: str  # "internal_gap" | "weak_join"
    target: SymbolId
    caller: SymbolId
    site: NodeRef
    distance: int
    seam_args: ArgShapes
    seam_outcome: str
    current_join: JoinStrength | None
    supporting_executions: int

    def describe(self) -> str:
        if self.kind == "uncovered_symbol":
            return (
                f"No existing execution reaches `{self.target}` at all (it is part of the "
                f"change). Write a probe that executes the real `{self.target}` directly. "
                "Substitute its direct in-repo collaborators with stand-ins that keep their "
                "identity (unittest.mock.patch(..., autospec=True) or jest.spyOn) so the seams "
                "are recorded, and substitute any external dependency."
            )
        if self.kind == "internal_gap":
            return (
                f"No existing test executes `{self.target}` for real. `{self.caller}` reaches it "
                f"only through a stand-in (called with {_fmt_args(self.seam_args)}, which "
                f"{self.seam_outcome}). Write a probe that executes the real `{self.target}` "
                f"from a comparable entry, with its own external dependencies substituted."
            )
        return (
            f"`{self.caller}` reaches `{self.target}` through a stand-in (called with "
            f"{_fmt_args(self.seam_args)}); existing executions of the real `{self.target}` only "
            f"match at {self.current_join.name if self.current_join else 'no'} strength. Write a "
            f"probe that executes the real `{self.target}` with arguments matching that call, so "
            f"the seam can be matched on values."
        )


def _fmt_args(args: ArgShapes) -> str:
    return "(" + ", ".join(f"{n}: {s}" for n, s, _ in args) + ")" if args else "no arguments"


def select_objectives(
    nb: Neighborhood,
    graph: BehavioralGraph,
    limit: int,
    index: SymbolIndex | None = None,
    skipped: list[str] | None = None,
) -> list[ProbeObjective]:
    """Deterministic priority: gaps before weak joins, nearer the change first, then the
    seams with the most upstream support. Targets must be repository code that a probe can
    make *execute*: a class with no in-repo __init__ never appears as a call, so a gap on
    it is recorded as not probeable rather than attempted."""
    out: list[ProbeObjective] = []
    seen: set[SymbolId] = set()

    def objective(kind: str, d: int, e: GraphEdge) -> ProbeObjective | None:
        if graph.origin(e.callee) is not Origin.REPO or e.callee in seen:
            return None
        sym = graph.symbols.get(e.callee)
        is_declaration = sym is not None and sym.kind == "declaration"
        if index is not None and not is_declaration:
            d_ = index.find(e.callee)
            is_declaration = d_ is not None and d_.kind == "class"
        if is_declaration:
            seen.add(e.callee)
            if skipped is not None:
                skipped.append(f"{e.callee}: declaration with no in-repo executable body")
            return None
        ev = e.evidence[0]
        assert graph.corpus is not None
        ex = graph.corpus.executions[ev.site.execution]
        node = ex.nodes[ev.site.node]
        args: ArgShapes = node.args if isinstance(node, SubstitutionNode | CallNode) else ()
        outcome = getattr(node, "outcome", "unknown")
        seen.add(e.callee)
        return ProbeObjective(
            kind, e.callee, e.caller, ev.site, d, args, outcome, e.best_join, len(e.executions)
        )

    # Changed symbols nothing executes: the change itself is dark. Distance 0.
    for seed in nb.seeds:
        if seed in graph.tests_by_symbol or seed in seen or graph.origin(seed) is Origin.TEST:
            continue
        if index is not None:
            d_ = index.find(seed)
            if d_ is None or d_.kind == "class":
                continue
        seen.add(seed)
        out.append(
            ProbeObjective(
                "uncovered_symbol", seed, seed, NodeRef("", 0), 0, (), "unknown", None, 0
            )
        )
        if len(out) >= limit:
            return out
    gaps = sorted(
        nb.edges_of(EvidenceKind.INTERNAL_GAP), key=lambda x: (x[0], -len(x[1].executions))
    )
    weak = sorted(
        ((d, e) for d, e in nb.edges_of(EvidenceKind.COMPOSED) if not e.strong),
        key=lambda x: (x[0], -len(x[1].executions)),
    )
    for kind, edges in (("internal_gap", gaps), ("weak_join", weak)):
        for d, e in edges:
            o = objective(kind, d, e)
            if o:
                out.append(o)
            if len(out) >= limit:
                return out
    return out


# --------------------------------------------------------------------------- context


class SourceContext:
    """Bounded probe context from the symbol index and the graph. Runtime-neutral: it asks
    the index for sources and modules and the runtime adapter for conventions."""

    def __init__(self, index: SymbolIndex, graph: BehavioralGraph) -> None:
        self.index = index
        self.graph = graph

    def build(self, o: ProbeObjective) -> str:
        parts: list[str] = []
        target_def = self.index.find(o.target)
        if target_def:
            parts.append(
                f"## Target `{o.target}` ({target_def.path}:{target_def.start}-{target_def.end})"
            )
            parts.append(_clip(self.index.source(o.target) or "", 120))
            cls = self.index.enclosing_class(o.target)
            if cls:
                # The whole class when it is small: the target usually delegates to
                # siblings (private helpers, constructors) the probe must understand.
                parts.append(f"## Enclosing class `{cls.symbol}`")
                parts.append(_clip(self.index.source(cls.symbol) or "", 160))
            parts.append(f"## Imports of {target_def.path}")
            parts.append(_module_head(self.index.repo_root / target_def.path))
        else:
            parts.append(f"## Target `{o.target}` (source not located)")
        if o.kind == "uncovered_symbol":
            parts.append("## Runtime evidence about the target")
            parts.append("- never executed by any existing test or probe")
            mod = self.index.module_of(o.target) or ""
            for tf in self.index.tests_importing(mod, limit=2) if mod else []:
                parts.append(f"## Existing test file {tf} (conventions; first lines)")
                text = (self.index.repo_root / tf).read_text(encoding="utf-8")
                parts.append(_clip(_numbered(text), 70))
            return "\n\n".join(parts)
        parts.append(f"## Caller `{o.caller}` (reaches the target through a stand-in)")
        parts.append(_clip(self.index.source(o.caller) or "(source not located)", 80))
        assert self.graph.corpus is not None
        seed = self.graph.corpus.executions[o.site.execution]
        parts.append(f"## The existing test that produced this seam: {seed.stimulus_ref}")
        test_source = None
        for n in seed.nodes:  # the root, or the first test-origin call under it
            if isinstance(n, CallNode) and self.graph.origin(n.symbol) is Origin.TEST:
                test_source = self.index.source(n.symbol)
                if test_source:
                    break
        parts.append(_clip(test_source or "(source not located)", 80))
        subs = [n for n in seed.nodes if isinstance(n, SubstitutionNode)]
        if subs:
            parts.append(
                "## Substitutions active in that test (keep the external ones substituted)"
            )
            for s in subs[:12]:
                origin = (
                    self.graph.origin(s.claimed_target).value if s.claimed_target else "unknown"
                )
                path = ".".join(s.path) or "<call>"
                parts.append(f"- {s.mechanism.value} .{path} claims={s.claimed_target} ({origin})")
        parts.append("## Runtime evidence about the target")
        outs = self.graph.outcomes_by_symbol.get(o.target)
        parts.append(f"- outcomes observed so far: {dict(outs) if outs else 'never executed'}")
        for e in self.graph.out.get(o.target, [])[:12]:
            parts.append(f"- {o.target.split('.')[-1]} → {e.callee} [{e.kind.value}]")
        module = self.index.module_of(o.target) if target_def else None
        for tf in self.index.tests_importing(module, limit=2) if module else []:
            parts.append(f"## Existing test file {tf} (conventions; first lines)")
            parts.append(
                _clip(_numbered((self.index.repo_root / tf).read_text(encoding="utf-8")), 70)
            )
        return "\n\n".join(parts)


def _numbered(text: str) -> str:
    return "\n".join(f"{i + 1:5d}  {line}" for i, line in enumerate(text.splitlines()))


def _module_head(path: Path) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    head = [
        line
        for line in lines[:60]
        if line.startswith(("import ", "from ")) or (line.startswith("_") and "=" in line)
    ]
    return "\n".join(head[:30])


def _clip(text: str, max_lines: int) -> str:
    lines = text.splitlines()
    return "\n".join(lines[:max_lines]) + (
        f"\n... ({len(lines) - max_lines} more lines)" if len(lines) > max_lines else ""
    )


# --------------------------------------------------------------------------- execution


@dataclass
class ProbeAttempt:
    objective: ProbeObjective
    attempt: int
    draft: ProbeDraft | None
    verdict: str  # "accepted" | "rejected" | "error"
    reasons: list[str] = field(default_factory=list)
    executions: list[Execution] = field(default_factory=list)
    metrics_before: Metrics | None = None
    metrics_after: Metrics | None = None
    learned: list[str] = field(default_factory=list)


@dataclass
class ProbeRunner:
    workspace: Workspace
    runtime: RuntimeAdapter

    def run(self, draft: ProbeDraft, tag: str, out_dir: Path) -> tuple[list[Execution], str, str]:
        rel = self.runtime.probe_relpath(tag)
        probe_file = self.workspace.repo / rel
        probe_file.parent.mkdir(parents=True, exist_ok=True)
        probe_file.write_text(draft.code)
        try:
            executions, stdout, stderr = self.runtime.trace(
                self.workspace, out_dir / f"traces-{tag}", Stimulus.GENERATED_PROBE, [rel]
            )
        finally:
            probe_file.unlink(missing_ok=True)
        return executions, stdout, stderr


def verify(
    o: ProbeObjective,
    executions: list[Execution],
    stdout: str,
    stderr: str,
    corpus: Corpus,
    seeds: list[SymbolId],
    before: Metrics,
    up: int,
    down: int,
) -> tuple[str, list[str], Metrics | None, list[str], Corpus | None]:
    """Deterministic verdict. Returns (verdict, reasons, metrics_after, learned, new_corpus)."""
    reasons: list[str] = []
    if not executions:
        tail = (stderr or stdout).strip().splitlines()[-8:]
        return (
            "error",
            ["probe produced no executions (collection or import error)", *tail],
            None,
            [],
            None,
        )
    failed = [e for e in executions if e.outcome != "passed"]
    if failed:
        text = stdout if "failed" in stdout or "FAIL" in stdout else stderr
        tail = [line for line in text.strip().splitlines() if line.strip()][-15:]
        reasons.append(f"{len(failed)} of {len(executions)} probe tests failed")
        reasons.extend(tail)
    egress = [
        (e.stimulus_ref, n.target)
        for e in executions
        for n in e.nodes
        if isinstance(n, OsEventNode)
    ]
    if egress:
        reasons.append("egress attempted: " + ", ".join(t for _, t in egress[:5]))
    ran_target = any(
        isinstance(n, CallNode) and n.symbol == o.target for e in executions for n in e.nodes
    )
    if not ran_target:
        reasons.append(f"target {o.target} did not execute as a real call")
    if reasons:
        return "rejected", reasons, None, [], None
    new_corpus = build_corpus(list(corpus.executions.values()) + executions)
    graph = build_graph(new_corpus)
    after = graph.neighborhood(seeds, up=up, down=down).metrics()
    learned: list[str] = []
    for e in executions:
        for n in e.nodes:
            if isinstance(n, CallNode) and n.id != 0 and n.parent is not None:
                p = e.nodes[n.parent]
                if isinstance(p, CallNode):
                    learned.append(f"{p.symbol} → {n.symbol} [{n.outcome}]")
    learned = sorted(set(learned))
    improved = (
        after.internal_gaps < before.internal_gaps
        or after.strong_joins > before.strong_joins
        or after.observed > before.observed
    )
    if not improved:
        return (
            "rejected",
            ["probe ran the target but added no evidence to the neighborhood"],
            after,
            learned,
            None,
        )
    return "accepted", [], after, learned, new_corpus


def run_probe_loop(
    graph: BehavioralGraph,
    neighborhood: Neighborhood,
    index: SymbolIndex,
    writer: ProbeWriter,
    runner: ProbeRunner,
    out_dir: Path,
    max_objectives: int,
    max_attempts: int,
    up: int,
    down: int,
    skipped: list[str] | None = None,
) -> tuple[list[ProbeAttempt], Corpus]:
    out_dir.mkdir(parents=True, exist_ok=True)
    assert graph.corpus is not None
    corpus = graph.corpus
    seeds = list(neighborhood.seeds)
    attempts: list[ProbeAttempt] = []
    objectives = select_objectives(neighborhood, graph, max_objectives, index, skipped)
    for i, o in enumerate(objectives):
        failures: list[str] = []
        current_graph = build_graph(corpus)
        before = current_graph.neighborhood(seeds, up=up, down=down).metrics()
        context = SourceContext(index, current_graph).build(o)
        conventions = runner.runtime.conventions(index)
        for attempt in range(1, max_attempts + 1):
            tag = f"{i}_{attempt}"
            request = ProbeRequest(o.describe(), context, CONSTRAINTS, conventions, failures)
            try:
                draft = writer.write(request)
            except Exception as exc:  # the writer is an external service
                attempts.append(ProbeAttempt(o, attempt, None, "error", [f"writer error: {exc}"]))
                break
            (out_dir / f"probe-{tag}.py").write_text(draft.code)
            try:
                executions, stdout, stderr = runner.run(draft, tag, out_dir)
                (out_dir / f"probe-{tag}.log").write_text(stdout + "\n--- stderr ---\n" + stderr)
            except Exception as exc:
                attempts.append(ProbeAttempt(o, attempt, draft, "error", [f"runner error: {exc}"]))
                break
            verdict, reasons, after, learned, new_corpus = verify(
                o, executions, stdout, stderr, corpus, seeds, before, up, down
            )
            attempts.append(
                ProbeAttempt(
                    o, attempt, draft, verdict, reasons, executions, before, after, learned
                )
            )
            if verdict == "accepted" and new_corpus is not None:
                corpus = new_corpus
                break
            failures.append(f"attempt {attempt}: " + "; ".join(reasons[:6]))
    return attempts, corpus


def copy_probe_traces(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.glob("*.json"):
        shutil.copy(f, dst / f.name)
