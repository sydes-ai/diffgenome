# Behavioral Genome — simplebank git diff 6e2679863e4c691db46ec14761a3b3e303e05ce1..2e2094e209a2e9432b53a0d142f52bc8ccce82c2 (`diffgenome-genome/0`, experimental)

Entry `None`. Semantic items proposed by `None` from a bounded context bundle (sha `None`); every status below was assigned by the deterministic checker, not by the model. Statuses: observed · static · HYPOTHESIS · supported (all citations check out) · VERIFIED (cites an `if` site and both branches observed, no contradiction) · REJECTED (contradicted by an execution).

## Entities (collector facts)


## Variables

- `context has metadata` (input) — supported
- `authorization header present` (input) — supported
- `authorization header has at least 2 fields` (input) — supported
- `authorization type is bearer` (input) ↔ observed `gapi.Server.authorizeUser arg:accessibleRoles` (is_set) — supported
- `access token is valid` (input) — supported
- `userRole equals first accessible role` (input) — supported
- `userRole equals second accessible role` (input) — supported
- `role is permitted` (derived) := `v_role_eq_first || v_role_eq_second` — supported
- `authorization failed` (derived) := `!v_has_metadata || !v_auth_header_present || !v_auth_header_format_valid || !v_auth_type_bearer || !v_token_valid || !v_has_access` — supported
- `request validation violations present` (input) — supported
- `caller is banker` (input) ↔ observed `gapi.Server.authorizeUser result` (bool) — HYPOTHESIS
- `caller updates self` (input) — HYPOTHESIS
- `password provided in request` (input) ↔ observed `gapi.Server.UpdateUser arg:req` (is_set) — supported
- `UpdateUser store call returned error` (input) — supported
- `error is record not found` (input) — supported
- `uuid.NewRandom failed` (input) — supported
- `paseto.Encrypt failed` (input) — supported

## Data dependencies


## Decisions, in path order

### D_auth_missing_metadata · `!v_has_metadata` at `go:gapi.Server.authorizeUser` site `br:e3505bc4c4b9` — VERIFIED

- TRUE : (no call); **stop** — missing metadata
- FALSE: (no call); continue — metadata present
- status: site br:e3505bc4c4b9 (`!ok`) observed true in 1 and false in 6 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 7 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### D_auth_header_empty · `!v_auth_header_present` at `go:gapi.Server.authorizeUser` site `br:a572eeb6a4c8` — supported

- TRUE : (no call); **stop** — missing authorization header
- FALSE: (no call); continue — authorization header present
- status: every cited reference checks out (branch); site: br:a572eeb6a4c8 (given); not verified: outcome true never observed at br:a572eeb6a4c8
  - ✓ branch None → None

### D_auth_header_format · `!v_auth_header_format_valid` at `go:gapi.Server.authorizeUser` site `br:4393757b65d7` — supported

- TRUE : (no call); **stop** — invalid authorization header format
- FALSE: (no call); continue — header format ok
- status: every cited reference checks out (branch); site: br:4393757b65d7 (given); not verified: outcome true never observed at br:4393757b65d7
  - ✓ branch None → None

### D_auth_type · `!v_auth_type_bearer` at `go:gapi.Server.authorizeUser` site `br:2e2f712d6301` — supported

- TRUE : (no call); **stop** — unsupported authorization type
- FALSE: (no call); continue — bearer type ok
- status: every cited reference checks out (branch); site: br:2e2f712d6301 (given); not verified: outcome true never observed at br:2e2f712d6301
  - ✓ branch None → None

### D_auth_verify_err · `!v_token_valid` at `go:gapi.Server.authorizeUser` site `br:c71158777bce` — VERIFIED

- TRUE : (no call); **stop** — invalid or expired access token
- FALSE: (no call); continue — token valid
- status: site br:c71158777bce (`err != nil`) observed true in 1 and false in 5 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 6 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### D_perm_eq_first · `v_role_eq_first` at `go:gapi.hasPermission` site `br:92f48828a554` — supported

- TRUE : (no call); **stop** — permission granted (first match)
- FALSE: (no call); continue — no match yet
- status: every cited reference checks out (branch, outcome); site: br:92f48828a554 (given); not verified: site shared with D_perm_eq_second — the observable outcome decides only their disjunction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### D_perm_eq_second · `v_role_eq_second` at `go:gapi.hasPermission` site `br:92f48828a554` — supported

- TRUE : (no call); **stop** — permission granted (second match)
- FALSE: (no call); **stop** — permission denied (no matches)
- status: every cited reference checks out (branch); site: br:92f48828a554 (given); not verified: site shared with D_perm_eq_first — the observable outcome decides only their disjunction
  - ✓ branch None → None
  - ✓ branch None → None

### D_auth_permission · `!v_has_access` at `go:gapi.Server.authorizeUser` site `br:c1bc39962889` — supported

