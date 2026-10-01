# Does DiffGenome's runtime data materially improve Sydes, and where?

Four real merged PRs:

| PR | change |
|---|---|
| Baserow #5507 | undo/redo with restricted-view permissions |
| Baserow #5972 | data-sync endpoint permission + PostgreSQL SSRF hardening |
| Baserow #5666 | periodic field updates fanned out behind a Redis run lock |
| simplebank #103 | RBAC; Go, gRPC, gomock store |

No genome, proposer or semantic layer was used; only what the collectors record. Everything is
local: nothing pushed, nothing published. Evidence is in `docs/runs/runtime-eval/`.

## 0. A bug found first (fixed, `b2e5992`)

With `--rev` set to a revision other than the checkout, the Python runtime built its symbol index
and its mechanics from the **checkout**, while the tests executed the **revision**. Changed-line
attribution and decision-site ids therefore came from a different file version.

| PR | effect of the bug |
|---|---|
| #5507 | 7 symbols wrongly attributed (e.g. `ViewHandler.get_view`); 8 missed, including the PR's core `restore_row`, `restore_rows`, `get_view_or_none` |
| #5972 | 2 unedited functions attributed as changed; `are_hostnames_same` missed. Site ids 38 lines off, so no branch outcome joined |
| #5666 | none: files identical at both revisions |
| #103 | none: Go/Node already used the workspace |

Both sides now read the workspace copy of the revision. There is a regression test that fails
before the fix. All results below use the fixed runs. The earlier `--behavioral-context` rounds
on these three Baserow PRs used the buggy attribution.

## 1. Setup

**Sydes configurations, run deterministically (no model call at all)** to score the primary
question:
- **S0, static only:** `--llm-policy never --impact-guide off --no-ai-recovery`.
- **R0, static + runtime:** the same plus `--behavioral-map diffgenome --behavioral-artifact
  <fixed artifact> --behavioral-context on`. The runtime contributes observed call edges into
  Sydes' reachability, observed-caller files, and the executed-test list.

**Model runs, one per configuration** (`gpt-6-astra`, `xhigh`, AI recovery on) were also made to
count AI-recovery cost. **OpenAI credits ran out during them.** The static runs lost 1 of 4
recovery calls on #5507, 4 of 7 on #5972 and 8 of 15 on #103; nearly every model call of the
runtime runs failed. Only #5666's static run completed its AI recovery; it is used below and
nothing else from the model runs is scored.

**Test universe:** the tests DiffGenome ran.
- **Baserow:** the PR's own test files. For #5972, 21 tests that fail in this environment
  without instrumentation were deselected (`pr5972-env-failing.txt`; the name filter removed
  37); 2 instrumentation-caused failures remain.
- **#103:** the `gapi`, `api` and `token` packages (62 executions). `db/sqlc` tests need
  Postgres and were not run.

