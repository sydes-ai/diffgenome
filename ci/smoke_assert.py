"""Check one smoke case's runtime contract against its expectations (ci/smoke-cases.json)."""

import json
import sys
from pathlib import Path

case = json.loads(Path(sys.argv[1]).read_text())[sys.argv[2]]["expect"]
runtime = json.loads(Path(sys.argv[3]).read_text())["runtime"]
fns = {f["symbol"].split(":", 1)[-1]: f for f in runtime["changed_functions"]}
passed = runtime["universe"]["passed"]
problems = []
if passed < case["min_passed"]:
    problems.append(f"{passed} tests passed < {case['min_passed']}")
for name in case.get("executed", []):
    if not fns.get(name, {}).get("executed"):
        problems.append(f"{name} not executed")
if "max_failed" in case and runtime["universe"]["failed"] > case["max_failed"]:
    problems.append(f"{runtime['universe']['failed']} tests failed > {case['max_failed']}")
if runtime["universe"].get("skipped", 0) < case.get("min_skipped", 0):
    problems.append(f"{runtime['universe'].get('skipped', 0)} skipped < {case['min_skipped']}")
for where in case.get("no_gap_at", []):  # "file:line": a gap DiffGenome must not report
    path, line = where.rsplit(":", 1)
    if any(g.get("file") == path and g.get("line") == int(line) for g in runtime["gaps"]):
        problems.append(f"wrong gap reported at {where}")
for name in case.get("ran_at_import", []):
    if not fns.get(name, {}).get("ran_at_import"):
        problems.append(f"{name} not seen at import")
print(f"{sys.argv[2]}: {passed} passed; "
      f"{sum(f['executed'] for f in fns.values())}/{len(fns)} changed functions executed")
if problems:
    sys.exit("FAILED: " + "; ".join(problems) + f"  ({case.get('why', '')})")
print("ok")
