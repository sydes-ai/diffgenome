# Behavioral Genome — None None (`diffgenome-genome/0`, experimental)

Entry `None`. Semantic items proposed by `None` from a bounded context bundle (sha `None`); every status below was assigned by the deterministic checker, not by the model. Statuses: observed · static · HYPOTHESIS · supported (all citations check out) · VERIFIED (cites an `if` site and both branches observed, no contradiction) · REJECTED (contradicted by an execution).

## Entities (collector facts)


## Variables

- `rng_ok` (setting) — supported
- `requested_type` (input) — supported
- `duration_negative` (input) — supported
- `issued_type` (state) — supported
- `expected_type` (input) — supported
- `token_expired` (state) — supported
- `token_authentic` (state) — supported
- `claims_are_payload` (derived) — supported
- `payload_valid` (derived) := `issued_type == expected_type && !token_expired` — supported
- `verify_failed` (derived) — supported
- `authorize_failed` (derived) — supported
- `token_create_failed` (derived) — supported
- `auth_metadata_present` (input) — supported
- `auth_header_present` (input) — supported
- `header_has_two_fields` (input) — supported
- `scheme_is_bearer` (input) — supported
- `role_permitted` (derived) ↔ observed `go:gapi.hasPermission result` (bool) — supported
- `has_violations` (input) — supported
- `caller_is_banker` (input) — supported
- `caller_is_target` (input) — supported
- `password_provided` (input) — supported
- `hash_failed` (input) — HYPOTHESIS
- `update_failed` (input) — supported
- `user_not_found` (input) — supported
- `request_malformed` (input) — HYPOTHESIS
- `user_lookup_failed` (input) — HYPOTHESIS
- `password_wrong` (input) — HYPOTHESIS
- `session_create_failed` (input) — HYPOTHESIS
- `session_lookup_failed` (input) — HYPOTHESIS
- `session_not_found` (input) — HYPOTHESIS
- `session_blocked` (input) — HYPOTHESIS
- `session_user_mismatch` (input) — HYPOTHESIS
- `session_token_mismatch` (input) — HYPOTHESIS
- `session_expired` (input) — HYPOTHESIS
- `create_failed` (input) — HYPOTHESIS
- `unique_violation` (input) — HYPOTHESIS

## Data dependencies


## Decisions, in path order

### d_np_rng · `!rng_ok` at `go:token.NewPayload` site `br:ecd8b89da8b7` — supported

- TRUE : (no call); **stop** — no payload; error propagates to CreateToken
- FALSE: (no call); continue — payload built with the requested type
- status: every cited reference checks out (branch); site: br:ecd8b89da8b7 (given); not verified: outcome true never observed at br:ecd8b89da8b7
  - ✓ branch None → None

### d_pc_err · `!rng_ok` at `go:token.PasetoMaker.CreateToken` site `br:0713394c9923` — supported

- TRUE : (no call); **stop** — no token
- FALSE: (no call); continue — payload encrypted into a token
- status: every cited reference checks out (branch); site: br:0713394c9923 (given); not verified: outcome true never observed at br:0713394c9923
  - ✓ branch None → None

### d_jc_err · `!rng_ok` at `go:token.JWTMaker.CreateToken` site `br:d9f1e0c214f9` — supported

- TRUE : (no call); **stop** — no token
- FALSE: (no call); continue — payload signed HS256
- status: every cited reference checks out (branch); site: br:d9f1e0c214f9 (given); not verified: outcome true never observed at br:d9f1e0c214f9
  - ✓ branch None → None

### d_valid_type · `issued_type != expected_type` at `go:token.Payload.Valid` site `br:8d10f2f9b136` — VERIFIED

- TRUE : (no call); never time.Now().After; **stop** — ErrInvalidToken: token of the wrong type; expiry is not examined
- FALSE: (no call); continue — type accepted; go on to expiry
- status: site br:8d10f2f9b136 (`payload.Type != tokenType`) observed true in 1 and false in 10 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 11 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ source token/payload.go:54 `if payload.Type != tokenType {`
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_pv_decrypt · `!token_authentic` at `go:token.PasetoMaker.VerifyToken` site `br:0607e4d952f6` — supported

- TRUE : (no call); never go:token.Payload.Valid; **stop** — ErrInvalidToken
- FALSE: (no call); continue — payload decrypted
- status: every cited reference checks out (branch); site: br:0607e4d952f6 (given); not verified: outcome true never observed at br:0607e4d952f6
  - ✓ branch None → None

