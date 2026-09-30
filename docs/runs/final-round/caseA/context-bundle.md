# Task: propose the semantic layer of a Behavioral Genome for a real code change

You are an abstraction engine. The change is git diff e9ef2697baf8d6967e254b468bf82483de121e68..70c81307d3b6b4951f82cac65cc7779462c026ac in the repository baserow (runtime
python/pytest). Changed symbols: baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields, baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies, baserow.contrib.database.fields.field_types.LinkRowFieldType, baserow.contrib.database.fields.field_types.LinkRowFieldType.get_import_dependency_when_referenced, baserow.contrib.database.fields.registries.FieldType, baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized, baserow.contrib.database.fields.registries.FieldType.get_import_dependency_when_referenced.

Deterministic machinery has ALREADY established the mechanics below. Do not re-derive them
and do not contradict them:
- decision sites (`if`) with stable ids `br:...`, source predicate, operand origins (local
  def-use), and the (site, outcome) pairs required to reach them;
- for every call and store: which (site, outcome) pairs it requires;
- for the tests: the ordered event log of the relevant calls, each call's argument shapes with
  value digests (`#abcd12`: equal digests = equal values; contents are not recorded), results,
  every call's observed EXIT, and the observed outcome (T/F) of every decision site in those
  calls. 

Your job is MEANING: name the variables that matter, abstract the predicates, and give compact
rules that GENERATE the observed behavior (which calls happen, which decisions go which way,
how each entry call exits). A machine checks everything you cite and assigns status; you assign
none. Write a scenario for every test listed, keyed by its exact test id as written in the
event logs; each is predicted from your genome and compared with what executed.

## The genome format (fixed; the checker and predictor implement exactly this)

Return ONLY one JSON object:

{
 "variables": [{"id", "name", "origin": "state|setting|input|derived", "description",
                "observed_as": null
                  | {"fact": "<receiver/global state fact>", "kind": "is_set|sign|bool"}
                  | {"at": {"entity": "<function>", "point": "arg:<name>" | "result"},
                     "kind": "is_set" | "changed_from:arg:<name>" | "size" | "bool"}
                  | {"at": {...}, "kind": "identity", "scope": "call" | "execution"}
                  | {"at": {...}, "kind": "equals_literal", "scope": "call" | "execution",
                     "literal": {"lang": "python", "type": "string|int|uint8|...|bool|nil", "value": <v>,
                                 "source": {"file": "<repo path>", "line": N}}}
                  | [<several of the above>],
                "definition": "<predicate over other variables>" | null,
                "evidence": [...]}],
 "decisions": [{"id", "entity", "site": "br:... (a HEAD site id)", "inputs": [...],
                "predicate": "<over variable names>", "order": <int>,
                "true_branch":  {"steps": [...], "calls": [...], "absent": [...], "stops": bool,
                                 "outcome": {"entity": "<function>", "is": "<exit>"} | null, "effect": "..."},
                "false_branch": {...}, "evidence": [...]}],
 "transitions": [{"id", "entity", "when": "<predicate or true>", "sets": {"<variable>": "<expr>"},
                  "state_before", "action", "state_after", "evidence": [...]}],
 "regions": [{"id", "entity": "<the enclosing function>", "head": "<the observed family that starts each repetition: a function name or site:br:...>",
              "steps": ["call:<entity>", "T:<transition id>", "D:<decision id>", ...], "evidence": [...]}],
 "procedures": [{"id", "entity", "steps": ["call:<entity>", "T:<transition id>", "D:<decision id>", "R:<region id>", ...],
                 "outcome": {"entity": "<function>", "is": "<exit>"} | null, "evidence": [...]}],
 "rules": [{"id", "name", "inputs", "relevant_state", "condition", "consequences": [...], "decision": "<id>|null", "evidence": [...]}],
 "regimes": [{"id", "name", "facts": {...}, "members": ["<test name>"], "evidence": [...]}],
 "scenarios": {"<test name>": {"state": {<variable>: value},
                               "calls": [{"entity": "<entity>", "facts": {<variable>: value},
                                          "occurrences": {"<region id>": [{"facts": {<variable>: value}}, ...]}}],
                               "phenotype": {"head": "<exit of the entry call>", "why": "<one sentence from your rules>"}}},
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

**Value identity and literals.** A binding of kind `identity` gives the variable an OPAQUE
value: the digest seen at that boundary, never decoded. With `scope: "execution"`, the value is
taken from that boundary's occurrences earlier in the same test (it must be unique there, or it
is unknown); with `scope: "call"` (default) from the call being judged. A variable with a LIST
of two or more `identity` bindings claims the SAME value appears at all of them in one test:
the checker verifies that from observed digest equality (equal in at least 2 tests carrying at
least 2 different values), rejects it if any test shows them different, and never infers flow
(only equality). Identity variables are compared only with `==` / `!=`. In scenarios, give an
identity variable a LABEL (any string, e.g. "access"): for shown tests the checker requires
equal labels exactly where the observed identities are equal. A binding of kind
`equals_literal` is true when the boundary value equals a literal WRITTEN in the source at the
cited line (bool, nil, an integer, or a short plain string); the checker confirms the literal on
that line and compares digests, it never decodes other values. Scenario facts for any bound
variable (boundary, identity, literal) are checked against the matching call in shown tests.

**Evidence and prediction eligibility.** Every item must cite checkable evidence; an item
with none stays a hypothesis and cannot drive a prediction. A supported item that some shown
test contradicts (e.g. its replayed outcome sequence differs) cannot drive a prediction either.
A variable with two or more identity bindings is evidenced by its bindings themselves.

**Outcome.** An exit is one of `returned`, `returned-error[:<kind>]`, `raised[:<kind>]`,
`panic[:<kind>]`, `cancelled` (`completed` = `returned`). `<kind>` is the runtime type name,
e.g. `raised:django.db.utils.DataError`. A branch's outcome names the function whose exit it
determines, which may be the deciding function or one ENCLOSING it (an effect that surfaces
later in the same call). A procedure's outcome is its entity's exit when its steps complete
without a stopping branch. Exits are compared with the observed exit of that function's calls,
never with test results.

**Repeated regions and occurrence facts.** Repeated region placement is supplied by mechanics.
Concrete occurrence facts are supplied by the scenario. Do not invent occurrence count, nesting
or order. A region (`regions`) is ONE body that runs once per occurrence of an OBSERVED repeated
region of its enclosing function (`entity`); its `head` must be the family that the observed
structure says starts every repetition, and its steps must follow the observed order inside one
repetition. The enclosing function's procedure places it with the step `"R:<region id>"`. The
genome never states how many times a region runs: a scenario's call of the enclosing function
supplies `occurrences: {"<region id>": [...]}`, one item per concrete occurrence in order, each
with that occurrence's facts (read them from the test's input; the k-th item is the k-th
repetition). For the shown tests the checker aligns your k-th item with the observed k-th
repetition and checks every fact it can observe there (boundary facts of the calls inside it,
and variables your atomic decisions `v` / `!v` bind from their observed outcomes); a
contradicted fact or a wrong count makes that prediction indeterminate.

**Execution structure is a constraint, not yours to choose.** The section "Observed execution
structure" below is derived mechanically from the shown executions: which function runs
during which (containment), the order of phases inside a function, which calls form a
repeated region, and the order of calls and decisions inside one repetition. Call nesting and
relative procedural placement supplied by mechanics are constraints. Do not reorder calls, and
do not hoist a call or a decision outside its observed enclosing function. The checker judges
every procedure's structure (which calls and decisions it places inside which function, and
the order of consecutive steps) against these facts, and a prediction that places a call or a
decision where it was never observed is indeterminate. Express a repetition inside its enclosing function as a region (see Repeated regions and occurrence facts, above), never by hoisting it.

**Not available** (deliberately): relation-valued variables, derived orders, iteration over
collections (loop variables, item identity across calls). If the behavior needs them, say so
precisely in `unknowns`; do not simulate them with per-instance variable names.

Semantics used by the predictor:
- A scenario's `calls` are the entry calls in order. A call of an entity with a procedure runs
  it; a call of an entity the genome says nothing about is recorded and skipped; a call of an
  entity that has decisions but no procedure stops the prediction (so give every entity whose
  decisions you list a procedure, or reach its decisions through another entity's procedure).
  "call:X" records a call and, if X has a procedure, runs it; "T:id" applies a transition
  (literals true/false/none/integers, `var`, `!var`, `var + k`, `var - k`, `max(0, var - k)`);
  "D:id" evaluates a decision and runs the taken branch's `steps` ONLY (a branch's
  `calls` are descriptive, what it reaches, and are never executed); a branch
  with `stops: true` ends the entity (inside a region too: there is no `continue`). "R:id"
  runs region id once per occurrence the current scenario call supplies, in order: that
  occurrence's facts hold during its body only (they are restored afterwards; variables bound
  to receiver/global state persist); a region with no supplied occurrences stops the prediction.
  Predicates: booleans/integers, `!name`, comparisons (identities: `==` / `!=` only),
  `&&`, `||`, no parentheses. A scenario
  lists every entry call, in order, with the facts that hold for that call and, for repeated
  regions inside it, per-occurrence facts.
- SCORING covers every observed evaluation of EVERY site listed under "Required sites" below
  (the changed functions and functions nested in them), in order, per test. A site no decision
  covers makes the prediction indeterminate. Predicted exits are compared per entity with the
  observed exits of that entity's calls.
- `phenotype` is your claim about the entry call's exit; scored separately.
- Use only site ids given. Evidence ref kinds (JSON):
  {"kind":"source","file":"<repo-relative path>","line":N,"text":"<exact text>"}
  {"kind":"branch","site":"br:...","test":"<shown test name>","outcome":true|false}
  {"kind":"control","site":"br:...","outcome":true|false,"callee":"<call expression>"}
  {"kind":"dataflow","site":"br:...","origin":"<e.g. param:req>"}
  {"kind":"boundary","entity":"<function>","point":"arg:<name>|result","binding":"is_set|changed_from:arg:<name>|size|bool","value":<value>,"test":"<shown test name>"}
  {"kind":"outcome","entity":"<function>","exit":"<exit>","test":"<shown test name>"}
  Cite only shown tests, and only head sites, in branch/boundary/outcome evidence.
- Prefer few, generative rules. Be honest in `unknowns`.



## Required sites

Every OBSERVED evaluation of these sites is scored, in every test.

- br:34ec71ee29c9 py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields line 456: `serialized_field['primary']`
- br:47a63ce03fc8 py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields line 532: `field_deps`
- br:09962e1ae1b2 py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields line 589: `field_type.needs_refresh_after_import_serialized`
- br:be7d3ee9e3b1 py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies line 497: `not field_deps`
- br:3f16965dcd1f py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized line 480: `table_instance not in table_fields_by_name`
- br:a0d4e306fb5a py:baserow.contrib.database.fields.field_types.LinkRowFieldType.get_import_dependency_when_referenced line 3710: `related_table_id is None or related_table_id not in primary_table_fields_map`
- br:f960d9f63045 py:baserow.contrib.database.fields.field_types.LinkRowFieldType.get_import_dependency_when_referenced line 3714: `primary_field_id not in serialized_fields_map`

## Observed execution structure (deterministic)

