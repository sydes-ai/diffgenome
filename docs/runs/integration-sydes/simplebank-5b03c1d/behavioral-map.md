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
  └→ [gap] db/sqlc.SQLStore.TransferTx
        evidence: rule=claim-member · tests 2

# api.Server.checkSufficientBalance   [changed; outcomes={'returned': 3}; reached by: tests 3: TestTransferAPI/InsufficientBalance, TestTransferAPI/OK, TestTransferAPI/TransferTxError]
## reaches the change
  └api.Server.createTransfer → this
        evidence: observed 3 exec · tests 3
     └api.authMiddleware.<anon>@21  [entrypoint] → this
           evidence: observed 11 exec · tests 11
           reached by: tests 32: TestAuthMiddleware/ExpiredToken, TestAuthMiddleware/InvalidAuthorizationFormat, TestAuthMiddleware/NoAuthorization …
## continues from the change
  └→ api.errorResponse  (see above)

