# ruff: noqa: E501
"""Experiment 09: establish a state genome from shown tests only, then predict everything.

usage: establish_exp09.py <run-dir> <case-dir> <repo> [<proposals.json>] [<out-prefix>]
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

from diffgenome.genome import Substrate, dumps, genome_from_proposals, render_markdown
from diffgenome.genome_state import (
    Mechanics,
    Observations,
    StateSubstrate,
    compare_sequence,
    establish_state,
    path_condition,
    predict_sequence,
    regimes,
)
from diffgenome.serialize import execution_from_json

MODEL = "claude-opus-5-5"
TESTS = "api/tests/test_model_unload.py"


def agreement_from_sequences(
    g: Any, scenarios: dict[str, Any], obs: Observations
) -> dict[str, list[tuple[str, bool]]]:
    """Per decision: (test, agrees) — its predicted outcome sequence at its site, from the
    scenario with every proposal usable, equals the observed sequence at that site."""
    out: dict[str, list[tuple[str, bool]]] = {}
    for test, sc in scenarios.items():
        ob = obs.get(test)
        if ob is None:
            continue
        pred = predict_sequence(g, sc, min_status="hypothesis")
        for d in g.decisions:
            if not d.site:
                continue
            p = [v for e in pred.events if e[0] == "branch" and e[1] == d.site for v in [e[2]]]
            o = [b.outcome for b in ob.branches if b.site == d.site]
            if not p and not o:
                continue
            if pred.indeterminate and len(p) < len(o):
                continue  # the prediction stopped before reaching every evaluation
            out.setdefault(d.id, []).append((test, p == o))
    return out


def run(
    run_dir: Path, case: Path, proposals: dict[str, Any], tag: str, repo: Path
) -> dict[str, Any]:
    holdout = json.loads((case / "holdout.json").read_text())
    runs = [
        execution_from_json(f.read_text())
        for f in sorted((run_dir / "traces-existing").glob("*.json"))
    ]
    runs = [
        e for e in runs if e.stimulus_ref.startswith(TESTS) and "endpoint" not in e.stimulus_ref
    ]
    shown = [e for e in runs if e.stimulus_ref.split("::")[-1] in holdout["shown"]]
    mech = Mechanics(json.loads((run_dir / "mechanics.json").read_text())["functions"])
    base = Substrate([], set(), repo, set())
    obs_shown = Observations(shown)
    sub = StateSubstrate(base, mech, obs_shown)
    g = genome_from_proposals(proposals, {"repo": "Kokoro-FastAPI", "entry": "ModelManager"}, MODEL)
    scenarios = proposals.get("scenarios") or {}
    # agreement uses shown, in-scope executions: a sequential genome cannot agree with
    # interleaved coroutines, and concurrency is out of this experiment's scope
    shown_scen = {
        t: s
        for t, s in scenarios.items()
        if t in holdout["shown"] and t not in holdout.get("not_scored", [])
    }
    agree = agreement_from_sequences(g, shown_scen, obs_shown)
    establish_state(g, sub, agreement_seq=agree, out_of_scope=set(holdout.get("not_scored", [])))
    obs_all = Observations(runs)
    sites = {d.site for d in g.decisions if d.site}
    per_test = []
    for test, sc in sorted(scenarios.items()):
        ob = obs_all.get(test)
        if ob is None:
            continue
        pred = predict_sequence(g, sc)
        r = compare_sequence(g, pred, ob, sites)
        r["test"] = test
        r["withheld"] = test in holdout["holdout"]
        r["scored"] = test not in holdout.get("not_scored", [])
        per_test.append(r)
    # ablation: the same genome with every transition made to change nothing
    stateless = copy.deepcopy(g)
    for t in stateless.transitions:
        t.sets = {}
    ablation = []
    for test, sc in sorted(scenarios.items()):
        ob = obs_all.get(test)
        if ob is None or test in holdout.get("not_scored", []):
            continue
        r = compare_sequence(stateless, predict_sequence(stateless, sc), ob, sites)
        ablation.append({"test": test, "match": r["match"], "branches_exact": r["branches_exact"]})
    statuses: dict[str, dict[str, int]] = {}
    for kind in ("variables", "decisions", "transitions", "procedures", "rules", "regimes"):
        c: dict[str, int] = {}
        for it in getattr(g, kind):
            c[it.status] = c.get(it.status, 0) + 1
        statuses[kind] = c
    classes = regimes(obs_all, sites)
    g.provenance = {
        "model": MODEL, "context_bundle_sha": (case / "context-bundle.sha").read_text().strip(),
        "checker": "genome-check/1 (mechanics + observed branches + state deltas)",
        "established_from": holdout["shown"], "withheld_from_model_and_checker": holdout["holdout"],
    }  # fmt: skip
    return {
        "genome": g,
        "statuses": statuses,
        "per_test": per_test,
        "ablation": ablation,
        "path_conditions": {
            ob.execution.stimulus_ref.split("::")[-1]: path_condition(ob, sites, mech)
            for ob in obs_all.by_test.values()
        },
        "regime_classes": [sorted(t.split("::")[-1] for t in v) for v in classes.values()],
        "tag": tag,
    }


def main() -> int:
    run_dir, case, repo = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    prop_path = Path(sys.argv[4]) if len(sys.argv) > 4 else case / "proposals.json"
    prefix = sys.argv[5] if len(sys.argv) > 5 else ""
    res = run(run_dir, case, json.loads(prop_path.read_text()), prefix or "main", repo)
    g = res.pop("genome")
    (case / f"{prefix}genome.json").write_text(dumps(g))
    (case / f"{prefix}evaluation.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    g.subject = {
        "repo": "Kokoro-FastAPI",
        "change": "ModelManager lifecycle",
        "entry": "ModelManager",
    }
    md = render_markdown(g)
    scored = [r for r in res["per_test"] if r["scored"]]
    held = [r for r in scored if r["withheld"]]
    md += (
        "\n## Generative check (state sequences)\n\n"
        f"Scenario → genome (procedures, decisions, transitions) → predicted decision outcomes at the genome's sites, "
        f"in order, and predicted final bound state; compared exactly with what executed. Statuses were established "
        f"from the shown tests only.\n\n- exact on scored tests: {sum(r['match'] for r in scored)}/{len(scored)}\n"
        f"- exact on tests withheld from the model and the checker: {sum(r['match'] for r in held)}/{len(held)}\n"
        f"- the same genome with every transition removed (stateless ablation): "
        f"{sum(r['match'] for r in res['ablation'])}/{len(res['ablation'])}\n"
    )
    (case / f"{prefix}genome.md").write_text(md)
    print(json.dumps(res["statuses"]))
    scored = [r for r in res["per_test"] if r["scored"]]
    held = [r for r in scored if r["withheld"]]
    print(
        f"exact (branch vector + final bound state): {sum(r['match'] for r in scored)}/{len(scored)} scored; withheld {sum(r['match'] for r in held)}/{len(held)}"
    )
    print(f"stateless ablation: {sum(r['match'] for r in res['ablation'])}/{len(res['ablation'])}")
    for r in res["per_test"]:
        if not r["match"]:
            print(
                "  MISS",
                r["test"],
                "withheld" if r["withheld"] else "",
                "" if r["scored"] else "(not scored)",
                r["indeterminate"] or "",
                "state_diff",
                r["state_diff"],
                ""
                if r["branches_exact"]
                else f"pred {[(s[-4:], v) for s, v in r['predicted_branches']]} obs {[(s[-4:], v) for s, v in r['observed_branches']]}",
            )
    for d in g.decisions:
        print(f"  {d.id:18} {d.status:10} {d.status_reason[-120:]}")
    for t in g.transitions:
        print(f"  {t.id:18} {t.status:10} {t.status_reason[-110:]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