```
(from 5 shown execution(s))
- py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields: 5 occurrence(s)
    nearest modeled caller: py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec)
    runs during: py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec)
- py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies: 43 occurrence(s)
    nearest modeled caller: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec)
    runs during: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec)
- py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized: 43 occurrence(s)
    nearest modeled caller: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports (in 5 exec)
    runs during: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec), py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports (in 5 exec)
- py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized: 5 occurrence(s)
    nearest modeled caller: <root> (in 5 exec)
    runs during: <root> (in 5 exec)
- py:baserow.contrib.database.fields.field_cache.FieldCache.__init__: 64 occurrence(s)
    nearest modeled caller: <root> (in 4 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized (in 5 exec)
    runs during: <root> (in 4 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec), py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports (in 5 exec)
- py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized: 11 occurrence(s)
    nearest modeled caller: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec)
    runs during: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec)
- py:baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized: 10 occurrence(s)
    nearest modeled caller: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec)
    runs during: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec)
- py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized: 18 occurrence(s)
    nearest modeled caller: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec)
    runs during: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec)
- py:baserow.contrib.database.fields.field_types.LinkRowFieldType.get_import_dependency_when_referenced: 7 occurrence(s)
    nearest modeled caller: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies (in 4 exec)
    runs during: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 4 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies (in 4 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 4 exec)
- py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized: 1 occurrence(s)
    nearest modeled caller: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 1 exec)
    runs during: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 1 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 1 exec)
- py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db: 11 occurrence(s)
    nearest modeled caller: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec)
    runs during: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec)
- py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized: 14 occurrence(s)
    nearest modeled caller: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec)
    runs during: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec)
- py:baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized: 32 occurrence(s)
    nearest modeled caller: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec)
    runs during: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec)
- py:baserow.contrib.database.fields.registries.FieldType.get_import_dependency_when_referenced: 1 occurrence(s)
    nearest modeled caller: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies (in 1 exec)
    runs during: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 1 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies (in 1 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 1 exec)
- py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__: 5 occurrence(s)
    nearest modeled caller: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec)
    runs during: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec)
- py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import: 11 occurrence(s)
    nearest modeled caller: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec)
    runs during: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec)
- py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports: 5 occurrence(s)
    nearest modeled caller: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec)
    runs during: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec)
- py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates: 15 occurrence(s)
    nearest modeled caller: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec)
    runs during: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec)
- py:baserow.core.registry.ModelRegistryMixin.get_by_model: 2624 occurrence(s)
    nearest modeled caller: <root> (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec), py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized (in 5 exec), py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized (in 5 exec)
    runs during: <root> (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec), py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized (in 5 exec), py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized (in 5 exec), py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports (in 5 exec)
- py:baserow.core.registry.Registry.get: 1984 occurrence(s)
    nearest modeled caller: <root> (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec), py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized (in 5 exec)
    runs during: <root> (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized (in 5 exec), py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized (in 5 exec), py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized (in 5 exec), py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports (in 5 exec)

inside py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields:
  family py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies: in 5 occurrence(s), repeated (up to 9 in one occurrence)
  family py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized: in 5 occurrence(s), repeated (up to 7 in one occurrence)
  family py:baserow.contrib.database.fields.field_cache.FieldCache.__init__: in 5 occurrence(s), once
  family py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized: in 5 occurrence(s), repeated (up to 3 in one occurrence)
  family py:baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized: in 5 occurrence(s), repeated (up to 2 in one occurrence)
  family py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized: in 5 occurrence(s), repeated (up to 4 in one occurrence)
  family py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized: in 1 occurrence(s), once
  family py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db: in 5 occurrence(s), repeated (up to 3 in one occurrence)
  family py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized: in 5 occurrence(s), repeated (up to 3 in one occurrence)
  family py:baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized: in 5 occurrence(s), repeated (up to 7 in one occurrence)
  family py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__: in 5 occurrence(s), once
  family py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import: in 5 occurrence(s), repeated (up to 3 in one occurrence)
  family py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports: in 5 occurrence(s), once
  family py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates: in 5 occurrence(s), repeated (up to 2 in one occurrence)
  family py:baserow.core.registry.ModelRegistryMixin.get_by_model: in 5 occurrence(s), repeated (up to 18 in one occurrence)
  family py:baserow.core.registry.Registry.get: in 5 occurrence(s), repeated (up to 9 in one occurrence)
  family site:br:09962e1ae1b2: in 5 occurrence(s), repeated (up to 3 in one occurrence)
  family site:br:34ec71ee29c9: in 5 occurrence(s), repeated (up to 3 in one occurrence)
  family site:br:47a63ce03fc8: in 5 occurrence(s), repeated (up to 9 in one occurrence)
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies BEFORE py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies BEFORE py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies BEFORE py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies BEFORE py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies BEFORE site:br:09962e1ae1b2  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized BEFORE py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized BEFORE py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized BEFORE py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized BEFORE py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized BEFORE py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized BEFORE site:br:09962e1ae1b2  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE py:baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE py:baserow.core.registry.Registry.get  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE site:br:09962e1ae1b2  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE site:br:34ec71ee29c9  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE site:br:47a63ce03fc8  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized BEFORE py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized BEFORE site:br:09962e1ae1b2  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  py:baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized BEFORE site:br:09962e1ae1b2  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized BEFORE py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized BEFORE site:br:09962e1ae1b2  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized BEFORE site:br:09962e1ae1b2  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized BEFORE py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized BEFORE site:br:09962e1ae1b2  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  py:baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized BEFORE site:br:09962e1ae1b2  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__ BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__ BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__ BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__ BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__ BEFORE py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__ BEFORE py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__ BEFORE py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__ BEFORE py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__ BEFORE py:baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__ BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__ BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__ BEFORE py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__ BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__ BEFORE py:baserow.core.registry.Registry.get  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__ BEFORE site:br:09962e1ae1b2  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__ BEFORE site:br:34ec71ee29c9  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__ BEFORE site:br:47a63ce03fc8  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import BEFORE py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import BEFORE py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import BEFORE py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import BEFORE py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import BEFORE site:br:09962e1ae1b2  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports BEFORE py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports BEFORE py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports BEFORE py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports BEFORE py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports BEFORE site:br:09962e1ae1b2  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates BEFORE py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates BEFORE py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates BEFORE py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates BEFORE site:br:09962e1ae1b2  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.core.registry.Registry.get BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.core.registry.Registry.get BEFORE py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.core.registry.Registry.get BEFORE py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  py:baserow.core.registry.Registry.get BEFORE py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.core.registry.Registry.get BEFORE py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.core.registry.Registry.get BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.core.registry.Registry.get BEFORE py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.core.registry.Registry.get BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.core.registry.Registry.get BEFORE site:br:09962e1ae1b2  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:34ec71ee29c9 BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:34ec71ee29c9 BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:34ec71ee29c9 BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:34ec71ee29c9 BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:34ec71ee29c9 BEFORE py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:34ec71ee29c9 BEFORE py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:34ec71ee29c9 BEFORE py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:34ec71ee29c9 BEFORE py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:34ec71ee29c9 BEFORE py:baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:34ec71ee29c9 BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:34ec71ee29c9 BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:34ec71ee29c9 BEFORE py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:34ec71ee29c9 BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:34ec71ee29c9 BEFORE py:baserow.core.registry.Registry.get  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:34ec71ee29c9 BEFORE site:br:09962e1ae1b2  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:34ec71ee29c9 BEFORE site:br:47a63ce03fc8  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:47a63ce03fc8 BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:47a63ce03fc8 BEFORE py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:47a63ce03fc8 BEFORE py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:47a63ce03fc8 BEFORE py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:47a63ce03fc8 BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:47a63ce03fc8 BEFORE py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:47a63ce03fc8 BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:47a63ce03fc8 BEFORE site:br:09962e1ae1b2  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  REPEATED REGION: py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies, py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized, py:baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized, py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized, py:baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized, py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import, py:baserow.core.registry.Registry.get, site:br:47a63ce03fc8
    each repetition starts with py:baserow.core.registry.Registry.get (up to 9 repetitions in one occurrence); inside one:
      py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized  (32 repetition(s))
      py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import  (11 repetition(s))
      py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies BEFORE site:br:47a63ce03fc8  (43 repetition(s))
      py:baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies  (10 repetition(s))
      py:baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import  (10 repetition(s))
      py:baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized BEFORE site:br:47a63ce03fc8  (10 repetition(s))
      py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies  (1 repetition(s))
      py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import  (1 repetition(s))
      py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized BEFORE site:br:47a63ce03fc8  (1 repetition(s))
      py:baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies  (32 repetition(s))
      py:baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized  (32 repetition(s))
      py:baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized BEFORE site:br:47a63ce03fc8  (32 repetition(s))
      py:baserow.core.registry.Registry.get BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies  (43 repetition(s))
      py:baserow.core.registry.Registry.get BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized  (32 repetition(s))
      py:baserow.core.registry.Registry.get BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized  (10 repetition(s))
      py:baserow.core.registry.Registry.get BEFORE py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized  (1 repetition(s))
      py:baserow.core.registry.Registry.get BEFORE py:baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized  (32 repetition(s))
      py:baserow.core.registry.Registry.get BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import  (11 repetition(s))
      py:baserow.core.registry.Registry.get BEFORE site:br:47a63ce03fc8  (43 repetition(s))
      site:br:47a63ce03fc8 BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized  (32 repetition(s))
      site:br:47a63ce03fc8 BEFORE py:baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import  (11 repetition(s))
  REPEATED REGION: py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized, py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized, py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db, py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized, py:baserow.core.registry.ModelRegistryMixin.get_by_model, site:br:09962e1ae1b2
    each repetition starts with py:baserow.core.registry.ModelRegistryMixin.get_by_model (up to 18 repetitions in one occurrence); inside one:
      py:baserow.core.registry.ModelRegistryMixin.get_by_model BEFORE py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized  (11 repetition(s))
      py:baserow.core.registry.ModelRegistryMixin.get_by_model BEFORE py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized  (18 repetition(s))
      py:baserow.core.registry.ModelRegistryMixin.get_by_model BEFORE py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db  (11 repetition(s))
      py:baserow.core.registry.ModelRegistryMixin.get_by_model BEFORE py:baserow.contrib.database.fields.registries.FieldType.after_import_serialized  (14 repetition(s))
      py:baserow.core.registry.ModelRegistryMixin.get_by_model BEFORE site:br:09962e1ae1b2  (11 repetition(s))
      site:br:09962e1ae1b2 BEFORE py:baserow.contrib.database.fields.models.FormulaField.refresh_from_db  (11 repetition(s))
  REPEATED REGION: site:br:34ec71ee29c9
    each repetition starts with site:br:34ec71ee29c9 (up to 3 repetitions in one occurrence); inside one:
  REPEATED REGION: py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates
    each repetition starts with py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates (up to 2 repetitions in one occurrence); inside one:

inside py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies:
  family py:baserow.contrib.database.fields.field_types.LinkRowFieldType.get_import_dependency_when_referenced: in 7 occurrence(s), once
  family py:baserow.contrib.database.fields.registries.FieldType.get_import_dependency_when_referenced: in 1 occurrence(s), once
  family py:baserow.core.registry.Registry.get: in 8 occurrence(s), once
  family site:br:be7d3ee9e3b1: in 43 occurrence(s), once
  py:baserow.core.registry.Registry.get BEFORE py:baserow.contrib.database.fields.field_types.LinkRowFieldType.get_import_dependency_when_referenced  (all of the first before all of the second;
      7 occurrence(s), 4 execution(s))
  py:baserow.core.registry.Registry.get BEFORE py:baserow.contrib.database.fields.registries.FieldType.get_import_dependency_when_referenced  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:be7d3ee9e3b1 BEFORE py:baserow.contrib.database.fields.field_types.LinkRowFieldType.get_import_dependency_when_referenced  (all of the first before all of the second;
      7 occurrence(s), 4 execution(s))
  site:br:be7d3ee9e3b1 BEFORE py:baserow.contrib.database.fields.registries.FieldType.get_import_dependency_when_referenced  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))
  site:br:be7d3ee9e3b1 BEFORE py:baserow.core.registry.Registry.get  (all of the first before all of the second;
      8 occurrence(s), 5 execution(s))

inside py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized:
  family py:baserow.contrib.database.fields.field_cache.FieldCache.__init__: in 11 occurrence(s), once
  family py:baserow.core.registry.ModelRegistryMixin.get_by_model: in 11 occurrence(s), repeated (up to 4 in one occurrence)
  family py:baserow.core.registry.Registry.get: in 43 occurrence(s), repeated (up to 4 in one occurrence)
  family site:br:3f16965dcd1f: in 43 occurrence(s), once
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      11 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.fields.field_cache.FieldCache.__init__ BEFORE site:br:3f16965dcd1f  (all of the first before all of the second;
      11 occurrence(s), 5 execution(s))
  py:baserow.core.registry.ModelRegistryMixin.get_by_model BEFORE site:br:3f16965dcd1f  (all of the first before all of the second;
      11 occurrence(s), 5 execution(s))
  py:baserow.core.registry.Registry.get BEFORE site:br:3f16965dcd1f  (all of the first before all of the second;
      43 occurrence(s), 5 execution(s))
  REPEATED REGION: py:baserow.contrib.database.fields.field_cache.FieldCache.__init__, py:baserow.core.registry.ModelRegistryMixin.get_by_model, py:baserow.core.registry.Registry.get
    (no member starts every repetition: only membership is known)

inside py:baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized:
  family py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields: in 5 occurrence(s), once
  family py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates: in 5 occurrence(s), once
  family py:baserow.core.registry.ModelRegistryMixin.get_by_model: in 5 occurrence(s), repeated (up to 35 in one occurrence)
  family py:baserow.core.registry.Registry.get: in 5 occurrence(s), repeated (up to 27 in one occurrence)
  family site:br:097a2673dd80: in 5 occurrence(s), once
  family site:br:118aa1d180ae: in 5 occurrence(s), once
  family site:br:1824a795083c: in 5 occurrence(s), once
  family site:br:2c3f0aee6188: in 5 occurrence(s), once
  family site:br:941534890084: in 5 occurrence(s), once
  family site:br:f16213112383: in 5 occurrence(s), once
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields BEFORE py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields BEFORE py:baserow.core.registry.Registry.get  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:097a2673dd80 BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:097a2673dd80 BEFORE py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:097a2673dd80 BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:097a2673dd80 BEFORE py:baserow.core.registry.Registry.get  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:097a2673dd80 BEFORE site:br:118aa1d180ae  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:097a2673dd80 BEFORE site:br:1824a795083c  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:097a2673dd80 BEFORE site:br:2c3f0aee6188  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:097a2673dd80 BEFORE site:br:941534890084  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:097a2673dd80 BEFORE site:br:f16213112383  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:118aa1d180ae BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:118aa1d180ae BEFORE py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:118aa1d180ae BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:118aa1d180ae BEFORE py:baserow.core.registry.Registry.get  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:118aa1d180ae BEFORE site:br:2c3f0aee6188  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:1824a795083c BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:1824a795083c BEFORE py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:1824a795083c BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:1824a795083c BEFORE py:baserow.core.registry.Registry.get  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:1824a795083c BEFORE site:br:118aa1d180ae  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:1824a795083c BEFORE site:br:2c3f0aee6188  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:1824a795083c BEFORE site:br:941534890084  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:1824a795083c BEFORE site:br:f16213112383  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:2c3f0aee6188 BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:2c3f0aee6188 BEFORE py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:2c3f0aee6188 BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:2c3f0aee6188 BEFORE py:baserow.core.registry.Registry.get  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:941534890084 BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:941534890084 BEFORE py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:941534890084 BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:941534890084 BEFORE py:baserow.core.registry.Registry.get  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:941534890084 BEFORE site:br:118aa1d180ae  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:941534890084 BEFORE site:br:2c3f0aee6188  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:f16213112383 BEFORE py:baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:f16213112383 BEFORE py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:f16213112383 BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:f16213112383 BEFORE py:baserow.core.registry.Registry.get  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:f16213112383 BEFORE site:br:118aa1d180ae  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:f16213112383 BEFORE site:br:2c3f0aee6188  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  site:br:f16213112383 BEFORE site:br:941534890084  (all of the first before all of the second;
      5 occurrence(s), 5 execution(s))
  REPEATED REGION: py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates, py:baserow.core.registry.ModelRegistryMixin.get_by_model, py:baserow.core.registry.Registry.get
    (no member starts every repetition: only membership is known)

inside py:baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized:
  family py:baserow.core.registry.ModelRegistryMixin.get_by_model: in 11 occurrence(s), repeated (up to 5 in one occurrence)
  family py:baserow.core.registry.Registry.get: in 11 occurrence(s), repeated (up to 3 in one occurrence)
  REPEATED REGION: py:baserow.core.registry.ModelRegistryMixin.get_by_model, py:baserow.core.registry.Registry.get
    (no member starts every repetition: only membership is known)

inside py:baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized:
  family py:baserow.core.registry.ModelRegistryMixin.get_by_model: in 18 occurrence(s), repeated (up to 2 in one occurrence)
  family site:br:e01cacc8ce73: in 18 occurrence(s), once
  site:br:e01cacc8ce73 BEFORE py:baserow.core.registry.ModelRegistryMixin.get_by_model  (all of the first before all of the second;
      18 occurrence(s), 5 execution(s))
  REPEATED REGION: py:baserow.core.registry.ModelRegistryMixin.get_by_model
    each repetition starts with py:baserow.core.registry.ModelRegistryMixin.get_by_model (up to 2 repetitions in one occurrence); inside one:

inside py:baserow.contrib.database.fields.field_types.LinkRowFieldType.get_import_dependency_when_referenced:
  family site:br:a0d4e306fb5a: in 7 occurrence(s), once
  family site:br:f960d9f63045: in 7 occurrence(s), once
  site:br:a0d4e306fb5a BEFORE site:br:f960d9f63045  (all of the first before all of the second;
      7 occurrence(s), 4 execution(s))

inside py:baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized:
  family site:br:b0d9d883d08b: in 1 occurrence(s), once
  family site:br:df188b1f6d10: in 1 occurrence(s), once
  site:br:df188b1f6d10 BEFORE site:br:b0d9d883d08b  (all of the first before all of the second;
      1 occurrence(s), 1 execution(s))

inside py:baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates:
  family site:br:b4a2eadbfca3: in 2 occurrence(s), once
  family site:br:dce56a309d5c: in 2 occurrence(s), repeated (up to 2 in one occurrence)
  site:br:dce56a309d5c BEFORE site:br:b4a2eadbfca3  (all of the first before all of the second;
      2 occurrence(s), 1 execution(s))
  REPEATED REGION: site:br:dce56a309d5c
    each repetition starts with site:br:dce56a309d5c (up to 2 repetitions in one occurrence); inside one:
```

