# Experiment 13: value identity across call boundaries (Cases B and C)

The design is in `docs/design-value-identity.md`. All work is local: nothing was pushed and
Sydes was not run. Relations, derived order and iteration were not touched.

## What was built, in order

1. **`Branch.calls` are descriptive.** Only `steps` (of procedures, regions and branches) are
   executable. **Measured before changing:** no recorded prediction depended on executable
   calls, so no genome needed migrating. The helper `migrate_executable_calls` exists but is
   not applied anywhere. In one Kokoro control (c2), transition `t_schedule_arm` moves from
   supported to verified, its status in the main genome.
2. **Prediction eligibility.** A supported item contradicted on a shown execution keeps its
   status, but cannot drive a prediction (`Item.contradicted`, internal). Diagnostics that
   request hypothesis-level prediction still see everything.
3. **Value identity.**
   - A boundary kind `identity` gives an opaque digest, compared with `==` / `!=` only.
   - `observed_as` may be a list, and scopes are `call` or `execution`. Execution scope takes
     the unique earlier value in the same test; if the values differ it is ambiguous, and
     never guessed.
   - A variable with two or more identity bindings is an **identity claim**:

     | status | rule |
     |---|---|
     | rejected | some shown test shows the sides differ |
     | verified | equal in at least 2 tests carrying at least 2 distinct values (a contrast) |
     | supported | equal, but with no contrast |
     | unknown | never observed on every side |

4. **Literal identity.** `equals_literal` is true when a boundary value equals a literal
   *written on a cited source line*: bool, nil, integers up to 64 bits, or short plain strings.
   It is compared by digest and never decoded. The collector's own canonical forms were
   confirmed against the traces: `string:"banker"` → `9f99e2`, `uint8:1` → `35ddf6`.
5. **Scenario facts become checkable.** On shown tests, a fact stated for a call is compared
   with that call's boundary, or with a unique boundary inside the call. Identity facts are
   labels whose pattern must match the observed identity pattern.

**Failures found and fixed during the pass:**
- **V-F1, a checker bug I introduced.** A variable rename left the identity count reading a
  stale loop variable, so identity claims were silently skipped when the last binding checked
  was not an identity. Found through Case B v5's username identity. There is a regression test.
- **V-F2, region semantics too broad.** After each occurrence *every* non-state variable was
  restored, discarding what the body's transitions set, such as a matching role in Case B's
  role loop. Now only the occurrence's supplied facts are local. There is a regression test.

**Regression, after the last change:**
- Experiment 09: 13/13, withheld 4/4, stateless 3/13. The main genome and 3 controls are
  unchanged. Control c2 loses 4 exact predictions to indeterminate under eligibility, and
  gains the transition status above. It still has 0 wrong.
- Experiment 08: identical.
- Baserow v2 and v3: identical.
- Baserow v4 under eligibility: **0 wrong** (was 2 in-sample), 0/5 exact, all indeterminate.
  All v4 controls are at 0 wrong.
- Tests: 106 pass (`tests/test_value_identity.py`, plus regression tests for V-F1 and V-F2).

## Case B, simplebank #103 (RBAC)

| run | held-out exact | all exact | confidently wrong | indeterminate | verified decisions | identity claims | literal bindings | scenario facts confirmed |
|---|---|---|---|---|---|---|---|---|
| Experiment 11 (before) | 1/2 | 2/7 | 0 (5 before B-F5) | 5 | 5/28 | — | — | — |
| existing proposal, new rules | **2/2** | **7/7** | 0 | 0 | 6/28 | — | — | 4 |
| fresh v5 proposal | **2/2** | **7/7** | 0 | 0 | 7/26 | `token_username` **verified** (4 tests, 2 values) | `caller_is_banker` valid (`"banker"`, util/role.go:5) | 24/24 |

- Resolving `Branch.calls` alone fixed the existing proposal. B-F4 was the whole failure.
- Verified outcomes: 11/27 claims.

**Role flow.** The v5 proposer deliberately declined a role identity. Every shown test is a
depositor, so a claim could not be verified. The checker agrees:

