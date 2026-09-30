# Behavioral Genome — None None (`diffgenome-genome/0`, experimental)

Entry `None`. Semantic items proposed by `None` from a bounded context bundle (sha `None`); every status below was assigned by the deterministic checker, not by the model. Statuses: observed · static · HYPOTHESIS · supported (all citations check out) · VERIFIED (cites an `if` site and both branches observed, no contradiction) · REJECTED (contradicted by an execution).

## Entities (collector facts)


## Variables

- `issued_type` (input) ↔ observed `go:token.NewPayload arg:tokenType` (identity) — supported
- `expected_type` (input) ↔ observed `go:token.PasetoMaker.VerifyToken arg:tokenType` (identity) ↔ observed `go:token.Payload.Valid arg:tokenType` (identity) — VERIFIED
- `expected_is_access` (input) ↔ observed `go:token.Payload.Valid arg:tokenType` (equals_literal) — supported
- `expected_is_refresh` (input) ↔ observed `go:token.Payload.Valid arg:tokenType` (equals_literal) — supported
- `token_expired` (input) — supported
- `token_authentic` (input) — supported
- `rng_fails` (setting) — supported
- `payload_valid` (derived) := `issued_type == expected_type && !token_expired` — supported
- `verify_ok` (derived) := `token_authentic && payload_valid` — supported
- `has_metadata` (input) — supported
- `has_auth_header` (input) — supported
- `header_has_two_fields` (input) — supported
- `scheme_is_bearer` (input) — supported
- `role_permitted` (input) ↔ observed `go:gapi.hasPermission result` (bool) — supported
- `authz_ok` (state) — supported
- `has_violations` (input) — supported
- `caller_is_banker` (input) — supported
- `caller_is_target` (input) — supported
- `password_given` (input) — supported
- `db_update_failed` (input) — supported
- `db_not_found` (input) — supported

## Data dependencies


## Decisions, in path order

### d_np_rng · `rng_fails` at `go:token.NewPayload` site `br:ecd8b89da8b7` — supported

- TRUE : (no call); never time.Now; **stop** — no payload
- FALSE: time.Now; continue — payload built with Type = tokenType
- status: every cited reference checks out (branch); site: br:ecd8b89da8b7 (given); not verified: outcome true never observed at br:ecd8b89da8b7
  - ✓ branch None → None
  - ✓ branch None → None

### d_pc_err · `rng_fails` at `go:token.PasetoMaker.CreateToken` site `br:0713394c9923` — supported

- TRUE : (no call); never maker.paseto.Encrypt; **stop** — creation fails
- FALSE: maker.paseto.Encrypt; continue — token encrypted with typed payload
- status: every cited reference checks out (branch); site: br:0713394c9923 (given); not verified: outcome true never observed at br:0713394c9923
  - ✓ branch None → None

### d_jc_err · `rng_fails` at `go:token.JWTMaker.CreateToken` site `br:d9f1e0c214f9` — supported

- TRUE : (no call); never jwt.NewWithClaims; **stop** — creation fails
- FALSE: jwt.NewWithClaims → jwtToken.SignedString; continue — token signed with typed payload
- status: every cited reference checks out (branch); site: br:d9f1e0c214f9 (given); not verified: outcome true never observed at br:d9f1e0c214f9
  - ✓ branch None → None

### d_valid_type · `issued_type != expected_type` at `go:token.Payload.Valid` site `br:8d10f2f9b136` — VERIFIED

- TRUE : (no call); never time.Now; **stop** — ErrInvalidToken: wrong token type
- FALSE: time.Now; continue — type accepted; expiry checked next
- status: site br:8d10f2f9b136 (`payload.Type != tokenType`) observed true in 1 and false in 10 execution(s); the predicate agrees with the observed outcome 11 time(s) from observed state and in 11 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ source token/payload.go:54 `if payload.Type != tokenType {`
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_pv_decrypt · `!token_authentic` at `go:token.PasetoMaker.VerifyToken` site `br:0607e4d952f6` — supported

- TRUE : (no call); never payload.Valid; **stop** — ErrInvalidToken: undecryptable
- FALSE: payload.Valid; continue — payload decoded, validated against expected type
- status: every cited reference checks out (branch); site: br:0607e4d952f6 (given); not verified: outcome true never observed at br:0607e4d952f6
  - ✓ branch None → None
  - ✓ branch None → None

