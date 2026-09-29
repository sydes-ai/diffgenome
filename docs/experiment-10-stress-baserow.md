# Experiment 10, Case A: stress test on a real change — Baserow #6069

## Question

Does the Experiment 08/09 method survive a real change from a large codebase it was not built
around? The method: exact change → deterministic mechanics → bounded bundle → holdout → fresh
Opus proposal → deterministic establishment → phenotype prediction → negative controls.

DiffGenome is frozen at commit 5f45eb2. Failures were recorded before any fix. Only two fixes
were applied during the case. Both are generic collector/runtime fixes, and both are listed
under F1 and F2 below. Mechanics, genome schema, checker and predictor are unchanged. Sydes
was not modified or run. Nothing was pushed, and nothing was submitted upstream.

## The case

| | |
|---|---|
| fork refs | base `sydes-test-base-6069` e995e8f9, head `sydes-baserow-import-dependency` 70c81307 |
| true change | merge base e9ef2697 → 70c81307: 3 source files, 1 new test file, a changelog entry, a workflow |
| what it fixes | a formula `field('LinkField')` declared a dependency only on the link field, so the deferred import could order it level with the linked table's formula primary. The consumer was then typed against a missing column, and row import raised `DataError: cannot extract elements from a scalar` |
| how | new hook `FieldType.get_import_dependency_when_referenced` (default None). `LinkRowFieldType` returns `(linked primary name, link name)`. A nested helper `_expand_implied_import_dependencies` inside `DatabaseApplicationType._import_table_fields` expands every same-table `(name, None)` through it |
| environment | detached worktrees, a Python 3.14.3 venv, and a disposable local PostgreSQL 16 container bound to 127.0.0.1 with test values. Runner: `experiments/genome/run_baserow_6069.sh` |
| tests traced | the 4 new tests, plus 5 neighbours (field-utils deferred import, formula-dependency import, formula import/export) |

