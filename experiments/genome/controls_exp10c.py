"""Experiment 10, case A v3: seeded negative controls derived from the fresh v3 proposal.

c1 inverted link-row guard; c2 pre-change semantics (the link-row hook implies nothing);
c3 missing decision; c4 fabricated site. The hoisting control is the v2 proposal itself,
re-scored with the structure checks (docs/runs/genome-baserow-6069-v2/structure.*).

usage: controls_exp10c.py <case-dir>
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

    controls = {}
    c = copy.deepcopy(base)
    d = dec(c, "d_link_table_outside")
    d["predicate"] = d["predicate"].removeprefix("!")
    controls["c1-inverted-link-guard"] = c
    c = copy.deepcopy(base)
    next(t for t in c["transitions"] if t["id"] == "t_implied")["sets"] = {
        "implied_dependency": "false"
    }
    for s in c["scenarios"].values():
        if s["phenotype"]["base"] != s["phenotype"]["head"]:
            s["phenotype"] = {**s["phenotype"], "head": s["phenotype"]["base"]}
    controls["c2-pre-change-semantics"] = c
    c = copy.deepcopy(base)
    c["decisions"] = [d for d in c["decisions"] if d["id"] != "d_link_primary_missing"]
    for p in c["procedures"]:
        p["steps"] = [s for s in p["steps"] if s != "D:d_link_primary_missing"]
    controls["c3-missing-decision"] = c
    c = copy.deepcopy(base)
    dec(c, "d_link_table_outside")["site"] = "br:000000000000"
    controls["c4-fabricated-site"] = c
    for k, v in controls.items():
        (out / f"{k}.proposals.json").write_text(json.dumps(v, indent=1) + "\n")
    print(" ".join(controls))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
