package pg

import (
	"context"
	"encoding/json"
	"errors"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
	"traning_ai/backend/internal/domain"
)

type VideoRepo struct {
	DB         *pgxpool.Pool
	DataOrigin string
}
type ClipRepo struct{ DB *pgxpool.Pool }
type JobRepo struct{ DB *pgxpool.Pool }
type UserRepo struct {
	DB         *pgxpool.Pool
	DataOrigin string
}
type SessionRepo struct{ DB *pgxpool.Pool }
type CategoryRepo struct{ DB *pgxpool.Pool }

func notFound(err, missing error) error {
	if errors.Is(err, pgx.ErrNoRows) {
		return missing
	}
	return err
}
func update(ctx context.Context, db *pgxpool.Pool, sql string, args ...any) error {
	result, err := db.Exec(ctx, sql, args...)
	if err != nil {
		return err
	}
	if result.RowsAffected() == 0 {
		return domain.ErrNotFound
	}
	return nil
}

const videoColumns = `id,title,description,raw_file_path,thumbnail_url,duration_seconds::float8,status,uploaded_by,category_id,deleted_at,created_at,updated_at,width,height,fps,hashtags,editorial_priority`

func scanVideo(row pgx.Row) (*domain.Video, error) {
	var v domain.Video
	err := row.Scan(videoTargets(&v)...)
	return &v, notFound(err, domain.ErrVideoNotFound)
}
func (r *VideoRepo) Create(ctx context.Context, v *domain.Video) error {
	_, err := r.DB.Exec(ctx, `INSERT INTO videos(id,title,description,raw_file_path,duration_seconds,status,uploaded_by,training_origin,width,height,fps,hashtags) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)`, v.ID, v.Title, v.Description, v.RawFilePath, v.DurationSeconds, v.Status, v.UploadedBy, trainingOrigin(r.DataOrigin, v.Title), v.Width, v.Height, v.FPS, v.Hashtags)
	return err
}
func (r *VideoRepo) Get(ctx context.Context, id string) (*domain.Video, error) {
	return scanCMSVideo(r.DB.QueryRow(ctx, videoCMSSelect()+` WHERE v.id=$1`, id))
}
func (r *VideoRepo) GetProcessed(ctx context.Context, id string) (*domain.Video, error) {
	return scanCMSVideo(r.DB.QueryRow(ctx, videoCMSSelect()+` WHERE v.id=$1 AND v.status='processed'`, id))
}
func (r *VideoRepo) List(ctx context.Context, status *string, page, size int) ([]domain.Video, int, error) {
	var total int
	if err := r.DB.QueryRow(ctx, `SELECT count(*) FROM videos WHERE ($1::text IS NULL OR status=$1)`, status).Scan(&total); err != nil {
		return nil, 0, err
	}
	rows, err := r.DB.Query(ctx, `SELECT `+videoColumns+` FROM videos WHERE ($1::text IS NULL OR status=$1) ORDER BY created_at DESC,id DESC LIMIT $2 OFFSET $3`, status, size, (page-1)*size)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()
	items := []domain.Video{}
	for rows.Next() {
		v, err := scanVideo(rows)
		if err != nil {
			return nil, 0, err
		}
		items = append(items, *v)
	}
	return items, total, rows.Err()
}
func (r *VideoRepo) SetStatus(ctx context.Context, id string, status domain.VideoStatus) error {
	return update(ctx, r.DB, `UPDATE videos SET status=$2,updated_at=now() WHERE id=$1 AND status!='deleted'`, id, status)
}
func (r *VideoRepo) SetCategory(ctx context.Context, id, category string) error {
	err := update(ctx, r.DB, `UPDATE videos SET category_id=$2,updated_at=now() WHERE id=$1 AND status!='deleted'`, id, category)
	if errors.Is(err, domain.ErrNotFound) {
		return domain.ErrVideoNotFound
	}
	return categoryReferenceError(err)
}
func (r *VideoRepo) SetMediaMetadata(ctx context.Context, id string, seconds float64, width, height *int, fps *float64) error {
	return update(ctx, r.DB, `UPDATE videos SET duration_seconds=$2,width=coalesce($3,width),height=coalesce($4,height),fps=coalesce($5,fps),updated_at=now() WHERE id=$1 AND status!='deleted'`, id, seconds, width, height, fps)
}
func (r *VideoRepo) UpdateMetadata(ctx context.Context, id, title, description string, hashtags []string, priority *string) (*domain.Video, error) {
	return scanVideo(r.DB.QueryRow(ctx, `UPDATE videos SET title=$2,description=$3,hashtags=$4,editorial_priority=coalesce($5,editorial_priority),updated_at=now() WHERE id=$1 AND status!='deleted' RETURNING `+videoColumns, id, title, description, hashtags, priority))
}
func (r *VideoRepo) SoftDelete(ctx context.Context, id string) error {
	return update(ctx, r.DB, `UPDATE videos SET status='deleted',deleted_at=now(),updated_at=now() WHERE id=$1`, id)
}

