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

## Mechanics at HEAD (deterministic, intra-procedural)

Nested functions of `_import_table_fields` are opaque to the static front end. `DeferredFieldImporter` is in a file the change does not touch, so no facts were computed for it.

### DatabaseApplicationType._import_table_fields  (backend/src/baserow/contrib/database/application_types.py)
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
- store `database_fields_map[]` ← unknown:UNKNOWN_DEPENDENCE:loop-variable line 455 requires: ?loop & ?loop
- store `primary_table_fields_map[]` ← unknown:UNKNOWN_DEPENDENCE:loop-variable line 457 requires: ?loop & ?loop & br:34ec71ee29c9=T
- store `id_mapping[]` ← const line 461 requires: —
- store `id_mapping[]` ← const line 462 requires: —
- OPAQUE statement line 464: FunctionDef (not lowered; its sites are runtime only)
- OPAQUE statement line 489: FunctionDef (not lowered; its sites are runtime only)

### LinkRowFieldType.get_import_dependency_when_referenced  (backend/src/baserow/contrib/database/fields/field_types.py)
- site br:a0d4e306fb5a line 3710: `related_table_id is None or related_table_id not in primary_table_fields_map` | operands: primary_table_fields_map ← param:primary_table_fields_map; related_table_id ← call:serialized_field.get | requires: — | then exits: True, else exits: False
- site br:f960d9f63045 line 3714: `primary_field_id not in serialized_fields_map` | operands: primary_field_id ← call:serialized_field.get, param:primary_table_fields_map; serialized_fields_map ← param:serialized_fields_map | requires: br:a0d4e306fb5a=F | then exits: True, else exits: False
- call `serialized_field.get` line 3706 requires: —

### FormulaFieldType.get_field_depdendencies_before_import_serialized  (backend/src/baserow/contrib/database/fields/field_types.py)
- site br:49c2edb05730 line 6249: `'formula' not in serialized_field` | operands: serialized_field ← param:serialized_field | requires: — | then exits: True, else exits: False
- call `NotImplementedError` line 6250 requires: br:49c2edb05730=T
- call `FormulaHandler.get_dependencies_field_names` line 6254 requires: br:49c2edb05730=F

### LookupFieldType.get_field_depdendencies_before_import_serialized  (backend/src/baserow/contrib/database/fields/field_types.py)
- site br:df188b1f6d10 line 6942: `through_field_id is None or through_field_id not in serialized_fields_map` | operands: serialized_fields_map ← param:serialized_fields_map; through_field_id ← call:serialized_field.get | requires: — | then exits: True, else exits: False
- site br:b0d9d883d08b line 6951: `target_field_id is None or target_field_id not in serialized_fields_map` | operands: serialized_fields_map ← param:serialized_fields_map; target_field_id ← call:serialized_field.get | requires: br:df188b1f6d10=F | then exits: True, else exits: False
- call `serialized_field.get` line 6941 requires: —
- call `serialized_field.get` line 6947 requires: br:df188b1f6d10=F

### FieldType.get_field_depdendencies_before_import_serialized  (backend/src/baserow/contrib/database/fields/registries.py)

### FieldType.get_import_dependency_when_referenced  (backend/src/baserow/contrib/database/fields/registries.py)

## Mechanics at BASE (same functions; site ids differ where lines moved)

### DatabaseApplicationType._import_table_fields  (backend/src/baserow/contrib/database/application_types.py)
- site br:34ec71ee29c9 line 456: `serialized_field['primary']` | operands: serialized_field ← unknown:UNKNOWN_DEPENDENCE:loop-variable | requires: ?loop & ?loop | then exits: False, else exits: False
- site br:0771b757bce0 line 504: `field_deps` | operands: field_deps ← call:field_type.get_field_depdendencies_before_import_serialized | requires: ?loop & ?loop | then exits: False, else exits: False
- site br:f38c5af64076 line 561: `field_type.needs_refresh_after_import_serialized` | operands: field_type.needs_refresh_after_import_serialized ← call:field_type_registry.get_by_model.needs_refresh_after_import_serialized | requires: ?loop & ?loop | then exits: False, else exits: False
- call `FieldCache` line 445 requires: —
- call `DeferredFieldImporter` line 447 requires: —
- call `field_type_registry.get` line 493 requires: ?loop & ?loop
- call `field_type.get_field_depdendencies_before_import_serialized` line 495 requires: ?loop & ?loop
- call `partial` line 505 requires: ?loop & ?loop & br:0771b757bce0=T
- call `deferred_field_importer.add_deferred_field_import` line 509 requires: ?loop & ?loop & br:0771b757bce0=T
- call `_import_field_serialized` line 517 requires: ?loop & ?loop & br:0771b757bce0=F
- call `fields_without_dependencies.append` line 520 requires: ?loop & ?loop & br:0771b757bce0=F
- call `deferred_field_importer.run_deferred_field_imports` line 524 requires: —
- call `deferred_fk_update_collector.run_deferred_fk_updates` line 528 requires: —
- call `field_type_registry.get` line 533 requires: ?loop
- call `field_type.import_serialized` line 534 requires: ?loop
- call `SearchHandler.schedule_update_search_data` line 541 requires: ?loop
- call `progress.increment` line 544 requires: ?loop
- call `deferred_fk_update_collector.run_deferred_fk_updates` line 546 requires: —
- call `field_type_registry.get_by_model` line 553 requires: ?loop
- call `field_type.after_import_serialized` line 554 requires: ?loop
- call `table_fields_by_name.values` line 558 requires: —
- call `table_fields.values` line 559 requires: ?loop
- call `field_type_registry.get_by_model` line 560 requires: ?loop & ?loop
- call `field_instance.refresh_from_db` line 562 requires: ?loop & ?loop & br:f38c5af64076=T
- call `ImportedFields` line 564 requires: —
- store `database_fields_map[]` ← unknown:UNKNOWN_DEPENDENCE:loop-variable line 455 requires: ?loop & ?loop
- store `primary_table_fields_map[]` ← unknown:UNKNOWN_DEPENDENCE:loop-variable line 457 requires: ?loop & ?loop & br:34ec71ee29c9=T
- store `id_mapping[]` ← const line 461 requires: —
- store `id_mapping[]` ← const line 462 requires: —
- OPAQUE statement line 464: FunctionDef (not lowered; its sites are runtime only)