### d_jv_parse · `!token_authentic || token_expired` at `go:token.JWTMaker.VerifyToken` site `br:b95a526c7153` — VERIFIED

- TRUE : (no call); never go:token.Payload.Valid; **stop** — jwt library rejects (bad signature/alg or exp claim); our Valid (and the type check) never runs
- FALSE: (no call); continue — claims parsed
- status: site br:b95a526c7153 (`err != nil`) observed true in 2 and false in 1 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 3 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ source token/jwt_maker.go:48 `jwtToken, err := jwt.ParseWithClaims(token, &Payload{}, keyFunc)`
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ branch None → None

### d_az_md · `!auth_metadata_present` at `go:gapi.Server.authorizeUser` site `br:e3505bc4c4b9` — VERIFIED

- TRUE : (no call); never go:token.PasetoMaker.VerifyToken; **stop** — missing metadata
- FALSE: (no call); continue — 
- status: site br:e3505bc4c4b9 (`!ok`) observed true in 1 and false in 6 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 7 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None

### d_uu_auth · `authorize_failed` at `go:gapi.Server.UpdateUser` site `br:0746154f1c47` — VERIFIED

- TRUE : (no call); never go:gapi.validateUpdateUserRequest, go:db/sqlc.Queries.UpdateUser; **stop** — codes.Unauthenticated
- FALSE: (no call); continue — 
- status: site br:0746154f1c47 (`err != nil`) observed true in 2 and false in 5 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 7 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ outcome None → None

### d_mw_hdr · `!auth_header_present` at `go:api.authMiddleware.<anon>@21` site `br:3efaa90434e1` — supported

- TRUE : (no call); never go:token.PasetoMaker.VerifyToken; **stop** — abort 401: header not provided
- FALSE: (no call); continue — 
- status: every cited reference checks out (branch, source); site: br:3efaa90434e1 (given; observed at runtime, no static facts); not verified: site br:3efaa90434e1 is observed both ways and the predicate agrees 4 time(s), but it has no static facts (unanchored), so its consequences cannot be checked
  - ✓ source api/middleware.go:24 `if len(authorizationHeader) == 0 {`
  - ✓ branch None → None
  - ✓ branch None → None

### d_rn_bind · `request_malformed` at `go:api.Server.renewAccessToken` site `br:51914597d4b2` — HYPOTHESIS

- TRUE : (no call); **stop** — 400
- FALSE: (no call); continue — 
- status: no evidence cited; site: br:51914597d4b2 (given)

### d_hl_bind · `request_malformed` at `go:api.Server.loginUser` site `br:eb7b1a216152` — HYPOTHESIS

- TRUE : (no call); **stop** — 400
- FALSE: (no call); continue — 
- status: no evidence cited; site: br:eb7b1a216152 (given)

### d_gl_valid · `has_violations` at `go:gapi.Server.LoginUser` site `br:76bc8d02ae40` — HYPOTHESIS

- TRUE : (no call); **stop** — InvalidArgument
- FALSE: (no call); continue — 
- status: no evidence cited; site: br:76bc8d02ae40 (given)

### d_cu_valid · `has_violations` at `go:gapi.Server.CreateUser` site `br:bb32884fc4f0` — HYPOTHESIS

- TRUE : (no call); **stop** — InvalidArgument
- FALSE: (no call); continue — 
- status: no evidence cited; site: br:bb32884fc4f0 (given)

### d_valid_expiry · `token_expired` at `go:token.Payload.Valid` site `br:bdb0acf90853` — VERIFIED

- TRUE : (no call); **stop** — ErrExpiredToken
- FALSE: (no call); continue — payload valid
- status: site br:bdb0acf90853 (`time.Now().After(payload.ExpiredAt)`) observed true in 3 and false in 7 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 10 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ source token/payload.go:57 `if time.Now().After(payload.ExpiredAt) {`
  - ✓ branch None → None
  - ✓ branch None → None

### d_pv_valid · `!payload_valid` at `go:token.PasetoMaker.VerifyToken` site `br:c7d403dfabc3` — VERIFIED

- TRUE : (no call); **stop** — Valid's error (invalid type or expired) is returned
- FALSE: (no call); continue — payload returned
- status: site br:c7d403dfabc3 (`err != nil`) observed true in 4 and false in 6 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 10 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_jv_expired · `token_expired` at `go:token.JWTMaker.VerifyToken` site `br:184d2ca72d5b` — VERIFIED

