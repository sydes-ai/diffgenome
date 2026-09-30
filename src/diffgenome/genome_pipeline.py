# ruff: noqa: E501
"""`diffgenome genome`: the Behavioral Genome of a change, as a product step.

Input is the output directory of `diffgenome change` (its artifact, mechanics and existing-test
traces). Four steps, each generic (no framework knowledge):

1. bundle: the proposer's instructions (the v5 schema), required sites, the observed execution
   structure, mechanics of the vocabulary's functions, the tests' event logs, the change's
   diff and the sources;
2. propose: a model writes the semantic layer (recorded proposals, or OpenAI live);
3. establish: the checker assigns statuses from ALL the traces, and every scenario is predicted
   and compared with what executed (consistency, not a held-out score);
4. summarize: only checked claims (verified, or supported and never contradicted) go to the
   artifact's `genome` section. Hypotheses and rejected items are counted, never exported.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path
from typing import Any

from diffgenome.genome import (
    SUPPORTED,
    VERIFIED,
    Genome,
    Item,
    Substrate,
    bindings_of,
    dumps,
    genome_from_proposals,
    render_markdown,
)
from diffgenome.genome_prompt import FORMAT, HEAD
from diffgenome.genome_state import (
    Mechanics,
    Observations,
    StateSubstrate,
    change_sites,
    compare_sequence,
    establish_state,
    genome_vocabulary,
    predict_sequence,
)
from diffgenome.model import CallNode, Execution, SubstitutionNode
from diffgenome.serialize import execution_from_json
from diffgenome.structure import build_skeleton, canonical, render

SUMMARY_FORMAT = "diffgenome-genome-summary/1"
MAX_VOCAB = 24
MAX_TESTS = 40
MAX_LOG_LINES = 120
MAX_EXTRA_FILES = 8
MAX_FILE_LINES = 400
WINDOW = 12
_SOURCE_EXT = (".go", ".py", ".js", ".ts", ".rs")


def _is_test_path(f: str) -> bool:
    name = f.rsplit("/", 1)[-1]
    return (
        name.endswith(("_test.go", ".test.ts", ".test.js"))
        or name.startswith("test_")
        or "/tests/" in f
    )


def _short(sym: str) -> str:
    return sym.split(":", 1)[-1]


class Run:
    """A `diffgenome change` output directory."""

    def __init__(self, run: Path) -> None:
        self.dir = run
        self.artifact: dict[str, Any] = json.loads((run / "diffgenome-change.json").read_text())
        self.mech_fns: list[dict[str, Any]] = json.loads((run / "mechanics.json").read_text())[
            "functions"
        ]
        self.mech = Mechanics(self.mech_fns)
        self.executions: dict[str, Execution] = {
            e.stimulus_ref: e
            for e in (
                execution_from_json(f.read_text())
                for f in sorted((run / "traces-existing").glob("*.json"))
            )
        }
        ch = self.artifact["change"]
        self.changed: list[str] = list(ch["symbols"])
        # executed = seen in a trace (the artifact's list may come from another run)
        seen = {
            n.symbol for e in self.executions.values() for n in e.nodes if isinstance(n, CallNode)
        }
        self.executed_changed = [s for s in self.changed if s in seen]
        repo = self.artifact["repository"]
        self.root = Path(repo["root"])
        self.revision: str = repo.get("revision") or "HEAD"
        self.runtime: str = repo.get("runtime", "")
        self.spec: str = ch.get("spec", "")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.root, capture_output=True, text=True, check=False
        ).stdout


def vocabulary(run: Run) -> list[str]:
    """Changed functions that executed, functions nested in them, and their direct callers
    and callees among the repository's functions (by observed call nesting)."""
    mech_syms = {f["symbol"] for f in run.mech_fns}
    changed = set(run.executed_changed)
    vocab = [s for s in run.executed_changed if s in mech_syms]
    nested: set[str] = set()
    near: dict[str, int] = {}
    for ex in run.executions.values():
        by_id = {n.id: n for n in ex.nodes}
        for n in ex.nodes:
            if not isinstance(n, CallNode):
                continue
            base = n.symbol.split(".<anon>")[0]
            if base in changed and n.symbol not in changed:
                nested.add(n.symbol)
            parent = by_id.get(n.parent) if n.parent is not None else None
            psym: str = getattr(parent, "symbol", "") or ""
            if n.symbol in changed and psym in mech_syms and psym not in changed:
                near[psym] = near.get(psym, 0) + 1
            if psym in changed and n.symbol in mech_syms and n.symbol not in changed:
                near[n.symbol] = near.get(n.symbol, 0) + 1
    vocab += sorted(nested - set(vocab))
    vocab += [s for s, _ in sorted(near.items(), key=lambda kv: (-kv[1], kv[0])) if s not in vocab]
    return vocab[:MAX_VOCAB]


