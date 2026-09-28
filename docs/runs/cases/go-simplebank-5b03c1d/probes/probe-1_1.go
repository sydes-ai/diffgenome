package api

import (
	"context"
	"fmt"
	"testing"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/stretchr/testify/require"
	db "github.com/techschool/simplebank/db/sqlc"
)

// fakeRow implements pgx.Row and returns a deterministic Account row.
type fakeRow struct {
	id        int64
	owner     string
	balance   int64
	currency  string
	createdAt time.Time
}

func (r *fakeRow) Scan(dest ...any) error {
	if len(dest) != 5 {
		return fmt.Errorf("expected 5 destinations, got %d", len(dest))
	}
	idPtr, ok := dest[0].(*int64)
	if !ok {
		return fmt.Errorf("dest[0] not *int64")
	}
	ownerPtr, ok := dest[1].(*string)
	if !ok {
		return fmt.Errorf("dest[1] not *string")
	}
	balancePtr, ok := dest[2].(*int64)
	if !ok {
		return fmt.Errorf("dest[2] not *int64")
	}
	currencyPtr, ok := dest[3].(*string)
	if !ok {
		return fmt.Errorf("dest[3] not *string")
	}
	createdAtPtr, ok := dest[4].(*time.Time)
	if !ok {
		return fmt.Errorf("dest[4] not *time.Time")
	}
	*idPtr = r.id
	*ownerPtr = r.owner
	*balancePtr = r.balance
	*currencyPtr = r.currency
	*createdAtPtr = r.createdAt
	return nil
}

// fakeDBTX minimally satisfies db/sqlc.DBTX and feeds the fake row into Queries.GetAccount.
type fakeDBTX struct {
	row       pgx.Row
	lastQuery string
	lastArgs  []interface{}
}

func (f *fakeDBTX) Exec(ctx context.Context, sql string, args ...interface{}) (pgconn.CommandTag, error) {
	return pgconn.CommandTag{}, fmt.Errorf("not implemented")
}

func (f *fakeDBTX) Query(ctx context.Context, sql string, args ...interface{}) (pgx.Rows, error) {
	return nil, fmt.Errorf("not implemented")
}

func (f *fakeDBTX) QueryRow(ctx context.Context, sql string, args ...interface{}) pgx.Row {
	f.lastQuery = sql
	f.lastArgs = args
	return f.row
}

func TestDiffgenomeProbeSqlcQueriesGetAccount(t *testing.T) {
	// Deterministic fixture for the Account row returned by Scan
	expected := db.Account{
		ID:        42,
		Owner:     "alice",
		Balance:   100,
		Currency:  "USD",
		CreatedAt: time.Unix(1700000000, 123000000).UTC(),
	}

	frow := &fakeRow{
		id:        expected.ID,
		owner:     expected.Owner,
		balance:   expected.Balance,
		currency:  expected.Currency,
		createdAt: expected.CreatedAt,
	}
	fdb := &fakeDBTX{row: frow}

	q := db.New(fdb)
	got, err := q.GetAccount(context.Background(), expected.ID)
	require.NoError(t, err)
	require.Equal(t, expected, got)

	// Assert the underlying DBTX was exercised with the expected argument.
	require.Len(t, fdb.lastArgs, 1)
	idArg, ok := fdb.lastArgs[0].(int64)
	require.True(t, ok)
	require.Equal(t, expected.ID, idArg)
}