## Mechanics (deterministic, intra-procedural)

### baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields  (backend/src/baserow/contrib/database/application_types.py)
- site br:34ec71ee29c9 line 456: `serialized_field['primary']` | operands: serialized_field ← unknown:UNKNOWN_DEPENDENCE:loop-variable | requires: ?loop & ?loop | then exits: False, else exits: False
- site br:47a63ce03fc8 line 532: `field_deps` | operands: field_deps ← call:_expand_implied_import_dependencies | requires: ?loop & ?loop | then exits: False, else exits: False
- site br:09962e1ae1b2 line 589: `field_type.needs_refresh_after_import_serialized` | operands: field_type.needs_refresh_after_import_serialized ← call:field_type_registry.get_by_model.needs_refresh_after_import_serialized | requires: ?loop & ?loop | then exits: False, else exits: False
- call `FieldCache` line 445 requires: —
- call `DeferredFieldImporter` line 447 requires: —
- call `field_type_registry.get` line 518 requires: ?loop & ?loop
- call `field_type.get_field_depdendencies_before_import_serialized` line 520 requires: ?loop & ?loop
- call `_expand_implied_import_dependencies` line 526 requires: ?loop & ?loop
- call `partial` line 533 requires: ?loop & ?loop & br:47a63ce03fc8=T
- call `deferred_field_importer.add_deferred_field_import` line 537 requires: ?loop & ?loop & br:47a63ce03fc8=T
- call `_import_field_serialized` line 545 requires: ?loop & ?loop & br:47a63ce03fc8=F
- call `fields_without_dependencies.append` line 548 requires: ?loop & ?loop & br:47a63ce03fc8=F
- call `deferred_field_importer.run_deferred_field_imports` line 552 requires: —
- call `deferred_fk_update_collector.run_deferred_fk_updates` line 556 requires: —
- call `field_type_registry.get` line 561 requires: ?loop
- call `field_type.import_serialized` line 562 requires: ?loop
- call `SearchHandler.schedule_update_search_data` line 569 requires: ?loop
- call `progress.increment` line 572 requires: ?loop
- call `deferred_fk_update_collector.run_deferred_fk_updates` line 574 requires: —
- call `field_type_registry.get_by_model` line 581 requires: ?loop
- call `field_type.after_import_serialized` line 582 requires: ?loop
- call `table_fields_by_name.values` line 586 requires: —
- call `table_fields.values` line 587 requires: ?loop
- call `field_type_registry.get_by_model` line 588 requires: ?loop & ?loop
- call `field_instance.refresh_from_db` line 590 requires: ?loop & ?loop & br:09962e1ae1b2=T
- call `ImportedFields` line 592 requires: —

### baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized  (backend/src/baserow/contrib/database/application_types.py)
- site br:3f16965dcd1f line 480: `table_instance not in table_fields_by_name` | operands: table_fields_by_name ← closure:table_fields_by_name; table_instance ← param:serialized_table | requires: — | then exits: False, else exits: False
- call `field_type_registry.get` line 471 requires: —
- call `field_type.import_serialized` line 472 requires: —
- call `serialized_table['field_instances'].append` line 479 requires: —
- call `progress.increment` line 484 requires: —

### baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies  (backend/src/baserow/contrib/database/application_types.py)
- site br:be7d3ee9e3b1 line 497: `not field_deps` | operands: field_deps ← param:field_deps | requires: — | then exits: True, else exits: False
- call `set` line 500 requires: br:be7d3ee9e3b1=F
- call `fields_by_name.get` line 502 requires: br:be7d3ee9e3b1=F & ?loop
- call `field_type_registry.get` line 503 requires: br:be7d3ee9e3b1=F & ?loop
- call `field_type_registry.get(referenced['type']).get_import_dependency_when_reference` line 503 requires: br:be7d3ee9e3b1=F & ?loop
- call `expanded.add` line 508 requires: br:be7d3ee9e3b1=F & ?loop

### baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized  (backend/src/baserow/contrib/database/application_types.py)
- site br:097a2673dd80 line 640: `'import_workspace_id' not in id_mapping and database.workspace is not None` | operands: database.workspace ← param:database.workspace; id_mapping ← param:id_mapping | requires: — | then exits: False, else exits: False
- site br:1824a795083c line 643: `'database_tables' not in id_mapping` | operands: id_mapping ← param:id_mapping | requires: — | then exits: False, else exits: False
- site br:f16213112383 line 646: `'database_fields' not in id_mapping` | operands: id_mapping ← param:id_mapping | requires: — | then exits: False, else exits: False
- site br:941534890084 line 649: `'database_field_names' not in id_mapping` | operands: id_mapping ← param:id_mapping | requires: — | then exits: False, else exits: False
- site br:118aa1d180ae line 652: `'workspace_id' not in id_mapping and database.workspace is not None` | operands: database.workspace ← param:database.workspace; id_mapping ← param:id_mapping | requires: — | then exits: False, else exits: False
- site br:2c3f0aee6188 line 667: `workspace_id_for_user_references` | operands: workspace_id_for_user_references ← call:id_mapping.get, param:id_mapping, param:import_export_config.workspace_for_user_references, param:import_export_config.workspace_for_user_references.id | requires: — | then exits: False, else exits: False
- call `self._ops_count_for_import_tables_serialized` line 635 requires: —
- call `ChildProgressBuilder.build` line 638 requires: —
- call `id_mapping.get` line 663 requires: —
- call `CoreHandler.get_user_email_mapping` line 668 requires: br:2c3f0aee6188=T
- call `self._import_tables` line 674 requires: —
- call `DeferredForeignKeyUpdater` line 678 requires: —
- call `self._import_table_fields` line 682 requires: —
- call `set` line 697 requires: —
- call `self._import_table_views` line 701 requires: ?loop
- call `self._create_table_schema` line 704 requires: ?loop
- call `progress.increment` line 707 requires: ?loop
- call `self._import_table_rows` line 713 requires: —
- call `self._import_extra_metadata` line 727 requires: —
- call `self._import_data_sync` line 729 requires: —
- call `self._import_field_rules` line 731 requires: —

### baserow.contrib.database.fields.field_cache.FieldCache.__init__  (backend/src/baserow/contrib/database/fields/field_cache.py)
- site br:0c9c7e593f44 line 23: `existing_cache is not None` | operands: existing_cache ← param:existing_cache | requires: — | then exits: False, else exits: False
- site br:9153cd1aa08c line 32: `existing_model is not None` | operands: existing_model ← param:existing_model | requires: — | then exits: False, else exits: False
- call `defaultdict` line 29 requires: br:0c9c7e593f44=F
- call `self.cache_model` line 33 requires: br:9153cd1aa08c=T

### baserow.contrib.database.fields.field_types.LinkRowFieldType.after_import_serialized  (backend/src/baserow/contrib/database/fields/field_types.py)
- site br:e01cacc8ce73 line 3613: `field.link_row_related_field` | operands: field.link_row_related_field ← param:field.link_row_related_field | requires: — | then exits: False, else exits: False
- call `FieldDependencyHandler.rebuild_dependencies` line 3614 requires: br:e01cacc8ce73=T
- call `FieldDependencyHandler.rebuild_dependencies` line 3617 requires: —

### baserow.contrib.database.fields.field_types.LinkRowFieldType.get_import_dependency_when_referenced  (backend/src/baserow/contrib/database/fields/field_types.py)
- site br:a0d4e306fb5a line 3710: `related_table_id is None or related_table_id not in primary_table_fields_map` | operands: primary_table_fields_map ← param:primary_table_fields_map; related_table_id ← call:serialized_field.get | requires: — | then exits: True, else exits: False
- site br:f960d9f63045 line 3714: `primary_field_id not in serialized_fields_map` | operands: primary_field_id ← call:serialized_field.get, param:primary_table_fields_map; serialized_fields_map ← param:serialized_fields_map | requires: br:a0d4e306fb5a=F | then exits: True, else exits: False
- call `serialized_field.get` line 3706 requires: —

### baserow.contrib.database.fields.field_types.FormulaFieldType.after_import_serialized  (backend/src/baserow/contrib/database/fields/field_types.py)
- call `field.save` line 6147 requires: —
- call `FieldDependencyHandler.rebuild_dependencies` line 6148 requires: —

### baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized  (backend/src/baserow/contrib/database/fields/field_types.py)
- site br:49c2edb05730 line 6249: `'formula' not in serialized_field` | operands: serialized_field ← param:serialized_field | requires: — | then exits: True, else exits: False
- call `NotImplementedError` line 6250 requires: br:49c2edb05730=T
- call `FormulaHandler.get_dependencies_field_names` line 6254 requires: br:49c2edb05730=F

### baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized  (backend/src/baserow/contrib/database/fields/field_types.py)
- site br:df188b1f6d10 line 6942: `through_field_id is None or through_field_id not in serialized_fields_map` | operands: serialized_fields_map ← param:serialized_fields_map; through_field_id ← call:serialized_field.get | requires: — | then exits: True, else exits: False
- site br:b0d9d883d08b line 6951: `target_field_id is None or target_field_id not in serialized_fields_map` | operands: serialized_fields_map ← param:serialized_fields_map; target_field_id ← call:serialized_field.get | requires: br:df188b1f6d10=F | then exits: True, else exits: False
- call `serialized_field.get` line 6941 requires: —
- call `serialized_field.get` line 6947 requires: br:df188b1f6d10=F

### baserow.contrib.database.fields.models.FormulaField.refresh_from_db  (backend/src/baserow/contrib/database/fields/models.py)
- call `super` line 788 requires: —
- call `super().refresh_from_db` line 788 requires: —
- call `self.clear_cached_properties` line 789 requires: —

### baserow.contrib.database.fields.registries.FieldType.after_import_serialized  (backend/src/baserow/contrib/database/fields/registries.py)

### baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized  (backend/src/baserow/contrib/database/fields/registries.py)

### baserow.contrib.database.fields.registries.FieldType.get_import_dependency_when_referenced  (backend/src/baserow/contrib/database/fields/registries.py)

### baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__  (backend/src/baserow/contrib/database/fields/utils/deferred_field_importer.py)

### baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import  (backend/src/baserow/contrib/database/fields/utils/deferred_field_importer.py)
- call `self._unique_field_name` line 46 requires: —

### baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports  (backend/src/baserow/contrib/database/fields/utils/deferred_field_importer.py)
- call `self.get_all_fields_dependencies` line 110 requires: —
- call `FieldDependencyHandler.group_dependencies_by_level` line 114 requires: —
- call `import_field_callback` line 125 requires: ?loop & ?loop
- call `imported_fields.append` line 126 requires: ?loop & ?loop

### baserow.contrib.database.fields.utils.deferred_foreign_key_updater.DeferredForeignKeyUpdater.run_deferred_fk_updates  (backend/src/baserow/contrib/database/fields/utils/deferred_foreign_key_updater.py)
- site br:dce56a309d5c line 54: `desired_field_id and run_mapping_key == mapping_key` | operands: desired_field_id ← unknown:UNKNOWN_DEPENDENCE:loop-variable; mapping_key ← unknown:UNKNOWN_DEPENDENCE:loop-variable; run_mapping_key ← param:run_mapping_key | requires: ?loop & ?loop | then exits: False, else exits: False
- site br:b4a2eadbfca3 line 64: `len(fields_to_bulk_update) > 0` | operands: fields_to_bulk_update ← const | requires: ?loop | then exits: False, else exits: False
- call `self.deferred_field_fk_updates_per_model_class.items` line 45 requires: —
- call `set` line 47 requires: ?loop
- call `fields_to_bulk_update.setdefault` line 55 requires: ?loop & ?loop & br:dce56a309d5c=T
- call `attr_names.add` line 58 requires: ?loop & ?loop & br:dce56a309d5c=T
- call `id_mapping.get` line 62 requires: ?loop & ?loop & br:dce56a309d5c=T
- call `id_mapping.get(mapping_key, {}).get` line 62 requires: ?loop & ?loop & br:dce56a309d5c=T
- call `setattr` line 59 requires: ?loop & ?loop & br:dce56a309d5c=T
- call `len` line 64 requires: ?loop
- call `fields_to_bulk_update.values` line 66 requires: ?loop & br:b4a2eadbfca3=T
- call `field_model_class.objects.bulk_update` line 65 requires: ?loop & br:b4a2eadbfca3=T

### baserow.core.registry.Registry.get  (backend/src/baserow/core/registry.py)
- site br:47fec536a3c0 line 785: `type_name not in self.registry` | operands: self.registry ← param:self.registry; type_name ← param:type_name | requires: — | then exits: False, else exits: False
- site br:2efe40b1c58a line 789: `type_name_via_compat` | operands: type_name_via_compat ← call:self.get_by_type_name_by_compat | requires: br:47fec536a3c0=T | then exits: False, else exits: True
- call `self.get_by_type_name_by_compat` line 788 requires: br:47fec536a3c0=T
- call `self.does_not_exist_exception_class` line 792 requires: br:47fec536a3c0=T & br:2efe40b1c58a=F

