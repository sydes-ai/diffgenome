# Behavioral Genome — baserow #6069 import dependency via link row (`diffgenome-genome/0`, experimental)

Entry `_import_table_fields`. Semantic items proposed by `claude-opus-5-5` from a bounded context bundle (sha `c90d89e1a1d10cbf`); every status below was assigned by the deterministic checker, not by the model. Statuses: observed · static · HYPOTHESIS · supported (all citations check out) · VERIFIED (cites an `if` site and both branches observed, no contradiction) · REJECTED (contradicted by an execution).

## Entities (collector facts)


## Variables

- `formula_present` (input) — supported
- `through_in_import` (input) — supported
- `target_in_import` (input) — supported
- `has_raw_deps` (input) — supported
- `has_deps` (derived) := `has_raw_deps` — supported
- `link_table_in_import` (input) — supported
- `link_primary_serialized` (input) — supported
- `implied_primary_dep` (state) — supported
- `explicit_primary_lookup` (input) — supported
- `implicit_link_reference` (input) — supported
- `consumer_ordered_after_primary` (derived) := `!implicit_link_reference || explicit_primary_lookup || implied_primary_dep` — supported

## Data dependencies


## Decisions, in path order

### d_formula_has_formula · `!formula_present` at `FormulaFieldType.get_field_depdendencies_before_import_serialized` site `br:49c2edb05730` — supported

