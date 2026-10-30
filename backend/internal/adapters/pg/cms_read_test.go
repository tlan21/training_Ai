package pg

import (
	"context"
	"os"
	"testing"
	"time"
	"traning_ai/backend/internal/domain"
)

func TestCMSOperationsRealPersistence(t *testing.T) {
	db := integrationDB(t)
	ctx := context.Background()
	// TEMP shadows keep migration and writes away from every product row and sequence.
	for _, table := range []string{"users", "categories", "videos", "clips", "video_processing_jobs", "user_interactions", "system_settings"} {
		if _, err := db.Exec(ctx, "CREATE TEMP TABLE "+table+" (LIKE public."+table+" INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES)"); err != nil {
			t.Fatal(err)
		}
	}
	migration, err := os.ReadFile("../../../../infra/postgres/migrations/006_cms_operations.sql")
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 2; i++ {
		if _, err := db.Exec(ctx, string(migration)); err != nil {
			t.Fatal(err)
		}
	}
	_, err = db.Exec(ctx, `INSERT INTO users(id,username,email,password_hash,role) VALUES('usr_admin','CMS user','cms@test.local','x','admin'),('usr_viewer','Viewer','viewer@test.local','x','client');
 INSERT INTO categories(id,name,keywords) VALUES('cat_news','News',ARRAY['news']);
 INSERT INTO videos(id,title,raw_file_path,status,uploaded_by,category_id,created_at,duration_seconds) VALUES
 ('vid_a','Literal_100% news','','processed','usr_admin','cat_news','2026-10-02T10:00:00Z',8),
 ('vid_b','LiteralX100Z news','','failed','usr_admin',NULL,'2026-10-03T10:00:00Z',8),
 ('vid_deleted','Literal_100% deleted','','deleted','usr_admin','cat_news','2026-10-04T10:00:00Z',8);
 INSERT INTO video_processing_jobs(id,video_id,status,started_at,completed_at) VALUES
 ('job_a','vid_a','completed','2026-10-02T10:00:00Z','2026-10-02T10:00:20Z'),('job_b','vid_b','failed',NULL,NULL),('job_deleted','vid_deleted','completed','2026-10-02T10:00:00Z','2026-10-02T10:00:40Z');
 INSERT INTO clips(id,video_id,title,start_time,end_time,average_score,status,created_by) VALUES('clp_a','vid_a','News clip',0,5,60,'published','usr_admin'),('clp_deleted','vid_deleted','Hidden clip',0,5,70,'published','usr_admin');
 INSERT INTO user_interactions(id,user_id,video_id,clip_id,interaction_type,created_at) VALUES
 (1,'usr_viewer','vid_a','clp_a','click','2026-10-02T12:00:00Z'),(2,'usr_viewer','vid_a','clp_a','watch_time',now()),(3,'usr_admin','vid_a','clp_a','click','2026-10-02T12:00:00Z');`)
	if err != nil {
		t.Fatal(err)
	}
	videos := &VideoRepo{DB: db}
	from, _ := time.Parse("2006-01-02", "2026-10-02")
	to := from.AddDate(0, 0, 1)
	f := domain.CMSVideoFilter{Query: "_100%", CategoryID: "cat_news", From: &from, To: &to, Page: 1, Size: 20}
	items, total, err := videos.ListCMS(ctx, f)
	if err != nil || total != 1 || len(items) != 1 || items[0].ID != "vid_a" || items[0].UploadedByName == nil || *items[0].UploadedByName != "CMS user" {
		t.Fatalf("filter/hydration: %+v %d %v", items, total, err)
	}
	f = domain.CMSVideoFilter{Page: 1, Size: 1}
	items, total, err = videos.ListCMS(ctx, f)
	if err != nil || total != 2 || len(items) != 1 || items[0].ID != "vid_b" {
		t.Fatalf("pagination/default deleted: %+v %d %v", items, total, err)
	}
	f.IncludeDeleted = true
	_, total, err = videos.ListCMS(ctx, f)
	if err != nil || total != 3 {
		t.Fatalf("deleted opt-in: %d %v", total, err)
	}
	priority := "high"
	if _, err := videos.UpdateMetadata(ctx, "vid_a", "Literal_100% news", "", []string{}, &priority); err != nil {
		t.Fatal(err)
	}
	v, err := videos.Get(ctx, "vid_a")
	if err != nil || v.EditorialPriority != "high" {
		t.Fatalf("priority: %+v %v", v, err)
	}
	jobs := &JobRepo{DB: db}
	options := domain.ProcessingOptions{AutoHighlightEnabled: true, AutoSubtitleEnabled: false}
	if err := jobs.SetProcessingOptions(ctx, "job_b", options); err != nil {
		t.Fatal(err)
	}
	job, err := jobs.Get(ctx, "job_b")
	if err != nil || job.ProcessingOptions == nil || job.ProcessingOptions.AutoSubtitleEnabled || len(job.SkippedStages) != 2 {
		t.Fatalf("snapshot: %+v %v", job, err)
	}
	cats := &CategoryRepo{DB: db}
	list, err := cats.List(ctx)
	if err != nil || len(list) != 1 || list[0].VideoCount != 1 {
		t.Fatalf("category true counts: %+v %v", list, err)
	}
	if _, err := cats.Update(ctx, "cat_news", "News", nil, []string{"edited"}); err != nil {
		t.Fatal(err)
	}
	c, err := cats.Update(ctx, "cat_news", "News", nil, nil)
	if err != nil || len(c.Keywords) != 1 || c.Keywords[0] != "edited" {
		t.Fatalf("preserve keywords: %+v %v", c, err)
	}
	if _, err := db.Exec(ctx, `ALTER TABLE videos ADD FOREIGN KEY(category_id) REFERENCES categories(id)`); err != nil {
		t.Fatal(err)
	}
	if err := cats.Delete(ctx, "cat_news"); err != domain.ErrConflict {
		t.Fatalf("referenced category deletion: %v", err)
	}
	clips, err := (&ClipRepo{DB: db}).ListCMS(ctx, nil, nil, "News")
	if err != nil || len(clips) != 1 || clips[0].ViewCount != 1 || clips[0].CreatedByName == nil || clips[0].CategoryName == nil {
		t.Fatalf("clip metadata: %+v %v", clips, err)
	}
	month := time.Date(2026, 10, 1, 0, 0, 0, 0, time.UTC)
	m, err := (&CMSRepo{DB: db}).Overview(ctx, month)
	if err != nil {
		t.Fatal(err)
	}
	if m.TotalVideos != 2 || m.DeletedVideos != 1 || m.ProcessedVideos != 1 || m.FailedVideos != 1 || m.PublishedClips != 1 || m.TotalUsers != 2 || m.ActiveUsers != 1 || m.ViewsMonth != 1 || m.TotalViews != 1 || m.CompletedJobs != 1 || m.FailedJobs != 1 || m.SuccessRate == nil || *m.SuccessRate != 50 || m.AverageProcessingSeconds == nil || *m.AverageProcessingSeconds != 20 || len(m.DailyProcessing) != 31 || m.DailyProcessing[1].Count != 1 {
		t.Fatalf("metrics: %+v", m)
	}
	var count int
	if err := db.QueryRow(ctx, `SELECT count(*) FROM videos`).Scan(&count); err != nil || count != 3 {
		t.Fatalf("rows changed: %d %v", count, err)
	}
}