### baserow.core.registry.ModelRegistryMixin.get_by_model  (backend/src/baserow/core/registry.py)
- site br:ca2997a425e6 line 903: `isinstance(model_instance, type)` | operands: model_instance ← param:model_instance; type ← global:type | requires: — | then exits: False, else exits: False
- call `isinstance` line 903 requires: —
- call `self.get_for_class` line 908 requires: —

## Observed event logs

Calls of the listed functions in chronological order, indented by depth among them, with argument shapes and value digests, results, exits, and the observed outcome of every decision site evaluated in those calls.

```
### tests/baserow/contrib/database/field/dependencies/test_field_dependency_handler.py::test_can_import_database_with_formula_dependencies  test: passed  exits: baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields returned; baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized returned; baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies returned; baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies returned; baserow.contrib.database.fields.registries.FieldType.get_import_dependency_when_referenced returned; baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized returned
call baserow.contrib.database.application_types.DatabaseApplicationType.import_tables_serialized(database=Database, serialized_tables=list[2], id_mapping=dict[0]#2e6f38, import_export_config=ImportExportConfig#bbc10d, files_zip=NoneType#99bf08, storage=NoneType#99bf08, progress_builder=NoneType#99bf08) [returned]
  branch br:097a2673dd80 `'import_workspace_id' not in id_mapping and database.workspace is not ` = T
  branch br:1824a795083c `'database_tables' not in id_mapping` = T
  branch br:f16213112383 `'database_fields' not in id_mapping` = T
  branch br:941534890084 `'database_field_names' not in id_mapping` = T
  branch br:118aa1d180ae `'workspace_id' not in id_mapping and database.workspace is not None` = T
  branch br:2c3f0aee6188 `workspace_id_for_user_references` = T
  call baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields(serialized_tables=list[2], id_mapping=dict[5]#b597f6, import_export_config=ImportExportConfig#bbc10d, external_table_fields_to_import=NoneType#99bf08, deferred_fk_update_collector=DeferredForeignKeyUpdater, progress=Progress) [returned]
    call baserow.contrib.database.fields.field_cache.FieldCache.__init__(existing_cache=NoneType#99bf08, existing_model=NoneType#99bf08) [returned] -> #99bf08
      branch br:0c9c7e593f44 `existing_cache is not None` = F
    call baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.__init__() [returned] -> #99bf08
    branch br:34ec71ee29c9 `serialized_field['primary']` = T
    branch br:34ec71ee29c9 `serialized_field['primary']` = T
    call baserow.core.registry.Registry.get(type_name=str#006842) [returned]
      branch br:47fec536a3c0 `type_name not in self.registry` = F
    call baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[6]#cd2376, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #99bf08
    call baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[4]#291c15) [returned] -> #99bf08
      branch br:be7d3ee9e3b1 `not field_deps` = T
    branch br:47a63ce03fc8 `field_deps` = F
    call baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[6]#cd2376) [returned]
      call baserow.core.registry.Registry.get(type_name=str#006842) [returned]
        branch br:47fec536a3c0 `type_name not in self.registry` = F
      branch br:3f16965dcd1f `table_instance not in table_fields_by_name` = T
    call baserow.core.registry.Registry.get(type_name=str#c2f755) [returned]
      branch br:47fec536a3c0 `type_name not in self.registry` = F
    call baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[8]#44a32e, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #c66ae3
      branch br:49c2edb05730 `'formula' not in serialized_field` = F
    call baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=set[1]#c66ae3, fields_by_name=dict[4]#291c15) [returned] -> #c66ae3
      branch br:be7d3ee9e3b1 `not field_deps` = F
      call baserow.core.registry.Registry.get(type_name=str#006842) [returned]
        branch br:47fec536a3c0 `type_name not in self.registry` = F
      call baserow.contrib.database.fields.registries.FieldType.get_import_dependency_when_referenced(serialized_field=dict[6]#5a1d44, reference_name=str#006842, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #99bf08
    branch br:47a63ce03fc8 `field_deps` = T
    call baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import(table=Table, field_name=str#c2f755, field_dependencies=set[1]#c66ae3, import_field_callback=partial) [returned] -> #99bf08
    call baserow.core.registry.Registry.get(type_name=str#006842) [returned]
      branch br:47fec536a3c0 `type_name not in self.registry` = F
    call baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[6]#5a1d44, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #99bf08
    call baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[4]#291c15) [returned] -> #99bf08
      branch br:be7d3ee9e3b1 `not field_deps` = T
    branch br:47a63ce03fc8 `field_deps` = F
    call baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[6]#5a1d44) [returned]
      call baserow.core.registry.Registry.get(type_name=str#006842) [returned]
        branch br:47fec536a3c0 `type_name not in self.registry` = F
      branch br:3f16965dcd1f `table_instance not in table_fields_by_name` = F
    call baserow.core.registry.Registry.get(type_name=str#b742b2) [returned]
      branch br:47fec536a3c0 `type_name not in self.registry` = F
    call baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[8]#c3fc04, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #99bf08
    call baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[4]#291c15) [returned] -> #99bf08
      branch br:be7d3ee9e3b1 `not field_deps` = T
    branch br:47a63ce03fc8 `field_deps` = F
    call baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[8]#c3fc04) [returned]
      call baserow.core.registry.Registry.get(type_name=str#b742b2) [returned]
        branch br:47fec536a3c0 `type_name not in self.registry` = F
      branch br:3f16965dcd1f `table_instance not in table_fields_by_name` = F
    call baserow.core.registry.Registry.get(type_name=str#006842) [returned]
      branch br:47fec536a3c0 `type_name not in self.registry` = F
    call baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[6]#a3ead1, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #99bf08
    call baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[4]#8d7b81) [returned] -> #99bf08
      branch br:be7d3ee9e3b1 `not field_deps` = T
    branch br:47a63ce03fc8 `field_deps` = F
    call baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[6]#a3ead1) [returned]
      call baserow.core.registry.Registry.get(type_name=str#006842) [returned]
        branch br:47fec536a3c0 `type_name not in self.registry` = F
      branch br:3f16965dcd1f `table_instance not in table_fields_by_name` = T
    call baserow.core.registry.Registry.get(type_name=str#c2f755) [returned]
      branch br:47fec536a3c0 `type_name not in self.registry` = F
    call baserow.contrib.database.fields.field_types.FormulaFieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[9]#f40287, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #edecd0
      branch br:49c2edb05730 `'formula' not in serialized_field` = F
    call baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=set[1]#edecd0, fields_by_name=dict[4]#8d7b81) [returned] -> #edecd0
      branch br:be7d3ee9e3b1 `not field_deps` = F
    branch br:47a63ce03fc8 `field_deps` = T
    call baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import(table=Table, field_name=str#de0c67, field_dependencies=set[1]#edecd0, import_field_callback=partial) [returned] -> #99bf08
    call baserow.core.registry.Registry.get(type_name=str#b742b2) [returned]
      branch br:47fec536a3c0 `type_name not in self.registry` = F
    call baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[8]#9c3aa8, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #99bf08
    call baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[4]#8d7b81) [returned] -> #99bf08
      branch br:be7d3ee9e3b1 `not field_deps` = T
    branch br:47a63ce03fc8 `field_deps` = F
    call baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[8]#9c3aa8) [returned]
      call baserow.core.registry.Registry.get(type_name=str#b742b2) [returned]
        branch br:47fec536a3c0 `type_name not in self.registry` = F
      branch br:3f16965dcd1f `table_instance not in table_fields_by_name` = F
    call baserow.core.registry.Registry.get(type_name=str#de0c67) [returned]
      branch br:47fec536a3c0 `type_name not in self.registry` = F
    call baserow.contrib.database.fields.field_types.LookupFieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[10]#fa755d, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #ae7de4
      branch br:df188b1f6d10 `through_field_id is None or through_field_id not in serialized_fields_` = F
      branch br:b0d9d883d08b `target_field_id is None or target_field_id not in serialized_fields_ma` = F
    call baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=set[1]#ae7de4, fields_by_name=dict[4]#8d7b81) [returned] -> #ae7de4
      branch br:be7d3ee9e3b1 `not field_deps` = F
    branch br:47a63ce03fc8 `field_deps` = T
    call baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.add_deferred_field_import(table=Table, field_name=str#1ff959, field_dependencies=set[1]#ae7de4, import_field_callback=partial) [returned] -> #99bf08
    call baserow.contrib.database.fields.utils.deferred_field_importer.DeferredFieldImporter.run_deferred_field_imports(field_name_fields_mapping=dict[2]) [returned]
      call baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[8]#44a32e) [returned]
        call baserow.core.registry.Registry.get(type_name=str#c2f755) [returned]
          branch br:47fec536a3c0 `type_name not in self.registry` = F
        call baserow.contrib.database.fields.field_cache.FieldCache.__init__(existing_cache=NoneType#99bf08, existing_model=NoneType#99bf08) [returned] -> #99bf08
          branch br:0c9c7e593f44 `existing_cache is not None` = F
        call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=TextField) [returned]
          branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
        call baserow.core.registry.Registry.get(type_name=str#48a309) [returned]
          branch br:47fec536a3c0 `type_name not in self.registry` = F
        branch br:3f16965dcd1f `table_instance not in table_fields_by_name` = F
      call baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[9]#f40287) [returned]
        call baserow.core.registry.Registry.get(type_name=str#c2f755) [returned]
          branch br:47fec536a3c0 `type_name not in self.registry` = F
        call baserow.contrib.database.fields.field_cache.FieldCache.__init__(existing_cache=NoneType#99bf08, existing_model=NoneType#99bf08) [returned] -> #99bf08
          branch br:0c9c7e593f44 `existing_cache is not None` = F
        call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=LinkRowField) [returned]
          branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
        call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=TextField) [returned]
          branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
        call baserow.core.registry.Registry.get(type_name=str#06dfa3) [returned]
          branch br:47fec536a3c0 `type_name not in self.registry` = F
        call baserow.core.registry.Registry.get(type_name=str#48a309) [returned]
          branch br:47fec536a3c0 `type_name not in self.registry` = F
        branch br:3f16965dcd1f `table_instance not in table_fields_by_name` = F
      call baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[10]#fa755d) [returned]
        call baserow.core.registry.Registry.get(type_name=str#de0c67) [returned]
          branch br:47fec536a3c0 `type_name not in self.registry` = F
        call baserow.contrib.database.fields.field_cache.FieldCache.__init__(existing_cache=NoneType#99bf08, existing_model=NoneType#99bf08) [returned] -> #99bf08
... (255 more events)

### tests/baserow/core/snapshots/test_snapshot_array_formula_import.py::test_duplicate_application_with_implicit_array_primary_dependency  test: passed  exits: baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields returned; baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized returned; baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies returned; baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized returned; baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies returned; baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies returned
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=TextField) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=TextField) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=TextField) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=BooleanField) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#3f8995) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#d4bb61) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#c8029e) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#6e4f93) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#0eb0c1) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#139cb0) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b1a37d) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#573155) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#3f8995) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#3c0069) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#a34e6f) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#15d62e) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b93fa6) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#d18dee) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#81b921) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#6c8da3) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b742b2) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#3f8995) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#d4bb61) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#c8029e) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#6e4f93) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#0eb0c1) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#139cb0) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b1a37d) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#573155) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#3f8995) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#3c0069) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#a34e6f) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#15d62e) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b93fa6) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#d18dee) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
... (2285 more events)

### tests/baserow/core/snapshots/test_snapshot_array_formula_import.py::test_snapshot_with_explicit_array_primary_dependency  test: passed  exits: baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields returned; baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized returned; baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies returned; baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized returned; baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies returned; baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies returned
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=TextField) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=TextField) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=TextField) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=BooleanField) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#3f8995) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#d4bb61) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#c8029e) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#6e4f93) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#0eb0c1) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#139cb0) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b1a37d) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#573155) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#3f8995) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#3c0069) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#a34e6f) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#15d62e) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b93fa6) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#d18dee) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#81b921) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#6c8da3) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b742b2) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#3f8995) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#d4bb61) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#c8029e) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#6e4f93) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#0eb0c1) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#139cb0) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b1a37d) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#573155) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#3f8995) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#3c0069) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#a34e6f) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#15d62e) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b93fa6) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#d18dee) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
... (2278 more events)

### tests/baserow/core/snapshots/test_snapshot_array_formula_import.py::test_snapshot_with_implicit_array_primary_dependency  test: passed  exits: baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields returned; baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized returned; baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies returned; baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized returned; baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies returned; baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies returned
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=TextField) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=TextField) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=TextField) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=BooleanField) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#3f8995) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#d4bb61) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#c8029e) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#6e4f93) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#0eb0c1) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#139cb0) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b1a37d) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#573155) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#3f8995) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#3c0069) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#a34e6f) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#15d62e) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b93fa6) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#d18dee) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#81b921) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#6c8da3) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b742b2) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#3f8995) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#d4bb61) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#c8029e) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#6e4f93) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#0eb0c1) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#139cb0) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b1a37d) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#573155) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#3f8995) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#3c0069) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#a34e6f) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#15d62e) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b93fa6) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#d18dee) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
... (2283 more events)

### tests/baserow/core/snapshots/test_snapshot_array_formula_import.py::test_snapshot_with_implicit_array_primary_dependency_two_links_deep  test: passed  exits: baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields returned; baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized returned; baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies returned; baserow.contrib.database.fields.registries.FieldType.get_field_depdendencies_before_import_serialized returned; baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies returned; baserow.contrib.database.application_types.DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies returned
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=TextField) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=TextField) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=TextField) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#3f8995) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#d4bb61) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#c8029e) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#6e4f93) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#0eb0c1) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#139cb0) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b1a37d) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#573155) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#3f8995) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#3c0069) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#a34e6f) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#15d62e) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b93fa6) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#d18dee) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#81b921) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#6c8da3) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b742b2) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#3f8995) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#d4bb61) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#c8029e) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#6e4f93) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#0eb0c1) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#139cb0) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b1a37d) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#573155) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#3f8995) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.Registry.get(type_name=str#3c0069) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#a34e6f) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#15d62e) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#b93fa6) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#d18dee) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
call baserow.core.registry.ModelRegistryMixin.get_by_model(model_instance=User) [returned]
  branch br:ca2997a425e6 `isinstance(model_instance, type)` = F
call baserow.core.registry.Registry.get(type_name=str#6c8da3) [returned]
  branch br:47fec536a3c0 `type_name not in self.registry` = F
... (2114 more events)
```

