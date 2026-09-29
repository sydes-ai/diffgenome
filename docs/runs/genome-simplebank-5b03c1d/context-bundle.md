# Task: propose the semantic layer of a Behavioral Genome

You are an abstraction engine. You receive evidence already collected from a Go service
(simplebank, change 5b03c1d: "Reject transfers exceeding source account balance"): the
source of the changed code and its direct callees, the tests, a behavioral map, and the
observed execution paths of most tests. Propose a compact, *generative* description of the
behavior of `Server.createTransfer`: which inputs and state feed which decisions, what each
branch does, and which few rules generate the observed paths. Do not describe the call
graph again; describe why paths differ.

Rules you must follow:
- Use only the evidence below. Do not assume behavior you cannot point to.
- Every item must cite evidence refs. A machine will check each ref and assign status
  (hypothesis / supported / verified / rejected). You do not assign status.
- Evidence ref kinds (JSON):
  {"kind": "source", "file": "api/transfer.go", "line": 83, "text": "<exact text on that line>"}
  {"kind": "execution", "test": "TestTransferAPI/OK", "calls": ["checkSufficientBalance", "TransferTx"],
   "absent": ["errorResponse"], "returns": {"checkSufficientBalance": "true"}}
     (calls: must occur in this order in that execution's path; absent: must not occur;
      returns: decoded return value shown as =true/=false in the paths below)
  {"kind": "edge", "caller": "Server.createTransfer", "callee": "Server.checkSufficientBalance"}
- Use entity names as they appear in the execution paths (e.g. `checkSufficientBalance`,
  `validAccount`, `GetAccount`, `TransferTx`, `errorResponse`).
- Predicates are symbolic over variable names you define, using only `<`, `<=`, `>`, `>=`,
  `==`, `!=`, `!name`, `&&`, `||` (no parentheses). Variable names like `request.amount`,
  `from_account.balance`, `from_account.exists`, `auth.username`.
- Some tests' observed paths are deliberately withheld (listed below). Still give their
  input/state facts from the test source in `test_facts`; they will be used to test whether
  your genome predicts what actually executed.

Return ONLY one JSON object with these keys (arrays may be empty; explain in `unknowns`):

{
 "variables":        [{"id", "name", "origin": "request|state|derived|environment", "description", "evidence": [...]}],
 "data_dependencies":[{"id", "source": "<variable>", "sink": "<decision id or entity>", "transform": null|"...", "evidence": [...]}],
 "decisions":        [{"id", "entity", "inputs": ["<variable>"], "predicate": "...", "order": <int, position along createTransfer>,
                       "true_branch":  {"returns": null|"true"|"false", "calls": [...], "absent": [...], "stops": bool, "effect": "..."},
                       "false_branch": {...}, "evidence": [...]}],
 "effects":          [{"id", "kind": "response|persistence|external|none", "target", "condition": "<decision/rule ids>", "evidence": [...]}],
 "transitions":      [{"id", "state_before", "action", "state_after", "evidence": [...]}],
 "rules":            [{"id", "name", "inputs", "relevant_state", "condition", "consequences": [...], "decision": "<decision id>|null", "evidence": [...]}],
 "regimes":          [{"id", "name", "facts": {<variable>: value}, "members": ["<test id>"], "evidence": [...]}],
 "test_facts":       {"<test id>": {<variable>: value, ...}},   (for EVERY test listed, including withheld ones)
 "unknowns":         [{"what", "why"}]
}

Decision semantics for prediction: decisions are evaluated in `order`; the branch taken
contributes its `calls` (the entities reached) and `absent` (entities not reached); a branch
with `stops: true` ends createTransfer. A decision's predicate must be decidable from
`test_facts` values (booleans or numbers).

## The change

```
{
 "spec": "git diff 67ccf46a9bb3366ab95c1ebf07b8f02f93b3b563..5b03c1dfd15e1ee8ea8334d5a60d534239b958a5",
 "symbols": [
  "go:api.Server.checkSufficientBalance",
  "go:api.Server.createTransfer"
 ],
 "symbols_never_executed": []
}
```

## Behavioral map around the change (evidence classes: → observed, ⇢ reconstructed, [gap])

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
  │  └→ [gap] db/sqlc.Queries.GetAccount
  │        evidence: rule=claim-member · tests 9
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

```

## Observed execution paths under createTransfer

Direct callees of `createTransfer` in call order, each with its own direct callees in [brackets]. `=true/=false` is a decoded return value; `!returned-error` is an error return; `(stand-in)` is a mocked call (the store is a gomock in every test). `<anon>@8` is the request-binding currency validator (api/validator.go:8). Every execution passed.

```
TestTransferAPI/FromAccountCurrencyMismatch  (passed)
    createTransfer → <anon>@8=true[IsSupportedCurrency=true], validAccount[GetAccount(stand-in), errorResponse]
