# ruff: noqa: E501
"""Experiment 10, case A (Baserow #6069): deterministic bundle for a fresh proposer.

Same method as Experiment 09: mechanics + chronological observed event logs (head AND base,
the before-phenotype), exact source, test source; some tests withheld from the model and the
checker. Case-specific names live here (experiment script), never in the core.

usage: build_context_exp10.py <head-run> <base-run> <head-tree> <base-tree> <out-dir>
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from diffgenome.collect.py_monitoring import if_sites
from diffgenome.model import CallNode
from diffgenome.serialize import execution_from_json

REPO = Path.home() / "sample_repos/baserow"
MB = "e9ef2697baf8d6967e254b468bf82483de121e68"
HEAD = "70c81307d3b6b4951f82cac65cc7779462c026ac"
FILES = [
    "backend/src/baserow/contrib/database/application_types.py",
    "backend/src/baserow/contrib/database/fields/field_types.py",
    "backend/src/baserow/contrib/database/fields/registries.py",
    "backend/src/baserow/contrib/database/fields/utils/deferred_field_importer.py",
]
ROOT = "DatabaseApplicationType._import_table_fields"
# entities shown in event logs (substring of the collector's symbol); everything else is looked through
ENTITIES = (
    "DatabaseApplicationType._import_table_fields",
    "get_field_depdendencies_before_import_serialized",
    "get_import_dependency_when_referenced",
    "DeferredFieldImporter.add_deferred_field_import",
    "DeferredFieldImporter.run_deferred_field_imports",
    "DeferredFieldImporter.get_all_fields_dependencies",
    "FieldDependencyHandler.group_dependencies_by_level",
)
NEW_TESTS = "backend/tests/baserow/core/snapshots/test_snapshot_array_formula_import.py"
SHOWN = [
    "test_snapshot_with_explicit_array_primary_dependency",
    "test_snapshot_with_implicit_array_primary_dependency",
    "test_can_import_database_with_formula_dependencies",
]
HOLDOUT = [
    "test_snapshot_with_implicit_array_primary_dependency_two_links_deep",
    "test_duplicate_application_with_implicit_array_primary_dependency",
]
EXTRA_TEST_SRC = (
    "backend/tests/baserow/contrib/database/field/dependencies/test_field_dependency_handler.py",
    "test_can_import_database_with_formula_dependencies",
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
- decision sites (`if`) with stable ids `br:...` (hash of repository-relative file and the
  condition's source span, per revision: the same `if` has DIFFERENT ids at base and head
  when lines moved), source predicate, and for sites in lowered functions: operand origins
  (local def-use) and the (site, outcome) pairs required to reach them;
- sites marked `runtime only` are inside NESTED functions, which the static front end does
  not lower: their outcomes are observed but no static facts exist for them;
- for every call and store in lowered functions: which (site, outcome) pairs it requires;
- for the tests shown, at head AND at base: the ordered event log of the relevant calls under
  `_import_table_fields`, each call's argument shapes with value digests (`#abcd12`: equal
  digests = equal values; contents are not recorded), results, the observed outcome (T/F)
  of every decision site in those calls, and the test's outcome with the raised exception.

Your job is MEANING: name the variables that matter, abstract the predicates, and give compact
rules that GENERATE the observed behavior of the head (the change), and explain the
before/after phenotype (which tests fail at base and pass at head, and why). A machine will
check everything you cite and assign status; you assign none. Two tests are withheld (their
traces, at base and head, are not shown; their source is). You must write scenarios for them;
they will be predicted from your genome and compared with what executed.

Return ONLY one JSON object:

{
 "variables": [{"id", "name", "origin": "state|setting|input|derived", "description",
                "observed_as": {"fact": "<state fact name>", "kind": "is_set|sign|bool"} | null,
                "definition": "<predicate over other variables>" | null,
                "evidence": [...]}],
 "decisions": [{"id", "entity": "<function, e.g. LinkRowFieldType.get_import_dependency_when_referenced>", "site": "br:... (a HEAD site id)",
                "inputs": [...], "predicate": "<over variable names>", "order": <int>,
                "true_branch":  {"steps": [...], "calls": [...], "absent": [...], "stops": bool, "effect": "..."},
                "false_branch": {...}, "evidence": [...]}],
 "transitions": [{"id", "entity", "when": "<predicate or true>", "sets": {"<variable>": "<expr>"},
                  "state_before", "action", "state_after", "evidence": [...]}],
 "procedures": [{"id", "entity", "steps": ["call:<entity>", "T:<transition id>", "D:<decision id>", ...], "evidence": [...]}],
 "rules": [{"id", "name", "inputs", "relevant_state", "condition", "consequences": [...], "decision": "<id>|null", "evidence": [...]}],
 "regimes": [{"id", "name", "facts": {...}, "members": ["<test name>"], "evidence": [...]}],
 "scenarios": {"<test name>": {"state": {<variable>: value},
                               "calls": [{"entity": "<entity>", "facts": {<variable>: value}}],
                               "phenotype": {"base": "passed|failed", "head": "passed|failed", "why": "<one sentence from your rules>"}}},
 "unknowns": [{"what", "why"}]
}

Semantics used by the predictor (it is fixed; you cannot change it):
- A call of an entity runs its procedure's steps in order. "call:X" records a call and, if X
  has a procedure, runs it; "T:id" applies a transition (if `when` holds, each variable in
  `sets` becomes the expression: literals true/false/none/integers, `var`, `!var`,
  `var + k`, `var - k`, `max(0, var - k)`); "D:id" evaluates a decision and runs the taken
  branch's `steps` (or, if empty, its `calls` as "call:" steps); a branch with `stops: true`
  ends the entity. Decisions evaluate `predicate` over the current variable values
  (booleans/integers; `!name`, comparisons, `&&`, `||`, no parentheses). There are no loops:
  a scenario lists every call, in order, with the facts that hold for that call.
- The predicted decision outcomes at your decision sites, in order, must equal the observed
  outcomes at those sites in the head execution (every evaluation, in order). Choose which
  sites your genome covers; every observed evaluation of a covered site counts.
- `phenotype` is your claim; the predictor cannot derive pass/fail, it is scored separately.
- Use only site ids given. Evidence ref kinds (JSON):
  {"kind":"source","file":"<repo-relative path>","line":N,"text":"<exact text>"}
  {"kind":"branch","site":"br:...","test":"<shown test name>","outcome":true|false}
  {"kind":"control","site":"br:...","outcome":true|false,"callee":"<call expression>"}
  {"kind":"dataflow","site":"br:...","origin":"<e.g. param:serialized_field>"}
  Cite only shown tests, and only head sites, in branch evidence.
- Prefer few, generative rules. Be honest in `unknowns` about what the evidence cannot settle
  and about anything this genome format cannot express.
"""