### d_jv_parse · `token_expired || !token_authentic` at `go:token.JWTMaker.VerifyToken` site `br:b95a526c7153` — VERIFIED

- TRUE : errors.Is; never payload.Valid; **stop** — jwt library rejects (expiry checked by the library, before Valid)
- FALSE: (no call); continue — claims parsed
- status: site br:b95a526c7153 (`err != nil`) observed true in 2 and false in 1 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 3 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_az_md · `!has_metadata` at `go:gapi.Server.authorizeUser` site `br:e3505bc4c4b9` — VERIFIED

- TRUE : fmt.Errorf; never server.tokenMaker.VerifyToken; **stop** — missing metadata
- FALSE: md.Get; continue — 
- status: site br:e3505bc4c4b9 (`!ok`) observed true in 1 and false in 6 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 7 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_mw_hdr · `!has_auth_header` at `go:api.authMiddleware.<anon>@21` site `br:3efaa90434e1` — supported

- TRUE : ctx.AbortWithStatusJSON; never tokenMaker.VerifyToken; **stop** — 401 header not provided
- FALSE: strings.Fields; continue — 
- status: every cited reference checks out (branch, outcome); site: br:3efaa90434e1 (given; observed at runtime, no static facts); not verified: site br:3efaa90434e1 is observed both ways and the predicate agrees 4 time(s), but it has no static facts (unanchored), so its consequences cannot be checked
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_uu_auth · `!authz_ok` at `go:gapi.Server.UpdateUser` site `br:0746154f1c47` — VERIFIED

- TRUE : unauthenticatedError; never validateUpdateUserRequest; **stop** — Unauthenticated
- FALSE: validateUpdateUserRequest; continue — 
- status: site br:0746154f1c47 (`err != nil`) observed true in 2 and false in 5 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 7 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_valid_exp · `token_expired` at `go:token.Payload.Valid` site `br:bdb0acf90853` — VERIFIED

- TRUE : (no call); **stop** — ErrExpiredToken
- FALSE: (no call); continue — payload valid
- status: site br:bdb0acf90853 (`time.Now().After(payload.ExpiredAt)`) observed true in 3 and false in 7 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 10 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_pv_valid · `!payload_valid` at `go:token.PasetoMaker.VerifyToken` site `br:c7d403dfabc3` — VERIFIED

- TRUE : (no call); **stop** — Valid's error propagated
- FALSE: (no call); continue — payload returned
- status: site br:c7d403dfabc3 (`err != nil`) observed true in 4 and false in 6 execution(s); the predicate agrees with the observed outcome 1 time(s) from observed state and in 10 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None
  - ✓ outcome None → None

### d_jv_expired · `token_expired` at `go:token.JWTMaker.VerifyToken` site `br:184d2ca72d5b` — VERIFIED

- TRUE : (no call); **stop** — ErrExpiredToken
- FALSE: (no call); **stop** — ErrInvalidToken
- status: site br:184d2ca72d5b (`errors.Is(err, jwt.ErrTokenExpired)`) observed true in 1 and false in 1 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 2 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_az_hdr · `!has_auth_header` at `go:gapi.Server.authorizeUser` site `br:a572eeb6a4c8` — supported

- TRUE : fmt.Errorf; never server.tokenMaker.VerifyToken; **stop** — missing authorization header
- FALSE: strings.Fields; continue — 
- status: every cited reference checks out (branch); site: br:a572eeb6a4c8 (given); not verified: outcome true never observed at br:a572eeb6a4c8
  - ✓ branch None → None

### d_mw_fields · `!header_has_two_fields` at `go:api.authMiddleware.<anon>@21` site `br:4ede9085ac0b` — supported

- TRUE : ctx.AbortWithStatusJSON; never tokenMaker.VerifyToken; **stop** — 401 invalid format
- FALSE: strings.ToLower; continue — 
- status: every cited reference checks out (branch, outcome); site: br:4ede9085ac0b (given; observed at runtime, no static facts); not verified: site br:4ede9085ac0b is observed both ways and the predicate agrees 3 time(s), but it has no static facts (unanchored), so its consequences cannot be checked
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_uu_viol · `has_violations` at `go:gapi.Server.UpdateUser` site `br:af0e24f4367b` — VERIFIED

