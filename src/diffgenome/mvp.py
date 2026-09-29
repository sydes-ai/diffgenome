"""One workflow: trace a repository's tests, build the map, centre on a change, probe the
gaps with generated unit probes under confinement, re-compose, report.

    python -m diffgenome mvp --runtime python --repo <r> --python .venv/bin/python \\
        --test-root tests --diff <rev> --writer openai --out out/run
    python -m diffgenome mvp --runtime node --repo <r> --source-root src --test-root test/unit \\
        --diff <rev> --writer openai --out out/run
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import sys
import time
from pathlib import Path

from diffgenome.ambiguity import render_ambiguity
from diffgenome.change import ChangeSet, changes_from_diff, changes_from_symbols, git_diff
from diffgenome.change_artifact import build_change_artifact
from diffgenome.change_artifact import dumps as dump_artifact
from diffgenome.compose import build_corpus
from diffgenome.graph import build_graph
from diffgenome.llm import OpenAIProbeWriter, ProbeWriter, RecordedProbeWriter
from diffgenome.model import Origin, Stimulus
from diffgenome.probe import ProbeAttempt, ProbeRunner, run_probe_loop
from diffgenome.projection import case_metrics, render_behavior_map, slice_json
from diffgenome.report import render_map_slice, render_report, report_json
from diffgenome.runtime import RuntimeAdapter, SymbolIndex
from diffgenome.sandbox import Workspace, host_supports_confinement
from diffgenome.serialize import execution_from_json
from diffgenome.static_types import apply_static_return_types


def _write_status(out: Path, status: str, reason: str) -> None:
    """When no diffgenome-change.json can be produced, say why in a file an integrator in
    another job can read (diffgenome-status/1), instead of leaving only a missing file."""
    (out / "diffgenome-status.json").write_text(
        json.dumps({"format": "diffgenome-status/1", "status": status, "reason": reason}) + "\n"
    )


def _log(msg: str) -> None:
    print(f"[diffgenome {time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def make_runtime(args: argparse.Namespace, repo: Path, pytest_args: list[str]) -> RuntimeAdapter:
    tests = args.tests or args.test_root
    if args.runtime == "python":
        from diffgenome.collect.py_runtime import PytestRuntime

        if not args.python:
            raise SystemExit("--python is required for --runtime python")
        # Never resolve symlinks: a venv's python is a symlink to the base interpreter, and
        # the venv is selected by the *unresolved* executable path.
        python = Path(
            os.path.abspath(args.python if args.python.is_absolute() else repo / args.python)
        )
        return PytestRuntime(repo, python, args.source_root, args.test_root, tests, pytest_args)
    if args.runtime == "node":
        from diffgenome.collect.node_jest import NodeJestRuntime

        return NodeJestRuntime(repo, args.source_root, args.test_root, tests)
    if args.runtime == "go":
        from diffgenome.collect.go_test import GoTestRuntime

        return GoTestRuntime(repo, args.source_root, args.test_root, tests, args.mock_dir)
    raise SystemExit(f"unknown runtime {args.runtime}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="diffgenome mvp")
    ap.add_argument("--runtime", default="python", choices=["python", "node", "go"])
    ap.add_argument(
        "--mock-dir",
        action="append",
        default=[],
        help="go: generated mock package dirs (test origin)",
    )
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--python", type=Path, help="target interpreter (python runtime)")
    ap.add_argument("--source-root", default=".")
    ap.add_argument("--test-root", required=True)
    ap.add_argument("--tests", default=None, help="test target path (default: test root)")
    ap.add_argument("--pytest-arg", action="append", default=[])
    ap.add_argument("--diff", help="git revspec: base..head, or a commit (vs its parent)")
    ap.add_argument(
        "--rev", help="analyze this git revision (workspace from `git archive`), not the checkout"
    )
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
    ap.add_argument(
        "--no-state", action="store_true", help="ignore state facts at seams (VALUE-only baseline)"
    )
    ap.add_argument(
        "--probe-max-distance",
        type=int,
        default=None,
        help="only probe gaps within this many hops of a changed symbol (integrated mode: 1)",
    )
    args = ap.parse_args(argv)

    repo = args.repo.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not host_supports_confinement():
        # Invariant: target code never runs unconfined. Say so in one line an integrator
        # can show verbatim, instead of failing later with a traceback.
        reason = (
            f"refusing to run: no supported OS sandbox on this host ({platform.system()}); "
            "target tests are never executed unconfined"
        )
        _log(reason)
        _write_status(out, "refused", reason)
        return 3
    pytest_args = [a for chunk in args.pytest_arg for a in shlex.split(chunk)]
    runtime = make_runtime(args, repo, pytest_args)
    notes: list[str] = []

    ws = Workspace.create(repo, args.workspaces or out / "workspaces", rev=args.rev)
    _log(f"workspace {ws.root} (copy of {repo}; original never written) runtime={runtime.name}")
    try:
        index: SymbolIndex = runtime.prepare(ws)
        # 1. existing executions
        if args.traces:
            executions = [
                execution_from_json(f.read_text()) for f in sorted(args.traces.glob("*.json"))
            ]
            _log(f"reusing {len(executions)} existing-test traces from {args.traces}")
        else:
            executions, stdout, stderr = runtime.trace(
                ws, out / "traces-existing", Stimulus.EXISTING_TEST, None
            )
            (out / "existing-tests.log").write_text(stdout + "\n" + stderr)
            tail = (stdout.strip() or stderr.strip()).splitlines()[-1:]
            _log(f"existing tests: {tail} -> {len(executions)} executions")
        if not executions and not args.traces:
            _log("no executions captured; see existing-tests.log")
            _write_status(
                out, "failed", "no test executions captured (test command failed or found no tests)"
            )
            return 2
        if not executions:
            notes.append("cold start: no existing executions; every changed symbol is uncovered")
        executions, n_static = apply_static_return_types(executions, index)
        if n_static:
            notes.append(
                f"{n_static} factory().member stand-ins resolved through declared return "
                "types (rule static-return-type)"
            )
        # 2. map
        corpus = build_corpus(executions)
        graph = build_graph(corpus, use_state=not args.no_state)
        _log(f"map: {len(graph.edges)} edges, {len(graph.symbols)} symbols, {len(graph.gaps)} gaps")
        # 3. change
        change: ChangeSet
        if args.diff:
            change = changes_from_diff(git_diff(repo, args.diff), index, f"git diff {args.diff}")
        elif args.symbol:
            change = changes_from_symbols(args.symbol)
        else:
            ap.error("one of --diff or --symbol is required")
        seeds = [
            s
            for s in change.symbols
            if (graph.origin(s) is Origin.REPO or s not in graph.symbols)
            and not _under_test_root(s, index)
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
            runner = ProbeRunner(ws, runtime)
            skipped: list[str] = []
            attempts, corpus_after = run_probe_loop(
                graph, nb_before, index, writer, runner, out, args.probes, args.attempts,
                args.up, args.down, skipped, max_distance=args.probe_max_distance,
            )  # fmt: skip
            notes.extend(f"not probeable: {s}" for s in skipped)
            accepted = sum(a.verdict == "accepted" for a in attempts)
            _log(f"probes: {accepted} accepted of {len(attempts)} attempts")
        graph_after = build_graph(corpus_after, use_state=not args.no_state) if attempts else None
        nb_after = (
            graph_after.neighborhood(seeds, up=args.up, down=args.down) if graph_after else None
        )
        # 12. materialize the graph and the report
        (out / "graph-before.json").write_text(json.dumps(graph.to_json(), indent=1) + "\n")
        final_graph = graph_after or graph
        (out / "graph.json").write_text(json.dumps(final_graph.to_json(), indent=1) + "\n")
        evidence_slice = render_map_slice(final_graph, seeds, up=args.up, down=args.down)
        (out / "map-evidence.md").write_text(evidence_slice)
        declared = {s for s in seeds if (d := index.find(s)) is not None and d.kind == "class"}
        behavior_map = render_behavior_map(
            final_graph, seeds, up=args.up, down=args.down, declarations=declared
        )
        (out / "ambiguity.md").write_text(render_ambiguity(final_graph))
        (out / "map.md").write_text(behavior_map)
        (out / "slice.json").write_text(
            json.dumps(slice_json(final_graph, seeds, args.up, args.down), indent=1) + "\n"
        )
        metrics = case_metrics(
            final_graph, seeds, args.up, args.down, attempts, graph if graph_after else None
        )
        (out / "metrics.json").write_text(json.dumps(metrics, indent=1) + "\n")
        text = render_report(change, graph, nb_before, attempts, graph_after, nb_after, notes)
        text += "\n## Behavioral map around the changed symbols\n\n```\n" + behavior_map + "```\n"
        text += (
            "\nThe full repo-level graph with every edge's provenance is `graph.json` next to this "
            "report (`graph-before.json` is the state before probes). Query it with "
            "`python -m diffgenome inspect --graph graph.json --symbol <id or suffix>`.\n"
        )
        (out / "report.md").write_text(text)
        (out / "report.json").write_text(report_json(change, nb_before, attempts, nb_after, notes))
        # 13. the integration artifact: bounded, change-centred, no internal objects
        artifact = build_change_artifact(
            final_graph,
            seeds,
            up=args.up,
            down=args.down,
            change_spec=change.description,
            runtime=runtime.name,
            repo=str(repo),
            revision=args.rev,
            budget={
                "writer": args.writer,
                "probes_requested": args.probes if writer is not None else 0,
                "attempts_per_probe": args.attempts,
                "llm_calls": sum(1 for a in attempts if a.draft is not None)
                if args.writer == "openai"
                else 0,
                "existing_traces_reused": bool(args.traces),
                "probe_max_distance": args.probe_max_distance,
            },
            probes=[
                {
                    "tag": f"{i}",
                    "objective": a.objective.kind,
                    "target": a.objective.target,
                    "attempt": a.attempt,
                    "verdict": a.verdict,
                    "reasons": list(a.reasons)[:3],
                }
                for i, a in enumerate(attempts)
            ],
            notes=notes,
            graph_before=graph if graph_after else None,
        )
        (out / "diffgenome-change.json").write_text(dump_artifact(artifact))
        (out / "behavioral-map.md").write_text(behavior_map)
        print(text)
        _log(f"report: {out / 'report.md'}  graph: {out / 'graph.json'}  map: {out / 'map.md'}")
    finally:
        ws.destroy()
    return 0


def _under_test_root(symbol: str, index: SymbolIndex) -> bool:
    """True if the symbol is test code, as the runtime's index defines test code."""
    return index.is_test(symbol)