def git_show(rev: str, path: str) -> str:
    return subprocess.run(
        ["git", "show", f"{rev}:{path}"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout


def site_table(rev: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for rel in FILES:
        src = git_show(rev, rel)
        lines = src.splitlines()
        for s in if_sites(src, rel):
            (l1, c1), (l2, c2) = s.test
            text = (
                lines[l1 - 1].encode()[c1 - 1 : c2 - 1].decode()
                if l1 == l2
                else lines[l1 - 1].encode()[c1 - 1 :].decode().strip() + " …"
            )
            out[s.site] = {"file": rel, "line": l1, "pred": text}
    return out


def fmt_req(req: list[list[Any]]) -> str:
    return (
        " & ".join(f"{r[0]}={'T' if r[1] else 'F'}" if r[1] is not None else r[0] for r in req)
        or "—"
    )


def short(sym: str) -> str:
    s = sym.split("baserow.contrib.database.", 1)[-1]
    for pre in ("application_types.", "fields.field_types.", "fields.registries.",
                "fields.utils.deferred_field_importer.", "fields.dependencies.handler."):  # fmt: skip
        if s.startswith(pre):
            return s[len(pre) :]
    return s


def args_str(n: CallNode) -> str:
    return ", ".join(
        f"{a}={t}" + (f"#{d[:6]}" if d else "") for a, t, d in n.args if a not in ("self", "cls")
    )


def event_log(ex: Any, sites: dict[str, dict[str, Any]], static: set[str]) -> list[str]:
    nodes = ex.nodes
    roots = [n.id for n in nodes if isinstance(n, CallNode) and n.symbol.endswith(ROOT)]
    if not roots:
        return ["(no call of _import_table_fields)"]
    in_sub: set[int] = set()
    for n in nodes:
        p = n.id
        while p is not None:
            if p in roots:
                in_sub.add(n.id)
                break
            p = nodes[p].parent

    def shown(n: Any) -> bool:
        return isinstance(n, CallNode) and n.id in in_sub and any(e in n.symbol for e in ENTITIES)

    def depth(nid: int) -> int:
        d, p = 0, nodes[nid].parent
        while p is not None:
            if shown(nodes[p]):
                d += 1
            p = nodes[p].parent
        return d

    out: list[str] = []
    events = [(n.id, 1, n) for n in nodes if shown(n)] + [
        (b.seq, 0, b) for b in ex.branches if b.node in in_sub and shown(nodes[b.node])
    ]
    for _, kind, o in sorted(events, key=lambda e: (e[0], e[1])):
        if kind == 0:
            meta = sites.get(o.site, {"line": "?", "pred": "?"})
            sym = nodes[o.node].symbol if isinstance(nodes[o.node], CallNode) else ""
            tag = (
                ""
                if o.site in static
                else "  (runtime only: nested function)"
                if "<locals>" in sym
                else "  (runtime only: file not lowered)"
            )
            out.append(
                f"{'  ' * (depth(o.node) + 1)}branch {o.site} L{meta['line']} `{meta['pred'][:70]}` = {'T' if o.outcome else 'F'}{tag}"
            )
        else:
            res = f" -> #{o.result[:6]}" if o.result else ""
            out.append(
                f"{'  ' * depth(o.id)}call {short(o.symbol)}({args_str(o)}) [{o.outcome.split(':')[0]}]{res}"
            )
    return out


def failure(ex: Any) -> str:
    if ex.outcome == "passed":
        return "passed"
    raised = [
        n
        for n in ex.nodes
        if isinstance(n, CallNode) and n.outcome.startswith("raised") and "baserow" in n.symbol
    ]
    # the outermost repo frame chain of the last raise that reached the test
    last = raised[-1] if raised else None
    chain = []
    n = last
    while n is not None and isinstance(n, CallNode):
        if n.outcome.startswith("raised") and "tests." not in n.symbol:
            chain.append(short(n.symbol).split(".")[-2] + "." + n.symbol.split(".")[-1])
        n = ex.nodes[n.parent] if n.parent is not None else None
    exc = last.outcome.split("raised:py:")[-1] if last else "?"
    top = [
        c
        for c in chain
        if "Formula" in c or "DatabaseApplicationType" in c or "Snapshot" in c or "CoreHandler" in c
    ]
    return f"failed: {exc} raised in {' <- '.join(top[:6])}"


def load(run: Path) -> dict[str, Any]:
    return {
        execution_from_json(f.read_text()).stimulus_ref.split("::")[-1]: execution_from_json(
            f.read_text()
        )
        for f in sorted((run / "traces-existing").glob("*.json"))
    }


def mechanics_section(run: Path, names: tuple[str, ...]) -> tuple[str, set[str]]:
    mech = json.loads((run / "mechanics.json").read_text())["functions"]
    static = {s["site"] for f in mech for s in f["sites"]}
    lines = []
    for f in mech:
        if not any(f["symbol"].endswith(n) for n in names):
            continue
        lines.append(f"### {short(f['symbol'].removeprefix('py:'))}  ({f['file']})")
        for s in f["sites"]:
            ops = "; ".join(f"{o['path']} ← {', '.join(o['origins'])}" for o in s["operands"])
            lines.append(
                f"- site {s['site']} line {s['line']}: `{s['pred']}` | operands: {ops} | requires: {fmt_req(s['requires'])} | then exits: {s['then_exits']}, else exits: {s['else_exits']}"
            )
        for c in f["calls"]:
            lines.append(
                f"- call `{c['callee'][:90]}` line {c['line']} requires: {fmt_req(c['requires'])}"
            )
        for st in f["stores"]:
            lines.append(
                f"- store `{st['path']}` ← {', '.join(st['origins'])} line {st['line']} requires: {fmt_req(st['requires'])}"
            )
        for u in f["unknown"]:
            lines.append(
                f"- OPAQUE statement line {u['line']}: {u['reason']} (not lowered; its sites are runtime only)"
            )
        lines.append("")
    return "\n".join(lines), static


def main() -> int:
    head_run, base_run, _head_tree, _base_tree, out = (Path(a) for a in sys.argv[1:6])
    out.mkdir(parents=True, exist_ok=True)
    names = (
        ROOT,
        "LinkRowFieldType.get_import_dependency_when_referenced",
        "registries.FieldType.get_import_dependency_when_referenced",
        "FormulaFieldType.get_field_depdendencies_before_import_serialized",
        "LookupFieldType.get_field_depdendencies_before_import_serialized",
        "registries.FieldType.get_field_depdendencies_before_import_serialized",
    )
    mh, static_h = mechanics_section(head_run, names)
    mb, static_b = mechanics_section(base_run, names)
    sites_h, sites_b = site_table(HEAD), site_table(MB)
    parts = [INSTRUCTIONS]
    parts.append(
        "## Mechanics at HEAD (deterministic, intra-procedural)\n\nNested functions of `_import_table_fields` are opaque to the static front end. "
        "`DeferredFieldImporter` is in a file the change does not touch, so no facts were computed for it.\n\n"
        + mh
    )
    parts.append(
        "## Mechanics at BASE (same functions; site ids differ where lines moved)\n\n" + mb
    )
    runtime_only = {
        s: m
        for s, m in sites_h.items()
        if s not in static_h
        and (
            ("application_types" in m["file"] and 464 <= m["line"] <= 530)
            or "deferred_field_importer" in m["file"]
        )
    }
    parts.append(
        "## Runtime-only sites at HEAD (nested functions of `_import_table_fields`, and the unlowered `DeferredFieldImporter`; outcome observed, no static facts)\n\n"
        + "\n".join(
            f"- {s} {m['file']}:{m['line']} `{m['pred']}`"
            for s, m in sorted(runtime_only.items(), key=lambda x: x[1]["line"])
        )
        + "\n"
    )
    H, B = load(head_run), load(base_run)
    logs = []
    for t in SHOWN:
        for tag, runs, sites, static in (
            ("HEAD", H, sites_h, static_h),
            ("BASE", B, sites_b, static_b),
        ):
            ex = runs[t]
            logs.append(
                f"### {t}  [{tag}]  outcome: {failure(ex)}\n"
                + "\n".join(event_log(ex, sites, static))
            )
    parts.append(
        "## Observed event logs (shown tests, at head and at base)\n\nCalls under `_import_table_fields` in chronological order, "
        "indented by depth among the shown calls (everything else is looked through), with argument shapes and value digests, "
        "results, and the observed outcome of every decision site evaluated in those calls.\n\n```\n"
        + "\n\n".join(logs)
        + "\n```\n\nWithheld (observed at head and base, not shown): "
        + ", ".join(HOLDOUT)
        + "\n"
    )
    diff = subprocess.run(
        ["git", "diff", f"{MB}..{HEAD}", "--", "backend/src"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
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
    ft = git_show(HEAD, FILES[1])
    parts.append(
        "## Source at HEAD: import-dependency methods of formula-like field types (field_types.py)\n\n```python\n"
        + extract_methods(
            ft,
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
    print(f"bundle {len(bundle)} chars, {bundle.count(chr(10))} lines, sha {digest}")
    return 0


def extract_function(src: str, name: str) -> str:
    import ast

    lines = src.splitlines()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            return "\n".join(
                f"{i:4d}  {lines[i - 1]}" for i in range(start, (node.end_lineno or start) + 1)
            )
    return "(not found)"


def extract_methods(src: str, names: tuple[str, ...]) -> str:
    import ast

    lines = src.splitlines()
    chunks = []
    for cls in ast.parse(src).body:
        if not isinstance(cls, ast.ClassDef):
            continue
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name in names:
                chunks.append(
                    f"# class {cls.name}\n"
                    + "\n".join(
                        f"{i:4d}  {lines[i - 1]}"
                        for i in range(node.lineno, (node.end_lineno or node.lineno) + 1)
                    )
                )
    return "\n\n".join(chunks)


if __name__ == "__main__":
    raise SystemExit(main())
