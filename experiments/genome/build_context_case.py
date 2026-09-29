# ruff: noqa: E501
"""Generic bundle for the stress-suite cases B and C (same protocol as Baserow v4).

Sections: instructions (the v4 schema: Outcome, boundary bindings, execution structure,
repeated regions with occurrence facts; no relations, derived order or iteration), required
sites, observed execution structure (shown executions only), mechanics of the vocabulary's
functions, chronological event logs of the shown tests, the change's diff, sources and tests.
Withheld traces never inform any section.

usage: build_context_case.py <case B|C> <head-run> <out-dir>
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from diffgenome.genome_state import Mechanics, Observations, change_sites
from diffgenome.model import CallNode, SubstitutionNode
from diffgenome.serialize import execution_from_json
from diffgenome.structure import build_skeleton, canonical, render

REPO = Path.home() / "sample_repos/simplebank"
V4 = Path(__file__).resolve().parents[2] / "docs/runs/genome-baserow-6069-v4/context-bundle.md"

CASES: dict[str, dict[str, Any]] = {
    "B": {
        "title": "simplebank #103 (upstream techschool/simplebank#103; fork sydes-examples/simplebank#5)",
        "base": "6e2679863e4c691db46ec14761a3b3e303e05ce1",
        "head": "2e2094e209a2e9432b53a0d142f52bc8ccce82c2",
        "summary": (
            '"add role-based access control (RBAC)". Users get a `role` (a new column, default '
            "`depositor`; constants `util.DepositorRole` and `util.BankerRole`). Token creation takes the "
            "role and stores it in the token payload. The gRPC `authorizeUser` now takes the accessible "
            "roles of the calling endpoint and rejects a verified token whose role is not among them "
            "(`hasPermission`). `UpdateUser` passes both roles and lets a banker update any user, while "
            "any other role may update only itself."
        ),
        "vocab": [
            "token.PasetoMaker.CreateToken",
            "token.NewPayload",
            "gapi.Server.UpdateUser",
            "gapi.Server.authorizeUser",
            "token.PasetoMaker.VerifyToken",
            "token.Payload.Valid",
            "gapi.hasPermission",
            "gapi.validateUpdateUserRequest",
            "db/sqlc.Queries.UpdateUser",
            "gapi.convertUser",
        ],
        "entries": ["gapi.Server.UpdateUser"],
        "tests_prefix": "TestUpdateUserAPI/",
        "holdout": ["BankerCanUpdateUserInfo", "ExpiredToken"],
        "diff_paths": ["gapi", "token", "util", "api"],
        "sources": [
            "gapi/authorization.go",
            "gapi/rpc_update_user.go",
            "token/payload.go",
            "token/paseto_maker.go",
            "util/role.go",
        ],
        "test_sources": ["gapi/rpc_update_user_test.go", "gapi/main_test.go"],
    },
}

HEAD_TMPL = """\
# Task: propose the semantic layer of a Behavioral Genome for a real code change

You are an abstraction engine. The change is {title} (base {base8} → head {head8}):
{summary}

Deterministic machinery has ALREADY established the mechanics below. Do not re-derive them
and do not contradict them:
- decision sites (`if`) with stable ids `br:...` (per revision), source predicate, operand
  origins (local def-use), and the (site, outcome) pairs required to reach them;
- for every call and store: which (site, outcome) pairs it requires;
- for the tests shown (at head): the ordered event log of the relevant calls, each call's
  argument shapes with value digests (`#abcd12`: equal digests = equal values; contents are
  not recorded), results, the observed outcome (T/F) of every decision site in those calls,
  and every call's observed EXIT (returned / returned-error / raised / panic). The digest
  `#5da3a4` is Go's `nil`.

Your job is MEANING: name the variables that matter, abstract the predicates, and give compact
rules that GENERATE the observed behavior of the head (which calls happen, which decisions
go which way, how each entry call exits). A machine checks everything you cite and assigns
status; you assign none. Tests are withheld (traces not shown; source shown). Write scenarios
for them; they will be predicted and compared with what executed.

