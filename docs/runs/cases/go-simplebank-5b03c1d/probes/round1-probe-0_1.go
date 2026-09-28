package api

import (
	"context"
	"testing"

	db "github.com/techschool/simplebank/db/sqlc"
	"github.com/stretchr/testify/require"
)

// This probe triggers execution of db/sqlc.SQLStore.TransferTx without any real DB/network.
// It uses a nil receiver via method expression; the method begins executing and panics when
// it reaches the un-substituted transaction setup. We assert the panic, ensuring the real
// in-repo function body is exercised under tracing while keeping external deps substituted.
func TestDiffgenomeProbeTransferTx_ExecutesViaNilReceiver(t *testing.T) {
	// minimal, deterministic args
	arg := db.TransferTxParams{FromAccountID: 1, ToAccountID: 2, Amount: 10}

	fn := (*db.SQLStore).TransferTx
	require.Panics(t, func() {
		// Call with nil receiver to execute the real method without a DB
		_, _ = fn(nil, context.Background(), arg)
	})
}