**Observed phenotype** (DiffGenome's own sandboxed runs; the base run is the merge base plus the unmodified new test file):

| test | base | head |
|---|---|---|
| explicit `lookup('LinkedChildren','ChildId')` | passed | passed |
| implicit `field('LinkedChildren')` | **failed** (DataError) | passed |
| implicit, two links deep | **failed** | passed |
| implicit, application duplication | **failed** | passed |
| `test_can_import_database_with_formula_dependencies` | passed | passed |

The DataError is raised in `FormulaFieldType.after_rows_imported`, called from
`_import_table_rows` by `import_tables_serialized`. That is two phases after the ordering
decision that causes it.

## Failures recorded against the frozen system

| id | failure | class | action |
|---|---|---|---|
| F1 | The pytest adapter could not pass import roots or environment, and denied loopback. First frozen run: `ModuleNotFoundError: baserow_premium` | collector/runtime | fixed generically (`--pythonpath`, `--test-env`, `--allow-loopback`) |
| F2 | The pytest plugin used the first source root as the repository root. Runtime site ids hashed `baserow/…`, while static ids hashed `backend/src/baserow/…`. **0 of 70,197 branch observations mapped.** Kokoro only worked because its source root was the repository root | collector/runtime | fixed (`--diffgenome-repo-root`, passed by the runtime), with a regression test that fails without the fix |
| F3 | Nested functions are lowered as opaque, including `_expand_implied_import_dependencies`, the core of the fix | deterministic mechanics | recorded, not fixed. Measured by an ablation built in the experiment script |
| F4 | Mechanics are computed only for files of changed symbols. `DeferredFieldImporter`, whose ordering *is* the phenotype, has no facts | deterministic mechanics | recorded |
| F5 | In the changed functions, 33 of 54 call arguments are `UNKNOWN_DEPENDENCE`: loop variables, since the code iterates tables × fields × dependencies | deterministic mechanics | recorded |
| F6 | Site ids are revision-local. The same `if field_deps:` is `br:0771…` at base and `br:47a6…` at head, and nothing maps one to the other | deterministic mechanics | recorded |
| F7 | Value-free digests show *that* the dependency set changed, not what it contains. Import order within a level is not observable: the field dicts are too large to digest | collector/runtime | recorded |
| F8 | The genome has no iteration construct. Scenarios must flatten per-field and per-dependency calls into one list | genome schema | recorded |
| F9 | The genome has no relation-valued state and no derived order, such as dependency levels or a transitive closure | genome schema | recorded |
| F10 | The genome has no outcome concept: pass/fail or "raises X" cannot be derived by the predictor | genome schema | recorded |
| F11 | Branch evidence at a site the static mechanics lack is treated as a *contradiction*. Three correct items were rejected for citing a real, runtime-observed site | checker | recorded |
| F12 | `absent` is judged over the whole continuation, including later loop iterations and deferred callbacks. Two correct "not now" claims were rejected | checker | recorded |
| F13 | Decisions over input facts, with no bound state, can be verified only through a completing scenario replay. With none, an inverted guard stays `supported` (control c1) | checker | recorded |
| F14 | The genome chooses which sites it is scored on. Dropping a decision drops its site from comparison (control c3) | checker | recorded |
| F15 | The proposer started every scenario with a call that has no procedure, so the fixed predictor stops at once. It also nested the defer decision inside the expansion procedure | semantic proposer | recorded; a diagnostic isolates it |
| F16 | The target needs PostgreSQL. Both runs share one test database and must run sequentially | target test/environment | handled locally |

## Mechanics after F1/F2

| | head | base |
|---|---|---|
| branch observations (whole run) | 70,197 | 68,879 |
| mapped to a static site | 2,083 | 1,998 |
| observations in the changed functions | 180 | 123 |
| of those, unmapped | 86, at 2 distinct sites, both in nested functions | 43, at 1 site |
| decision operands with `UNKNOWN_DEPENDENCE` | 1 / 20 (5%) | 1 / 16 |
| call arguments with `UNKNOWN_DEPENDENCE` | 33 / 54 (61%) | 30 / 50 |
| opaque statements | 2: the nested defs | 1 |

The rest of the unmapped observations lie in files outside the change (routers, formula AST,
registries). A mechanical before/after signature exists without any semantics, at the unlowered
importer site `via_field_name is not None`. That file is unchanged, so the site id is the same
at base and head:

| test | base | head | level-grouping result digest |
|---|---|---|---|
| explicit | TTF | TTT | changed |
| implicit | TFF | TTT | changed |
| two links deep | FF | TT | changed |
| duplication | TFF | TTT | changed |
| formula dependencies | FTT | FTT | **identical** |

The digest identifies the four tests whose import ordering changed, and the one whose ordering
did not. It cannot say which change matters: the explicit test changes order and passes at
both revisions.

## Bundle, proposal, establishment

- **Bundle.** 1,540 lines, digest `c90d89e1a1d10cbf`. It holds mechanics at head and base, the
  runtime-only sites with their predicates, chronological head *and base* event logs for 3 shown
  tests (with argument digests and the raised exception), the diff, `_import_table_fields`,
  `DeferredFieldImporter`, the relevant methods, and the test sources.
- **Holdout.** Two-links-deep (transitive generalization) and duplication (a different entry
  point). Their traces at both revisions are withheld from the model and the checker.
- **Proposal.** A fresh Opus subagent read only the bundle, in one call of about 122k tokens.
  It produced 11 variables, 7 decisions (all at given head sites, 1 of them runtime-only),
  2 transitions, 4 procedures, 4 rules, 2 regimes, 5 scenarios and 7 unknowns. Its unknowns
  name F8, F9 and the unobservable within-level order itself.
- **Establishment.** Statuses come from the shown tests only, under the unchanged checker, on
  two substrates:
  - **frozen**: `mechanics.json` as written;
  - **coverage**: an ablation that applies the same front end to nested functions and to the
    importer file. Closure variables resolve as `global:`.

## Metrics

| metric | frozen | coverage ablation |
|---|---|---|
| held-out exact | **0 / 2** | 0 / 2 |
| all scenario tests exact | 0 / 5 | 0 / 5 |
| confidently wrong | 0 (vacuous: every prediction stops at the first call, F15) | 0 |
| indeterminate | 5 / 5 | 5 / 5 |
| verified decisions | 0 / 7 | 0 / 7 |
| verified transitions | 0 / 2 | 0 / 2 |
| `UNKNOWN_DEPENDENCE` | 1/20 operands, 33/54 arguments | same |
| unmapped sites in changed functions | 2 sites, 86 observations (before F2: all 70,197) | 0 |
| proposals rejected / demoted | 4 rejected, 1 hypothesis, of 30 items | 2 rejected |
| rejections of actually wrong semantics | 0: 3 are F11 collateral, 1 is F12 | 0: both F12 |
| new semantic concepts required | 2: an implied dependency through a referencing field, and "ordered after its producer" | |
| new core schema concepts required | 3 fundamental: iteration (F8), relation-valued state with a derived order (F9), outcome effects (F10). Plus 1 mechanics concept: cross-revision site correspondence (F6) | |

**Diagnostics** (`diagnostic.txt`; not scores). The first diagnostic drops the procedure-less
top-level calls and ignores statuses:

| | result |
|---|---|
| exact global order | 1 / 5 (0 / 2 held out) |
| per-site outcome sequence equal to observed | **7/7 sites in 5/5 tests, including both held-out tests** |

The model's local semantics are right everywhere. What is wrong is the flattening: the defer
decision is placed before the link-row call instead of after it (F8, F15).

The second diagnostic scores the model's **phenotype claims**, which are not derived by the
genome: **5 / 5 exact at both revisions, including 2 / 2 held out**. The claims are "fails at
base, passes at head" for the implicit, two-links and duplication tests, and "passes at both"
for the other two.

## Negative controls (same pipeline)

| control | checker | scored | diagnostic (per-site) |
|---|---|---|---|
| c1 inverted link-row guard | **not caught**: stays `supported` (F13) | 5 indeterminate | caught: 5/7 sites in 4 tests |
| c2 pre-change semantics (a link reference implies nothing; head claimed to fail) | **not caught** | 5 indeterminate; phenotype claims 2/5 | **indistinguishable: 7/7** |
| c3 missing decision | not caught (F14) | 5 indeterminate | invisible: 6/6 |
| c4 fabricated site id | **caught**: hypothesis | 5 indeterminate | — |

c2 is the central result. With or without the meaning of the change, the machine-checkable
genome is identical at every site it covers. The implied dependency changes only the *content*
of a dependency set, and so the order of imports. No covered decision observes that content
(F7, F9).

## Answers

**Could the existing genome express the change without a new fundamental concept? No.**

- It expresses the *mechanics of the new code* correctly: 7 of 7 sites have correct local
  sequences, including held-out tests.
- It cannot express the behavior the change exists for, which is an **order over a relation**:
  - fields and their dependency pairs;
  - levels computed by a closure;
  - a consumer placed after the producer it reads through a link.
- It cannot express the **effect of a wrong order**: a typing error that surfaces as an
  exception two phases later.

This needs relation-valued state with a derived order (F9) and outcome effects (F10). Scenarios
over collections also need an iteration construct (F8). None is Baserow-specific: dependency
ordering is how importers, build systems, migrations and schedulers behave.

**Did the model add abstraction beyond the mechanics? Yes, but it lies outside what the
genome can check.**

- It gave the correct causal account: shared level, then the consumer typed before its
  producer, then a DataError.
- It predicted all 5 before/after phenotypes, including both held-out tests and the transitive
  two-links case.
- Unprompted, it identified the one site whose outcome vector carries the phenotype (TFF → TTT).
- It named precisely what it could not encode.

None of this is established. The checker gives the correct genome and the pre-change genome the
same standing (c2), and it cannot reject an inverted guard (c1). The only protection against
confident error was indeterminacy, and here that indeterminacy came from a format error, not
from a principled stop.

**Did the method survive?** Partly:

| stage | held? |
|---|---|
| exact change, deterministic runs and phenotype | yes, after two generic collector fixes |
| mechanics | partly: the core of the fix is a closure, and the ordering lives in an unchanged file |
| proposer | yes, semantically |
| establishment | **no**: 0 verified decisions, 3 wrong rejections, 2 missed controls |
| prediction | no: indeterminate everywhere |

The Experiment 09 success depended on a component whose behavior is scalar state in `self`.
This change's behavior is a relation.

## What would have to change (proposed, not implemented; decide before Cases B/C)

1. **Mechanics**:
   - lower nested functions, with a closure scope instead of `global:`;
   - compute facts for the dependence frontier of the change, not only changed files: here, the
     callee of `add_deferred_field_import`;
   - add a base↔head site correspondence built from the diff hunks.
2. **Checker**:
   - a branch at a runtime-observed site without static facts is unanchored, not contradictory
     (F11);
   - `absent` needs a scope: this iteration, this call, or the rest of the run (F12);
   - scoring must cover every observed evaluation of every site in the change's functions, not
     only the sites the genome picks (F14).
3. **Schema**: iteration, relation-valued variables with one derived order (rank or transitive
   closure), and outcome effects. This is the fundamental addition. It should be designed once,
   language-neutral, and tested against Case B (RBAC, which is relational over roles) before
   being built.
4. **Collector**: optional value capture for small, keyed structures, such as dependency sets
   of name pairs, under the existing value-free default, so that the relation can be observed
   rather than inferred.

Per the brief, no architectural change was made for Cases B and C before this analysis. They have not been run. Items 1 and 2 were later applied as the Step 1 repairs below. Items 3 and 4 remain open.

## Step 1 repairs (applied after the failures above were recorded)

These are generic repairs with no Baserow logic. Mechanics, checker and predictor changed. The
schema gained only an explicit absence scope. The proposal is **the same frozen proposal**, not
re-asked. Tests: `tests/test_exp10.py`, a synthetic importer with the same shape.

| repair | fixes | where |
|---|---|---|
| Nested functions are lowered as functions of their own, named like the collector's `co_qualname` (`outer.<locals>.inner`). A nested `def` statement is a local definition, not opaque. Free variables of the enclosing scopes resolve to `closure:<name>`, not `global:` | F3 | `frontends/python_ir.py`, `dependence.py` |
| Comprehension targets are bound by the comprehension. Previously `{f.name: f for f in xs}` produced `global:f` | found while repairing F3 | `frontends/python_ir.py` |
| Mechanics frontier: Python mechanics also cover the files of in-repo functions that changed code (or code nested in it) was observed calling *directly*. `mechanics.json` records each file's role (`changed` / `frontier`) | F4 | `mvp.py` (`mechanics_frontier`) |
| A branch reference or decision site that was observed at runtime but has no static facts is *unanchored*. It can support, never contradict, and never verifies. A site nothing knows is missing support (hypothesis), not a contradiction | F11 | `genome_state.py`, `EvidenceRef.unanchored` |
| `absent` is judged per **episode**. The episode runs up to the next evaluation of the same site or the next call of the deciding function. For a site inside a loop, it ends at the first call the static facts place outside every loop. It reaches into the caller's continuation only when the branch exits. `absent_scope: "run"` keeps the old meaning | F12 | `genome_state.episode_calls`, `Branch.absent_scope` |
| A genome is scored on every observed site of the changed functions and of functions nested in them (`change_sites`). An observed evaluation that no decision covers makes the prediction indeterminate | F14 | `genome_state.compare_sequence(required_sites=…)` |
| A top-level scenario call of an entity the genome says nothing about is skipped. An entity that has decisions but no procedure still stops the prediction, with that reason | F15 (the silent part) | `genome_state.predict_sequence` |

**No regression on earlier experiments:**
- Experiment 09 (Kokoro), re-established with the repaired checker: every status and every
  per-test result is identical in the main genome and the four controls (13/13, withheld 4/4,
  stateless 3/13).
- Kokoro's mechanics regenerated with the repaired front end are identical: 24 functions, no
  change.
- Experiment 08 (simplebank, Go), re-checked: identical statuses. Only reason wording differs.

**Case A, rerun** (DiffGenome at head and base again, same phenotype: 9/9 and 6/9 passed):

| | frozen 5f45eb2 | repaired |
|---|---|---|
| mechanics files | 3 (changed) | 3 changed + 6 frontier, including `deferred_field_importer.py` |
| observations in changed functions mapped to a static site | 94 / 180 | **180 / 180** |
| whole-run observations mapped | 2,083 / 70,197 | 11,862 / 70,197 |
| opaque statements in the change | 2 | **0** |
| `UNKNOWN_DEPENDENCE` (the change's functions and the importer) | operands 1/20, arguments 33/54 | operands 2/24, arguments 40/78 (more functions now have facts) |
| proposal items rejected / demoted | 4 rejected + 1 hypothesis, none actually wrong | **0 / 0** |
| decisions anchored at a static site | 6 / 7 | **7 / 7** |
| verified decisions / transitions | 0/7, 0/2 | 0/7, 0/2 |
| held-out exact | 0 / 2 | 0 / 2 |
| confidently wrong | 0 | 0 |
| indeterminate | 5/5, silently at the first call | 5/5, stated: "no procedure for `_import_table_fields`, which has decisions", and 3 observed change sites no decision covers |
| control c1 inverted guard | not caught | not caught (F13) |
| control c2 pre-change semantics | indistinguishable | indistinguishable (F9) |
| control c3 missing decision | invisible | **detected**: its site is reported uncovered, and prediction is indeterminate |
| control c4 fabricated site | hypothesis | hypothesis |

**What the repairs settle:**
- **Tooling.** The wrongful rejections and the mapping gap were tooling faults, and they are gone.
- **The indeterminacy.** It is now principled and attributed to named causes.

**What they do not settle:**
- **Verification.** Nothing verifies, because these decisions read input facts that no
  observed state binds. Verification would need a completing scenario replay, and the
  proposal's flattening (F8, F15) prevents that.
- **The semantic gap.** c2 remains indistinguishable. That is the Step 2 question, relations
  with a derived order (F9), and it is untouched here.

## Artifacts

`docs/runs/genome-baserow-6069/`:

| file | contents |
|---|---|
| `context-bundle.md` and `.sha` | the bundle and its digest |
| `holdout.json` | shown and withheld tests |
| `proposals.json` | the fresh Opus proposal |
| `frozen.genome.*`, `coverage.genome.*` | the established genome on each substrate |
| `evaluation.json` | full evaluation |
| `controls/` | seeded proposals and their evaluations |
| `diagnostic.txt` | diagnostic output |
| `substrate-stats.json` | branch mapping, unknowns, and the importer signature per test and revision |
| `mechanics-head.json`, `mechanics-base.json` | filtered mechanics |
| `frozen-failures.md` | failures recorded before any fix |
| `existing-tests-*.log` | test logs |

| `repaired.evaluation.json`, `repaired.genome.*`, `controls/*.repaired.*` | the same proposal and controls on the repaired substrate |
| `repaired-mechanics-*.json`, `repaired-substrate-stats.json` | repaired mechanics (filtered) and statistics |

Scripts: `experiments/genome/{run_baserow_6069.sh, build_context_exp10.py, establish_exp10.py, controls_exp10.py, diagnose_exp10.py}`.
`establish_exp10.py … repaired` scores on the repaired substrate.
