# ruff: noqa: E501
"""Experiment 10, case A. DIAGNOSTIC ONLY, never a score.

Drops top-level scenario calls whose entity has no procedure (the proposal's format error),
predicts with every proposal usable (statuses ignored), and compares with the head traces:
exact global order, and each site's own outcome sequence (local semantics).

usage: diagnose_exp10.py <head-run> <case-dir> <proposals.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from diffgenome.genome import genome_from_proposals
from diffgenome.genome_state import Observations, compare_sequence, predict_sequence
from diffgenome.serialize import execution_from_json


def main() -> int:
    head, prop = Path(sys.argv[1]), Path(sys.argv[3])
    p = json.loads(prop.read_text())
    g = genome_from_proposals(p, {}, "diagnostic")
    procs = {pr.entity for pr in g.procedures}

    def has(e: str) -> bool:
        return any(k == e or k.endswith("." + e) or e.endswith("." + k) for k in procs)

    obs = Observations(
        [
            execution_from_json(f.read_text())
            for f in sorted((head / "traces-existing").glob("*.json"))
        ]
    )
    sites = {d.site for d in g.decisions if d.site}
    results = []
    for t, sc in sorted(p["scenarios"].items()):
        sc2 = {**sc, "calls": [c for c in sc["calls"] if has(c["entity"])]}
        r = compare_sequence(
            g, predict_sequence(g, sc2, min_status="hypothesis"), obs.get(t), sites
        )
        pv, ov = r["predicted_branches"], r["observed_branches"]
        i = next((k for k in range(min(len(pv), len(ov))) if pv[k] != ov[k]), min(len(pv), len(ov)))
        per_site = {
            s: [v for x, v in pv if x == s] == [v for x, v in ov if x == s] for s in sorted(sites)
        }
        results.append((t, r, pv, ov, i, per_site))
        print(
            f"{t[:66]:66} global-order match={r['match']} ind={r['indeterminate']} len p/o {len(pv)}/{len(ov)} first diff @{i}: p {pv[i : i + 2]} o {ov[i : i + 2]}"
        )
    print("-- per-site projection: predicted outcome sequence at each site == observed")
    for t, _r, _pv, _ov, _i, per_site in results:
        bad = [s[-4:] for s, v in per_site.items() if not v]
        print(f"{t[:66]:66} sites agreeing {sum(per_site.values())}/{len(per_site)} {bad}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
