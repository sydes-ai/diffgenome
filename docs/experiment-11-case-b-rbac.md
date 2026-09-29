# Experiment 11, Case B: simplebank #103, role-based access control

## The case

| | |
|---|---|
| change | upstream techschool/simplebank#103, reproduced by fork sydes-examples/simplebank#5 |
| revisions | base `6e26798` → merged upstream `2e2094e`. The fork head `9a53ee3` is not in the local clone. The upstream commit and its parent were used, as the brief allows. Nothing was fetched; the target change was not modified |
| behavior | a scalar `role` on users (default `depositor`) is copied into the token payload at creation. `authorizeUser(ctx, accessibleRoles)` rejects a verified token whose role is not in the endpoint's literal list (`hasPermission`, a loop over that list). `UpdateUser` passes `[banker, depositor]` and lets a banker update anyone, and anyone else only themselves |
| tests | `gapi` package, the 7 `TestUpdateUserAPI` subtests (one execution each). **Withheld:** `BankerCanUpdateUserInfo` (the new RBAC case) and `ExpiredToken`. Shown: OK, OtherDepositorCannotUpdateThisUserInfo, UserNotFound, InvalidEmail, NoAuthorization |
| before-phenotype | **not observable without editing tests.** The head's tests pass a role to the test helpers, which do not compile against the base. The genome is of the head only (target test/environment) |
| method | the same as Baserow v4: bundle (generic builder `experiments/genome/build_context_case.py`, 1,484 lines, digest `1d090611b879774c`), fresh isolated Opus proposer, statuses from shown tests only, scoring over every observed evaluation of the change's sites with placement checks (`experiments/genome/establish_case.py`) |

## Failures recorded in order (`docs/runs/genome-simplebank-rbac-103/frozen-failures.txt`)

| id | class | failure | action |
|---|---|---|---|
| B-F1 | environment | the sandboxed `go test` could not download `jwt-go`: 0 executions | module cache filled outside the sandbox from a `git archive` copy |
| B-F2 | experiment harness | my establishment script gave the checker the run directory as the source root; every `source` citation failed and 13 items became hypotheses (`frozen/evaluation.json`: 0/7, all indeterminate) | pass the head's source tree |
| B-F3 | **checker (DiffGenome)** | `exit_matches` stripped the runtime prefix (`go:`) from the observed exit kind only, so a claim copied from the logs never matched itself. 6 decisions were wrongly rejected | both sides normalized, with a test |
| B-F4 | **schema ambiguity + proposer** | branches list `calls` *descriptively* ("reached next") while procedures also call them. The predictor runs a branch's `calls` when it has no `steps`, so `hasPermission` and request validation ran twice. Frozen after B-F2 and B-F3: 2/7 exact, 1/2 withheld, **5 confidently wrong** (`frozen/evaluation-after-B-F2-F3.json`) | recorded; the schema is not changed |
| B-F5 | **checker gap** | `hasPermission` and validation were observed exactly once per call in every shown execution, yet a prediction repeating them was not flagged | generic fix: predicting a family repeating inside one occurrence, when it was never observed repeating there (at least 2 executions, and not a member of a repeated region), is a placement problem, so the prediction is indeterminate. No count is claimed |

## Results

| metric | value |
|---|---|
| held-out exact | **1 / 2** (`ExpiredToken`; the banker case is indeterminate, from B-F4) |
| all scenarios exact | 2 / 7 |
| confidently wrong | **0** (5 before B-F5) |
| indeterminate | 5: "hasPermission predicted 2 times inside one authorizeUser, never observed repeating" |
| verified decisions | 5 / 28 (no metadata, unauthenticated, invalid argument, **not owner**, store failed) |
| verified transitions | 0 / 0 (none proposed) |
| verified outcomes | 9 / 30 outcome claims |
| verified occurrence bindings | none used (0 regions) |
| required sites observed and uncovered | 0 |
| `UNKNOWN_DEPENDENCE` (changed functions) | 2 / 57 decision operands, 24 / 207 call arguments |
| model proposals rejected / demoted | 0 / 0 after the tool fixes (6 wrongly rejected and 13 wrongly demoted before B-F2 and B-F3) |
| structure claims | 51 verified, 7 supported, 0 rejected |
| new schema concepts required | none for this behavior (see below) |
| phenotype claims (UpdateUser exit) | 7 / 7 |

**Diagnostic** (not a score; `diagnostic/`). With branches' descriptive `calls` ignored, the same
genome predicts **7/7, including both withheld tests**. It predicts the banker updating another
user correctly, from the source alone. The semantics are right; the failure is B-F4.

## Answers to the Case B questions

1. **Relations avoided?** Yes. The proposer used scalar inputs (the role is banker, the role is
   depositor, the caller is themself), decisions and outcomes. No regions, no occurrence facts.
   The one loop, `hasPermission` over the endpoint's literal list, was unrolled into two
   decisions on its one site. That is correct for the only call site in #103, and it cannot be
   verified: "site shared, the outcome decides only their disjunction".
2. **Role flow through token and auth boundaries.** It is observable but not expressible. The
   role digest passed to `CreateToken` equals the `userRole` digest `hasPermission` receives
   (`#9f99e2` for the banker test). No binding kind relates values at two different boundaries,
   and the digest of a string cannot be decoded. So the role is a scenario input, not a checked
   fact. The missing piece is an *identity-equality binding* between two call boundaries, or
   decoding against source literals. That needs the digest-domain decision from the Step 2
   design.
3. **Can Outcome distinguish results?**
   - **Success vs error:** yes (`returned` vs `returned-error:*status.Error`).
   - **PermissionDenied vs Unauthenticated vs NotFound vs InvalidArgument:** no. All are the
     same Go type, `*status.Error`. The code is a value.
   - **Permission denied inside `authorizeUser`:** it surfaces from `UpdateUser` as
     Unauthenticated (it is wrapped). The proposer noticed this.
4. **Same site, different behavior per role or user?** Yes:

   | site | banker | depositor | other user |
   |---|---|---|---|
   | `userRole == role` | T at the first element | F then T | — |
   | ownership (`role != banker && not self`) | F | F when self | T |

   This comes entirely from scenario inputs.
5. **Occurrence structure for reused authorization calls?** #103 has one call site, so there
   is nothing to disambiguate. Structure did catch the double call (B-F5).
6. **Value-level status-code capture needed?** Yes, to distinguish PermissionDenied,
   Unauthenticated, NotFound and InvalidArgument. Error type and exit category are enough only
   for success vs failure.

**Did occurrence binding stay optional?** Yes. No regions were proposed. The only repetition
(`hasPermission`'s loop over two roles) was modeled as two decisions, and nothing in the result
depends on regions.

## Artifacts

`docs/runs/genome-simplebank-rbac-103/`:

| file | contents |
|---|---|
| `context-bundle.md` and `.sha` | the bundle and its digest |
| `holdout.json` | shown and withheld tests |
| `proposals.json` | the fresh Opus proposal |
| `genome.*`, `evaluation.json` | the established genome and its evaluation |
| `frozen/` | results before and after B-F2/B-F3 |
| `diagnostic/` | the no-branch-calls diagnostic |
| `frozen-failures.txt` | the failure log |
| `existing-tests-head.log` | test log |