**Ground truth:**
- **Entrypoints:** labelled by hand from the code.
- **Test → changed-function mapping:** from the traces, checked against the test code by hand
  for `restore_row`, `restore_rows`, `get_row_for_update`, `get_view_or_none` and
  `UpdateRowsActionType.undo` (#5507), plus the #5666 and #103 examples below. They agree
  exactly.
- **Gaps:** meaningful changed behaviors with no exercising test, labelled from the diff and test
  bodies before comparing with the runtime report
  (`experiments/runtime_eval/runtime_report.py`).

## 2. Results

| | #5507 | #5972 | #5666 | #103 |
|---|---|---|---|---|
| **true entrypoints** (hand-labelled) | undo API, redo API, row-PATCH API, trash-restore API | properties endpoint, create / update / sync / properties-of-sync endpoints, periodic data-sync task | beat task `run_periodic_fields_updates`, management command, 2 chord tasks; secondary: search and AI-field tasks via the flag | gRPC UpdateUser, LoginUser, CreateUser, VerifyEmail; HTTP login, renew, create-user |
| entrypoint recall, S0 → R0 | 0/4 → 0/4 entrypoints; the **dispatch path** to `ActionHandler._undo_action/_redo_action` is new in R0 | 2/6 → 2/6 | 3/4 → 3/4 (the command is missed by both; secondary 2/2 both) | 3/7 → 3/7 (gRPC not discovered deterministically) |
| false static entrypoints, S0 → R0 | 0 → 0 | 12 → 12 (`decorator_reference` to a changed settings constant) | 12 → 12 (same, plus a `clear` name collision) | 0 → 0 |
| changed functions unresolved, S0 → R0 | **8 → 3** | 10 → 9 | 2 → 1 | 30 → 30 |
| runtime edges added (new vs already static) | 37 (37 / 0) | 11 (11 / 7) | 8 (8 / 11) | 0 (0 / 2) |
| tests mapped to the change: recall S0 → R0 | **0/13 → 13/13** | **0/15 → 14/15** | **0/35 → 32/35** | 12/12 → 12/12 test functions (R0 adds the exact subtests) |
| wrong tests suggested, S0 → R0 | 0 → 0 | 0 → 0 | 0 → 0 | 1 → 1 (`TestCreateUserAPI`: store is a gomock, so the changed query never runs) + 5 db tests unverifiable |
| meaningful uncovered changed behaviors: identified / ground truth | **4 full + 2 partial / 6** | **3 / 5** | **3 full + 1 partial / 5** | **4 / 4** |
| AI-recovery model calls (static) | 4 (1 failed) | 7 (4 failed) | **26**, all succeeded | 15 (8 failed) |
| AI-recovery triggers removed by runtime data | "no relevant test mapped" | same | same | same |
| extra runtime cost (DiffGenome, wall) | 74 s (55 tests) | 438 s (180 tests) | 20 s (38 tests) | 50 s (62 tests, 3 packages) |

**How the gaps were classified:**
- **#5507:** restore never via `TrashHandler.restore_item` (function never exercised); restore
  rejections for a trashed parent or a non-owner (branch); the missing-view path (`view_id is
  None` never true: branch; the `ViewDoesNotExist` handler: partial); PermissionDenied during
  replay (outcome never observed); `restore_rows` with `row_ids=None` (type regime: always
  `list[2]`); the row-PATCH API route (partial: only direct action calls were observed).
  `DatabaseConfig.ready` is startup code and not counted.
- **#5972:** the production validation and IP-pinning path (`not settings.TESTS` never true:
  branch); a successful PostgreSQL connection and statement-timeout handling (exits only
  SyncError 4/4: outcome and boundary); the properties endpoint's database-not-found and
  not-in-workspace outcomes (never observed). **Not identified:** the IPv4-mapped ×
  local-interface regime, and the `netifaces`-missing fail-open handler.
- **#5666:** `SingletonAutoRescheduleFlag.set` and `clear` never executed (function); the
  idle-workspace skip (`if not fields` never true: branch); the Celery chord as an external
  boundary (eager). **Partial:** soft timeout during the heartbeat (see §3). **Not identified:**
  a real Redis behind the Lua scripts.
- **#103:** `renewAccessToken` and gRPC `LoginUser` never executed (function); the role-column
  queries (gomock stand-ins: boundary); `!hasPermission(...)` never true (branch: no test
  denies by role).

### Concrete examples

