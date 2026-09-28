# diffgenome behavioral impact report

Change: git diff 5b03c1d
Changed symbols (6):
  api.Server.createTransfer  executed by 11 test(s)
  api.Server.checkSufficientBalance  executed by 3 test(s)
  api.TestTransferAPI  executed by 1 test(s)
  api.TestTransferAPI.<anon>@233  executed by 1 test(s)
  api.TestTransferAPI.<anon>@236  executed by 1 test(s)
  api.TestTransferAPI.<anon>@244  executed by 1 test(s)

## Behavioral neighborhood (before probes)

### Upstream (what reaches the change)
  d1  api.Server.createTransfer → api.Server.checkSufficientBalance  tests=3
  d1  api.authMiddleware.<anon>@21 → api.Server.createTransfer  tests=11
  d2  api.TestAuthMiddleware.<anon>@91 → api.authMiddleware.<anon>@21  tests=5
  d2  api.TestCreateAccountAPI.<anon>@247 → api.authMiddleware.<anon>@21  tests=4
  d2  api.TestGetAccountAPI.<anon>@134 → api.authMiddleware.<anon>@21  tests=6
  d2  api.TestListAccountsAPI.<anon>@396 → api.authMiddleware.<anon>@21  tests=5
  d2  api.TestTransferAPI.<anon>@292 → api.authMiddleware.<anon>@21  tests=12
  d3  TestAuthMiddleware/ExpiredToken → api.TestAuthMiddleware.<anon>@91  tests=1
  d3  TestAuthMiddleware/InvalidAuthorizationFormat → api.TestAuthMiddleware.<anon>@91  tests=1
  d3  TestAuthMiddleware/NoAuthorization → api.TestAuthMiddleware.<anon>@91  tests=1
  d3  TestAuthMiddleware/OK → api.TestAuthMiddleware.<anon>@91  tests=1
  d3  TestAuthMiddleware/UnsupportedAuthorization → api.TestAuthMiddleware.<anon>@91  tests=1
  d3  TestCreateAccountAPI/InternalError → api.TestCreateAccountAPI.<anon>@247  tests=1
  d3  TestCreateAccountAPI/InvalidCurrency → api.TestCreateAccountAPI.<anon>@247  tests=1
  d3  TestCreateAccountAPI/NoAuthorization → api.TestCreateAccountAPI.<anon>@247  tests=1
  d3  TestCreateAccountAPI/OK → api.TestCreateAccountAPI.<anon>@247  tests=1
  d3  TestGetAccountAPI/InternalError → api.TestGetAccountAPI.<anon>@134  tests=1
  d3  TestGetAccountAPI/InvalidID → api.TestGetAccountAPI.<anon>@134  tests=1
  d3  TestGetAccountAPI/NoAuthorization → api.TestGetAccountAPI.<anon>@134  tests=1
  d3  TestGetAccountAPI/NotFound → api.TestGetAccountAPI.<anon>@134  tests=1
  d3  TestGetAccountAPI/OK → api.TestGetAccountAPI.<anon>@134  tests=1
  d3  TestGetAccountAPI/UnauthorizedUser → api.TestGetAccountAPI.<anon>@134  tests=1
  d3  TestListAccountsAPI/InternalError → api.TestListAccountsAPI.<anon>@396  tests=1
  d3  TestListAccountsAPI/InvalidPageID → api.TestListAccountsAPI.<anon>@396  tests=1
  d3  TestListAccountsAPI/InvalidPageSize → api.TestListAccountsAPI.<anon>@396  tests=1
  d3  TestListAccountsAPI/NoAuthorization → api.TestListAccountsAPI.<anon>@396  tests=1
  d3  TestListAccountsAPI/OK → api.TestListAccountsAPI.<anon>@396  tests=1
  d3  TestTransferAPI/FromAccountCurrencyMismatch → api.TestTransferAPI.<anon>@292  tests=1
  d3  TestTransferAPI/FromAccountNotFound → api.TestTransferAPI.<anon>@292  tests=1
  d3  TestTransferAPI/GetAccountError → api.TestTransferAPI.<anon>@292  tests=1
  d3  TestTransferAPI/InsufficientBalance → api.TestTransferAPI.<anon>@292  tests=1
  d3  TestTransferAPI/InvalidCurrency → api.TestTransferAPI.<anon>@292  tests=1
  d3  TestTransferAPI/NegativeAmount → api.TestTransferAPI.<anon>@292  tests=1
  d3  TestTransferAPI/NoAuthorization → api.TestTransferAPI.<anon>@292  tests=1
  d3  TestTransferAPI/OK → api.TestTransferAPI.<anon>@292  tests=1
  d3  TestTransferAPI/ToAccountCurrencyMismatch → api.TestTransferAPI.<anon>@292  tests=1
  d3  TestTransferAPI/ToAccountNotFound → api.TestTransferAPI.<anon>@292  tests=1
  d3  TestTransferAPI/TransferTxError → api.TestTransferAPI.<anon>@292  tests=1
  d3  TestTransferAPI/UnauthorizedUser → api.TestTransferAPI.<anon>@292  tests=1

