# Behavioral Genome — None None (`diffgenome-genome/0`, experimental)

Entry `None`. Semantic items proposed by `None` from a bounded context bundle (sha `None`); every status below was assigned by the deterministic checker, not by the model. Statuses: observed · static · HYPOTHESIS · supported (all citations check out) · VERIFIED (cites an `if` site and both branches observed, no contradiction) · REJECTED (contradicted by an execution).

## Entities (collector facts)


## Variables

- `uuid_failed` (setting) — supported
- `token_username` (input) ↔ observed `token.PasetoMaker.CreateToken arg:username` (identity) ↔ observed `token.NewPayload arg:username` (identity) — VERIFIED
- `caller_is_banker` (input) ↔ observed `token.PasetoMaker.CreateToken arg:role` (equals_literal) — supported
- `target_username` (input) — supported
- `has_metadata` (input) — supported
- `has_auth_header` (input) — supported
- `header_well_formed` (input) — supported
- `auth_type_bearer` (input) — supported
- `token_decrypts` (input) — supported
- `token_expired` (input) ↔ observed `token.Payload.Valid result` (is_set) — supported
- `role_matches` (input) — supported
- `has_permission` (derived) — supported
- `auth_failed` (derived) — supported
- `username_invalid` (input) — supported
- `password_set` (input) — supported
- `password_invalid` (input) — supported
- `fullname_set` (input) — supported
- `fullname_invalid` (input) — supported
- `email_set` (input) — supported
- `email_invalid` (input) — supported
- `request_invalid` (derived) — supported
- `hash_failed` (setting) — supported
- `store_failed` (state) — supported
- `store_not_found` (state) — supported

## Data dependencies


## Decisions, in path order

### d_np_uuid · `uuid_failed` at `token.NewPayload` site `br:b4114c26b15a` — supported

- TRUE : (no call); never time.Now; **stop** — no payload
- FALSE: time.Now; continue — payload built with username and role
- status: every cited reference checks out (branch); site: br:b4114c26b15a (given); not verified: outcome true never observed at br:b4114c26b15a
  - ✓ branch None → None

### d_ct_err · `uuid_failed` at `token.PasetoMaker.CreateToken` site `br:0713394c9923` — supported

- TRUE : (no call); never maker.paseto.Encrypt; **stop** — token not created
- FALSE: maker.paseto.Encrypt; continue — payload encrypted into token
- status: every cited reference checks out (branch, control); site: br:0713394c9923 (given); not verified: outcome true never observed at br:0713394c9923
  - ✓ branch None → None
  - ✓ control None → maker.paseto.Encrypt

### d_vt_decrypt · `!token_decrypts` at `token.PasetoMaker.VerifyToken` site `br:0607e4d952f6` — supported

- TRUE : (no call); never payload.Valid; **stop** — ErrInvalidToken
- FALSE: payload.Valid; continue — payload decoded
- status: every cited reference checks out (branch, control); site: br:0607e4d952f6 (given); not verified: outcome true never observed at br:0607e4d952f6
  - ✓ branch None → None
  - ✓ control None → payload.Valid

### d_valid_expired · `token_expired` at `token.Payload.Valid` site `br:28f7c30a7189` — supported

- TRUE : (no call); **stop** — ErrExpiredToken
- FALSE: (no call); continue — nil error
- status: every cited reference checks out (branch, outcome); site: br:28f7c30a7189 (given); not verified: outcome true never observed at br:28f7c30a7189
  - ✓ branch None → None
  - ✓ outcome None → None

### d_az_md · `!has_metadata` at `gapi.Server.authorizeUser` site `br:e3505bc4c4b9` — VERIFIED

- TRUE : fmt.Errorf; never md.Get; **stop** — missing metadata
- FALSE: md.Get; continue — read authorization header
- status: site br:e3505bc4c4b9 (`!ok`) observed true in 1 and false in 4 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 5 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_hp_match · `role_matches` at `gapi.hasPermission` site `br:92f48828a554` — VERIFIED

- TRUE : (no call); **stop** — return true
- FALSE: (no call); continue — try next accessible role
- status: site br:92f48828a554 (`userRole == role`) observed true in 4 and false in 4 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 4 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_vu_username · `username_invalid` at `gapi.validateUpdateUserRequest` site `br:57793335771a` — supported

- TRUE : fieldViolation; continue — username violation
- FALSE: (no call); continue — 
- status: every cited reference checks out (branch); site: br:57793335771a (given); not verified: outcome true never observed at br:57793335771a
  - ✓ branch None → None

