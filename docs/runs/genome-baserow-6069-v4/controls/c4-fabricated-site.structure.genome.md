# Behavioral Genome — baserow #6069 import dependency via link row (`diffgenome-genome/0`, experimental)

Entry `_import_table_fields`. Semantic items proposed by `claude-opus-5-5` from a bounded context bundle (sha `42e94518e62ff39b`); every status below was assigned by the deterministic checker, not by the model. Statuses: observed · static · HYPOTHESIS · supported (all citations check out) · VERIFIED (cites an `if` site and both branches observed, no contradiction) · REJECTED (contradicted by an execution).

## Entities (collector facts)


## Variables

- `field_is_primary` (input) — supported
- `has_import_deps` (derived) ↔ observed `None` (is_set) — supported
- `reference_expanded` (derived) ↔ observed `None` (changed_from:arg:field_deps) — supported
- `first_import_in_table` (derived) — supported
- `link_target_outside_import` (input) — supported
- `target_primary_missing` (input) — supported
- `implied_dependency_found` (derived) := `!link_target_outside_import && !target_primary_missing` — supported
- `needs_refresh` (input) — supported

## Data dependencies


## Decisions, in path order

### d_primary · `field_is_primary` at `DatabaseApplicationType._import_table_fields` site `br:34ec71ee29c9` — supported

- TRUE : (no call); continue — primary_table_fields_map[table id] = primary field id
- FALSE: (no call); continue — field only recorded in database_fields_map
- status: every cited reference checks out (branch); site: br:34ec71ee29c9 (given); not verified: outcome false never observed at br:34ec71ee29c9; agrees with the observed outcome at 8 occurrence evaluation(s)
  - ✓ branch None → None

### d_expand_empty · `!has_import_deps` at `DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies` site `br:be7d3ee9e3b1` — VERIFIED

- TRUE : (no call); never LinkRowFieldType.get_import_dependency_when_referenced; **stop** — returns the empty/None dependencies unchanged
- FALSE: (no call); continue — each same-table name reference is asked for the dependency it implies; the implied one replaces it
- status: site br:be7d3ee9e3b1 (`not field_deps`) observed true in 3 and false in 3 execution(s); the predicate agrees with the observed outcome 26 time(s) from observed state and in 3 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None

### d_link_outside · `link_target_outside_import` at `LinkRowFieldType.get_import_dependency_when_referenced` site `br:000000000000` — HYPOTHESIS

- TRUE : (no call); **stop** — returns None: target table pre-exists, nothing to order
- FALSE: (no call); continue — target table is imported; look up its primary
- status: names a decision site that does not exist: br:000000000000
  - ✓ branch None → None

### d_primary_missing · `target_primary_missing` at `LinkRowFieldType.get_import_dependency_when_referenced` site `br:f960d9f63045` — supported

- TRUE : (no call); **stop** — returns None
- FALSE: (no call); continue — returns (target primary name, link field name): the referencing field now depends on the linked table's primary via the link
- status: every cited reference checks out (branch); site: br:f960d9f63045 (given); not verified: predicate disagrees with observed outcomes: test_snapshot_with_explicit_array_primary_dependency: replayed outcome sequence differs; test_can_import_database_with_formula_dependencies: replayed outcome sequence differs; agrees with the observed outcome at 3 occurrence evaluation(s)
  - ✓ branch None → None

### d_defer · `has_import_deps` at `DatabaseApplicationType._import_table_fields` site `br:47a63ce03fc8` — VERIFIED

- TRUE : (no call); never DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized; continue — field deferred with its (expanded) dependencies
- FALSE: (no call); never DeferredFieldImporter.add_deferred_field_import; continue — field imported immediately
- status: site br:47a63ce03fc8 (`field_deps`) observed true in 3 and false in 3 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 3 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ control None → deferred_field_importer.add_deferred_field_import
  - ✓ control None → _import_field_serialized
  - ✓ branch None → None

### d_first_field · `first_import_in_table` at `DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized` site `br:3f16965dcd1f` — VERIFIED

- TRUE : (no call); continue — creates the table's bucket in table_fields_by_name
- FALSE: (no call); continue — table bucket already exists
- status: site br:3f16965dcd1f (`table_instance not in table_fields_by_name`) observed true in 3 and false in 3 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 3 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None

### d_refresh · `needs_refresh` at `DatabaseApplicationType._import_table_fields` site `br:09962e1ae1b2` — supported

