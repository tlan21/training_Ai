package pg

import (
	"context"
	"errors"
	"strconv"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
	"traning_ai/backend/internal/domain"
)

// LibraryRepo — INT-61 (migration 008). user_interactions is never modified here.
type LibraryRepo struct{ DB *pgxpool.Pool }

// visibleClip is the public-clip rule: published clip of a processed, non-deleted video.
const visibleClip = `clips.status='published' AND EXISTS(SELECT 1 FROM videos v WHERE v.id=clips.video_id AND v.status='processed' AND v.deleted_at IS NULL)`

// qualifiedClipColumns = clipColumns with the clips. prefix (joined tables also have created_at/clip_id).
var qualifiedClipColumns = func() string {
	cols := strings.Split(clipColumns, ",")
	for i, c := range cols {
		cols[i] = "clips." + c
	}
	return strings.Join(cols, ",")
}()

// Cursor "<unix micro>.<clip id>" of the last row: stable under equal timestamps.
func parseTimeCursor(cursor *string) (*time.Time, string, error) {
	if cursor == nil {
		return nil, "", nil
	}
	head, clip, ok := strings.Cut(*cursor, ".")
	micro, err := strconv.ParseInt(head, 10, 64)
	if !ok || err != nil || micro <= 0 || clip == "" {
		return nil, "", domain.ErrValidation
	}
	at := time.UnixMicro(micro)
	return &at, clip, nil
}

func timeCursor(at time.Time, clip string) *string {
	value := strconv.FormatInt(at.UnixMicro(), 10) + "." + clip
	return &value
}

// clipPage runs a "<clip columns>, <sort time>" query ordered newest first (LIMIT limit+1) and builds the next cursor.
func clipPage(ctx context.Context, db *pgxpool.Pool, limit int, sql string, args ...any) ([]domain.Clip, *string, error) {
	rows, err := db.Query(ctx, sql, args...)
	if err != nil {
		return nil, nil, err
	}
	defer rows.Close()
	clips := []domain.Clip{}
	var last time.Time
	for rows.Next() {
		if len(clips) == limit {
			return clips, timeCursor(last, clips[len(clips)-1].ID), nil
		}
		var c domain.Clip
		if err := rows.Scan(&c.ID, &c.VideoID, &c.Title, &c.StartTime, &c.EndTime, &c.AverageScore, &c.ClipFilePath, &c.ThumbnailURL,
			&c.Status, &c.CreatedBy, &c.CategoryID, &c.CreatedAt, &c.UpdatedAt, &c.SourceSegments, &last); err != nil {
			return nil, nil, err
		}
		clips = append(clips, c)
	}
	return clips, nil, rows.Err()
}

func (r *LibraryRepo) SetMark(ctx context.Context, userID, clipID, kind string, on bool) (bool, string, error) {
	if kind != domain.MarkLike && kind != domain.MarkSave {
		return false, "", domain.ErrValidation
	}
	if !on {
		_, err := r.DB.Exec(ctx, `DELETE FROM user_clip_marks WHERE user_id=$1 AND kind=$2 AND clip_id=$3`, userID, kind, clipID)
		return false, "", err
	}
	var videoID string
	if err := r.DB.QueryRow(ctx, `SELECT video_id FROM clips WHERE id=$1 AND `+visibleClip, clipID).Scan(&videoID); err != nil {
		return false, "", notFound(err, domain.ErrClipNotFound)
	}
	tag, err := r.DB.Exec(ctx, `INSERT INTO user_clip_marks(user_id,clip_id,kind) VALUES($1,$2,$3) ON CONFLICT DO NOTHING`, userID, clipID, kind)
	if err != nil {
		return false, "", err
	}
	return tag.RowsAffected() == 1, videoID, nil
}

func (r *LibraryRepo) Marks(ctx context.Context, userID, kind string, cursor *string, limit int) ([]domain.Clip, *string, error) {
	return marks(ctx, r.DB, userID, kind, cursor, limit)
}

func marks(ctx context.Context, db *pgxpool.Pool, userID, kind string, cursor *string, limit int) ([]domain.Clip, *string, error) {
	at, clip, err := parseTimeCursor(cursor)
	if err != nil || limit < 1 || limit > 100 {
		return nil, nil, domain.ErrValidation
	}
	return clipPage(ctx, db, limit, `SELECT `+qualifiedClipColumns+`,m.created_at FROM user_clip_marks m JOIN clips ON clips.id=m.clip_id
		WHERE m.user_id=$1 AND m.kind=$2 AND `+visibleClip+`
		AND ($3::timestamptz IS NULL OR (m.created_at,m.clip_id)<($3::timestamptz,$4::varchar))
		ORDER BY m.created_at DESC,m.clip_id DESC LIMIT $5`, userID, kind, at, clip, limit+1)
}

