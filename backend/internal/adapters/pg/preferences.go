package pg

import (
	"context"
	"errors"

	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
	"traning_ai/backend/internal/domain"
)

type PreferenceRepo struct{ DB *pgxpool.Pool }

func (r *PreferenceRepo) Get(ctx context.Context, userID string) ([]string, error) {
	rows, err := r.DB.Query(ctx, `SELECT category_id FROM user_preferences WHERE user_id=$1 ORDER BY category_id`, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	ids := []string{}
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			return nil, err
		}
		ids = append(ids, id)
	}
	return ids, rows.Err()
}

func (r *PreferenceRepo) Replace(ctx context.Context, userID string, categoryIDs []string) error {
	tx, err := r.DB.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)
	var id string
	if err := tx.QueryRow(ctx, `SELECT id FROM users WHERE id=$1 FOR UPDATE`, userID).Scan(&id); err != nil {
		return notFound(err, domain.ErrUserNotFound)
	}
	if _, err := tx.Exec(ctx, `DELETE FROM user_preferences WHERE user_id=$1`, userID); err != nil {
		return err
	}
	if _, err := tx.Exec(ctx, `INSERT INTO user_preferences(user_id,category_id) SELECT $1::varchar,unnest($2::varchar[])`, userID, categoryIDs); err != nil {
		var pgerr *pgconn.PgError
		if errors.As(err, &pgerr) && (pgerr.Code == "23503" || pgerr.Code == "23505") {
			return domain.ErrValidation
		}
		return err
	}
	return tx.Commit(ctx)
}
