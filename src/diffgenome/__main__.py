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


if __name__ == "__main__":
    argv = sys.argv[1:]
    if argv and argv[0] == "inspect":
        sys.exit(inspect_main(argv[1:]))
    if argv and argv[0] == "mvp":
        argv = argv[1:]
    sys.exit(mvp.main(argv))
