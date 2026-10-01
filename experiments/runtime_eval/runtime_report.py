# ruff: noqa: E501
"""Deterministic runtime facts about a change, from a `diffgenome change` run (no model, no genome).

For every function whose body the diff touches (head-side changed lines):
  - executed or not, how often, by which tests, with which exits;
  - decision sites on changed lines: outcomes observed (T/F) or never evaluated;
  - calls on changed lines: observed from that function or not;
  - exceptions raised by callees inside it (how except-handlers become observable).
Plus the observation boundaries of the artifact and the test universe that was run.

usage: runtime_report.py <run-dir> <repo-clone> <base> <head> <out.json>
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from diffgenome.serialize import execution_from_json
from diffgenome.model import CallNode


def changed_lines(repo: Path, base: str, head: str) -> dict[str, set[int]]:
    out: dict[str, set[int]] = defaultdict(set)
    cur = None
    diff = subprocess.run(["git", "-C", str(repo), "diff", "-U0", base, head], capture_output=True, text=True).stdout
    for ln in diff.splitlines():
        if ln.startswith("+++ "):
            cur = ln[6:] if ln.startswith("+++ b/") else None
        elif ln.startswith("@@") and cur:
            m = re.search(r"\+(\d+)(?:,(\d+))?", ln)
            start, n = int(m.group(1)), int(m.group(2) or 1)
            out[cur].update(range(start, start + max(n, 1)))
    return out


def main() -> int:
    run, repo, base, head, out = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4], Path(sys.argv[5])
    lines = changed_lines(repo, base, head)
    mech = json.loads((run / "mechanics.json").read_text())["functions"]
    art = json.loads((run / "diffgenome-change.json").read_text())

    # functions whose span (first..last recorded line) the diff touches, from mechanics
    def span(f):
        ls = [s["line"] for s in f["sites"]] + [c["line"] for c in f["calls"]] + [r["line"] for r in f.get("returns", [])]
        return (min(ls), max(ls)) if ls else None

    touched = {}
    for f in mech:
        sp, cl = span(f), lines.get(f["file"], set())
        if sp and any(sp[0] - 3 <= ln <= sp[1] + 1 for ln in cl):
            touched[f["symbol"]] = f
    for s in art["change"]["symbols"]:  # attribution may name functions without mechanics (e.g. Go)
        touched.setdefault(s, None)

    calls = defaultdict(list)      # symbol -> [(test, outcome)]
    tests_of = defaultdict(set)
    site_out = defaultdict(Counter)  # site -> Counter(True/False)
    child_seen = defaultdict(set)  # parent symbol -> callee symbols observed
    raised_inside = defaultdict(Counter)  # parent symbol -> Counter(child raised outcome)
    universe = []
    for f in sorted((run / "traces-existing").glob("*.json")):
        ex = execution_from_json(f.read_text())
        universe.append((ex.stimulus_ref, ex.outcome))
        nodes = {n.id: n for n in ex.nodes}
        for n in ex.nodes:
            if not isinstance(n, CallNode):
                continue
            calls[n.symbol].append((ex.stimulus_ref, n.outcome))
            tests_of[n.symbol].add(ex.stimulus_ref)
            p = nodes.get(n.parent) if n.parent is not None else None
            if isinstance(p, CallNode):
                child_seen[p.symbol].add(n.symbol)
                if str(n.outcome).startswith(("raised", "panic", "returned-error")):
                    raised_inside[p.symbol][n.outcome] += 1
        for b in ex.branches:
            site_out[b.site][b.outcome] += 1

    report = {"universe": {"executions": len(universe), "passed": sum(o == "passed" for _, o in universe),
                           "failed": sum(o != "passed" for _, o in universe)},
              "boundaries": [{k: b.get(k) for k in ("kind", "caller", "target")} for b in art.get("boundaries") or []],
              "functions": []}
    for sym, f in sorted(touched.items()):
        cl = lines.get(f["file"], set()) if f else set()
        entry = {
            "symbol": sym,
            "file": f["file"] if f else None,
            "executed_calls": len(calls.get(sym, [])),
            "tests": sorted(tests_of.get(sym, set())),
            "exits": dict(Counter(o for _, o in calls.get(sym, []))),
            "raised_inside": dict(raised_inside.get(sym, {})),
            "changed_sites": [
                {"site": s["site"], "line": s["line"], "pred": s["pred"],
                 "true": site_out[s["site"]].get(True, 0), "false": site_out[s["site"]].get(False, 0)}
                for s in (f["sites"] if f else []) if s["line"] in cl
            ],
            "changed_calls": [
                {"line": c["line"], "callee": c["callee"],
                 "observed": any(x.split(":")[-1].endswith("." + c["callee"].split(".")[-1]) or x.endswith(":" + c["callee"]) for x in child_seen.get(sym, set()))}
                for c in (f["calls"] if f else []) if c["line"] in cl
            ],
        }
        report["functions"].append(entry)
    out.write_text(json.dumps(report, indent=1) + "\n")
    fs = report["functions"]
    print(f"universe {report['universe']}; changed functions {len(fs)}; executed {sum(1 for x in fs if x['executed_calls'])}")
    for x in fs:
        part = [f"{x['symbol'].split(':',1)[-1][-70:]:70} calls={x['executed_calls']:4} tests={len(x['tests']):3} exits={x['exits']}"]
        for s in x["changed_sites"]:
            part.append(f"      site L{s['line']} `{s['pred'][:60]}` T={s['true']} F={s['false']}")
        for c in x["changed_calls"]:
            if not c["observed"]:
                part.append(f"      call L{c['line']} {c['callee'][:60]} NOT observed")
        print("\n".join(part))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