| role identity (`CreateToken arg:role == hasPermission arg:userRole`) | status |
|---|---|
| on shown tests | **supported**: 4 tests, 1 distinct value, no contrast |
| including the withheld banker test (diagnostic only; withheld traces never feed the checker) | verified |

What *is* established from observation is "the role given at token creation is (not) the
banker literal". It is a literal binding at creation, and its scenario facts are confirmed on
every shown test.

**Status codes.** PermissionDenied, NotFound, Unauthenticated and InvalidArgument are not
distinguishable. The code sits inside an error value whose digest also covers the message,
and no boundary carries the code alone. This is a separate value-decoding limitation;
Outcome is not overloaded.

## Case C, simplebank #136 (token type)

| run | held-out exact | all exact | confidently wrong | indeterminate | verified decisions | identity claims | literal bindings | scenario facts confirmed |
|---|---|---|---|---|---|---|---|---|
| Experiment 12 (before) | 0/3 | 1/20 | 0 | 19 | 11/55 | — | — | — |
| existing proposal, new rules | 0/3 | 1/20 | 0 | 19 | 11/55 | — | — | 5 |
| **fresh v5 proposal** | **3/3** | **20/20** | **0** | 0 | 11/27 | `expected_type` **verified** (10 tests, 2 values, across `VerifyToken` and `Valid`) | `expected_is_access` (`= 1`, payload.go:20), `expected_is_refresh` (`= 2`, payload.go:21), both valid | 38/38 |

- **The type rule is now established from observation.** `d_valid_type`, predicate
  `issued_type != expected_type` at `payload.Type != tokenType`, is **verified by local
  agreement 11 times from observed values**. The issued type is the creation's argument,
  taken with execution scope. The expected type is the verification call's argument. Both
  are compared as opaque identities, and nothing is decoded.
- The withheld JWT, gRPC and HTTP cases are all exact.
- **The existing proposal is unchanged**, because its missing evidence still dominates. No
  evidence was attached mechanically. The improvement comes entirely from a fresh proposal
  that cites evidence and uses identity bindings.
- Verified outcomes: 15/37 claims.

## Identity controls (seeded into the v5 proposals)

| control | Case B | Case C | wrong |
|---|---|---|---|
| i1 wrong equality (sides whose shown digests differ) | `name_is_role` **rejected** | `type_everywhere` **rejected** | 0 |
| i2 swapped identity (issued type taken from the verification's occurrence) | — | `d_valid_type` **rejected** (local disagreement); 14 indeterminate | 0 |
| i3 overgeneralized constant (every shown scenario says "expects access") | — | contradicted on the shown wrong-type test, which becomes indeterminate | 0 |
| i4 missing side | identity stays **supported** | identity stays **supported** | 0 |
| i5 wrong literal | `d_upd_owner` **rejected**, 8 facts contradicted | 11 facts contradicted, 11 indeterminate | 0 |

**No control produced a confidently wrong prediction.**
- **i3 and i5 in Case C** were first undetected: their facts were stated on entry calls,
  while the binding lives in a callee. Checking a call's facts against a unique boundary
  *inside* the call fixed that generically.
- **Held-out predictions in i3 and i5 stay exact:** held-out facts are never checked, and
  these seeded errors were confined to shown scenarios.

## Artifacts

| path | contents |
|---|---|
| `docs/runs/genome-simplebank-rbac-103-v5/` | bundle (digest `13ee75db156925c5`), proposal, genome, evaluation, `controls/`, `diagnostic/role-identity.json` |
| `docs/runs/genome-simplebank-tokentype-136-v5/` | bundle (digest `02bbf51cfab90606`), proposal, genome, evaluation, `controls/` |
| `docs/runs/genome-simplebank-{rbac-103,tokentype-136}/rerun-v5/` | the existing proposals under the new rules |
| `docs/runs/value-identity-regression/` | re-established Baserow v4 and Kokoro c2 under the new rules |
| `experiments/genome/controls_value_identity.py` | the identity controls |
| `experiments/genome/build_context_case.py … v5` | the v5 bundles |