- TRUE : invalidArgumentError; never server.store.UpdateUser; **stop** — InvalidArgument
- FALSE: (no call); continue — 
- status: site br:af0e24f4367b (`violations != nil`) observed true in 1 and false in 4 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 5 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_jv_claims · `false` at `go:token.JWTMaker.VerifyToken` site `br:46e44adad2e4` — supported

- TRUE : (no call); never payload.Valid; **stop** — claims not a *Payload
- FALSE: payload.Valid; continue — claims are a *Payload
- status: every cited reference checks out (branch); site: br:46e44adad2e4 (given); not verified: outcome true never observed at br:46e44adad2e4
  - ✓ branch None → None

### d_az_fields · `!header_has_two_fields` at `go:gapi.Server.authorizeUser` site `br:4393757b65d7` — supported

- TRUE : fmt.Errorf; never server.tokenMaker.VerifyToken; **stop** — invalid header format
- FALSE: strings.ToLower; continue — 
- status: every cited reference checks out (branch); site: br:4393757b65d7 (given); not verified: outcome true never observed at br:4393757b65d7
  - ✓ branch None → None

### d_mw_bearer · `!scheme_is_bearer` at `go:api.authMiddleware.<anon>@21` site `br:96c4e761344c` — supported

- TRUE : ctx.AbortWithStatusJSON; never tokenMaker.VerifyToken; **stop** — 401 unsupported type
- FALSE: tokenMaker.VerifyToken; continue — verify as ACCESS token
- status: every cited reference checks out (branch, outcome); site: br:96c4e761344c (given; observed at runtime, no static facts); not verified: site br:96c4e761344c is observed both ways and the predicate agrees 2 time(s), but it has no static facts (unanchored), so its consequences cannot be checked
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_uu_owner · `!caller_is_banker && !caller_is_target` at `go:gapi.Server.UpdateUser` site `br:01807a7b80a2` — VERIFIED

- TRUE : status.Errorf; never server.store.UpdateUser; **stop** — PermissionDenied
- FALSE: (no call); continue — 
- status: site br:01807a7b80a2 (`authPayload.Role != util.BankerRole && authPayload.Username != req.GetUsername()`) observed true in 1 and false in 3 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 4 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_jv_valid · `!payload_valid` at `go:token.JWTMaker.VerifyToken` site `br:8a21855c007e` — supported

- TRUE : (no call); **stop** — Valid's error (wrong type) propagated
- FALSE: (no call); continue — payload returned
- status: every cited reference checks out (branch, outcome, source); site: br:8a21855c007e (given); not verified: outcome true never observed at br:8a21855c007e
  - ✓ branch None → None
  - ✓ source token/jwt_maker.go:61 `err = payload.Valid(tokenType)`
  - ✓ outcome None → None

### d_az_bearer · `!scheme_is_bearer` at `go:gapi.Server.authorizeUser` site `br:2e2f712d6301` — supported

- TRUE : fmt.Errorf; never server.tokenMaker.VerifyToken; **stop** — unsupported authorization type
- FALSE: server.tokenMaker.VerifyToken; continue — verify as ACCESS token
- status: every cited reference checks out (branch); site: br:2e2f712d6301 (given); not verified: outcome true never observed at br:2e2f712d6301
  - ✓ branch None → None

### d_mw_verify · `!verify_ok` at `go:api.authMiddleware.<anon>@21` site `br:052de203d9d4` — supported

- TRUE : ctx.AbortWithStatusJSON; never ctx.Next; **stop** — 401 invalid/expired/wrong-type token
- FALSE: ctx.Set → ctx.Next; continue — payload stored, next handler runs
- status: every cited reference checks out (branch, outcome, source); site: br:052de203d9d4 (given; observed at runtime, no static facts); not verified: outcome false never observed at br:052de203d9d4
  - ✓ source api/middleware.go:45 `payload, err := tokenMaker.VerifyToken(accessToken, token.TokenTypeAcc`
  - ✓ branch None → None
  - ✓ outcome None → None

### d_uu_pw · `password_given` at `go:gapi.Server.UpdateUser` site `br:815be3bfb43a` — supported

- TRUE : util.HashPassword; continue — password hashed into params
- FALSE: (no call); never util.HashPassword; continue — 
- status: every cited reference checks out (branch); site: br:815be3bfb43a (given); not verified: outcome true never observed at br:815be3bfb43a
  - ✓ branch None → None

### d_az_verify · `!verify_ok` at `go:gapi.Server.authorizeUser` site `br:c71158777bce` — VERIFIED

