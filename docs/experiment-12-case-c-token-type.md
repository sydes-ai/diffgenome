# Experiment 12, Case C: simplebank #136, token type

## The case

| | |
|---|---|
| change | upstream techschool/simplebank#136, reproduced by fork sydes-examples/simplebank#4 |
| revisions | base `7c6f92f` → upstream merge `97f000f`. The fork head `81a38b6` is not in the local clone; the upstream commit and its parent were used. The change was not modified |
| behavior | a `TokenType` (access = 1, refresh = 2) is set at creation and stored in the payload. Both makers' `VerifyToken` take the expected type, and `Payload.Valid` rejects a mismatch with `ErrInvalidToken`. The gRPC `authorizeUser` and the HTTP `authMiddleware` expect access; the HTTP `renewAccessToken` expects refresh; login creates one of each |
| tests | three packages, each run by DiffGenome separately at head and merged: `token` (Paseto and JWT: maker, expired, wrong type, alg none), `gapi` (`TestUpdateUserAPI/*`, including the new `WrongTokenType`), `api` (HTTP `TestAuthMiddleware/*`). 20 tests. **Withheld:** `TestJWTWrongTokenType` (generalization across makers), `TestUpdateUserAPI/WrongTokenType` (gRPC entry) and `TestAuthMiddleware/OK` (HTTP entry) |
| method | the same as Case B: generic builder (2,257 lines, digest `2db56c3b1180a2bd`), fresh isolated Opus proposer, statuses from shown tests only, scoring with required sites and placement checks |

## Failures recorded in order (`docs/runs/genome-simplebank-tokentype-136/frozen-failures.txt`)

| id | class | failure |
|---|---|---|
| C-F0 | target test/environment | The head tests do not compile against the base, so there is no before-phenotype. **No test exercises `renewAccessToken`, so "refresh token accepted for renewal" cannot be scored.** Same-named `CreateUser` traces in `api` and `gapi` collide; they are out of scope |
| C-F1 | mechanics (known since Experiment 09) | Go closures are not lowered. 4 required sites in the HTTP middleware closure are runtime-only (no static facts) |
| C-F2 | **checker (DiffGenome)** | The proposal wrote transition values as JSON literals (`true`, `1`), and the checker crashed. Fixed generically: literals are normalized to expression text at load, with a test |
| C-F3 | proposer | 59 items cite no evidence. They include every token-creation procedure, 16 transitions and 13 variables, so they stay hypotheses and 19 of 20 predictions stop |

## Results

| metric | value |
|---|---|
| held-out exact | **0 / 3** (all indeterminate, from C-F3) |
| all scenarios exact | 1 / 20 |
| confidently wrong | **0** |
| indeterminate | 19 |
| verified decisions | 11 / 55. These include **the type check `payload.Type != tokenType` (`d_valid_type`)**, expiry, both makers' verification paths, `authorizeUser`'s verification, and UpdateUser's auth, validation, permission and update decisions |
| verified transitions | 0 / 22 (none cite evidence, and none is bound at a boundary) |
| verified outcomes | 16 / 73 outcome claims |
| verified occurrence bindings | none used (0 regions) |
| required sites observed and uncovered | 0 |
| `UNKNOWN_DEPENDENCE` (changed functions) | 1 / 61 decision operands, 24 / 181 call arguments |
| rejected / demoted | 0 rejected; 59 hypotheses, all "no evidence cited" |
| structure claims | 50 verified, 40 supported, 0 rejected |
| new schema concepts required | none for this behavior |
| phenotype claims (entry exit) | 18 / 20. The 2 misses are my scoring filter: "VerifyToken" also matched JWT's key closure `VerifyToken.<anon>`, which returns normally. On the `VerifyToken` call itself all 20 are right |

**Diagnostic** (not a score; `diagnostic/`). With every proposed item usable, whatever its
status, the genome predicts **20/20, including all 3 withheld tests**:
- the JWT wrong type, generalized from the Paseto test;
- the gRPC `UpdateUser` with a refresh token;
- the HTTP middleware accepting an access token.

The meaning is right everywhere. The scored failure is the proposer leaving out evidence.

## Answers to the Case C questions

1. **Can the genome track the token-type distinction?** Yes. `NewPayload` stamps the requested
   type (a transition), each entry point sets the expected type, and the verified decision at
   `payload.Type != tokenType` compares them.
2. **Can it predict the four behaviors?**

   | behavior | result |
   |---|---|
   | access token accepted | predicted (diagnostic); held-out HTTP `OK` right |
   | refresh token rejected at an authenticated endpoint | predicted; held-out gRPC `WrongTokenType` and JWT `WrongTokenType` right |
   | refresh token accepted for renewal | **not scorable**: no test runs `renewAccessToken` |
   | newly generated token type | stamped by a transition; checkable only as a scenario input (see 3) |

3. **Does the distinction need value-level identity?**
   - **What is observable:** the digests differ, access `#35ddf6` and refresh `#018508`. The
     type passed at creation and the type expected at verification are equal digests exactly
     when they match.
   - **What is missing:** no binding kind relates two boundaries, and small integers are not
     decoded. So "issued type" and "expected type" are scenario inputs, checked only through
     the verified decision's outcomes.
   - This is the same gap as Case B's role flow: *identity equality between two call
     boundaries*.
4. **Do HTTP and gRPC produce the same rule?** Yes, one rule: `Valid` compares, the entry
   supplies the expected type. The exits differ:

   | entry | on a mismatch |
   |---|---|
   | gRPC | `UpdateUser` returns `*status.Error` |
   | HTTP middleware | returns normally, having aborted with 401. The status code is a value, so Outcome cannot see it |

5. **Does the rule generalize across entry points?** Yes. In the diagnostic, the withheld
   HTTP and gRPC tests were predicted from the direct token tests plus the source. Under the
   scored policy it stays unverified because of C-F3.

**Did occurrence binding stay optional?** Yes: 0 regions. The observed structure showed no
repeated region in the scope, and the proposer used none.

## Artifacts

`docs/runs/genome-simplebank-tokentype-136/`:

| file | contents |
|---|---|
| `context-bundle.md` and `.sha` | the bundle and its digest |
| `holdout.json` | shown and withheld tests |
| `proposals.json` | the fresh Opus proposal |
| `genome.*`, `evaluation.json` | the established genome and its evaluation |
| `diagnostic/` | the all-proposals-usable diagnostic |
| `frozen-failures.txt` | the failure log |
| `existing-tests-{token,gapi,api}.log` | test logs |