## The change (git diff e9ef2697baf8d6967e254b468bf82483de121e68..70c81307d3b6b4951f82cac65cc7779462c026ac, the files shown below)

```diff
diff --git a/backend/src/baserow/contrib/database/application_types.py b/backend/src/baserow/contrib/database/application_types.py
index 406301204..52df49d19 100755
--- a/backend/src/baserow/contrib/database/application_types.py
+++ b/backend/src/baserow/contrib/database/application_types.py
@@ -464,62 +464,90 @@ class DatabaseApplicationType(ApplicationType):
         def _import_field_serialized(serialized_table, serialized_field):
             """
             Create the field instance and add it to the table_fields_by_name mapping.
             The logic is wrapped in a function to allow using it for deferred imports.
             """
 
             table_instance = serialized_table["_object"]
             field_type = field_type_registry.get(serialized_field["type"])
             field_instance = field_type.import_serialized(
                 table_instance,
                 serialized_field,
                 import_export_config,
                 id_mapping,
                 deferred_fk_update_collector,
             )
             serialized_table["field_instances"].append(field_instance)
             if table_instance not in table_fields_by_name:
                 table_fields_by_name[table_instance] = {}
             table_fields_by_name[table_instance][field_instance.name] = field_instance
             table_name = serialized_table["name"]
             progress.increment(
                 state=f"{IMPORT_SERIALIZED_IMPORTING_TABLE_STRUCTURE}{table_name}"
             )
             return field_instance
 
+        def _expand_implied_import_dependencies(field_deps, fields_by_name):
+            """
+            A dependency of `(name, None)` is a reference by name to a field in the
+            same table. Some field types, like `link_row`, render a value borrowed
+            from another table, so referencing them implies a dependency on that
+            other field instead. Let each referenced field type say so.
+            """
+
+            if not field_deps:
+                return field_deps
+
+            expanded = set()
+            for name, via in field_deps:
+                referenced = fields_by_name.get(name) if via is None else None
+                implied = referenced and field_type_registry.get(
+                    referenced["type"]
+                ).get_import_dependency_when_referenced(
+                    referenced, name, database_fields_map, primary_table_fields_map
+                )
+                expanded.add(implied or (name, via))
+            return expanded
+
         fields_without_dependencies: List[Field] = []
         for serialized_table in serialized_tables:
             table_instance = serialized_table["_object"]
+            serialized_fields_by_name = {
+                f["name"]: f for f in serialized_table["fields"]
+            }
             for serialized_field in serialized_table["fields"]:
                 field_type = field_type_registry.get(serialized_field["type"])
                 field_deps = (
                     field_type.get_field_depdendencies_before_import_serialized(
                         serialized_field,
-                        id_mapping["database_fields_map"],
-                        id_mapping["primary_table_fields_map"],
+                        database_fields_map,
+                        primary_table_fields_map,
                     )
                 )
+                field_deps = _expand_implied_import_dependencies(
+                    field_deps, serialized_fields_by_name
+                )
 
                 # If the field has dependencies, we want to defer the import of the
                 # field until all the dependencies have been imported.
                 if field_deps:
                     import_field_callback = partial(
                         _import_field_serialized, serialized_table, serialized_field
                     )
 
                     deferred_field_importer.add_deferred_field_import(
                         table_instance,
                         serialized_field["name"],
                         field_deps,
                         import_field_callback,
                     )
                 else:
                     # If the field has no dependencies, we can import it right away.
                     field_instance = _import_field_serialized(
                         serialized_table, serialized_field
                     )
                     fields_without_dependencies.append(field_instance)
 
         # Now that we have all the fields and their dependencies we can import all the
         # remaining fields in the correct order.
         fields_with_dependencies = deferred_field_importer.run_deferred_field_imports(
             id_mapping["database_field_names"]
diff --git a/backend/src/baserow/contrib/database/fields/field_types.py b/backend/src/baserow/contrib/database/fields/field_types.py
index c37655e0e..2af36bafe 100755
--- a/backend/src/baserow/contrib/database/fields/field_types.py
+++ b/backend/src/baserow/contrib/database/fields/field_types.py
@@ -3671,50 +3671,73 @@ class LinkRowFieldType(
             return related_field_type.to_baserow_formula_type(primary_field)
 
     def to_baserow_formula_expression(
         self, field
     ) -> BaserowExpression[BaserowFormulaType]:
         primary_field = field.link_row_table_primary_field
         return FormulaHandler.get_lookup_field_reference_expression(
             field, primary_field, self.to_baserow_formula_type(field)
         )
 
     def get_field_dependencies(
         self, field_instance: LinkRowField, field_cache: "FieldCache"
     ) -> FieldDependencies:
         primary_related_field = field_instance.link_row_table_primary_field
         if primary_related_field is not None:
             return [
                 FieldDependency(
                     dependency=primary_related_field,
                     dependant=field_instance,
                     via=field_instance,
                 )
             ]
         else:
             return []
 
+    def get_import_dependency_when_referenced(
+        self,
+        serialized_field: Dict[str, Any],
+        reference_name: str,
+        serialized_fields_map: Dict[int, Dict[str, Any]],
+        primary_table_fields_map: Dict[int, int],
+    ) -> Optional[Tuple[Union[int, str], Union[int, str]]]:
+        # A link row field renders the linked table's primary field, so referencing it
+        # by name really depends on that primary field, reached via this link row
+        # field. This is the import-time counterpart of `get_field_dependencies`.
+        related_table_id = serialized_field.get("link_row_table_id", None)
+
+        # A missing table means we're referencing a table that already exists before
+        # the import (i.e. duplicating a table/field), so there is nothing to order.
+        if related_table_id is None or related_table_id not in primary_table_fields_map:
+            return None
+
+        primary_field_id = primary_table_fields_map[related_table_id]
+        if primary_field_id not in serialized_fields_map:
+            return None
+
+        return (serialized_fields_map[primary_field_id]["name"], reference_name)
+
     def should_backup_field_data_for_same_type_update(
         self, old_field: LinkRowField, new_field_attrs: Dict[str, Any]
     ) -> bool:
         new_link_row_table_id = new_field_attrs.get(
             "link_row_table_id", old_field.link_row_table_id
         )
         return old_field.link_row_table_id != new_link_row_table_id
 
     def should_update_search_data(
         self, old_field: LinkRowField, new_field_attrs: Dict[str, Any]
     ) -> bool:
         new_link_row_table_id = new_field_attrs.get(
             "link_row_table_id", old_field.link_row_table_id
         )
         return old_field.link_row_table_id != new_link_row_table_id
 
     def get_dependants_which_will_break_when_field_type_changes(
         self, field: LinkRowField, to_field_type: "FieldType", field_cache: "FieldCache"
     ) -> "FieldDependants":
         """
         When a LinkRowField is converted to a different field type, the metadata row
         in the database_linkrowfield table is deleted. This causes a cascading delete
         of any FieldDependency rows which depend via this link row field. We use this
         hook to first query for these via dependencies prior to the type change and
         cascading delete so we can subsequently trigger updates for the affected
diff --git a/backend/src/baserow/contrib/database/fields/registries.py b/backend/src/baserow/contrib/database/fields/registries.py
index 8d9054d60..d4861aa61 100644
--- a/backend/src/baserow/contrib/database/fields/registries.py
+++ b/backend/src/baserow/contrib/database/fields/registries.py
@@ -1571,56 +1571,90 @@ class FieldType(
             back to the starting table where the row was created.
         :param already_updated_fields: A list of fields that have already been updated
             before. That can happen because it was a dependency of another field for
             example.
         :param skip_search_updates: If True, search index updates should be skipped.
         :param database_id: The id of the database that the fields belong to. If not
             provided, it means fields might belong to different databases and so we
             should not assume they belong to the same database.
         """
 
         return already_updated_fields
 
     def get_field_depdendencies_before_import_serialized(
         self,
         serialized_field: Dict[str, Any],
         serialized_fields_map: Dict[int, Dict[str, Any]],
         primary_table_fields_map: Dict[int, int],
     ) -> Optional[Set[Tuple[Union[int, str], Union[int, str]]]]:
         """
         Returns a list of field dependencies that must be imported before this field. If
         the depenndency is a field in the same table, the field name is returned. If the
         dependency is a field in a different table, a tuple of the link row field name
         and the field name is returned.
 
         :param serialized_field: The serialized field that is being imported.
+        :param serialized_fields_map: A map of all the serialized fields in the import,
+            keyed by their original field id.
+        :param primary_table_fields_map: A map of table id to the id of that table's
+            primary field, for all the tables in the import.
         :return: A list of field name dependencies that must be imported before this
             field.
         """
 
         return None
 
+    def get_import_dependency_when_referenced(
+        self,
+        serialized_field: Dict[str, Any],
+        reference_name: str,
+        serialized_fields_map: Dict[int, Dict[str, Any]],
+        primary_table_fields_map: Dict[int, int],
+    ) -> Optional[Tuple[Union[int, str], Union[int, str]]]:
+        """
+        Returns the dependency implied by referencing this field by name from another
+        field in the same table, or `None` if referencing it does not imply a
+        dependency on anything other than the field itself.
+
+        Field types whose value is borrowed from another table, like `link_row` which
+        renders the linked table's primary field, must return that other field here.
+        Otherwise the import would order the referencing field before the field it
+        actually reads from.
+
+        :param serialized_field: The serialized field that is being referenced.
+        :param reference_name: The name the referencing field used, which is the name
+            of this field and therefore the `via` of any returned dependency.
+        :param serialized_fields_map: A map of all the serialized fields in the import,
+            keyed by their original field id.
+        :param primary_table_fields_map: A map of table id to the id of that table's
+            primary field, for all the tables in the import.
+        :return: A `(field_name, via_field_name)` dependency, or `None` when
+            referencing this field implies no further dependency.
+        """
+
+        return None
+
     def valid_for_bulk_update(self, field: Field) -> bool:
         """
         Returns whether the field is valid for bulk updating. Fields that need to be
         updated in a specific order or have dependencies on other fields should return
         False.
 
         :param field: The field instance to check.
         :return: True if the field is valid for bulk updating, False otherwise.
         """
 
         return True
 
     def restore_failed(self, field_instance, restore_exception):
         """
         Called when restoring field_instance has caused an exception. Return True if
         the exception should be swallowed and the restore operation should succeed or
         False if it should fail and rollback.
 
         :param field_instance: The instance of the field which caused
             restore_exception on field restore.
         :type field_instance: Field
         :param restore_exception: The exception that was raised when restoring the
             field.
         :type restore_exception:
         :return: True to swallow the exception and succeed the restore, false to
```

## Source: backend/src/baserow/contrib/database/application_types.py

