# ruff: noqa: E501  (the verbatim model prompt and report lines)
"""Build the bounded context bundle the model sees, deterministically.

usage: build_context.py <diffgenome-run-dir> <source-root> <out-dir>

Contents (and nothing else): the change, the change-centred behavioral map, the observed
execution paths under the entry (minus a declared holdout), decoded return values and
outcomes, cheap static decision sites, the source of the changed symbols and their direct
callees, and the test source. The holdout's observed paths are withheld so that the
generative check predicts paths the model never saw.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from diffgenome.compose import build_corpus
from diffgenome.genome import execution_paths, static_decision_sites
from diffgenome.serialize import execution_from_json

ENTRY = "go:api.Server.createTransfer"
SOURCES = [
    "api/transfer.go",
    "api/validator.go",
    "util/currency.go",
    "api/server.go",
    "api/middleware.go",
    "db/sqlc/store.go",
    "db/sqlc/tx_transfer.go",
    "api/transfer_test.go",
]
DECISION_FILES = ["api/transfer.go", "api/validator.go", "util/currency.go"]
# Withheld from the model; predicted afterwards and compared with what executed.
HOLDOUT = [
    "TestTransferAPI/InsufficientBalance",
    "TestTransferAPI/TransferTxError",
    "TestTransferAPI/ToAccountCurrencyMismatch",
    "TestTransferAPI/UnauthorizedUser",
]

INSTRUCTIONS = """\
# Task: propose the semantic layer of a Behavioral Genome

You are an abstraction engine. You receive evidence already collected from a Go service
(simplebank, change 5b03c1d: "Reject transfers exceeding source account balance"): the
source of the changed code and its direct callees, the tests, a behavioral map, and the
observed execution paths of most tests. Propose a compact, *generative* description of the
behavior of `Server.createTransfer`: which inputs and state feed which decisions, what each
branch does, and which few rules generate the observed paths. Do not describe the call
graph again; describe why paths differ.

Rules you must follow:
- Use only the evidence below. Do not assume behavior you cannot point to.
- Every item must cite evidence refs. A machine will check each ref and assign status
  (hypothesis / supported / verified / rejected). You do not assign status.
- Evidence ref kinds (JSON):
  {"kind": "source", "file": "api/transfer.go", "line": 83, "text": "<exact text on that line>"}
  {"kind": "execution", "test": "TestTransferAPI/OK", "calls": ["checkSufficientBalance", "TransferTx"],
   "absent": ["errorResponse"], "returns": {"checkSufficientBalance": "true"}}
     (calls: must occur in this order in that execution's path; absent: must not occur;
      returns: decoded return value shown as =true/=false in the paths below)
  {"kind": "edge", "caller": "Server.createTransfer", "callee": "Server.checkSufficientBalance"}
- Use entity names as they appear in the execution paths (e.g. `checkSufficientBalance`,
  `validAccount`, `GetAccount`, `TransferTx`, `errorResponse`).
- Predicates are symbolic over variable names you define, using only `<`, `<=`, `>`, `>=`,
  `==`, `!=`, `!name`, `&&`, `||` (no parentheses). Variable names like `request.amount`,
  `from_account.balance`, `from_account.exists`, `auth.username`.
- Some tests' observed paths are deliberately withheld (listed below). Still give their
  input/state facts from the test source in `test_facts`; they will be used to test whether
  your genome predicts what actually executed.

Return ONLY one JSON object with these keys (arrays may be empty; explain in `unknowns`):

{
 "variables":        [{"id", "name", "origin": "request|state|derived|environment", "description", "evidence": [...]}],
 "data_dependencies":[{"id", "source": "<variable>", "sink": "<decision id or entity>", "transform": null|"...", "evidence": [...]}],
 "decisions":        [{"id", "entity", "inputs": ["<variable>"], "predicate": "...", "order": <int, position along createTransfer>,
                       "true_branch":  {"returns": null|"true"|"false", "calls": [...], "absent": [...], "stops": bool, "effect": "..."},
                       "false_branch": {...}, "evidence": [...]}],
 "effects":          [{"id", "kind": "response|persistence|external|none", "target", "condition": "<decision/rule ids>", "evidence": [...]}],
 "transitions":      [{"id", "state_before", "action", "state_after", "evidence": [...]}],
 "rules":            [{"id", "name", "inputs", "relevant_state", "condition", "consequences": [...], "decision": "<decision id>|null", "evidence": [...]}],
 "regimes":          [{"id", "name", "facts": {<variable>: value}, "members": ["<test id>"], "evidence": [...]}],
 "test_facts":       {"<test id>": {<variable>: value, ...}},   (for EVERY test listed, including withheld ones)
 "unknowns":         [{"what", "why"}]
}