def relevant_tests(run: Run) -> dict[str, Execution]:
    """Executions that call a changed function (or a function nested in one)."""
    changed = set(run.executed_changed)
    return {
        ref: ex
        for ref, ex in sorted(run.executions.items())
        if any(
            isinstance(n, CallNode)
            and (n.symbol in changed or n.symbol.split(".<anon>")[0] in changed)
            for n in ex.nodes
        )
    }


def shown_tests(tests: dict[str, Execution], required: set[str]) -> dict[str, Execution]:
    """At most MAX_TESTS for the bundle: one test per distinct observed behavior (the
    outcome vector of the required sites and the changed calls' exits) first, then the rest."""

    def signature(ex: Execution) -> tuple[Any, ...]:
        return (
            tuple((b.site, b.outcome) for b in ex.branches if b.site in required),
            tuple(sorted({n.outcome for n in ex.nodes if isinstance(n, CallNode)})),
        )

    first: dict[tuple[Any, ...], str] = {}
    for ref, ex in tests.items():
        first.setdefault(signature(ex), ref)
    picked = list(first.values())
    picked += [r for r in tests if r not in picked]
    keep = set(picked[:MAX_TESTS])
    return {r: ex for r, ex in tests.items() if r in keep}


def event_log(ex: Execution, vocab: list[str], preds: dict[str, str]) -> list[str]:
    nodes = ex.nodes
    name = {
        n.id: canonical(vocab, getattr(n, "symbol", None) or getattr(n, "claimed_target", "") or "")
        for n in nodes
    }

    def depth(i: int) -> int:
        d, p = 0, nodes[i].parent
        while p is not None:
            d += name.get(p) is not None
            p = nodes[p].parent
        return d

    events: list[tuple[int, int, Any]] = [(n.id, 1, n) for n in nodes if name.get(n.id)]
    events += [(b.seq, 0, b) for b in ex.branches if name.get(b.node)]
    out = []
    for _, kind, o in sorted(events, key=lambda e: (e[0], e[1])):
        if kind == 0:
            out.append(
                f"{'  ' * (depth(o.node) + 1)}branch {o.site} `{preds.get(o.site, '?')[:70]}` = {'T' if o.outcome else 'F'}"
            )
        else:
            args = ", ".join(
                f"{a}={t}" + (f"#{d[:6]}" if d else "") for a, t, d in getattr(o, "args", ())
            )
            res = f" -> #{o.result[:6]}" if getattr(o, "result", "") else ""
            tag = " (stand-in, mocked)" if isinstance(o, SubstitutionNode) else ""
            out.append(
                f"{'  ' * depth(o.id)}call {_short(name[o.id] or '')}({args}) [{getattr(o, 'outcome', '?')}]{res}{tag}"
            )
    if len(out) > MAX_LOG_LINES:
        out = [*out[:MAX_LOG_LINES], f"... ({len(out) - MAX_LOG_LINES} more events)"]
    return out