### d_upd_auth · `auth_failed` at `gapi.Server.UpdateUser` site `br:0746154f1c47` — VERIFIED

- TRUE : unauthenticatedError; never validateUpdateUserRequest, server.store.UpdateUser; **stop** — Unauthenticated
- FALSE: validateUpdateUserRequest; continue — validate request
- status: site br:0746154f1c47 (`err != nil`) observed true in 1 and false in 4 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 5 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None
  - ✓ control None → unauthenticatedError

### d_vt_valid · `token_expired` at `token.PasetoMaker.VerifyToken` site `br:c7d403dfabc3` — supported

- TRUE : (no call); **stop** — expired token rejected
- FALSE: (no call); continue — payload returned
- status: every cited reference checks out (branch, outcome); site: br:c7d403dfabc3 (given); not verified: outcome true never observed at br:c7d403dfabc3
  - ✓ branch None → None
  - ✓ outcome None → None

### d_az_header · `!has_auth_header` at `gapi.Server.authorizeUser` site `br:a572eeb6a4c8` — supported

- TRUE : fmt.Errorf; never strings.Fields; **stop** — missing authorization header
- FALSE: strings.Fields; continue — split header
- status: every cited reference checks out (branch); site: br:a572eeb6a4c8 (given); not verified: outcome true never observed at br:a572eeb6a4c8
  - ✓ branch None → None

### d_vu_password · `password_set` at `gapi.validateUpdateUserRequest` site `br:444b7eee95f8` — supported

- TRUE : val.ValidatePassword; continue — validate password
- FALSE: (no call); never val.ValidatePassword; continue — 
- status: every cited reference checks out (branch); site: br:444b7eee95f8 (given); not verified: outcome true never observed at br:444b7eee95f8
  - ✓ branch None → None

### d_upd_violations · `request_invalid` at `gapi.Server.UpdateUser` site `br:af0e24f4367b` — VERIFIED

- TRUE : invalidArgumentError; never server.store.UpdateUser; **stop** — InvalidArgument
- FALSE: (no call); continue — ownership check
- status: site br:af0e24f4367b (`violations != nil`) observed true in 1 and false in 3 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 4 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_az_fields · `!header_well_formed` at `gapi.Server.authorizeUser` site `br:4393757b65d7` — supported

- TRUE : fmt.Errorf; never strings.ToLower; **stop** — invalid header format
- FALSE: strings.ToLower; continue — auth type extracted
- status: every cited reference checks out (branch); site: br:4393757b65d7 (given); not verified: outcome true never observed at br:4393757b65d7
  - ✓ branch None → None

### d_vu_password_err · `password_invalid` at `gapi.validateUpdateUserRequest` site `br:d827424c3b5f` — supported