### Downstream (what continues from the change)
  d1  api.Server.checkSufficientBalance → api.errorResponse  tests=1
  d1  api.Server.createTransfer → api.<anon>@8  tests=11
  d1  api.Server.createTransfer → api.Server.validAccount  tests=9
  d1  api.Server.createTransfer → api.errorResponse  tests=4
  d1  api.Server.createTransfer → [gap] db/sqlc.SQLStore.TransferTx  tests=2  rule=claim-member
  d2  api.<anon>@8 → util.IsSupportedCurrency  tests=14
  d2  api.Server.validAccount → api.errorResponse  tests=5
  d2  api.Server.validAccount → [gap] db/sqlc.Queries.GetAccount  tests=9  rule=claim-member

### Tests establishing these paths (41)
  TestAuthMiddleware/ExpiredToken
  TestAuthMiddleware/InvalidAuthorizationFormat
  TestAuthMiddleware/NoAuthorization
  TestAuthMiddleware/OK
  TestAuthMiddleware/UnsupportedAuthorization
  TestCreateAccountAPI/InternalError
  TestCreateAccountAPI/InvalidCurrency
  TestCreateAccountAPI/NoAuthorization
  TestCreateAccountAPI/OK
  TestCreateUserAPI/DuplicateUsername
  TestCreateUserAPI/InternalError
  TestCreateUserAPI/InvalidEmail
  TestCreateUserAPI/InvalidUsername
  TestCreateUserAPI/TooShortPassword
  TestGetAccountAPI/InternalError
  TestGetAccountAPI/InvalidID
  TestGetAccountAPI/NoAuthorization
  TestGetAccountAPI/NotFound
  TestGetAccountAPI/OK
  TestGetAccountAPI/UnauthorizedUser
  TestListAccountsAPI/InternalError
  TestListAccountsAPI/InvalidPageID
  TestListAccountsAPI/InvalidPageSize
  TestListAccountsAPI/NoAuthorization
  TestListAccountsAPI/OK
  TestLoginUserAPI/IncorrectPassword
  TestLoginUserAPI/InternalError
  TestLoginUserAPI/InvalidUsername
  TestLoginUserAPI/UserNotFound
  TestTransferAPI/FromAccountCurrencyMismatch
  TestTransferAPI/FromAccountNotFound
  TestTransferAPI/GetAccountError
  TestTransferAPI/InsufficientBalance
  TestTransferAPI/InvalidCurrency
  TestTransferAPI/NegativeAmount
  TestTransferAPI/NoAuthorization
  TestTransferAPI/OK
  TestTransferAPI/ToAccountCurrencyMismatch
  TestTransferAPI/ToAccountNotFound
  TestTransferAPI/TransferTxError
  ... 1 more

## Where knowledge stops (before probes)
### internal_gap (2)
  d1  api.Server.createTransfer → [gap] db/sqlc.SQLStore.TransferTx  tests=2  rule=claim-member
  d2  api.Server.validAccount → [gap] db/sqlc.Queries.GetAccount  tests=9  rule=claim-member

## Generated probes
- objective: internal_gap db/sqlc.SQLStore.TransferTx (from api.Server.createTransfer, d1)
  attempt 1: accepted  model=recorded
  learned 5 observed edge(s):
    + go:TestDiffgenomeProbe_TransferTx_ExecutesReal → go:api.TestDiffgenomeProbe_TransferTx_ExecutesReal [raised:go:panic:runtime.errorString]
    + go:api.TestDiffgenomeProbe_TransferTx_ExecutesReal → go:api.newFakeDBTX [returned]
    + go:api.TestDiffgenomeProbe_TransferTx_ExecutesReal → go:db/sqlc.New [returned]
    + go:api.TestDiffgenomeProbe_TransferTx_ExecutesReal → go:db/sqlc.SQLStore.TransferTx [raised:go:panic:runtime.errorString]
    + go:db/sqlc.SQLStore.TransferTx → go:db/sqlc.SQLStore.execTx [raised:go:panic:runtime.errorString]
- objective: internal_gap db/sqlc.Queries.GetAccount (from api.Server.validAccount, d2)
  attempt 1: accepted  model=recorded
  learned 3 observed edge(s):
    + go:TestDiffgenomeProbeQueriesGetAccountExecutes → go:api.TestDiffgenomeProbeQueriesGetAccountExecutes [returned]
    + go:api.TestDiffgenomeProbeQueriesGetAccountExecutes → go:db/sqlc.New [returned]
    + go:api.TestDiffgenomeProbeQueriesGetAccountExecutes → go:db/sqlc.Queries.GetAccount [returned]

