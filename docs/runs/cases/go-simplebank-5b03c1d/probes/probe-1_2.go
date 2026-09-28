package api

import (
	"context"
	"fmt"
	"testing"
	"time"

	pgx "github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	
	db "github.com/techschool/simplebank/db/sqlc"
	"github.com/stretchr/testify/require"
)

// fakeRow implements pgx.Row to provide deterministic Scan behavior for sqlc GetAccount.
type fakeRow struct {
	id        int64
	owner     string
	balance   int64
	currency  string
	createdAt time.Time
	err       error
}

func (r *fakeRow) Scan(dest ...any) error {
	if len(dest) != 5 {
		return fmt.Errorf("unexpected number of dests: %d", len(dest))
	}
	p0, ok := dest[0].(*int64)
	if !ok {
		return fmt.Errorf("dest[0] not *int64")
	}
	p1, ok := dest[1].(*string)
	if !ok {
		return fmt.Errorf("dest[1] not *string")
	}
	p2, ok := dest[2].(*int64)
	if !ok {
		return fmt.Errorf("dest[2] not *int64")
	}
	p3, ok := dest[3].(*string)
	if !ok {
		return fmt.Errorf("dest[3] not *string")
	}
	p4, ok := dest[4].(*time.Time)
	if !ok {
		return fmt.Errorf("dest[4] not *time.Time")
	}
	*p0 = r.id
	*p1 = r.owner
	*p2 = r.balance
	*p3 = r.currency
	*p4 = r.createdAt
	return r.err
}

// fakeDB implements db.DBTX minimally for Queries.GetAccount; only QueryRow is used.
type fakeDB struct {
	owner     string
	balance   int64
	currency  string
	createdAt time.Time
}

// Ensure fakeDB satisfies the interface expected by sqlc-generated Queries.
var _ db.DBTX = (*fakeDB)(nil)

func (f *fakeDB) QueryRow(ctx context.Context, sql string, args ...any) pgx.Row {
	var id int64
	if len(args) > 0 {
		switch v := args[0].(type) {
		case int64:
			id = v
		case int32:
			id = int64(v)
		case uint64:
			id = int64(v)
		}
	}
	return &fakeRow{
		id:        id,
		owner:     f.owner,
		balance:   f.balance,
		currency:  f.currency,
		createdAt: f.createdAt,
	}
}

func (f *fakeDB) Exec(ctx context.Context, sql string, args ...any) (pgconn.CommandTag, error) {
	return pgconn.CommandTag{}, fmt.Errorf("Exec not used in probe")
}

func (f *fakeDB) Query(ctx context.Context, sql string, args ...any) (pgx.Rows, error) {
	return nil, fmt.Errorf("Query not used in probe")
}

func TestDiffgenomeProbeQueriesGetAccountExecutes(t *testing.T) {
	// Deterministic fixture values
	id := int64(12345)
	owner := "alice"
	balance := int64(100)
	currency := "USD"
	createdAt := time.Unix(1_700_000_000, 0).UTC()

	// Substitute external DB with a hand-written pgx DBTX fake that drives real sqlc code.
	fdb := &fakeDB{owner: owner, balance: balance, currency: currency, createdAt: createdAt}
	q := db.New(fdb)

	acct, err := q.GetAccount(context.Background(), id)
	require.NoError(t, err)
	// Verify the returned Account matches our fake row and that the id flowed through args.
	require.Equal(t, id, acct.ID)
	require.Equal(t, owner, acct.Owner)
	require.Equal(t, balance, acct.Balance)
	require.Equal(t, currency, acct.Currency)
	require.WithinDuration(t, createdAt, acct.CreatedAt, time.Microsecond)
}