def build_bundle(run: Run) -> tuple[str, list[str], dict[str, Execution]]:
    vocab = vocabulary(run)
    everything = relevant_tests(run)
    required = change_sites(run.mech, Observations(list(everything.values())), run.changed)
    tests = shown_tests(everything, required)
    sk = build_skeleton(list(tests.values()), vocab)
    preds = {s: rec["pred"] for s, rec in run.mech.sites.items()}
    go = run.runtime.startswith("go")
    null_note = "The digest `#5da3a4` is Go's `nil`." if go else ""
    parts = [
        HEAD.format(
            spec=run.spec or "(unspecified)",
            repo=run.root.name,
            runtime=run.runtime,
            symbols=", ".join(_short(s) for s in run.changed),
            null_note=null_note,
        )
        + FORMAT.replace('"lang": "go"', f'"lang": "{"go" if go else "python"}"')
    ]
    seen = {b.site for ex in tests.values() for b in ex.branches}
    parts.append(
        "## Required sites\n\nEvery OBSERVED evaluation of these sites is scored, in every test.\n\n"
        + "\n".join(
            f"- {s} {run.mech.sites[s]['symbol']} line {run.mech.sites[s]['line']}: `{run.mech.sites[s]['pred']}`"
            + ("" if s in seen else "   (not evaluated by any test)")
            for s in sorted(
                (s for s in required if s in run.mech.sites),
                key=lambda s: (run.mech.sites[s]["symbol"], run.mech.sites[s]["line"]),
            )
        )
        + "\n"
    )
    runtime_only: dict[str, set[str]] = {}
    for ex in tests.values():
        for b in ex.branches:
            if b.site in required and b.site not in run.mech.sites:
                runtime_only.setdefault(b.site, set()).add(getattr(ex.nodes[b.node], "symbol", "?"))
    if runtime_only:
        parts.append(
            "Runtime-only required sites (observed; no static facts, e.g. in closures): "
            + "; ".join(f"{s} in {', '.join(sorted(v))}" for s, v in sorted(runtime_only.items()))
            + "\n"
        )
    parts.append(
        "## Observed execution structure (deterministic)\n\n```\n" + render(sk) + "\n```\n"
    )
    lines = []
    files: list[str] = []
    for f in run.mech_fns:
        if canonical(vocab, f["symbol"]) is None:
            continue
        if f["file"] not in files:
            files.append(f["file"])
        lines.append(f"### {_short(f['symbol'])}  ({f['file']})")
        for s in f["sites"]:
            ops = "; ".join(f"{o['path']} ← {', '.join(o['origins'])}" for o in s["operands"])
            req = " & ".join(
                f"{r[0]}={'T' if r[1] else 'F'}" if r[1] is not None else r[0]
                for r in s["requires"]
            )
            lines.append(
                f"- site {s['site']} line {s['line']}: `{s['pred']}` | operands: {ops} | requires: {req or '—'} | then exits: {s['then_exits']}, else exits: {s['else_exits']}"
            )
        for c in f["calls"]:
            req = " & ".join(
                f"{r[0]}={'T' if r[1] else 'F'}" if r[1] is not None else r[0]
                for r in c["requires"]
            )
            lines.append(f"- call `{c['callee'][:80]}` line {c['line']} requires: {req or '—'}")
        lines.append("")
    parts.append("## Mechanics (deterministic, intra-procedural)\n\n" + "\n".join(lines))
    logs = []
    entries = set(run.executed_changed)
    for ref, ex in tests.items():
        exits = [
            f"{_short(n.symbol)} {n.outcome}"
            for n in ex.nodes
            if isinstance(n, CallNode) and n.symbol in entries
        ][:6]
        logs.append(
            f"### {ref}  test: {ex.outcome}  exits: {'; '.join(exits)}\n"
            + "\n".join(event_log(ex, vocab, preds))
        )
    parts.append(
        "## Observed event logs\n\nCalls of the listed functions in chronological order, indented by depth among them, "
        "with argument shapes and value digests, results, exits, and the observed outcome of every decision site "
        "evaluated in those calls.\n\n```\n" + "\n\n".join(logs) + "\n```\n"
    )
    rng = run.spec.split()[-1] if run.spec.startswith("git diff") else ""
    if rng:
        # the change's non-test files beside the vocabulary's (constants and literals live there)
        touched = [
            f
            for f in run.git("diff", "--name-only", rng).split()
            if f not in files and not _is_test_path(f) and f.endswith(_SOURCE_EXT)
        ]
        # smallest first (constants files are small), generated code skipped
        heads = {f: run.git("show", f"{run.revision}:{f}") for f in touched}
        touched = sorted(
            (f for f in touched if heads[f] and "Code generated" not in heads[f][:400]),
            key=lambda f: len(heads[f]),
        )
        files += touched[:MAX_EXTRA_FILES]
        diff = run.git("diff", "-U25", rng, "--", *files)
        parts.append(f"## The change ({run.spec}, the files shown below)\n\n```diff\n{diff}```\n")
    test_files = sorted({f for f in (_test_file(run, r) for r in tests) if f})
    marks: dict[str, set[int]] = {}
    for f in run.mech_fns:
        if canonical(vocab, f["symbol"]) is not None:
            marks.setdefault(f["file"], set()).update(
                x["line"] for x in (*f["sites"], *f["calls"]) if x.get("line")
            )
    test_names = {r.split("::")[-1].split("/")[0] for r in tests}
    for src in files + test_files:
        text = run.git("show", f"{run.revision}:{src}").splitlines()
        if not text:
            continue
        keep = _windows(text, marks.get(src, set()), test_names)
        body, prev = [], 0
        for i in keep:
            if i != prev + 1:
                body.append("   ...")
            body.append(f"{i:4d}  {text[i - 1]}")
            prev = i
        parts.append(f"## Source: {src}\n\n```\n" + "\n".join(body) + "\n```\n")
    if len(tests) < len(everything):
        parts.append(
            f"({len(everything) - len(tests)} further tests executed the change and are checked too; not listed.)\n"
        )
    return "\n".join(parts), vocab, everything