Decision semantics for prediction: decisions are evaluated in `order`; the branch taken
contributes its `calls` (the entities reached) and `absent` (entities not reached); a branch
with `stops: true` ends createTransfer. A decision's predicate must be decidable from
`test_facts` values (booleans or numbers).
"""


def numbered(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(f"{i:4d}  {line}" for i, line in enumerate(lines, start=1))


def render_path(p) -> str:  # type: ignore[no-untyped-def]
    def fmt(steps) -> str:  # type: ignore[no-untyped-def]
        parts = []
        for s in steps:
            t = s.symbol.split(".")[-1]
            if s.symbol.startswith("stand-in:"):
                t += "(stand-in)"
            if s.result:
                t += f"={s.result}"
            if s.outcome != "returned":
                t += f"!{s.outcome.split(':')[0]}"
            if s.children:
                t += f"[{fmt(s.children)}]"
            parts.append(t)
        return ", ".join(parts)

    return f"{p.execution}  ({p.outcome})\n    createTransfer → {fmt(p.steps)}"


def main() -> int:
    run, source_root, out = (Path(a) for a in sys.argv[1:4])
    out.mkdir(parents=True, exist_ok=True)
    runs = [
        execution_from_json(f.read_text()) for f in sorted((run / "traces-existing").glob("*.json"))
    ]
    corpus = build_corpus(runs)
    paths = execution_paths(corpus, ENTRY, depth=2)
    shown = [p for p in paths if p.execution not in HOLDOUT]
    held = [p for p in paths if p.execution in HOLDOUT]
    parts = [INSTRUCTIONS]
    parts.append(
        "## The change\n\n```\n"
        + json.dumps(json.loads((run / "diffgenome-change.json").read_text())["change"], indent=1)
        + "\n```\n"
    )
    parts.append(
        "## Behavioral map around the change (evidence classes: → observed, ⇢ reconstructed, [gap])\n\n```\n"
        + (run / "behavioral-map.md").read_text()
        + "```\n"
    )
    parts.append(
        "## Observed execution paths under createTransfer\n\n"
        "Direct callees of `createTransfer` in call order, each with its own direct callees in "
        "[brackets]. `=true/=false` is a decoded return value; `!returned-error` is an error "
        "return; `(stand-in)` is a mocked call (the store is a gomock in every test). "
        "`<anon>@8` is the request-binding currency validator (api/validator.go:8). Every "
        "execution passed.\n\n```\n" + "\n".join(render_path(p) for p in shown) + "\n```\n\n"
        "Withheld (observed but not shown): " + ", ".join(p.execution for p in held) + "\n"
    )
    sites = static_decision_sites(source_root, DECISION_FILES)
    parts.append(
        "## Static decision sites (every `if` line; no semantics)\n\n"
        + "\n".join(f"- {s['file']}:{s['line']}  if {s['condition']}" for s in sites)
        + "\n"
    )
    for rel in SOURCES:
        parts.append(f"## Source: {rel}\n\n```go\n{numbered(source_root / rel)}\n```\n")
    bundle = "\n".join(parts)
    (out / "context-bundle.md").write_text(bundle)
    (out / "holdout.json").write_text(
        json.dumps(
            {"holdout": [p.execution for p in held], "shown": [p.execution for p in shown]},
            indent=1,
        )
        + "\n"
    )
    digest = hashlib.sha256(bundle.encode()).hexdigest()[:16]
    (out / "context-bundle.sha").write_text(digest + "\n")
    print(
        f"bundle {len(bundle)} chars, {bundle.count(chr(10))} lines, sha {digest}; shown {len(shown)}, withheld {len(held)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
