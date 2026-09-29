# ruff: noqa: E501
"""Experiment 10, case A v4: seeded controls derived from the fresh v4 proposal.

c1  inverted link-row guard
c2  pre-change semantics seeded into the GENOME: the expansion's procedure sets
    reference_expanded := false (the reference implies nothing)
c2i pre-change semantics seeded into the INPUT: every occurrence says reference_expanded false
c3  missing decision
c4  fabricated site
c5  occurrence permutation in the SHOWN scenarios (two field occurrences with different facts
    swap facts; the checker can see these executions)
c5h the same permutation in the WITHHELD scenarios (no checker can see these executions)

usage: controls_exp10d.py <case-dir>
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any


def swap_first_differing(items: list[dict[str, Any]]) -> bool:
    for i in range(len(items) - 1):
        for j in range(i + 1, len(items)):
            if items[i]["facts"] != items[j]["facts"]:
                items[i]["facts"], items[j]["facts"] = items[j]["facts"], items[i]["facts"]
                return True
    return False


def main() -> int:
    case = Path(sys.argv[1])
    base = json.loads((case / "proposals.json").read_text())
    hold = json.loads((case / "holdout.json").read_text())
    out = case / "controls"
    out.mkdir(exist_ok=True)

    def dec(p: dict, i: str) -> dict:
        return next(d for d in p["decisions"] if d["id"] == i)

    controls: dict[str, Any] = {}
    c = copy.deepcopy(base)
    d = dec(c, "d_link_outside")
    d["predicate"] = "!" + d["predicate"]
    controls["c1-inverted-link-guard"] = c

    c = copy.deepcopy(base)
    c["transitions"] = [
        *c.get("transitions", []),
        {"id": "t_pre_change", "entity": "DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies",
         "when": "true", "sets": {"reference_expanded": "false"},
         "evidence": [{"kind": "source", "file": "backend/src/baserow/contrib/database/application_types.py", "line": 497, "text": "if not field_deps:"}]},
    ]  # fmt: skip
    for p in c["procedures"]:
        if p["entity"].endswith("_expand_implied_import_dependencies"):
            p["steps"] = [*p["steps"], "T:t_pre_change"]
    for v in c["variables"]:
        if v["name"] == "implied_dependency_found":
            v["definition"] = "false"
    controls["c2-pre-change-semantics"] = c

    c = copy.deepcopy(base)
    for sc in c["scenarios"].values():
        for call in sc["calls"]:
            for items in (call.get("occurrences") or {}).values():
                for it in items:
                    if "reference_expanded" in it.get("facts", {}):
                        it["facts"]["reference_expanded"] = False
    controls["c2i-pre-change-input"] = c

    c = copy.deepcopy(base)
    c["decisions"] = [d for d in c["decisions"] if d["id"] != "d_primary_missing"]
    for d in c["decisions"]:
        for b in ("true_branch", "false_branch"):
            d[b]["steps"] = [s for s in d[b].get("steps") or [] if s != "D:d_primary_missing"]
    controls["c3-missing-decision"] = c

    c = copy.deepcopy(base)
    dec(c, "d_link_outside")["site"] = "br:000000000000"
    controls["c4-fabricated-site"] = c

    for name, tests in (("c5-occurrence-permutation", hold["shown"]),
                        ("c5h-occurrence-permutation-withheld", hold["holdout"])):  # fmt: skip
        c = copy.deepcopy(base)
        for t in tests:
            for call in c["scenarios"][t]["calls"]:
                items = (call.get("occurrences") or {}).get("r_field")
                if items:
                    assert swap_first_differing(items)
        controls[name] = c

    for k, v in controls.items():
        (out / f"{k}.proposals.json").write_text(json.dumps(v, indent=1) + "\n")
    print(" ".join(controls))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
