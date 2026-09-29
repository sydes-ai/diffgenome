# ruff: noqa: E501  (the verbatim model prompt and report lines)
"""Establish the genome from model proposals + substrate, predict, and measure.

usage: establish.py <diffgenome-run-dir> <source-root> <case-dir> [<proposals.json>]

Writes <case-dir>/genome.json, evaluation.json. Status is assigned only by
diffgenome.genome.establish; the model's output is never trusted as-is.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from diffgenome.compose import build_corpus
from diffgenome.genome import (
    OBSERVED,
    STATIC,
    VERIFIED,
    Entity,
    Substrate,
    compare,
    dumps,
    establish,
    execution_paths,
    genome_from_proposals,
    predict,
    render_markdown,
    static_decision_sites,
    vocabulary,
)
from diffgenome.graph import BehavioralGraph
from diffgenome.serialize import execution_from_json

ENTRY = "go:api.Server.createTransfer"
MODEL = "claude-opus-5-5"
# Two scenario facts sets for the generative check, stated as the user would state them:
# the other gates pass, and only the amount/balance relation differs.
GATES_PASS = {
    "auth.present": True, "request.currency_supported": True, "from_account.found": True,
    "from_account.currency_match": True, "from_account.owned_by_auth": True,
    "to_account.found": True, "to_account.currency_match": True, "transfer_tx.ok": True,
}  # fmt: skip
CASES = {
    "A: amount > balance": {**GATES_PASS, "request.amount": 10, "from_account.balance": 9},
    "B: amount <= balance": {**GATES_PASS, "request.amount": 10, "from_account.balance": 10},
}


def main() -> int:
    run, source_root, case = (Path(a) for a in sys.argv[1:4])
    proposals_path = Path(sys.argv[4]) if len(sys.argv) > 4 else case / "proposals.json"
    proposals = json.loads(proposals_path.read_text())
    runs = [
        execution_from_json(f.read_text()) for f in sorted((run / "traces-existing").glob("*.json"))
    ]
    corpus = build_corpus(runs)
    paths = execution_paths(corpus, ENTRY, depth=2)
    graph = BehavioralGraph.from_json(json.loads((run / "graph.json").read_text()))
    observed_edges = {
        (e.caller.split(":", 1)[-1], e.callee.split(":", 1)[-1])
        for e in graph.edges.values()
        if e.kind.value == "observed"
    }
    sites = static_decision_sites(
        source_root, ["api/transfer.go", "api/validator.go", "api/middleware.go"]
    )
    sub = Substrate(paths, observed_edges, source_root, {(x["file"], x["line"]) for x in sites})
    artifact = json.loads((run / "diffgenome-change.json").read_text())

    g = genome_from_proposals(
        proposals,
        subject={"repo": "simplebank", "change": "5b03c1d", "entry": ENTRY},
        model=MODEL,
    )
    # the fact layer is the collector's, not the model's
    for n in artifact["nodes"]:
        g.entities.append(
            Entity(id=n["id"], derived_by="collector", status=OBSERVED, symbol=n["id"],
                   role="changed" if n["changed"] else "executed",
                   status_reason=f"executed by {n['executed_by']} existing execution(s)")
        )  # fmt: skip
    for b in artifact["boundaries"]:
        g.entities.append(
            Entity(id=b["target"], derived_by="collector", status=OBSERVED, symbol=b["target"],
                   role=f"boundary:{b['kind']}", status_reason=f"{b['kind']} via rule {'/'.join(b['rules'])}")
        )  # fmt: skip
    establish(g, sub)
    held = json.loads((case / "holdout.json").read_text())["holdout"]
    g.provenance = {
        "model": MODEL,
        "context_bundle_sha": (case / "context-bundle.sha").read_text().strip(),
        "checker": "genome-check/0",
        "substrate": {"executions": len(corpus.executions), "paths_under_entry": len(paths),
                      "observed_edges": len(observed_edges)},
        "withheld_from_model": held,
        "static_decision_sites": [
            {**s, "status": STATIC}
            for s in sites
        ],
    }  # fmt: skip
    (case / "genome.json").write_text(dumps(g))

    # generative check 1: each test's facts (from test source, proposed by the model)
    test_facts = proposals.get("test_facts") or {}
    per_test = []
    for p in paths:
        facts = test_facts.get(p.execution)
        if facts is None:
            per_test.append(
                {"execution": p.execution, "match": False, "indeterminate": "no test_facts"}
            )
            continue
        r = compare(predict(g, facts), p, vocabulary(g))
        r["withheld"] = p.execution in held
        per_test.append(r)
    # generative check 2: the two scenarios, using only decisions that reached VERIFIED
    # and, separately, everything at SUPPORTED or better
    scenarios = {}
    for name, facts in CASES.items():
        for floor in ("supported", VERIFIED):
            pr = predict(g, facts, min_status=floor)
            scenarios[f"{name} (decisions >= {floor})"] = {
                "facts": facts, "fired": pr.fired, "path": pr.path, "absent": pr.absent,
                "stopped_at": pr.stopped_at, "indeterminate": pr.indeterminate,
            }  # fmt: skip
    statuses: dict[str, dict[str, int]] = {}
    for kind in (
        "variables",
        "data_dependencies",
        "decisions",
        "effects",
        "transitions",
        "rules",
        "regimes",
    ):
        c: dict[str, int] = {}
        for it in getattr(g, kind):
            c[it.status] = c.get(it.status, 0) + 1
        statuses[kind] = c
    evaluation = {"statuses": statuses, "per_test": per_test, "scenarios": scenarios}
    (case / "evaluation.json").write_text(json.dumps(evaluation, indent=1) + "\n")
    (case / "genome.md").write_text(render_markdown(g, evaluation))
    print(json.dumps(statuses))
    exact = sum(1 for r in per_test if r.get("exact"))
    print(f"count-exact predictions: {exact}/{len(per_test)}")
    for r in per_test:
        if r.get("match") and not r.get("exact"):
            print("  COUNT", r["execution"], r.get("count_mismatch"))
    ok = sum(1 for r in per_test if r.get("match"))
    ok_held = sum(1 for r in per_test if r.get("match") and r.get("withheld"))
    print(
        f"per-test predictions matching observed paths: {ok}/{len(per_test)} (withheld: {ok_held}/{len(held)})"
    )
    for r in per_test:
        if not r.get("match"):
            print(
                "  MISS",
                r["execution"],
                {
                    k: r.get(k)
                    for k in (
                        "indeterminate",
                        "missing",
                        "out_of_order",
                        "wrongly_present",
                        "unpredicted",
                        "stopped_at",
                    )
                },
            )
    for k, v in scenarios.items():
        print(
            " ",
            k,
            "->",
            v["indeterminate"] or f"path {v['path']} absent {v['absent']} stop {v['stopped_at']}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