### FormulaFieldType.get_field_depdendencies_before_import_serialized  (backend/src/baserow/contrib/database/fields/field_types.py)
- site br:1c6b5568b809 line 6226: `'formula' not in serialized_field` | operands: serialized_field ← param:serialized_field | requires: — | then exits: True, else exits: False
- call `NotImplementedError` line 6227 requires: br:1c6b5568b809=T
- call `FormulaHandler.get_dependencies_field_names` line 6231 requires: br:1c6b5568b809=F

### LookupFieldType.get_field_depdendencies_before_import_serialized  (backend/src/baserow/contrib/database/fields/field_types.py)
- site br:ef6ec241fb07 line 6919: `through_field_id is None or through_field_id not in serialized_fields_map` | operands: serialized_fields_map ← param:serialized_fields_map; through_field_id ← call:serialized_field.get | requires: — | then exits: True, else exits: False
- site br:0f9dcde0ef18 line 6928: `target_field_id is None or target_field_id not in serialized_fields_map` | operands: serialized_fields_map ← param:serialized_fields_map; target_field_id ← call:serialized_field.get | requires: br:ef6ec241fb07=F | then exits: True, else exits: False
- call `serialized_field.get` line 6918 requires: —
- call `serialized_field.get` line 6924 requires: br:ef6ec241fb07=F

### FieldType.get_field_depdendencies_before_import_serialized  (backend/src/baserow/contrib/database/fields/registries.py)

## Runtime-only sites at HEAD (nested functions of `_import_table_fields`, and the unlowered `DeferredFieldImporter`; outcome observed, no static facts)

- br:0a953aea08c4 backend/src/baserow/contrib/database/fields/utils/deferred_field_importer.py:5 `typing.TYPE_CHECKING`
- br:cbfe8c1c2b07 backend/src/baserow/contrib/database/fields/utils/deferred_field_importer.py:68 `via_field_name is not None`
- br:3f16965dcd1f backend/src/baserow/contrib/database/application_types.py:480 `table_instance not in table_fields_by_name`
- br:be7d3ee9e3b1 backend/src/baserow/contrib/database/application_types.py:497 `not field_deps`

## Observed event logs (shown tests, at head and at base)

Calls under `_import_table_fields` in chronological order, indented by depth among the shown calls (everything else is looked through), with argument shapes and value digests, results, and the observed outcome of every decision site evaluated in those calls.

