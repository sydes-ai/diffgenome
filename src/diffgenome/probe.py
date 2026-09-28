"""Map-driven probe generation: pick a deficit, ask for one probe, run it confined, verify.

Language-neutral above the `SourceContext` adapter (which reads Python source) and the
runner command (pytest). The verdict on a probe comes from its trace, never from the model:
it passed, it executed the intended target as a real call, it attempted no egress, and it
changed the map.
"""

from __future__ import annotations

import ast
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from diffgenome.collect.py_symbols import PythonSymbolIndex
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
from diffgenome.sandbox import Workspace
from diffgenome.serialize import execution_from_json

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
    index: PythonSymbolIndex | None = None,
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
        if index is not None:
            d_ = index.find(e.callee)
            if d_ is not None and d_.kind == "class":
                seen.add(e.callee)
                if skipped is not None:
                    skipped.append(f"{e.callee}: class construction with no in-repo __init__")
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
    """Python source adapter for probe context. Bounded on purpose."""

    def __init__(self, index: PythonSymbolIndex, graph: BehavioralGraph) -> None:
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
                parts.append(f"## Enclosing class `{cls.symbol}`: __init__ and signature")
                init = self.index.source(cls.symbol + ".__init__")
                head = _clip(self.index.source(cls.symbol) or "", 15)
                parts.append(head)
                if init:
                    parts.append(_clip(init, 60))
            parts.append(f"## Imports of {target_def.path}")
            parts.append(_module_head(self.index.repo_root / target_def.path))
        else:
            parts.append(f"## Target `{o.target}` (source not located)")
        parts.append(f"## Caller `{o.caller}` (reaches the target through a stand-in)")
        parts.append(_clip(self.index.source(o.caller) or "(source not located)", 80))
        assert self.graph.corpus is not None
        seed = self.graph.corpus.executions[o.site.execution]
        parts.append(f"## The existing test that produced this seam: {seed.stimulus_ref}")
        test_symbol = seed.nodes[0].symbol if isinstance(seed.nodes[0], CallNode) else None
        if test_symbol:
            parts.append(_clip(self.index.source(test_symbol) or "(source not located)", 80))
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
        module = o.target.split(":", 1)[1].rsplit(".", 2)[0] if target_def else ""
        for tf in self.index.tests_importing(module, limit=2) if module else []:
            parts.append(f"## Existing test file {tf} (conventions; first lines)")
            parts.append(
                _clip(_numbered((self.index.repo_root / tf).read_text(encoding="utf-8")), 70)
            )
        conftest = self._conftest()
        if conftest:
            parts.append("## conftest fixtures available")
            parts.append(conftest)
        cfg = self._pytest_config()
        if cfg:
            parts.append("## pytest configuration")
            parts.append(cfg)
        return "\n\n".join(parts)

    def _pytest_config(self) -> str:
        out: list[str] = []
        ini = self.index.repo_root / "pytest.ini"
        if ini.is_file():
            out.append(_clip(ini.read_text(encoding="utf-8"), 20))
        pyproject = self.index.repo_root / "pyproject.toml"
        if pyproject.is_file():
            text = pyproject.read_text(encoding="utf-8")
            if "[tool.pytest" in text:
                section = text[text.index("[tool.pytest") :]
                out.append(_clip(section, 15))
        return "\n".join(out)

    def _conftest(self) -> str:
        lines: list[str] = []
        for root in self.index.test_roots:
            f = root / "conftest.py"
            if f.is_file():
                try:
                    tree = ast.parse(f.read_text(encoding="utf-8"))
                except SyntaxError:
                    continue
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and any(
                        "fixture" in ast.unparse(d) for d in node.decorator_list
                    ):
                        doc = ast.get_docstring(node) or ""
                        params = ", ".join(a.arg for a in node.args.args)
                        first = doc.splitlines()[0] if doc else ""
                        lines.append(f"- {node.name}({params}): {first}")
        return "\n".join(lines[:30])


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
    python: Path  # target interpreter (read-only, outside the workspace)
    diffgenome_src: Path
    source_root: str  # relative to repo
    test_root: str  # relative to repo
    pytest_args: list[str]
    env: dict[str, str] = field(default_factory=dict)  # extra variables (e.g. PYTHONPATH)

    def run(self, draft: ProbeDraft, tag: str, out_dir: Path) -> tuple[list[Execution], str, str]:
        probe_dir = self.workspace.repo / self.test_root
        name = f"test_diffgenome_probe_{tag}.py"
        (probe_dir / name).write_text(draft.code)
        traces_ws = self.workspace.root / f"traces-{tag}"
        traces_ws.mkdir(parents=True, exist_ok=True)
        argv = [
            str(self.python), "-m", "pytest", "-q", "-p", "no:cacheprovider",
            "-p", "diffgenome.collect.pytest_plugin",
            "--diffgenome-out", str(traces_ws),
            "--diffgenome-source-root", self.source_root,
            "--diffgenome-test-root", self.test_root,
            "--diffgenome-stimulus", Stimulus.GENERATED_PROBE.value,
            "--diffgenome-egress-guard",
            *self.pytest_args,
            f"{self.test_root}/{name}",
        ]  # fmt: skip
        env = {"PYTHONPATH": str(self.diffgenome_src), **self.env}
        result = self.workspace.run(argv, env=env, timeout=600)
        traces = out_dir / f"traces-{tag}"
        copy_probe_traces(traces_ws, traces)
        executions = [execution_from_json(f.read_text()) for f in sorted(traces.glob("*.json"))]
        (probe_dir / name).unlink(missing_ok=True)
        return executions, result.stdout, result.stderr


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
        tail = stdout.strip().splitlines()[-15:]
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
    index: PythonSymbolIndex,
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
        for attempt in range(1, max_attempts + 1):
            tag = f"{i}_{attempt}"
            request = ProbeRequest(o.describe(), context, CONSTRAINTS, failures)
            try:
                draft = writer.write(request)
            except Exception as exc:  # the writer is an external service
                attempts.append(ProbeAttempt(o, attempt, None, "error", [f"writer error: {exc}"]))
                break
            (out_dir / f"probe-{tag}.py").write_text(draft.code)
            try:
                executions, stdout, stderr = runner.run(draft, tag, out_dir)
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
