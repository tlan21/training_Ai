package pg

import (
	"context"
	"os"
	"testing"
	"time"

	"github.com/jackc/pgx/v5"
)

func TestStartupWaitsForDelayedPostgres(t *testing.T) {
	dsn := os.Getenv("STARTUP_POSTGRES_DSN")
	if dsn == "" {
		t.Skip("set STARTUP_POSTGRES_DSN against the isolated delayed-start fixture")
	}
	probe, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
	conn, err := pgx.Connect(probe, dsn)
	cancel()
	if err == nil {
		_ = conn.Close(context.Background())
		t.Fatal("fixture was already ready; delayed-start path not exercised")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 40*time.Second)
	defer cancel()
	db, err := New(ctx, dsn)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	if err := db.Ping(ctx); err != nil {
		t.Fatal(err)
	}
	t.Log("initial PostgreSQL connection failed; bounded startup recovered against real PostgreSQL")
}