def _windows(text: list[str], marks: set[int], test_names: set[str]) -> list[int]:
    """All lines of a small file; of a large one, windows around the marked lines and the
    bodies of the listed tests."""
    n = len(text)
    if n <= MAX_FILE_LINES:
        return list(range(1, n + 1))
    keep: set[int] = set()
    for m in marks:
        keep.update(range(max(1, m - WINDOW), min(n, m + WINDOW) + 1))
    for i, ln in enumerate(text, 1):
        s = ln.lstrip()
        if s.startswith(("def ", "func ", "async def ")) and any(f"{t}(" in s for t in test_names):
            ind = len(ln) - len(s)
            j = i + 1
            while j <= n and (
                not text[j - 1].strip()
                or len(text[j - 1]) - len(text[j - 1].lstrip()) > ind
                or text[j - 1].lstrip().startswith((")", "}"))
            ):
                j += 1
            keep.update(range(i, min(n, j) + 1))
    return sorted(keep)


def _test_file(run: Run, ref: str) -> str | None:
    for e in run.artifact.get("executions") or []:
        if e.get("id") == ref:
            return str(e["file"]) if e.get("file") else None
    return None


def propose(bundle: str, writer: str) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """`recorded:<proposals.json>` replays a proposal; `openai[:<model>]` asks OpenAI."""
    t0 = time.monotonic()
    if writer.startswith("recorded:"):
        path = Path(writer.split(":", 1)[1])
        meta = (
            json.loads(path.with_suffix(".meta.json").read_text())
            if path.with_suffix(".meta.json").exists()
            else {}
        )
        return (
            json.loads(path.read_text()),
            str(meta.get("model", f"recorded:{path.name}")),
            {"seconds": 0.0},
        )
    if writer.startswith("openai"):
        from diffgenome.llm import OpenAIProbeWriter

        model = writer.split(":", 1)[1] if ":" in writer else None
        w = OpenAIProbeWriter(model=model, timeout=900)
        data = w._post(
            "/chat/completions",
            {
                "model": w.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You write Behavioral Genome proposals. Output one JSON object only.",
                    },
                    {"role": "user", "content": bundle},
                ],
                "response_format": {"type": "json_object"},
            },
        )
        choices = data.get("choices")
        assert isinstance(choices, list) and choices
        usage = data.get("usage") or {}
        return (
            json.loads(choices[0]["message"]["content"]),
            w.model,
            {"seconds": round(time.monotonic() - t0, 1), "usage": usage},
        )
    raise ValueError(f"unknown writer {writer!r}")


def _resolve(key: str, refs: list[str]) -> str | None:
    """A scenario key names a test by its full id, or by a unique suffix after '/'."""
    if key in refs:
        return key
    hits = [r for r in refs if r.endswith(("/" + key, "::" + key))]
    return hits[0] if len(hits) == 1 else None


def changed_lines(run: Any) -> dict[str, set[int]]:
    """Head-side line numbers the change added or modified, per file."""
    rng = run.spec.split()[-1] if getattr(run, "spec", "").startswith("git diff") else ""
    out: dict[str, set[int]] = {}
    if not rng:
        return out
    cur = ""
    for ln in run.git("diff", "-U0", rng).splitlines():
        if ln.startswith("+++ "):
            cur = ln[6:] if ln.startswith("+++ b/") else ""
        elif ln.startswith("@@") and cur:
            new = ln.split("+", 1)[1].split(" ", 1)[0]
            start, _, count = new.partition(",")
            n = int(count) if count else 1
            out.setdefault(cur, set()).update(range(int(start), int(start) + n))
    return out


def _site_changed(run: Any, site: str | None, touched: dict[str, set[int]]) -> bool:
    s = run.mech.sites.get(site or "")
    return bool(s) and s["line"] in touched.get(s.get("file", ""), set())


def eligible(it: Item) -> bool:
    return it.status == VERIFIED or (it.status == SUPPORTED and not it.contradicted)


