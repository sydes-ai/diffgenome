# ruff: noqa: E501
"""Experiment 10, case A: establish the proposed genome from shown tests only, predict all.

Two substrates, same proposal and same frozen checker (genome_state at 5f45eb2):
  frozen   — mechanics.json exactly as `diffgenome change` wrote it;
  coverage — ABLATION computed here, not in the core: the same front end additionally
             applied to nested functions of the lowered files and to the unchanged
             DeferredFieldImporter file. Closure variables of a nested function resolve as
             `global:` (the front end has no closure scope) — a stated caveat.

usage: establish_exp10.py <head-run> <base-run> <case-dir> <head-tree> [<proposals.json>] [<out-prefix>] [frozen|repaired]
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

from diffgenome.dependence import analyze_all
from diffgenome.frontends.python_ir import _Lower, lower_functions
from diffgenome.genome import Substrate, dumps, genome_from_proposals, render_markdown
from diffgenome.genome_state import (
    Mechanics,
    Observations,
    StateSubstrate,
    change_sites,
    compare_sequence,
    establish_state,
    predict_sequence,
    regimes,
)
from diffgenome.serialize import execution_from_json

MODEL = "claude-opus-5-5"
LOWERED = {
    "backend/src/baserow/contrib/database/application_types.py": "baserow.contrib.database.application_types",
    "backend/src/baserow/contrib/database/fields/field_types.py": "baserow.contrib.database.fields.field_types",
    "backend/src/baserow/contrib/database/fields/registries.py": "baserow.contrib.database.fields.registries",
}
UNCHANGED = {
    "backend/src/baserow/contrib/database/fields/utils/deferred_field_importer.py": "baserow.contrib.database.fields.utils.deferred_field_importer",
}


def nested_functions(source: str, rel: str, module: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def params(n: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
        a = n.args
        ps = [x.arg for x in [*a.posonlyargs, *a.args, *a.kwonlyargs]]
        return ps + [x.arg for x in (a.vararg, a.kwarg) if x is not None]

    def visit(body: list[ast.stmt], prefix: str, in_fn: bool) -> None:
        for n in body:
            if isinstance(n, ast.ClassDef) and not in_fn:
                visit(n.body, f"{prefix}{n.name}.", False)
            elif isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef):
                q = f"{prefix}{n.name}"
                if in_fn:
                    out.append(
                        {"symbol": f"py:{module}.{q}", "file": rel, "params": params(n),
                         "body": _Lower(rel).block(n.body)}
                    )  # fmt: skip
                visit(n.body, f"{q}.<locals>.", True)

    visit(ast.parse(source).body, "", False)
    return out


def coverage_mechanics(frozen: list[dict[str, Any]], tree: Path) -> list[dict[str, Any]]:
    extra: list[dict[str, Any]] = []
    for rel, mod in LOWERED.items():
        extra += nested_functions((tree / rel).read_text(), rel, mod)
    for rel, mod in UNCHANGED.items():
        src = (tree / rel).read_text()
        extra += lower_functions(src, rel, mod) + nested_functions(src, rel, mod)
    return frozen + analyze_all(extra)


def run(
    head_run: Path,
    base_run: Path,
    case: Path,
    proposals: dict[str, Any],
    mech_fns: list[dict[str, Any]],
    tree: Path,
    required_symbols: list[str] | None = None,
) -> dict[str, Any]:
    holdout = json.loads((case / "holdout.json").read_text())
    scenarios = proposals.get("scenarios") or {}
    runs = [
        execution_from_json(f.read_text())
        for f in sorted((head_run / "traces-existing").glob("*.json"))
    ]
    base_runs = {
        e.stimulus_ref.split("::")[-1]: e
        for e in (
            execution_from_json(f.read_text())
            for f in sorted((base_run / "traces-existing").glob("*.json"))
        )
    }
    in_scope = [
        e for e in runs if e.stimulus_ref.split("::")[-1] in (holdout["shown"] + holdout["holdout"])
    ]
    shown = [e for e in in_scope if e.stimulus_ref.split("::")[-1] in holdout["shown"]]
    mech = Mechanics(mech_fns)
    sub = StateSubstrate(Substrate([], set(), tree, set()), mech, Observations(shown))
    g = genome_from_proposals(
        proposals, {"repo": "baserow", "entry": "_import_table_fields"}, MODEL
    )
    obs_shown = Observations(shown)
    # scenario agreement from shown tests (as Experiment 09)
    agree: dict[str, list[tuple[str, bool]]] = {}
    for test, sc in scenarios.items():
        if test not in holdout["shown"]:
            continue
        ob = obs_shown.get(test)
        if ob is None:
            continue
        pred = predict_sequence(g, sc, min_status="hypothesis")
        for d in g.decisions:
            if not d.site:
                continue
            p = [e[2] for e in pred.events if e[0] == "branch" and e[1] == d.site]
            o = [b.outcome for b in ob.branches if b.site == d.site]
            if not p and not o:
                continue
            if pred.indeterminate and len(p) < len(o):
                continue
            agree.setdefault(d.id, []).append((test, p == o))
    establish_state(g, sub, agreement_seq=agree)
    obs_all = Observations(in_scope)
    sites = {d.site for d in g.decisions if d.site}
    # scored on every observed site of the changed functions (genome_state.change_sites),
    # not only on the sites the genome chose; None keeps Experiment 09's rule
    required = change_sites(mech, obs_all, required_symbols) if required_symbols else None
    per_test = []
    for test, sc in sorted(scenarios.items()):
        ob = obs_all.get(test)
        if ob is None:
            continue
        pred = predict_sequence(g, sc)
        r = compare_sequence(g, pred, ob, sites, required)
        chosen = compare_sequence(g, pred, ob, sites)
        # the same prediction with every proposal usable: what the model's semantics alone
        # would have predicted, independent of what the checker could establish
        rh = compare_sequence(g, predict_sequence(g, sc, min_status="hypothesis"), ob, sites)
        ph = sc.get("phenotype") or {}
        base_ex = base_runs.get(test)
        r.update(
            test=test,
            withheld=test in holdout["holdout"],
            match_on_genome_sites=chosen["match"],
            unchecked_semantics_match=rh["match"],
            unchecked_indeterminate=rh["indeterminate"],
            phenotype_claim=ph,
            phenotype_observed={
                "head": ob.execution.outcome,
                "base": base_ex.outcome if base_ex else None,
            },
            phenotype_exact=ph.get("head") == ob.execution.outcome
            and base_ex is not None
            and ph.get("base") == base_ex.outcome,
            n_observed_at_sites=len(r["observed_branches"]),
        )
        per_test.append(r)
    statuses: dict[str, dict[str, int]] = {}
    for kind in ("variables", "decisions", "transitions", "procedures", "rules", "regimes"):
        c: dict[str, int] = {}
        for it in getattr(g, kind):
            c[it.status] = c.get(it.status, 0) + 1
        statuses[kind] = c
    g.provenance = {
        "model": MODEL, "context_bundle_sha": (case / "context-bundle.sha").read_text().strip(),
        "checker": "genome-check/1 (genome_state at 5f45eb2, unchanged)",
        "established_from": holdout["shown"], "withheld_from_model_and_checker": holdout["holdout"],
    }  # fmt: skip
    return {
        "genome": g,
        "statuses": statuses,
        "per_test": per_test,
        "regime_classes": [
            sorted(t.split("::")[-1] for t in v) for v in regimes(obs_all, sites).values()
        ],
        "sites_in_mechanics": sorted(s for s in sites if s in mech.sites),
        "sites_not_in_mechanics": sorted(s for s in sites if s not in mech.sites),
        "required_sites": sorted(required or []),
        "required_sites_uncovered": sorted((required or set()) - sites),
    }


def summarize(res: dict[str, Any], g: Any) -> dict[str, Any]:
    pt = res["per_test"]
    held = [r for r in pt if r["withheld"]]
    return {
        "exact_all": f"{sum(r['match'] for r in pt)}/{len(pt)}",
        "exact_withheld": f"{sum(r['match'] for r in held)}/{len(held)}",
        "exact_on_genome_chosen_sites": f"{sum(r['match_on_genome_sites'] for r in pt)}/{len(pt)}",
        "required_sites_uncovered": res["required_sites_uncovered"],
        "indeterminate": sum(1 for r in pt if r["indeterminate"]),
        "confidently_wrong": sum(1 for r in pt if not r["indeterminate"] and not r["match"]),
        "unchecked_semantics_exact": f"{sum(r['unchecked_semantics_match'] for r in pt)}/{len(pt)}",
        "phenotype_claims_exact": f"{sum(r['phenotype_exact'] for r in pt)}/{len(pt)}",
        "decisions_verified": f"{sum(d.status == 'verified' for d in g.decisions)}/{len(g.decisions)}",
        "transitions_verified": f"{sum(t.status == 'verified' for t in g.transitions)}/{len(g.transitions)}",
        "rejected": [
            i.id
            for k in ("variables", "decisions", "transitions", "procedures", "rules", "regimes")
            for i in getattr(g, k)
            if i.status == "rejected"
        ],
        "hypothesis": [
            i.id
            for k in ("variables", "decisions", "transitions", "procedures", "rules", "regimes")
            for i in getattr(g, k)
            if i.status == "hypothesis"
        ],
        "sites_not_in_mechanics": res["sites_not_in_mechanics"],
    }


def main() -> int:
    head_run, base_run, case, tree = (
        Path(sys.argv[1]),
        Path(sys.argv[2]),
        Path(sys.argv[3]),
        Path(sys.argv[4]),
    )
    prop_path = Path(sys.argv[5]) if len(sys.argv) > 5 else case / "proposals.json"
    prefix = sys.argv[6] if len(sys.argv) > 6 else ""
    # "frozen": the recorded 5f45eb2 substrate (+ the coverage ablation);
    # "repaired": mechanics.json written by the repaired DiffGenome, scored on every
    # observed site of the changed symbols listed in its own change artifact
    mode = sys.argv[7] if len(sys.argv) > 7 else "frozen"
    proposals = json.loads(prop_path.read_text())
    frozen = json.loads((head_run / "mechanics.json").read_text())["functions"]
    report: dict[str, Any] = {}
    required: list[str] | None = None
    if mode == "repaired":
        substrates = [("repaired", frozen)]
        artifact = json.loads((head_run / "diffgenome-change.json").read_text())
        required = list(artifact["change"]["symbols"])
    else:
        substrates = [("frozen", frozen), ("coverage", coverage_mechanics(frozen, tree))]
    for tag, fns in substrates:
        res = run(head_run, base_run, case, proposals, fns, tree, required)
        g = res.pop("genome")
        res["summary"] = summarize(res, g)
        report[tag] = res
        (case / f"{prefix}{tag}.genome.json").write_text(dumps(g))
        g.subject = {
            "repo": "baserow",
            "change": "#6069 import dependency via link row",
            "entry": "_import_table_fields",
        }
        (case / f"{prefix}{tag}.genome.md").write_text(render_markdown(g))
        print(f"== {prefix}{tag}: {json.dumps(res['summary'])}")
        for r in res["per_test"]:
            print(
                f"  {'W' if r['withheld'] else 'S'} {r['test'][:62]:62} match={r['match']!s:5} unchecked={r['unchecked_semantics_match']!s:5} "
                f"obs@sites={r['n_observed_at_sites']} ind={(r['indeterminate'] or '')[:70]} pheno={r['phenotype_exact']}"
            )
            if not r["unchecked_semantics_match"] and not r["unchecked_indeterminate"]:
                p, o = r["predicted_branches"], r["observed_branches"]
                i = next(
                    (k for k in range(min(len(p), len(o))) if p[k] != o[k]), min(len(p), len(o))
                )
                print(
                    f"      first divergence at {i}: pred {p[i : i + 3]} obs {o[i : i + 3]} (len pred {len(p)}, obs {len(o)})"
                )
        for d in g.decisions:
            print(f"    {d.id:28} {d.status:10} {d.status_reason[-150:]}")
        for t in g.transitions:
            print(f"    {t.id:28} {t.status:10} {t.status_reason[-120:]}")
    name = "evaluation.json" if mode == "frozen" else f"{mode}.evaluation.json"
    (case / f"{prefix}{name}").write_text(json.dumps(report, indent=1, default=str) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