- TRUE : (no call); **stop** — permission denied
- FALSE: (no call); continue — permission ok
- status: every cited reference checks out (branch); site: br:c1bc39962889 (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ branch None → None

### D_update_auth_err · `v_auth_error` at `go:gapi.Server.UpdateUser` site `br:0746154f1c47` — supported

- TRUE : (no call); **stop** — unauthenticated
- FALSE: (no call); continue — authorized
- status: every cited reference checks out (branch, outcome); site: br:0746154f1c47 (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### D_update_violations · `v_violations_present` at `go:gapi.Server.UpdateUser` site `br:af0e24f4367b` — supported

- TRUE : (no call); **stop** — invalid argument
- FALSE: (no call); continue — no validation errors
- status: every cited reference checks out (branch, outcome); site: br:af0e24f4367b (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### D_update_perm_denied · `!v_is_banker && !v_is_self_user` at `go:gapi.Server.UpdateUser` site `br:01807a7b80a2` — supported

- TRUE : (no call); **stop** — permission denied (cannot update other user's info)
- FALSE: (no call); continue — allowed to update
- status: every cited reference checks out (branch); site: br:01807a7b80a2 (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ branch None → None

### D_update_pwd_present · `v_password_provided` at `go:gapi.Server.UpdateUser` site `br:815be3bfb43a` — supported

- TRUE : (no call); continue — would hash password (not exercised)
- FALSE: (no call); continue — no password change
- status: every cited reference checks out (branch); site: br:815be3bfb43a (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ branch None → None

### D_update_db_err · `v_db_update_error` at `go:gapi.Server.UpdateUser` site `br:17f2bce25a0f` — supported

- TRUE : (no call); continue — db update returned error
- FALSE: (no call); continue — db update ok
- status: every cited reference checks out (branch); site: br:17f2bce25a0f (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ branch None → None
  - ✓ branch None → None

### D_update_not_found · `v_not_found_error` at `go:gapi.Server.UpdateUser` site `br:fb1ba40798cf` — supported

- TRUE : (no call); **stop** — user not found
- FALSE: (no call); **stop** — internal update error
- status: every cited reference checks out (branch, outcome); site: br:fb1ba40798cf (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ branch None → None
  - ✓ outcome None → None

### D_np_uuid_err · `v_uuid_error` at `go:token.NewPayload` site `br:b4114c26b15a` — supported

- TRUE : (no call); **stop** — uuid generation failed
- FALSE: (no call); continue — payload created
- status: every cited reference checks out (branch); site: br:b4114c26b15a (given); not verified: outcome true never observed at br:b4114c26b15a
  - ✓ branch None → None

### D_pm_create_err · `v_paseto_create_error` at `go:token.PasetoMaker.CreateToken` site `br:0713394c9923` — supported

- TRUE : (no call); **stop** — encrypt failed
- FALSE: (no call); continue — token created
- status: every cited reference checks out (branch); site: br:0713394c9923 (given); not verified: outcome true never observed at br:0713394c9923
  - ✓ branch None → None

## Behavioral rules

- **R1 Authorization required and role-permitted** — supported
  - when `!v_has_metadata || !v_auth_header_present || !v_auth_header_format_valid || !v_auth_type_bearer || !v_token_valid || !v_has_access`
  - then D_update_auth_err:true -> unauthenticated
  - summarizes D_update_auth_err; every cited reference checks out (branch)
- **R2 Validation guards update** — supported
  - when `v_violations_present`
  - then D_update_violations:true -> invalid argument error
  - summarizes D_update_violations; every cited reference checks out (branch)
- **R3 Only banker or self can update** — supported
  - when `!v_is_banker && !v_is_self_user`
  - then D_update_perm_denied:true -> permission denied
  - summarizes D_update_perm_denied; every cited reference checks out (branch)
- **R4 DB error classification** — supported
  - when `v_db_update_error`
  - then if v_not_found_error then NotFound else Internal
  - summarizes D_update_db_err; every cited reference checks out (branch)
- **R5 Token creation succeeds** — supported
  - when `!v_uuid_error && !v_paseto_create_error`
  - then CreateToken returns
  - summarizes D_pm_create_err; every cited reference checks out (branch)

## Regimes (behavioral equivalence classes)

- **Authorized and valid request** — 2 test(s): OK, BankerCanUpdateUserInfo — supported
- **Missing authorization** — 1 test(s): NoAuthorization — supported
- **Expired token** — 1 test(s): ExpiredToken — supported
- **Invalid email** — 1 test(s): InvalidEmail — supported
- **DB not found** — 1 test(s): UserNotFound — supported

## Procedures (composition)

- `go:gapi.Server.authorizeUser`: D:D_auth_missing_metadata → D:D_auth_header_empty → D:D_auth_header_format → D:D_auth_type → call:go:token.PasetoMaker.VerifyToken → D:D_auth_verify_err → call:go:gapi.hasPermission → D:D_auth_permission — HYPOTHESIS
- `go:gapi.hasPermission`: D:D_perm_eq_first → D:D_perm_eq_second — supported
- `go:gapi.Server.UpdateUser`: call:go:gapi.Server.authorizeUser → D:D_update_auth_err → call:go:gapi.validateUpdateUserRequest → D:D_update_violations → D:D_update_perm_denied → D:D_update_pwd_present → D:D_update_db_err → D:D_update_not_found → call:go:gapi.convertUser — supported
- `go:token.NewPayload`: D:D_np_uuid_err — supported
- `go:token.PasetoMaker.CreateToken`: call:go:token.NewPayload → D:D_pm_create_err — supported

## Unknown / incomplete (as stated by the model)

- Exact iteration over accessibleRoles inside hasPermission beyond two roles: Observed tests pass at most two roles; loop length not modeled generically. We model two comparisons explicitly to match observed evaluations.
