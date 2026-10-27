package pg

import (
	"context"
	"fmt"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"traning_ai/backend/internal/domain"
)

// Session-local shadow tables exercise real SQL without touching product rows or sequences.
func contentPageDB(t *testing.T) *pgxpool.Pool {
	t.Helper()
	db := integrationDB(t)
	ctx := context.Background()
	for _, table := range []string{"videos", "clips", "user_interactions"} {
		if _, err := db.Exec(ctx, "CREATE TEMP TABLE "+table+" (LIKE public."+table+" INCLUDING DEFAULTS)"); err != nil {
			t.Fatal(err)
		}
	}
	base := time.Now().UTC().Add(-time.Hour).Truncate(time.Microsecond)
	for i := 0; i < 12; i++ {
		id, cat := fmt.Sprintf("vid_page_%02d", i), "cat_a"
		if i%2 == 1 {
			cat = "cat_b"
		}
		if _, err := db.Exec(ctx, `INSERT INTO videos(id,title,raw_file_path,duration_seconds,status,category_id,created_at) VALUES($1,$1,'test',8,'processed',$2,$3)`, id, cat, base); err != nil {
			t.Fatal(err)
		}
		for j := 0; j < 2; j++ {
			clip := fmt.Sprintf("clp_page_%02d_%d", i, j)
			if _, err := db.Exec(ctx, `INSERT INTO clips(id,video_id,title,start_time,end_time,average_score,status,created_at) VALUES($1,$2,$1,0,5,80,'published',$3)`, clip, id, base); err != nil {
				t.Fatal(err)
			}
		}
	}
	if _, err := db.Exec(ctx, `INSERT INTO user_interactions(id,user_id,video_id,interaction_type,created_at)
		SELECT n,'usr_test','vid_page_00','click',$1::timestamptz FROM generate_series(1,3) n`, base); err != nil {
		t.Fatal(err)
	}
	return db
}

func TestContentPages_RealFeedSnapshotPrivacyAndColdTail(t *testing.T) {
	db := contentPageDB(t)
	ctx := context.Background()
	repo := &ClipRepo{DB: db}
	items, next, err := repo.ListPopularPage(ctx, "", 3)
	if err != nil || len(items) != 3 || next == nil || items[0].VideoID != "vid_page_00" || items[1].VideoID != "vid_page_00" {
		t.Fatalf("first page %+v %v %v", items, next, err)
	}
	p, err := domain.ParseContentCursor(*next, "feed", 3)
	if err != nil {
		t.Fatal(err)
	}
	exec := func(sql string, args ...any) {
		t.Helper()
		if _, err := db.Exec(ctx, sql, args...); err != nil {
			t.Fatal(err)
		}
	}
	// Removing an already-seen row must not offset/skip the following row.
	exec(`UPDATE clips SET status='rejected' WHERE id=$1`, items[0].ID)
	exec(`UPDATE clips SET status='rejected' WHERE id='clp_page_06_0'`)
	exec(`UPDATE videos SET deleted_at=now() WHERE id='vid_page_07'`)
	exec(`UPDATE clips SET title='updated current title' WHERE id='clp_page_03_0'`)
	exec(`INSERT INTO user_interactions(id,user_id,video_id,interaction_type,created_at)
		SELECT n,'usr_test','vid_page_01','click',$1 FROM generate_series(100,150) n`, p.Snapshot.Add(time.Second))
	exec(`INSERT INTO clips(id,video_id,title,start_time,end_time,average_score,status,created_at) VALUES('clp_new','vid_page_01','new',0,5,80,'published',$1)`, p.Snapshot.Add(time.Second))
	seen := map[string]bool{}
	updated := false
	for _, c := range items {
		seen[c.ID] = true
	}
	for page := 0; next != nil && page < 20; page++ {
		items, next, err = repo.ListPopularPage(ctx, *next, 4)
		if err != nil || len(items) > 4 {
			t.Fatal(items, err)
		}
		for _, c := range items {
			if seen[c.ID] || c.ID == "clp_new" || c.ID == "clp_page_06_0" || c.VideoID == "vid_page_07" {
				t.Fatal("duplicate/new/private row", c.ID)
			}
			seen[c.ID] = true
			if c.ID == "clp_page_03_0" {
				updated = c.Title == "updated current title"
			}
		}
	}
	if next != nil || len(seen) != 21 || !updated {
		t.Fatalf("incomplete traversal count%d next%v updated%v", len(seen), next, updated)
	}
	if _, _, err := repo.ListPopularPage(ctx, "bad!", 3); err != domain.ErrValidation {
		t.Fatal("invalid cursor accepted", err)
	}
	t.Log("24 original clips traversed; unseen hidden/deleted3 excluded, seen-row deletion/new50interactions/newclip did not shift cursor; cold tail/current metadata PASS")
}