- TRUE : fieldViolation; continue — password violation
- FALSE: (no call); continue — 
- status: every cited reference checks out (source); site: br:d827424c3b5f (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ source gapi/rpc_update_user.go:82 `if err := val.ValidatePassword(req.GetPassword()); err != nil {`

### d_upd_owner · `!caller_is_banker && token_username != target_username` at `gapi.Server.UpdateUser` site `br:01807a7b80a2` — VERIFIED

- TRUE : status.Errorf; never server.store.UpdateUser; **stop** — PermissionDenied: cannot update other user's info
- FALSE: server.store.UpdateUser; continue — build update params
- status: site br:01807a7b80a2 (`authPayload.Role != util.BankerRole && authPayload.Username != req.GetUsername()`) observed true in 1 and false in 2 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 3 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None
  - ✓ control None → server.store.UpdateUser

### d_az_type · `!auth_type_bearer` at `gapi.Server.authorizeUser` site `br:2e2f712d6301` — supported

- TRUE : fmt.Errorf; never server.tokenMaker.VerifyToken; **stop** — unsupported authorization type
- FALSE: server.tokenMaker.VerifyToken; continue — token verified next
- status: every cited reference checks out (branch, control); site: br:2e2f712d6301 (given); not verified: outcome true never observed at br:2e2f712d6301
  - ✓ branch None → None
  - ✓ control None → server.tokenMaker.VerifyToken

### d_vu_fullname · `fullname_set` at `gapi.validateUpdateUserRequest` site `br:578b58ceb4d3` — supported

- TRUE : val.ValidateFullName; continue — validate full name
- FALSE: (no call); never val.ValidateFullName; continue — 
- status: every cited reference checks out (branch); site: br:578b58ceb4d3 (given); not verified: outcome false never observed at br:578b58ceb4d3
  - ✓ branch None → None

### d_upd_password · `password_set` at `gapi.Server.UpdateUser` site `br:815be3bfb43a` — supported

- TRUE : util.HashPassword; continue — hash new password
- FALSE: (no call); never util.HashPassword; continue — password unchanged
- status: every cited reference checks out (branch); site: br:815be3bfb43a (given); not verified: outcome true never observed at br:815be3bfb43a
  - ✓ branch None → None

### d_az_verify · `!token_decrypts || token_expired` at `gapi.Server.authorizeUser` site `br:c71158777bce` — supported

- TRUE : fmt.Errorf; never hasPermission; **stop** — invalid access token
- FALSE: hasPermission; continue — role check next
- status: every cited reference checks out (branch, control); site: br:c71158777bce (given); not verified: outcome true never observed at br:c71158777bce
  - ✓ branch None → None
  - ✓ control None → hasPermission

### d_vu_fullname_err · `fullname_invalid` at `gapi.validateUpdateUserRequest` site `br:864c3600c3d5` — supported

- TRUE : fieldViolation; continue — full name violation
- FALSE: (no call); continue — 
- status: every cited reference checks out (branch); site: br:864c3600c3d5 (given); not verified: outcome true never observed at br:864c3600c3d5
  - ✓ branch None → None

### d_upd_hash · `hash_failed` at `gapi.Server.UpdateUser` site `br:5f17958f3d3f` — supported

- TRUE : status.Errorf; never server.store.UpdateUser; **stop** — Internal: failed to hash password
- FALSE: time.Now; continue — hashed password set
- status: every cited reference checks out (source); site: br:5f17958f3d3f (given); not verified: inconsistent with static control facts: server.store.UpdateUser reachable when br:5f17958f3d3f=True
  - ✓ source gapi/rpc_update_user.go:48 `return nil, status.Errorf(codes.Internal, "failed to hash password: %s`

### d_az_perm · `!has_permission` at `gapi.Server.authorizeUser` site `br:c1bc39962889` — supported

- TRUE : fmt.Errorf; **stop** — permission denied
- FALSE: (no call); continue — payload returned
- status: every cited reference checks out (branch, outcome); site: br:c1bc39962889 (given); not verified: outcome true never observed at br:c1bc39962889
  - ✓ branch None → None
  - ✓ outcome None → None

### d_vu_email · `email_set` at `gapi.validateUpdateUserRequest` site `br:9558e38bf1ec` — supported

- TRUE : val.ValidateEmail; continue — validate email
- FALSE: (no call); never val.ValidateEmail; continue — 
- status: every cited reference checks out (branch); site: br:9558e38bf1ec (given); not verified: outcome false never observed at br:9558e38bf1ec
  - ✓ branch None → None

### d_upd_store · `store_failed` at `gapi.Server.UpdateUser` site `br:17f2bce25a0f` — VERIFIED

- TRUE : errors.Is; never convertUser; **stop** — store error mapped to status
- FALSE: convertUser; continue — response built
- status: site br:17f2bce25a0f (`err != nil`) observed true in 1 and false in 1 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 2 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_vu_email_err · `email_invalid` at `gapi.validateUpdateUserRequest` site `br:f63e639d4185` — VERIFIED

- TRUE : fieldViolation; continue — email violation
- FALSE: (no call); continue — 
- status: site br:f63e639d4185 (`err != nil`) observed true in 1 and false in 3 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 4 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None

### d_upd_notfound · `store_not_found` at `gapi.Server.UpdateUser` site `br:fb1ba40798cf` — supported

- TRUE : status.Errorf; **stop** — NotFound
- FALSE: status.Errorf; **stop** — Internal
- status: every cited reference checks out (branch, outcome); site: br:fb1ba40798cf (given); not verified: outcome false never observed at br:fb1ba40798cf
  - ✓ branch None → None
  - ✓ outcome None → None

## Behavioral rules

- **r_authn authentication gate** — supported
  - when `!has_metadata || !has_auth_header || !header_well_formed || !auth_type_bearer || !token_decrypts || token_expired`
  - then authorizeUser returns an error at the first failing check; UpdateUser returns Unauthenticated (*status.Error) without validating or touching the store
  - summarizes d_upd_auth; every cited reference checks out (branch)
- **r_role_gate endpoint role gate** — supported
  - when `no accessible role of the endpoint equals the token role`
  - then hasPermission scans accessibleRoles in order and returns at the first match; authorizeUser returns 'permission denied'; UpdateUser returns Unauthenticated
  - summarizes d_az_perm; every cited reference checks out (branch)
- **r_validation request validation** — supported
  - when `request_invalid`
  - then UpdateUser returns InvalidArgument before the ownership check
  - summarizes d_upd_violations; every cited reference checks out (branch)
- **r_owner_or_banker banker may update anyone, others only themselves** — supported
  - when `!caller_is_banker && token_username != target_username`
  - then UpdateUser returns PermissionDenied and never calls the store
  - summarizes d_upd_owner; every cited reference checks out (branch)
- **r_store store failure mapping** — supported
  - when `store_failed`
  - then NotFound if ErrRecordNotFound, else Internal; otherwise convertUser and return
  - summarizes d_upd_store; every cited reference checks out (branch)

## Regimes (behavioral equivalence classes)

- **caller not authenticated** — 2 test(s): NoAuthorization, ExpiredToken — supported
- **depositor acting on own account** — 3 test(s): OK, UserNotFound, InvalidEmail — supported
- **depositor acting on another account** — 1 test(s): OtherDepositorCannotUpdateThisUserInfo — supported
- **banker acting on another account** — 1 test(s): BankerCanUpdateUserInfo — supported

## State transitions

- **t_auth_reset** `gapi.Server.authorizeUser`: `auth_failed := false` — supported
- **t_auth_fail** `gapi.Server.authorizeUser`: `auth_failed := true` — supported
- **t_perm_reset** `gapi.hasPermission`: `has_permission := false` — supported
- **t_perm_grant** `gapi.hasPermission` when `role_matches`: `has_permission := true` — supported
- **t_viol_reset** `gapi.validateUpdateUserRequest`: `request_invalid := false` — supported
- **t_viol_add** `gapi.validateUpdateUserRequest`: `request_invalid := true` — supported

## Procedures (composition)

- `token.NewPayload`: D:d_np_uuid — supported
- `token.PasetoMaker.CreateToken`: call:token.NewPayload → D:d_ct_err — supported
- `token.Payload.Valid`: D:d_valid_expired — supported
- `token.PasetoMaker.VerifyToken`: D:d_vt_decrypt → call:token.Payload.Valid → D:d_vt_valid — supported
- `gapi.hasPermission`: T:t_perm_reset → R:rg_roles — supported
- `gapi.Server.authorizeUser`: T:t_auth_reset → D:d_az_md → D:d_az_header → D:d_az_fields → D:d_az_type → call:token.PasetoMaker.VerifyToken → D:d_az_verify → call:gapi.hasPermission → D:d_az_perm — supported
- `gapi.validateUpdateUserRequest`: T:t_viol_reset → D:d_vu_username → D:d_vu_password → D:d_vu_fullname → D:d_vu_email — supported
- `gapi.Server.UpdateUser`: call:gapi.Server.authorizeUser → D:d_upd_auth → call:gapi.validateUpdateUserRequest → D:d_upd_violations → D:d_upd_owner → D:d_upd_password → call:db/sqlc.Queries.UpdateUser → D:d_upd_store → call:gapi.convertUser — supported

## Unknown / incomplete (as stated by the model)

- occurrence facts for rg_roles (role_matches per accessible role): hasPermission iterates accessibleRoles ([banker, depositor] from UpdateUser); whether each entry matches depends on the token role vs the k-th list element, a relation over a collection the format cannot express; the mechanics also printed no explicit repeated-region block for hasPermission, so the region is declared from the two observed evaluations of br:92f48828a554 per call
- target_username vs token_username: req.Username is only visible inside the UpdateUserRequest digest, so the request side of the ownership comparison cannot be bound; only the token side (CreateToken/NewPayload arg:username) is bound as an identity
- role identity through the token: the role passed to CreateToken, stored in the payload and read back as hasPermission's userRole is plausibly one value, but the shown tests carry only the depositor role, so an identity list across those boundaries could not be confirmed (needs two distinct values)
- sites in api.Server.loginUser, api.Server.renewAccessToken, gapi.Server.LoginUser, token.JWTMaker.CreateToken: not evaluated by any shown test and not reached by the UpdateUser tests; no decisions proposed for them
- store_failed/store_not_found and token_decrypts binding: the store is a mock stand-in and Go multi-value results make result is_set bindings ambiguous; these remain scenario inputs