TestTransferAPI/FromAccountNotFound  (passed)
    createTransfer → <anon>@8=true[IsSupportedCurrency=true], validAccount[GetAccount(stand-in)!returned-error, errorResponse]
TestTransferAPI/GetAccountError  (passed)
    createTransfer → <anon>@8=true[IsSupportedCurrency=true], validAccount[GetAccount(stand-in)!returned-error, errorResponse]
TestTransferAPI/InvalidCurrency  (passed)
    createTransfer → <anon>@8=false[IsSupportedCurrency=false], errorResponse
TestTransferAPI/NegativeAmount  (passed)
    createTransfer → <anon>@8=true[IsSupportedCurrency=true], errorResponse
TestTransferAPI/OK  (passed)
    createTransfer → <anon>@8=true[IsSupportedCurrency=true], validAccount[GetAccount(stand-in)], validAccount[GetAccount(stand-in)], checkSufficientBalance=true, TransferTx(stand-in)
TestTransferAPI/ToAccountNotFound  (passed)
    createTransfer → <anon>@8=true[IsSupportedCurrency=true], validAccount[GetAccount(stand-in)], validAccount[GetAccount(stand-in)!returned-error, errorResponse]
```

Withheld (observed but not shown): TestTransferAPI/InsufficientBalance, TestTransferAPI/ToAccountCurrencyMismatch, TestTransferAPI/TransferTxError, TestTransferAPI/UnauthorizedUser

## Static decision sites (every `if` line; no semantics)

- api/transfer.go:22  if err := ctx.ShouldBindJSON(&req); err != nil
- api/transfer.go:28  if !valid
- api/transfer.go:33  if fromAccount.Owner != authPayload.Username
- api/transfer.go:40  if !valid
- api/transfer.go:44  if !server.checkSufficientBalance(ctx, fromAccount, req.Amount)
- api/transfer.go:55  if err != nil
- api/transfer.go:65  if err != nil
- api/transfer.go:66  if errors.Is(err, db.ErrRecordNotFound)
- api/transfer.go:75  if account.Currency != currency
- api/transfer.go:85  if account.Balance < amount
- api/validator.go:9  if currency, ok := fieldLevel.Field().Interface().(string); ok

## Source: api/transfer.go

```go
   1  package api
   2  
   3  import (
   4  	"errors"
   5  	"fmt"
   6  	"net/http"
   7  
   8  	"github.com/gin-gonic/gin"
   9  	db "github.com/techschool/simplebank/db/sqlc"
  10  	"github.com/techschool/simplebank/token"
  11  )
  12  
  13  type transferRequest struct {
  14  	FromAccountID int64  `json:"from_account_id" binding:"required,min=1"`
  15  	ToAccountID   int64  `json:"to_account_id" binding:"required,min=1"`
  16  	Amount        int64  `json:"amount" binding:"required,gt=0"`
  17  	Currency      string `json:"currency" binding:"required,currency"`
  18  }
  19  
  20  func (server *Server) createTransfer(ctx *gin.Context) {
  21  	var req transferRequest
  22  	if err := ctx.ShouldBindJSON(&req); err != nil {
  23  		ctx.JSON(http.StatusBadRequest, errorResponse(err))
  24  		return
  25  	}
  26  
  27  	fromAccount, valid := server.validAccount(ctx, req.FromAccountID, req.Currency)
  28  	if !valid {
  29  		return
  30  	}
  31  
  32  	authPayload := ctx.MustGet(authorizationPayloadKey).(*token.Payload)
  33  	if fromAccount.Owner != authPayload.Username {
  34  		err := errors.New("from account doesn't belong to the authenticated user")
  35  		ctx.JSON(http.StatusUnauthorized, errorResponse(err))
  36  		return
  37  	}
  38  
  39  	_, valid = server.validAccount(ctx, req.ToAccountID, req.Currency)
  40  	if !valid {
  41  		return
  42  	}
  43  
  44  	if !server.checkSufficientBalance(ctx, fromAccount, req.Amount) {
  45  		return
  46  	}
  47  
  48  	arg := db.TransferTxParams{
  49  		FromAccountID: req.FromAccountID,
  50  		ToAccountID:   req.ToAccountID,
  51  		Amount:        req.Amount,
  52  	}
  53  
  54  	result, err := server.store.TransferTx(ctx, arg)
  55  	if err != nil {
  56  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
  57  		return
  58  	}
  59  
  60  	ctx.JSON(http.StatusOK, result)
  61  }
  62  
  63  func (server *Server) validAccount(ctx *gin.Context, accountID int64, currency string) (db.Account, bool) {
  64  	account, err := server.store.GetAccount(ctx, accountID)
  65  	if err != nil {
  66  		if errors.Is(err, db.ErrRecordNotFound) {
  67  			ctx.JSON(http.StatusNotFound, errorResponse(err))
  68  			return account, false
  69  		}
  70  
  71  		ctx.JSON(http.StatusInternalServerError, errorResponse(err))
  72  		return account, false
  73  	}
  74  
  75  	if account.Currency != currency {
  76  		err := fmt.Errorf("account [%d] currency mismatch: %s vs %s", account.ID, account.Currency, currency)
  77  		ctx.JSON(http.StatusBadRequest, errorResponse(err))
  78  		return account, false
  79  	}
  80  
  81  	return account, true
  82  }
  83  
  84  func (server *Server) checkSufficientBalance(ctx *gin.Context, account db.Account, amount int64) bool {
  85  	if account.Balance < amount {
  86  		err := fmt.Errorf("account [%d] has insufficient balance: %d < %d", account.ID, account.Balance, amount)
  87  		ctx.JSON(http.StatusBadRequest, errorResponse(err))
  88  		return false
  89  	}
  90  
  91  	return true
  92  }
