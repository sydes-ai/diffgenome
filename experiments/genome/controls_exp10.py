"""Experiment 10, case A: seeded negative controls derived from the fresh proposal.

usage: controls_exp10.py <case-dir>
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


def dec(p: dict, i: str) -> dict:
    return next(d for d in p["decisions"] if d["id"] == i)


def main() -> int:
    case = Path(sys.argv[1])
    base = json.loads((case / "proposals.json").read_text())
    out = case / "controls"
    out.mkdir(exist_ok=True)
    controls = {}
    c = copy.deepcopy(base)  # c1: the link-row guard inverted
    d = dec(c, "d_link_table_in_import")
    d["predicate"] = "link_table_in_import"
    controls["c1-inverted-link-guard"] = c
    c = copy.deepcopy(base)  # c2: the pre-change semantics: a link reference implies nothing
    for t in c["transitions"]:
        if t["id"] == "t_link_implies_primary":
            t["sets"] = {"implied_primary_dep": "false"}
    for s in c["scenarios"].values():
        if s["phenotype"]["base"] == "failed":  # the fix no longer fixes anything
            s["phenotype"] = {**s["phenotype"], "head": "failed"}
    controls["c2-pre-change-semantics"] = c
    c = copy.deepcopy(base)  # c3: missing decision
    c["decisions"] = [d for d in c["decisions"] if d["id"] != "d_link_primary_serialized"]
    for pr in c["procedures"]:
        pr["steps"] = [s for s in pr["steps"] if s != "D:d_link_primary_serialized"]
    controls["c3-missing-decision"] = c
    c = copy.deepcopy(base)  # c4: fabricated site id
    dec(c, "d_link_table_in_import")["site"] = "br:000000000000"
    controls["c4-fabricated-site"] = c
    for k, v in controls.items():
        (out / f"{k}.proposals.json").write_text(json.dumps(v, indent=1) + "\n")
    print(" ".join(controls))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
