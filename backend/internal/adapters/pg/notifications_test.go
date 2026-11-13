package pg

import (
	"context"
	"os"
	"strconv"
	"testing"
	"time"
)

func TestNotificationRepository_RealFanOutRecipientsAndInbox(t *testing.T) {
	db := integrationDB(t)
	ctx := context.Background()
	migration, err := os.ReadFile("../../../../infra/postgres/migrations/009_user_notifications.sql")
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 2; i++ { // additive + repeatable
		if _, err := db.Exec(ctx, string(migration)); err != nil {
			t.Fatal(err)
		}
	}
	s := strconv.FormatInt(time.Now().UnixNano(), 36)
	catA, catB := "cat_na_"+s, "cat_nb_"+s
	fan, other, noPref, admin := "usr_nf_"+s, "usr_no_"+s, "usr_nn_"+s, "usr_na_"+s
	videoA, videoNone := "vid_na_"+s, "vid_nn_"+s
	clipA, clipNone, draft := "clp_na_"+s, "clp_nn_"+s, "clp_nd_"+s
	exec := func(sql string, args ...any) {
		t.Helper()
		if _, err := db.Exec(ctx, sql, args...); err != nil {
			t.Fatal(err)
		}
	}
	t.Cleanup(func() {
		_, _ = db.Exec(ctx, `DELETE FROM videos WHERE id=ANY($1::text[])`, []string{videoA, videoNone})
		_, _ = db.Exec(ctx, `DELETE FROM users WHERE id=ANY($1::text[])`, []string{fan, other, noPref, admin})
		_, _ = db.Exec(ctx, `DELETE FROM categories WHERE id=ANY($1::text[])`, []string{catA, catB})
	})
	exec(`INSERT INTO categories(id,name) VALUES($1,$1),($2,$2)`, catA, catB)
	exec(`INSERT INTO users(id,username,email,password_hash,role) VALUES($1,$1,$1,'t','client'),($2,$2,$2,'t','client'),($3,$3,$3,'t','client'),($4,$4,$4,'t','admin')`,
		fan, other, noPref, admin)
	exec(`INSERT INTO user_preferences(user_id,category_id) VALUES($1,$3),($2,$4),($5,$3)`, fan, other, catA, catB, admin)
	exec(`INSERT INTO videos(id,title,raw_file_path,duration_seconds,status,category_id) VALUES($1,'a','t',10,'processed',$3),($2,'n','t',10,'processed',NULL)`,
		videoA, videoNone, catA)
	exec(`INSERT INTO clips(id,video_id,title,start_time,end_time,average_score,status) VALUES
		($1,$4,'Bàn thắng A',0,5,80,'published'),($2,$5,'Không danh mục',0,5,80,'published'),($3,$4,'Nháp',0,5,80,'draft')`,
		clipA, clipNone, draft, videoA, videoNone)
	repo := &NotificationRepo{DB: db}
	count := func(uid string) int {
		t.Helper()
		var n int
		if err := db.QueryRow(ctx, `SELECT count(*) FROM user_notifications WHERE user_id=$1`, uid).Scan(&n); err != nil {
			t.Fatal(err)
		}
		return n
	}

	// Category A (from the video): only the client who chose A — not the other client, not the admin with A.
	if _, err := repo.FanOutClipPublished(ctx, clipA); err != nil {
		t.Fatal(err)
	}
	if count(fan) != 1 || count(other) != 0 || count(noPref) != 0 || count(admin) != 0 {
		t.Fatalf("category recipients: fan %d other %d noPref %d admin %d", count(fan), count(other), count(noPref), count(admin))
	}
	// Redelivered event: no duplicate.
	if n, err := repo.FanOutClipPublished(ctx, clipA); err != nil || n != 0 || count(fan) != 1 {
		t.Fatalf("redelivery duplicated: new %d total %d %v", n, count(fan), err)
	}
	// No category anywhere: every client user (still not the admin).
	if _, err := repo.FanOutClipPublished(ctx, clipNone); err != nil {
		t.Fatal(err)
	}
	if count(fan) != 2 || count(other) != 1 || count(noPref) != 1 || count(admin) != 0 {
		t.Fatalf("no-category recipients: fan %d other %d noPref %d admin %d", count(fan), count(other), count(noPref), count(admin))
	}
	// A clip that is not public creates nothing.
	if n, err := repo.FanOutClipPublished(ctx, draft); err != nil || n != 0 {
		t.Fatalf("draft fanned out: %d %v", n, err)
	}

	items, next, unread, err := repo.List(ctx, fan, nil, 1)
	if err != nil || len(items) != 1 || items[0].ClipID != clipNone || next == nil || unread != 2 || items[0].Read || items[0].Title != "Không danh mục" {
		t.Fatalf("inbox page 1: %+v %v %d %v", items, next, unread, err)
	}
	if items, next, _, _ = repo.List(ctx, fan, next, 1); len(items) != 1 || items[0].ClipID != clipA || next != nil {
		t.Fatalf("inbox page 2: %+v %v", items, next)
	}
	if err := repo.MarkRead(ctx, other, []int64{items[0].ID}); err != nil { // another user's id: ignored
		t.Fatal(err)
	}
	if err := repo.MarkRead(ctx, fan, []int64{items[0].ID}); err != nil {
		t.Fatal(err)
	}
	if _, _, unread, _ = repo.List(ctx, fan, nil, 10); unread != 1 {
		t.Fatalf("mark one: unread %d", unread)
	}
	if err := repo.MarkRead(ctx, fan, nil); err != nil {
		t.Fatal(err)
	}
	if all, _, unread, _ := repo.List(ctx, fan, nil, 10); unread != 0 || len(all) != 2 || !all[0].Read || !all[1].Read {
		t.Fatalf("mark all: %+v %d", all, unread)
	}
	// A clip taken down later disappears from the inbox (no dead links).
	exec(`UPDATE clips SET status='rejected' WHERE id=$1`, clipNone)
	if all, _, _, _ := repo.List(ctx, other, nil, 10); len(all) != 0 {
		t.Fatalf("unpublished clip still listed: %+v", all)
	}
}