```
### test_snapshot_with_explicit_array_primary_dependency  [HEAD]  outcome: passed
call DatabaseApplicationType._import_table_fields(serialized_tables=list[3], id_mapping=dict[5]#7e27b4, import_export_config=ImportExportConfig, external_table_fields_to_import=NoneType#99bf08, deferred_fk_update_collector=DeferredForeignKeyUpdater, progress=Progress) [returned]
  branch br:34ec71ee29c9 L456 `serialized_field["primary"]` = T
  branch br:34ec71ee29c9 L456 `serialized_field["primary"]` = T
  branch br:34ec71ee29c9 L456 `serialized_field["primary"]` = T
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[12]#700575, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#3f2497) [returned] -> #99bf08
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[3]) [returned] -> #99bf08
    branch br:be7d3ee9e3b1 L497 `not field_deps` = T  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[12]#700575) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = T  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[16]#29d905, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#3f2497) [returned] -> #99bf08
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[3]) [returned] -> #99bf08
    branch br:be7d3ee9e3b1 L497 `not field_deps` = T  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[16]#29d905) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call FormulaFieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[26], serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#3f2497) [returned] -> #8b5219
    branch br:49c2edb05730 L6249 `"formula" not in serialized_field` = F
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=set[2]#8b5219, fields_by_name=dict[3]) [returned] -> #8b5219
    branch br:be7d3ee9e3b1 L497 `not field_deps` = F  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = T
  call DeferredFieldImporter.add_deferred_field_import(table=Table, field_name=str#764977, field_dependencies=set[2]#8b5219, import_field_callback=partial) [returned] -> #99bf08
  call FormulaFieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[26], serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#3f2497) [returned] -> #0d70db
    branch br:49c2edb05730 L6249 `"formula" not in serialized_field` = F
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=set[1]#0d70db, fields_by_name=dict[4]) [returned] -> #c2703a
    branch br:be7d3ee9e3b1 L497 `not field_deps` = F  (runtime only: nested function)
    call LinkRowFieldType.get_import_dependency_when_referenced(serialized_field=dict[16]#e7d704, reference_name=str#3e37c7, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#3f2497) [returned] -> #9151ed
      branch br:a0d4e306fb5a L3710 `related_table_id is None or related_table_id not in primary_table_fiel` = F
      branch br:f960d9f63045 L3714 `primary_field_id not in serialized_fields_map` = F
  branch br:47a63ce03fc8 L532 `field_deps` = T
  call DeferredFieldImporter.add_deferred_field_import(table=Table, field_name=str#c0347b, field_dependencies=set[1]#c2703a, import_field_callback=partial) [returned] -> #99bf08
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[12]#0aedaa, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#3f2497) [returned] -> #99bf08
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[4]) [returned] -> #99bf08
    branch br:be7d3ee9e3b1 L497 `not field_deps` = T  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[12]#0aedaa) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = T  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[16]#68cd48, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#3f2497) [returned] -> #99bf08
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[4]) [returned] -> #99bf08
    branch br:be7d3ee9e3b1 L497 `not field_deps` = T  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[16]#68cd48) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[16]#e7d704, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#3f2497) [returned] -> #99bf08
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[4]) [returned] -> #99bf08
    branch br:be7d3ee9e3b1 L497 `not field_deps` = T  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[16]#e7d704) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[12]#fccc70, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#3f2497) [returned] -> #99bf08
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[2]#1f2535) [returned] -> #99bf08
    branch br:be7d3ee9e3b1 L497 `not field_deps` = T  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[12]#fccc70) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = T  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[16]#b5f3d8, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#3f2497) [returned] -> #99bf08
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[2]#1f2535) [returned] -> #99bf08
    branch br:be7d3ee9e3b1 L497 `not field_deps` = T  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[16]#b5f3d8) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call DeferredFieldImporter.run_deferred_field_imports(field_name_fields_mapping=dict[3]) [returned]
    call DeferredFieldImporter.get_all_fields_dependencies(field_name_fields_mapping=dict[3]) [returned] -> #4debb5
      branch br:cbfe8c1c2b07 L68 `via_field_name is not None` = T  (runtime only: file not lowered)
      branch br:cbfe8c1c2b07 L68 `via_field_name is not None` = T  (runtime only: file not lowered)
      branch br:cbfe8c1c2b07 L68 `via_field_name is not None` = T  (runtime only: file not lowered)
    call FieldDependencyHandler.group_dependencies_by_level(dependencies=defaultdict[2]#4debb5) [returned] -> #7e94af
    call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[26]) [returned]
      branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
    call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[26]) [returned]
      branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  branch br:09962e1ae1b2 L589 `field_type.needs_refresh_after_import_serialized` = T
  branch br:09962e1ae1b2 L589 `field_type.needs_refresh_after_import_serialized` = T

### test_snapshot_with_explicit_array_primary_dependency  [BASE]  outcome: passed
call DatabaseApplicationType._import_table_fields(serialized_tables=list[3], id_mapping=dict[5]#7e27b4, import_export_config=ImportExportConfig, external_table_fields_to_import=NoneType#99bf08, deferred_fk_update_collector=DeferredForeignKeyUpdater, progress=Progress) [returned]
  branch br:34ec71ee29c9 L456 `serialized_field["primary"]` = T
  branch br:34ec71ee29c9 L456 `serialized_field["primary"]` = T
  branch br:34ec71ee29c9 L456 `serialized_field["primary"]` = T
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[12]#700575, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#3f2497) [returned] -> #99bf08
  branch br:0771b757bce0 L504 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[12]#700575) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = T  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[16]#29d905, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#3f2497) [returned] -> #99bf08
  branch br:0771b757bce0 L504 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[16]#29d905) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call FormulaFieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[26], serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#3f2497) [returned] -> #8b5219
    branch br:1c6b5568b809 L6226 `"formula" not in serialized_field` = F
  branch br:0771b757bce0 L504 `field_deps` = T
  call DeferredFieldImporter.add_deferred_field_import(table=Table, field_name=str#764977, field_dependencies=set[2]#8b5219, import_field_callback=partial) [returned] -> #99bf08
  call FormulaFieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[26], serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#3f2497) [returned] -> #0d70db
    branch br:1c6b5568b809 L6226 `"formula" not in serialized_field` = F
  branch br:0771b757bce0 L504 `field_deps` = T
  call DeferredFieldImporter.add_deferred_field_import(table=Table, field_name=str#c0347b, field_dependencies=set[1]#0d70db, import_field_callback=partial) [returned] -> #99bf08
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[12]#0aedaa, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#3f2497) [returned] -> #99bf08
  branch br:0771b757bce0 L504 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[12]#0aedaa) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = T  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[16]#68cd48, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#3f2497) [returned] -> #99bf08
  branch br:0771b757bce0 L504 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[16]#68cd48) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[16]#e7d704, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#3f2497) [returned] -> #99bf08
  branch br:0771b757bce0 L504 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[16]#e7d704) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[12]#fccc70, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#3f2497) [returned] -> #99bf08
  branch br:0771b757bce0 L504 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[12]#fccc70) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = T  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[16]#b5f3d8, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#3f2497) [returned] -> #99bf08
  branch br:0771b757bce0 L504 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[16]#b5f3d8) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call DeferredFieldImporter.run_deferred_field_imports(field_name_fields_mapping=dict[3]) [returned]
    call DeferredFieldImporter.get_all_fields_dependencies(field_name_fields_mapping=dict[3]) [returned] -> #152d13
      branch br:cbfe8c1c2b07 L68 `via_field_name is not None` = T  (runtime only: file not lowered)
      branch br:cbfe8c1c2b07 L68 `via_field_name is not None` = T  (runtime only: file not lowered)
      branch br:cbfe8c1c2b07 L68 `via_field_name is not None` = F  (runtime only: file not lowered)
    call FieldDependencyHandler.group_dependencies_by_level(dependencies=defaultdict[2]#152d13) [returned] -> #c537c8
    call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[26]) [returned]
      branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
    call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[26]) [returned]
      branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  branch br:f38c5af64076 L561 `field_type.needs_refresh_after_import_serialized` = T
  branch br:f38c5af64076 L561 `field_type.needs_refresh_after_import_serialized` = T

### test_snapshot_with_implicit_array_primary_dependency  [HEAD]  outcome: passed
call DatabaseApplicationType._import_table_fields(serialized_tables=list[3], id_mapping=dict[5]#7c347f, import_export_config=ImportExportConfig, external_table_fields_to_import=NoneType#99bf08, deferred_fk_update_collector=DeferredForeignKeyUpdater, progress=Progress) [returned]
  branch br:34ec71ee29c9 L456 `serialized_field["primary"]` = T
  branch br:34ec71ee29c9 L456 `serialized_field["primary"]` = T
  branch br:34ec71ee29c9 L456 `serialized_field["primary"]` = T
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[12]#59720c, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #99bf08
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[3]) [returned] -> #99bf08
    branch br:be7d3ee9e3b1 L497 `not field_deps` = T  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[12]#59720c) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = T  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[16]#2496fd, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #99bf08
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[3]) [returned] -> #99bf08
    branch br:be7d3ee9e3b1 L497 `not field_deps` = T  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[16]#2496fd) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call FormulaFieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[26], serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #3241eb
    branch br:49c2edb05730 L6249 `"formula" not in serialized_field` = F
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=set[2]#3241eb, fields_by_name=dict[3]) [returned] -> #8b5219
    branch br:be7d3ee9e3b1 L497 `not field_deps` = F  (runtime only: nested function)
    call LinkRowFieldType.get_import_dependency_when_referenced(serialized_field=dict[16]#2496fd, reference_name=str#1f758b, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #da8a86
      branch br:a0d4e306fb5a L3710 `related_table_id is None or related_table_id not in primary_table_fiel` = F
      branch br:f960d9f63045 L3714 `primary_field_id not in serialized_fields_map` = F
  branch br:47a63ce03fc8 L532 `field_deps` = T
  call DeferredFieldImporter.add_deferred_field_import(table=Table, field_name=str#764977, field_dependencies=set[2]#8b5219, import_field_callback=partial) [returned] -> #99bf08
  call FormulaFieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[26], serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #0d70db
    branch br:49c2edb05730 L6249 `"formula" not in serialized_field` = F
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=set[1]#0d70db, fields_by_name=dict[4]) [returned] -> #c2703a
    branch br:be7d3ee9e3b1 L497 `not field_deps` = F  (runtime only: nested function)
    call LinkRowFieldType.get_import_dependency_when_referenced(serialized_field=dict[16]#306f01, reference_name=str#3e37c7, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #9151ed
      branch br:a0d4e306fb5a L3710 `related_table_id is None or related_table_id not in primary_table_fiel` = F
      branch br:f960d9f63045 L3714 `primary_field_id not in serialized_fields_map` = F
  branch br:47a63ce03fc8 L532 `field_deps` = T
  call DeferredFieldImporter.add_deferred_field_import(table=Table, field_name=str#c0347b, field_dependencies=set[1]#c2703a, import_field_callback=partial) [returned] -> #99bf08
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[12]#4468bb, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #99bf08
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[4]) [returned] -> #99bf08
    branch br:be7d3ee9e3b1 L497 `not field_deps` = T  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[12]#4468bb) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = T  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[16]#17139d, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #99bf08
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[4]) [returned] -> #99bf08
    branch br:be7d3ee9e3b1 L497 `not field_deps` = T  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[16]#17139d) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[16]#306f01, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #99bf08
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[4]) [returned] -> #99bf08
    branch br:be7d3ee9e3b1 L497 `not field_deps` = T  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[16]#306f01) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[12]#0116a9, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #99bf08
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[2]#4757e9) [returned] -> #99bf08
    branch br:be7d3ee9e3b1 L497 `not field_deps` = T  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[12]#0116a9) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = T  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[16]#402253, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #99bf08
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[2]#4757e9) [returned] -> #99bf08
    branch br:be7d3ee9e3b1 L497 `not field_deps` = T  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[16]#402253) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call DeferredFieldImporter.run_deferred_field_imports(field_name_fields_mapping=dict[3]) [returned]
    call DeferredFieldImporter.get_all_fields_dependencies(field_name_fields_mapping=dict[3]) [returned] -> #dc0f2d
      branch br:cbfe8c1c2b07 L68 `via_field_name is not None` = T  (runtime only: file not lowered)
      branch br:cbfe8c1c2b07 L68 `via_field_name is not None` = T  (runtime only: file not lowered)
      branch br:cbfe8c1c2b07 L68 `via_field_name is not None` = T  (runtime only: file not lowered)
    call FieldDependencyHandler.group_dependencies_by_level(dependencies=defaultdict[2]#dc0f2d) [returned] -> #62601a
    call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[26]) [returned]
      branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
    call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[26]) [returned]
      branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  branch br:09962e1ae1b2 L589 `field_type.needs_refresh_after_import_serialized` = T
  branch br:09962e1ae1b2 L589 `field_type.needs_refresh_after_import_serialized` = T

### test_snapshot_with_implicit_array_primary_dependency  [BASE]  outcome: failed: django.db.utils.DataError raised in FormulaFieldType.after_rows_imported <- DatabaseApplicationType._after_rows_imported <- DatabaseApplicationType._import_table_rows <- DatabaseApplicationType.import_tables_serialized <- DatabaseApplicationType.import_serialized <- SnapshotHandler.perform_create
call DatabaseApplicationType._import_table_fields(serialized_tables=list[3], id_mapping=dict[5]#7c347f, import_export_config=ImportExportConfig, external_table_fields_to_import=NoneType#99bf08, deferred_fk_update_collector=DeferredForeignKeyUpdater, progress=Progress) [returned]
  branch br:34ec71ee29c9 L456 `serialized_field["primary"]` = T
  branch br:34ec71ee29c9 L456 `serialized_field["primary"]` = T
  branch br:34ec71ee29c9 L456 `serialized_field["primary"]` = T
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[12]#59720c, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #99bf08
  branch br:0771b757bce0 L504 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[12]#59720c) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = T  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[16]#2496fd, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #99bf08
  branch br:0771b757bce0 L504 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[16]#2496fd) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call FormulaFieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[26], serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #3241eb
    branch br:1c6b5568b809 L6226 `"formula" not in serialized_field` = F
  branch br:0771b757bce0 L504 `field_deps` = T
  call DeferredFieldImporter.add_deferred_field_import(table=Table, field_name=str#764977, field_dependencies=set[2]#3241eb, import_field_callback=partial) [returned] -> #99bf08
  call FormulaFieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[26], serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #0d70db
    branch br:1c6b5568b809 L6226 `"formula" not in serialized_field` = F
  branch br:0771b757bce0 L504 `field_deps` = T
  call DeferredFieldImporter.add_deferred_field_import(table=Table, field_name=str#c0347b, field_dependencies=set[1]#0d70db, import_field_callback=partial) [returned] -> #99bf08
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[12]#4468bb, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #99bf08
  branch br:0771b757bce0 L504 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[12]#4468bb) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = T  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[16]#17139d, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #99bf08
  branch br:0771b757bce0 L504 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[16]#17139d) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[16]#306f01, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #99bf08
  branch br:0771b757bce0 L504 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[16]#306f01) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[12]#0116a9, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #99bf08
  branch br:0771b757bce0 L504 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[12]#0116a9) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = T  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[16]#402253, serialized_fields_map=dict[9], primary_table_fields_map=dict[3]#9011a8) [returned] -> #99bf08
  branch br:0771b757bce0 L504 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[16]#402253) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call DeferredFieldImporter.run_deferred_field_imports(field_name_fields_mapping=dict[3]) [returned]
    call DeferredFieldImporter.get_all_fields_dependencies(field_name_fields_mapping=dict[3]) [returned] -> #6f72c5
      branch br:cbfe8c1c2b07 L68 `via_field_name is not None` = T  (runtime only: file not lowered)
      branch br:cbfe8c1c2b07 L68 `via_field_name is not None` = F  (runtime only: file not lowered)
      branch br:cbfe8c1c2b07 L68 `via_field_name is not None` = F  (runtime only: file not lowered)
    call FieldDependencyHandler.group_dependencies_by_level(dependencies=defaultdict[2]#6f72c5) [returned] -> #001017
    call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[26]) [returned]
      branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
    call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[10], serialized_field=dict[26]) [returned]
      branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  branch br:f38c5af64076 L561 `field_type.needs_refresh_after_import_serialized` = T
  branch br:f38c5af64076 L561 `field_type.needs_refresh_after_import_serialized` = T

### test_can_import_database_with_formula_dependencies  [HEAD]  outcome: passed
call DatabaseApplicationType._import_table_fields(serialized_tables=list[2], id_mapping=dict[5]#b597f6, import_export_config=ImportExportConfig#bbc10d, external_table_fields_to_import=NoneType#99bf08, deferred_fk_update_collector=DeferredForeignKeyUpdater, progress=Progress) [returned]
  branch br:34ec71ee29c9 L456 `serialized_field["primary"]` = T
  branch br:34ec71ee29c9 L456 `serialized_field["primary"]` = T
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[6]#cd2376, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #99bf08
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[4]#291c15) [returned] -> #99bf08
    branch br:be7d3ee9e3b1 L497 `not field_deps` = T  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[6]#cd2376) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = T  (runtime only: nested function)
  call FormulaFieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[8]#44a32e, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #c66ae3
    branch br:49c2edb05730 L6249 `"formula" not in serialized_field` = F
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=set[1]#c66ae3, fields_by_name=dict[4]#291c15) [returned] -> #c66ae3
    branch br:be7d3ee9e3b1 L497 `not field_deps` = F  (runtime only: nested function)
    call FieldType.get_import_dependency_when_referenced(serialized_field=dict[6]#5a1d44, reference_name=str#006842, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #99bf08
  branch br:47a63ce03fc8 L532 `field_deps` = T
  call DeferredFieldImporter.add_deferred_field_import(table=Table, field_name=str#c2f755, field_dependencies=set[1]#c66ae3, import_field_callback=partial) [returned] -> #99bf08
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[6]#5a1d44, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #99bf08
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[4]#291c15) [returned] -> #99bf08
    branch br:be7d3ee9e3b1 L497 `not field_deps` = T  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[6]#5a1d44) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[8]#c3fc04, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #99bf08
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[4]#291c15) [returned] -> #99bf08
    branch br:be7d3ee9e3b1 L497 `not field_deps` = T  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[8]#c3fc04) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[6]#a3ead1, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #99bf08
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[4]#8d7b81) [returned] -> #99bf08
    branch br:be7d3ee9e3b1 L497 `not field_deps` = T  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[6]#a3ead1) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = T  (runtime only: nested function)
  call FormulaFieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[9]#f40287, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #edecd0
    branch br:49c2edb05730 L6249 `"formula" not in serialized_field` = F
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=set[1]#edecd0, fields_by_name=dict[4]#8d7b81) [returned] -> #edecd0
    branch br:be7d3ee9e3b1 L497 `not field_deps` = F  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = T
  call DeferredFieldImporter.add_deferred_field_import(table=Table, field_name=str#de0c67, field_dependencies=set[1]#edecd0, import_field_callback=partial) [returned] -> #99bf08
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[8]#9c3aa8, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #99bf08
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=NoneType#99bf08, fields_by_name=dict[4]#8d7b81) [returned] -> #99bf08
    branch br:be7d3ee9e3b1 L497 `not field_deps` = T  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[8]#9c3aa8) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call LookupFieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[10]#fa755d, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #ae7de4
    branch br:df188b1f6d10 L6942 `through_field_id is None or through_field_id not in serialized_fields_` = F
    branch br:b0d9d883d08b L6951 `target_field_id is None or target_field_id not in serialized_fields_ma` = F
  call DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies(field_deps=set[1]#ae7de4, fields_by_name=dict[4]#8d7b81) [returned] -> #ae7de4
    branch br:be7d3ee9e3b1 L497 `not field_deps` = F  (runtime only: nested function)
  branch br:47a63ce03fc8 L532 `field_deps` = T
  call DeferredFieldImporter.add_deferred_field_import(table=Table, field_name=str#1ff959, field_dependencies=set[1]#ae7de4, import_field_callback=partial) [returned] -> #99bf08
  call DeferredFieldImporter.run_deferred_field_imports(field_name_fields_mapping=dict[2]) [returned]
    call DeferredFieldImporter.get_all_fields_dependencies(field_name_fields_mapping=dict[2]) [returned] -> #1b93ed
      branch br:cbfe8c1c2b07 L68 `via_field_name is not None` = F  (runtime only: file not lowered)
      branch br:cbfe8c1c2b07 L68 `via_field_name is not None` = T  (runtime only: file not lowered)
      branch br:cbfe8c1c2b07 L68 `via_field_name is not None` = T  (runtime only: file not lowered)
    call FieldDependencyHandler.group_dependencies_by_level(dependencies=defaultdict[3]#1b93ed) [returned] -> #2e88e4
    call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[8]#44a32e) [returned]
      branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
    call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[9]#f40287) [returned]
      branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
    call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[10]#fa755d) [returned]
      branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  branch br:09962e1ae1b2 L589 `field_type.needs_refresh_after_import_serialized` = T
  branch br:09962e1ae1b2 L589 `field_type.needs_refresh_after_import_serialized` = T
  branch br:09962e1ae1b2 L589 `field_type.needs_refresh_after_import_serialized` = T

### test_can_import_database_with_formula_dependencies  [BASE]  outcome: passed
call DatabaseApplicationType._import_table_fields(serialized_tables=list[2], id_mapping=dict[5]#b597f6, import_export_config=ImportExportConfig#bbc10d, external_table_fields_to_import=NoneType#99bf08, deferred_fk_update_collector=DeferredForeignKeyUpdater, progress=Progress) [returned]
  branch br:34ec71ee29c9 L456 `serialized_field["primary"]` = T
  branch br:34ec71ee29c9 L456 `serialized_field["primary"]` = T
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[6]#cd2376, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #99bf08
  branch br:0771b757bce0 L504 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[6]#cd2376) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = T  (runtime only: nested function)
  call FormulaFieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[8]#44a32e, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #c66ae3
    branch br:1c6b5568b809 L6226 `"formula" not in serialized_field` = F
  branch br:0771b757bce0 L504 `field_deps` = T
  call DeferredFieldImporter.add_deferred_field_import(table=Table, field_name=str#c2f755, field_dependencies=set[1]#c66ae3, import_field_callback=partial) [returned] -> #99bf08
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[6]#5a1d44, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #99bf08
  branch br:0771b757bce0 L504 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[6]#5a1d44) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[8]#c3fc04, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #99bf08
  branch br:0771b757bce0 L504 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[8]#c3fc04) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[6]#a3ead1, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #99bf08
  branch br:0771b757bce0 L504 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[6]#a3ead1) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = T  (runtime only: nested function)
  call FormulaFieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[9]#f40287, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #edecd0
    branch br:1c6b5568b809 L6226 `"formula" not in serialized_field` = F
  branch br:0771b757bce0 L504 `field_deps` = T
  call DeferredFieldImporter.add_deferred_field_import(table=Table, field_name=str#de0c67, field_dependencies=set[1]#edecd0, import_field_callback=partial) [returned] -> #99bf08
  call FieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[8]#9c3aa8, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #99bf08
  branch br:0771b757bce0 L504 `field_deps` = F
  call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[8]#9c3aa8) [returned]
    branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  call LookupFieldType.get_field_depdendencies_before_import_serialized(serialized_field=dict[10]#fa755d, serialized_fields_map=dict[8]#31245e, primary_table_fields_map=dict[2]#7288d8) [returned] -> #ae7de4
    branch br:ef6ec241fb07 L6919 `through_field_id is None or through_field_id not in serialized_fields_` = F
    branch br:0f9dcde0ef18 L6928 `target_field_id is None or target_field_id not in serialized_fields_ma` = F
  branch br:0771b757bce0 L504 `field_deps` = T
  call DeferredFieldImporter.add_deferred_field_import(table=Table, field_name=str#1ff959, field_dependencies=set[1]#ae7de4, import_field_callback=partial) [returned] -> #99bf08
  call DeferredFieldImporter.run_deferred_field_imports(field_name_fields_mapping=dict[2]) [returned]
    call DeferredFieldImporter.get_all_fields_dependencies(field_name_fields_mapping=dict[2]) [returned] -> #1b93ed
      branch br:cbfe8c1c2b07 L68 `via_field_name is not None` = F  (runtime only: file not lowered)
      branch br:cbfe8c1c2b07 L68 `via_field_name is not None` = T  (runtime only: file not lowered)
      branch br:cbfe8c1c2b07 L68 `via_field_name is not None` = T  (runtime only: file not lowered)
    call FieldDependencyHandler.group_dependencies_by_level(dependencies=defaultdict[3]#1b93ed) [returned] -> #2e88e4
    call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[8]#44a32e) [returned]
      branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
    call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[9]#f40287) [returned]
      branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
    call DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized(serialized_table=dict[8], serialized_field=dict[10]#fa755d) [returned]
      branch br:3f16965dcd1f L480 `table_instance not in table_fields_by_name` = F  (runtime only: nested function)
  branch br:f38c5af64076 L561 `field_type.needs_refresh_after_import_serialized` = T
  branch br:f38c5af64076 L561 `field_type.needs_refresh_after_import_serialized` = T
  branch br:f38c5af64076 L561 `field_type.needs_refresh_after_import_serialized` = T
```