func (r *LibraryRepo) ClipStates(ctx context.Context, userID string, clipIDs []string) ([]domain.ClipState, error) {
	rows, err := r.DB.Query(ctx, `SELECT clips.id,
		EXISTS(SELECT 1 FROM user_clip_marks m WHERE m.user_id=$1 AND m.clip_id=clips.id AND m.kind='like'),
		EXISTS(SELECT 1 FROM user_clip_marks m WHERE m.user_id=$1 AND m.clip_id=clips.id AND m.kind='save'),
		coalesce((SELECT array_agg(l.id ORDER BY l.id) FROM user_lists l JOIN user_list_items i ON i.list_id=l.id
			WHERE l.user_id=$1 AND i.clip_id=clips.id),'{}')
		FROM clips WHERE clips.id=ANY($2::varchar[]) AND `+visibleClip+` ORDER BY array_position($2::varchar[],clips.id)`, userID, clipIDs)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	states := []domain.ClipState{}
	for rows.Next() {
		var s domain.ClipState
		if err := rows.Scan(&s.ClipID, &s.Liked, &s.Saved, &s.ListIDs); err != nil {
			return nil, err
		}
		states = append(states, s)
	}
	return states, rows.Err()
}

// HideHistory: unknown clip ids are a no-op (idempotent delete, 204).
func (r *LibraryRepo) HideHistory(ctx context.Context, userID, clipID string) error {
	_, err := r.DB.Exec(ctx, `INSERT INTO user_history_hidden(user_id,clip_id) SELECT $1,id FROM clips WHERE id=$2
		ON CONFLICT (user_id,clip_id) DO UPDATE SET hidden_at=now()`, userID, clipID)
	return err
}

func (r *LibraryRepo) ClearHistory(ctx context.Context, userID string) error {
	_, err := r.DB.Exec(ctx, `INSERT INTO user_history_cleared(user_id) VALUES($1) ON CONFLICT (user_id) DO UPDATE SET cleared_at=now()`, userID)
	return err
}

const listColumns = `l.id,l.user_id,l.name,
	(SELECT count(*) FROM user_list_items i JOIN clips ON clips.id=i.clip_id WHERE i.list_id=l.id AND ` + visibleClip + `)::int,
	(SELECT clips.thumbnail_url FROM user_list_items i JOIN clips ON clips.id=i.clip_id WHERE i.list_id=l.id AND ` + visibleClip + `
		ORDER BY i.added_at DESC,i.clip_id DESC LIMIT 1),
	l.created_at,l.updated_at`

func scanList(row pgx.Row) (*domain.UserList, error) {
	var l domain.UserList
	if err := row.Scan(&l.ID, &l.UserID, &l.Name, &l.ItemCount, &l.CoverThumbnailURL, &l.CreatedAt, &l.UpdatedAt); err != nil {
		return nil, err
	}
	return &l, nil
}

func (r *LibraryRepo) Lists(ctx context.Context, userID string) ([]domain.UserList, error) {
	rows, err := r.DB.Query(ctx, `SELECT `+listColumns+` FROM user_lists l WHERE l.user_id=$1 ORDER BY l.updated_at DESC,l.id DESC`, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	lists := []domain.UserList{}
	for rows.Next() {
		l, err := scanList(rows)
		if err != nil {
			return nil, err
		}
		lists = append(lists, *l)
	}
	return lists, rows.Err()
}

func listNameErr(err error) error {
	var pgerr *pgconn.PgError
	if errors.As(err, &pgerr) && pgerr.Code == "23505" {
		return domain.ErrListNameTaken
	}
	if errors.As(err, &pgerr) && (pgerr.Code == "23514" || pgerr.Code == "22001") {
		return domain.ErrValidation
	}
	return err
}

func (r *LibraryRepo) CreateList(ctx context.Context, userID, name string) (*domain.UserList, error) {
	// ponytail: count check and insert are not one lock; two concurrent creates at 49 can reach 51. Fine for a personal list cap.
	var id string
	err := r.DB.QueryRow(ctx, `INSERT INTO user_lists(user_id,name) SELECT $1::varchar,$2::varchar
		WHERE (SELECT count(*) FROM user_lists WHERE user_id=$1::varchar)<$3::int RETURNING id`, userID, name, domain.MaxUserLists).Scan(&id)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, domain.ErrListLimit
	}
	if err != nil {
		return nil, listNameErr(err)
	}
	return scanList(r.DB.QueryRow(ctx, `SELECT `+listColumns+` FROM user_lists l WHERE l.id=$1`, id))
}