```
   ...
 433          :param import_export_config: provides configuration options for the
 434              import/export process to customize how it works.
 435          :param external_table_fields_to_import: An optional list of fields which should
 436              also be imported. These fields will be imported into the existing table
 437              provided in the first item in the tuple, the second being the serialized
 438              field to import.
 439          :param deferred_fk_update_collector: A collector that collects all the foreign
 440              keys to update them later when the model with all the fields is created.
 441          :param progress: A progress used to report progress of the import.
 442          :return: The imported fields.
 443          """
 444  
 445          field_cache = FieldCache()
 446          table_fields_by_name = {}
 447          deferred_field_importer = DeferredFieldImporter()
 448  
 449          # Create a mapping between the old field id and the field name. This is used
 450          # to resolve dependencies between fields.
 451          database_fields_map: Dict[int, str] = {}
 452          primary_table_fields_map: Dict[int, int] = {}
 453          for serialized_table in serialized_tables:
 454              for serialized_field in serialized_table["fields"]:
 455                  database_fields_map[serialized_field["id"]] = serialized_field
 456                  if serialized_field["primary"]:
 457                      primary_table_fields_map[serialized_table["id"]] = serialized_field[
 458                          "id"
 459                      ]
 460  
 461          id_mapping["database_fields_map"] = database_fields_map
 462          id_mapping["primary_table_fields_map"] = primary_table_fields_map
 463  
 464          def _import_field_serialized(serialized_table, serialized_field):
 465              """
 466              Create the field instance and add it to the table_fields_by_name mapping.
 467              The logic is wrapped in a function to allow using it for deferred imports.
 468              """
 469  
 470              table_instance = serialized_table["_object"]
 471              field_type = field_type_registry.get(serialized_field["type"])
 472              field_instance = field_type.import_serialized(
 473                  table_instance,
 474                  serialized_field,
 475                  import_export_config,
 476                  id_mapping,
 477                  deferred_fk_update_collector,
 478              )
 479              serialized_table["field_instances"].append(field_instance)
 480              if table_instance not in table_fields_by_name:
 481                  table_fields_by_name[table_instance] = {}
 482              table_fields_by_name[table_instance][field_instance.name] = field_instance
 483              table_name = serialized_table["name"]
 484              progress.increment(
 485                  state=f"{IMPORT_SERIALIZED_IMPORTING_TABLE_STRUCTURE}{table_name}"
 486              )
 487              return field_instance
 488  
 489          def _expand_implied_import_dependencies(field_deps, fields_by_name):
 490              """
 491              A dependency of `(name, None)` is a reference by name to a field in the
 492              same table. Some field types, like `link_row`, render a value borrowed
 493              from another table, so referencing them implies a dependency on that
 494              other field instead. Let each referenced field type say so.
 495              """
 496  
 497              if not field_deps:
 498                  return field_deps
 499  
 500              expanded = set()
 501              for name, via in field_deps:
 502                  referenced = fields_by_name.get(name) if via is None else None
 503                  implied = referenced and field_type_registry.get(
 504                      referenced["type"]
 505                  ).get_import_dependency_when_referenced(
 506                      referenced, name, database_fields_map, primary_table_fields_map
 507                  )
 508                  expanded.add(implied or (name, via))
 509              return expanded
 510  
 511          fields_without_dependencies: List[Field] = []
 512          for serialized_table in serialized_tables:
 513              table_instance = serialized_table["_object"]
 514              serialized_fields_by_name = {
 515                  f["name"]: f for f in serialized_table["fields"]
 516              }
 517              for serialized_field in serialized_table["fields"]:
 518                  field_type = field_type_registry.get(serialized_field["type"])
 519                  field_deps = (
 520                      field_type.get_field_depdendencies_before_import_serialized(
 521                          serialized_field,
 522                          database_fields_map,
 523                          primary_table_fields_map,
 524                      )
 525                  )
 526                  field_deps = _expand_implied_import_dependencies(
 527                      field_deps, serialized_fields_by_name
 528                  )
 529  
 530                  # If the field has dependencies, we want to defer the import of the
 531                  # field until all the dependencies have been imported.
 532                  if field_deps:
 533                      import_field_callback = partial(
 534                          _import_field_serialized, serialized_table, serialized_field
 535                      )
 536  
 537                      deferred_field_importer.add_deferred_field_import(
 538                          table_instance,
 539                          serialized_field["name"],
 540                          field_deps,
 541                          import_field_callback,
 542                      )
 543                  else:
 544                      # If the field has no dependencies, we can import it right away.
 545                      field_instance = _import_field_serialized(
 546                          serialized_table, serialized_field
 547                      )
 548                      fields_without_dependencies.append(field_instance)
 549  
 550          # Now that we have all the fields and their dependencies we can import all the
 551          # remaining fields in the correct order.
 552          fields_with_dependencies = deferred_field_importer.run_deferred_field_imports(
 553              id_mapping["database_field_names"]
 554          )
 555  
 556          deferred_fk_update_collector.run_deferred_fk_updates(
 557              id_mapping, "database_fields"
 558          )
 559  
 560          for external_table, serialized_field in external_table_fields_to_import or []:
 561              field_type = field_type_registry.get(serialized_field["type"])
 562              external_field = field_type.import_serialized(
 563                  external_table,
 564                  serialized_field,
 565                  import_export_config,
 566                  id_mapping,
 567                  deferred_fk_update_collector,
 568              )
 569              SearchHandler.schedule_update_search_data(
 570                  external_table, fields=[external_field]
 571              )
 572              progress.increment()
 573  
 574          deferred_fk_update_collector.run_deferred_fk_updates(
 575              id_mapping, "database_fields"
 576          )
 577  
 578          # For each field we call `after_import_serialized` which ensures that
 579          # formulas recalculate themselves now that all fields exist.
 580          for field_instance in fields_without_dependencies + fields_with_dependencies:
 581              field_type = field_type_registry.get_by_model(field_instance)
 582              field_type.after_import_serialized(field_instance, field_cache, id_mapping)
 583  
 584          # The loop above might have recalculated the formula fields in the list,
 585          # we need to refresh the instances we have as a result as they might be stale.
 586          for table_fields in table_fields_by_name.values():
 587              for field_instance in table_fields.values():
 588                  field_type = field_type_registry.get_by_model(field_instance)
 589                  if field_type.needs_refresh_after_import_serialized:
 590                      field_instance.refresh_from_db()
 591  
 592          return ImportedFields(
 593              table_fields_by_name=table_fields_by_name,
 594              fields_without_dependencies=fields_without_dependencies,
 595              fields_with_dependencies=fields_with_dependencies,
 596              field_cache=field_cache,
 597          )
 598  
 599      def import_tables_serialized(
 600          self,
 601          database: Database,
 602          serialized_tables: List[Dict[str, Any]],
 603          id_mapping: Dict[str, Any],
 604          import_export_config: ImportExportConfig,
   ...
 623              import.
 624          :param external_table_fields_to_import: An optional list of fields which should
 625              also be imported. These fields will be imported into the existing table
 626              provided in the first item in the tuple, the second being the serialized
 627              field to import.
 628              Useful for when importing a single table which also needs to add related
 629              fields to other existing tables in the database.
 630          :param import_export_config: provides configuration options for the
 631              import/export process to customize how it works.
 632          :return: The list of created tables
 633          """
 634  
 635          child_total = self._ops_count_for_import_tables_serialized(
 636              serialized_tables, external_table_fields_to_import
 637          )
 638          progress = ChildProgressBuilder.build(progress_builder, child_total=child_total)
 639  
 640          if "import_workspace_id" not in id_mapping and database.workspace is not None:
 641              id_mapping["import_workspace_id"] = database.workspace.id
 642  
 643          if "database_tables" not in id_mapping:
 644              id_mapping["database_tables"] = {}
 645  
 646          if "database_fields" not in id_mapping:
 647              id_mapping["database_fields"] = {}
 648  
 649          if "database_field_names" not in id_mapping:
 650              id_mapping["database_field_names"] = {}
 651  
 652          if "workspace_id" not in id_mapping and database.workspace is not None:
 653              id_mapping["workspace_id"] = database.workspace.id
 654  
 655          # Snapshots will provide a specific workspace to import user references from, so
 656          # we need to use that instead of the workspace the database is in if provided.
 657          workspace_for_user_references = (
 658              import_export_config.workspace_for_user_references
 659          )
 660          workspace_id_for_user_references = (
 661              workspace_for_user_references.id
 662              if workspace_for_user_references is not None
 663              else id_mapping.get("workspace_id", None)
 664          )
 665  
 666          user_email_mapping = {}
 667          if workspace_id_for_user_references:
 668              user_email_mapping = CoreHandler.get_user_email_mapping(
 669                  workspace_id_for_user_references, only_emails=[]
 670              )
 671  
 672          # First, we want to create all the table instances because it could be that
 673          # field or view properties depend on the existence of a table.
 674          imported_tables = self._import_tables(
 675              database, serialized_tables, id_mapping, progress
 676          )
 677  
 678          deferred_fk_update_collector = DeferredForeignKeyUpdater()
 679          # Because view properties might depend on fields, we first want to create all
 680          # the fields. Fields might have dependencies on other fields, so we want to
 681          # import them in the correct order.
 682          imported_fields = self._import_table_fields(
 683              serialized_tables,
 684              id_mapping,
 685              import_export_config,
 686              external_table_fields_to_import,
 687              deferred_fk_update_collector,
 688              progress,
 689          )
 690  
 691          # schema_editor.create_model will also create any m2m/through tables which
 692          # connect two models together. Once we create_model on the first model
 693          # the m2m will be made, so if we blindly call create_model on the second
 694          # model it will crash as the m2m connecting those two models already exists.
 695          # So instead we keep track of which m2m's have already been made to not
 696          # make them twice!
 697          already_created_through_table_names = set()
 698          # Now that the all tables and fields exist, we can create the views and create
 699          # the table schema in the database.
 700          for serialized_table in serialized_tables:
 701              self._import_table_views(
 702                  serialized_table, import_export_config, id_mapping, files_zip, progress
 703              )
 704              self._create_table_schema(
 705                  serialized_table, already_created_through_table_names
 706              )
 707              progress.increment(
 708                  state=f"{IMPORT_SERIALIZED_IMPORTING_TABLE_STRUCTURE}{serialized_table['name']}"
 709              )
 710  
 711          # Now that everything is in place we can start filling the table with the rows
 712          # in an efficient matter by using the bulk_create functionality.
 713          self._import_table_rows(
 714              serialized_tables,
 715              imported_fields,
 716              user_email_mapping,
 717              deferred_fk_update_collector,
 718              id_mapping,
 719              files_zip,
 720              storage,
 721              progress,
 722          )
 723  
 724          # Finally, now that everything has been created, loop over the
 725          # `serialization_processor_registry` registry and ensure extra
 726          # metadata is imported too.
 727          self._import_extra_metadata(serialized_tables, id_mapping, import_export_config)
 728  
 729          self._import_data_sync(serialized_tables, id_mapping, import_export_config)
 730  
 731          self._import_field_rules(serialized_tables, id_mapping, import_export_config)
 732  
 733          return imported_tables
 734  
 735      def _import_extra_metadata(
 736          self, serialized_tables, id_mapping, import_export_config
 737      ):
 738          if "_import_workspace_obj" not in id_mapping:
 739              id_mapping["_import_workspace_obj"] = Workspace.objects.get(
 740                  pk=id_mapping["import_workspace_id"]
 741              )
 742          source_workspace = id_mapping["_import_workspace_obj"]
 743          for serialized_table in serialized_tables:
```

## Source: backend/src/baserow/contrib/database/fields/field_cache.py

```
   1  from collections import defaultdict
   2  from typing import Optional, Type
   3  
   4  from django.core.exceptions import ObjectDoesNotExist
   5  from django.db.models import Model
   6  
   7  
   8  class FieldCache:
   9      """
  10      A cache which can be used to get the specific version of a field given a
  11      non-specific version or to get a field using a table and field name. If a cache
  12      miss occurs it will actually lookup the field from the database, cache it and
  13      return it, otherwise if the field does not exist None will be returned.
  14  
  15      Trashed fields are excluded from the cache.
  16      """
  17  
  18      def __init__(
  19          self,
  20          existing_cache: Optional["FieldCache"] = None,
  21          existing_model: Optional[Type[Model]] = None,
  22      ):
  23          if existing_cache is not None:
  24              self._cached_field_by_name_per_table = (
  25                  existing_cache._cached_field_by_name_per_table
  26              )
  27              self._model_cache = existing_cache._model_cache
  28          else:
  29              self._cached_field_by_name_per_table = defaultdict(dict)
  30              self._model_cache = {}
  31  
  32          if existing_model is not None:
  33              self.cache_model(existing_model)
  34  
  35      # noinspection PyUnresolvedReferences,PyProtectedMember
  36      def cache_model(self, model: Type[Model]):
  37          self._model_cache[model.baserow_table_id] = model
  38          self.cache_model_fields(model)
  39  
  40      # noinspection PyUnresolvedReferences,PyProtectedMember
  41      def cache_model_fields(self, model: Type[Model]):
  42          for field_object in model._field_objects.values():
  43              self.cache_field(field_object["field"])
  44  
  45      def get_model(self, table):
  46          table_id = table.id
  47          if table_id not in self._model_cache:
  48              model = table.get_model()
  49              self._model_cache[table_id] = model
  50              # Immediately cache the model fields because they're already in the most
  51              # specific form, and they might be needed later. This reduces the number
  52              # of queries.
  53              self.cache_model_fields(model)
  54          return self._model_cache[table_id]
  55  
  56      def uncache_field(self, field):
  57          return self._cached_field_by_name_per_table[field.table_id].pop(
  58              field.name, None
  59          )
  60  
  61      def reset_cache(self):
  62          self._cached_field_by_name_per_table = defaultdict(dict)
  63          self._model_cache = {}
  64  
  65      def cache_field(self, field):
  66          if not field.trashed:
  67              cached_fields = self._cached_field_by_name_per_table[field.table_id]
  68  
  69              try:
  70                  specific_field = field.specific
  71              except ObjectDoesNotExist:
  72                  return None
  73  
  74              cached_fields[field.name] = specific_field
  75              return specific_field
  76          else:
  77              return None
  78  
  79      def lookup_specific(self, non_specific_field, fetch_if_missing=True):
  80          try:
  81              return self._cached_field_by_name_per_table[non_specific_field.table_id][
  82                  non_specific_field.name
  83              ]
  84          except KeyError:
  85              if fetch_if_missing:
  86                  return self.cache_field(non_specific_field)
  87              else:
  88                  return None
  89  
  90      def lookup_by_name(self, table, field_name: str):
  91          try:
  92              return self._cached_field_by_name_per_table[table.id][field_name]
  93          except KeyError:
  94              try:
  95                  return self.cache_field(table.field_set.get(name=field_name))
  96              except ObjectDoesNotExist:
  97                  return None
```

## Source: backend/src/baserow/contrib/database/fields/field_types.py