Withheld (observed at head and base, not shown): test_snapshot_with_implicit_array_primary_dependency_two_links_deep, test_duplicate_application_with_implicit_array_primary_dependency

## The change (git diff e9ef2697..70c81307 -- backend/src)

```diff
diff --git a/backend/src/baserow/contrib/database/application_types.py b/backend/src/baserow/contrib/database/application_types.py
index 406301204..52df49d19 100755
--- a/backend/src/baserow/contrib/database/application_types.py
+++ b/backend/src/baserow/contrib/database/application_types.py
@@ -486,18 +486,46 @@ class DatabaseApplicationType(ApplicationType):
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
diff --git a/backend/src/baserow/contrib/database/fields/field_types.py b/backend/src/baserow/contrib/database/fields/field_types.py
index c37655e0e..2af36bafe 100755
--- a/backend/src/baserow/contrib/database/fields/field_types.py
+++ b/backend/src/baserow/contrib/database/fields/field_types.py
@@ -3693,6 +3693,29 @@ class LinkRowFieldType(
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
diff --git a/backend/src/baserow/contrib/database/fields/registries.py b/backend/src/baserow/contrib/database/fields/registries.py
index 8d9054d60..d4861aa61 100644
--- a/backend/src/baserow/contrib/database/fields/registries.py
+++ b/backend/src/baserow/contrib/database/fields/registries.py
@@ -1593,12 +1593,46 @@ class FieldType(
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
```