func (r *LibraryRepo) RenameList(ctx context.Context, userID, listID, name string) (*domain.UserList, error) {
	tag, err := r.DB.Exec(ctx, `UPDATE user_lists SET name=$3,updated_at=now() WHERE id=$1 AND user_id=$2`, listID, userID, name)
	if err != nil {
		return nil, listNameErr(err)
	}
	if tag.RowsAffected() == 0 {
		return nil, domain.ErrListNotFound
	}
	return scanList(r.DB.QueryRow(ctx, `SELECT `+listColumns+` FROM user_lists l WHERE l.id=$1`, listID))
}

func (r *LibraryRepo) DeleteList(ctx context.Context, userID, listID string) error {
	tag, err := r.DB.Exec(ctx, `DELETE FROM user_lists WHERE id=$1 AND user_id=$2`, listID, userID)
	if err == nil && tag.RowsAffected() == 0 {
		return domain.ErrListNotFound
	}
	return err
}

// owns: another user's list is reported as not found (no existence leak).
func (r *LibraryRepo) owns(ctx context.Context, userID, listID string) error {
	var ok bool
	if err := r.DB.QueryRow(ctx, `SELECT EXISTS(SELECT 1 FROM user_lists WHERE id=$1 AND user_id=$2)`, listID, userID).Scan(&ok); err != nil {
		return err
	}
	if !ok {
		return domain.ErrListNotFound
	}
	return nil
}

func (r *LibraryRepo) ListItems(ctx context.Context, userID, listID string, cursor *string, limit int) ([]domain.Clip, *string, error) {
	at, clip, err := parseTimeCursor(cursor)
	if err != nil || limit < 1 || limit > 100 {
		return nil, nil, domain.ErrValidation
	}
	if err := r.owns(ctx, userID, listID); err != nil {
		return nil, nil, err
	}
	return clipPage(ctx, r.DB, limit, `SELECT `+qualifiedClipColumns+`,i.added_at FROM user_list_items i JOIN clips ON clips.id=i.clip_id
		WHERE i.list_id=$1 AND `+visibleClip+`
		AND ($2::timestamptz IS NULL OR (i.added_at,i.clip_id)<($2::timestamptz,$3::varchar))
		ORDER BY i.added_at DESC,i.clip_id DESC LIMIT $4`, listID, at, clip, limit+1)
}

func (r *LibraryRepo) SetListItem(ctx context.Context, userID, listID, clipID string, on bool) error {
	if err := r.owns(ctx, userID, listID); err != nil {
		return err
	}
	if !on {
		tag, err := r.DB.Exec(ctx, `DELETE FROM user_list_items WHERE list_id=$1 AND clip_id=$2`, listID, clipID)
		if err == nil && tag.RowsAffected() == 1 {
			_, err = r.DB.Exec(ctx, `UPDATE user_lists SET updated_at=now() WHERE id=$1`, listID)
		}
		return err
	}
	var visible, present bool
	if err := r.DB.QueryRow(ctx, `SELECT EXISTS(SELECT 1 FROM clips WHERE id=$2 AND `+visibleClip+`),
		EXISTS(SELECT 1 FROM user_list_items WHERE list_id=$1 AND clip_id=$2)`, listID, clipID).Scan(&visible, &present); err != nil {
		return err
	}
	if !visible {
		return domain.ErrClipNotFound
	}
	if present {
		return nil
	}
	tag, err := r.DB.Exec(ctx, `INSERT INTO user_list_items(list_id,clip_id) SELECT $1::varchar,$2::varchar
		WHERE (SELECT count(*) FROM user_list_items WHERE list_id=$1::varchar)<$3::int ON CONFLICT DO NOTHING`, listID, clipID, domain.MaxListItems)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return domain.ErrListFull
	}
	_, err = r.DB.Exec(ctx, `UPDATE user_lists SET updated_at=now() WHERE id=$1`, listID)
	return err
}