```

## Source: api/validator.go

```go
   1  package api
   2  
   3  import (
   4  	"github.com/go-playground/validator/v10"
   5  	"github.com/techschool/simplebank/util"
   6  )
   7  
   8  var validCurrency validator.Func = func(fieldLevel validator.FieldLevel) bool {
   9  	if currency, ok := fieldLevel.Field().Interface().(string); ok {
  10  		return util.IsSupportedCurrency(currency)
  11  	}
  12  	return false
  13  }
```

## Source: util/currency.go

```go
   1  package util
   2  
   3  // Constants for all supported currencies
   4  const (
   5  	USD = "USD"
   6  	EUR = "EUR"
   7  	CAD = "CAD"
   8  )
   9  
  10  // IsSupportedCurrency returns true if the currency is supported
  11  func IsSupportedCurrency(currency string) bool {
  12  	switch currency {
  13  	case USD, EUR, CAD:
  14  		return true
  15  	}
  16  	return false
  17  }
```

## Source: api/server.go

```go
   1  package api
   2  
   3  import (
   4  	"fmt"
   5  
   6  	"github.com/gin-gonic/gin"
   7  	"github.com/gin-gonic/gin/binding"
   8  	"github.com/go-playground/validator/v10"
   9  	db "github.com/techschool/simplebank/db/sqlc"
  10  	"github.com/techschool/simplebank/token"
  11  	"github.com/techschool/simplebank/util"
  12  )
  13  
  14  // Server serves HTTP requests for our banking service.
  15  type Server struct {
  16  	config     util.Config
  17  	store      db.Store
  18  	tokenMaker token.Maker
  19  	router     *gin.Engine
  20  }
  21  
  22  // NewServer creates a new HTTP server and set up routing.
  23  func NewServer(config util.Config, store db.Store) (*Server, error) {
  24  	tokenMaker, err := token.NewPasetoMaker(config.TokenSymmetricKey)
  25  	if err != nil {
  26  		return nil, fmt.Errorf("cannot create token maker: %w", err)
  27  	}
  28  
  29  	server := &Server{
  30  		config:     config,
  31  		store:      store,
  32  		tokenMaker: tokenMaker,
  33  	}
  34  
  35  	if v, ok := binding.Validator.Engine().(*validator.Validate); ok {
  36  		v.RegisterValidation("currency", validCurrency)
  37  	}
  38  
  39  	server.setupRouter()
  40  	return server, nil
  41  }
  42  
  43  func (server *Server) setupRouter() {
  44  	router := gin.Default()
  45  
  46  	router.POST("/users", server.createUser)
  47  	router.POST("/users/login", server.loginUser)
  48  	router.POST("/tokens/renew_access", server.renewAccessToken)
  49  
  50  	authRoutes := router.Group("/").Use(authMiddleware(server.tokenMaker))
  51  	authRoutes.POST("/accounts", server.createAccount)
  52  	authRoutes.GET("/accounts/:id", server.getAccount)
  53  	authRoutes.GET("/accounts", server.listAccounts)
  54  
  55  	authRoutes.POST("/transfers", server.createTransfer)
  56  
  57  	server.router = router
  58  }
  59  
  60  // Start runs the HTTP server on a specific address.
  61  func (server *Server) Start(address string) error {
  62  	return server.router.Run(address)
  63  }
  64  
  65  func errorResponse(err error) gin.H {
  66  	return gin.H{"error": err.Error()}
  67  }
