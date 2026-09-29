# Behavioral Genome — baserow #6069 import dependency via link row (`diffgenome-genome/0`, experimental)

Entry `_import_table_fields`. Semantic items proposed by `claude-opus-5-5` from a bounded context bundle (sha `58057121dc2b16fd`); every status below was assigned by the deterministic checker, not by the model. Statuses: observed · static · HYPOTHESIS · supported (all citations check out) · VERIFIED (cites an `if` site and both branches observed, no contradiction) · REJECTED (contradicted by an execution).

## Entities (collector facts)


## Variables

- `field_is_primary` (input) — supported
- `field_needs_refresh` (setting) — supported
- `raw_deps_set` (derived) ↔ observed `None` (is_set) — supported
- `expanded_deps_set` (derived) := `raw_deps_set` ↔ observed `None` (is_set) — supported
- `refs_link_in_import` (input) — supported
- `deps_rewritten` (derived) := `refs_link_in_import && !link_table_outside_import && !linked_primary_unserialized` ↔ observed `None` (changed_from:arg:field_deps) — supported
- `link_table_outside_import` (state) — supported
- `linked_primary_unserialized` (state) — supported
- `implied_dep_found` (derived) := `!link_table_outside_import && !linked_primary_unserialized` ↔ observed `None` (is_set) — supported
- `table_seen` (state) — supported

## Data dependencies


## Decisions, in path order

### d_primary_scan · `field_is_primary` at `DatabaseApplicationType._import_table_fields` site `br:34ec71ee29c9` — supported

- TRUE : (no call); continue — primary_table_fields_map[table id] = primary field id
- FALSE: (no call); continue — field only recorded in database_fields_map
- status: every cited reference checks out (branch, source); site: br:34ec71ee29c9 (given); not verified: predicate disagrees with observed outcomes: test_can_import_database_with_formula_dependencies: replayed outcome sequence differs
  - ✓ source backend/src/baserow/contrib/database/application_types.py:456 `if serialized_field["primary"]:`
  - ✓ branch None → None
  - ✓ branch None → None

### d_expand_empty · `!raw_deps_set` at `DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies` site `br:be7d3ee9e3b1` — VERIFIED

- TRUE : (no call); never LinkRowFieldType.get_import_dependency_when_referenced; **stop** — no dependencies: returned unchanged (None); caller then imports the field immediately
- FALSE: (no call); continue — each (name, via) maps to exactly one element: the referenced field type's implied dependency for same-table refs if any, else itself; referenced link_row fields are asked via get_import_dependency_when_referenced
- status: site br:be7d3ee9e3b1 (`not field_deps`) observed true in 3 and false in 3 execution(s); the predicate agrees with the observed outcome 26 time(s) from observed state and in 3 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ source backend/src/baserow/contrib/database/application_types.py:497 `if not field_deps:`
  - ✓ dataflow None → None
  - ✓ branch None → None
  - ✓ branch None → None

### d_defer · `expanded_deps_set` at `DatabaseApplicationType._import_table_fields` site `br:47a63ce03fc8` — VERIFIED

- TRUE : DeferredFieldImporter.add_deferred_field_import; never DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized; continue — field import deferred with its (expanded) dependency set; imported later by run_deferred_field_imports in dependency-level order
- FALSE: DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized; never DeferredFieldImporter.add_deferred_field_import; continue — field imported immediately and appended to fields_without_dependencies
- status: site br:47a63ce03fc8 (`field_deps`) observed true in 3 and false in 3 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 3 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ source backend/src/baserow/contrib/database/application_types.py:532 `if field_deps:`
  - ✓ control None → deferred_field_importer.add_deferred_field_import
  - ✓ control None → _import_field_serialized
  - ✓ branch None → None
  - ✓ branch None → None

### d_table_bucket · `!table_seen` at `DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized` site `br:3f16965dcd1f` — VERIFIED

- TRUE : (no call); continue — creates the per-table name->field bucket in table_fields_by_name
- FALSE: (no call); continue — reuses the existing bucket
- status: site br:3f16965dcd1f (`table_instance not in table_fields_by_name`) observed true in 3 and false in 3 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 3 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ source backend/src/baserow/contrib/database/application_types.py:480 `if table_instance not in table_fields_by_name:`
  - ✓ branch None → None
  - ✓ branch None → None

