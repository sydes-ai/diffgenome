# Case A (Baserow #6069) — failures recorded against frozen DiffGenome 5f45eb2, before any fix

F1 runtime/environment (collector/runtime): the pytest adapter could not pass PYTHONPATH roots or
   env vars, and denied loopback. Baserow needs premium/enterprise src on the path and a local
   PostgreSQL. First frozen run: ModuleNotFoundError baserow_premium. Fixed generically
   (--pythonpath / --test-env / --allow-loopback); no Baserow logic.
F2 site identity (collector/runtime): pytest plugin sets Tracer.repo_root = first source root, so the
   runtime hashes `baserow/...` while the static front end hashes `backend/src/baserow/...`.
   Head run: 70,197 branch observations, 0 mapped to a static site. Kokoro only worked because its
   source root was the repository root. Contract violation of sites.py ("repository-relative file").
F3 nested functions (deterministic mechanics): `_import_table_fields` contains two nested defs
   (line 464 `_import_field_serialized`, line 489 `_expand_implied_import_dependencies`), lowered
   as opaque. The core of the fix has runtime branch observations (43 in head run) but no static
   facts. NOT fixed in this pass.
F4 scope of mechanics (deterministic mechanics): mechanics are lowered only for files of changed
   symbols; `DeferredFieldImporter` (fields/utils/deferred_field_importer.py), which performs the
   toposort whose order is the phenotype, has no facts. NOT fixed.
F5 dependence (deterministic mechanics): of 54 call arguments in the changed functions, 33 carry
   UNKNOWN_DEPENDENCE (loop variables: the change iterates tables and fields). 1/20 decision operands.