```

## Source: api/middleware.go

```go
   1  package api
   2  
   3  import (
   4  	"errors"
   5  	"fmt"
   6  	"net/http"
   7  	"strings"
   8  
   9  	"github.com/gin-gonic/gin"
  10  	"github.com/techschool/simplebank/token"
  11  )
  12  
  13  const (
  14  	authorizationHeaderKey  = "authorization"
  15  	authorizationTypeBearer = "bearer"
  16  	authorizationPayloadKey = "authorization_payload"
  17  )
  18  
  19  // AuthMiddleware creates a gin middleware for authorization
  20  func authMiddleware(tokenMaker token.Maker) gin.HandlerFunc {
  21  	return func(ctx *gin.Context) {
  22  		authorizationHeader := ctx.GetHeader(authorizationHeaderKey)
  23  
  24  		if len(authorizationHeader) == 0 {
  25  			err := errors.New("authorization header is not provided")
  26  			ctx.AbortWithStatusJSON(http.StatusUnauthorized, errorResponse(err))
  27  			return
  28  		}
  29  
  30  		fields := strings.Fields(authorizationHeader)
  31  		if len(fields) < 2 {
  32  			err := errors.New("invalid authorization header format")
  33  			ctx.AbortWithStatusJSON(http.StatusUnauthorized, errorResponse(err))
  34  			return
  35  		}
  36  
  37  		authorizationType := strings.ToLower(fields[0])
  38  		if authorizationType != authorizationTypeBearer {
  39  			err := fmt.Errorf("unsupported authorization type %s", authorizationType)
  40  			ctx.AbortWithStatusJSON(http.StatusUnauthorized, errorResponse(err))
  41  			return
  42  		}
  43  
  44  		accessToken := fields[1]
  45  		payload, err := tokenMaker.VerifyToken(accessToken, token.TokenTypeAccessToken)
  46  		if err != nil {
  47  			ctx.AbortWithStatusJSON(http.StatusUnauthorized, errorResponse(err))
  48  			return
  49  		}
  50  
  51  		ctx.Set(authorizationPayloadKey, payload)
  52  		ctx.Next()
  53  	}
  54  }
```

## Source: db/sqlc/store.go

```go
   1  package db
   2  
   3  import (
   4  	"context"
   5  
   6  	"github.com/jackc/pgx/v5/pgxpool"
   7  )
   8  
   9  // Store defines all functions to execute db queries and transactions
  10  type Store interface {
  11  	Querier
  12  	TransferTx(ctx context.Context, arg TransferTxParams) (TransferTxResult, error)
  13  	CreateUserTx(ctx context.Context, arg CreateUserTxParams) (CreateUserTxResult, error)
  14  	VerifyEmailTx(ctx context.Context, arg VerifyEmailTxParams) (VerifyEmailTxResult, error)
  15  }
  16  
  17  // SQLStore provides all functions to execute SQL queries and transactions
  18  type SQLStore struct {
  19  	connPool *pgxpool.Pool
  20  	*Queries
  21  }
  22  
  23  // NewStore creates a new store
  24  func NewStore(connPool *pgxpool.Pool) Store {
  25  	return &SQLStore{
  26  		connPool: connPool,
  27  		Queries:  New(connPool),
  28  	}
  29  }