func TestContentPages_RealCatalogCategorySnapshotAndExhaustion(t *testing.T) {
	for _, order := range []string{"newest", "trending"} {
		t.Run(order, func(t *testing.T) {
			db := contentPageDB(t)
			ctx := context.Background()
			repo := &VideoRepo{DB: db}
			items, next, err := repo.ListPublicPage(ctx, "cat_a", order, "", 2)
			if err != nil || len(items) != 2 || next == nil {
				t.Fatal(items, next, err)
			}
			if order == "trending" && items[0].ID != "vid_page_00" {
				t.Fatal("seven-day rank ignored")
			}
			if order == "newest" && items[0].ID != "vid_page_10" {
				t.Fatal("stable ID tie ignored")
			}
			p, err := domain.ParseContentCursor(*next, "videos/"+order+"/cat_a", 2)
			if err != nil {
				t.Fatal(err)
			}
			for _, filter := range []struct{ cat, sort string }{{"cat_b", order}, {"cat_a", map[string]string{"newest": "trending", "trending": "newest"}[order]}} {
				if _, _, err := repo.ListPublicPage(ctx, filter.cat, filter.sort, *next, 2); err != domain.ErrValidation {
					t.Fatal("cross-filter cursor accepted", err)
				}
			}
			if _, err := db.Exec(ctx, `UPDATE videos SET status='deleted' WHERE id=$1`, items[0].ID); err != nil {
				t.Fatal(err)
			}
			if _, err := db.Exec(ctx, `INSERT INTO videos(id,title,raw_file_path,duration_seconds,status,category_id,created_at) VALUES('vid_new','new','test',8,'processed','cat_a',$1)`, p.Snapshot.Add(time.Second)); err != nil {
				t.Fatal(err)
			}
			if _, err := db.Exec(ctx, `INSERT INTO user_interactions(id,user_id,video_id,interaction_type,created_at)
			SELECT n,'usr_test','vid_page_02','click',$1 FROM generate_series(100,150) n`, p.Snapshot.Add(time.Second)); err != nil {
				t.Fatal(err)
			}
			seen := map[string]bool{}
			for _, v := range items {
				seen[v.ID] = true
			}
			for page := 0; next != nil && page < 10; page++ {
				items, next, err = repo.ListPublicPage(ctx, "cat_a", order, *next, 2)
				if err != nil {
					t.Fatal(err)
				}
				for _, v := range items {
					if seen[v.ID] || v.ID == "vid_new" || v.CategoryID == nil || *v.CategoryID != "cat_a" {
						t.Fatal("duplicate/new/wrong-category", v.ID)
					}
					seen[v.ID] = true
				}
			}
			if next != nil || len(seen) != 6 {
				t.Fatalf("traversal count%d next%v", len(seen), next)
			}
			if _, _, err := repo.ListPublicPage(ctx, "cat_a", "invalid", "", 2); err != domain.ErrValidation {
				t.Fatal("invalid sort accepted")
			}
			t.Log("category6 rows, stable tied ordering, snapshot after new interaction/video, deletion of seen anchor, changed-filter422 and exhaustion PASS")
		})
	}
}
