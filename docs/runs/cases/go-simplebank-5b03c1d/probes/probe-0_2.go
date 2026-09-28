package api

import (
	"context"
	"errors"
	"io"
	"reflect"
	"testing"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/stretchr/testify/require"
	db "github.com/techschool/simplebank/db/sqlc"
)

// fakeDBTX implements db.DBTX (sqlc's DB interface) to drive real Queries code
// without contacting any database. It returns deterministic rows in sequence
// matching the calls performed by TransferTx.
type fakeDBTX struct {
	rows []fakeRow
	idx  int
}

type fakeRow struct {
	vals []any
	err  error
}

type fRow struct{ data fakeRow }

func (r *fRow) Scan(dest ...any) error {
	if r.data.err != nil {
		return r.data.err
	}
	if len(dest) != len(r.data.vals) {
		return errors.New("scan dest/vals length mismatch")
	}
	for i := range dest {
		vd := reflect.ValueOf(dest[i])
		if vd.Kind() != reflect.Ptr || vd.IsNil() {
			return errors.New("dest must be non-nil pointer")
		}
		vv := reflect.ValueOf(r.data.vals[i])
		if !vv.Type().AssignableTo(vd.Elem().Type()) {
			return errors.New("type mismatch in scan")
		}
		vd.Elem().Set(vv)
	}
	return nil
}

// Unused in this probe, keep minimal stubs.
func (f *fakeDBTX) Exec(ctx context.Context, sql string, args ...any) (pgconn.CommandTag, error) {
	var tag pgconn.CommandTag
	return tag, nil
}

func (f *fakeDBTX) Query(ctx context.Context, sql string, args ...any) (pgx.Rows, error) {
	return &emptyRows{}, nil
}

func (f *fakeDBTX) QueryRow(ctx context.Context, sql string, args ...any) pgx.Row {
	if f.idx >= len(f.rows) {
		return &fRow{data: fakeRow{err: errors.New("no more rows queued")}}
	}
	r := &fRow{data: f.rows[f.idx]}
	f.idx++
	return r
}

type emptyRows struct{}

func (e *emptyRows) Close()                                 {}
func (e *emptyRows) Err() error                             { return nil }
func (e *emptyRows) Next() bool                             { return false }
func (e *emptyRows) Scan(dest ...any) error                 { return io.EOF }
func (e *emptyRows) Values() ([]any, error)                 { return nil, io.EOF }
func (e *emptyRows) RawValues() [][]byte                    { return nil }
func (e *emptyRows) FieldDescriptions() []pgconn.FieldDescription { return nil }
func (e *emptyRows) Conn() *pgx.Conn                        { return nil }

func TestDiffgenomeProbe_TransferTx_RealSQLStoreWithFakeDBTX(t *testing.T) {
	// Deterministic timestamps and IDs
	now := time.Unix(1234567890, 0)
	fromID := int64(1)
	toID := int64(2)
	amount := int64(10)

	// Prepare the exact sequence of single-row results returned by sqlc Queries:
	// 1) CreateTransfer -> transfers row
	// 2) CreateEntry (from) -> entries row
	// 3) CreateEntry (to) -> entries row
	// 4) AddAccountBalance (from) -> accounts row (after -amount)
	// 5) AddAccountBalance (to) -> accounts row (after +amount)
	fdb := &fakeDBTX{rows: []fakeRow{
		{vals: []any{int64(101), fromID, toID, amount, now}},          // transfers
		{vals: []any{int64(201), fromID, -amount, now}},               // entries (from)
		{vals: []any{int64(202), toID, amount, now}},                  // entries (to)
		{vals: []any{fromID, "alice", int64(90), "USD", now}},      // accounts (from updated)
		{vals: []any{toID, "bob", int64(60), "USD", now}},          // accounts (to updated)
	}}

	// Build real sqlc Queries on top of our fake DBTX, then real SQLStore using them.
	q := db.New(fdb)
	store := &db.SQLStore{Queries: q}

	// Invoke the real TransferTx. Under our assumption (as exercised here), execTx
	// will drive the provided *Queries without requiring a real database.
	res, err := store.TransferTx(context.Background(), db.TransferTxParams{
		FromAccountID: fromID,
		ToAccountID:   toID,
		Amount:        amount,
	})
	require.NoError(t, err)

	// Validate the composed result reflects our fake rows, proving inner calls ran.
	require.Equal(t, int64(101), res.Transfer.ID)
	require.Equal(t, fromID, res.Transfer.FromAccountID)
	require.Equal(t, toID, res.Transfer.ToAccountID)
	require.Equal(t, amount, res.Transfer.Amount)

	require.Equal(t, int64(201), res.FromEntry.ID)
	require.Equal(t, fromID, res.FromEntry.AccountID)
	require.Equal(t, -amount, res.FromEntry.Amount)

	require.Equal(t, int64(202), res.ToEntry.ID)
	require.Equal(t, toID, res.ToEntry.AccountID)
	require.Equal(t, amount, res.ToEntry.Amount)

	require.Equal(t, fromID, res.FromAccount.ID)
	require.Equal(t, int64(90), res.FromAccount.Balance)
	require.Equal(t, toID, res.ToAccount.ID)
	require.Equal(t, int64(60), res.ToAccount.Balance)

	// Ensure all planned query rows were consumed (i.e., all inner calls executed).
	require.Equal(t, 5, fdb.idx)
}