- TRUE : (no call); continue — field_instance.refresh_from_db()
- FALSE: (no call); continue — no refresh
- status: every cited reference checks out (branch); site: br:09962e1ae1b2 (given); not verified: outcome false never observed at br:09962e1ae1b2; agrees with the observed outcome at 7 occurrence evaluation(s)
  - ✓ branch None → None

## Behavioral rules

- **rule_defer Fields with dependencies are deferred, others imported at once** — supported
  - when `has_import_deps`
  - then add_deferred_field_import is called and the field is imported later by run_deferred_field_imports in dependency-level order; otherwise _import_field_serialized runs immediately
  - summarizes d_defer; every cited reference checks out (control)
- **rule_implied_link A by-name reference to a link row field implies a dependency on the linked table's primary** — supported
  - when `has_import_deps && !link_target_outside_import && !target_primary_missing`
  - then (link name, None) is rewritten to (target primary name, link name); the referencing field is ordered after the linked table's primary, which may itself be a deferred (array) formula
  - summarizes d_primary_missing; every cited reference checks out (boundary, branch)
- **rule_phenotype Missing implied dependency makes the consumer recalculate before its producer (base failure)** — supported
  - when `reference_expanded`
  - then base: consumer and linked-table primary formula land in the same dependency level, the consumer recalculates against a still-NULL array column and import_tables_serialized raises django.db.utils.DataError in after_rows_imported; head: the implied dependency orders the primary first and import_tables_serialized returns
- **rule_table_bucket First field instance of a table creates its bucket** — supported
  - when `first_import_in_table`
  - then table_fields_by_name[table] = {} before recording the field
  - summarizes d_first_field; every cited reference checks out (branch)

## Regimes (behavioral equivalence classes)

- **No by-name link reference to expand (dependencies already explicit)** — 2 test(s): test_snapshot_with_explicit_array_primary_dependency, test_can_import_database_with_formula_dependencies — supported
- **Consumer references a link row field by name whose target primary is a deferred array formula** — 3 test(s): test_snapshot_with_implicit_array_primary_dependency, test_snapshot_with_implicit_array_primary_dependency_two_links_deep, test_duplicate_application_with_implicit_array_primary_dependency — supported

## Procedures (composition)

- `DatabaseApplicationType._import_table_fields`: R:r_primary_scan → R:r_field → call:DeferredFieldImporter.run_deferred_field_imports → R:r_refresh — supported
- `DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies`: D:d_expand_empty — supported
- `LinkRowFieldType.get_import_dependency_when_referenced`: D:d_link_outside — supported
- `DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized`: D:d_first_field — supported
- `DeferredFieldImporter.run_deferred_field_imports`: call:DeferredFieldImporter.get_all_fields_dependencies → R:r_deferred_import — supported

## Unknown / incomplete (as stated by the model)

- Whether and which get_import_dependency_when_referenced is called inside _expand_implied_import_dependencies: It depends on iterating the dependency set and, per element, on via being None and on the referenced field's type (link_row vs default FieldType). There is no decision site for that dispatch, and iterating collections is not expressible. So the model calls LinkRowFieldType whenever deps are non-empty. This over-predicts calls where no dependency is a same-table name reference (explicit test's ActiveChildren, the formula-dependency test), and predicts LinkRow where FieldType's default was called.
- Dependency-level ordering in run_deferred_field_imports / group_dependencies_by_level: The failure mechanism (consumer and producer in the same level, relative order within a level) is relation-valued over field identities and cannot be stated. The base DataError is claimed only as a phenotype.
- Where the base failure surfaces: DataError is raised in FormulaFieldType.after_rows_imported during _import_table_rows, outside the modeled entities. _import_table_fields itself returns at both revisions.
- first_import_in_table: This is table_fields_by_name membership per table identity (closure state across calls and tables). It is supplied as a per-occurrence fact, not derived by transitions.
- Counts of br:34ec71ee29c9 and br:09962e1ae1b2 evaluations: Only true evaluations were observed: one per table for the primary check and one per formula-like field for the refresh. Occurrence counts for withheld tests follow that pattern (3 tables; 2 formula fields) rather than the full field loop.
- DeferredFieldImporter.get_all_fields_dependencies via-field branch (br:cbfe8c1c2b07): This is not a required site and it iterates each deferred field's dependency set. It is left unmodeled (the call is recorded and skipped).