## Source at HEAD: backend/src/baserow/contrib/database/application_types.py lines 404-597 (`_import_table_fields`)

```python
 404          created application.
 405  
 406          :param user: The user that creates the application.
 407          :param application: The application to initialize with data.
 408          """
 409  
 410          with translation.override(user.profile.language):
 411              first_table_name = _("Table")
 412  
 413          return TableHandler().create_table(
 414              user, application, first_table_name, fill_example=True
 415          )
 416  
 417      def _import_table_fields(
 418          self,
 419          serialized_tables: List[Dict[str, Any]],
 420          id_mapping: Dict[str, Any],
 421          import_export_config: ImportExportConfig,
 422          external_table_fields_to_import: List[Tuple[Table, Dict[str, Any]]],
 423          deferred_fk_update_collector: DeferredForeignKeyUpdater,
 424          progress: Progress,
 425      ) -> ImportedFields:
 426          """
 427          Import the fields from the serialized data in the correct order based on their
 428          dependencies.
 429  
 430          :param serialized_tables: The serialized tables to import the fields from.
 431          :param id_mapping: A mapping of any table ids that might be referenced in
 432              serialized_tables to their new/existing ids to use in this import.
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
```

## Source: backend/src/baserow/contrib/database/fields/utils/deferred_field_importer.py (unchanged by the change)