def establish(
    run: Run, proposals: dict[str, Any], model: str, tests: dict[str, Execution], tree: Path
) -> tuple[Genome, dict[str, Any]]:
    refs = list(tests)
    scen_in = proposals.get("scenarios") or {}
    scenarios = {r: s for k, s in scen_in.items() if (r := _resolve(k, refs))}
    obs = Observations(list(tests.values()))
    g = genome_from_proposals(proposals, {"repo": run.root.name, "change": run.spec}, model)
    agree: dict[str, list[tuple[str, bool]]] = {}
    for ref, sc in scenarios.items():
        ob = obs.get(ref)
        assert ob is not None
        pred = predict_sequence(g, sc, min_status="hypothesis")
        for d in g.decisions:
            if not d.site:
                continue
            p = [e[2] for e in pred.events if e[0] == "branch" and e[1] == d.site]
            o = [b.outcome for b in ob.branches if b.site == d.site]
            if (not p and not o) or (pred.indeterminate and len(p) < len(o)):
                continue
            agree.setdefault(d.id, []).append((ref, p == o))
    sub = StateSubstrate(Substrate([], set(), tree, set()), run.mech, obs)
    establish_state(g, sub, agreement_seq=agree, scenarios=scenarios)
    sk = build_skeleton(list(tests.values()), genome_vocabulary(g))
    required = change_sites(run.mech, obs, run.changed)
    sites = {d.site for d in g.decisions if d.site}
    per_test: list[dict[str, Any]] = []
    for ref, sc in sorted(scenarios.items()):
        ob = obs.get(ref)
        assert ob is not None
        cmp = compare_sequence(g, predict_sequence(g, sc), ob, sites, required, sk, sc)
        per_test.append(
            {"test": ref, "match": bool(cmp["match"]), "indeterminate": cmp["indeterminate"] or ""}
        )
    ev = {
        "tests": len(tests),
        "scenarios": len(scenarios),
        "unresolved_scenarios": sorted(k for k in scen_in if not _resolve(k, refs)),
        "consistent": sum(r["match"] for r in per_test),
        "indeterminate": sum(1 for r in per_test if r["indeterminate"]),
        "contradicted": sum(1 for r in per_test if not r["match"] and not r["indeterminate"]),
        "per_test": per_test,
        "site_agreement": {k: [ok for _, ok in v] for k, v in agree.items()},
    }
    return g, ev


