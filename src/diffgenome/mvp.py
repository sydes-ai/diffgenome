"""One workflow: trace a repository's tests, build the map, centre on a change, probe the
gaps with generated unit probes under confinement, re-compose, report.

    python -m diffgenome mvp --repo ~/sample_repos/Kokoro-FastAPI --python .venv/bin/python \\
        --test-root api/tests --diff 8307b0e --pytest-arg=--no-cov \\
        --pytest-arg=--ignore=api/tests/integration --out out/kokoro
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import time
from pathlib import Path

from diffgenome.change import ChangeSet, changes_from_diff, changes_from_symbols, git_diff
from diffgenome.collect.py_symbols import PythonSymbolIndex
from diffgenome.compose import build_corpus
from diffgenome.graph import build_graph
from diffgenome.llm import OpenAIProbeWriter, ProbeWriter, RecordedProbeWriter
from diffgenome.model import Execution, Origin
from diffgenome.probe import ProbeAttempt, ProbeRunner, copy_probe_traces, run_probe_loop
from diffgenome.report import render_map_slice, render_report, report_json
from diffgenome.sandbox import Workspace
from diffgenome.serialize import execution_from_json

DIFFGENOME_SRC = Path(__file__).resolve().parent.parent


def _log(msg: str) -> None:
    print(f"[diffgenome {time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def trace_existing_tests(
    ws: Workspace,
    python: Path,
    source_root: str,
    test_root: str,
    pytest_args: list[str],
    tests: str,
    out: Path,
) -> list[Execution]:
    # Traces are written inside the workspace (the sandbox refuses writes elsewhere) and
    # copied out afterwards.
    traces_ws = ws.root / "traces-existing"
    traces_ws.mkdir(parents=True, exist_ok=True)
    argv = [
        str(python), "-m", "pytest", "-q", "-p", "no:cacheprovider",
        "-p", "diffgenome.collect.pytest_plugin",
        "--diffgenome-out", str(traces_ws),
        "--diffgenome-source-root", source_root,
        "--diffgenome-test-root", test_root,
        "--diffgenome-egress-guard",
        *pytest_args, tests,
    ]  # fmt: skip
    result = ws.run(argv, env={"PYTHONPATH": str(DIFFGENOME_SRC)}, timeout=1800)
    traces = out / "traces-existing"
    copy_probe_traces(traces_ws, traces)
    (out / "existing-tests.log").write_text(result.stdout + "\n" + result.stderr)
    summary = (
        result.stdout.strip().splitlines()[-1] if result.stdout.strip() else result.stderr[-200:]
    )
    _log(f"existing tests: {summary} ({result.seconds:.0f}s, confined={result.confined})")
    return [execution_from_json(f.read_text()) for f in sorted(traces.glob("*.json"))]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="diffgenome mvp")
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--python", required=True, type=Path, help="target interpreter (its venv)")
    ap.add_argument("--source-root", default=".")
    ap.add_argument("--test-root", required=True)
    ap.add_argument("--tests", default=None, help="pytest target path (default: test root)")
    ap.add_argument("--pytest-arg", action="append", default=[])
    ap.add_argument("--diff", help="git revspec: base..head, or a commit (vs its parent)")
    ap.add_argument("--symbol", action="append", default=[], help="explicit changed symbol")
    ap.add_argument("--traces", type=Path, help="reuse existing-test traces from this directory")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--workspaces", type=Path, default=None)
    ap.add_argument("--writer", default="openai", help="openai | none | recorded:<dir>")
    ap.add_argument("--model", default=None)
    ap.add_argument("--probes", type=int, default=3)
    ap.add_argument("--attempts", type=int, default=2)
    ap.add_argument("--up", type=int, default=3)
    ap.add_argument("--down", type=int, default=4)
    args = ap.parse_args(argv)

    repo = args.repo.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    # Never resolve symlinks here: a venv's python is a symlink to the base interpreter,
    # and the venv is selected by the *unresolved* executable path.
    python = Path(os.path.abspath(args.python if args.python.is_absolute() else repo / args.python))
    pytest_args = [a for chunk in args.pytest_arg for a in shlex.split(chunk)]
    tests = args.tests or args.test_root
    notes: list[str] = []

    ws = Workspace.create(repo, args.workspaces or out / "workspaces")
    _log(f"workspace {ws.root} (copy of {repo}; original never written)")
    try:
        # 1. existing executions
        if args.traces:
            executions = [
                execution_from_json(f.read_text()) for f in sorted(args.traces.glob("*.json"))
            ]
            _log(f"reusing {len(executions)} existing-test traces from {args.traces}")
        else:
            executions = trace_existing_tests(
                ws, python, args.source_root, args.test_root, pytest_args, tests, out
            )
        # 2. map
        corpus = build_corpus(executions)
        graph = build_graph(corpus)
        _log(f"map: {len(graph.edges)} edges, {len(graph.symbols)} symbols, {len(graph.gaps)} gaps")
        # 3. change
        index = PythonSymbolIndex(repo, [repo / args.source_root], [repo / args.test_root])
        change: ChangeSet
        if args.diff:
            change = changes_from_diff(git_diff(repo, args.diff), index, f"git diff {args.diff}")
        elif args.symbol:
            change = changes_from_symbols(args.symbol)
        else:
            ap.error("one of --diff or --symbol is required")
        seeds = [
            s for s in change.symbols if graph.origin(s) is Origin.REPO or s not in graph.symbols
        ]
        seeds = [
            s for s in seeds if not any(s.startswith(f"py:{p}") for p in _test_prefixes(index))
        ]
        never_run = [s for s in seeds if s not in graph.tests_by_symbol]
        if never_run:
            notes.append(
                f"{len(never_run)} changed symbol(s) have no existing execution at all: "
                + ", ".join(s.split(":")[-1] for s in never_run[:8])
            )
        _log(f"change: {len(change.symbols)} symbols, {len(seeds)} in-repo seeds")
        # 4-5. neighborhood
        nb_before = graph.neighborhood(seeds, up=args.up, down=args.down)
        _log(f"neighborhood: {nb_before.metrics().as_dict()}")
        # 6-11. probes
        attempts: list[ProbeAttempt] = []
        corpus_after = corpus
        writer: ProbeWriter | None = None
        if args.writer == "openai":
            try:
                writer = OpenAIProbeWriter(model=args.model)
            except RuntimeError as exc:
                notes.append(f"no probe writer: {exc}")
                _log(f"probes skipped: {exc}")
        elif args.writer.startswith("recorded:"):
            writer = RecordedProbeWriter(Path(args.writer.split(":", 1)[1]))
        if writer is not None and args.probes > 0:
            runner = ProbeRunner(
                ws, python, DIFFGENOME_SRC, args.source_root, args.test_root, pytest_args
            )
            skipped: list[str] = []
            attempts, corpus_after = run_probe_loop(
                graph,
                nb_before,
                index,
                writer,
                runner,
                out,
                args.probes,
                args.attempts,
                args.up,
                args.down,
                skipped,
            )
            notes.extend(f"not probeable: {s}" for s in skipped)
            accepted = sum(a.verdict == "accepted" for a in attempts)
            _log(f"probes: {accepted} accepted of {len(attempts)} attempts")
        graph_after = build_graph(corpus_after) if attempts else None
        nb_after = (
            graph_after.neighborhood(seeds, up=args.up, down=args.down) if graph_after else None
        )
        # 12. materialize the graph and the report
        (out / "graph-before.json").write_text(json.dumps(graph.to_json(), indent=1) + "\n")
        final_graph = graph_after or graph
        (out / "graph.json").write_text(json.dumps(final_graph.to_json(), indent=1) + "\n")
        map_slice = render_map_slice(final_graph, seeds, up=args.up, down=args.down)
        (out / "map.md").write_text(map_slice)
        text = render_report(change, graph, nb_before, attempts, graph_after, nb_after, notes)
        text += (
            "\n## Behavioral map slice around the changed symbols\n\n```\n" + map_slice + "```\n"
        )
        text += (
            "\nThe full repo-level graph with every edge's provenance is `graph.json` next to this "
            "report (`graph-before.json` is the state before probes). Query it with "
            "`python -m diffgenome inspect --graph graph.json --symbol <id or suffix>`.\n"
        )
        (out / "report.md").write_text(text)
        (out / "report.json").write_text(report_json(change, nb_before, attempts, nb_after, notes))
        print(text)
        _log(f"report: {out / 'report.md'}  graph: {out / 'graph.json'}  map: {out / 'map.md'}")
    finally:
        ws.destroy()
    return 0


def _test_prefixes(index: PythonSymbolIndex) -> list[str]:
    return [".".join(r.relative_to(index.repo_root).parts) for r in index.test_roots]
