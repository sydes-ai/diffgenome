# Behavioral Genome — None None (`diffgenome-genome/0`, experimental)

Entry `None`. Semantic items proposed by `None` from a bounded context bundle (sha `None`); every status below was assigned by the deterministic checker, not by the model. Statuses: observed · static · HYPOTHESIS · supported (all citations check out) · VERIFIED (cites an `if` site and both branches observed, no contradiction) · REJECTED (contradicted by an execution).

## Entities (collector facts)


## Variables

- `has_metadata` (input) — supported
- `has_auth_header` (input) — supported
- `header_well_formed` (input) — supported
- `bearer_type` (input) — supported
- `token_decrypts` (input) — supported
- `token_expired` (input) ↔ observed `None` (is_set) — supported
- `token_rejected` (derived) := `!token_decrypts || token_expired` — supported
- `role_is_banker` (input) — supported
- `role_is_depositor` (input) — supported
- `role_permitted` (derived) := `role_is_banker || role_is_depositor` — supported
- `authorized` (derived) := `has_metadata && has_auth_header && header_well_formed && bearer_type && !token_rejected && role_permitted` — supported
- `is_self` (input) — supported
- `username_invalid` (input) — supported
- `password_set` (input) — supported
- `password_invalid` (input) — supported
- `fullname_set` (input) — supported
- `fullname_invalid` (input) — supported
- `email_set` (input) — supported
- `email_invalid` (input) — supported
- `has_violations` (derived) := `username_invalid || password_set && password_invalid || fullname_set && fullname_invalid || email_set && email_invalid` — supported
- `hash_fails` (input) — supported
- `store_failed` (input) — supported
- `store_not_found` (input) — supported
- `uuid_fails` (input) — supported

## Data dependencies


## Decisions, in path order

### d_uuid · `uuid_fails` at `go:token.NewPayload` site `br:b4114c26b15a` — supported

- TRUE : (no call); never time.Now; **stop** — no payload is built
- FALSE: (no call); continue — payload carries username, role, issued/expiry times
- status: every cited reference checks out (branch, source); site: br:b4114c26b15a (given); not verified: outcome true never observed at br:b4114c26b15a
  - ✓ branch None → None
  - ✓ source token/payload.go:35 `Role:      role,`

### d_paseto_payload_err · `uuid_fails` at `go:token.PasetoMaker.CreateToken` site `br:0713394c9923` — supported

- TRUE : (no call); never maker.paseto.Encrypt; **stop** — no token
- FALSE: maker.paseto.Encrypt; continue — token encrypts the payload including the role
- status: every cited reference checks out (branch); site: br:0713394c9923 (given); not verified: outcome true never observed at br:0713394c9923
  - ✓ branch None → None

### d_jwt_payload_err · `uuid_fails` at `go:token.JWTMaker.CreateToken` site `br:d9f1e0c214f9` — supported