- TRUE : NotImplementedError; never FormulaHandler.get_dependencies_field_names; **stop** — raise: formula subtype must implement
- FALSE: FormulaHandler.get_dependencies_field_names; never NotImplementedError; continue — returns the set of (name, via) references parsed from the formula
- status: every cited reference checks out (branch, control); site: br:49c2edb05730 (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ branch None → None
  - ✓ control None → FormulaHandler.get_dependencies_field_names

### d_lookup_through · `!through_in_import` at `LookupFieldType.get_field_depdendencies_before_import_serialized` site `br:df188b1f6d10` — supported

- TRUE : (no call); **stop** — returns None (broken reference): no deps
- FALSE: (no call); continue — continue to target check
- status: every cited reference checks out (branch); site: br:df188b1f6d10 (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ branch None → None

### d_expand_empty · `!has_raw_deps` at `DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies` site `br:be7d3ee9e3b1` — REJECTED

- TRUE : (no call); never LinkRowFieldType.get_import_dependency_when_referenced, FieldType.get_import_dependency_when_referenced; continue — returns field_deps unchanged (None); no referenced field type is consulted
- FALSE: (no call); continue — for each (name, None) whose name is a field of the same table, asks that field's type for an implied dependency; replaces the reference with it if not None
- status: contradicted by observed branches: tests/baserow/contrib/database/field/dependencies/test_field_dependency_handler.py::test_can_import_database_with_formula_dependencies: FieldType.get_import_dependency_when_referenced ran after br:be7d3ee9e3b1=True; tests/baserow/core/snapshots/test_snapshot_array_formula_import.py::test_snapshot_with_explicit_array_primary_dependency: LinkRowFieldType.get_import_dependency_when_referenced ran after br:be7d3ee9e3b1=True; tests/baserow/core/snapshots/test_snapshot_array_formula_import.py::test_snapshot_with_implicit_array_primary_dependency: LinkRowFieldType.get_import_dependency_when_referenced ran after br:be7d3ee9e3b1=True
  - ✓ source backend/src/baserow/contrib/database/application_types.py:497 `if not field_deps:`
  - ✓ branch None → None
  - ✓ branch None → None

### d_link_table_in_import · `!link_table_in_import` at `LinkRowFieldType.get_import_dependency_when_referenced` site `br:a0d4e306fb5a` — supported

- TRUE : (no call); **stop** — returns None: linked table pre-exists the import, reference kept as (name, None)
- FALSE: (no call); continue — look up linked table's primary field id
- status: every cited reference checks out (branch, dataflow); site: br:a0d4e306fb5a (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ dataflow None → None
  - ✓ branch None → None

### d_lookup_target · `!target_in_import` at `LookupFieldType.get_field_depdendencies_before_import_serialized` site `br:b0d9d883d08b` — supported

- TRUE : (no call); **stop** — returns None: target pre-exists the import
- FALSE: (no call); continue — returns {(target_name, via_name)}
- status: every cited reference checks out (branch); site: br:b0d9d883d08b (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ branch None → None

### d_defer_field · `has_deps` at `DatabaseApplicationType._import_table_fields` site `br:47a63ce03fc8` — REJECTED

- TRUE : DeferredFieldImporter.add_deferred_field_import; never DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized; continue — field is deferred with its (expanded) dependency set
- FALSE: DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized; never DeferredFieldImporter.add_deferred_field_import; continue — field imported immediately (level 0)
- status: contradicted by observed branches: tests/baserow/contrib/database/field/dependencies/test_field_dependency_handler.py::test_can_import_database_with_formula_dependencies: DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized ran after br:47a63ce03fc8=True; tests/baserow/contrib/database/field/dependencies/test_field_dependency_handler.py::test_can_import_database_with_formula_dependencies: DeferredFieldImporter.add_deferred_field_import ran after br:47a63ce03fc8=False; tests/baserow/core/snapshots/test_snapshot_array_formula_import.py::test_snapshot_with_explicit_array_primary_dependency: DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized ran after br:47a63ce03fc8=True
  - ✓ control None → deferred_field_importer.add_deferred_field_import
  - ✓ control None → _import_field_serialized
  - ✓ dataflow None → None
  - ✓ branch None → None
  - ✓ branch None → None

## Behavioral rules

- **r_defer_iff_deps A field is deferred iff its type reports dependencies** — supported
  - when `has_raw_deps`
  - then add_deferred_field_import called with the expanded set; otherwise _import_field_serialized called immediately
  - summarizes d_defer_field; every cited reference checks out (branch)
- **r_link_reference_expands A by-name reference to a same-table link_row field becomes a dependency on the linked primary** — supported
  - when `link_table_in_import && link_primary_serialized`
  - then (LinkField, None) replaced by (LinkedPrimary, LinkField); implied_primary_dep := true
  - summarizes d_link_primary_serialized; every cited reference checks out (branch)
- **r_non_link_reference_unchanged References to non-link fields, or with a via, are kept as-is** — supported
  - when `has_raw_deps`
  - then FieldType.get_import_dependency_when_referenced returns None for non-link types; dependency unchanged; (name, via) with via set is never consulted
  - summarizes d_expand_empty; every cited reference checks out (branch)
- **r_ordering_phenotype A consumer must be levelled after the primary it reads through a link** — supported
  - when `implicit_link_reference && !explicit_primary_lookup && !implied_primary_dep`
  - then base: consumer depends only on already-imported level-0 fields, so it lands in the same deferred level as the linked table's primary formula and may be recalculated before that column is populated -> DataError in FormulaFieldType.after_rows_imported; head: implied (primary, link) dependency makes the consumer's level strictly greater; import succeeds

## Regimes (behavioral equivalence classes)

- **Formula references a link_row field by name; linked primary is a deferred formula in the import** — 3 test(s): test_snapshot_with_implicit_array_primary_dependency, test_snapshot_with_implicit_array_primary_dependency_two_links_deep, test_duplicate_application_with_implicit_array_primary_dependency — supported
- **Dependency graph already complete without expansion** — 2 test(s): test_snapshot_with_explicit_array_primary_dependency, test_can_import_database_with_formula_dependencies — supported

## State transitions

- **t_expand_preserves_emptiness** `DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies`: `has_deps := has_raw_deps` — supported
- **t_link_implies_primary** `LinkRowFieldType.get_import_dependency_when_referenced` when `link_table_in_import && link_primary_serialized`: `implied_primary_dep := true` — supported

## Procedures (composition)

- `FormulaFieldType.get_field_depdendencies_before_import_serialized`: D:d_formula_has_formula — supported
- `LookupFieldType.get_field_depdendencies_before_import_serialized`: D:d_lookup_through → D:d_lookup_target — supported
- `DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies`: T:t_expand_preserves_emptiness → D:d_expand_empty → D:d_defer_field — supported
- `LinkRowFieldType.get_import_dependency_when_referenced`: D:d_link_table_in_import → T:t_link_implies_primary — supported

## Unknown / incomplete (as stated by the model)

- Per-reference dispatch inside _expand_implied_import_dependencies (whether a referenced type method is called, and which type): Lines 502-507 are expressions (conditional expression and `and`), not `if` statements, so no site id exists; the genome cannot put a sited decision there. I list the referenced-type call as its own scenario call after the expand call, and place the br:47a63ce03fc8 decision inside the expand procedure, so predicted call nesting/order around add_deferred_field_import differs from the trace even though per-site outcome sequences match.
- br:cbfe8c1c2b07 (via_field_name is not None) in DeferredFieldImporter.get_all_fields_dependencies: This site directly shows the phenotype (base implicit: T,F,F; head: T,T,T), but its evaluation order follows dict/set iteration over deferred fields and their dependency sets, which is not determined by anything I can express without loops or sets; left uncovered.
- Why the same-level order at base puts the consumer before the linked primary: group_dependencies_by_level is not shown; within a level the order is not derivable from the bundle. The base failure is attributed to lack of ordering, not to a proven deterministic misordering; the withheld two-links-deep base outcome is predicted by analogy.
- Mechanism of the DataError: It is raised in FormulaFieldType.after_rows_imported, outside _import_table_fields; the link between field import order and row-phase recalculation (e.g. formula type/ internal formula computed against a not-yet-typed primary) is inferred from the test docstring, not traced.
- Duplication path facts: Assumed that duplicate_application serializes link_row_table_id with old table ids matching serialized_table ids, so link_table_in_import holds; not observable in the bundle (the LinkRow docstring says a missing table corresponds to duplicating a table/field, which is a different case).
- Sets, names, and value-level dependency content: The format has booleans/integers only and no loops, so the actual dependency tuples, the rewrite (LinkField,None)->(Primary,LinkField), and the level assignment of the deferred graph are expressed only as the boolean implied_primary_dep and a derived ordering flag.
- br:34ec71ee29c9 and br:09962e1ae1b2: Deliberately not covered: they are unchanged by the change and their observed evaluation counts (e.g. only T recorded for the primary check) do not map onto a per-field call list I can state reliably.
