# ruff: noqa: E501
"""Experiment 10, case A, v3: the v2 bundle plus DETERMINISTIC EXECUTION STRUCTURE.

The observed skeleton (diffgenome.structure) of the SHOWN head executions, over the entities
of the bundle, is added as constraints: containment, phase order, repeated regions and the
order inside one repetition. Withheld traces never inform it. Same schema as v2 (Outcome and
boundary bindings; no relations, derived order or iteration).

usage: build_context_exp10c.py <head-run> <base-run> <out-dir>
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import build_context_exp10b as v2
from build_context_exp10 import SHOWN, load

from diffgenome.structure import build_skeleton, render

VOCAB = [
    "DatabaseApplicationType._import_table_fields",
    "DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies",
    "DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized",
    "LinkRowFieldType.get_import_dependency_when_referenced",
    "FieldType.get_import_dependency_when_referenced",
    "FormulaFieldType.get_field_depdendencies_before_import_serialized",
    "LookupFieldType.get_field_depdendencies_before_import_serialized",
    "FieldType.get_field_depdendencies_before_import_serialized",
    "DeferredFieldImporter.add_deferred_field_import",
    "DeferredFieldImporter.run_deferred_field_imports",
    "DeferredFieldImporter.get_all_fields_dependencies",
]

RULES = """
**Execution structure is a constraint, not yours to choose.** The section "Observed execution
structure" below is derived mechanically from the shown executions: which function runs
during which (containment), the order of phases inside a function, which calls form a
repeated region, and the order of calls and decisions inside one repetition. Call nesting and
relative procedural placement supplied by mechanics are constraints. Do not reorder calls, and
do not hoist a call or a decision outside its observed enclosing function. The checker judges
every procedure's structure (which calls and decisions it places inside which function, and
the order of consecutive steps) against these facts, and a prediction that places a call or a
decision where it was never observed is indeterminate. The format has no loops: if you cannot
express a repetition inside its enclosing function without violating these constraints, say
so in `unknowns` rather than hoisting it.
"""


def main() -> int:
    head_run, base_run, out = (Path(a) for a in sys.argv[1:4])
    v2.INSTRUCTIONS = v2.INSTRUCTIONS.replace(
        "**Not available** (deliberately)", RULES.strip() + "\n\n**Not available** (deliberately)"
    )
    v2.main.__globals__["INSTRUCTIONS"] = v2.INSTRUCTIONS
    sys.argv = [sys.argv[0], str(head_run), str(base_run), str(out)]
    v2.main()
    H = load(head_run)
    sk = build_skeleton([H[t] for t in SHOWN], VOCAB)
    section = (
        "## Observed execution structure (deterministic; shown head executions only)\n\n"
        "`site:br:…` is a decision site evaluated in that function's own call. A function's nearest "
        "modeled caller is the closest enclosing call among the functions listed; `<root>` means none.\n\n```\n"
        + render(sk)
        + "\n```\n"
    )
    bundle = (out / "context-bundle.md").read_text()
    anchor = "## Mechanics at HEAD"
    assert anchor in bundle
    bundle = bundle.replace(anchor, section + "\n" + anchor, 1)
    (out / "context-bundle.md").write_text(bundle)
    digest = hashlib.sha256(bundle.encode()).hexdigest()[:16]
    (out / "context-bundle.sha").write_text(digest + "\n")
    print(f"v3 bundle {len(bundle)} chars, {bundle.count(chr(10))} lines, sha {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
