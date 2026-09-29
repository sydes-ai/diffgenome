# ruff: noqa: E501
"""Re-check experiment 08's proposals (unchanged) against the stronger substrate.

usage: reestablish_exp08.py <run-dir with traces-existing + mechanics.json + graph.json> <source-root> <exp08-case-dir> <out.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from diffgenome.compose import build_corpus
from diffgenome.genome import (
    Substrate,
    execution_paths,
    genome_from_proposals,
    static_decision_sites,
)
from diffgenome.genome_state import (
    Mechanics,
    Observations,
    StateSubstrate,
    agreement_from_facts,
    establish_state,
)
from diffgenome.graph import BehavioralGraph
from diffgenome.serialize import execution_from_json

ENTRY = "go:api.Server.createTransfer"


def main() -> int:
    run, src, case, out = (Path(a) for a in sys.argv[1:5])
    runs = [
        execution_from_json(f.read_text()) for f in sorted((run / "traces-existing").glob("*.json"))
    ]
    corpus = build_corpus(runs)
    graph = BehavioralGraph.from_json(json.loads((run / "graph.json").read_text()))
    edges = {
        (e.caller.split(":", 1)[-1], e.callee.split(":", 1)[-1])
        for e in graph.edges.values()
        if e.kind.value == "observed"
    }
    sites = static_decision_sites(src, ["api/transfer.go", "api/validator.go", "api/middleware.go"])
    base = Substrate(
        execution_paths(corpus, ENTRY, 2), edges, src, {(x["file"], x["line"]) for x in sites}
    )
    mech = Mechanics(json.loads((run / "mechanics.json").read_text())["functions"])
    sub = StateSubstrate(base, mech, Observations(runs))
    before = {
        d["id"]: d["status"] for d in json.loads((case / "genome.json").read_text())["decisions"]
    }
    proposals = json.loads((case / "proposals-v1.json").read_text())
    g = genome_from_proposals(proposals, {"entry": ENTRY}, "claude-opus-5-5")
    establish_state(g, sub, agreement_from_facts(g, proposals.get("test_facts") or {}))
    rows = [
        {
            "id": d.id,
            "predicate": d.predicate,
            "entity": d.entity,
            "exp08": before.get(d.id),
            "now": d.status,
            "site": d.site,
            "site_pred": mech.sites.get(d.site or "", {}).get("pred"),
            "reason": d.status_reason,
        }
        for d in g.decisions
    ]
    Path(out).write_text(json.dumps(rows, indent=1) + "\n")
    for r in rows:
        print(
            f"{r['id']:3} {r['exp08']:9} -> {r['now']:9} site `{r['site_pred']}` | {r['reason'][-150:]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