"""


def instructions(cfg: dict[str, Any]) -> str:
    v4 = V4.read_text()
    fmt = v4[v4.index("## The genome format") : v4.index("## Required sites")]
    fmt = fmt.replace(
        '"phenotype": {"base": "<exit of import_tables_serialized>", "head": "<exit>", "why": "<one sentence from your rules>"}',
        '"phenotype": {"head": "<exit of the entry call>", "why": "<one sentence from your rules>"}',
    )
    fmt = fmt.replace(
        "- `phenotype` is your claim about the entry's exit at base and head; scored separately.",
        "- `phenotype` is your claim about the entry call's exit; scored separately.",
    )
    fmt = fmt.replace("param:serialized_field", "param:req")
    head = HEAD_TMPL.format(
        title=cfg["title"], base8=cfg["base"][:8], head8=cfg["head"][:8], summary=cfg["summary"]
    )
    return head + fmt


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout


def short(sym: str) -> str:
    return sym.split(":", 1)[-1]


def event_log(ex: Any, vocab: list[str], preds: dict[str, str]) -> list[str]:
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

    events = [(n.id, 1, n) for n in nodes if name.get(n.id)] + [
        (b.seq, 0, b) for b in ex.branches if name.get(b.node)
    ]
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
                f"{'  ' * depth(o.id)}call {short(name[o.id])}({args}) [{getattr(o, 'outcome', '?')}]{res}{tag}"
            )
    return out


def main() -> int:
    case, run, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    cfg = CASES[case]
    out.mkdir(parents=True, exist_ok=True)
    vocab = [f"go:{v}" if not v.startswith("go:") else v for v in cfg["vocab"]]
    runs = {
        e.stimulus_ref: e
        for e in (
            execution_from_json(f.read_text())
            for f in sorted((run / "traces-existing").glob("*.json"))
        )
    }
    tests = {k.split("/", 1)[1]: v for k, v in runs.items() if k.startswith(cfg["tests_prefix"])}
    shown = sorted(t for t in tests if t not in cfg["holdout"])
    mfns = json.loads((run / "mechanics.json").read_text())["functions"]
    mech = Mechanics(mfns)
    preds = {s: rec["pred"] for s, rec in mech.sites.items()}
    changed = json.loads((run / "diffgenome-change.json").read_text())["change"]["symbols"]
    required = change_sites(mech, Observations([tests[t] for t in shown]), changed)
    sk = build_skeleton([tests[t] for t in shown], vocab)
    parts = [instructions(cfg)]
    seen_sites = {b.site for t in shown for b in tests[t].branches}
    parts.append(
        "## Required sites (head ids)\n\nEvery OBSERVED evaluation of these sites is scored, in every test. Sites the "
        "shown tests never evaluated are marked; a withheld test that evaluates one needs a decision for it.\n\n"
        + "\n".join(
            f"- {s} {mech.sites[s]['symbol']} line {mech.sites[s]['line']}: `{mech.sites[s]['pred']}`"
            + ("" if s in seen_sites else "   (not evaluated in the shown tests)")
            for s in sorted(
                required, key=lambda s: (mech.sites[s]["symbol"], mech.sites[s]["line"])
            )
            if s in mech.sites
        )
        + "\n"
    )
    parts.append(
        "## Observed execution structure (deterministic; shown executions only)\n\n```\n"
        + render(sk)
        + "\n```\n"
    )
    lines = []
    for f in mfns:
        if canonical(vocab, f["symbol"]) is None:
            continue
        lines.append(f"### {short(f['symbol'])}  ({f['file']})")
        for s in f["sites"]:
            ops = "; ".join(f"{o['path']} ← {', '.join(o['origins'])}" for o in s["operands"])
            req = (
                " & ".join(
                    f"{r[0]}={'T' if r[1] else 'F'}" if r[1] is not None else r[0]
                    for r in s["requires"]
                )
                or "—"
            )
            lines.append(
                f"- site {s['site']} line {s['line']}: `{s['pred']}` | operands: {ops} | requires: {req} | then exits: {s['then_exits']}, else exits: {s['else_exits']}"
            )
        for c in f["calls"]:
            req = (
                " & ".join(
                    f"{r[0]}={'T' if r[1] else 'F'}" if r[1] is not None else r[0]
                    for r in c["requires"]
                )
                or "—"
            )
            lines.append(f"- call `{c['callee'][:80]}` line {c['line']} requires: {req}")
        lines.append("")
    parts.append("## Mechanics at HEAD (deterministic, intra-procedural)\n\n" + "\n".join(lines))
    logs = []
    for t in shown:
        ex = tests[t]
        entry_exits = [
            f"{short(n.symbol)} {n.outcome}"
            for n in ex.nodes
            if isinstance(n, CallNode) and any(n.symbol.endswith(e) for e in cfg["entries"])
        ]
        logs.append(
            f"### {t}  test: {ex.outcome}  exits: {'; '.join(entry_exits)}\n"
            + "\n".join(event_log(ex, vocab, preds))
        )
    parts.append(
        "## Observed event logs (shown tests, at head)\n\nCalls of the listed functions in chronological order, indented by depth among them "
        "(everything else is looked through), with argument shapes and value digests, results, exits, and the observed outcome of "
        "every decision site evaluated in those calls.\n\n```\n"
        + "\n\n".join(logs)
        + "\n```\n\nWithheld (observed, not shown): "
        + ", ".join(cfg["holdout"])
        + "\n"
    )
    diff = git(
        "diff",
        f"{cfg['base']}..{cfg['head']}",
        "--",
        *[f"{p}/*.go" for p in cfg["diff_paths"]],
        ":!*_test.go",
    )
    parts.append(
        f"## The change (git diff {cfg['base'][:8]}..{cfg['head'][:8]}, non-test Go sources in {', '.join(cfg['diff_paths'])})\n\n```diff\n{diff}```\n"
    )
    for src in cfg["sources"] + cfg["test_sources"]:
        text = git("show", f"{cfg['head']}:{src}").splitlines()
        parts.append(
            f"## Source at HEAD: {src}\n\n```go\n"
            + "\n".join(f"{i:4d}  {ln}" for i, ln in enumerate(text, 1))
            + "\n```\n"
        )
    bundle = "\n".join(parts)
    (out / "context-bundle.md").write_text(bundle)
    digest = hashlib.sha256(bundle.encode()).hexdigest()[:16]
    (out / "context-bundle.sha").write_text(digest + "\n")
    (out / "holdout.json").write_text(
        json.dumps({"holdout": cfg["holdout"], "shown": shown, "not_scored": []}, indent=1) + "\n"
    )
    print(
        f"case {case} bundle {len(bundle)} chars, {bundle.count(chr(10))} lines, sha {digest}; shown {len(shown)}, withheld {len(cfg['holdout'])}, required sites {len(required)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