```python
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

## Source at HEAD: import-dependency methods of formula-like field types (field_types.py)

```python
# class LinkRowFieldType
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

# class FormulaFieldType
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

# class CountFieldType
6406      def get_field_depdendencies_before_import_serialized(
6407          self,
6408          serialized_field: Dict[str, Any],
6409          serialized_fields_map: Dict[int, Dict[str, Any]],
6410          primary_table_fields_map: Dict[int, int],
6411      ) -> Optional[Set[Tuple[Union[int, str], Union[int, str]]]]:
6412          through_field_id = serialized_field.get("through_field_id", None)
6413          if through_field_id is None or through_field_id not in serialized_fields_map:
6414              return None  # broken reference
6415          through_field = serialized_fields_map[through_field_id]
6416          through_field_name = through_field["name"]
6417          related_table_id = through_field.get("link_row_table_id", None)
6418  
6419          # it means we're targeting a field that already exists before the import
6420          # (i.e. duplicating a table/field)
6421          if related_table_id is None or related_table_id not in primary_table_fields_map:
6422              return None
6423  
6424          target_field_id = primary_table_fields_map[related_table_id]
6425          target_field = serialized_fields_map[target_field_id]
6426          target_field_name = target_field["name"]
6427          return {(target_field_name, through_field_name)}

