package pg

import (
	"context"
	"traning_ai/backend/internal/domain"
)

const popularityWindow = `WITH popularity AS (
	SELECT video_id,count(*) AS score FROM user_interactions
	WHERE created_at>$1::timestamptz-interval '7 days' AND created_at<=$1 GROUP BY video_id
)`

func (r *ClipRepo) ListPopularPage(ctx context.Context, cursor string, limit int) ([]domain.Clip, *string, error) {
	p, err := domain.ParseContentCursor(cursor, "feed", limit)
	if err != nil {
		return nil, nil, err
	}
	rows, err := r.DB.Query(ctx, popularityWindow+`, ranked AS (
		SELECT clips.*,COALESCE(p.score,0) AS rank
		FROM clips LEFT JOIN popularity p ON p.video_id=clips.video_id
		WHERE clips.status='published' AND clips.created_at<=$1
		AND EXISTS(SELECT 1 FROM videos v WHERE v.id=clips.video_id AND v.status='processed' AND v.deleted_at IS NULL AND v.created_at<=$1)
	) SELECT `+clipColumns+`,rank FROM ranked
	WHERE ($2='' OR (rank,created_at,id)<($3::bigint,$4::timestamptz,$2::text))
	ORDER BY rank DESC,created_at DESC,id DESC LIMIT $5`, p.Snapshot, p.ID, p.Rank, p.CreatedAt, limit+1)
	if err != nil {
		return nil, nil, err
	}
	defer rows.Close()
	items := []domain.Clip{}
	more := false
	for rows.Next() {
		var c domain.Clip
		var rank int64
		err := rows.Scan(&c.ID, &c.VideoID, &c.Title, &c.StartTime, &c.EndTime, &c.AverageScore, &c.ClipFilePath, &c.ThumbnailURL, &c.Status, &c.CreatedBy, &c.CategoryID, &c.CreatedAt, &c.UpdatedAt, &rank)
		if err != nil {
			return nil, nil, err
		}
		if len(items) == limit {
			more = true
			continue
		}
		items = append(items, c)
		p.Rank, p.CreatedAt, p.ID = rank, c.CreatedAt, c.ID
	}
	if err := rows.Err(); err != nil {
		return nil, nil, err
	}
	if more {
		next, err := p.Encode()
		return items, &next, err
	}
	return items, nil, nil
}

func (r *VideoRepo) ListPublicPage(ctx context.Context, categoryID, sort, cursor string, limit int) ([]domain.Video, *string, error) {
	if sort != "newest" && sort != "trending" {
		return nil, nil, domain.ErrValidation
	}
	p, err := domain.ParseContentCursor(cursor, "videos/"+sort+"/"+categoryID, limit)
	if err != nil {
		return nil, nil, err
	}
	ranking := "0::bigint"
	join := ""
	published := ""
	if sort == "trending" {
		ranking = "COALESCE(p.score,0)"
		join = " LEFT JOIN popularity p ON p.video_id=videos.id"
		published = " AND EXISTS(SELECT 1 FROM clips c WHERE c.video_id=videos.id AND c.status='published' AND c.created_at<=$1)"
	}
	rows, err := r.DB.Query(ctx, popularityWindow+`, ranked AS (
		SELECT videos.*,`+ranking+` AS rank FROM videos`+join+`
		WHERE videos.status='processed' AND videos.deleted_at IS NULL AND videos.created_at<=$1 AND ($2='' OR videos.category_id=$2)`+published+`
	) SELECT `+videoColumns+`,rank FROM ranked
	WHERE ($3='' OR (rank,created_at,id)<($4::bigint,$5::timestamptz,$3::text))
	ORDER BY rank DESC,created_at DESC,id DESC LIMIT $6`, p.Snapshot, categoryID, p.ID, p.Rank, p.CreatedAt, limit+1)
	if err != nil {
		return nil, nil, err
	}
	defer rows.Close()
	items := []domain.Video{}
	more := false
	for rows.Next() {
		var v domain.Video
		var rank int64
		err := rows.Scan(&v.ID, &v.Title, &v.Description, &v.RawFilePath, &v.ThumbnailURL, &v.DurationSeconds, &v.Status, &v.UploadedBy, &v.CategoryID, &v.DeletedAt, &v.CreatedAt, &v.UpdatedAt, &rank)
		if err != nil {
			return nil, nil, err
		}
		if len(items) == limit {
			more = true
			continue
		}
		items = append(items, v)
		p.Rank, p.CreatedAt, p.ID = rank, v.CreatedAt, v.ID
	}
	if err := rows.Err(); err != nil {
		return nil, nil, err
	}
	if more {
		next, err := p.Encode()
		return items, &next, err
	}
	return items, nil, nil
}
