# Behavioral Genome — simplebank 5b03c1d (`diffgenome-genome/0`, experimental)

Entry `go:api.Server.createTransfer`. Semantic items proposed by `claude-opus-5-5` from a bounded context bundle (sha `a0fd457517e27822`); every status below was assigned by the deterministic checker, not by the model. Statuses: observed · static · HYPOTHESIS · supported (all citations check out) · VERIFIED (cites an `if` site and both branches observed, no contradiction) · REJECTED (contradicted by an execution).

## Entities (collector facts)

- `api.<anon>@8` — executed · executed by 14 existing execution(s)
- `api.Server.checkSufficientBalance` — changed · executed by 3 existing execution(s)
- `api.Server.createTransfer` — changed · executed by 11 existing execution(s)
- `api.Server.validAccount` — executed · executed by 9 existing execution(s)
- `api.authMiddleware.<anon>@21` — executed · executed by 32 existing execution(s)
- `api.errorResponse` — executed · executed by 36 existing execution(s)
- `util.IsSupportedCurrency` — executed · executed by 14 existing execution(s)
- `sqlc.SQLStore.TransferTx` — boundary:gap · gap via rule claim-member
- `sqlc.Queries.GetAccount` — boundary:gap · gap via rule claim-member

## Variables

- `auth.present` (environment) — supported
- `request.currency_supported` (request) — supported
- `request.amount` (request) — supported
- `from_account.found` (state) — supported
- `from_account.not_found_error` (state) — supported
- `from_account.currency_match` (derived) — supported
- `from_account.owned_by_auth` (derived) — supported
- `to_account.found` (state) — supported
- `to_account.currency_match` (derived) — supported
- `from_account.balance` (state) — supported
- `from_account.balance_sufficient` (derived) := `from_account.balance >= request.amount` — supported
- `transfer_tx.ok` (state) — supported

## Data dependencies

- `request.currency_supported` → D1 (IsSupportedCurrency(request.currency) via binding validator <anon>@8) — supported
- `request.amount` → D2 (binding rule gt=0) — supported
- `request.currency` → Server.validAccount (compared to account.Currency for both from and to accounts) — supported
- `from_account.balance` → D8 (compared with request.amount (balance < amount)) — supported
- `request.amount` → TransferTx (copied into TransferTxParams with from/to ids) — supported
- `auth.username` → D5 (compared with from_account.owner) — supported

## Decisions, in path order

### D0 · `!auth.present` at `authMiddleware` — supported

- TRUE : (no call); never <anon>@8, validAccount, checkSufficientBalance, TransferTx; **stop** — middleware aborts with 401; createTransfer never runs
- FALSE: (no call); continue — payload set, handler invoked
- status: every cited reference checks out (source); not verified: true/false branch not observed with a decodable outcome
  - ✓ source api/middleware.go:24 `if len(authorizationHeader) == 0 {`
  - ✓ source api/middleware.go:51 `ctx.Set(authorizationPayloadKey, payload)`

### D1 · `!request.currency_supported` at `<anon>@8` — VERIFIED

- TRUE : returns false; <anon>@8 → errorResponse; never validAccount, checkSufficientBalance, TransferTx; **stop** — binding fails: 400 Bad Request
- FALSE: returns true; <anon>@8; continue — currency accepted
- status: cites an `if` site; true branch observed in 1 execution(s), false branch in 10; no contradiction
  - ✓ source api/transfer.go:22 `if err := ctx.ShouldBindJSON(&req); err != nil {`
  - ✓ source api/transfer.go:23 `ctx.JSON(http.StatusBadRequest, errorResponse(err))`
  - ✓ execution TestTransferAPI/InvalidCurrency: calls <anon>@8 → errorResponse; never validAccount, TransferTx; <anon>@8=false

### D2 · `request.amount <= 0` at `createTransfer` — supported

- TRUE : errorResponse; never validAccount, checkSufficientBalance, TransferTx; **stop** — binding fails (gt=0): 400 Bad Request
- FALSE: (no call); continue — request bound
- status: every cited reference checks out (execution, source); not verified: true/false branch not observed with a decodable outcome
  - ✓ source api/transfer.go:16 `Amount        int64  `json:"amount" binding:"required,gt=0"``
  - ✓ source api/transfer.go:22 `if err := ctx.ShouldBindJSON(&req); err != nil {`
  - ✓ execution TestTransferAPI/NegativeAmount: calls <anon>@8 → errorResponse; never validAccount, TransferTx; <anon>@8=true

### D3 · `!from_account.found` at `validAccount` — supported