# class RollupFieldType
6616      def get_field_depdendencies_before_import_serialized(
6617          self,
6618          serialized_field: Dict[str, Any],
6619          serialized_fields_map: Dict[int, Dict[str, Any]],
6620          primary_table_fields_map: Dict[int, int],
6621      ) -> Optional[Set[Tuple[Union[int, str], Union[int, str]]]]:
6622          through_field_id = serialized_field.get("through_field_id", None)
6623          if through_field_id is None or through_field_id not in serialized_fields_map:
6624              return None  # broken reference
6625  
6626          via_field = serialized_fields_map[through_field_id]
6627          via_field_name = via_field["name"]
6628          target_field_id = serialized_field.get("target_field_id", None)
6629  
6630          # it means we're targeting a field that already exists before the import
6631          # (i.e. duplicating a table/field)
6632          if target_field_id is None or target_field_id not in serialized_fields_map:
6633              return None
6634  
6635          target_field = serialized_fields_map[target_field_id]
6636          target_field_name = target_field["name"]
6637          return {(target_field_name, via_field_name)}

# class LookupFieldType
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
```

## Source: backend/tests/baserow/core/snapshots/test_snapshot_array_formula_import.py (added by the change; the same file was run at base)

```python
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

## Source: backend/tests/baserow/contrib/database/field/dependencies/test_field_dependency_handler.py::test_can_import_database_with_formula_dependencies

```python
 799  @pytest.mark.django_db
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
```