- TRUE : fmt.Errorf; never hasPermission; **stop** — invalid access token (expired, undecryptable, or not an access token)
- FALSE: hasPermission; continue — 
- status: site br:c71158777bce (`err != nil`) observed true in 1 and false in 5 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 6 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ source gapi/authorization.go:40 `payload, err := server.tokenMaker.VerifyToken(accessToken, token.Token`
  - ✓ branch None → None
  - ✓ branch None → None
  - ✓ outcome None → None

### d_uu_dberr · `db_update_failed` at `go:gapi.Server.UpdateUser` site `br:17f2bce25a0f` — VERIFIED

- TRUE : errors.Is; never convertUser; **stop** — store error
- FALSE: convertUser; continue — 
- status: site br:17f2bce25a0f (`err != nil`) observed true in 1 and false in 2 execution(s); the predicate agrees with the observed outcome 0 time(s) from observed state and in 3 replayed/stated case(s), disagreeing in none; branch consequences consistent with static control facts; no contradiction
  - ✓ branch None → None
  - ✓ branch None → None

### d_az_perm · `!role_permitted` at `go:gapi.Server.authorizeUser` site `br:c1bc39962889` — supported

- TRUE : fmt.Errorf; **stop** — permission denied
- FALSE: (no call); continue — payload returned
- status: every cited reference checks out (branch, outcome); site: br:c1bc39962889 (given); not verified: outcome true never observed at br:c1bc39962889
  - ✓ branch None → None
  - ✓ outcome None → None

### d_uu_nf · `db_not_found` at `go:gapi.Server.UpdateUser` site `br:fb1ba40798cf` — supported

- TRUE : status.Errorf; **stop** — NotFound
- FALSE: status.Errorf; **stop** — Internal
- status: every cited reference checks out (branch, outcome); site: br:fb1ba40798cf (given); not verified: outcome false never observed at br:fb1ba40798cf
  - ✓ branch None → None
  - ✓ outcome None → None

## Behavioral rules

- **r_type_match A token is only accepted as the type it was issued as** — supported
  - when `issued_type != expected_type`
  - then Payload.Valid returns ErrInvalidToken before checking expiry; VerifyToken (PASETO and JWT) returns that error and no payload; every caller that verifies fails: gRPC authorizeUser -> UpdateUser Unauthenticated; HTTP authMiddleware -> 401 abort
  - summarizes d_valid_type; every cited reference checks out (branch, source)
- **r_expiry An expired token of the right type is rejected (JWT: by the library at parse time; PASETO: by Valid)** — supported
  - when `issued_type == expected_type && token_expired`
  - then VerifyToken returns ErrExpiredToken; callers reject as for r_type_match
  - summarizes d_valid_exp; every cited reference checks out (branch)
- **r_access_gates Request gates (gRPC authorizeUser, HTTP authMiddleware) demand an ACCESS token** — supported
  - when `has_auth_header && header_has_two_fields && scheme_is_bearer`
  - then VerifyToken is called with expected_type = TokenTypeAccessToken (literal 1); a refresh token presented as bearer fails r_type_match; !verify_ok -> gate rejects
  - summarizes d_az_verify; every cited reference checks out (branch, source)
- **r_refresh_gate Renewing requires a REFRESH token; login issues one of each** — supported
  - when `true`
  - then renewAccessToken verifies req.RefreshToken with TokenTypeRefreshToken, so an access token is rejected with 401; renewAccessToken, loginUser and gapi LoginUser create access tokens with TokenTypeAccessToken and refresh tokens with TokenTypeRefreshToken

## Regimes (behavioral equivalence classes)

- **correctly-typed live access token** — 8 test(s): TestPasetoMaker, TestJWTMaker, OK, BankerCanUpdateUserInfo, InvalidEmail, OtherDepositorCannotUpdateThisUserInfo, UserNotFound, OK — supported
- **token presented as the other type** — 3 test(s): TestPasetoWrongTokenType, TestJWTWrongTokenType, WrongTokenType — supported
- **expired token** — 4 test(s): TestExpiredPasetoToken, TestExpiredJWTToken, ExpiredToken, ExpiredToken — supported
- **no or malformed credentials** — 5 test(s): NoAuthorization, InvalidAuthorizationFormat, UnsupportedAuthorization, NoAuthorization, TestInvalidJWTTokenAlgNone — supported

## State transitions

