# ruff: noqa: E501
"""Experiment 10, case A, after Step 2 (Outcome + boundary bindings): fresh bundle.

Same case, same holdout, same event-log rendering as build_context_exp10.py, over the
repaired substrate (nested functions and the mechanics frontier lowered). The instructions
describe the extended schema: boundary bindings (design 5.1) and Outcome (5.5). Relations,
derived order and iteration are NOT available (design: DO NOT BUILD YET) and are said so.

usage: build_context_exp10b.py <head-run> <base-run> <out-dir>
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from build_context_exp10 import (
    EXTRA_TEST_SRC,
    FILES,
    HEAD,
    HOLDOUT,
    MB,
    NEW_TESTS,
    REPO,
    SHOWN,
    event_log,
    extract_function,
    extract_methods,
    failure,
    git_show,
    load,
    mechanics_section,
    site_table,
)

from diffgenome.genome_state import Mechanics, Observations, change_sites
from diffgenome.model import CallNode

ENTRIES = (
    "DatabaseApplicationType.import_tables_serialized",
    "DatabaseApplicationType.import_serialized",
)

INSTRUCTIONS = """\
# Task: propose the semantic layer of a Behavioral Genome for a real code change

You are an abstraction engine. The change is Baserow PR #6069 (merge base e9ef2697 → head
70c81307): "import dependency of a formula that references a link row field by name".
When a database is imported (snapshot, duplication), fields with dependencies are deferred
and imported in dependency order by `DeferredFieldImporter`. Before the change, a formula
`field('LinkField')` declared only a dependency on the link row field itself. The change adds
`FieldType.get_import_dependency_when_referenced` (default: None), overrides it in
`LinkRowFieldType` to return `(<linked table's primary field name>, <link field name>)`, and
expands every same-table reference `(name, None)` through it in a nested helper
`_expand_implied_import_dependencies` inside `DatabaseApplicationType._import_table_fields`.

Deterministic machinery has ALREADY established the mechanics below. Do not re-derive them
and do not contradict them:
- decision sites (`if`) with stable ids `br:...` (per revision: the same `if` has DIFFERENT
  ids at base and head when lines moved), source predicate, operand origins (local def-use,
  `closure:` = read from an enclosing function), and the (site, outcome) pairs required to
  reach them. Nested functions and the directly called `DeferredFieldImporter` have facts;
- for every call and store: which (site, outcome) pairs it requires;
- for the tests shown, at head AND at base: the ordered event log of the relevant calls under
  `_import_table_fields`, each call's argument shapes with value digests (`#abcd12`: equal
  digests = equal values; contents are not recorded), results, the observed outcome (T/F)
  of every decision site in those calls, and the observed EXIT of the import entry points.
  The digest `#99bf08` is the digest of None; `NoneType` is None's shape.

Your job is MEANING: name the variables that matter, abstract the predicates, and give compact
rules that GENERATE the observed behavior of the head, and explain the before/after phenotype
(which calls end how at base and at head, and why). A machine checks everything you cite and
assigns status; you assign none. Two tests are withheld (traces at base and head not shown;
source shown). Write scenarios for them; they will be predicted and compared with what executed.

## The genome format (fixed; the checker and predictor implement exactly this)

Return ONLY one JSON object:

{
 "variables": [{"id", "name", "origin": "state|setting|input|derived", "description",
                "observed_as": null
                  | {"fact": "<receiver/global state fact>", "kind": "is_set|sign|bool"}
                  | {"at": {"entity": "<function>", "point": "arg:<name>" | "result"},
                     "kind": "is_set" | "changed_from:arg:<name>" | "size" | "bool"},
                "definition": "<predicate over other variables>" | null,
                "evidence": [...]}],
 "decisions": [{"id", "entity", "site": "br:... (a HEAD site id)", "inputs": [...],
                "predicate": "<over variable names>", "order": <int>,
                "true_branch":  {"steps": [...], "calls": [...], "absent": [...], "stops": bool,
                                 "outcome": {"entity": "<function>", "is": "<exit>"} | null, "effect": "..."},
                "false_branch": {...}, "evidence": [...]}],
 "transitions": [{"id", "entity", "when": "<predicate or true>", "sets": {"<variable>": "<expr>"},
                  "state_before", "action", "state_after", "evidence": [...]}],
 "procedures": [{"id", "entity", "steps": ["call:<entity>", "T:<transition id>", "D:<decision id>", ...],
                 "outcome": {"entity": "<function>", "is": "<exit>"} | null, "evidence": [...]}],
 "rules": [{"id", "name", "inputs", "relevant_state", "condition", "consequences": [...], "decision": "<id>|null", "evidence": [...]}],
 "regimes": [{"id", "name", "facts": {...}, "members": ["<test name>"], "evidence": [...]}],
 "scenarios": {"<test name>": {"state": {<variable>: value},
                               "calls": [{"entity": "<entity>", "facts": {<variable>: value}}],
                               "phenotype": {"base": "<exit of import_tables_serialized>", "head": "<exit>", "why": "<one sentence from your rules>"}}},
 "unknowns": [{"what", "why"}]
}