```

## Source: db/sqlc/tx_transfer.go

```go
   1  package db
   2  
   3  import "context"
   4  
   5  // TransferTxParams contains the input parameters of the transfer transaction
   6  type TransferTxParams struct {
   7  	FromAccountID int64 `json:"from_account_id"`
   8  	ToAccountID   int64 `json:"to_account_id"`
   9  	Amount        int64 `json:"amount"`
  10  }
  11  
  12  // TransferTxResult is the result of the transfer transaction
  13  type TransferTxResult struct {
  14  	Transfer    Transfer `json:"transfer"`
  15  	FromAccount Account  `json:"from_account"`
  16  	ToAccount   Account  `json:"to_account"`
  17  	FromEntry   Entry    `json:"from_entry"`
  18  	ToEntry     Entry    `json:"to_entry"`
  19  }
  20  
  21  // TransferTx performs a money transfer from one account to the other.
  22  // It creates the transfer, add account entries, and update accounts' balance within a database transaction
  23  func (store *SQLStore) TransferTx(ctx context.Context, arg TransferTxParams) (TransferTxResult, error) {
  24  	var result TransferTxResult
  25  
  26  	err := store.execTx(ctx, func(q *Queries) error {
  27  		var err error
  28  
  29  		result.Transfer, err = q.CreateTransfer(ctx, CreateTransferParams{
  30  			FromAccountID: arg.FromAccountID,
  31  			ToAccountID:   arg.ToAccountID,
  32  			Amount:        arg.Amount,
  33  		})
  34  		if err != nil {
  35  			return err
  36  		}
  37  
  38  		result.FromEntry, err = q.CreateEntry(ctx, CreateEntryParams{
  39  			AccountID: arg.FromAccountID,
  40  			Amount:    -arg.Amount,
  41  		})
  42  		if err != nil {
  43  			return err
  44  		}
  45  
  46  		result.ToEntry, err = q.CreateEntry(ctx, CreateEntryParams{
  47  			AccountID: arg.ToAccountID,
  48  			Amount:    arg.Amount,
  49  		})
  50  		if err != nil {
  51  			return err
  52  		}
  53  
  54  		if arg.FromAccountID < arg.ToAccountID {
  55  			result.FromAccount, result.ToAccount, err = addMoney(ctx, q, arg.FromAccountID, -arg.Amount, arg.ToAccountID, arg.Amount)
  56  		} else {
  57  			result.ToAccount, result.FromAccount, err = addMoney(ctx, q, arg.ToAccountID, arg.Amount, arg.FromAccountID, -arg.Amount)
  58  		}
  59  
  60  		return err
  61  	})
  62  
  63  	return result, err
  64  }
  65  
  66  func addMoney(
  67  	ctx context.Context,
  68  	q *Queries,
  69  	accountID1 int64,
  70  	amount1 int64,
  71  	accountID2 int64,
  72  	amount2 int64,
  73  ) (account1 Account, account2 Account, err error) {
  74  	account1, err = q.AddAccountBalance(ctx, AddAccountBalanceParams{
  75  		ID:     accountID1,
  76  		Amount: amount1,
  77  	})
  78  	if err != nil {
  79  		return
  80  	}
  81  
  82  	account2, err = q.AddAccountBalance(ctx, AddAccountBalanceParams{
  83  		ID:     accountID2,
  84  		Amount: amount2,
  85  	})
  86  	return
  87  }
