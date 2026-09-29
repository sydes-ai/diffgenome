# Behavioral Genome — baserow #6069 import dependency via link row (`diffgenome-genome/0`, experimental)

Entry `_import_table_fields`. Semantic items proposed by `claude-opus-5-5` from a bounded context bundle (sha `a51a942b4fd62ef1`); every status below was assigned by the deterministic checker, not by the model. Statuses: observed · static · HYPOTHESIS · supported (all citations check out) · VERIFIED (cites an `if` site and both branches observed, no contradiction) · REJECTED (contradicted by an execution).

## Entities (collector facts)


## Variables

- `is_primary` (input) — supported
- `field_deps_present` (derived) ↔ observed `None` (is_set) — supported
- `deferred` (derived) := `field_deps_present` ↔ observed `None` (is_set) — supported
- `deps_rewritten` (derived) ↔ observed `None` (changed_from:arg:field_deps) — supported
- `link_table_in_import` (input) — supported
- `link_primary_serialized` (input) — supported
- `implied_dependency` (derived) := `link_table_in_import && link_primary_serialized` ↔ observed `None` (is_set) — supported
- `table_first_field` (state) — supported
- `needs_refresh` (setting) — supported
- `refs_link_to_deferred_primary` (input) — supported
- `order_hazard_base` (derived) := `refs_link_to_deferred_primary` — supported
- `order_hazard_head` (derived) := `refs_link_to_deferred_primary && !implied_dependency` — supported

## Data dependencies


## Decisions, in path order

### d_primary · `is_primary` at `DatabaseApplicationType._import_table_fields` site `br:34ec71ee29c9` — supported

