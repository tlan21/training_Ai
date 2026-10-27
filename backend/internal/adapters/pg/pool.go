package pg

import (
	"context"
	"github.com/jackc/pgx/v5/pgxpool"
	"traning_ai/backend/internal/startup"
)

func New(ctx context.Context, dsn string) (*pgxpool.Pool, error) {
	db, err := pgxpool.New(ctx, dsn)
	if err != nil {
		return nil, err
	}
	if err := startup.Wait(ctx, "PostgreSQL", db.Ping); err != nil {
		db.Close()
		return nil, err
	}
	return db, nil
}
