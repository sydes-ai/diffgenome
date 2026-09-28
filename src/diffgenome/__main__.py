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
    args = ap.parse_args(argv)
    from diffgenome.graph import BehavioralGraph
    from diffgenome.report import render_map_slice

    graph = BehavioralGraph.from_json(json.loads(args.graph.read_text()))
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
        from diffgenome.model import CallNode

        per_exec: dict[str, set[tuple[str, str]]] = {}
        for d in args.traces:
            for f in sorted(d.glob("*.json")):
                ex = execution_from_json(f.read_text())
                by_id = {n.id: n for n in ex.nodes}
                edges = set()
                for n in ex.nodes:
                    if isinstance(n, CallNode) and n.parent is not None:
                        p = by_id[n.parent]
                        if (
                            isinstance(p, CallNode)
                            and origins.get(p.symbol) is Origin.REPO
                            and origins.get(n.symbol) is Origin.REPO
                        ):
                            edges.add((p.symbol, n.symbol))
                per_exec[ex.id] = edges
        grades = seam_precision(graph, per_exec, gt)
        print("## Join lattice: seam-level precision")
        print(render_seams(grades))
        doc["seam_grades"] = [g.__dict__ for g in grades]
    if args.json:
        args.json.write_text(json.dumps(doc, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    if argv and argv[0] == "inspect":
        sys.exit(inspect_main(argv[1:]))
    if argv and argv[0] == "evaluate":
        sys.exit(evaluate_main(argv[1:]))
    if argv and argv[0] == "mvp":
        argv = argv[1:]
    sys.exit(mvp.main(argv))
