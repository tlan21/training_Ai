package pg

import (
	"context"
	"errors"
	"os"
	"strconv"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"traning_ai/backend/internal/domain"
)

func integrationDB(t *testing.T) *pgxpool.Pool {
	t.Helper()
	dsn := os.Getenv("TEST_POSTGRES_DSN")
	if dsn == "" {
		t.Skip("set TEST_POSTGRES_DSN to test real PostgreSQL")
	}
	cfg, err := pgxpool.ParseConfig(dsn)
	if err != nil {
		t.Fatal(err)
	}
	cfg.MaxConns = 1
	db, err := pgxpool.NewWithConfig(context.Background(), cfg)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(db.Close)
	return db
}

func TestInteractionRepository_RealPersistencePaginationAndPrivacy(t *testing.T) {
	db := integrationDB(t)
	ctx := context.Background()
	suffix := strconv.FormatInt(time.Now().UnixNano(), 36)
	user, other := "usr_int_"+suffix, "usr_other_"+suffix
	video, hiddenVideo := "vid_int_"+suffix, "vid_hidden_"+suffix
	clip1, clip2, draft := "clp_one_"+suffix, "clp_two_"+suffix, "clp_draft_"+suffix
	exec := func(sql string, args ...any) {
		t.Helper()
		if _, err := db.Exec(ctx, sql, args...); err != nil {
			t.Fatal(err)
		}
	}
	t.Cleanup(func() {
		_, _ = db.Exec(ctx, `DELETE FROM videos WHERE id=ANY($1::text[])`, []string{video, hiddenVideo})
		_, _ = db.Exec(ctx, `DELETE FROM users WHERE id=ANY($1::text[])`, []string{user, other})
	})
	exec(`INSERT INTO users(id,username,email,password_hash) VALUES($1,$1,$1,'test'),($2,$2,$2,'test')`, user, other)
	exec(`INSERT INTO videos(id,title,raw_file_path,duration_seconds,status) VALUES($1,'test','test',10,'processed'),($2,'hidden','test',10,'uploaded')`, video, hiddenVideo)
	exec(`INSERT INTO clips(id,video_id,title,start_time,end_time,average_score,status)
		VALUES($1,$4,'one',0,5,80,'published'),($2,$4,'two',5,10,80,'published'),($3,$4,'draft',0,5,80,'draft')`, clip1, clip2, draft, video)
	repo := &InteractionRepo{DB: db}
	add := func(uid, clip, kind string, seconds int) {
		t.Helper()
		i := &domain.Interaction{UserID: uid, VideoID: video, ClipID: &clip, InteractionType: domain.InteractionType(kind), DurationWatched: seconds}
		if err := repo.Add(ctx, i); err != nil || i.ID == 0 || i.CreatedAt.IsZero() {
			t.Fatalf("interaction not saved: %v", err)
		}
	}
	add(user, clip1, "watch_time", 10)
	add(user, clip1, "watch_time", 2)
	add(user, clip2, "click", 0)
	add(user, clip2, "watch_time", 5)
	add(user, clip1, "like", 0)
	add(user, clip1, "like", 0)
	add(user, clip2, "like", 0)
	add(other, clip1, "watch_time", 99)
	// A fresh repository must read the same stored data, not process-local memory.
	repo = &InteractionRepo{DB: db}
	history, next, err := repo.History(ctx, user, nil, 1)
	if err != nil || len(history) != 1 || history[0].Clip.ID != clip2 || history[0].DurationWatched != 5 || next == nil {
		t.Fatalf("history first page: %+v %v %v", history, next, err)
	}
	history, next, err = repo.History(ctx, user, next, 1)
	if err != nil || len(history) != 1 || history[0].Clip.ID != clip1 || history[0].DurationWatched != 12 || next != nil {
		t.Fatalf("history second page: %+v %v %v", history, next, err)
	}
	likes, next, err := repo.Likes(ctx, user, nil, 1)
	if err != nil || len(likes) != 1 || likes[0].ID != clip2 || next == nil {
		t.Fatalf("likes first page: %+v %v %v", likes, next, err)
	}
	likes, next, err = repo.Likes(ctx, user, next, 1)
	if err != nil || len(likes) != 1 || likes[0].ID != clip1 || next != nil {
		t.Fatalf("likes dedup/pagination: %+v %v %v", likes, next, err)
	}
	likes, _, err = repo.Likes(ctx, other, nil, 10)
	if err != nil || len(likes) != 0 {
		t.Fatalf("likes crossed user boundary: %+v %v", likes, err)
	}
	for _, i := range []*domain.Interaction{
		{UserID: user, VideoID: video, ClipID: &draft, InteractionType: domain.InteractLike},
		{UserID: user, VideoID: hiddenVideo, ClipID: &clip1, InteractionType: domain.InteractLike},
	} {
		if err := repo.Add(ctx, i); !errors.Is(err, domain.ErrVideoNotFound) {
			t.Fatalf("unavailable content accepted: %v", err)
		}
	}
	var count int
	if err := db.QueryRow(ctx, `SELECT count(*) FROM user_interactions WHERE user_id=$1`, user).Scan(&count); err != nil || count != 7 {
		t.Fatalf("events not persisted: %d %v", count, err)
	}
	exec(`UPDATE users SET role='admin' WHERE id=$1`, other)
	if err := repo.Add(ctx, &domain.Interaction{UserID: other, VideoID: video, InteractionType: domain.InteractClick}); !errors.Is(err, domain.ErrVideoNotFound) {
		t.Fatalf("non-client event accepted: %v", err)
	}
	exec(`UPDATE videos SET deleted_at=now() WHERE id=$1`, video)
	if err := repo.Add(ctx, &domain.Interaction{UserID: user, VideoID: video, InteractionType: domain.InteractClick}); !errors.Is(err, domain.ErrVideoNotFound) {
		t.Fatalf("deleted event accepted: %v", err)
	}
	exec(`UPDATE videos SET deleted_at=NULL WHERE id=$1`, video)
	ids, err := repo.PopularityTop(ctx, 100)
	if err != nil {
		t.Fatal(err)
	}
	found := false
	for _, id := range ids {
		found = found || id == video
	}
	if !found {
		t.Fatal("recent interactions missing from popularity")
	}
	exec(`UPDATE clips SET status='rejected' WHERE video_id=$1`, video)
	ids, err = repo.PopularityTop(ctx, 100)
	if err != nil {
		t.Fatal(err)
	}
	for _, id := range ids {
		if id == video {
			t.Fatal("video without published clips included in popularity")
		}
	}
	exec(`UPDATE clips SET status='published' WHERE id=ANY($1::text[])`, []string{clip1, clip2})
	exec(`UPDATE user_interactions SET created_at=now()-interval '8 days' WHERE video_id=$1`, video)
	ids, err = repo.PopularityTop(ctx, 100)
	if err != nil {
		t.Fatal(err)
	}
	for _, id := range ids {
		if id == video {
			t.Fatal("expired interactions included in seven-day popularity")
		}
	}
	exec(`UPDATE clips SET status='rejected' WHERE id=$1`, clip1)
	history, _, err = repo.History(ctx, user, nil, 10)
	if err != nil || len(history) != 1 || history[0].Clip.ID != clip2 {
		t.Fatalf("hidden clip leaked: %+v %v", history, err)
	}
	exec(`UPDATE videos SET status='deleted' WHERE id=$1`, video)
	likes, _, err = repo.Likes(ctx, user, nil, 10)
	if err != nil || len(likes) != 0 {
		t.Fatalf("deleted video leaked: %+v %v", likes, err)
	}
}

func TestInteractionRepository_RejectsInvalidInputs(t *testing.T) {
	repo := &InteractionRepo{}
	for _, value := range []string{"bad", "-1", "0", "9223372036854775808"} {
		if _, _, err := repo.History(context.Background(), "usr_test", &value, 10); !errors.Is(err, domain.ErrValidation) {
			t.Fatalf("invalid cursor %q accepted: %v", value, err)
		}
	}
	if err := repo.Add(context.Background(), &domain.Interaction{DurationWatched: -1}); !errors.Is(err, domain.ErrValidation) {
		t.Fatal("negative duration accepted")
	}
}