- TRUE : (no call); continue — table id -> primary field id recorded in primary_table_fields_map (later read by LinkRowFieldType.get_import_dependency_when_referenced)
- FALSE: (no call); continue — field only recorded in database_fields_map
- status: every cited reference checks out (branch, source); site: br:34ec71ee29c9 (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ source backend/src/baserow/contrib/database/application_types.py:456 `if serialized_field["primary"]:`
  - ✓ branch None → None

### d_expand_passthrough · `!field_deps_present` at `DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies` site `br:be7d3ee9e3b1` — VERIFIED

- TRUE : (no call); never LinkRowFieldType.get_import_dependency_when_referenced, FieldType.get_import_dependency_when_referenced; **stop** — no dependencies: returned unchanged (None)
- FALSE: (no call); continue — each (name, None) dependency naming a same-table field is offered to that field's type; the implied dependency, if any, replaces it; other dependencies are kept
- status: site br:be7d3ee9e3b1 (`not field_deps`) observed true in 3 and false in 3 execution(s); the predicate agrees with the observed outcome 26 time(s) from observed state and in 0 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ source backend/src/baserow/contrib/database/application_types.py:497 `if not field_deps:`
  - ✓ dataflow None → None
  - ✓ branch None → None
  - ✓ branch None → None

### d_defer · `deferred` at `DatabaseApplicationType._import_table_fields` site `br:47a63ce03fc8` — supported

- TRUE : DeferredFieldImporter.add_deferred_field_import; never DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized; continue — field registered with its (expanded) dependency set; imported later by run_deferred_field_imports in dependency order
- FALSE: DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized; never DeferredFieldImporter.add_deferred_field_import; continue — field imported immediately and appended to fields_without_dependencies
- status: every cited reference checks out (branch, control, dataflow, source); site: br:47a63ce03fc8 (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ source backend/src/baserow/contrib/database/application_types.py:532 `if field_deps:`
  - ✓ dataflow None → None
  - ✓ control None → deferred_field_importer.add_deferred_field_import
  - ✓ control None → _import_field_serialized
  - ✓ branch None → None
  - ✓ branch None → None

### d_first_field_of_table · `table_first_field` at `DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized` site `br:3f16965dcd1f` — supported

- TRUE : (no call); continue — per-table name->field map created in table_fields_by_name
- FALSE: (no call); continue — existing per-table map reused
- status: every cited reference checks out (branch, dataflow, source); site: br:3f16965dcd1f (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ source backend/src/baserow/contrib/database/application_types.py:480 `if table_instance not in table_fields_by_name:`
  - ✓ dataflow None → None
  - ✓ branch None → None
  - ✓ branch None → None

### d_link_table_outside · `link_table_in_import` at `LinkRowFieldType.get_import_dependency_when_referenced` site `br:a0d4e306fb5a` — supported

- TRUE : (no call); **stop** — linked table pre-exists the import: no implied dependency (None), reference kept as (name, None)
- FALSE: (no call); continue — linked table is imported too: look up its primary field
- status: every cited reference checks out (branch, dataflow, source); site: br:a0d4e306fb5a (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ source backend/src/baserow/contrib/database/fields/field_types.py:3710 `if related_table_id is None or related_table_id not in primary_table_f`
  - ✓ dataflow None → None
  - ✓ branch None → None

### d_link_primary_missing · `!link_primary_serialized` at `LinkRowFieldType.get_import_dependency_when_referenced` site `br:f960d9f63045` — supported

- TRUE : (no call); **stop** — primary not serialized: no implied dependency (None)
- FALSE: (no call); continue — returns (linked primary name, link field name)
- status: every cited reference checks out (branch, dataflow, source); site: br:f960d9f63045 (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ source backend/src/baserow/contrib/database/fields/field_types.py:3714 `if primary_field_id not in serialized_fields_map:`
  - ✓ dataflow None → None
  - ✓ branch None → None

### d_refresh · `needs_refresh` at `DatabaseApplicationType._import_table_fields` site `br:09962e1ae1b2` — supported

- TRUE : (no call); continue — field_instance.refresh_from_db() after recalculation
- FALSE: (no call); continue — instance kept as is
- status: every cited reference checks out (branch, control, source); site: br:09962e1ae1b2 (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ source backend/src/baserow/contrib/database/application_types.py:589 `if field_type.needs_refresh_after_import_serialized:`
  - ✓ control None → field_instance.refresh_from_db
  - ✓ branch None → None

## Behavioral rules

- **r_link_reference_implies_primary A by-name reference to a link_row field depends on the linked table's primary** — supported
  - when `link_table_in_import && link_primary_serialized`
  - then (link, None) in a field's declared dependencies is replaced by (linked primary name, link); the expanded set differs from the declared set (deps_rewritten); for field('LinkedChildren') the head dependency set becomes identical to the explicit lookup('LinkedChildren','ChildId') form (same digest #8b5219 in both snapshot tests)
  - summarizes d_link_primary_missing; every cited reference checks out (boundary)
- **r_non_link_reference_unchanged References to non-link fields (or via-references) are kept as declared** — supported
  - when `field_deps_present && !deps_rewritten`
  - then expanded set equals declared set; base and head dependency graphs coincide
  - summarizes d_expand_passthrough; every cited reference checks out (boundary)
- **r_defer_iff_dependencies A field is deferred iff it declares dependencies** — supported
  - when `deferred`
  - then add_deferred_field_import instead of immediate _import_field_serialized; imported later from run_deferred_field_imports by level
  - summarizes d_defer; every cited reference checks out (branch, control)
- **r_order_hazard A consumer not ordered after a deferred linked primary crashes the row import** — supported
  - when `order_hazard_base at base; order_hazard_head at head`
  - then at base the consumer and the linked array primary share a dependency level, the consumer is recalculated before the primary's column is populated, and import_tables_serialized raises django.db.utils.DataError (surfacing in FormulaFieldType.after_rows_imported, after _import_table_fields has returned); at head the rewritten dependency puts the consumer one level after the linked primary, so import_tables_serialized returns; _import_table_fields itself returns in both revisions

## Regimes (behavioral equivalence classes)

- **No by-name reference to a link whose primary is deferred** — 2 test(s): test_snapshot_with_explicit_array_primary_dependency, test_can_import_database_with_formula_dependencies — supported
- **By-name reference to a link whose linked primary is a deferred array formula, linked table in the import** — 1 test(s): test_snapshot_with_implicit_array_primary_dependency — supported

## State transitions

- **t_implied** `LinkRowFieldType.get_import_dependency_when_referenced` when `link_table_in_import && link_primary_serialized`: `implied_dependency := true` — supported
- **t_expanded** `DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies` when `field_deps_present`: `deferred := true` — VERIFIED

## Procedures (composition)

- `DatabaseApplicationType._import_table_fields.<locals>._expand_implied_import_dependencies`: D:d_expand_passthrough → T:t_expanded — supported
- `LinkRowFieldType.get_import_dependency_when_referenced`: D:d_link_table_outside → D:d_link_primary_missing → T:t_implied — supported
- `DatabaseApplicationType._import_table_fields.<locals>._import_field_serialized`: D:d_first_field_of_table — supported

## Unknown / incomplete (as stated by the model)

- No procedure for DatabaseApplicationType._import_table_fields (so predictions stop at that call).: Its required sites br:34ec71ee29c9 (per field of the pre-scan), br:47a63ce03fc8 (per field, inside the observed repeated region together with get_field_depdendencies_before_import_serialized, _expand_implied_import_dependencies, add_deferred_field_import and _import_field_serialized) and br:09962e1ae1b2 (per imported field) are evaluated a data-dependent number of times inside ONE call. The format has no loops or iteration steps; listing each once would mispredict counts, unrolling needs per-field variable names (forbidden), and moving the per-field calls to scenario entry calls would hoist them out of their observed enclosing function.
- Which get_import_dependency_when_referenced implementation _expand_implied_import_dependencies calls, and how many times.: Inside one _expand call there is a loop over the dependency set, and dispatch is by the referenced field's type through the registry (LinkRowFieldType vs the FieldType default, or no call when via is set or the name is absent); there is no decision site for this dispatch and no iteration step, so p_expand does not place the call and the LinkRow sites br:a0d4e306fb5a / br:f960d9f63045 are not reached from it.
- Dependency ordering by DeferredFieldImporter (get_all_fields_dependencies, group_dependencies_by_level, then one _import_field_serialized callback per deferred field).: The fix works by changing a relation (which field depends on which, across tables) and the derived level order; relation-valued variables and derived orders are not available, and run_deferred_field_imports repeats _import_field_serialized, so neither it nor the 'imported after' consequence can be expressed except as rule text.
- Where the base DataError is raised.: It surfaces in FormulaFieldType.after_rows_imported during _import_table_rows, outside the shown logs; _import_table_fields returns in both revisions, so the link between level order and the later crash is asserted by r_order_hazard, not derivable from shown mechanics. Level order within the same level (why the consumer comes first) is also not observed.
- Why br:34ec71ee29c9 is logged only as one T per table.: The site is evaluated for every serialized field but the logs show only as many (all true) evaluations as there are tables; the tracer's recording of false outcomes here is not explained by the bundle.