- **t_valid_ok** `go:token.Payload.Valid` when `issued_type == expected_type && !token_expired`: `payload_valid := true` — supported
- **t_valid_bad** `go:token.Payload.Valid` when `issued_type != expected_type || token_expired`: `payload_valid := false` — supported
- **t_pv_ok** `go:token.PasetoMaker.VerifyToken` when `token_authentic && payload_valid`: `verify_ok := true` — supported
- **t_pv_bad** `go:token.PasetoMaker.VerifyToken` when `!token_authentic || !payload_valid`: `verify_ok := false` — supported
- **t_jv_ok** `go:token.JWTMaker.VerifyToken` when `token_authentic && payload_valid`: `verify_ok := true` — supported
- **t_jv_bad** `go:token.JWTMaker.VerifyToken` when `!token_authentic || token_expired || !payload_valid`: `verify_ok := false` — supported
- **t_authz_granted** `go:gapi.Server.authorizeUser` when `has_metadata && has_auth_header && header_has_two_fields && scheme_is_bearer && verify_ok && role_permitted`: `authz_ok := true` — supported
- **t_authz_denied** `go:gapi.Server.authorizeUser` when `!has_metadata || !has_auth_header || !header_has_two_fields || !scheme_is_bearer || !verify_ok || !role_permitted`: `authz_ok := false` — supported

## Procedures (composition)

- `go:token.NewPayload`: D:d_np_rng — supported
- `go:token.PasetoMaker.CreateToken`: call:go:token.NewPayload → D:d_pc_err — supported
- `go:token.JWTMaker.CreateToken`: call:go:token.NewPayload → D:d_jc_err — supported
- `go:token.Payload.Valid`: D:d_valid_type → D:d_valid_exp → T:t_valid_ok — supported
- `go:token.PasetoMaker.VerifyToken`: D:d_pv_decrypt → call:go:token.Payload.Valid → D:d_pv_valid → T:t_pv_ok — supported
- `go:token.JWTMaker.VerifyToken`: D:d_jv_parse → D:d_jv_claims → call:go:token.Payload.Valid → D:d_jv_valid → T:t_jv_ok — supported
- `go:gapi.Server.authorizeUser`: D:d_az_md → D:d_az_hdr → D:d_az_fields → D:d_az_bearer → call:go:token.PasetoMaker.VerifyToken → D:d_az_verify → call:go:gapi.hasPermission → D:d_az_perm → T:t_authz_granted — supported
- `go:api.authMiddleware.<anon>@21`: D:d_mw_hdr → D:d_mw_fields → D:d_mw_bearer → call:go:token.PasetoMaker.VerifyToken → D:d_mw_verify — supported
- `go:gapi.Server.UpdateUser`: call:go:gapi.Server.authorizeUser → D:d_uu_auth → call:go:gapi.validateUpdateUserRequest → D:d_uu_viol → D:d_uu_owner → D:d_uu_pw → call:go:db/sqlc.Queries.UpdateUser → D:d_uu_dberr → call:go:gapi.convertUser — supported

## Unknown / incomplete (as stated by the model)

- Flow of the type through the token string: issued_type is bound to NewPayload's argument with execution scope and compared by identity with Valid's argument; the genome cannot state that the decrypted payload.Type IS the value encoded at creation (no flow, only equality), and with two tokens created in one execution (login issues access + refresh, renew issues a new access token) the execution-scoped identity is no longer unique, so it would be unknown.
- Which Maker implementation a server uses: Procedures call PasetoMaker.VerifyToken directly because that is what executed; interface dispatch (JWT vs PASETO maker behind token.Maker) is not expressible.
- loginUser, renewAccessToken, gapi LoginUser, gapi CreateUser sites: Not evaluated by any shown or withheld test; not modeled beyond rule r_refresh_gate. renewAccessToken's refresh-typed VerifyToken and session checks would need store/session variables and a relation between the session's stored refresh token and the request token.
- hasPermission role membership: It iterates over accessibleRoles; iteration/membership is not available, so role_permitted is an input bound to hasPermission's bool result.
- JWT expiry location: For JWT, expiry is enforced inside jwt.ParseWithClaims (library), so Valid's expiry branch is effectively unreachable for JWT; modeled by making the parse decision depend on token_expired.
- Literal type of TokenType constants: TokenTypeAccessToken/RefreshToken are untyped constants converted to TokenType (byte); the literal bindings assume the observed value is uint8 1/2.