## Before vs after
| metric | before | after |
|---|---|---|
| observed edges | 45 | 46 |
| composed edges | 0 | 2 |
| strong joins (VALUE+) | 0 | 0 |
| weak joins | 0 | 2 |
| internal gaps | 2 | 2 |
| unresolved boundaries | 0 | 2 |
| external boundaries | 0 | 0 |
| os boundaries | 0 | 0 |
| unsound attempts | 0 | 4 |
| probe-derived edges | 0 | 5 |
| symbols | 46 | 49 |
| tests | 41 | 43 |
| reconstructed / provisional denominator | 45/47 = 0.957 | 46/52 = 0.885 |

Denominator is provisional: observed + composed edges + internal gaps + unresolved
stand-ins inside the neighborhood, i.e. the seams we know about. It excludes behavior
no execution has come near, and external/OS boundaries, which are terminal by design.

## Remaining after probes
### internal_gap (2)
  d1  api.Server.createTransfer → [gap] db/sqlc.SQLStore.TransferTx  tests=1  rule=claim-member
  d2  api.Server.validAccount → [gap] db/sqlc.Queries.GetAccount  tests=3  rule=claim-member
### unresolved_boundary (2)
  d3  db/sqlc.Queries.GetAccount → [unresolved] go:api.fakeDB.QueryRow  tests=1  rule=no-claim  probe-derived
  d3  db/sqlc.Queries.GetAccount → [unresolved] go:api.fakeRow.Scan  tests=1  rule=no-claim  probe-derived
### weak joins (2)
  d1  api.Server.createTransfer ⇢ db/sqlc.SQLStore.TransferTx  tests=2  join=arg_shape  rule=claim-member  probe-derived
  d2  api.Server.validAccount ⇢ db/sqlc.Queries.GetAccount  tests=8  join=arg_shape  rule=claim-member  probe-derived

## Behavioral map around the changed symbols

```
legend: → observed continuation  ⇢ composed continuation (grade)  [external] outside the repo  [unresolved] stand-in without a resolution  [gap] internal continuation nobody has executed  [declaration] construction/declaration with no in-repo executable body

# api.Server.createTransfer   [changed; outcomes={'returned': 11}; reached by: tests 11: TestTransferAPI/FromAccountCurrencyMismatch, TestTransferAPI/FromAccountNotFound, TestTransferAPI/GetAccountError …]
## reaches the change
  └api.authMiddleware.<anon>@21  [entrypoint] → this
        evidence: observed 11 exec · tests 11
        reached by: tests 32: TestAuthMiddleware/ExpiredToken, TestAuthMiddleware/InvalidAuthorizationFormat, TestAuthMiddleware/NoAuthorization …
## continues from the change
  ├→ api.<anon>@8
  │     evidence: observed 11 exec · tests 11
  │  └→ util.IsSupportedCurrency
  │        evidence: observed 14 exec · tests 14
  ├→ api.Server.checkSufficientBalance
  │     evidence: observed 3 exec · tests 3
  │  └→ api.errorResponse
  │        evidence: observed 1 exec · tests 1
  ├→ api.Server.validAccount
  │     evidence: observed 9 exec · tests 9
  │  ├→ api.errorResponse
  │  │     evidence: observed 5 exec · tests 5
  │  └⇢ db/sqlc.Queries.GetAccount (ARG_SHAPE)
  │        evidence: composed ARG_SHAPE x11 · rule=claim-member · tests 9 · probes 1
  │     ├→ [unresolved] go:api.fakeDB.QueryRow
  │     │     evidence: rule=no-claim · tests 0 · probes 1
  │     └→ [unresolved] go:api.fakeRow.Scan
  │           evidence: rule=no-claim · tests 0 · probes 1
  ├→ api.errorResponse
  │     evidence: observed 4 exec · tests 4
  └⇢ db/sqlc.SQLStore.TransferTx (ARG_SHAPE)
        evidence: composed ARG_SHAPE x1 · rule=claim-member · tests 2 · probes 1
     └→ db/sqlc.SQLStore.execTx
           evidence: observed 1 exec · tests 0 · probes 1

# api.Server.checkSufficientBalance   [changed; outcomes={'returned': 3}; reached by: tests 3: TestTransferAPI/InsufficientBalance, TestTransferAPI/OK, TestTransferAPI/TransferTxError]
## reaches the change
  └api.Server.createTransfer → this
        evidence: observed 3 exec · tests 3
     └api.authMiddleware.<anon>@21  [entrypoint] → this
           evidence: observed 11 exec · tests 11
           reached by: tests 32: TestAuthMiddleware/ExpiredToken, TestAuthMiddleware/InvalidAuthorizationFormat, TestAuthMiddleware/NoAuthorization …
## continues from the change
  └→ api.errorResponse  (see above)

```

The full repo-level graph with every edge's provenance is `graph.json` next to this report (`graph-before.json` is the state before probes). Query it with `python -m diffgenome inspect --graph graph.json --symbol <id or suffix>`.
