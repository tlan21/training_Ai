package pg

import (
	"context"
	"errors"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// CMSAlertsRepo — INT-64 (migration 010): the bell "seen" snapshot + videos that still need a category.
type CMSAlertsRepo struct{ DB *pgxpool.Pool }

// Seen returns the last snapshot; an account that never opened the bell has seen nothing (0, 0, nil).
func (r *CMSAlertsRepo) Seen(ctx context.Context, userID string) (int, int, *time.Time, error) {
	var failed, uncategorized int
	var at time.Time
	err := r.DB.QueryRow(ctx, `SELECT failed_jobs,uncategorized_videos,seen_at FROM cms_alert_seen WHERE user_id=$1`, userID).Scan(&failed, &uncategorized, &at)
	if errors.Is(err, pgx.ErrNoRows) {
		return 0, 0, nil, nil
	}
	if err != nil {
		return 0, 0, nil, err
	}
	return failed, uncategorized, &at, nil
}

func (r *CMSAlertsRepo) MarkSeen(ctx context.Context, userID string, failed, uncategorized int) error {
	_, err := r.DB.Exec(ctx, `INSERT INTO cms_alert_seen(user_id,failed_jobs,uncategorized_videos) VALUES($1,$2,$3)
		ON CONFLICT (user_id) DO UPDATE SET failed_jobs=excluded.failed_jobs,uncategorized_videos=excluded.uncategorized_videos,seen_at=now()`,
		userID, failed, uncategorized)
	return err
}

// UncategorizedProcessed lists processed, non-deleted videos without a category (oldest first).
func (r *CMSAlertsRepo) UncategorizedProcessed(ctx context.Context) ([]string, error) {
	rows, err := r.DB.Query(ctx, `SELECT id FROM videos WHERE status='processed' AND deleted_at IS NULL AND category_id IS NULL ORDER BY created_at,id`)
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
