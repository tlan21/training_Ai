package pg

import (
	"context"
	"errors"
	"strconv"

	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
	"traning_ai/backend/internal/domain"
)

type InteractionRepo struct{ DB *pgxpool.Pool }

func (r *InteractionRepo) Add(ctx context.Context, i *domain.Interaction) error {
	if i.DurationWatched < 0 || int64(i.DurationWatched) > 2147483647 {
		return domain.ErrValidation
	}
	err := r.DB.QueryRow(ctx, `INSERT INTO user_interactions(user_id,video_id,clip_id,interaction_type,duration_watched)
		SELECT $1::varchar,$2::varchar,$3::varchar,$4::varchar,$5::int FROM videos v WHERE v.id=$2 AND v.status='processed'
		AND ($3::varchar IS NULL OR EXISTS(SELECT 1 FROM clips c WHERE c.id=$3 AND c.video_id=v.id AND c.status='published'))
		RETURNING id,created_at`, i.UserID, i.VideoID, i.ClipID, i.InteractionType, i.DurationWatched).Scan(&i.ID, &i.CreatedAt)
	var pgerr *pgconn.PgError
	if errors.As(err, &pgerr) && (pgerr.Code == "23503" || pgerr.Code == "23514") {
		return domain.ErrValidation
	}
	return notFound(err, domain.ErrVideoNotFound)
}

func (r *InteractionRepo) History(ctx context.Context, userID string, cursor *string, limit int) ([]domain.HistoryItem, *string, error) {
	return r.list(ctx, userID, cursor, limit, []string{"click", "watch_time"})
}

func (r *InteractionRepo) Likes(ctx context.Context, userID string, cursor *string, limit int) ([]domain.Clip, *string, error) {
	items, next, err := r.list(ctx, userID, cursor, limit, []string{"like"})
	clips := make([]domain.Clip, 0, len(items))
	for _, item := range items {
		clips = append(clips, item.Clip)
	}
	return clips, next, err
}

func (r *InteractionRepo) list(ctx context.Context, userID string, cursor *string, limit int, types []string) ([]domain.HistoryItem, *string, error) {
	var before *int64
	if cursor != nil {
		id, err := strconv.ParseInt(*cursor, 10, 64)
		if err != nil || id <= 0 {
			return nil, nil, domain.ErrValidation
		}
		before = &id
	}
	if limit < 1 || limit > 100 {
		return nil, nil, domain.ErrValidation
	}
	rows, err := r.DB.Query(ctx, `WITH recent AS (
		SELECT clip_id AS watched_clip,max(id) AS interaction_id,max(created_at) AS watched_at,sum(duration_watched) AS duration_watched
		FROM user_interactions WHERE user_id=$1 AND interaction_type=ANY($4::text[]) AND clip_id IS NOT NULL GROUP BY clip_id
	)
	SELECT `+clipColumns+`,recent.interaction_id,recent.watched_at,recent.duration_watched
	FROM clips JOIN recent ON clips.id=recent.watched_clip
	WHERE clips.status='published' AND EXISTS(SELECT 1 FROM videos WHERE videos.id=clips.video_id AND videos.status='processed')
	AND ($2::bigint IS NULL OR recent.interaction_id<$2) ORDER BY recent.interaction_id DESC LIMIT $3`, userID, before, limit+1, types)
	if err != nil {
		return nil, nil, err
	}
	defer rows.Close()
	items := []domain.HistoryItem{}
	var next *string
	for rows.Next() {
		if len(items) == limit {
			return items, next, nil
		}
		var item domain.HistoryItem
		var id int64
		c := &item.Clip
		if err := rows.Scan(&c.ID, &c.VideoID, &c.Title, &c.StartTime, &c.EndTime, &c.AverageScore,
			&c.ClipFilePath, &c.ThumbnailURL, &c.Status, &c.CreatedBy, &c.CategoryID, &c.CreatedAt, &c.UpdatedAt,
			&id, &item.WatchedAt, &item.DurationWatched); err != nil {
			return nil, nil, err
		}
		items = append(items, item)
		value := strconv.FormatInt(id, 10)
		next = &value
	}
	return items, nil, rows.Err()
}

func (r *InteractionRepo) PopularityTop(ctx context.Context, limit int) ([]string, error) {
	rows, err := r.DB.Query(ctx, `SELECT i.video_id FROM user_interactions i JOIN videos v ON v.id=i.video_id
		WHERE i.created_at>=now()-interval '7 days' AND v.status='processed'
		AND EXISTS(SELECT 1 FROM clips c WHERE c.video_id=v.id AND c.status='published')
		GROUP BY i.video_id ORDER BY count(*) DESC,i.video_id LIMIT $1`, limit)
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
