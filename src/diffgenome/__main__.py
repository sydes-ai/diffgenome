import argparse
import json
import sys
from pathlib import Path

from diffgenome import mvp


def inspect_main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="diffgenome inspect")
    ap.add_argument("--graph", required=True, type=Path, help="graph.json written by an mvp run")
    ap.add_argument("--symbol", action="append", default=[], help="symbol id, or a suffix of one")
    ap.add_argument("--up", type=int, default=3)
    ap.add_argument("--down", type=int, default=4)
    ap.add_argument("--json", action="store_true", help="print the neighborhood as JSON")
    ap.add_argument(
        "--ambiguity", action="store_true", help="print the ambiguity/rejected-join report"
    )
    ap.add_argument(
        "--behavior",
        action="store_true",
        help="print the behavioral projection instead of the evidence slice",
    )
    args = ap.parse_args(argv)
    from diffgenome.graph import BehavioralGraph
    from diffgenome.report import render_map_slice

    graph = BehavioralGraph.from_json(json.loads(args.graph.read_text()))
    if args.ambiguity:
        from diffgenome.ambiguity import render_ambiguity

        print(render_ambiguity(graph))
        return 0
    if not args.symbol:
        print(f"{len(graph.symbols)} symbols, {len(graph.edges)} edges, {len(graph.gaps)} gaps")
        return 0
    seeds: list[str] = []
    for q in args.symbol:
        matches = [s for s in graph.symbols if s == q or s.endswith(q)]
        if not matches:
            print(f"no symbol matches {q!r}", file=sys.stderr)
            return 1
        seeds.extend(sorted(matches))
    if args.json:
        nb = graph.neighborhood(seeds, up=args.up, down=args.down)
        print(
            json.dumps(
                {
                    "seeds": seeds,
                    "metrics": nb.metrics().as_dict(),
                    "edges": [
                        {
                            "distance": d,
                            "caller": e.caller,
                            "callee": e.callee,
                            "kind": e.kind.value,
                            "best_join": e.best_join.name if e.best_join else None,
                            "executions": sorted(e.executions),
                            "probe_derived": e.probe_derived,
                        }
                        for d, e in sorted(
                            nb.edges.values(), key=lambda x: (x[0], x[1].caller, x[1].callee)
                        )
                    ],
                },
                indent=1,
            )
        )
    elif args.behavior:
        from diffgenome.projection import render_behavior_map

        print(render_behavior_map(graph, seeds, up=args.up, down=args.down))
    else:
        print(render_map_slice(graph, seeds, up=args.up, down=args.down))
    return 0


