package pg

import (
	"context"
	"errors"
	"os"
	"strconv"
	"testing"
	"time"

	"traning_ai/backend/internal/domain"
)

func TestLibraryRepository_RealStateHistoryAndLists(t *testing.T) {
	db := integrationDB(t)
	ctx := context.Background()
	migration, err := os.ReadFile("../../../../infra/postgres/migrations/008_user_library.sql")
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 2; i++ { // additive + repeatable
		if _, err := db.Exec(ctx, string(migration)); err != nil {
			t.Fatal(err)
		}
	}
	suffix := strconv.FormatInt(time.Now().UnixNano(), 36)
	user, other := "usr_lib_"+suffix, "usr_lib2_"+suffix
	video := "vid_lib_" + suffix
	c1, c2, c3, draft := "clp_l1_"+suffix, "clp_l2_"+suffix, "clp_l3_"+suffix, "clp_ld_"+suffix
	exec := func(sql string, args ...any) {
		t.Helper()
		if _, err := db.Exec(ctx, sql, args...); err != nil {
			t.Fatal(err)
		}
	}
	t.Cleanup(func() {
		_, _ = db.Exec(ctx, `DELETE FROM videos WHERE id=$1`, video)
		_, _ = db.Exec(ctx, `DELETE FROM users WHERE id=ANY($1::text[])`, []string{user, other})
	})
	exec(`INSERT INTO users(id,username,email,password_hash) VALUES($1,$1,$1,'test'),($2,$2,$2,'test')`, user, other)
	exec(`INSERT INTO videos(id,title,raw_file_path,duration_seconds,status) VALUES($1,'lib','test',30,'processed')`, video)
	exec(`INSERT INTO clips(id,video_id,title,start_time,end_time,average_score,status,thumbnail_url) VALUES
		($1,$5,'one',0,5,80,'published','thumbnails/a.jpg'),($2,$5,'two',5,10,80,'published','thumbnails/b.jpg'),
		($3,$5,'three',10,15,80,'published','thumbnails/c.jpg'),($4,$5,'draft',0,5,80,'draft',NULL)`, c1, c2, c3, draft, video)
	repo := &LibraryRepo{DB: db}

	// marks: idempotent, newest first, hidden clips 404, per user
	created, vid, err := repo.SetMark(ctx, user, c1, domain.MarkSave, true)
	if err != nil || !created || vid != video {
		t.Fatalf("first save: %v %v %v", created, vid, err)
	}
	if created, _, err = repo.SetMark(ctx, user, c1, domain.MarkSave, true); err != nil || created {
		t.Fatalf("repeat save must be a no-op: %v %v", created, err)
	}
	if _, _, err = repo.SetMark(ctx, user, c2, domain.MarkSave, true); err != nil {
		t.Fatal(err)
	}
	if _, _, err = repo.SetMark(ctx, user, draft, domain.MarkSave, true); !errors.Is(err, domain.ErrClipNotFound) {
		t.Fatalf("draft clip saved: %v", err)
	}
	page, next, err := repo.Marks(ctx, user, domain.MarkSave, nil, 1)
	if err != nil || len(page) != 1 || page[0].ID != c2 || next == nil {
		t.Fatalf("saved page 1: %+v %v %v", page, next, err)
	}
	page, next, err = repo.Marks(ctx, user, domain.MarkSave, next, 1)
	if err != nil || len(page) != 1 || page[0].ID != c1 || next != nil {
		t.Fatalf("saved page 2: %+v %v %v", page, next, err)
	}
	if _, _, err = repo.Marks(ctx, user, domain.MarkSave, ptr("garbage"), 1); !errors.Is(err, domain.ErrValidation) {
		t.Fatalf("bad cursor: %v", err)
	}
	if page, _, _ = repo.Marks(ctx, other, domain.MarkSave, nil, 10); len(page) != 0 {
		t.Fatalf("saved crossed users: %+v", page)
	}
	if _, _, err = repo.SetMark(ctx, user, c1, domain.MarkSave, false); err != nil {
		t.Fatal(err)
	}
	if page, _, _ = repo.Marks(ctx, user, domain.MarkSave, nil, 10); len(page) != 1 || page[0].ID != c2 {
		t.Fatalf("unsave: %+v", page)
	}

	// history hide / clear: events stay, rewatch shows again
	events := &InteractionRepo{DB: db}
	watch := func(clip string) {
		t.Helper()
		if err := events.Add(ctx, &domain.Interaction{UserID: user, VideoID: video, ClipID: &clip, InteractionType: domain.InteractClick}); err != nil {
			t.Fatal(err)
		}
	}
	watch(c1)
	watch(c2)
	if err := repo.HideHistory(ctx, user, c1); err != nil {
		t.Fatal(err)
	}
	if err := repo.HideHistory(ctx, user, "clp_missing_"+suffix); err != nil {
		t.Fatalf("unknown clip hide must be a no-op: %v", err)
	}
	if h, _, _ := events.History(ctx, user, nil, 10); len(h) != 1 || h[0].Clip.ID != c2 {
		t.Fatalf("hidden clip still listed: %+v", h)
	}
	time.Sleep(5 * time.Millisecond)
	watch(c1)
	if h, _, _ := events.History(ctx, user, nil, 10); len(h) != 2 || h[0].Clip.ID != c1 {
		t.Fatalf("rewatch after hide must show again: %+v", h)
	}
	if err := repo.ClearHistory(ctx, user); err != nil {
		t.Fatal(err)
	}
	if h, _, _ := events.History(ctx, user, nil, 10); len(h) != 0 {
		t.Fatalf("clear left items: %+v", h)
	}
	var kept int
	if err := db.QueryRow(ctx, `SELECT count(*) FROM user_interactions WHERE user_id=$1`, user).Scan(&kept); err != nil || kept != 3 {
		t.Fatalf("events must be kept (user decision): %d %v", kept, err)
	}

	// lists: create, case-insensitive duplicate, items, ownership, states, rename, delete
	l, err := repo.CreateList(ctx, user, "Bóng đá")
	if err != nil || l.ItemCount != 0 || l.CoverThumbnailURL != nil {
		t.Fatalf("create: %+v %v", l, err)
	}
	if _, err = repo.CreateList(ctx, user, "BÓNG ĐÁ"); !errors.Is(err, domain.ErrListNameTaken) {
		t.Fatalf("duplicate name: %v", err)
	}
	if _, err = repo.CreateList(ctx, other, "Bóng đá"); err != nil {
		t.Fatalf("same name for another user must be allowed: %v", err)
	}
	for _, clip := range []string{c1, c2, c3, c3} {
		if err := repo.SetListItem(ctx, user, l.ID, clip, true); err != nil {
			t.Fatal(err)
		}
	}
	if err := repo.SetListItem(ctx, user, l.ID, draft, true); !errors.Is(err, domain.ErrClipNotFound) {
		t.Fatalf("draft added: %v", err)
	}
	if err := repo.SetListItem(ctx, other, l.ID, c1, true); !errors.Is(err, domain.ErrListNotFound) {
		t.Fatalf("other user wrote my list: %v", err)
	}
	if _, _, err := repo.ListItems(ctx, other, l.ID, nil, 10); !errors.Is(err, domain.ErrListNotFound) {
		t.Fatalf("other user read my list: %v", err)
	}
	items, next, err := repo.ListItems(ctx, user, l.ID, nil, 2)
	if err != nil || len(items) != 2 || items[0].ID != c3 || next == nil {
		t.Fatalf("items page 1: %+v %v %v", items, next, err)
	}
	if items, next, _ = repo.ListItems(ctx, user, l.ID, next, 2); len(items) != 1 || items[0].ID != c1 || next != nil {
		t.Fatalf("items page 2: %+v %v", items, next)
	}
	lists, err := repo.Lists(ctx, user)
	if err != nil || len(lists) != 1 || lists[0].ItemCount != 3 || lists[0].CoverThumbnailURL == nil || *lists[0].CoverThumbnailURL != "thumbnails/c.jpg" {
		t.Fatalf("list summary: %+v %v", lists, err)
	}
	states, err := repo.ClipStates(ctx, user, []string{c2, draft, c1, "clp_missing_" + suffix})
	if err != nil || len(states) != 2 || states[0].ClipID != c2 || !states[0].Saved || len(states[0].ListIDs) != 1 || states[1].Saved {
		t.Fatalf("states: %+v %v", states, err)
	}
	if err := repo.SetListItem(ctx, user, l.ID, c3, false); err != nil {
		t.Fatal(err)
	}
	renamed, err := repo.RenameList(ctx, user, l.ID, "Highlight hay")
	if err != nil || renamed.Name != "Highlight hay" || renamed.ItemCount != 2 {
		t.Fatalf("rename: %+v %v", renamed, err)
	}
	if _, err = repo.RenameList(ctx, other, l.ID, "x"); !errors.Is(err, domain.ErrListNotFound) {
		t.Fatalf("other user renamed my list: %v", err)
	}
	if err := repo.DeleteList(ctx, user, l.ID); err != nil {
		t.Fatal(err)
	}
	if err := repo.DeleteList(ctx, user, l.ID); !errors.Is(err, domain.ErrListNotFound) {
		t.Fatalf("delete twice: %v", err)
	}
	var clipsLeft int
	if err := db.QueryRow(ctx, `SELECT count(*) FROM clips WHERE video_id=$1`, video).Scan(&clipsLeft); err != nil || clipsLeft != 4 {
		t.Fatalf("deleting a list must not delete clips: %d %v", clipsLeft, err)
	}

	// list cap (50 per user)
	exec(`INSERT INTO user_lists(user_id,name) SELECT $1,'cap '||g FROM generate_series(1,50) g`, user)
	if _, err = repo.CreateList(ctx, user, "one too many"); !errors.Is(err, domain.ErrListLimit) {
		t.Fatalf("list cap: %v", err)
	}
}

func ptr(s string) *string { return &s }