def summary(
    run: Run,
    g: Genome,
    ev: dict[str, Any],
    model: str,
    proposals: dict[str, Any],
    bundle_digest: str,
    cost: dict[str, Any],
) -> dict[str, Any]:
    """The artifact's `genome` section: checked claims only."""

    def site_ref(site: str | None) -> dict[str, Any]:
        s = run.mech.sites.get(site or "")
        return {"file": s.get("file"), "line": s["line"], "source": s["pred"]} if s else {}

    def outcome(b: Any) -> str | None:
        o = b.outcome or {}
        return f"{_short(o.get('entity', ''))} {o['is']}" if o.get("is") else None

    agreement = ev.get("site_agreement") or {}
    touched = changed_lines(run)
    rules = []
    for d in g.decisions:
        # a supported rule is shown only when its predicted outcomes matched the observed
        # ones in every test that exercised it (a checked meaning, not only a cited source)
        seen = agreement.get(d.id) or []
        if not eligible(d) or (d.status != VERIFIED and not (seen and all(seen))):
            continue
        rules.append(
            {
                "id": d.id,
                "status": d.status,
                "entity": _short(d.entity),
                "site": d.site,
                **site_ref(d.site),
                "meaning": d.predicate,
                "inputs": d.inputs,
                "when_true": d.true_branch.effect or None,
                "when_false": d.false_branch.effect or None,
                "outcome_true": outcome(d.true_branch),
                "outcome_false": outcome(d.false_branch),
                "basis": d.status_reason[-200:],
                "agreeing_tests": sum(seen),
                "at_changed_line": _site_changed(run, d.site, touched),
            }
        )
    rules.sort(key=lambda r: (not r["at_changed_line"], r["status"] != VERIFIED))
    identities = []
    literals = []
    for v in g.variables:
        bs = bindings_of(v)
        ids = [b for b in bs if b.get("kind") == "identity"]
        if len(ids) >= 2 and eligible(v):
            identities.append(
                {
                    "name": v.name,
                    "status": v.status,
                    "same_value_at": [
                        f"{_short(b['at']['entity'])} {b['at']['point']}" for b in ids
                    ],
                    "basis": v.status_reason[-200:],
                }
            )
        for b in bs:
            if b.get("kind") == "equals_literal" and b.get("_literal_ok"):
                lit = b.get("literal") or {}
                src = lit.get("source") or {}
                literals.append(
                    {
                        "name": v.name,
                        "at": f"{_short(b['at']['entity'])} {b['at']['point']}",
                        "equals": lit.get("value"),
                        "written_at": f"{src.get('file')}:{src.get('line')}",
                    }
                )
    transitions = [
        {"id": t.id, "entity": _short(t.entity), "when": t.when, "sets": t.sets, "status": t.status}
        for t in g.transitions
        if t.status == VERIFIED
    ]
    kinds = ("variables", "decisions", "transitions", "procedures", "regions", "rules", "regimes")
    counts = {
        st: sum(1 for k in kinds for i in getattr(g, k) if i.status == st)
        for st in ("verified", "supported", "hypothesis", "rejected")
    }
    counts["contradicted_not_exported"] = sum(
        1 for k in kinds for i in getattr(g, k) if i.contradicted and i.status != VERIFIED
    )
    return {
        "format": SUMMARY_FORMAT,
        "proposed_by": model,
        "bundle_digest": bundle_digest,
        "established_from": f"{ev['tests']} executions of existing tests",
        # three different counts; a consumer must not report one as another
        "accounting": {
            "relevant_executions_checked": ev["tests"],
            "scenario_predictions_checked": ev["scenarios"],
            "executions_listed_in_artifact": len(
                getattr(run, "artifact", {}).get("executions") or []
            ),
        },
        "consistency": {
            k: ev[k] for k in ("scenarios", "consistent", "indeterminate", "contradicted")
        },
        "decision_rules": rules,
        "identities": identities,
        "literals": literals,
        "transitions": transitions,
        "statuses": counts,
        "unknowns": [u for u in (proposals.get("unknowns") or []) if isinstance(u, dict)][:12],
        "cost": cost,
        "note": "Only verified claims, and supported claims no execution contradicted, are listed. Meanings are the model's words; statuses come from the traces.",
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="diffgenome genome")
    ap.add_argument(
        "--run", required=True, type=Path, help="output directory of `diffgenome change`"
    )
    ap.add_argument(
        "--tree",
        type=Path,
        default=None,
        help="source tree at head (default: the artifact's repository root)",
    )
    ap.add_argument(
        "--writer",
        default="bundle-only",
        help="bundle-only | recorded:<proposals.json> | openai[:<model>]",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="directory for the bundle, proposals, genome and evaluation (default: <run>/genome)",
    )
    ap.add_argument(
        "--attach",
        action="store_true",
        help="write the summary into <run>/diffgenome-change.json as `genome`",
    )
    args = ap.parse_args(argv)
    run = Run(args.run)
    out = args.out or args.run / "genome"
    out.mkdir(parents=True, exist_ok=True)
    bundle, vocab, tests = build_bundle(run)
    digest = hashlib.sha256(bundle.encode()).hexdigest()[:16]
    (out / "context-bundle.md").write_text(bundle)
    print(
        f"bundle {digest}: {len(vocab)} functions, {len(tests)} tests, {len(bundle) // 1024} KiB -> {out / 'context-bundle.md'}"
    )
    if args.writer == "bundle-only":
        return 0
    proposals, model, cost = propose(bundle, args.writer)
    (out / "proposals.json").write_text(json.dumps(proposals, indent=1) + "\n")
    g, ev = establish(run, proposals, model, tests, args.tree or run.root)
    s = summary(run, g, ev, model, proposals, digest, cost)
    (out / "genome.json").write_text(dumps(g))
    (out / "genome.md").write_text(render_markdown(g))
    (out / "evaluation.json").write_text(json.dumps(ev, indent=1) + "\n")
    (out / "genome-summary.json").write_text(json.dumps(s, indent=1) + "\n")
    print(json.dumps({k: s[k] for k in ("consistency", "statuses")}))
    print(
        f"exported: {len(s['decision_rules'])} decision rules, {len(s['identities'])} identities, {len(s['literals'])} literals, {len(s['transitions'])} transitions"
    )
    if args.attach:
        art_path = args.run / "diffgenome-change.json"
        art = json.loads(art_path.read_text())
        art["genome"] = s
        art_path.write_text(json.dumps(art, indent=1) + "\n")
        print(f"attached to {art_path}")
    return 0
