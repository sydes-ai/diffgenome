package api

import (
	"context"
	"fmt"
	"io"
	"testing"
	"time"

	"github.com/jackc/pgconn"
	"github.com/jackc/pgx/v5"
	"github.com/stretchr/testify/require"
	db "github.com/techschool/simplebank/db/sqlc"
)

// fakeRow implements pgx.Row and returns a single deterministic account row on Scan.
type fakeRow struct {
	id        int64
	owner     string
	balance   int64
	currency  string
	createdAt time.Time
}

func (r *fakeRow) Scan(dest ...any) error {
	if len(dest) != 5 {
		return fmt.Errorf("unexpected number of scan destinations: %d", len(dest))
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

// fakeRows is a stub for pgx.Rows; it's never iterated in this probe but must satisfy the interface.
type fakeRows struct{}

func (*fakeRows) Close()                                  {}
func (*fakeRows) Err() error                              { return nil }
func (*fakeRows) CommandTag() pgconn.CommandTag           { return pgconn.CommandTag{} }
func (*fakeRows) FieldDescriptions() []pgconn.FieldDescription { return nil }
func (*fakeRows) Next() bool                              { return false }
func (*fakeRows) Scan(dest ...any) error                  { return io.EOF }
func (*fakeRows) Values() ([]any, error)                  { return nil, io.EOF }
func (*fakeRows) RawValues() [][]byte                     { return nil }

// fakeDB implements db.DBTX, returning our fakeRow from QueryRow. Other methods are stubbed.
type fakeDB struct{ row pgx.Row }

func (f *fakeDB) Exec(ctx context.Context, sql string, args ...any) (pgconn.CommandTag, error) {
	return pgconn.CommandTag{}, nil
}

func (f *fakeDB) Query(ctx context.Context, sql string, args ...any) (pgx.Rows, error) {
	return &fakeRows{}, nil
}

func (f *fakeDB) QueryRow(ctx context.Context, sql string, args ...any) pgx.Row {
	return f.row
}

func TestDiffgenomeProbeGetAccountDirect(t *testing.T) {
	ctx := context.Background()

	// Deterministic account values to be returned by the fake DB row.
	want := db.Account{
		ID:        42,
		Owner:     "alice",
		Balance:   1000,
		Currency:  "USD",
		CreatedAt: time.Unix(1_600_000_000, 0),
	}

	// Inject a fake DBTX into the real sqlc Queries so GetAccount executes for real.
	q := db.New(&fakeDB{row: &fakeRow{
		id:        want.ID,
		owner:     want.Owner,
		balance:   want.Balance,
		currency:  want.Currency,
		createdAt: want.CreatedAt,
	}})

	got, err := q.GetAccount(ctx, want.ID)
	require.NoError(t, err)
	require.Equal(t, want.ID, got.ID)
	require.Equal(t, want.Owner, got.Owner)
	require.Equal(t, want.Balance, got.Balance)
	require.Equal(t, want.Currency, got.Currency)
	require.True(t, got.CreatedAt.Equal(want.CreatedAt))
}