const clipColumns = `id,video_id,title,start_time::float8,end_time::float8,average_score::float8,clip_file_path,thumbnail_url,status,created_by,category_id,created_at,updated_at,source_segments`

func scanClip(row pgx.Row) (*domain.Clip, error) {
	var c domain.Clip
	err := row.Scan(clipTargets(&c)...)
	return &c, notFound(err, domain.ErrClipNotFound)
}
func (r *ClipRepo) Create(ctx context.Context, c *domain.Clip) error {
	_, err := r.DB.Exec(ctx, `INSERT INTO clips(id,video_id,title,start_time,end_time,average_score,status,thumbnail_url,source_segments,created_by) VALUES($1,$2,$3,$4,$5,$6,$7,$8,coalesce($9::jsonb,'[]'::jsonb),$10)`, c.ID, c.VideoID, c.Title, c.StartTime, c.EndTime, c.AverageScore, c.Status, c.ThumbnailURL, c.SourceSegments, c.CreatedBy)
	return err
}
func (r *ClipRepo) Get(ctx context.Context, id string) (*domain.Clip, error) {
	return scanClip(r.DB.QueryRow(ctx, `SELECT `+clipColumns+` FROM clips WHERE id=$1`, id))
}
func (r *ClipRepo) GetPublished(ctx context.Context, id string) (*domain.Clip, error) {
	return scanClip(r.DB.QueryRow(ctx, `SELECT `+clipColumns+` FROM clips WHERE id=$1 AND status='published' AND EXISTS(SELECT 1 FROM videos WHERE videos.id=clips.video_id AND videos.status='processed')`, id))
}
func (r *ClipRepo) ListPublishedByVideo(ctx context.Context, id string) ([]domain.Clip, error) {
	status := "published"
	return r.List(ctx, &id, &status)
}
func (r *ClipRepo) List(ctx context.Context, videoID, status *string) ([]domain.Clip, error) {
	rows, err := r.DB.Query(ctx, `SELECT `+clipColumns+` FROM clips WHERE ($1::text IS NULL OR video_id=$1) AND ($2::text IS NULL OR status=$2) AND (status!='published' OR EXISTS(SELECT 1 FROM videos WHERE videos.id=clips.video_id AND videos.status='processed')) ORDER BY created_at DESC,id DESC`, videoID, status)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := []domain.Clip{}
	for rows.Next() {
		c, err := scanClip(rows)
		if err != nil {
			return nil, err
		}
		items = append(items, *c)
	}
	return items, rows.Err()
}
func (r *ClipRepo) SetStatus(ctx context.Context, id string, status domain.ClipStatus) error {
	return update(ctx, r.DB, `UPDATE clips SET status=$2,updated_at=now() WHERE id=$1`, id, status)
}
func (r *ClipRepo) SetFilePath(ctx context.Context, id, path string) error {
	return update(ctx, r.DB, `UPDATE clips SET clip_file_path=$2,updated_at=now() WHERE id=$1`, id, path)
}
func (r *ClipRepo) UpdateMeta(ctx context.Context, id string, title *string, start, end *float64, category *string) (*domain.Clip, error) {
	c, err := scanClip(r.DB.QueryRow(ctx, `UPDATE clips SET title=coalesce($2,title),start_time=coalesce($3,start_time),end_time=coalesce($4,end_time),category_id=coalesce($5,category_id),updated_at=now() WHERE id=$1 RETURNING `+clipColumns, id, title, start, end, category))
	return c, categoryReferenceError(err)
}
func (r *ClipRepo) HideByVideo(ctx context.Context, id string) error {
	_, err := r.DB.Exec(ctx, `UPDATE clips SET status='rejected',updated_at=now() WHERE video_id=$1`, id)
	return err
}