```

## Source: api/transfer_test.go

```go
   1  package api
   2  
   3  import (
   4  	"bytes"
   5  	"database/sql"
   6  	"encoding/json"
   7  	"net/http"
   8  	"net/http/httptest"
   9  	"testing"
  10  	"time"
  11  
  12  	"github.com/gin-gonic/gin"
  13  	"github.com/golang/mock/gomock"
  14  	"github.com/stretchr/testify/require"
  15  	mockdb "github.com/techschool/simplebank/db/mock"
  16  	db "github.com/techschool/simplebank/db/sqlc"
  17  	"github.com/techschool/simplebank/token"
  18  	"github.com/techschool/simplebank/util"
  19  )
  20  
  21  func TestTransferAPI(t *testing.T) {
  22  	amount := int64(10)
  23  
  24  	user1, _ := randomUser(t)
  25  	user2, _ := randomUser(t)
  26  	user3, _ := randomUser(t)
  27  
  28  	account1 := randomAccount(user1.Username)
  29  	account2 := randomAccount(user2.Username)
  30  	account3 := randomAccount(user3.Username)
  31  
  32  	account1.Currency = util.USD
  33  	account2.Currency = util.USD
  34  	account3.Currency = util.EUR
  35  
  36  	testCases := []struct {
  37  		name          string
  38  		body          gin.H
  39  		setupAuth     func(t *testing.T, request *http.Request, tokenMaker token.Maker)
  40  		buildStubs    func(store *mockdb.MockStore)
  41  		checkResponse func(recoder *httptest.ResponseRecorder)
  42  	}{
  43  		{
  44  			name: "OK",
  45  			body: gin.H{
  46  				"from_account_id": account1.ID,
  47  				"to_account_id":   account2.ID,
  48  				"amount":          amount,
  49  				"currency":        util.USD,
  50  			},
  51  			setupAuth: func(t *testing.T, request *http.Request, tokenMaker token.Maker) {
  52  				addAuthorization(t, request, tokenMaker, authorizationTypeBearer, user1.Username, user1.Role, time.Minute)
  53  			},
  54  			buildStubs: func(store *mockdb.MockStore) {
  55  				store.EXPECT().GetAccount(gomock.Any(), gomock.Eq(account1.ID)).Times(1).Return(account1, nil)
  56  				store.EXPECT().GetAccount(gomock.Any(), gomock.Eq(account2.ID)).Times(1).Return(account2, nil)
  57  
  58  				arg := db.TransferTxParams{
  59  					FromAccountID: account1.ID,
  60  					ToAccountID:   account2.ID,
  61  					Amount:        amount,
  62  				}
  63  				store.EXPECT().TransferTx(gomock.Any(), gomock.Eq(arg)).Times(1)
  64  			},
  65  			checkResponse: func(recorder *httptest.ResponseRecorder) {
  66  				require.Equal(t, http.StatusOK, recorder.Code)
  67  			},
  68  		},
  69  		{
  70  			name: "UnauthorizedUser",
  71  			body: gin.H{
  72  				"from_account_id": account1.ID,
  73  				"to_account_id":   account2.ID,
  74  				"amount":          amount,
  75  				"currency":        util.USD,
  76  			},
  77  			setupAuth: func(t *testing.T, request *http.Request, tokenMaker token.Maker) {
  78  				addAuthorization(t, request, tokenMaker, authorizationTypeBearer, user2.Username, user2.Role, time.Minute)
  79  			},
  80  			buildStubs: func(store *mockdb.MockStore) {
  81  				store.EXPECT().GetAccount(gomock.Any(), gomock.Eq(account1.ID)).Times(1).Return(account1, nil)
  82  				store.EXPECT().GetAccount(gomock.Any(), gomock.Eq(account2.ID)).Times(0)
  83  				store.EXPECT().TransferTx(gomock.Any(), gomock.Any()).Times(0)
  84  			},
  85  			checkResponse: func(recorder *httptest.ResponseRecorder) {
  86  				require.Equal(t, http.StatusUnauthorized, recorder.Code)
  87  			},
  88  		},
  89  		{
  90  			name: "NoAuthorization",
  91  			body: gin.H{
  92  				"from_account_id": account1.ID,
  93  				"to_account_id":   account2.ID,
  94  				"amount":          amount,
  95  				"currency":        util.USD,
  96  			},
  97  			setupAuth: func(t *testing.T, request *http.Request, tokenMaker token.Maker) {
  98  			},
  99  			buildStubs: func(store *mockdb.MockStore) {
 100  				store.EXPECT().GetAccount(gomock.Any(), gomock.Any()).Times(0)
 101  				store.EXPECT().TransferTx(gomock.Any(), gomock.Any()).Times(0)
 102  			},
 103  			checkResponse: func(recorder *httptest.ResponseRecorder) {
 104  				require.Equal(t, http.StatusUnauthorized, recorder.Code)
 105  			},
 106  		},
 107  		{
 108  			name: "FromAccountNotFound",
 109  			body: gin.H{
 110  				"from_account_id": account1.ID,
 111  				"to_account_id":   account2.ID,
 112  				"amount":          amount,
 113  				"currency":        util.USD,
 114  			},
 115  			setupAuth: func(t *testing.T, request *http.Request, tokenMaker token.Maker) {
 116  				addAuthorization(t, request, tokenMaker, authorizationTypeBearer, user1.Username, user1.Role, time.Minute)
 117  			},
 118  			buildStubs: func(store *mockdb.MockStore) {
 119  				store.EXPECT().GetAccount(gomock.Any(), gomock.Eq(account1.ID)).Times(1).Return(db.Account{}, db.ErrRecordNotFound)
 120  				store.EXPECT().GetAccount(gomock.Any(), gomock.Eq(account2.ID)).Times(0)
 121  				store.EXPECT().TransferTx(gomock.Any(), gomock.Any()).Times(0)
 122  			},
 123  			checkResponse: func(recorder *httptest.ResponseRecorder) {
 124  				require.Equal(t, http.StatusNotFound, recorder.Code)
 125  			},
 126  		},
 127  		{
 128  			name: "ToAccountNotFound",
 129  			body: gin.H{
 130  				"from_account_id": account1.ID,
 131  				"to_account_id":   account2.ID,
 132  				"amount":          amount,
 133  				"currency":        util.USD,
 134  			},
 135  			setupAuth: func(t *testing.T, request *http.Request, tokenMaker token.Maker) {
 136  				addAuthorization(t, request, tokenMaker, authorizationTypeBearer, user1.Username, user1.Role, time.Minute)
 137  			},
 138  			buildStubs: func(store *mockdb.MockStore) {
 139  				store.EXPECT().GetAccount(gomock.Any(), gomock.Eq(account1.ID)).Times(1).Return(account1, nil)
 140  				store.EXPECT().GetAccount(gomock.Any(), gomock.Eq(account2.ID)).Times(1).Return(db.Account{}, db.ErrRecordNotFound)
 141  				store.EXPECT().TransferTx(gomock.Any(), gomock.Any()).Times(0)
 142  			},
 143  			checkResponse: func(recorder *httptest.ResponseRecorder) {
 144  				require.Equal(t, http.StatusNotFound, recorder.Code)
 145  			},
 146  		},
 147  		{
 148  			name: "FromAccountCurrencyMismatch",
 149  			body: gin.H{
 150  				"from_account_id": account3.ID,
 151  				"to_account_id":   account2.ID,
 152  				"amount":          amount,
 153  				"currency":        util.USD,
 154  			},
 155  			setupAuth: func(t *testing.T, request *http.Request, tokenMaker token.Maker) {
 156  				addAuthorization(t, request, tokenMaker, authorizationTypeBearer, user3.Username, user3.Role, time.Minute)
 157  			},
 158  			buildStubs: func(store *mockdb.MockStore) {
 159  				store.EXPECT().GetAccount(gomock.Any(), gomock.Eq(account3.ID)).Times(1).Return(account3, nil)
 160  				store.EXPECT().GetAccount(gomock.Any(), gomock.Eq(account2.ID)).Times(0)
 161  				store.EXPECT().TransferTx(gomock.Any(), gomock.Any()).Times(0)
 162  			},
 163  			checkResponse: func(recorder *httptest.ResponseRecorder) {
 164  				require.Equal(t, http.StatusBadRequest, recorder.Code)
 165  			},
 166  		},
 167  		{
 168  			name: "ToAccountCurrencyMismatch",
 169  			body: gin.H{
 170  				"from_account_id": account1.ID,
 171  				"to_account_id":   account3.ID,
 172  				"amount":          amount,
 173  				"currency":        util.USD,
 174  			},
 175  			setupAuth: func(t *testing.T, request *http.Request, tokenMaker token.Maker) {
 176  				addAuthorization(t, request, tokenMaker, authorizationTypeBearer, user1.Username, user1.Role, time.Minute)
 177  			},
 178  			buildStubs: func(store *mockdb.MockStore) {
 179  				store.EXPECT().GetAccount(gomock.Any(), gomock.Eq(account1.ID)).Times(1).Return(account1, nil)
 180  				store.EXPECT().GetAccount(gomock.Any(), gomock.Eq(account3.ID)).Times(1).Return(account3, nil)
 181  				store.EXPECT().TransferTx(gomock.Any(), gomock.Any()).Times(0)
 182  			},
 183  			checkResponse: func(recorder *httptest.ResponseRecorder) {
 184  				require.Equal(t, http.StatusBadRequest, recorder.Code)
 185  			},
 186  		},
 187  		{
 188  			name: "InvalidCurrency",
 189  			body: gin.H{
 190  				"from_account_id": account1.ID,
 191  				"to_account_id":   account2.ID,
 192  				"amount":          amount,
 193  				"currency":        "XYZ",
 194  			},
 195  			setupAuth: func(t *testing.T, request *http.Request, tokenMaker token.Maker) {
 196  				addAuthorization(t, request, tokenMaker, authorizationTypeBearer, user1.Username, user1.Role, time.Minute)
 197  			},
 198  			buildStubs: func(store *mockdb.MockStore) {
 199  				store.EXPECT().GetAccount(gomock.Any(), gomock.Any()).Times(0)
 200  				store.EXPECT().TransferTx(gomock.Any(), gomock.Any()).Times(0)
 201  			},
 202  			checkResponse: func(recorder *httptest.ResponseRecorder) {
 203  				require.Equal(t, http.StatusBadRequest, recorder.Code)
 204  			},
 205  		},
 206  		{
 207  			name: "NegativeAmount",
 208  			body: gin.H{
 209  				"from_account_id": account1.ID,
 210  				"to_account_id":   account2.ID,
 211  				"amount":          -amount,
 212  				"currency":        util.USD,
 213  			},
 214  			setupAuth: func(t *testing.T, request *http.Request, tokenMaker token.Maker) {
 215  				addAuthorization(t, request, tokenMaker, authorizationTypeBearer, user1.Username, user1.Role, time.Minute)
 216  			},
 217  			buildStubs: func(store *mockdb.MockStore) {
 218  				store.EXPECT().GetAccount(gomock.Any(), gomock.Any()).Times(0)
 219  				store.EXPECT().TransferTx(gomock.Any(), gomock.Any()).Times(0)
 220  			},
 221  			checkResponse: func(recorder *httptest.ResponseRecorder) {
 222  				require.Equal(t, http.StatusBadRequest, recorder.Code)
 223  			},
 224  		},
 225  		{
 226  			name: "InsufficientBalance",
 227  			body: gin.H{
 228  				"from_account_id": account1.ID,
 229  				"to_account_id":   account2.ID,
 230  				"amount":          amount,
 231  				"currency":        util.USD,
 232  			},
 233  			setupAuth: func(t *testing.T, request *http.Request, tokenMaker token.Maker) {
 234  				addAuthorization(t, request, tokenMaker, authorizationTypeBearer, user1.Username, user1.Role, time.Minute)
 235  			},
 236  			buildStubs: func(store *mockdb.MockStore) {
 237  				insufficientAccount := account1
 238  				insufficientAccount.Balance = amount - 1
 239  
 240  				store.EXPECT().GetAccount(gomock.Any(), gomock.Eq(account1.ID)).Times(1).Return(insufficientAccount, nil)
 241  				store.EXPECT().GetAccount(gomock.Any(), gomock.Eq(account2.ID)).Times(1).Return(account2, nil)
 242  				store.EXPECT().TransferTx(gomock.Any(), gomock.Any()).Times(0)
 243  			},
 244  			checkResponse: func(recorder *httptest.ResponseRecorder) {
 245  				require.Equal(t, http.StatusBadRequest, recorder.Code)
 246  			},
 247  		},
 248  		{
 249  			name: "GetAccountError",
 250  			body: gin.H{
 251  				"from_account_id": account1.ID,
 252  				"to_account_id":   account2.ID,
 253  				"amount":          amount,
 254  				"currency":        util.USD,
 255  			},
 256  			setupAuth: func(t *testing.T, request *http.Request, tokenMaker token.Maker) {
 257  				addAuthorization(t, request, tokenMaker, authorizationTypeBearer, user1.Username, user1.Role, time.Minute)
 258  			},
 259  			buildStubs: func(store *mockdb.MockStore) {
 260  				store.EXPECT().GetAccount(gomock.Any(), gomock.Any()).Times(1).Return(db.Account{}, sql.ErrConnDone)
 261  				store.EXPECT().TransferTx(gomock.Any(), gomock.Any()).Times(0)
 262  			},
 263  			checkResponse: func(recorder *httptest.ResponseRecorder) {
 264  				require.Equal(t, http.StatusInternalServerError, recorder.Code)
 265  			},
 266  		},
 267  		{
 268  			name: "TransferTxError",
 269  			body: gin.H{
 270  				"from_account_id": account1.ID,
 271  				"to_account_id":   account2.ID,
 272  				"amount":          amount,
 273  				"currency":        util.USD,
 274  			},
 275  			setupAuth: func(t *testing.T, request *http.Request, tokenMaker token.Maker) {
 276  				addAuthorization(t, request, tokenMaker, authorizationTypeBearer, user1.Username, user1.Role, time.Minute)
 277  			},
 278  			buildStubs: func(store *mockdb.MockStore) {
 279  				store.EXPECT().GetAccount(gomock.Any(), gomock.Eq(account1.ID)).Times(1).Return(account1, nil)
 280  				store.EXPECT().GetAccount(gomock.Any(), gomock.Eq(account2.ID)).Times(1).Return(account2, nil)
 281  				store.EXPECT().TransferTx(gomock.Any(), gomock.Any()).Times(1).Return(db.TransferTxResult{}, sql.ErrTxDone)
 282  			},
 283  			checkResponse: func(recorder *httptest.ResponseRecorder) {
 284  				require.Equal(t, http.StatusInternalServerError, recorder.Code)
 285  			},
 286  		},
 287  	}
 288  
 289  	for i := range testCases {
 290  		tc := testCases[i]
 291  
 292  		t.Run(tc.name, func(t *testing.T) {
 293  			ctrl := gomock.NewController(t)
 294  			defer ctrl.Finish()
 295  
 296  			store := mockdb.NewMockStore(ctrl)
 297  			tc.buildStubs(store)
 298  
 299  			server := newTestServer(t, store)
 300  			recorder := httptest.NewRecorder()
 301  
 302  			// Marshal body data to JSON
 303  			data, err := json.Marshal(tc.body)
 304  			require.NoError(t, err)
 305  
 306  			url := "/transfers"
 307  			request, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(data))
 308  			require.NoError(t, err)
 309  
 310  			tc.setupAuth(t, request, server.tokenMaker)
 311  			server.router.ServeHTTP(recorder, request)
 312  			tc.checkResponse(recorder)
 313  		})
 314  	}
 315  }
```