- TRUE : returns false; validAccount → GetAccount → errorResponse; never checkSufficientBalance, TransferTx; **stop** — 404 if ErrRecordNotFound else 500
- FALSE: validAccount → GetAccount; continue — from account loaded
- status: every cited reference checks out (execution, source); not verified: true branch not observed with a decodable outcome
  - ✓ source api/transfer.go:66 `if errors.Is(err, db.ErrRecordNotFound) {`
  - ✓ source api/transfer.go:67 `ctx.JSON(http.StatusNotFound, errorResponse(err))`
  - ✓ source api/transfer.go:71 `ctx.JSON(http.StatusInternalServerError, errorResponse(err))`
  - ✓ execution TestTransferAPI/FromAccountNotFound: calls <anon>@8 → validAccount; never checkSufficientBalance, TransferTx
  - ✓ execution TestTransferAPI/GetAccountError: calls <anon>@8 → validAccount; never checkSufficientBalance, TransferTx

### D4 · `!from_account.currency_match` at `validAccount` — supported

- TRUE : returns false; errorResponse; never checkSufficientBalance, TransferTx; **stop** — 400 currency mismatch
- FALSE: returns true; (no call); continue — from account valid
- status: every cited reference checks out (execution, source); not verified: true/false branch not observed with a decodable outcome
  - ✓ source api/transfer.go:75 `if account.Currency != currency {`
  - ✓ source api/transfer.go:77 `ctx.JSON(http.StatusBadRequest, errorResponse(err))`
  - ✓ execution TestTransferAPI/FromAccountCurrencyMismatch: calls <anon>@8 → validAccount; never checkSufficientBalance, TransferTx

### D5 · `!from_account.owned_by_auth` at `createTransfer` — supported

- TRUE : errorResponse; never checkSufficientBalance, TransferTx; **stop** — 401 Unauthorized; to account never looked up
- FALSE: (no call); continue — ownership confirmed
- status: every cited reference checks out (source); not verified: true/false branch not observed with a decodable outcome
  - ✓ source api/transfer.go:33 `if fromAccount.Owner != authPayload.Username {`
  - ✓ source api/transfer.go:35 `ctx.JSON(http.StatusUnauthorized, errorResponse(err))`

### D6 · `!to_account.found` at `validAccount` — supported

- TRUE : returns false; validAccount → GetAccount → errorResponse; never checkSufficientBalance, TransferTx; **stop** — 404 if ErrRecordNotFound else 500
- FALSE: validAccount → GetAccount; continue — to account loaded
- status: every cited reference checks out (execution, source); not verified: no cited `if` site anchors the predicate
  - ✓ source api/transfer.go:39 `_, valid = server.validAccount(ctx, req.ToAccountID, req.Currency)`
  - ✓ source api/transfer.go:67 `ctx.JSON(http.StatusNotFound, errorResponse(err))`
  - ✓ execution TestTransferAPI/ToAccountNotFound: calls <anon>@8 → validAccount → validAccount; never checkSufficientBalance, TransferTx

### D7 · `!to_account.currency_match` at `validAccount` — supported

- TRUE : returns false; errorResponse; never checkSufficientBalance, TransferTx; **stop** — 400 currency mismatch
- FALSE: returns true; (no call); continue — to account valid
- status: every cited reference checks out (source); not verified: true/false branch not observed with a decodable outcome
  - ✓ source api/transfer.go:75 `if account.Currency != currency {`
  - ✓ source api/transfer.go:40 `if !valid {`

### D8 · `!from_account.balance_sufficient` at `checkSufficientBalance` — VERIFIED

- TRUE : returns false; checkSufficientBalance → errorResponse; never TransferTx; **stop** — 400 insufficient balance; no transfer persisted (the change)
- FALSE: returns true; checkSufficientBalance; continue — proceed to TransferTx
- status: cites an `if` site; true branch observed in 1 execution(s), false branch in 2; no contradiction
  - ✓ source api/transfer.go:44 `if !server.checkSufficientBalance(ctx, fromAccount, req.Amount) {`
  - ✓ source api/transfer.go:85 `if account.Balance < amount {`
  - ✓ source api/transfer.go:87 `ctx.JSON(http.StatusBadRequest, errorResponse(err))`
  - ✓ source api/transfer.go:88 `return false`
  - ✓ execution TestTransferAPI/OK: calls validAccount → validAccount → checkSufficientBalance → TransferTx; never errorResponse; checkSufficientBalance=true

### D9 · `!transfer_tx.ok` at `createTransfer` — supported

- TRUE : TransferTx → errorResponse; **stop** — 500 Internal Server Error
- FALSE: TransferTx; never errorResponse; **stop** — 200 OK with TransferTxResult
- status: every cited reference checks out (execution, source); not verified: true/false branch not observed with a decodable outcome
  - ✓ source api/transfer.go:55 `if err != nil {`
  - ✓ source api/transfer.go:56 `ctx.JSON(http.StatusInternalServerError, errorResponse(err))`
  - ✓ source api/transfer.go:60 `ctx.JSON(http.StatusOK, result)`
  - ✓ execution TestTransferAPI/OK: calls checkSufficientBalance → TransferTx; never errorResponse; checkSufficientBalance=true