```
   ...
3601                  link_row_limit_selection_view_id,
3602                  "database_views",
3603              )
3604  
3605          return field
3606  
3607      def after_import_serialized(
3608          self,
3609          field: LinkRowField,
3610          field_cache: "FieldCache",
3611          id_mapping: Dict[str, Any],
3612      ):
3613          if field.link_row_related_field:
3614              FieldDependencyHandler.rebuild_dependencies(
3615                  [field.link_row_related_field], field_cache
3616              )
3617          FieldDependencyHandler.rebuild_dependencies([field], field_cache)
3618  
3619      def get_export_serialized_value(self, row, field_name, cache, files_zip, storage):
3620          cache_entry = f"{field_name}_relations"
3621          if cache_entry not in cache:
3622              # In order to prevent a lot of lookup queries in the through table,
3623              # we want to fetch all the relations and add it to a temporary in memory
3624              # cache containing a mapping of the old ids to the new ids. Every relation
3625              # can use the cached mapped relations to find the correct id.
3626              cache[cache_entry] = defaultdict(list)
3627              through_model = row._meta.get_field(field_name).remote_field.through
3628              through_model_fields = through_model._meta.get_fields()
3629              current_field_name = through_model_fields[1].name
   ...
3694              return []
3695  
3696      def get_import_dependency_when_referenced(
3697          self,
3698          serialized_field: Dict[str, Any],
3699          reference_name: str,
3700          serialized_fields_map: Dict[int, Dict[str, Any]],
3701          primary_table_fields_map: Dict[int, int],
3702      ) -> Optional[Tuple[Union[int, str], Union[int, str]]]:
3703          # A link row field renders the linked table's primary field, so referencing it
3704          # by name really depends on that primary field, reached via this link row
3705          # field. This is the import-time counterpart of `get_field_dependencies`.
3706          related_table_id = serialized_field.get("link_row_table_id", None)
3707  
3708          # A missing table means we're referencing a table that already exists before
3709          # the import (i.e. duplicating a table/field), so there is nothing to order.
3710          if related_table_id is None or related_table_id not in primary_table_fields_map:
3711              return None
3712  
3713          primary_field_id = primary_table_fields_map[related_table_id]
3714          if primary_field_id not in serialized_fields_map:
3715              return None
3716  
3717          return (serialized_fields_map[primary_field_id]["name"], reference_name)
3718  
3719      def should_backup_field_data_for_same_type_update(
3720          self, old_field: LinkRowField, new_field_attrs: Dict[str, Any]
3721      ) -> bool:
3722          new_link_row_table_id = new_field_attrs.get(
3723              "link_row_table_id", old_field.link_row_table_id
3724          )
3725          return old_field.link_row_table_id != new_link_row_table_id
3726  
   ...
6135          connection,
6136          altered_column,
6137          before,
6138          to_field_kwargs,
6139      ):
6140          to_model = to_field.table.get_model()
6141          expr = FormulaHandler.baserow_expression_to_update_django_expression(
6142              to_field.cached_typed_internal_expression, to_model
6143          )
6144          to_model.objects_and_trash.all().update(**{f"{to_field.db_column}": expr})
6145  
6146      def after_import_serialized(self, field, field_cache, id_mapping):
6147          field.save(recalculate=True, field_cache=field_cache)
6148          FieldDependencyHandler.rebuild_dependencies([field], field_cache)
6149  
6150      def after_rows_imported(
6151          self,
6152          field: FormulaField,
6153          update_collector: Optional[FieldUpdateCollector] = None,
6154          field_cache: Optional["FieldCache"] = None,
6155          via_path_to_starting_table: Optional[List[LinkRowField]] = None,
6156      ):
6157          apply_updates = False
6158          if update_collector is None:
6159              update_collector = FieldUpdateCollector(field.table)
6160              apply_updates = True
   ...
6237          )
6238  
6239      def valid_for_bulk_update(self, field: Field) -> bool:
6240          # Let the dependency handler handle the update in the right order
6241          return False
6242  
6243      def get_field_depdendencies_before_import_serialized(
6244          self,
6245          serialized_field: Dict[str, Any],
6246          serialized_fields_map: Dict[int, Dict[str, Any]],
6247          primary_table_fields_map: Dict[int, int],
6248      ) -> Optional[Set[Tuple[Union[int, str], Union[int, str]]]]:
6249          if "formula" not in serialized_field:
6250              raise NotImplementedError(
6251                  "Each formula subtype needs to implement this method."
6252              )
6253  
6254          return FormulaHandler.get_dependencies_field_names(serialized_field["formula"])
6255  
6256      def parse_filter_value(self, field, model_field, value):
6257          (
6258              field_instance,
6259              field_type,
6260          ) = self.get_field_instance_and_type_from_formula_field(field)
6261          return field_type.parse_filter_value(field_instance, model_field, value)
6262  
6263      def can_have_db_index(self, field: Field) -> bool:
6264          return self.to_baserow_formula_type(field.specific).can_have_db_index
6265  
6266  
   ...
6929          )
6930          deferred_fk_update_collector.add_deferred_fk_to_update(
6931              field, "target_field_id", original_target_field_id, "database_fields"
6932          )
6933          return field
6934  
6935      def get_field_depdendencies_before_import_serialized(
6936          self,
6937          serialized_field: Dict[str, Any],
6938          serialized_fields_map: Dict[int, Dict[str, Any]],
6939          primary_table_fields_map: Dict[int, int],
6940      ) -> Optional[Set[Tuple[Union[int, str], Union[int, str]]]]:
6941          through_field_id = serialized_field.get("through_field_id", None)
6942          if through_field_id is None or through_field_id not in serialized_fields_map:
6943              return None  # broken reference
6944  
6945          via_field = serialized_fields_map[through_field_id]
6946          via_field_name = via_field["name"]
6947          target_field_id = serialized_field.get("target_field_id", None)
6948  
6949          # it means we're targeting a field that already exists before the import
6950          # (i.e. duplicating a table/field)
6951          if target_field_id is None or target_field_id not in serialized_fields_map:
6952              return None
6953  
6954          target_field_id = serialized_field["target_field_id"]
6955          target_field = serialized_fields_map[target_field_id]
6956          target_field_name = target_field["name"]
6957  
6958          return {(target_field_name, via_field_name)}
6959  
6960      def enhance_field_queryset(
6961          self, queryset: QuerySet[Field], field: Field
6962      ) -> QuerySet[Field]:
6963          return queryset.select_related("through_field", "target_field")
```

## Source: backend/src/baserow/contrib/database/fields/models.py

```
   ...
 776          raise_if_invalid = kwargs.pop("raise_if_invalid", False)
 777  
 778          if recalculate:
 779              self.recalculate_internal_fields(
 780                  field_cache=field_cache, raise_if_invalid=raise_if_invalid
 781              )
 782          super().save(*args, **kwargs)
 783          # Keep field_cache consistent to avoid stale type info downstream. See GH #5371.
 784          if field_cache is not None:
 785              field_cache.cache_field(self)
 786  
 787      def refresh_from_db(self, *args, **kwargs) -> None:
 788          super().refresh_from_db(*args, **kwargs)
 789          self.clear_cached_properties()
 790  
 791      def __str__(self):
 792          return (
 793              "FormulaField(\n"
 794              + f"formula={self.formula},\n"
 795              + f"internal_formula={self.internal_formula},\n"
 796              + f"formula_type={self.formula_type},\n"
 797              + f"error={self.error},\n"
 798              + ")"
 799          )
 800  
 801  
```

## Source: backend/src/baserow/contrib/database/fields/registries.py

```

```

## Source: backend/src/baserow/contrib/database/fields/utils/deferred_field_importer.py

```
   1  import typing
   2  from collections import defaultdict
   3  from typing import Callable, Dict, List, Set, Tuple
   4  
   5  if typing.TYPE_CHECKING:
   6      from baserow.contrib.database.fields.models import Field
   7      from baserow.contrib.database.table.models import Table
   8  
   9  
  10  class DeferredFieldImporter:
  11      """
  12      This class is used to import fields in the correct order based on their dependencies
  13      after all the fields without dependencies have been imported. This is useful when
  14      importing or duplicating a table with formulas or other fields that have
  15      dependencies.
  16      """
  17  
  18      def __init__(self):
  19          self.deferred_field_imports = {}
  20          self.field_import_callback_mapping = {}
  21  
  22      def _unique_field_name(self, table_id: int, field_name: str) -> str:
  23          return f"{table_id}:{field_name}"
  24  
  25      def add_deferred_field_import(
  26          self,
  27          table: "Table",
  28          field_name: str,
  29          field_dependencies: Set[Tuple[str, str]],
  30          import_field_callback: Callable,
  31      ) -> None:
  32          """
  33          Adds a field and its dependencies to the list of deferred field to import. The
  34          field will be imported in the right order once `run_deferred_field_imports` is
  35          called.
  36  
  37          :param table: The table the field belongs to.
  38          :param field_name: The name of the field.
  39          :param field_dependencies: A set of tuples where the first element is the name
  40              of the field that the field depends on and the second element is the name of
  41              the link row field to reach the target field. If the second element is None
  42              the target field is in the same table.
  43          :param import_field_callback: The callback that will import the field.
  44          """
  45  
  46          unique_field_name = self._unique_field_name(table.id, field_name)
  47          self.deferred_field_imports[unique_field_name] = (table, field_dependencies)
  48          self.field_import_callback_mapping[unique_field_name] = import_field_callback
  49  
  50      def get_all_fields_dependencies(
  51          self, field_name_fields_mapping: Dict[int, Dict[str, "Field"]]
  52      ) -> Dict[str, Set[str]]:
  53          """
  54          Merges all the field dependencies into a single dictionary. Dependencies use the
  55          table id and the field name to identify the field. The returned dictionary will
  56          have the field name as the key and a set of field names that it depends on as
  57          the value.
  58  
  59          :param field_name_fields_mapping: A mapping from table id to field name to field
  60          :return: A dictionary with the field name as the key and a set of field names
  61              representing the dependencies.
  62          """
  63  
  64          dependencies = defaultdict(set)
  65  
  66          for field_temp_id, (table, field_deps) in self.deferred_field_imports.items():
  67              for dep_field_name, via_field_name in field_deps:
  68                  if via_field_name is not None:
  69                      try:
  70                          # The target field is in the linked table
  71                          link_row_field = field_name_fields_mapping[table.id][
  72                              via_field_name
  73                          ]
  74                          dep_table_id = link_row_field.link_row_table_id
  75                      except KeyError:
  76                          # If the `via_field_name` does not exist, then there is a
  77                          # broken dependency. In that case, it's okay to use the
  78                          # `table.id` as `dep_table_id` because it does not matter how
  79                          # it's grouped later.
  80                          dep_table_id = table.id
  81                  else:
  82                      # The target field is in the same table
  83                      dep_table_id = table.id
  84  
  85                  dep_field_temp_id = self._unique_field_name(
  86                      dep_table_id, dep_field_name
  87                  )
  88                  dependencies[field_temp_id].add(dep_field_temp_id)
  89  
  90          return dependencies
  91  
  92      def run_deferred_field_imports(
  93          self, field_name_fields_mapping: Dict[int, Dict[str, "Field"]]
  94      ) -> List["Field"]:
  95          """
  96          Performs the deferred field imports in the correct order. The fields will be
  97          imported in the correct order based on the dependencies. The dependencies are
  98          based on the table and field name. Because this happens at import time, we don't
  99          have the field instances yet, so we need to re-create the dependendency tree
 100          based on the field names and the table where they belong.
 101  
 102          :param field_name_fields_mapping: A mapping from table id to field name to field
 103          :return: The imported fields.
 104          """
 105  
 106          from baserow.contrib.database.fields.dependencies.handler import (
 107              FieldDependencyHandler,
 108          )
 109  
 110          dependencies = self.get_all_fields_dependencies(field_name_fields_mapping)
 111  
 112          # Now we can import the fields in the correct order
 113          imported_fields: List[Field] = []
 114          dependency_levels = FieldDependencyHandler.group_dependencies_by_level(
 115              dependencies
 116          )
 117  
 118          # The first level are the fields without dependencies, but we don't need to
 119          # import them because they have already been imported.
 120          for level in dependency_levels[1:]:
 121              for unique_field_name in level:
 122                  import_field_callback = self.field_import_callback_mapping[
 123                      unique_field_name
 124                  ]
 125                  imported_field = import_field_callback()
 126                  imported_fields.append(imported_field)
 127  
 128          return imported_fields
```

## Source: backend/src/baserow/contrib/database/fields/utils/deferred_foreign_key_updater.py

```
   1  import typing
   2  from collections import defaultdict
   3  from typing import Dict
   4  
   5  if typing.TYPE_CHECKING:
   6      from django.db.models import Model
   7  
   8  
   9  class DeferredForeignKeyUpdater:
  10      """
  11      This class keeps track of foreign keys to other fields which need to be set once
  12      we have bulk created a set of fields.
  13  
  14      For example, when importing a table/database/workspace we have to go through and
  15      create many fields all at once. Fields can have FKs to other fields, but because we
  16      can only create fields one a time we can't set these FKs to other fields as
  17      they might not exist yet.
  18  
  19      This class keeps track of which foreign keys which need to be set once all
  20      depenencies have been created in the database. At which point you can call
  21      `run_deferred_fk_updates` with a mapping from the original field ids to
  22      the new ones to bulk setup all the pending FKs.
  23      """
  24  
  25      def __init__(self):
  26          self.deferred_field_fk_updates_per_model_class = defaultdict(list)
  27  
  28      def add_deferred_fk_to_update(
  29          self,
  30          instance: "Model",
  31          fk_attr: str,
  32          original_fk_id: int,
  33          mapping_key: str,
  34      ):
  35          self.deferred_field_fk_updates_per_model_class[type(instance)].append(
  36              (instance, fk_attr, original_fk_id, mapping_key)
  37          )
  38  
  39      def run_deferred_fk_updates(
  40          self, id_mapping: Dict[str, Dict[int, int]], run_mapping_key: str
  41      ):
  42          for (
  43              field_model_class,
  44              deferred_field_fk_updates,
  45          ) in self.deferred_field_fk_updates_per_model_class.items():
  46              fields_to_bulk_update = {}
  47              attr_names = set()
  48              for (
  49                  field,
  50                  attr_name,
  51                  desired_field_id,
  52                  mapping_key,
  53              ) in deferred_field_fk_updates:
  54                  if desired_field_id and run_mapping_key == mapping_key:
  55                      field_to_bulk_update = fields_to_bulk_update.setdefault(
  56                          field.id, field
  57                      )
  58                      attr_names.add(attr_name)
  59                      setattr(
  60                          field_to_bulk_update,
  61                          attr_name,
  62                          id_mapping.get(mapping_key, {}).get(desired_field_id, None),
  63                      )
  64              if len(fields_to_bulk_update) > 0:
  65                  field_model_class.objects.bulk_update(
  66                      fields_to_bulk_update.values(), attr_names
  67                  )
```

## Source: backend/src/baserow/core/registry.py

```
   ...
 773          """
 774          Returns a registered instance of the given type name.
 775  
 776          :param type_name: The unique name of the registered instance.
 777          :type type_name: str
 778          :raises InstanceTypeDoesNotExist: If the instance with the provided `type_name`
 779              does not exist in the registry.
 780          :return: The requested instance.
 781          :rtype: InstanceModelInstance
 782          """
 783  
 784          # If the `type_name` isn't in the registry, we may raise DoesNotExist.
 785          if type_name not in self.registry:
 786              # But first, we'll test to see if it matches an Instance's
 787              # `compat_name`. If it does, we'll use that Instance's `type`.
 788              type_name_via_compat = self.get_by_type_name_by_compat(type_name)
 789              if type_name_via_compat:
 790                  type_name = type_name_via_compat
 791              else:
 792                  raise self.does_not_exist_exception_class(
 793                      type_name, f"The {self.name} type {type_name} does not exist."
 794                  )
 795  
 796          return self.registry[type_name]
 797  
 798      def get_by_type_name_by_compat(self, compat_name: str) -> Optional[str]:
 799          """
 800          Returns a registered instance's `type` by using the compatibility name.
 801          """
 802  
 803          for instance in self.get_all():
 804              if instance.compat_type == compat_name:
   ...
 891          self, model_instance: Union[DjangoModel, Type[DjangoModel]]
 892      ) -> InstanceSubClass:
 893          """
 894          Returns a registered instance of the given model class.
 895  
 896          :param model_instance: The value that must be a Model class or
 897              an instance of any model_class.
 898          :raises InstanceTypeDoesNotExist: When the provided model instance is not
 899              found in the registry.
 900          :return: The registered instance.
 901          """
 902  
 903          if isinstance(model_instance, type):
 904              clazz = model_instance
 905          else:
 906              clazz = model_instance.__class__
 907  
 908          return self.get_for_class(clazz)
 909  
 910      @lru_cache
 911      def get_for_class(self, clazz: Type[DjangoModel]) -> InstanceSubClass:
 912          """
 913          Returns a registered instance of the given model class.
 914  
 915          :param model_instance: The value that must be a Model class.
 916          :raises InstanceTypeDoesNotExist: When the provided model instance is not
 917              found in the registry.
 918          :return: The registered instance.
 919          """
 920  
```