**Boundary bindings.** A variable may be bound to an identity-level fact at a call boundary of
an entity: `is_set` (the argument/result is not None), `changed_from:arg:<name>` (the result's
digest differs from that argument's digest), `size` (an argument's collection size), `bool`.
The checker reads these from the digests and shapes you see in the logs, per call. Argument
facts are known when the call starts; result and change facts when it ends. A transition of
an entity that sets a boundary-bound variable is checked against that call's observed
boundary: when the entry state cannot decide the path, the checker follows the branches that
actually executed in that call (a decision with an atomic predicate `v` / `!v` then binds v).

**Outcome.** An exit is one of `returned`, `returned-error[:<kind>]`, `raised[:<kind>]`,
`panic[:<kind>]`, `cancelled` (`completed` = `returned`). `<kind>` is the runtime type name,
e.g. `raised:django.db.utils.DataError`. A branch's outcome names the function whose exit it
determines, which may be the deciding function or one ENCLOSING it (an effect that surfaces
later in the same call). A procedure's outcome is its entity's exit when its steps complete
without a stopping branch. Exits are compared with the observed exit of that function's calls,
never with test results.

**Not available** (deliberately): relation-valued variables, derived orders, iteration steps.
If the behavior needs them, say so precisely in `unknowns`; do not simulate them with
per-instance variable names.