- TRUE : (no call); **stop** — no token
- FALSE: (no call); continue — token signs the payload including the role
- status: every cited reference checks out (source); site: br:d9f1e0c214f9 (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ source token/jwt_maker.go:28 `payload, err := NewPayload(username, role, duration)`

### d_decrypt · `!token_decrypts` at `go:token.PasetoMaker.VerifyToken` site `br:0607e4d952f6` — supported

- TRUE : (no call); never payload.Valid; **stop** — ErrInvalidToken
- FALSE: (no call); continue — payload decoded
- status: every cited reference checks out (branch); site: br:0607e4d952f6 (given); not verified: outcome true never observed at br:0607e4d952f6
  - ✓ branch None → None

### d_valid_expired · `token_expired` at `go:token.Payload.Valid` site `br:28f7c30a7189` — supported

- TRUE : (no call); **stop** — ErrExpiredToken
- FALSE: (no call); continue — nil error
- status: every cited reference checks out (branch, outcome); site: br:28f7c30a7189 (given); not verified: outcome true never observed at br:28f7c30a7189
  - ✓ branch None → None
  - ✓ outcome None → None

### d_no_metadata · `!has_metadata` at `go:gapi.Server.authorizeUser` site `br:e3505bc4c4b9` — VERIFIED

- TRUE : fmt.Errorf; never md.Get, server.tokenMaker.VerifyToken, hasPermission; **stop** — missing metadata
- FALSE: md.Get; continue — continue
- status: site br:e3505bc4c4b9 (`!ok`) observed true in 1 and false in 4 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 5 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ outcome None → None

### d_hp_matches_banker · `role_is_banker` at `go:gapi.hasPermission` site `br:92f48828a554` — supported

- TRUE : (no call); **stop** — true: role matches the first accessible role (banker)
- FALSE: (no call); continue — compare against the next accessible role
- status: every cited reference checks out (branch, source); site: br:92f48828a554 (given); not verified: site shared with d_hp_matches_depositor — the observable outcome decides only their disjunction
  - ✓ branch None → None
  - ✓ source gapi/authorization.go:54 `if userRole == role {`

### d_val_username · `username_invalid` at `go:gapi.validateUpdateUserRequest` site `br:57793335771a` — supported

- TRUE : fieldViolation; continue — username violation appended
- FALSE: (no call); continue — none
- status: every cited reference checks out (branch); site: br:57793335771a (given); not verified: predicate disagrees with observed outcomes: OK: replayed outcome sequence differs; OtherDepositorCannotUpdateThisUserInfo: replayed outcome sequence differs; UserNotFound: replayed outcome sequence differs
  - ✓ branch None → None

### d_unauthenticated · `!authorized` at `go:gapi.Server.UpdateUser` site `br:0746154f1c47` — VERIFIED

- TRUE : unauthenticatedError; never validateUpdateUserRequest, server.store.UpdateUser; **stop** — codes.Unauthenticated (covers missing auth, bad/expired token and role not permitted)
- FALSE: validateUpdateUserRequest; continue — continue with verified payload
- status: site br:0746154f1c47 (`err != nil`) observed true in 1 and false in 4 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 5 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ outcome None → None

### d_verify_expired · `token_expired` at `go:token.PasetoMaker.VerifyToken` site `br:c7d403dfabc3` — supported

- TRUE : (no call); **stop** — expired token rejected
- FALSE: (no call); continue — payload returned
- status: every cited reference checks out (branch, outcome); site: br:c7d403dfabc3 (given); not verified: outcome true never observed at br:c7d403dfabc3
  - ✓ branch None → None
  - ✓ outcome None → None

### d_no_auth_header · `!has_auth_header` at `go:gapi.Server.authorizeUser` site `br:a572eeb6a4c8` — supported

- TRUE : fmt.Errorf; never server.tokenMaker.VerifyToken; **stop** — missing authorization header
- FALSE: strings.Fields; continue — continue
- status: every cited reference checks out (branch); site: br:a572eeb6a4c8 (given); not verified: outcome true never observed at br:a572eeb6a4c8
  - ✓ branch None → None

### d_hp_matches_depositor · `role_is_depositor` at `go:gapi.hasPermission` site `br:92f48828a554` — supported

- TRUE : (no call); **stop** — true: role matches the second accessible role (depositor)
- FALSE: (no call); continue — list exhausted: false
- status: every cited reference checks out (branch, outcome); site: br:92f48828a554 (given); not verified: site shared with d_hp_matches_banker — the observable outcome decides only their disjunction
  - ✓ branch None → None
  - ✓ outcome None → None

### d_val_password_set · `password_set` at `go:gapi.validateUpdateUserRequest` site `br:444b7eee95f8` — supported

- TRUE : val.ValidatePassword; continue — validate password
- FALSE: (no call); never val.ValidatePassword; continue — skip
- status: every cited reference checks out (branch); site: br:444b7eee95f8 (given); not verified: predicate disagrees with observed outcomes: OK: replayed outcome sequence differs; OtherDepositorCannotUpdateThisUserInfo: replayed outcome sequence differs; UserNotFound: replayed outcome sequence differs
  - ✓ branch None → None

### d_invalid_argument · `has_violations` at `go:gapi.Server.UpdateUser` site `br:af0e24f4367b` — VERIFIED

- TRUE : invalidArgumentError; never server.store.UpdateUser; **stop** — codes.InvalidArgument
- FALSE: (no call); continue — continue
- status: site br:af0e24f4367b (`violations != nil`) observed true in 1 and false in 3 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 4 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ outcome None → None

### d_bad_header_format · `!header_well_formed` at `go:gapi.Server.authorizeUser` site `br:4393757b65d7` — supported

- TRUE : fmt.Errorf; never server.tokenMaker.VerifyToken; **stop** — invalid header format
- FALSE: strings.ToLower; continue — continue
- status: every cited reference checks out (branch); site: br:4393757b65d7 (given); not verified: outcome true never observed at br:4393757b65d7
  - ✓ branch None → None

### d_val_password · `password_invalid` at `go:gapi.validateUpdateUserRequest` site `br:d827424c3b5f` — supported

- TRUE : fieldViolation; continue — password violation appended
- FALSE: (no call); continue — none
- status: every cited reference checks out (source); site: br:d827424c3b5f (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ source gapi/rpc_update_user.go:82 `if err := val.ValidatePassword(req.GetPassword()); err != nil {`

### d_not_owner · `!role_is_banker && !is_self` at `go:gapi.Server.UpdateUser` site `br:01807a7b80a2` — VERIFIED

- TRUE : status.Errorf; never server.store.UpdateUser; **stop** — codes.PermissionDenied: a non-banker may only update itself
- FALSE: (no call); continue — banker, or self-update: proceed
- status: site br:01807a7b80a2 (`authPayload.Role != util.BankerRole && authPayload.Username != req.GetUsername()`) observed true in 1 and false in 2 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 3 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_not_bearer · `!bearer_type` at `go:gapi.Server.authorizeUser` site `br:2e2f712d6301` — supported

- TRUE : fmt.Errorf; never server.tokenMaker.VerifyToken; **stop** — unsupported authorization type
- FALSE: server.tokenMaker.VerifyToken; continue — verify the token
- status: every cited reference checks out (branch); site: br:2e2f712d6301 (given); not verified: outcome true never observed at br:2e2f712d6301
  - ✓ branch None → None

### d_val_fullname_set · `fullname_set` at `go:gapi.validateUpdateUserRequest` site `br:578b58ceb4d3` — supported

- TRUE : val.ValidateFullName; continue — validate full name
- FALSE: (no call); never val.ValidateFullName; continue — skip
- status: every cited reference checks out (branch); site: br:578b58ceb4d3 (given); not verified: predicate disagrees with observed outcomes: OK: replayed outcome sequence differs; OtherDepositorCannotUpdateThisUserInfo: replayed outcome sequence differs; UserNotFound: replayed outcome sequence differs
  - ✓ branch None → None

### d_password_update · `password_set` at `go:gapi.Server.UpdateUser` site `br:815be3bfb43a` — supported

- TRUE : util.HashPassword; continue — hash new password
- FALSE: (no call); never util.HashPassword; continue — password unchanged
- status: every cited reference checks out (branch); site: br:815be3bfb43a (given); not verified: outcome true never observed at br:815be3bfb43a
  - ✓ branch None → None

### d_token_rejected · `token_rejected` at `go:gapi.Server.authorizeUser` site `br:c71158777bce` — supported

- TRUE : fmt.Errorf; never hasPermission; **stop** — invalid access token
- FALSE: hasPermission; continue — check role permission
- status: every cited reference checks out (branch); site: br:c71158777bce (given); not verified: outcome true never observed at br:c71158777bce
  - ✓ branch None → None

### d_val_fullname · `fullname_invalid` at `go:gapi.validateUpdateUserRequest` site `br:864c3600c3d5` — supported

- TRUE : fieldViolation; continue — full_name violation appended
- FALSE: (no call); continue — none
- status: every cited reference checks out (branch); site: br:864c3600c3d5 (given); not verified: predicate disagrees with observed outcomes: OK: replayed outcome sequence differs; OtherDepositorCannotUpdateThisUserInfo: replayed outcome sequence differs; UserNotFound: replayed outcome sequence differs
  - ✓ branch None → None

### d_hash_fails · `hash_fails` at `go:gapi.Server.UpdateUser` site `br:5f17958f3d3f` — supported

- TRUE : status.Errorf; never server.store.UpdateUser; **stop** — codes.Internal
- FALSE: time.Now; continue — hashed password and change time set
- status: every cited reference checks out (source); site: br:5f17958f3d3f (given); not verified: inconsistent with static control facts: server.store.UpdateUser reachable when br:5f17958f3d3f=True
  - ✓ source gapi/rpc_update_user.go:48 `return nil, status.Errorf(codes.Internal, "failed to hash password: %s`

### d_role_not_permitted · `!role_permitted` at `go:gapi.Server.authorizeUser` site `br:c1bc39962889` — supported

- TRUE : fmt.Errorf; **stop** — permission denied
- FALSE: (no call); continue — payload returned
- status: every cited reference checks out (branch, source); site: br:c1bc39962889 (given); not verified: outcome true never observed at br:c1bc39962889
  - ✓ branch None → None
  - ✓ source gapi/authorization.go:45 `if !hasPermission(payload.Role, accessibleRoles) {`

### d_val_email_set · `email_set` at `go:gapi.validateUpdateUserRequest` site `br:9558e38bf1ec` — supported

- TRUE : val.ValidateEmail; continue — validate email
- FALSE: (no call); never val.ValidateEmail; continue — skip
- status: every cited reference checks out (branch); site: br:9558e38bf1ec (given); not verified: predicate disagrees with observed outcomes: OK: replayed outcome sequence differs; OtherDepositorCannotUpdateThisUserInfo: replayed outcome sequence differs; UserNotFound: replayed outcome sequence differs
  - ✓ branch None → None

### d_store_failed · `store_failed` at `go:gapi.Server.UpdateUser` site `br:17f2bce25a0f` — VERIFIED

- TRUE : (no call); never convertUser; **stop** — map store error to status
- FALSE: (no call); continue — convert and return the updated user
- status: site br:17f2bce25a0f (`err != nil`) observed true in 1 and false in 1 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 2 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None

### d_val_email · `email_invalid` at `go:gapi.validateUpdateUserRequest` site `br:f63e639d4185` — supported

- TRUE : fieldViolation; continue — email violation appended
- FALSE: (no call); continue — none
- status: every cited reference checks out (branch); site: br:f63e639d4185 (given); not verified: predicate disagrees with observed outcomes: OK: replayed outcome sequence differs; OtherDepositorCannotUpdateThisUserInfo: replayed outcome sequence differs; UserNotFound: replayed outcome sequence differs
  - ✓ branch None → None
  - ✓ branch None → None

### d_store_not_found · `store_not_found` at `go:gapi.Server.UpdateUser` site `br:fb1ba40798cf` — supported

- TRUE : status.Errorf; **stop** — codes.NotFound
- FALSE: status.Errorf; **stop** — codes.Internal
- status: every cited reference checks out (branch, outcome); site: br:fb1ba40798cf (given); not verified: outcome false never observed at br:fb1ba40798cf
  - ✓ branch None → None
  - ✓ outcome None → None

## Behavioral rules

- **r_token_carries_role Tokens carry the user's role** — supported
  - when `!uuid_fails`
  - then the payload stores the role passed to CreateToken; authorization later reads role_is_banker / role_is_depositor from it
  - summarizes d_uuid; every cited reference checks out (source)
- **r_authentication Unauthenticated callers are rejected before anything else** — supported
  - when `!has_metadata || !has_auth_header || !header_well_formed || !bearer_type || token_rejected`
  - then authorizeUser returns an error at the first failing check; UpdateUser returns codes.Unauthenticated without validating or touching the store
  - summarizes d_unauthenticated; every cited reference checks out (branch)
- **r_role_gate Endpoint role gate** — supported
  - when `!role_permitted`
  - then hasPermission scans the endpoint's accessible roles [banker, depositor] in order, stopping at the first match; a role outside the list makes authorizeUser fail with 'permission denied', which UpdateUser reports as Unauthenticated
  - summarizes d_role_not_permitted; every cited reference checks out (branch)
- **r_validation Invalid fields rejected before ownership** — supported
  - when `has_violations`
  - then UpdateUser returns codes.InvalidArgument; ownership is not checked and the store is not called
  - summarizes d_invalid_argument; every cited reference checks out (branch)
- **r_ownership Bankers may update anyone; others only themselves** — supported
  - when `!role_is_banker && !is_self`
  - then UpdateUser returns codes.PermissionDenied and the store is not called
  - summarizes d_not_owner; every cited reference checks out (branch)
- **r_store_mapping Store result mapping** — supported
  - when `store_failed`
  - then store_not_found -> codes.NotFound, else codes.Internal; otherwise the updated user is converted and returned
  - summarizes d_store_failed; every cited reference checks out (branch)

## Regimes (behavioral equivalence classes)

- **caller not authenticated** — 2 test(s): NoAuthorization, ExpiredToken — supported
- **depositor updating itself** — 3 test(s): OK, UserNotFound, InvalidEmail — supported
- **depositor updating another user** — 1 test(s): OtherDepositorCannotUpdateThisUserInfo — supported
- **banker updating any user** — 1 test(s): BankerCanUpdateUserInfo — supported

## Procedures (composition)

- `go:token.NewPayload`: D:d_uuid — supported
- `go:token.PasetoMaker.CreateToken`: call:go:token.NewPayload → D:d_paseto_payload_err — supported
- `go:token.JWTMaker.CreateToken`: call:go:token.NewPayload → D:d_jwt_payload_err — supported
- `go:token.Payload.Valid`: D:d_valid_expired — supported
- `go:token.PasetoMaker.VerifyToken`: D:d_decrypt → call:go:token.Payload.Valid → D:d_verify_expired — supported
- `go:gapi.hasPermission`: D:d_hp_matches_banker → D:d_hp_matches_depositor — supported
- `go:gapi.Server.authorizeUser`: D:d_no_metadata → D:d_no_auth_header → D:d_bad_header_format → D:d_not_bearer → call:go:token.PasetoMaker.VerifyToken → D:d_token_rejected → call:go:gapi.hasPermission → D:d_role_not_permitted — supported
- `go:gapi.validateUpdateUserRequest`: D:d_val_username → D:d_val_password_set → D:d_val_fullname_set → D:d_val_email_set — supported
- `go:gapi.Server.UpdateUser`: call:go:gapi.Server.authorizeUser → D:d_unauthenticated → call:go:gapi.validateUpdateUserRequest → D:d_invalid_argument → D:d_not_owner → D:d_password_update → call:go:db/sqlc.Queries.UpdateUser → D:d_store_failed → call:go:gapi.convertUser — supported

## Unknown / incomplete (as stated by the model)

- hasPermission's loop over accessibleRoles: Site br:92f48828a554 is evaluated once per list element, but the observed structure reports no repeated region inside hasPermission and iteration over collections is not available. I unrolled it as two decisions on the same site (banker, then depositor), which holds only for UpdateUser's fixed argument []string{BankerRole, DepositorRole}; other endpoints with different accessible-role lists cannot be expressed generically.
- Role identity between token creation and authorization: The role string passed to CreateToken flows through the encrypted token into payload.Role; the genome cannot relate values across calls (only is_set/size/bool/changed_from bindings), so role_is_banker / role_is_depositor / is_self are scenario inputs rather than derived from the CreateToken arguments.
- Non-UpdateUser callers of CreateToken (api loginUser, renewAccessToken, gapi LoginUser): Their required sites are never evaluated by the shown or withheld UpdateUser tests; no decisions or procedures are given for them. A test driving them would be indeterminate.
- Which authorizeUser failure occurred: All authorizeUser errors (including 'permission denied' from the new role gate) are collapsed by UpdateUser into codes.Unauthenticated; the genome cannot distinguish error messages or gRPC codes, only the *status.Error exit kind.
- Boolean results of hasPermission and validateUpdateUserRequest: Result digests (#4026e0, #0dd246, #e96533) are not interpretable as booleans/nil with certainty (a nil typed slice need not digest as Go nil), so role_permitted and has_violations are derived rather than bound at those boundaries.