const jobColumns = `id,video_id,queue_name,status,worker_node_id,error_log,started_at,completed_at,updated_at,current_stage,progress,processing_options,skipped_stages`

func scanJob(row pgx.Row) (*domain.ProcessingJob, error) {
	var j domain.ProcessingJob
	err := row.Scan(&j.ID, &j.VideoID, &j.QueueName, &j.Status, &j.WorkerNodeID, &j.ErrorLog, &j.StartedAt, &j.CompletedAt, &j.UpdatedAt, &j.CurrentStage, &j.Progress, &j.ProcessingOptions, &j.SkippedStages)
	return &j, notFound(err, domain.ErrJobNotFound)
}
func (r *JobRepo) Create(ctx context.Context, videoID string) (*domain.ProcessingJob, error) {
	return scanJob(r.DB.QueryRow(ctx, `INSERT INTO video_processing_jobs(video_id) VALUES($1) RETURNING `+jobColumns, videoID))
}
func (r *JobRepo) Get(ctx context.Context, id string) (*domain.ProcessingJob, error) {
	return scanJob(r.DB.QueryRow(ctx, `SELECT `+jobColumns+` FROM video_processing_jobs WHERE id=$1`, id))
}
func (r *JobRepo) GetByVideo(ctx context.Context, id string) (*domain.ProcessingJob, error) {
	return scanJob(r.DB.QueryRow(ctx, `SELECT `+jobColumns+` FROM video_processing_jobs WHERE video_id=$1`, id))
}
func (r *JobRepo) List(ctx context.Context, status *string) ([]domain.ProcessingJob, error) {
	rows, err := r.DB.Query(ctx, `SELECT `+jobColumns+` FROM video_processing_jobs WHERE ($1::text IS NULL OR status=$1) ORDER BY updated_at DESC,id DESC`, status)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := []domain.ProcessingJob{}
	for rows.Next() {
		j, err := scanJob(rows)
		if err != nil {
			return nil, err
		}
		items = append(items, *j)
	}
	return items, rows.Err()
}
func (r *JobRepo) SetStatus(ctx context.Context, id string, status domain.JobStatus, started, completed bool) error {
	err := update(ctx, r.DB, `UPDATE video_processing_jobs SET status=$2::varchar,started_at=CASE WHEN $2::varchar='pending' THEN NULL WHEN $3 THEN coalesce(started_at,now()) ELSE started_at END,completed_at=CASE WHEN $2::varchar='pending' THEN NULL WHEN $4 THEN now() ELSE completed_at END,current_stage=CASE WHEN $2::varchar='pending' THEN NULL ELSE current_stage END,progress=CASE WHEN $2::varchar='pending' THEN 0 ELSE progress END,error_log=CASE WHEN $2::varchar='pending' THEN NULL ELSE error_log END,updated_at=now() WHERE id=$1 AND ($2::varchar!='completed' OR error_log IS DISTINCT FROM 'canceled_by_user')`, id, status, started, completed)
	if status == domain.JobCompleted && errors.Is(err, domain.ErrNotFound) {
		return domain.ErrConflict
	}
	return err
}
func (r *JobRepo) SetStage(ctx context.Context, id string, stage domain.Stage) error {
	return update(ctx, r.DB, `UPDATE video_processing_jobs SET current_stage=$2,progress=$3,updated_at=now() WHERE id=$1`, id, stage, domain.StageProgress[stage])
}
func (r *JobRepo) SetError(ctx context.Context, id, message string) error {
	return update(ctx, r.DB, `UPDATE video_processing_jobs SET error_log=$2,updated_at=now() WHERE id=$1`, id, message)
}
func (r *JobRepo) SetProcessingOptions(ctx context.Context, id string, options domain.ProcessingOptions) error {
	data, err := json.Marshal(options)
	if err != nil {
		return err
	}
	return update(ctx, r.DB, `UPDATE video_processing_jobs SET processing_options=$2::jsonb,skipped_stages=$3,updated_at=now() WHERE id=$1`, id, string(data), options.SkippedStages())
}