## Behavioral rules

- **R1 Request shape gate** — supported
  - when `!request.currency_supported || request.amount <= 0`
  - then 400; no store access (no validAccount, no TransferTx)
  - summarizes D1; summarizes verified decision D1, but its condition also uses request.amount, which that decision does not decide
- **R2 Account eligibility (applied to from, then to)** — supported
  - when `an account must exist (else 404 / 500 on store error) and have the request currency (else 400); first failing account stops the handler`
  - then validAccount returns false; error response inside validAccount; no checkSufficientBalance, no TransferTx
- **R3 Ownership of source account** — supported
  - when `!from_account.owned_by_auth (checked after from is valid, before to is looked up)`
  - then 401; second validAccount not called; no TransferTx
  - summarizes D5; every cited reference checks out (source)
- **R4 Sufficient balance guard (the change)** — VERIFIED
  - when `from_account.balance < request.amount`
  - then checkSufficientBalance returns false; 400; TransferTx not called
  - summarizes D8; summarizes verified decision D8
- **R5 Persist transfer when all gates pass** — supported
  - when `all of R1-R4 pass`
  - then TransferTx called; 200 if transfer_tx.ok else 500
  - summarizes D9; every cited reference checks out (execution, source)

## Regimes (behavioral equivalence classes)

- **unauthenticated (handler not reached)** — 1 test(s): NoAuthorization — supported
- **rejected at binding** — 2 test(s): InvalidCurrency, NegativeAmount — supported
- **rejected at account eligibility** — 5 test(s): FromAccountNotFound, GetAccountError, FromAccountCurrencyMismatch, ToAccountNotFound, ToAccountCurrencyMismatch — supported
- **rejected on ownership** — 1 test(s): UnauthorizedUser — supported
- **rejected on insufficient balance** — 1 test(s): InsufficientBalance — supported
- **transfer attempted** — 2 test(s): OK, TransferTxError — supported

## Effects

- response `HTTP 400 Bad Request` when D1 true | D2 true | D4 true | D7 true | D8 true — supported
- response `HTTP 404 Not Found` when D3 true or D6 true with ErrRecordNotFound — supported
- response `HTTP 500 Internal Server Error` when D3/D6 true with a non-not-found error | D9 true — supported
- response `HTTP 401 Unauthorized` when D0 true | D5 true — supported
- persistence `store.TransferTx (transfer + two entries + two balance updates)` when R5 (all gates pass) — supported
- response `HTTP 200 OK with TransferTxResult` when D9 false — supported

## Unknown / incomplete (as stated by the model)

- Exact from_account.balance in OK / TransferTxError: randomAccount's balance generator is not in the bundle; only InsufficientBalance pins it (amount - 1 = 9). OK's observed checkSufficientBalance=true implies balance >= 10 there; TransferTxError is withheld, so its sufficiency is inferred, not observed. Hence the boolean from_account.balance_sufficient in the decision predicate.
- Whether NoAuthorization reaches createTransfer at all: It is not listed among the 11 executions reaching createTransfer; middleware source shows an abort on empty header, so D0 predicts no handler entry, but no path is shown.
- Order of binding checks when both currency and amount are invalid: D1 (currency) is modeled before D2 (amount), but NegativeAmount shows the currency validator runs even when amount fails; the validator library's field order/aggregation is outside the evidence. No test has both invalid.
- Race between balance check and TransferTx: The guard reads the balance snapshot from GetAccount; TransferTx does not re-check balance (addMoney just adds). Concurrent transfers could still overdraw; tests use a mock store, so this is unobservable here.
- Behaviour of real TransferTx / GetAccount: Store is a gomock in every test; T1 is from source only and never executed.
- Whether 'calls' matching flattens nested callees (e.g. GetAccount, errorResponse inside validAccount): Decision branches list nested entities (GetAccount, errorResponse inside validAccount) in the order they appear in the rendered path; execution refs were restricted to top-level callees to avoid ambiguity.

## Generative check

- **A: amount > balance (decisions >= supported)**: <anon>@8 → validAccount → GetAccount → validAccount → GetAccount → checkSufficientBalance → errorResponse; never TransferTx; stops at D8
- **A: amount > balance (decisions >= verified)**: D0 is supported: its semantics are not established at >= verified
- **B: amount <= balance (decisions >= supported)**: <anon>@8 → validAccount → GetAccount → validAccount → GetAccount → checkSufficientBalance → TransferTx; never errorResponse; stops at D9
- **B: amount <= balance (decisions >= verified)**: D0 is supported: its semantics are not established at >= verified

Per-test phenotype prediction (test facts → genome → predicted path, compared with what executed, order- and count-exact): 11/11; on the executions withheld from the model: 4/4.