### d_link_table_missing · `link_table_outside_import` at `LinkRowFieldType.get_import_dependency_when_referenced` site `br:a0d4e306fb5a` — supported

- TRUE : (no call); **stop** — returns None: linked table pre-exists the import, nothing to order; reference kept as (link, None)
- FALSE: (no call); continue — linked table is part of the import
- status: every cited reference checks out (branch, dataflow, source); site: br:a0d4e306fb5a (given); not verified: outcome true never observed at br:a0d4e306fb5a
  - ✓ source backend/src/baserow/contrib/database/fields/field_types.py:3710 `if related_table_id is None or related_table_id not in primary_table_f`
  - ✓ dataflow None → None
  - ✓ branch None → None
  - ✓ branch None → None

### d_link_primary_missing · `linked_primary_unserialized` at `LinkRowFieldType.get_import_dependency_when_referenced` site `br:f960d9f63045` — supported

- TRUE : (no call); **stop** — returns None
- FALSE: (no call); continue — returns (linked table primary field name, link field name): the reference now depends on the linked primary, reached via the link
- status: every cited reference checks out (branch, source); site: br:f960d9f63045 (given); not verified: outcome true never observed at br:f960d9f63045
  - ✓ source backend/src/baserow/contrib/database/fields/field_types.py:3714 `if primary_field_id not in serialized_fields_map:`
  - ✓ source backend/src/baserow/contrib/database/fields/field_types.py:3717 `return (serialized_fields_map[primary_field_id]["name"], reference_nam`
  - ✓ branch None → None
  - ✓ branch None → None

### d_refresh · `field_needs_refresh` at `DatabaseApplicationType._import_table_fields` site `br:09962e1ae1b2` — supported

- TRUE : (no call); continue — field_instance.refresh_from_db()
- FALSE: (no call); continue — no refresh
- status: every cited reference checks out (branch, control, source); site: br:09962e1ae1b2 (given); not verified: predicate disagrees with observed outcomes: test_can_import_database_with_formula_dependencies: replayed outcome sequence differs
  - ✓ source backend/src/baserow/contrib/database/application_types.py:589 `if field_type.needs_refresh_after_import_serialized:`
  - ✓ control None → field_instance.refresh_from_db
  - ✓ branch None → None
  - ✓ branch None → None

## Behavioral rules

- **r_implied_link_dependency Referencing a link_row by name depends on the linked table's primary** — supported
  - when `refs_link_in_import && !link_table_outside_import && !linked_primary_unserialized`
  - then LinkRowFieldType.get_import_dependency_when_referenced returns (linked primary name, link name); the expanded dependency set differs from the declared one (deps_rewritten); DeferredFieldImporter resolves the dependency through the link (via_field_name is not None) into the linked table instead of the referencing table
  - summarizes d_link_table_missing; every cited reference checks out (boundary, branch, source)
- **r_expansion_preserves_deferral Expansion never changes whether a field is deferred** — supported
  - when `true`
  - then expanded_deps_set == raw_deps_set (each dependency maps to exactly one); d_defer takes the same branch at head as the base `field_deps` branch did; only the content of deferred dependency sets changes
  - summarizes d_expand_empty; every cited reference checks out (boundary, branch)
- **r_defer_iff_deps Fields with dependencies are deferred, others imported at once** — supported
  - when `expanded_deps_set`
  - then add_deferred_field_import called; _import_field_serialized for that field happens later inside run_deferred_field_imports
  - summarizes d_defer; every cited reference checks out (control)
- **r_first_field_creates_bucket The first imported field of a table creates its bucket** — supported
  - when `!table_seen`
  - then br:3f16965dcd1f true once per table (the first non-deferred field in serialized order); false for all later fields and all deferred imports
  - summarizes d_table_bucket; every cited reference checks out (branch)
- **r_ordering_phenotype Producer array primary must be imported before its consumer** — supported
  - when `deps_rewritten`
  - then a consumer formula field('Link') lands at a dependency level after the linked table's (possibly deferred) primary, transitively through chains; after_import_serialized / after_rows_imported recalculate the producer before the consumer: import_tables_serialized returns; at base the dependency stayed (Link, None) in the consumer's own table, so consumer and deferred producer shared a level; the consumer recalculated against the producer's still-empty array column and FormulaFieldType.after_rows_imported raised django.db.utils.DataError