- TRUE : (no call); **stop** — ErrExpiredToken
- FALSE: (no call); **stop** — ErrInvalidToken
- status: site br:184d2ca72d5b (`errors.Is(err, jwt.ErrTokenExpired)`) observed true in 1 and false in 1 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 2 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None

### d_az_hdr · `!auth_header_present` at `go:gapi.Server.authorizeUser` site `br:a572eeb6a4c8` — supported

- TRUE : (no call); **stop** — missing authorization header
- FALSE: (no call); continue — 
- status: every cited reference checks out (branch); site: br:a572eeb6a4c8 (given); not verified: outcome true never observed at br:a572eeb6a4c8
  - ✓ branch None → None

### d_uu_valid · `has_violations` at `go:gapi.Server.UpdateUser` site `br:af0e24f4367b` — VERIFIED

- TRUE : (no call); never go:db/sqlc.Queries.UpdateUser; **stop** — codes.InvalidArgument
- FALSE: (no call); continue — 
- status: site br:af0e24f4367b (`violations != nil`) observed true in 1 and false in 4 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 5 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None

### d_mw_fields · `!header_has_two_fields` at `go:api.authMiddleware.<anon>@21` site `br:4ede9085ac0b` — supported

- TRUE : (no call); never go:token.PasetoMaker.VerifyToken; **stop** — abort 401: invalid format
- FALSE: (no call); continue — 
- status: every cited reference checks out (branch, source); site: br:4ede9085ac0b (given; observed at runtime, no static facts); not verified: site br:4ede9085ac0b is observed both ways and the predicate agrees 3 time(s), but it has no static facts (unanchored), so its consequences cannot be checked
  - ✓ source api/middleware.go:31 `if len(fields) < 2 {`
  - ✓ branch None → None

### d_rn_verify · `verify_failed` at `go:api.Server.renewAccessToken` site `br:b98712eb46d4` — supported