Semantics used by the predictor:
- A scenario's `calls` are the entry calls in order. A call of an entity with a procedure runs
  it; a call of an entity the genome says nothing about is recorded and skipped; a call of an
  entity that has decisions but no procedure stops the prediction (so give every entity whose
  decisions you list a procedure, or reach its decisions through another entity's procedure).
  "call:X" records a call and, if X has a procedure, runs it; "T:id" applies a transition
  (literals true/false/none/integers, `var`, `!var`, `var + k`, `var - k`, `max(0, var - k)`);
  "D:id" evaluates a decision and runs the taken branch's `steps` (or its `calls`); a branch
  with `stops: true` ends the entity. Predicates: booleans/integers, `!name`, comparisons,
  `&&`, `||`, no parentheses. There are no loops: a scenario lists every call, in order, with
  the facts that hold for that call.
- SCORING covers every observed evaluation of EVERY site listed under "Required sites" below
  (the changed functions and functions nested in them), in order, per test. A site no decision
  covers makes the prediction indeterminate. Predicted exits are compared per entity with the
  observed exits of that entity's calls.
- `phenotype` is your claim about the entry's exit at base and head; scored separately.
- Use only site ids given. Evidence ref kinds (JSON):
  {"kind":"source","file":"<repo-relative path>","line":N,"text":"<exact text>"}
  {"kind":"branch","site":"br:...","test":"<shown test name>","outcome":true|false}
  {"kind":"control","site":"br:...","outcome":true|false,"callee":"<call expression>"}
  {"kind":"dataflow","site":"br:...","origin":"<e.g. param:serialized_field>"}
  {"kind":"boundary","entity":"<function>","point":"arg:<name>|result","binding":"is_set|changed_from:arg:<name>|size|bool","value":<value>,"test":"<shown test name>"}
  {"kind":"outcome","entity":"<function>","exit":"<exit>","test":"<shown test name>"}
  Cite only shown tests, and only head sites, in branch/boundary/outcome evidence.
- Prefer few, generative rules. Be honest in `unknowns`.
"""


def main() -> int:
    head_run, base_run, out = (Path(a) for a in sys.argv[1:4])
    out.mkdir(parents=True, exist_ok=True)
    names = (
        "DatabaseApplicationType._import_table_fields",
        "_import_table_fields.<locals>._expand_implied_import_dependencies",
        "_import_table_fields.<locals>._import_field_serialized",
        "LinkRowFieldType.get_import_dependency_when_referenced",
        "registries.FieldType.get_import_dependency_when_referenced",
        "FormulaFieldType.get_field_depdendencies_before_import_serialized",
        "LookupFieldType.get_field_depdendencies_before_import_serialized",
        "registries.FieldType.get_field_depdendencies_before_import_serialized",
        "DeferredFieldImporter.add_deferred_field_import",
        "DeferredFieldImporter.get_all_fields_dependencies",
        "DeferredFieldImporter.run_deferred_field_imports",
    )
    mh, static_h = mechanics_section(head_run, names)
    mb, static_b = mechanics_section(base_run, names)
    sites_h, sites_b = site_table(HEAD), site_table(MB)
    H, B = load(head_run), load(base_run)
    mech = Mechanics(json.loads((head_run / "mechanics.json").read_text())["functions"])
    changed = json.loads((head_run / "diffgenome-change.json").read_text())["change"]["symbols"]
    shown_obs = Observations([H[t] for t in SHOWN])
    required = change_sites(mech, shown_obs, changed)
    parts = [INSTRUCTIONS]
    parts.append(
        "## Required sites (scored in every test; head ids)\n\n"
        + "\n".join(
            f"- {s} {sites_h.get(s, {}).get('file', '?')}:{sites_h.get(s, {}).get('line', '?')} `{sites_h.get(s, {}).get('pred', '?')}`"
            for s in sorted(
                required,
                key=lambda s: (
                    sites_h.get(s, {}).get("file", ""),
                    sites_h.get(s, {}).get("line", 0),
                ),
            )
        )
        + "\n"
    )
    parts.append("## Mechanics at HEAD (deterministic, intra-procedural)\n\n" + mh)
    parts.append(
        "## Mechanics at BASE (same functions; site ids differ where lines moved)\n\n" + mb
    )
    logs = []
    for t in SHOWN:
        for tag, runs, sites, static in (
            ("HEAD", H, sites_h, static_h),
            ("BASE", B, sites_b, static_b),
        ):
            ex = runs[t]
            exits = [
                f"{n.symbol.split('.')[-2]}.{n.symbol.split('.')[-1]} {n.outcome.replace(':py:', ':')}"
                for n in ex.nodes
                if isinstance(n, CallNode) and any(n.symbol.endswith(e) for e in ENTRIES)
            ]
            logs.append(
                f"### {t}  [{tag}]  test: {failure(ex)}\nexits: {'; '.join(exits)}\n"
                + "\n".join(event_log(ex, sites, static))
            )
    parts.append(
        "## Observed event logs (shown tests, at head and at base)\n\nCalls under `_import_table_fields` in chronological order, "
        "indented by depth among the shown calls (everything else is looked through), with argument shapes and value digests, "
        "results, and the observed outcome of every decision site evaluated in those calls. `exits` are the observed exits of "
        "the import entry points in that test.\n\n```\n"
        + "\n\n".join(logs)
        + "\n```\n\nWithheld (observed at head and base, not shown): "
        + ", ".join(HOLDOUT)
        + "\n"
    )
    diff = subprocess.run(
        ["git", "diff", f"{MB}..{HEAD}", "--", "backend/src"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    parts.append(
        f"## The change (git diff {MB[:8]}..{HEAD[:8]} -- backend/src)\n\n```diff\n{diff}```\n"
    )
    at = git_show(HEAD, FILES[0]).splitlines()
    parts.append(
        f"## Source at HEAD: {FILES[0]} lines 404-597 (`_import_table_fields`)\n\n```python\n"
        + "\n".join(f"{i:4d}  {ln}" for i, ln in enumerate(at[403:597], 404))
        + "\n```\n"
    )
    dfi = git_show(HEAD, FILES[3]).splitlines()
    parts.append(
        f"## Source: {FILES[3]} (unchanged by the change)\n\n```python\n"
        + "\n".join(f"{i:4d}  {ln}" for i, ln in enumerate(dfi, 1))
        + "\n```\n"
    )
    parts.append(
        "## Source at HEAD: import-dependency methods of formula-like field types (field_types.py)\n\n```python\n"
        + extract_methods(
            git_show(HEAD, FILES[1]),
            (
                "get_field_depdendencies_before_import_serialized",
                "get_import_dependency_when_referenced",
            ),
        )
        + "\n```\n"
    )
    ts = git_show(HEAD, NEW_TESTS).splitlines()
    parts.append(
        f"## Source: {NEW_TESTS} (added by the change; the same file was run at base)\n\n```python\n"
        + "\n".join(f"{i:4d}  {ln}" for i, ln in enumerate(ts, 1))
        + "\n```\n"
    )
    parts.append(
        f"## Source: {EXTRA_TEST_SRC[0]}::{EXTRA_TEST_SRC[1]}\n\n```python\n"
        + extract_function(git_show(HEAD, EXTRA_TEST_SRC[0]), EXTRA_TEST_SRC[1])
        + "\n```\n"
    )
    bundle = "\n".join(parts)
    (out / "context-bundle.md").write_text(bundle)
    digest = hashlib.sha256(bundle.encode()).hexdigest()[:16]
    (out / "context-bundle.sha").write_text(digest + "\n")
    (out / "holdout.json").write_text(
        json.dumps({"holdout": HOLDOUT, "shown": SHOWN, "not_scored": []}, indent=1) + "\n"
    )
    print(
        f"bundle {len(bundle)} chars, {bundle.count(chr(10))} lines, sha {digest}; required sites {len(required)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