## Regimes (behavioral equivalence classes)

- **Formula references a link_row by name whose linked table (with array-formula primary) is in the import** — 3 test(s): test_snapshot_with_implicit_array_primary_dependency, test_snapshot_with_implicit_array_primary_dependency_two_links_deep, test_duplicate_application_with_implicit_array_primary_dependency — supported
- **Consumer uses lookup(link, primary) explicitly; only the producer's own field('Link') gets rewritten** — 1 test(s): test_snapshot_with_explicit_array_primary_dependency — supported
- **No same-table reference to a link_row; expansion is identity** — 1 test(s): test_can_import_database_with_formula_dependencies — supported

## State transitions

- **t_expand_passthrough** `DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies` when `!raw_deps_set`: `expanded_deps_set := raw_deps_set`, `deps_rewritten := false` — VERIFIED
- **t_expand_map** `DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies` when `raw_deps_set`: `expanded_deps_set := raw_deps_set`, `deps_rewritten := refs_link_in_import` — VERIFIED
- **t_link_none** `LinkRowFieldType.get_import_dependency_when_referenced`: `implied_dep_found := false` — supported
- **t_link_found** `LinkRowFieldType.get_import_dependency_when_referenced`: `implied_dep_found := true` — VERIFIED
- **t_table_seen** `DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized`: `table_seen := true` — supported

## Procedures (composition)

- `DatabaseApplicationType._import_table_fields`: D:d_primary_scan → D:d_primary_scan → D:d_primary_scan → D:d_refresh → D:d_refresh — supported
- `DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies`: D:d_expand_empty — supported
- `DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized`: D:d_table_bucket → T:t_table_seen — supported
- `LinkRowFieldType.get_import_dependency_when_referenced`: D:d_link_table_missing — supported
- `DeferredFieldImporter.add_deferred_field_import`:  — supported
- `DeferredFieldImporter.run_deferred_field_imports`: call:DeferredFieldImporter.get_all_fields_dependencies — supported

## Unknown / incomplete (as stated by the model)

- Iteration counts of the loop-level sites br:34ec71ee29c9 (one observed true per table primary) and br:09962e1ae1b2 (one observed true per formula-like field).: No iteration steps and no per-iteration traced call host these sites, so p_import_table_fields hard-codes 3 primary scans and 2 refreshes. This fits the 3-table/2-formula tests (including both withheld ones) but not test_can_import_database_with_formula_dependencies (2 tables, 3 refreshes). The false outcomes of these two sites are never observed (they fall through to the loop header), so only the true evaluations are modelled.
- Where calls interleave between the expand helper, the LinkRow callee, and the caller's br:47a63ce03fc8.: Which dependency in a set is a same-table link_row reference is decided per element of a loop with no `if` site (`referenced and ...`). So the LinkRow call can't be gated inside the expand procedure and is listed as a separate entry call after expand. br:47a63ce03fc8 (a caller site) is reached from the expand procedure. Per-site order is right; the global interleaving is only approximate.
- The before/after ordering phenotype: which deferred field lands at which dependency level, including the transitive two-link chain.: This is relation-valued: dependency edges between named fields across tables, and levels from group_dependencies_by_level. It is a derived order and cannot be expressed. The phenotype is stated in r_ordering_phenotype and the scenario `why` fields, not generated by decisions.
- The DataError at base.: It surfaces in FormulaFieldType.after_rows_imported during row import, outside the traced functions. No head decision owns it, and the fixed format has no base-revision decisions, so no branch claims a raised outcome.
- Several same-table link references in one dependency set.: refs_link_in_import is an aggregate boolean. With k such references the helper would call get_import_dependency_when_referenced k times. No observed or withheld case has k>1, but the genome cannot generate a count.
- Base exit of test_duplicate_application_with_implicit_array_primary_dependency.: Predicted to be the same DataError as the snapshot case because duplication uses the same import path. Whether duplicate_application's wrapper changes that path at base is not visible in the bundle.