**STATIC MISSED → RUNTIME RECOVERED** (#5507). `ActionHandler._undo_action →
DeleteRowActionType.undo → RowHandler.restore_row → TrashHandler.force_restore_item`, and its
redo, update and bulk variants: registry dispatch the static graph cannot follow. Sydes' own
interpreter now reaches the action dispatcher, labelled `runtime_observed_reachability`.
Unresolved changed functions went 8 → 3.

**STATIC CLAIM → RUNTIME SHOWED NOT EXECUTED** (#103). Static Sydes maps `TestCreateUserAPI` to
the change, but the changed `Queries.CreateUser` never executes in it; the store is a gomock.
(The 12 false periodic tasks each on #5972 and #5666 are outside the test universe, so runtime data
can say "not observed" there, not "false".)

**TEST MISSED BY SYDES → RUNTIME PROVED EXECUTION** (#5666). Static AI recovery spent 26 model
calls, accepted 4 tests, and **rejected** `test_acquire_is_atomic_and_stores_token` ("no evidence
cited at all") and `test_clear_if_only_deletes_on_matching_token`. Both execute changed
functions (`acquire`, `clear_if`), and the traces name them along with 30 others. On #5507 and
#5972 static Sydes maps no test at all; runtime data names 13 and 14.

**CHANGED BEHAVIOR → NO TEST OBSERVED IT:**
- #5666: the idle-workspace skip (`if not fields:` reached 16 times, never true);
  `SingletonAutoRescheduleFlag.set` never called.
- #5507: restore rejections (trashed parent, foreign owner) never taken; no replay ever denied.
- #5972: the production host validation and IP pinning never run under tests (`not
  settings.TESTS` 0/4); every recorded connection attempt ended in SyncError.
- #103: no test denies UpdateUser by role (`!hasPermission` 0/5).

## 3. The known-defect check

**#5972, IPv4-mapped address bypassing the local-interface check.**
- **Did a test exercise the defect regime?** No. The tests cover mapped private addresses with
  `allow_private=True` against the real interface set, and the local-interface rejection once
  with a patched set and a plain IPv4 (`192.0.2.99`). Never both together.
- **Does runtime data expose that?** **No.** By branch coverage the code looks exercised:
  `ip_obj in local_addresses` was true once and false 26 times, and mapped-address
  normalization ran both ways. The missing case is a value regime (mapped × private allowed ×
  local interface). DiffGenome records value fingerprints and type shapes, not values; for the
  interface set it recorded no shape at all.

**#5666, soft timeout during the lock heartbeat.**
- **Did a test exercise it?** No. The only soft-timeout test raises from the workspace update.
- **Does runtime data expose it?** **Only as a raw fact.** `extend_if` returned 21 times out of
  21 and never raised; `SoftTimeLimitExceeded` was observed only from
  `_update_workspace_periodic_fields`. The report shows this, but nothing ranks it above the
  many other never-raised calls. Seeing that it matters requires knowing that the call sits
  outside the `try`, which the current mechanics do not record (`except` handlers are not
  sites).

## 4. Decision

**A. Runtime extraction: reliable enough for Sydes now.**
- which changed functions executed, and in which tests (verified by hand against test code);
- observed call edges, including dynamic dispatch, decorators and registries;
- exits and exceptions per call;
- decision-site outcomes on changed lines;
- argument type shapes;
- observation boundaries (mocks, stand-ins, eager Celery).

These require the `--rev` fix above. Not reliable or not present: values (only fingerprints and
type shapes); coverage of `except` handlers; per-line coverage.

**B. Static augmentation: one blind spot consistently repaired, small elsewhere.**
- **Repaired:** reachability through dynamic dispatch (#5507: 8 → 3 unresolved, the undo/redo
  dispatcher path recovered); marginal on #5972 and #5666 (−1 each); none on #103, where static
  already had the edges.
- **Not repaired:** no false static path was removed. The runtime is additive, and the false
  entrypoints (12 and 13, from settings `decorator_reference` and name collision) come from a
  Sydes rule that runtime evidence cannot veto, because those tasks are outside any test's
  reach.
- **Not helped:** entrypoint recall at the API/command level. Sydes does not treat DRF views,
  management commands or gRPC methods as entrypoints here, with or without runtime edges.

**C. Test mapping: yes, materially, the clearest win.** On the three Baserow PRs, static Sydes
mapped **0** tests to the change; runtime evidence named **59 of 63** executing tests with **0**
wrong. On Go/#103, static already found the 12 test functions at function granularity; runtime
adds subtest precision and proves one static claim wrong.

**D. Verification gaps: yes for function-, branch- and outcome-level gaps; no for value
regimes.** It identified 14 of 20 hand-labelled gaps fully and 3 more partially. The misses are
value combinations (the #5972 defect), `except`-handler paths, and real external dependencies
behind stand-ins. **It did not expose either validated defect as a gap.** It exposes the
untested regions around them (the production validation path in #5972; the heartbeat call's
outcome in #5666), not the defects.

**E. Cost: yes for test mapping; unproven for AI recovery.**
- DiffGenome adds 20–438 s per PR, dominated by graph building on large test sets.
- Runtime evidence answers the "no test mapped" gap without a model. On #5666 that is the work
  26 recovery calls did, with better precision and 8× the recall.
- **Not shown:** that it removes AI recovery entirely. Recovery still triggers for unresolved
  changed functions, and the credit failure prevented measuring how many calls remain.

**F. Smallest DiffGenome feature set Sydes should depend on now:**
1. the existing-test run, with call trees, exits and arguments' type shapes (`diffgenome change`,
   no probes, no model);
2. per changed function: executed / not executed, with tests and exits;
3. decision-site outcomes on changed lines, which needs the `--rev` fix;
4. observed call edges, for Sydes' reachability (already integrated behind
   `--behavioral-context`);
5. the observation-boundary list.

**Not needed:** the genome layer, probes and the proposer. A runtime gap report like
`runtime_report.py` is a small packaging step over facts DiffGenome already records, not new
research. None of these four PRs showed a missing runtime fact that blocks the product. Value
regimes and `except`-handler coverage would be needed to expose defects like the two validated
ones, but that is research, not a blocker.

## 5. Limits

- Four PRs and one model-free configuration pair. AI-recovery cost was measurable for #5666 only,
  because the credits ran out.
- Test universes are the PRs' own test files (Baserow) or three packages (#103). Recall is
  relative to them.
- Ground truth for test mapping is the traces, hand-checked on a sample rather than
  independently derived for every function.