const userColumns = `id,username,email,avatar_url,password_hash,role,created_at,updated_at`

func scanUser(row pgx.Row) (*domain.User, error) {
	var u domain.User
	err := row.Scan(&u.ID, &u.Username, &u.Email, &u.AvatarURL, &u.PasswordHash, &u.Role, &u.CreatedAt, &u.UpdatedAt)
	return &u, notFound(err, domain.ErrUserNotFound)
}
func (r *UserRepo) Create(ctx context.Context, u *domain.User) error {
	_, err := r.DB.Exec(ctx, `INSERT INTO users(id,username,email,password_hash,role,training_origin) VALUES($1,$2,$3,$4,$5,$6)`, u.ID, u.Username, u.Email, u.PasswordHash, u.Role, trainingOrigin(r.DataOrigin, u.Username, u.Email))
	var pgerr *pgconn.PgError
	if errors.As(err, &pgerr) && pgerr.Code == "23505" {
		if strings.Contains(pgerr.ConstraintName, "email") {
			return domain.ErrEmailTaken
		}
		return domain.ErrUsernameTaken
	}
	return err
}
func (r *UserRepo) Get(ctx context.Context, id string) (*domain.User, error) {
	return scanUser(r.DB.QueryRow(ctx, `SELECT `+userColumns+` FROM users WHERE id=$1`, id))
}
func (r *UserRepo) GetByEmail(ctx context.Context, email string) (*domain.User, error) {
	return scanUser(r.DB.QueryRow(ctx, `SELECT `+userColumns+` FROM users WHERE email=$1`, email))
}
func (r *UserRepo) UpdateProfile(ctx context.Context, id string, name *string) (*domain.User, error) {
	return scanUser(r.DB.QueryRow(ctx, `UPDATE users SET username=coalesce($2,username),updated_at=now() WHERE id=$1 RETURNING `+userColumns, id, name))
}
func (r *UserRepo) UpdatePassword(ctx context.Context, id, hash string) error {
	return update(ctx, r.DB, `UPDATE users SET password_hash=$2,updated_at=now() WHERE id=$1`, id, hash)
}
func (r *UserRepo) List(ctx context.Context, page, size int, query string) ([]domain.User, int, error) {
	var total int
	pattern := "%" + strings.NewReplacer(`\`, `\\`, "%", `\%`, "_", `\_`).Replace(strings.TrimSpace(query)) + "%"
	if err := r.DB.QueryRow(ctx, `SELECT count(*) FROM users WHERE username ILIKE $1 OR email ILIKE $1`, pattern).Scan(&total); err != nil {
		return nil, 0, err
	}
	rows, err := r.DB.Query(ctx, `SELECT `+userColumns+` FROM users WHERE username ILIKE $1 OR email ILIKE $1 ORDER BY created_at DESC,id DESC LIMIT $2 OFFSET $3`, pattern, size, (page-1)*size)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()
	items := []domain.User{}
	for rows.Next() {
		u, err := scanUser(rows)
		if err != nil {
			return nil, 0, err
		}
		items = append(items, *u)
	}
	return items, total, rows.Err()
}

func (r *SessionRepo) Create(ctx context.Context, userID, hash string, expires time.Time) (string, error) {
	var id string
	err := r.DB.QueryRow(ctx, `INSERT INTO user_sessions(user_id,refresh_token_hash,expires_at) VALUES($1,$2,$3) RETURNING id`, userID, hash, expires).Scan(&id)
	return id, err
}
func (r *SessionRepo) GetByHash(ctx context.Context, hash string) (*domain.Session, error) {
	var s domain.Session
	err := r.DB.QueryRow(ctx, `SELECT id,user_id,refresh_token_hash,expires_at,created_at FROM user_sessions WHERE refresh_token_hash=$1`, hash).Scan(&s.ID, &s.UserID, &s.RefreshTokenHash, &s.ExpiresAt, &s.CreatedAt)
	return &s, notFound(err, domain.ErrNotFound)
}
func (r *SessionRepo) Delete(ctx context.Context, id string) error {
	_, err := r.DB.Exec(ctx, `DELETE FROM user_sessions WHERE id=$1`, id)
	return err
}
func (r *SessionRepo) DeleteByUser(ctx context.Context, id string) error {
	_, err := r.DB.Exec(ctx, `DELETE FROM user_sessions WHERE user_id=$1`, id)
	return err
}

func (r *CategoryRepo) List(ctx context.Context) ([]domain.Category, error) {
	rows, err := r.DB.Query(ctx, `SELECT c.id,c.name,c.created_at,c.description,c.keywords,(SELECT count(*) FROM videos v WHERE v.category_id=c.id AND v.status!='deleted') FROM categories c ORDER BY c.name,c.id`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := []domain.Category{}
	for rows.Next() {
		var c domain.Category
		if err := rows.Scan(&c.ID, &c.Name, &c.CreatedAt, &c.Description, &c.Keywords, &c.VideoCount); err != nil {
			return nil, err
		}
		items = append(items, c)
	}
	return items, rows.Err()
}
func (r *CategoryRepo) Create(ctx context.Context, name string, description *string, keywords []string) (*domain.Category, error) {
	if keywords == nil {
		keywords = []string{}
	}
	var c domain.Category
	err := r.DB.QueryRow(ctx, `INSERT INTO categories(name,description,keywords) VALUES($1,$2,$3) RETURNING id,name,created_at,description,keywords`, name, description, keywords).Scan(&c.ID, &c.Name, &c.CreatedAt, &c.Description, &c.Keywords)
	return &c, categoryWriteError(err)
}
func (r *CategoryRepo) Update(ctx context.Context, id, name string, description *string, keywords []string) (*domain.Category, error) {
	var c domain.Category
	err := r.DB.QueryRow(ctx, `UPDATE categories SET name=$2,description=coalesce($3,description),keywords=coalesce($4,keywords) WHERE id=$1 RETURNING id,name,created_at,description,keywords,(SELECT count(*) FROM videos v WHERE v.category_id=$1 AND v.status!='deleted')`, id, name, description, keywords).Scan(&c.ID, &c.Name, &c.CreatedAt, &c.Description, &c.Keywords, &c.VideoCount)
	return &c, categoryWriteError(notFound(err, domain.ErrCategoryNotFound))
}
func categoryWriteError(err error) error {
	var conflict *pgconn.PgError
	if errors.As(err, &conflict) && (conflict.Code == "23505" || conflict.Code == "23503") {
		return domain.ErrConflict
	}
	return err
}
func (r *CategoryRepo) Delete(ctx context.Context, id string) error {
	tx, err := r.DB.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)
	// User decision 2026-11-02: soft-deleted videos (and their clips) must not pin a category the CMS shows as unused
	// (video_count excludes them). Live videos, clips of live videos and user preferences still block via FK → 409.
	if _, err = tx.Exec(ctx, `UPDATE clips SET category_id=NULL WHERE category_id=$1 AND video_id IN (SELECT id FROM videos WHERE status='deleted')`, id); err != nil {
		return err
	}
	if _, err = tx.Exec(ctx, `UPDATE videos SET category_id=NULL WHERE category_id=$1 AND status='deleted'`, id); err != nil {
		return err
	}
	tag, err := tx.Exec(ctx, `DELETE FROM categories WHERE id=$1`, id)
	if err != nil {
		return categoryWriteError(err)
	}
	if tag.RowsAffected() == 0 {
		return domain.ErrCategoryNotFound
	}
	return tx.Commit(ctx)
}

func categoryReferenceError(err error) error {
	var ref *pgconn.PgError
	if errors.As(err, &ref) && ref.Code == "23503" {
		return domain.ErrCategoryNotFound
	}
	return err
}

func (r *JobRepo) RequestCancel(ctx context.Context, id string) error {
	tag, err := r.DB.Exec(ctx, `UPDATE video_processing_jobs SET error_log='canceled_by_user',updated_at=now() WHERE id=$1 AND status IN ('pending','running')`, id)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return domain.ErrConflict
	}
	return nil
}