- TRUE : (no call); **stop** — 401: e.g. an access token presented as a refresh token
- FALSE: (no call); continue — 
- status: every cited reference checks out (source); site: br:b98712eb46d4 (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ source api/token.go:30 `refreshPayload, err := server.tokenMaker.VerifyToken(req.RefreshToken,`

### d_hl_user · `user_lookup_failed` at `go:api.Server.loginUser` site `br:84d886a24efe` — HYPOTHESIS

- TRUE : (no call); **stop** — 404 or 500
- FALSE: (no call); continue — 
- status: no evidence cited; site: br:84d886a24efe (given)

### d_gl_user · `user_lookup_failed` at `go:gapi.Server.LoginUser` site `br:bbafcfbd5eed` — HYPOTHESIS

- TRUE : (no call); **stop** — NotFound or Internal
- FALSE: (no call); continue — 
- status: no evidence cited; site: br:bbafcfbd5eed (given)

### d_cu_hash · `hash_failed` at `go:gapi.Server.CreateUser` site `br:be27f218e30f` — HYPOTHESIS

- TRUE : (no call); **stop** — Internal
- FALSE: (no call); continue — 
- status: no evidence cited; site: br:be27f218e30f (given)

### d_jv_claims · `!claims_are_payload` at `go:token.JWTMaker.VerifyToken` site `br:46e44adad2e4` — supported

- TRUE : (no call); never go:token.Payload.Valid; **stop** — ErrInvalidToken
- FALSE: (no call); continue — go on to Payload.Valid
- status: every cited reference checks out (branch); site: br:46e44adad2e4 (given); not verified: outcome true never observed at br:46e44adad2e4
  - ✓ branch None → None

### d_az_fields · `!header_has_two_fields` at `go:gapi.Server.authorizeUser` site `br:4393757b65d7` — supported

- TRUE : (no call); **stop** — invalid header format
- FALSE: (no call); continue — 
- status: every cited reference checks out (branch); site: br:4393757b65d7 (given); not verified: outcome true never observed at br:4393757b65d7
  - ✓ branch None → None

### d_uu_perm · `!caller_is_banker && !caller_is_target` at `go:gapi.Server.UpdateUser` site `br:01807a7b80a2` — VERIFIED

- TRUE : (no call); never go:db/sqlc.Queries.UpdateUser; **stop** — codes.PermissionDenied
- FALSE: (no call); continue — 
- status: site br:01807a7b80a2 (`authPayload.Role != util.BankerRole && authPayload.Username != req.GetUsername()`) observed true in 1 and false in 3 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 4 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None

### d_mw_scheme · `!scheme_is_bearer` at `go:api.authMiddleware.<anon>@21` site `br:96c4e761344c` — supported

- TRUE : (no call); never go:token.PasetoMaker.VerifyToken; **stop** — abort 401: unsupported type
- FALSE: (no call); continue — 
- status: every cited reference checks out (branch, source); site: br:96c4e761344c (given; observed at runtime, no static facts); not verified: site br:96c4e761344c is observed both ways and the predicate agrees 2 time(s), but it has no static facts (unanchored), so its consequences cannot be checked
  - ✓ source api/middleware.go:38 `if authorizationType != authorizationTypeBearer {`
  - ✓ branch None → None

### d_rn_session · `session_lookup_failed` at `go:api.Server.renewAccessToken` site `br:d2add7aaa3bb` — HYPOTHESIS

- TRUE : (no call); **stop** — 404 or 500
- FALSE: (no call); continue — 
- status: no evidence cited; site: br:d2add7aaa3bb (given)

### d_hl_notfound · `user_not_found` at `go:api.Server.loginUser` site `br:e540ee8e596a` — HYPOTHESIS

- TRUE : (no call); **stop** — 404
- FALSE: (no call); **stop** — 500
- status: no evidence cited; site: br:e540ee8e596a (given)

### d_gl_notfound · `user_not_found` at `go:gapi.Server.LoginUser` site `br:5524c0c4b7f1` — HYPOTHESIS

- TRUE : (no call); **stop** — NotFound
- FALSE: (no call); **stop** — Internal
- status: no evidence cited; site: br:5524c0c4b7f1 (given)

### d_cu_create · `create_failed` at `go:gapi.Server.CreateUser` site `br:086cd7460869` — HYPOTHESIS

- TRUE : (no call); **stop** — AlreadyExists or Internal
- FALSE: (no call); continue — 
- status: no evidence cited; site: br:086cd7460869 (given)

### d_jv_valid · `!payload_valid` at `go:token.JWTMaker.VerifyToken` site `br:8a21855c007e` — supported

- TRUE : (no call); **stop** — Valid's error (in practice ErrInvalidToken for a wrong type) returned
- FALSE: (no call); continue — payload returned
- status: every cited reference checks out (branch, source); site: br:8a21855c007e (given); not verified: outcome true never observed at br:8a21855c007e
  - ✓ source token/jwt_maker.go:61 `err = payload.Valid(tokenType)`
  - ✓ branch None → None

### d_az_scheme · `!scheme_is_bearer` at `go:gapi.Server.authorizeUser` site `br:2e2f712d6301` — supported

- TRUE : (no call); **stop** — unsupported authorization type
- FALSE: (no call); continue — 
- status: every cited reference checks out (branch); site: br:2e2f712d6301 (given); not verified: outcome true never observed at br:2e2f712d6301
  - ✓ branch None → None

### d_uu_pw · `password_provided` at `go:gapi.Server.UpdateUser` site `br:815be3bfb43a` — supported

- TRUE : (no call); continue — hash the new password
- FALSE: (no call); continue — password untouched
- status: every cited reference checks out (branch); site: br:815be3bfb43a (given); not verified: outcome true never observed at br:815be3bfb43a
  - ✓ branch None → None

### d_mw_verify · `verify_failed` at `go:api.authMiddleware.<anon>@21` site `br:052de203d9d4` — supported

- TRUE : (no call); **stop** — abort 401 with the verification error
- FALSE: (no call); continue — payload stored in context; ctx.Next()
- status: every cited reference checks out (branch, outcome, source); site: br:052de203d9d4 (given; observed at runtime, no static facts); not verified: outcome false never observed at br:052de203d9d4
  - ✓ source api/middleware.go:46 `if err != nil {`
  - ✓ branch None → None
  - ✓ outcome None → None

### d_rn_notfound · `session_not_found` at `go:api.Server.renewAccessToken` site `br:c91282863028` — HYPOTHESIS

- TRUE : (no call); **stop** — 404
- FALSE: (no call); **stop** — 500
- status: no evidence cited; site: br:c91282863028 (given)

### d_hl_pw · `password_wrong` at `go:api.Server.loginUser` site `br:8ac57f80bf1d` — HYPOTHESIS

- TRUE : (no call); **stop** — 401
- FALSE: (no call); continue — 
- status: no evidence cited; site: br:8ac57f80bf1d (given)

### d_gl_pw · `password_wrong` at `go:gapi.Server.LoginUser` site `br:7b2947a85e0c` — HYPOTHESIS

- TRUE : (no call); **stop** — NotFound/Unauthenticated
- FALSE: (no call); continue — 
- status: no evidence cited; site: br:7b2947a85e0c (given)

### d_cu_unique · `unique_violation` at `go:gapi.Server.CreateUser` site `br:f9551788eb8d` — HYPOTHESIS

- TRUE : (no call); **stop** — AlreadyExists (message now passed verbatim via status.Error)
- FALSE: (no call); **stop** — Internal
- status: no evidence cited; site: br:f9551788eb8d (given)

### d_az_verify · `verify_failed` at `go:gapi.Server.authorizeUser` site `br:c71158777bce` — VERIFIED

- TRUE : (no call); never go:gapi.hasPermission; **stop** — invalid access token (wrong type, expired, or undecryptable)
- FALSE: (no call); continue — 
- status: site br:c71158777bce (`err != nil`) observed true in 1 and false in 5 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 6 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_uu_hash · `hash_failed` at `go:gapi.Server.UpdateUser` site `br:5f17958f3d3f` — HYPOTHESIS

- TRUE : (no call); **stop** — codes.Internal
- FALSE: (no call); continue — 
- status: no evidence cited; site: br:5f17958f3d3f (given)

### d_rn_blocked · `session_blocked` at `go:api.Server.renewAccessToken` site `br:4c153bb03d9c` — HYPOTHESIS

- TRUE : (no call); **stop** — 401 blocked session
- FALSE: (no call); continue — 
- status: no evidence cited; site: br:4c153bb03d9c (given)

### d_hl_access · `token_create_failed` at `go:api.Server.loginUser` site `br:b2bb97f7167b` — supported

- TRUE : (no call); **stop** — 500 access token
- FALSE: (no call); continue — 
- status: every cited reference checks out (source); site: br:b2bb97f7167b (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ source api/user.go:115 `token.TokenTypeAccessToken,`

### d_gl_access · `token_create_failed` at `go:gapi.Server.LoginUser` site `br:85b863c14186` — supported

- TRUE : (no call); **stop** — failed to create access token
- FALSE: (no call); continue — 
- status: every cited reference checks out (source); site: br:85b863c14186 (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ source gapi/rpc_login_user.go:41 `token.TokenTypeAccessToken,`

### d_az_role · `!role_permitted` at `go:gapi.Server.authorizeUser` site `br:c1bc39962889` — supported

- TRUE : (no call); **stop** — permission denied
- FALSE: (no call); continue — payload returned
- status: every cited reference checks out (branch); site: br:c1bc39962889 (given); not verified: outcome true never observed at br:c1bc39962889
  - ✓ branch None → None

### d_uu_update · `update_failed` at `go:gapi.Server.UpdateUser` site `br:17f2bce25a0f` — VERIFIED

- TRUE : (no call); never go:gapi.convertUser; **stop** — store error surfaced
- FALSE: (no call); continue — convert and return the user
- status: site br:17f2bce25a0f (`err != nil`) observed true in 1 and false in 2 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 3 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None

### d_rn_user · `session_user_mismatch` at `go:api.Server.renewAccessToken` site `br:58d817da41f5` — HYPOTHESIS

- TRUE : (no call); **stop** — 401 incorrect session user
- FALSE: (no call); continue — 
- status: no evidence cited; site: br:58d817da41f5 (given)

### d_hl_refresh · `token_create_failed` at `go:api.Server.loginUser` site `br:81d23a5f3d1d` — supported

- TRUE : (no call); **stop** — 500 refresh token
- FALSE: (no call); continue — 
- status: every cited reference checks out (source); site: br:81d23a5f3d1d (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ source api/user.go:126 `token.TokenTypeRefreshToken,`

### d_gl_refresh · `token_create_failed` at `go:gapi.Server.LoginUser` site `br:791afc927393` — supported

- TRUE : (no call); **stop** — failed to create refresh token
- FALSE: (no call); continue — 
- status: every cited reference checks out (source); site: br:791afc927393 (given); not verified: neither the observed state at the site nor any stated input facts decide the predicate, so its meaning cannot be checked
  - ✓ source gapi/rpc_login_user.go:51 `token.TokenTypeRefreshToken,`

### d_uu_notfound · `user_not_found` at `go:gapi.Server.UpdateUser` site `br:fb1ba40798cf` — supported

- TRUE : (no call); **stop** — codes.NotFound
- FALSE: (no call); **stop** — codes.Internal
- status: every cited reference checks out (branch); site: br:fb1ba40798cf (given); not verified: outcome false never observed at br:fb1ba40798cf
  - ✓ branch None → None

### d_rn_token · `session_token_mismatch` at `go:api.Server.renewAccessToken` site `br:48d3578e9a44` — HYPOTHESIS

- TRUE : (no call); **stop** — 401 mismatched session token
- FALSE: (no call); continue — 
- status: no evidence cited; site: br:48d3578e9a44 (given)

### d_hl_session · `session_create_failed` at `go:api.Server.loginUser` site `br:7fe5569cfdac` — HYPOTHESIS

- TRUE : (no call); **stop** — 500
- FALSE: (no call); continue — 200 with access + refresh tokens
- status: no evidence cited; site: br:7fe5569cfdac (given)

### d_gl_session · `session_create_failed` at `go:gapi.Server.LoginUser` site `br:65d9ca0b3d0c` — HYPOTHESIS

- TRUE : (no call); **stop** — Internal
- FALSE: (no call); continue — 
- status: no evidence cited; site: br:65d9ca0b3d0c (given)

### d_rn_expired · `session_expired` at `go:api.Server.renewAccessToken` site `br:7b9ae91490eb` — HYPOTHESIS

- TRUE : (no call); **stop** — 401 expired session
- FALSE: (no call); continue — 
- status: no evidence cited; site: br:7b9ae91490eb (given)

### d_rn_create · `token_create_failed` at `go:api.Server.renewAccessToken` site `br:65b3034c3f05` — HYPOTHESIS

- TRUE : (no call); **stop** — 500
- FALSE: (no call); continue — 200 with a new ACCESS-typed token
- status: no evidence cited; site: br:65b3034c3f05 (given)

## Behavioral rules

- **r_type_gate A token is accepted only for the type it was issued as** — supported
  - when `issued_type != expected_type`
  - then Payload.Valid returns ErrInvalidToken before looking at expiry; PasetoMaker.VerifyToken / JWTMaker.VerifyToken return that error; every caller treats it exactly like any other verification failure
  - summarizes d_valid_type; every cited reference checks out (branch)
- **r_type_stamped Creation stamps the requested type into the payload** — supported
  - when `rng_ok`
  - then issued_type := requested_type; login issues one access (1) and one refresh (2) token; renew issues an access token
- **r_entry_expectations Entry points fix the expected type** — supported
  - when `true`
  - then HTTP authMiddleware: expected_type := 1 (access); gRPC authorizeUser: expected_type := 1 (access); HTTP renewAccessToken: expected_type := 2 (refresh); direct VerifyToken callers choose it
- **r_expiry Expired tokens are rejected (after the type check for PASETO; by the JWT library before the type check for JWT)** — supported
  - when `token_expired`
  - then PASETO: Valid returns ErrExpiredToken only if the type matched; JWT: ParseWithClaims fails with ErrTokenExpired and VerifyToken returns ErrExpiredToken; Valid is never reached
  - summarizes d_valid_expiry; every cited reference checks out (branch)
- **r_authenticity Tokens not sealed by this maker are invalid** — supported
  - when `!token_authentic`
  - then VerifyToken returns ErrInvalidToken without calling Valid
  - summarizes d_pv_decrypt; every cited reference checks out (branch)
- **r_verify_to_unauth Verification failure ends the request as unauthenticated** — supported
  - when `verify_failed`
  - then authMiddleware aborts 401 and returns; authorizeUser errors so UpdateUser returns codes.Unauthenticated (*status.Error); renewAccessToken answers 401
  - summarizes d_az_verify; every cited reference checks out (branch)
- **r_header_shape Bearer header required before any token work** — supported
  - when `!auth_header_present || !header_has_two_fields || !scheme_is_bearer`
  - then reject without calling VerifyToken (HTTP 401 / gRPC Unauthenticated)
  - summarizes d_mw_hdr; every cited reference checks out (branch)
- **r_update_policy UpdateUser: valid fields, and banker or self** — supported
  - when `authorized`
  - then violations -> InvalidArgument; neither banker nor self -> PermissionDenied; store not found -> NotFound; else update and return user
  - summarizes d_uu_perm; every cited reference checks out (branch)

## Regimes (behavioral equivalence classes)

- **authentic, unexpired access token presented where access is expected** — 8 test(s): TestPasetoMaker, TestJWTMaker, OK, OK, BankerCanUpdateUserInfo, InvalidEmail, OtherDepositorCannotUpdateThisUserInfo, UserNotFound — HYPOTHESIS
- **token presented as the other type** — 3 test(s): TestPasetoWrongTokenType, TestJWTWrongTokenType, WrongTokenType — supported
- **right type, expired** — 4 test(s): TestExpiredPasetoToken, TestExpiredJWTToken, ExpiredToken, ExpiredToken — HYPOTHESIS
- **token not sealed by the maker** — 1 test(s): TestInvalidJWTTokenAlgNone — HYPOTHESIS
- **authorization header missing or malformed** — 4 test(s): NoAuthorization, InvalidAuthorizationFormat, UnsupportedAuthorization, NoAuthorization — HYPOTHESIS

## State transitions

- **t_stamp_payload** `go:token.NewPayload` when `rng_ok`: `issued_type := requested_type`, `token_expired := duration_negative` — supported
- **t_pc_sealed** `go:token.PasetoMaker.CreateToken`: `token_authentic := true`, `token_create_failed := false` — HYPOTHESIS
- **t_pc_failed** `go:token.PasetoMaker.CreateToken`: `token_create_failed := true` — HYPOTHESIS
- **t_jc_sealed** `go:token.JWTMaker.CreateToken`: `token_authentic := true`, `token_create_failed := false` — HYPOTHESIS
- **t_jc_failed** `go:token.JWTMaker.CreateToken`: `token_create_failed := true` — HYPOTHESIS
- **t_valid_reject** `go:token.Payload.Valid`: `payload_valid := false` — HYPOTHESIS
- **t_valid_accept** `go:token.Payload.Valid`: `payload_valid := true` — HYPOTHESIS
- **t_pv_failed** `go:token.PasetoMaker.VerifyToken`: `verify_failed := true` — HYPOTHESIS
- **t_pv_ok** `go:token.PasetoMaker.VerifyToken`: `verify_failed := false` — HYPOTHESIS
- **t_jv_failed** `go:token.JWTMaker.VerifyToken`: `verify_failed := true` — HYPOTHESIS
- **t_jv_claims** `go:token.JWTMaker.VerifyToken`: `claims_are_payload := true` — supported
- **t_jv_ok** `go:token.JWTMaker.VerifyToken`: `verify_failed := false` — HYPOTHESIS
- **t_az_expect_access** `go:gapi.Server.authorizeUser`: `expected_type := 1` — supported
- **t_az_failed** `go:gapi.Server.authorizeUser`: `authorize_failed := true` — HYPOTHESIS
- **t_az_ok** `go:gapi.Server.authorizeUser`: `authorize_failed := false` — HYPOTHESIS
- **t_mw_expect_access** `go:api.authMiddleware.<anon>@21`: `expected_type := 1` — supported
- **t_rn_expect_refresh** `go:api.Server.renewAccessToken`: `expected_type := 2` — supported
- **t_rn_request_access** `go:api.Server.renewAccessToken`: `requested_type := 1` — supported
- **t_hl_request_access** `go:api.Server.loginUser`: `requested_type := 1` — supported
- **t_hl_request_refresh** `go:api.Server.loginUser`: `requested_type := 2` — supported
- **t_gl_request_access** `go:gapi.Server.LoginUser`: `requested_type := 1` — supported
- **t_gl_request_refresh** `go:gapi.Server.LoginUser`: `requested_type := 2` — supported

## Procedures (composition)

- `go:token.NewPayload`: D:d_np_rng → T:t_stamp_payload — HYPOTHESIS
- `go:token.PasetoMaker.CreateToken`: call:go:token.NewPayload → D:d_pc_err → T:t_pc_sealed — HYPOTHESIS
- `go:token.JWTMaker.CreateToken`: call:go:token.NewPayload → D:d_jc_err → T:t_jc_sealed — HYPOTHESIS
- `go:token.Payload.Valid`: D:d_valid_type → D:d_valid_expiry → T:t_valid_accept — supported
- `go:token.PasetoMaker.VerifyToken`: D:d_pv_decrypt → call:go:token.Payload.Valid → D:d_pv_valid → T:t_pv_ok — supported
- `go:token.JWTMaker.VerifyToken`: D:d_jv_parse → D:d_jv_claims → call:go:token.Payload.Valid → D:d_jv_valid → T:t_jv_ok — supported
- `go:gapi.Server.authorizeUser`: D:d_az_md → D:d_az_hdr → D:d_az_fields → D:d_az_scheme → T:t_az_expect_access → call:go:token.PasetoMaker.VerifyToken → D:d_az_verify → call:go:gapi.hasPermission → D:d_az_role → T:t_az_ok — supported
- `go:gapi.Server.UpdateUser`: call:go:gapi.Server.authorizeUser → D:d_uu_auth → call:go:gapi.validateUpdateUserRequest → D:d_uu_valid → D:d_uu_perm → D:d_uu_pw → call:go:db/sqlc.Queries.UpdateUser → D:d_uu_update → call:go:gapi.convertUser — supported
- `go:api.authMiddleware.<anon>@21`: D:d_mw_hdr → D:d_mw_fields → D:d_mw_scheme → T:t_mw_expect_access → call:go:token.PasetoMaker.VerifyToken → D:d_mw_verify — supported
- `go:api.Server.renewAccessToken`: D:d_rn_bind → T:t_rn_expect_refresh → call:go:token.PasetoMaker.VerifyToken → D:d_rn_verify → D:d_rn_session → D:d_rn_blocked → D:d_rn_user → D:d_rn_token → D:d_rn_expired → T:t_rn_request_access → call:go:token.PasetoMaker.CreateToken → D:d_rn_create — HYPOTHESIS
- `go:api.Server.loginUser`: D:d_hl_bind → D:d_hl_user → D:d_hl_pw → T:t_hl_request_access → call:go:token.PasetoMaker.CreateToken → D:d_hl_access → T:t_hl_request_refresh → call:go:token.PasetoMaker.CreateToken → D:d_hl_refresh → D:d_hl_session — HYPOTHESIS
- `go:gapi.Server.LoginUser`: D:d_gl_valid → D:d_gl_user → D:d_gl_pw → T:t_gl_request_access → call:go:token.PasetoMaker.CreateToken → D:d_gl_access → T:t_gl_request_refresh → call:go:token.PasetoMaker.CreateToken → D:d_gl_refresh → D:d_gl_session — HYPOTHESIS
- `go:gapi.Server.CreateUser`: D:d_cu_valid → D:d_cu_hash → D:d_cu_create — HYPOTHESIS

## Unknown / incomplete (as stated by the model)

- Equality of token types at call boundaries: The only boundary facts are is_set/changed_from/size/bool; the tokenType argument digests (#35ddf6 vs #018508) cannot be bound to integer variables, so issued_type and expected_type are carried by transitions and scenario facts and checked only through br:8d10f2f9b136 outcomes.
- Which token a verification refers to: issued_type/token_expired/token_authentic describe a single 'current token'. Login creates two tokens (access then refresh) and renew verifies one and creates another; tracking per-token identity (the refresh token later presented to renew) needs relation-valued variables or item identity, which are not available. A scenario that creates two tokens and verifies the first would be mis-predicted.
- Interface dispatch of token.Maker: authorizeUser, authMiddleware, renew and login call the Maker interface; procedures name PasetoMaker because servers are observed with PASETO. A JWT-backed server would route to JWTMaker.VerifyToken, whose type check runs after the library's expiry check (ordering differs: expired+wrong-type is ErrExpiredToken for JWT, ErrInvalidToken for PASETO).
- hasPermission loop (br:92f48828a554) and validateUpdateUserRequest internals: Not required; hasPermission is modeled only by its bool result (role_permitted), the loop over accessibleRoles is iteration over a collection.
- HTTP login/renew, gRPC LoginUser/CreateUser runtime behavior: No shown test exercises them; their decisions are proposed from source only, and exit kinds for gRPC error paths are assumed to be *status.Error.
- JWT keyFunc closure (JWTMaker.VerifyToken.<anon>@40): Called by the jwt library; folded into token_authentic rather than modeled.