def evaluate_main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="diffgenome evaluate")
    ap.add_argument("--graph", required=True, type=Path, help="reconstructed graph.json")
    ap.add_argument("--ground-truth", required=True, type=Path, help="directory of complete traces")
    ap.add_argument("--entry", action="append", required=True, help="entry symbol (exact id)")
    ap.add_argument("--depth", type=int, default=6)
    ap.add_argument("--json", type=Path, default=None, help="also write the evaluation as JSON")
    ap.add_argument(
        "--traces",
        action="append",
        default=[],
        type=Path,
        help="directories of the executions the graph was built from (for seam grading)",
    )
    ap.add_argument(
        "--no-state",
        action="store_true",
        help="rebuild the graph from --traces ignoring state facts (the VALUE-only baseline)",
    )
    args = ap.parse_args(argv)
    from diffgenome.evaluate import (
        evaluate,
        ground_truth_from,
        render_evaluation,
        render_seams,
        seam_precision,
    )
    from diffgenome.graph import BehavioralGraph
    from diffgenome.model import Origin
    from diffgenome.serialize import execution_from_json

    graph = BehavioralGraph.from_json(json.loads(args.graph.read_text()))
    if args.no_state:
        from diffgenome.compose import build_corpus as _build_corpus
        from diffgenome.graph import build_graph as _build_graph

        runs = [
            execution_from_json(f.read_text())
            for d in args.traces
            for f in sorted(d.glob("*.json"))
        ]
        graph = _build_graph(_build_corpus(runs), use_state=False)
        print("(graph rebuilt from --traces with state facts ignored: VALUE-only baseline)\n")
    truth_runs = [
        execution_from_json(f.read_text()) for f in sorted(args.ground_truth.glob("*.json"))
    ]
    origins = {s.id: s.origin for e in truth_runs for s in e.symbols}
    origins.update(
        {sid: s.origin for sid, s in graph.symbols.items() if s.origin is not Origin.UNKNOWN}
    )
    gt = ground_truth_from(truth_runs, args.entry, origins)
    ev = evaluate(graph, gt, args.entry, depth=args.depth)
    print(render_evaluation(ev))
    doc = ev.as_dict()
    if args.traces:
        # path level needs the corpus behind the graph
        from diffgenome.compose import build_corpus
        from diffgenome.evaluate import (
            evaluate_paths,
            explain_paths,
            join_matrix,
            render_matrix,
            render_paths,
        )
        from diffgenome.graph import build_graph

        corpus_runs = [
            execution_from_json(f.read_text())
            for d in args.traces
            for f in sorted(d.glob("*.json"))
        ]
        full = build_graph(build_corpus(corpus_runs), use_state=not args.no_state)
        path_docs: list[dict[str, object]] = []
        for entry in args.entry:
            pe = evaluate_paths(full, truth_runs, entry, origins)
            print(render_paths(pe))
            explanations = explain_paths(pe, full)
            for line in explanations:
                print("  " + line)
            print()
            path_docs.append(
                {
                    "entry": entry,
                    "truth": pe.truth_paths,
                    "claimed": pe.claimed_paths,
                    "matched": pe.matched,
                    "extra": [list(p) for p in pe.extra],
                    "missed": [list(p) for p in pe.missed],
                    "outcome_mismatches": pe.outcome_mismatches,
                    "explanations": explanations,
                }
            )
        doc["paths"] = path_docs
    if args.traces:
        from diffgenome.model import CallNode, Execution

        def _repo_edges(ex: Execution) -> set[tuple[str, str]]:
            by_id = {n.id: n for n in ex.nodes}
            edges: set[tuple[str, str]] = set()
            for n in ex.nodes:
                if isinstance(n, CallNode) and n.parent is not None:
                    p = by_id[n.parent]
                    if (
                        isinstance(p, CallNode)
                        and origins.get(p.symbol) is Origin.REPO
                        and origins.get(n.symbol) is Origin.REPO
                    ):
                        edges.add((p.symbol, n.symbol))
            return edges

        per_exec = {ex.id: _repo_edges(ex) for ex in corpus_runs}
        truth_per_exec = [_repo_edges(ex) for ex in truth_runs]
        grades = seam_precision(graph, per_exec, gt)
        print("## Join lattice: seam-level precision")
        print(render_seams(grades))
        doc["seam_grades"] = [g.__dict__ for g in grades]
        rows = join_matrix(full, per_exec, gt, truth_per_exec)
        print("## Join matrix (seams on ground-truth paths)")
        print(render_matrix(rows))
        doc["join_matrix"] = [r.__dict__ for r in rows]
    if args.json:
        args.json.write_text(json.dumps(doc, indent=1) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "inspect":
        return inspect_main(argv[1:])
    if argv and argv[0] == "evaluate":
        return evaluate_main(argv[1:])
    if argv and argv[0] == "change":
        # The integrator's entry point: same pipeline as `mvp`, existing tests only by
        # default (no LLM call), and the diffgenome-change/1 artifact as the product.
        rest = argv[1:]
        if "--writer" not in rest:
            rest = ["--writer", "none", *rest]
        if "--probes" not in rest:
            rest = ["--probes", "0", *rest]
        if "--up" not in rest:
            # integrators ask "what reaches the change": follow callers far enough to meet
            # an entry point even when the change sits deep below it
            rest = ["--up", "5", *rest]
        if "--probe-max-distance" not in rest:
            # a probe is only worth its cost when the gap sits next to the change
            rest = ["--probe-max-distance", "1", *rest]
        return mvp.main(rest)
    if argv and argv[0] == "mvp":
        argv = argv[1:]
    return mvp.main(argv)


if __name__ == "__main__":
    sys.exit(main())
