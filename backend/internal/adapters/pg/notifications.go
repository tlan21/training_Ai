package pg

import (
	"context"
	"strconv"

	"github.com/jackc/pgx/v5/pgxpool"
	"traning_ai/backend/internal/domain"
)

// NotificationRepo — INT-62 (migration 009).
type NotificationRepo struct{ DB *pgxpool.Pool }

// FanOutClipPublished: recipients = client users whose preferences contain the clip's category
// (clip category, else its video's); a clip without any category goes to every client user (user decision).
// The clip is re-read here, so an event for a clip that is no longer public creates nothing.
func (r *NotificationRepo) FanOutClipPublished(ctx context.Context, clipID string) (int64, error) {
	tag, err := r.DB.Exec(ctx, `INSERT INTO user_notifications(user_id,kind,clip_id,video_id,title)
		SELECT u.id,$2::varchar,clips.id,clips.video_id,clips.title
		FROM clips JOIN videos cv ON cv.id=clips.video_id CROSS JOIN users u
		WHERE clips.id=$1::varchar AND `+visibleClip+` AND u.role='client'
		AND (coalesce(clips.category_id,cv.category_id) IS NULL OR EXISTS(SELECT 1 FROM user_preferences p
			WHERE p.user_id=u.id AND p.category_id=coalesce(clips.category_id,cv.category_id)))
		ON CONFLICT (user_id,kind,clip_id) DO NOTHING`, clipID, domain.NotifyKindClipPublished)
	if err != nil {
		return 0, err
	}
	return tag.RowsAffected(), nil
}

func (r *NotificationRepo) List(ctx context.Context, userID string, cursor *string, limit int) ([]domain.UserNotification, *string, int, error) {
	var before *int64
	if cursor != nil {
		id, err := strconv.ParseInt(*cursor, 10, 64)
		if err != nil || id <= 0 {
			return nil, nil, 0, domain.ErrValidation
		}
		before = &id
	}
	if limit < 1 || limit > 100 {
		return nil, nil, 0, domain.ErrValidation
	}
	const visible = `FROM user_notifications n JOIN clips ON clips.id=n.clip_id WHERE n.user_id=$1 AND ` + visibleClip
	var unread int
	if err := r.DB.QueryRow(ctx, `SELECT count(*) `+visible+` AND n.read_at IS NULL`, userID).Scan(&unread); err != nil {
		return nil, nil, 0, err
	}
	rows, err := r.DB.Query(ctx, `SELECT n.id,n.kind,n.clip_id,n.video_id,n.title,clips.thumbnail_url,n.created_at,n.read_at IS NOT NULL `+visible+`
		AND ($2::bigint IS NULL OR n.id<$2) ORDER BY n.id DESC LIMIT $3`, userID, before, limit+1)
	if err != nil {
		return nil, nil, 0, err
	}
	defer rows.Close()
	items := []domain.UserNotification{}
	for rows.Next() {
		if len(items) == limit {
			next := strconv.FormatInt(items[len(items)-1].ID, 10)
			return items, &next, unread, nil
		}
		var n domain.UserNotification
		if err := rows.Scan(&n.ID, &n.Kind, &n.ClipID, &n.VideoID, &n.Title, &n.ThumbnailURL, &n.CreatedAt, &n.Read); err != nil {
			return nil, nil, 0, err
		}
		items = append(items, n)
	}
	return items, nil, unread, rows.Err()
}

// MarkRead: nil/empty ids = all of the user's notifications. Other users' ids are ignored (no existence leak).
func (r *NotificationRepo) MarkRead(ctx context.Context, userID string, ids []int64) error {
	if ids == nil {
		ids = []int64{}
	}
	_, err := r.DB.Exec(ctx, `UPDATE user_notifications SET read_at=now()
		WHERE user_id=$1 AND read_at IS NULL AND (cardinality($2::bigint[])=0 OR id=ANY($2::bigint[]))`, userID, ids)
	return err
}
