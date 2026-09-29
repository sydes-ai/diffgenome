# ruff: noqa: E501
"""Experiment 10, case A v4: per-occurrence (local/procedural) accuracy of a region, separate
from whole-test exactness. For every occurrence of the region, the predicted properties
(site outcomes inside it, which modeled calls it makes) are compared with the aligned observed
repetition. Held-out traces are used here only to SCORE, never to check or build anything.

usage: occurrence_metrics_exp10.py <head-run> <case-dir> <region-id>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from diffgenome.genome import genome_from_proposals
from diffgenome.genome_state import genome_vocabulary, predict_sequence
from diffgenome.serialize import execution_from_json
from diffgenome.structure import build_skeleton, occurrences, repetitions, resolve


def predicted_occurrences(pred: Any, rid: str) -> list[list[tuple[str, bool]]]:
    out: list[list[tuple[str, bool]]] = []
    depth_region = False
    for e in pred.events:
        if e[0] == "occurrence":
            depth_region = e[1] == rid
            if depth_region:
                out.append([])
        elif e[0] == "branch" and depth_region and out:
            out[-1].append((e[1], e[2]))
    return out


def main() -> int:
    head, case, rid = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    p = json.loads((case / "proposals.json").read_text())
    hold = json.loads((case / "holdout.json").read_text())
    g = genome_from_proposals(p, {}, "m")
    r = next(x for x in g.regions if x.id == rid)
    vocab = genome_vocabulary(g)
    exs = {
        e.stimulus_ref.split("::")[-1]: e
        for e in (
            execution_from_json(f.read_text())
            for f in sorted((head / "traces-existing").glob("*.json"))
        )
    }
    sk = build_skeleton([exs[t] for t in hold["shown"]], vocab)
    reg = next(
        x for x in sk.regions[resolve(vocab, r.entity)] if x["head"] == resolve(vocab, r.head)
    )
    rows = []
    for t, sc in sorted(p["scenarios"].items()):
        pred = predict_sequence(g, sc, min_status="hypothesis")
        po = predicted_occurrences(pred, rid)
        occs = occurrences(exs[t], vocab)
        home = next(o for o in occs.values() if o.entity == resolve(vocab, r.entity))
        reps = repetitions(occs, home.id, reg["members"], reg["head"])
        exact = 0
        for i in range(max(len(po), len(reps))):
            pv = po[i] if i < len(po) else None
            ov = [(s, v) for s, v in (reps[i]["branches"] if i < len(reps) else [])]
            if pv is not None and sorted(pv) == sorted(ov):
                exact += 1
        rows.append(
            {
                "test": t,
                "withheld": t in hold["holdout"],
                "predicted": len(po),
                "observed": len(reps),
                "exact_occurrences": exact,
                "indeterminate": pred.indeterminate,
            }
        )
        print(
            f"{'W' if t in hold['holdout'] else 'S'} {t[:60]:60} occurrences exact {exact}/{len(reps)} (predicted {len(po)})"
        )
    (case / f"occurrence-metrics-{rid}.json").write_text(json.dumps(rows, indent=1) + "\n")
    tot = sum(x["observed"] for x in rows)
    print(
        f"total exact occurrences {sum(x['exact_occurrences'] for x in rows)}/{tot}; withheld {sum(x['exact_occurrences'] for x in rows if x['withheld'])}/{sum(x['observed'] for x in rows if x['withheld'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
