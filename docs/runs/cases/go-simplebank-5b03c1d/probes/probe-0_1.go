package api

import (
	"context"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/stretchr/testify/require"
	db "github.com/techschool/simplebank/db/sqlc"
)

// fakeDBTX implements the sqlc DBTX interface (pgx) with in-memory behavior.
// It returns deterministic rows for the specific queries used by TransferTx.
type fakeDBTX struct {
	mu              sync.Mutex
	accounts        map[int64]db.Account
	nextTransferID  int64
	nextEntryID     int64
}

func newFakeDBTX() *fakeDBTX {
	fixed := time.Unix(0, 0).UTC()
	return &fakeDBTX{
		accounts: map[int64]db.Account{
			1: {ID: 1, Owner: "alice", Balance: 100, Currency: "USD", CreatedAt: fixed},
			2: {ID: 2, Owner: "bob", Balance: 100, Currency: "USD", CreatedAt: fixed},
		},
		nextTransferID: 1,
		nextEntryID:    1,
	}
}

// Exec is unused by the targeted code paths; keep as stub.
func (f *fakeDBTX) Exec(ctx context.Context, sql string, args ...any) (pgconn.CommandTag, error) {
	return pgconn.CommandTag{}, nil
}

// Query is unused by the targeted code paths; keep as stub.
func (f *fakeDBTX) Query(ctx context.Context, sql string, args ...any) (pgx.Rows, error) {
	return nil, nil
}

// QueryRow returns a fake row for the INSERT/UPDATE ... RETURNING statements used by:
// - CreateTransfer
// - CreateEntry
// - AddAccountBalance
func (f *fakeDBTX) QueryRow(ctx context.Context, sql string, args ...any) pgx.Row {
	f.mu.Lock()
	defer f.mu.Unlock()

	fixed := time.Unix(0, 0).UTC()

	s := strings.ToLower(sql)
	switch {
	case strings.Contains(s, "insert into transfers"):
		// args: from_account_id int64, to_account_id int64, amount int64
		id := f.nextTransferID
		f.nextTransferID++
		fromID := args[0].(int64)
		toID := args[1].(int64)
		amount := args[2].(int64)
		return fakeRow(func(dest ...any) error {
			*(dest[0].(*int64)) = id
			*(dest[1].(*int64)) = fromID
			*(dest[2].(*int64)) = toID
			*(dest[3].(*int64)) = amount
			*(dest[4].(*time.Time)) = fixed
			return nil
		})

	case strings.Contains(s, "insert into entries"):
		// args: account_id int64, amount int64
		id := f.nextEntryID
		f.nextEntryID++
		accountID := args[0].(int64)
		amount := args[1].(int64)
		return fakeRow(func(dest ...any) error {
			*(dest[0].(*int64)) = id
			*(dest[1].(*int64)) = accountID
			*(dest[2].(*int64)) = amount
			*(dest[3].(*time.Time)) = fixed
			return nil
		})

	case strings.Contains(s, "update accounts set balance") && strings.Contains(s, "returning"):
		// args: id int64, amount int64 (sqlc generated order typically: id, amount)
		id := args[0].(int64)
		amount := args[1].(int64)
		a := f.accounts[id]
		a.Balance = a.Balance + amount
		f.accounts[id] = a
		return fakeRow(func(dest ...any) error {
			// RETURNING full account row: id, owner, balance, currency, created_at
			*(dest[0].(*int64)) = a.ID
			*(dest[1].(*string)) = a.Owner
			*(dest[2].(*int64)) = a.Balance
			*(dest[3].(*string)) = a.Currency
			*(dest[4].(*time.Time)) = a.CreatedAt
			return nil
		})
	}

	// Default: return a row that errors if scanned (should not happen in this probe)
	return fakeRow(func(dest ...any) error { return nil })
}

// fakeRow is a minimal pgx.Row that fulfills Scan by invoking a closure.
type fakeRow func(dest ...any) error

func (r fakeRow) Scan(dest ...any) error { return r(dest...) }

func TestDiffgenomeProbe_TransferTx_ExecutesReal(t *testing.T) {
	// Arrange: a real SQLStore with Queries bound to our fake in-memory DBTX.
	fdb := newFakeDBTX()
	store := &db.SQLStore{Queries: db.New(fdb)}

	ctx := context.Background()
	arg := db.TransferTxParams{FromAccountID: 1, ToAccountID: 2, Amount: 10}

	// Act: execute the real TransferTx. Our execTx path should drive real sqlc queries
	// against the fake DBTX without any external dependencies.
	res, err := store.TransferTx(ctx, arg)

	// Assert: no error and expected side effects/responses.
	require.NoError(t, err)

	require.Equal(t, arg.FromAccountID, res.Transfer.FromAccountID)
	require.Equal(t, arg.ToAccountID, res.Transfer.ToAccountID)
	require.Equal(t, arg.Amount, res.Transfer.Amount)

	require.Equal(t, arg.FromAccountID, res.FromEntry.AccountID)
	require.Equal(t, -arg.Amount, res.FromEntry.Amount)
	require.Equal(t, arg.ToAccountID, res.ToEntry.AccountID)
	require.Equal(t, arg.Amount, res.ToEntry.Amount)

	require.Equal(t, int64(1), res.FromAccount.ID)
	require.Equal(t, int64(2), res.ToAccount.ID)
	require.Equal(t, int64(90), res.FromAccount.Balance)
	require.Equal(t, int64(110), res.ToAccount.Balance)
}
