package pg

import (
	"context"
	"os"
	"strconv"
	"testing"
	"time"
)

func TestCMSAlertsRepo_RealSeenAndUncategorized(t *testing.T) {
	db := integrationDB(t)
	ctx := context.Background()
	migration, err := os.ReadFile("../../../../infra/postgres/migrations/010_cms_alert_seen.sql")
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 2; i++ {
		if _, err := db.Exec(ctx, string(migration)); err != nil {
			t.Fatal(err)
		}
	}
	s := strconv.FormatInt(time.Now().UnixNano(), 36)
	admin, editor := "usr_al_"+s, "usr_ae_"+s
	open, done, gone := "vid_al_"+s, "vid_ad_"+s, "vid_ag_"+s
	t.Cleanup(func() {
		_, _ = db.Exec(ctx, `DELETE FROM videos WHERE id=ANY($1::text[])`, []string{open, done, gone})
		_, _ = db.Exec(ctx, `DELETE FROM users WHERE id=ANY($1::text[])`, []string{admin, editor})
	})
	if _, err := db.Exec(ctx, `INSERT INTO users(id,username,email,password_hash,role) VALUES($1,$1,$1,'t','admin'),($2,$2,$2,'t','editor')`, admin, editor); err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec(ctx, `INSERT INTO videos(id,title,raw_file_path,duration_seconds,status,category_id,deleted_at) VALUES
		($1,'a','t',1,'processed',NULL,NULL),($2,'b','t',1,'processed',(SELECT id FROM categories LIMIT 1),NULL),($3,'c','t',1,'processed',NULL,now())`, open, done, gone); err != nil {
		t.Fatal(err)
	}
	repo := &CMSAlertsRepo{DB: db}
	if f, u, at, err := repo.Seen(ctx, admin); err != nil || f != 0 || u != 0 || at != nil {
		t.Fatalf("never seen: %d %d %v %v", f, u, at, err)
	}
	if err := repo.MarkSeen(ctx, admin, 4, 2); err != nil {
		t.Fatal(err)
	}
	if err := repo.MarkSeen(ctx, admin, 5, 1); err != nil { // upsert, latest wins
		t.Fatal(err)
	}
	if f, u, at, err := repo.Seen(ctx, admin); err != nil || f != 5 || u != 1 || at == nil {
		t.Fatalf("seen: %d %d %v %v", f, u, at, err)
	}
	if f, _, _, _ := repo.Seen(ctx, editor); f != 0 {
		t.Fatalf("seen crossed accounts: %d", f)
	}
	ids, err := repo.UncategorizedProcessed(ctx)
	if err != nil {
		t.Fatal(err)
	}
	found := map[string]bool{}
	for _, id := range ids {
		found[id] = true
	}
	if !found[open] || found[done] || found[gone] {
		t.Fatalf("uncategorized list wrong: open %v done %v deleted %v", found[open], found[done], found[gone])
	}
}