## Source: backend/tests/baserow/contrib/database/field/dependencies/test_field_dependency_handler.py

```
   ...
 800  def test_can_import_database_with_formula_dependencies(data_fixture):
 801      user = data_fixture.create_user()
 802      database = data_fixture.create_database_application(user=user)
 803      id_mapping = {}
 804      tables = DatabaseApplicationType().import_tables_serialized(
 805          database,
 806          EXPORTED_TABLES_WITH_DEPENDENCIES_EXAMPLE,
 807          id_mapping,
 808          ImportExportConfig(include_permission_data=False),
 809      )
 810      assert len(tables) == 2
 811  
 812      # Verify formulas are imported correctly and rows have correct values
 813      t1 = tables[0].get_model(attribute_names=True)
 814      r1 = t1.objects.get(pk=1)
 815  
 816      assert r1.formula == "A"
 817  
 818      t2 = tables[1].get_model(attribute_names=True)
 819      r2 = t2.objects.get(pk=1)
 820  
 821      assert r2.lookup == [{"id": 1, "value": "A"}]
 822      assert r2.lookup2 == [{"id": 1, "value": "A"}]
 823  
 824  
 825  @pytest.mark.django_db
```

## Source: backend/tests/baserow/core/snapshots/test_snapshot_array_formula_import.py

```
   1  import pytest
   2  
   3  from baserow.contrib.database.fields.handler import FieldHandler
   4  from baserow.contrib.database.rows.handler import RowHandler
   5  from baserow.core.handler import CoreHandler
   6  from baserow.core.snapshots.handler import SnapshotHandler
   7  from baserow.core.utils import Progress
   8  
   9  
  10  @pytest.mark.django_db(transaction=True)
  11  def test_snapshot_with_explicit_array_primary_dependency(data_fixture):
  12      """
  13      When the formula explicitly references the linked table's primary via
  14      lookup('LinkField', 'PrimaryField'), the dependency graph is complete
  15      and the snapshot import produces correct values.
  16      """
  17  
  18      user = data_fixture.create_user()
  19      database = data_fixture.create_database_application(user=user)
  20      parent_table = data_fixture.create_database_table(
  21          database=database, name="Parents", order=0
  22      )
  23      child_table = data_fixture.create_database_table(
  24          database=database, name="Children", order=1
  25      )
  26      detail_table = data_fixture.create_database_table(
  27          database=database, name="Details", order=2
  28      )
  29      data_fixture.create_text_field(table=parent_table, name="Name", primary=True)
  30      child_primary = data_fixture.create_text_field(
  31          table=child_table, name="ChildId", primary=True
  32      )
  33      detail_name = data_fixture.create_text_field(
  34          table=detail_table, name="Label", primary=True
  35      )
  36      is_active = data_fixture.create_boolean_field(table=child_table, name="IsActive")
  37  
  38      fh = FieldHandler()
  39      parent_link = fh.create_field(
  40          user,
  41          parent_table,
  42          "link_row",
  43          name="LinkedChildren",
  44          link_row_table=child_table,
  45      )
  46      detail_link = fh.create_field(
  47          user, child_table, "link_row", name="Detail", link_row_table=detail_table
  48      )
  49      child_primary = fh.update_field(
  50          user,
  51          child_primary,
  52          new_type_name="formula",
  53          formula="concat('ID-', field('Detail'))",
  54      )
  55  
  56      consumer = fh.create_field(
  57          user,
  58          parent_table,
  59          "formula",
  60          name="ActiveChildren",
  61          formula=(
  62              "filter(lookup('LinkedChildren', 'ChildId'), "
  63              "lookup('LinkedChildren', 'IsActive'))"
  64          ),
  65      )
  66      assert child_primary.formula_type == "array"
  67      assert "array_agg_unnesting" in consumer.internal_formula
  68  
  69      rh = RowHandler()
  70      detail_row = rh.create_row(user, detail_table, values={detail_name.db_column: "D1"})
  71      child_row = rh.create_row(
  72          user,
  73          child_table,
  74          values={is_active.db_column: True, detail_link.db_column: [detail_row.id]},
  75      )
  76      rh.create_row(user, parent_table, values={parent_link.db_column: [child_row.id]})
  77  
  78      expected = list(
  79          parent_table.get_model().objects.values_list(consumer.db_column, flat=True)
  80      )
  81      assert expected[0] and expected[0][0]["value"] == "ID-D1"
  82  
  83      snapshot = data_fixture.create_snapshot(
  84          snapshot_from_application=database, created_by=user
  85      )
  86      SnapshotHandler().perform_create(snapshot, Progress(total=100))
  87      snapshot.refresh_from_db()
  88  
  89      imported_parent = snapshot.snapshot_to_application.specific.table_set.get(
  90          name="Parents"
  91      )
  92      imported_consumer = imported_parent.field_set.get(name="ActiveChildren")
  93      actual = list(
  94          imported_parent.get_model().objects.values_list(
  95              imported_consumer.db_column, flat=True
  96          )
  97      )
  98      assert actual == expected
  99  
 100  
 101  @pytest.mark.django_db(transaction=True)
 102  def test_snapshot_with_implicit_array_primary_dependency(data_fixture):
 103      """
 104      When the formula uses field('LinkField') (implicit primary reference),
 105      the import-time dependency graph must still resolve the linked table's
 106      primary so recalculation order is correct and values are preserved.
 107      Previously this crashed with DataError because the consumer formula ran
 108      before the producer's column was populated.
 109      """
 110  
 111      user = data_fixture.create_user()
 112      database = data_fixture.create_database_application(user=user)
 113      parent_table = data_fixture.create_database_table(
 114          database=database, name="Parents", order=0
 115      )
 116      child_table = data_fixture.create_database_table(
 117          database=database, name="Children", order=1
 118      )
 119      detail_table = data_fixture.create_database_table(
 120          database=database, name="Details", order=2
 121      )
 122      data_fixture.create_text_field(table=parent_table, name="Name", primary=True)
 123      child_primary = data_fixture.create_text_field(
 124          table=child_table, name="ChildId", primary=True
 125      )
 126      detail_name = data_fixture.create_text_field(
 127          table=detail_table, name="Label", primary=True
 128      )
 129      is_active = data_fixture.create_boolean_field(table=child_table, name="IsActive")
 130  
 131      fh = FieldHandler()
 132      parent_link = fh.create_field(
 133          user,
 134          parent_table,
 135          "link_row",
 136          name="LinkedChildren",
 137          link_row_table=child_table,
 138      )
 139      detail_link = fh.create_field(
 140          user, child_table, "link_row", name="Detail", link_row_table=detail_table
 141      )
 142      child_primary = fh.update_field(
 143          user,
 144          child_primary,
 145          new_type_name="formula",
 146          formula="concat('ID-', field('Detail'))",
 147      )
 148  
 149      consumer = fh.create_field(
 150          user,
 151          parent_table,
 152          "formula",
 153          name="ActiveChildren",
 154          formula=(
 155              "filter(field('LinkedChildren'), lookup('LinkedChildren', 'IsActive'))"
 156          ),
 157      )
 158      assert child_primary.formula_type == "array"
 159      assert "array_agg_unnesting" in consumer.internal_formula
 160  
 161      rh = RowHandler()
 162      detail_row = rh.create_row(user, detail_table, values={detail_name.db_column: "D1"})
 163      child_row = rh.create_row(
 164          user,
 165          child_table,
 166          values={is_active.db_column: True, detail_link.db_column: [detail_row.id]},
 167      )
 168      rh.create_row(user, parent_table, values={parent_link.db_column: [child_row.id]})
 169  
 170      expected = list(
 171          parent_table.get_model().objects.values_list(consumer.db_column, flat=True)
 172      )
 173      assert expected[0] and expected[0][0]["value"] == "ID-D1"
 174  
 175      snapshot = data_fixture.create_snapshot(
 176          snapshot_from_application=database, created_by=user
 177      )
 178      SnapshotHandler().perform_create(snapshot, Progress(total=100))
 179      snapshot.refresh_from_db()
 180  
 181      imported_parent = snapshot.snapshot_to_application.specific.table_set.get(
 182          name="Parents"
 183      )
 184      imported_consumer = imported_parent.field_set.get(name="ActiveChildren")
 185      actual = list(
 186          imported_parent.get_model().objects.values_list(
 187              imported_consumer.db_column, flat=True
 188          )
 189      )
 190      assert actual == expected
 191  
 192  
 193  @pytest.mark.django_db(transaction=True)
 194  def test_snapshot_with_implicit_array_primary_dependency_two_links_deep(data_fixture):
 195      """
 196      The implied dependency may itself be deferred: here the linked table's primary
 197      is an array formula reading through a second link. Resolving one hop is not
 198      enough, the whole chain has to be ordered, otherwise the middle table's primary
 199      is still NULL when the consumer recalculates.
 200      """
 201  
 202      user = data_fixture.create_user()
 203      database = data_fixture.create_database_application(user=user)
 204      table_a = data_fixture.create_database_table(database=database, name="A", order=0)
 205      table_b = data_fixture.create_database_table(database=database, name="B", order=1)
 206      table_c = data_fixture.create_database_table(database=database, name="C", order=2)
 207      data_fixture.create_text_field(table=table_a, name="AName", primary=True)
 208      b_primary = data_fixture.create_text_field(table=table_b, name="BId", primary=True)
 209      c_label = data_fixture.create_text_field(table=table_c, name="CLabel", primary=True)
 210  
 211      fh = FieldHandler()
 212      a_link = fh.create_field(
 213          user, table_a, "link_row", name="ToB", link_row_table=table_b
 214      )
 215      b_link = fh.create_field(
 216          user, table_b, "link_row", name="ToC", link_row_table=table_c
 217      )
 218      b_primary = fh.update_field(
 219          user, b_primary, new_type_name="formula", formula="field('ToC')"
 220      )
 221  
 222      consumer = fh.create_field(
 223          user, table_a, "formula", name="AConsumer", formula="field('ToB')"
 224      )
 225      assert b_primary.formula_type == "array"
 226      assert "array_agg_unnesting" in consumer.internal_formula
 227  
 228      rh = RowHandler()
 229      c_row = rh.create_row(user, table_c, values={c_label.db_column: "C1"})
 230      b_row = rh.create_row(user, table_b, values={b_link.db_column: [c_row.id]})
 231      rh.create_row(user, table_a, values={a_link.db_column: [b_row.id]})
 232  
 233      expected = list(
 234          table_a.get_model().objects.values_list(consumer.db_column, flat=True)
 235      )
 236      assert expected[0] and expected[0][0]["value"] == "C1"
 237  
 238      snapshot = data_fixture.create_snapshot(
 239          snapshot_from_application=database, created_by=user
 240      )
 241      SnapshotHandler().perform_create(snapshot, Progress(total=100))
 242      snapshot.refresh_from_db()
 243  
 244      imported_a = snapshot.snapshot_to_application.specific.table_set.get(name="A")
 245      imported_consumer = imported_a.field_set.get(name="AConsumer")
 246      actual = list(
 247          imported_a.get_model().objects.values_list(
 248              imported_consumer.db_column, flat=True
 249          )
 250      )
 251      assert actual == expected
 252  
 253  
 254  @pytest.mark.django_db(transaction=True)
 255  def test_duplicate_application_with_implicit_array_primary_dependency(data_fixture):
 256      """
 257      Duplicating an application imports the serialized fields through the same
 258      dependency ordering, so the implicit `field('LinkField')` reference must be
 259      resolved there too.
 260      """
 261  
 262      user = data_fixture.create_user()
 263      database = data_fixture.create_database_application(user=user)
 264      parent_table = data_fixture.create_database_table(
 265          database=database, name="Parents", order=0
 266      )
 267      child_table = data_fixture.create_database_table(
 268          database=database, name="Children", order=1
 269      )
 270      detail_table = data_fixture.create_database_table(
 271          database=database, name="Details", order=2
 272      )
 273      data_fixture.create_text_field(table=parent_table, name="Name", primary=True)
 274      child_primary = data_fixture.create_text_field(
 275          table=child_table, name="ChildId", primary=True
 276      )
 277      detail_name = data_fixture.create_text_field(
 278          table=detail_table, name="Label", primary=True
 279      )
 280      is_active = data_fixture.create_boolean_field(table=child_table, name="IsActive")
 281  
 282      fh = FieldHandler()
 283      parent_link = fh.create_field(
 284          user,
 285          parent_table,
 286          "link_row",
 287          name="LinkedChildren",
 288          link_row_table=child_table,
 289      )
 290      detail_link = fh.create_field(
 291          user, child_table, "link_row", name="Detail", link_row_table=detail_table
 292      )
 293      child_primary = fh.update_field(
 294          user,
 295          child_primary,
 296          new_type_name="formula",
 297          formula="concat('ID-', field('Detail'))",
 298      )
 299  
 300      consumer = fh.create_field(
 301          user,
 302          parent_table,
 303          "formula",
 304          name="ActiveChildren",
 305          formula=(
 306              "filter(field('LinkedChildren'), lookup('LinkedChildren', 'IsActive'))"
 307          ),
 308      )
 309      assert child_primary.formula_type == "array"
 310      assert "array_agg_unnesting" in consumer.internal_formula
 311  
 312      rh = RowHandler()
 313      detail_row = rh.create_row(user, detail_table, values={detail_name.db_column: "D1"})
 314      child_row = rh.create_row(
 315          user,
 316          child_table,
 317          values={is_active.db_column: True, detail_link.db_column: [detail_row.id]},
 318      )
 319      rh.create_row(user, parent_table, values={parent_link.db_column: [child_row.id]})
 320  
 321      expected = list(
 322          parent_table.get_model().objects.values_list(consumer.db_column, flat=True)
 323      )
 324      assert expected[0] and expected[0][0]["value"] == "ID-D1"
 325  
 326      duplicated = CoreHandler().duplicate_application(user, database)
 327  
 328      duplicated_parent = duplicated.specific.table_set.get(name="Parents")
 329      duplicated_consumer = duplicated_parent.field_set.get(name="ActiveChildren")
 330      actual = list(
 331          duplicated_parent.get_model().objects.values_list(
 332              duplicated_consumer.db_column, flat=True
 333          )
 334      )
 335      assert actual == expected
```
