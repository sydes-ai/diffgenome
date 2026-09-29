"""Experiment 10, case A v2: seeded negative controls derived from the fresh v2 proposal.

c1 inverted link-row guard; c2 pre-change semantics (the link-row hook implies nothing and
the expansion never rewrites a dependency set); c3 missing decision; c4 fabricated site.

usage: controls_exp10b.py <case-dir>
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


def main() -> int:
    case = Path(sys.argv[1])
    base = json.loads((case / "proposals.json").read_text())
    out = case / "controls"
    out.mkdir(exist_ok=True)

    def dec(p: dict, i: str) -> dict:
        return next(d for d in p["decisions"] if d["id"] == i)

    def tr(p: dict, i: str) -> dict:
        return next(t for t in p["transitions"] if t["id"] == i)

    controls = {}
    c = copy.deepcopy(base)
    d = dec(c, "d_link_table_missing")
    d["predicate"] = "!" + d["predicate"]
    controls["c1-inverted-link-guard"] = c
    c = copy.deepcopy(base)
    tr(c, "t_link_found")["sets"] = {"implied_dep_found": "false"}
    tr(c, "t_expand_map")["sets"] = {**tr(c, "t_expand_map")["sets"], "deps_rewritten": "false"}
    for v in c["variables"]:
        if v["name"] in ("implied_dep_found", "deps_rewritten"):
            v["definition"] = "false"
    for s in c["scenarios"].values():  # under these semantics the fix fixes nothing
        if s["phenotype"]["base"] != s["phenotype"]["head"]:
            s["phenotype"] = {**s["phenotype"], "head": s["phenotype"]["base"]}
    controls["c2-pre-change-semantics"] = c
    c = copy.deepcopy(base)
    c["decisions"] = [d for d in c["decisions"] if d["id"] != "d_link_primary_missing"]
    for d in c["decisions"]:
        for b in ("true_branch", "false_branch"):
            d[b]["steps"] = [
                s if s != "D:d_link_primary_missing" else "T:t_link_found"
                for s in d[b].get("steps") or []
            ]
    controls["c3-missing-decision"] = c
    c = copy.deepcopy(base)
    dec(c, "d_link_table_missing")["site"] = "br:000000000000"
    controls["c4-fabricated-site"] = c
    for k, v in controls.items():
        (out / f"{k}.proposals.json").write_text(json.dumps(v, indent=1) + "\n")
    print(" ".join(controls))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
