package pg

import (
	"context"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"traning_ai/backend/internal/domain"
)

func likePattern(query string) string {
	return "%" + strings.NewReplacer(`\`, `\\`, "%", `\%`, "_", `\_`).Replace(strings.TrimSpace(query)) + "%"
}
func qualified(columns, alias string) string {
	return alias + "." + strings.ReplaceAll(columns, ",", ","+alias+".")
}
func videoTargets(v *domain.Video) []any {
	return []any{&v.ID, &v.Title, &v.Description, &v.RawFilePath, &v.ThumbnailURL, &v.DurationSeconds, &v.Status, &v.UploadedBy, &v.CategoryID, &v.DeletedAt, &v.CreatedAt, &v.UpdatedAt, &v.Width, &v.Height, &v.FPS, &v.Hashtags, &v.EditorialPriority}
}
func scanCMSVideo(row pgx.Row) (*domain.Video, error) {
	var v domain.Video
	fields := append(videoTargets(&v), &v.CategoryName, &v.UploadedByName, &v.CategoryAssignedAt)
	err := row.Scan(fields...)
	return &v, notFound(err, domain.ErrVideoNotFound)
}
func videoCMSSelect() string {
	return `SELECT ` + qualified(videoColumns, "v") + `,c.name,u.username,v.category_assigned_at FROM videos v LEFT JOIN categories c ON c.id=v.category_id LEFT JOIN users u ON u.id=v.uploaded_by `
}
func (r *VideoRepo) ListCMS(ctx context.Context, f domain.CMSVideoFilter) ([]domain.Video, int, error) {
	where := ` WHERE ($1::text IS NULL OR v.status=$1) AND ($2::bool OR v.status!='deleted' OR $1::text='deleted')
	 AND (v.title ILIKE $3) AND ($4='' OR v.category_id=$4) AND ($5::timestamptz IS NULL OR v.created_at>=$5)
	 AND ($6::timestamptz IS NULL OR v.created_at<$6)`
	args := []any{f.Status, f.IncludeDeleted, likePattern(f.Query), f.CategoryID, f.From, f.To}
	var total int
	if err := r.DB.QueryRow(ctx, `SELECT count(*) FROM videos v`+where, args...).Scan(&total); err != nil {
		return nil, 0, err
	}
	order := ` ORDER BY v.created_at DESC,v.id DESC`
	if f.SortAssigned {
		order = ` ORDER BY v.category_assigned_at DESC NULLS LAST,v.created_at DESC,v.id DESC`
	}
	rows, err := r.DB.Query(ctx, videoCMSSelect()+where+order+` LIMIT $7 OFFSET $8`, append(args, f.Size, (f.Page-1)*f.Size)...)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()
	items := []domain.Video{}
	for rows.Next() {
		v, err := scanCMSVideo(rows)
		if err != nil {
			return nil, 0, err
		}
		items = append(items, *v)
	}
	return items, total, rows.Err()
}
func clipTargets(c *domain.Clip) []any {
	return []any{&c.ID, &c.VideoID, &c.Title, &c.StartTime, &c.EndTime, &c.AverageScore, &c.ClipFilePath, &c.ThumbnailURL, &c.Status, &c.CreatedBy, &c.CategoryID, &c.CreatedAt, &c.UpdatedAt, &c.SourceSegments}
}
func (r *ClipRepo) ListCMS(ctx context.Context, videoID, status *string, query string) ([]domain.Clip, error) {
	rows, err := r.DB.Query(ctx, `SELECT `+qualified(clipColumns, "cl")+`,u.username,cat.name,
	 (SELECT count(*) FROM user_interactions i JOIN users viewer ON viewer.id=i.user_id WHERE i.clip_id=cl.id AND i.interaction_type='click' AND viewer.role='client')
	 FROM clips cl JOIN videos v ON v.id=cl.video_id LEFT JOIN users u ON u.id=cl.created_by
	 LEFT JOIN categories cat ON cat.id=coalesce(cl.category_id,v.category_id)
	 WHERE v.status!='deleted' AND ($1::text IS NULL OR cl.video_id=$1) AND ($2::text IS NULL OR cl.status=$2) AND cl.title ILIKE $3
	 AND (cl.status!='published' OR v.status='processed') ORDER BY cl.created_at DESC,cl.id DESC`, videoID, status, likePattern(query))
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := []domain.Clip{}
	for rows.Next() {
		var c domain.Clip
		fields := append(clipTargets(&c), &c.CreatedByName, &c.CategoryName, &c.ViewCount)
		if err := rows.Scan(fields...); err != nil {
			return nil, err
		}
		items = append(items, c)
	}
	return items, rows.Err()
}

type CMSRepo struct{ DB *pgxpool.Pool }

func (r *CMSRepo) Overview(ctx context.Context, month time.Time) (*domain.CMSMetrics, error) {
	end := month.AddDate(0, 1, 0)
	m := &domain.CMSMetrics{DailyProcessing: []domain.DailyProcessing{}}
	err := r.DB.QueryRow(ctx, `WITH vs AS (
	 SELECT count(*) FILTER(WHERE status!='deleted') total,count(*) FILTER(WHERE status='processed') processed,
	 count(*) FILTER(WHERE status='failed') failed,count(*) FILTER(WHERE status='deleted') deleted FROM videos),
	 js AS (SELECT count(*) FILTER(WHERE j.status='pending') pending,count(*) FILTER(WHERE j.status='running') running,
	 count(*) FILTER(WHERE j.status='completed') completed,count(*) FILTER(WHERE j.status='failed') failed,
	 avg(extract(epoch FROM j.completed_at-j.started_at)) FILTER(WHERE j.status='completed' AND j.started_at IS NOT NULL AND j.completed_at>=j.started_at)::float8 elapsed
	 FROM video_processing_jobs j JOIN videos v ON v.id=j.video_id WHERE v.status!='deleted'),
	 ix AS (SELECT count(DISTINCT i.user_id) FILTER(WHERE i.created_at>=now()-interval '15 minutes') active,
	 count(*) FILTER(WHERE i.interaction_type='click') views,
	 count(*) FILTER(WHERE i.interaction_type='click' AND i.created_at>=$1 AND i.created_at<$2) month_views
	 FROM user_interactions i JOIN users u ON u.id=i.user_id WHERE u.role='client')
	 SELECT vs.total,vs.processed,vs.failed,vs.deleted,
	 (SELECT count(*) FROM clips c JOIN videos v ON v.id=c.video_id WHERE c.status='published' AND v.status='processed'),
	 js.pending,js.running,js.completed,js.failed,(SELECT count(*) FROM users),ix.active,ix.month_views,ix.views,
	 js.completed::float8/nullif(js.completed+js.failed,0)*100,js.elapsed FROM vs,js,ix`, month, end).Scan(
		&m.TotalVideos, &m.ProcessedVideos, &m.FailedVideos, &m.DeletedVideos, &m.PublishedClips, &m.PendingJobs, &m.RunningJobs,
		&m.CompletedJobs, &m.FailedJobs, &m.TotalUsers, &m.ActiveUsers, &m.ViewsMonth, &m.TotalViews, &m.SuccessRate, &m.AverageProcessingSeconds)
	if err != nil {
		return nil, err
	}
	rows, err := r.DB.Query(ctx, `SELECT to_char(d AT TIME ZONE 'UTC','YYYY-MM-DD'),count(j.id) FROM generate_series($1::timestamptz,$2::timestamptz-interval '1 day',interval '1 day') d
	 LEFT JOIN (video_processing_jobs j JOIN videos v ON v.id=j.video_id AND v.status!='deleted')
	 ON j.status='completed' AND (j.completed_at AT TIME ZONE 'UTC')::date=(d AT TIME ZONE 'UTC')::date
	 GROUP BY d ORDER BY d`, month, end)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	for rows.Next() {
		var day domain.DailyProcessing
		if err := rows.Scan(&day.Date, &day.Count); err != nil {
			return nil, err
		}
		m.DailyProcessing = append(m.DailyProcessing, day)
	}
	return m, rows.Err()
}
