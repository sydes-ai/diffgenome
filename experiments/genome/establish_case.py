# ruff: noqa: E501
"""Establish a stress-suite case (B, C) exactly as Baserow v4: statuses from the SHOWN tests
only; prediction of every scenario scored against every observed evaluation of the change's
sites, with the observed-structure placement check and (shown tests only) occurrence checks.

usage: establish_case.py <head-run> <case-dir> <test-prefix> <entry> <head-tree> [<proposals.json>] [<out-prefix>]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from diffgenome.genome import (
    SUPPORTED,
    VERIFIED,
    Substrate,
    bindings_of,
    dumps,
    genome_from_proposals,
    render_markdown,
)
from diffgenome.genome_state import (
    Mechanics,
    Observations,
    StateSubstrate,
    change_sites,
    compare_sequence,
    establish_state,
    exit_matches,
    genome_vocabulary,
    predict_sequence,
    procedure_structure_claims,
)
from diffgenome.model import CallNode
from diffgenome.serialize import execution_from_json
from diffgenome.structure import build_skeleton

MODEL = "claude-opus-5-5"


def unknown_dependence(mech_fns: list[dict[str, Any]], changed: list[str]) -> dict[str, int]:
    ops = unk = args = uargs = 0
    for f in mech_fns:
        if f["symbol"] not in changed:
            continue
        for s in f["sites"]:
            for o in s["operands"]:
                ops += 1
                unk += any(x.startswith("unknown:") for x in o["origins"])
        for c in f["calls"]:
            for a in c["arg_origins"]:
                args += 1
                uargs += any(x.startswith("unknown:") for x in a)
    return {
        "decision_operands": ops,
        "unknown_operands": unk,
        "call_args": args,
        "unknown_call_args": uargs,
    }


def main() -> int:
    run, case, prefix, entry = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
    tree = Path(sys.argv[5])  # the head's source tree: `source` evidence is checked against it
    prop_path = Path(sys.argv[6]) if len(sys.argv) > 6 else case / "proposals.json"
    out_prefix = sys.argv[7] if len(sys.argv) > 7 else ""
    proposals = json.loads(prop_path.read_text())
    hold = json.loads((case / "holdout.json").read_text())
    runs = {
        e.stimulus_ref: e
        for e in (
            execution_from_json(f.read_text())
            for f in sorted((run / "traces-existing").glob("*.json"))
        )
    }
    # one prefix: tests named by subtest; several (comma-separated): by full reference
    prefixes = prefix.split(",")
    full = len(prefixes) > 1
    tests = {
        (k if full else k.split("/", 1)[1]): v
        for k, v in runs.items()
        if k.startswith(tuple(prefixes))
    }
    shown = [tests[t] for t in hold["shown"]]
    mfns = json.loads((run / "mechanics.json").read_text())["functions"]
    mech = Mechanics(mfns)
    changed = json.loads((run / "diffgenome-change.json").read_text())["change"]["symbols"]
    obs_shown = Observations(shown)
    obs_all = Observations(list(tests.values()))
    g = genome_from_proposals(proposals, {"case": case.name}, MODEL)
    scenarios = proposals.get("scenarios") or {}
    # observations are keyed by the full stimulus ref; scenarios by the subtest name
    ref = {t: (t if full else f"{prefix}{t}") for t in tests}
    agree: dict[str, list[tuple[str, bool]]] = {}
    for t, sc in scenarios.items():
        if t not in hold["shown"]:
            continue
        ob = obs_shown.get(ref[t])
        pred = predict_sequence(g, sc, min_status="hypothesis")
        for d in g.decisions:
            if not d.site:
                continue
            p = [e[2] for e in pred.events if e[0] == "branch" and e[1] == d.site]
            o = [b.outcome for b in ob.branches if b.site == d.site]
            if (not p and not o) or (pred.indeterminate and len(p) < len(o)):
                continue
            agree.setdefault(d.id, []).append((t, p == o))
    sub = StateSubstrate(Substrate([], set(), tree, set()), mech, obs_shown)
    shown_scen = {ref[t]: s for t, s in scenarios.items() if t in hold["shown"]}
    establish_state(g, sub, agreement_seq=agree, scenarios=shown_scen)
    sk = build_skeleton(shown, genome_vocabulary(g))
    required = change_sites(mech, obs_shown, changed)
    sites = {d.site for d in g.decisions if d.site}
    per_test = []
    for t, sc in sorted(scenarios.items()):
        if t not in tests:
            continue
        ob = obs_all.get(ref[t])
        pred = predict_sequence(g, sc)
        visible = t in hold["shown"]
        r = compare_sequence(g, pred, ob, sites, required, sk, sc if visible else None)
        # the test's entry: the first listed entry (comma-separated, outermost first) it calls
        calls = [n for n in ob.execution.nodes if isinstance(n, CallNode)]
        chosen = next((e for e in entry.split(",") if any(e in n.symbol for n in calls)), None)
        exits = [n.outcome for n in calls if chosen and chosen in n.symbol]
        ph = (sc.get("phenotype") or {}).get("head")
        r.update(test=t, withheld=t in hold["holdout"], observed_entry_exits=exits,
                 phenotype_claim=ph, phenotype_exact=bool(exits) and ph is not None and all(exit_matches(ph, o) is True for o in exits))  # fmt: skip
        per_test.append(r)
    claims = procedure_structure_claims(g, sk)
    outcome_claims = []
    for d in g.decisions:
        for b in (d.true_branch, d.false_branch):
            if b.outcome and b.outcome.get("is"):
                outcome_claims.append(("branch", d.id, d.status == VERIFIED))
    for p in g.procedures:
        if p.outcome and p.outcome.get("is"):
            outcome_claims.append(
                ("procedure", p.id, p.status == SUPPORTED and "observed in" in p.status_reason)
            )
    pt = per_test
    held = [r for r in pt if r["withheld"]]
    summary = {
        "exact_all": f"{sum(r['match'] for r in pt)}/{len(pt)}",
        "exact_withheld": f"{sum(r['match'] for r in held)}/{len(held)}",
        "confidently_wrong": sum(1 for r in pt if not r["indeterminate"] and not r["match"]),
        "indeterminate": sum(1 for r in pt if r["indeterminate"]),
        "decisions_verified": f"{sum(d.status == VERIFIED for d in g.decisions)}/{len(g.decisions)}",
        "transitions_verified": f"{sum(t.status == VERIFIED for t in g.transitions)}/{len(g.transitions)}",
        "outcomes_verified": f"{sum(ok for *_, ok in outcome_claims)}/{len(outcome_claims)}",
        "occurrence_facts": {
            st: sum((r.get("occurrence_checks") or {}).get(st, 0) for r in pt)
            for st in ("confirmed", "contradicted", "unobservable")
        },
        "regions": len(g.regions),
        "structure_claims": {
            st: sum(1 for c in claims if c["status"] == st)
            for st in ("verified", "supported", "rejected", "not established", "unobserved")
        },
        "required_sites_observed_uncovered": sorted(
            {s for r in pt for s in r.get("uncovered_sites", [])}
        ),
        "unknown_dependence": unknown_dependence(mfns, changed),
        "rejected": [
            i.id
            for k in (
                "variables",
                "decisions",
                "transitions",
                "procedures",
                "regions",
                "rules",
                "regimes",
            )
            for i in getattr(g, k)
            if i.status == "rejected"
        ],
        "hypothesis": [
            i.id
            for k in (
                "variables",
                "decisions",
                "transitions",
                "procedures",
                "regions",
                "rules",
                "regimes",
            )
            for i in getattr(g, k)
            if i.status == "hypothesis"
        ],
        "phenotype_claims_exact": f"{sum(r['phenotype_exact'] for r in pt)}/{len(pt)}",
        "identity_claims": {
            v.name: v.status
            for v in g.variables
            if sum(1 for b in bindings_of(v) if b.get("kind") == "identity") >= 2
        },
        "literal_bindings": {
            v.name: bool(b.get("_literal_ok"))
            for v in g.variables
            for b in bindings_of(v)
            if b.get("kind") == "equals_literal"
        },
    }
    (case / f"{out_prefix}genome.json").write_text(dumps(g))
    (case / f"{out_prefix}genome.md").write_text(render_markdown(g))
    (case / f"{out_prefix}evaluation.json").write_text(
        json.dumps(
            {"summary": summary, "per_test": per_test, "structure_claims": claims},
            indent=1,
            default=str,
        )
        + "\n"
    )
    print(json.dumps(summary))
    for r in pt:
        print(
            f"  {'W' if r['withheld'] else 'S'} {r['test'][:50]:50} match={r['match']!s:5} ind={(r['indeterminate'] or '')[:80]}"
        )
        if not r["match"] and not r["indeterminate"]:
            p, o = r["predicted_branches"], r["observed_branches"]
            i = next((k for k in range(min(len(p), len(o))) if p[k] != o[k]), min(len(p), len(o)))
            print(
                f"      first divergence at {i}: pred {p[i : i + 2]} obs {o[i : i + 2]} (len {len(p)}/{len(o)}) outcome_diff {r.get('outcome_diff')}"
            )
    for d in g.decisions:
        print(f"    {d.id:26} {d.status:10} {d.status_reason[-110:]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
