package pg

import (
	"context"
	"os"
	"strings"
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
	assigned, err := os.ReadFile("../../../../infra/postgres/migrations/007_category_assigned_at.sql")
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 2; i++ {
		if _, err := db.Exec(ctx, string(assigned)); err != nil {
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
	// 0.9.0: assignment time recorded on change only, kept on a same-category save, used by sort=category_assigned
	if err := videos.SetCategory(ctx, "vid_b", "cat_news"); err != nil {
		t.Fatal(err)
	}
	assignedB, err := videos.Get(ctx, "vid_b")
	if err != nil || assignedB.CategoryAssignedAt == nil {
		t.Fatalf("assigned_at not recorded: %+v %v", assignedB, err)
	}
	if err := videos.SetCategory(ctx, "vid_b", "cat_news"); err != nil {
		t.Fatal(err)
	}
	if again, err := videos.Get(ctx, "vid_b"); err != nil || !again.CategoryAssignedAt.Equal(*assignedB.CategoryAssignedAt) {
		t.Fatalf("same-category save moved assigned_at: %v", err)
	}
	if a, err := videos.Get(ctx, "vid_a"); err != nil || a.CategoryAssignedAt != nil {
		t.Fatalf("pre-0.9.0 assignment must stay NULL: %v", err)
	}
	sorted, _, err := videos.ListCMS(ctx, domain.CMSVideoFilter{SortAssigned: true, Page: 1, Size: 20})
	if err != nil || len(sorted) != 2 || sorted[0].ID != "vid_b" {
		t.Fatalf("sort=category_assigned: %+v %v", sorted, err)
	}
	if _, err := db.Exec(ctx, `UPDATE videos SET category_id=NULL,category_assigned_at=NULL WHERE id='vid_b'`); err != nil {
		t.Fatal(err)
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
	if err := jobs.SetStatus(ctx, "job_b", domain.JobRunning, true, false); err != nil {
		t.Fatal(err)
	}
	if err := jobs.SetStage(ctx, "job_b", domain.StageHighlightScoring); err != nil {
		t.Fatal(err)
	}
	if err := jobs.RequestCancel(ctx, "job_a"); err != domain.ErrConflict {
		t.Fatalf("completed cancellation accepted: %v", err)
	}
	if err := jobs.RequestCancel(ctx, "job_b"); err != nil {
		t.Fatal(err)
	}
	if err := jobs.SetStatus(ctx, "job_b", domain.JobCompleted, false, true); err != domain.ErrConflict {
		t.Fatalf("cancellation raced past completed guard: %v", err)
	}
	pendingCancel, err := jobs.Get(ctx, "job_b")
	if err != nil || pendingCancel.Status != domain.JobRunning || pendingCancel.CompletedAt != nil {
		t.Fatalf("premature cancellation acknowledgement: %+v %v", pendingCancel, err)
	}
	if err := jobs.SetError(ctx, "job_b", "old error"); err != nil {
		t.Fatal(err)
	}
	if err := jobs.SetStatus(ctx, "job_b", domain.JobFailed, false, true); err != nil {
		t.Fatal(err)
	}
	if err := jobs.SetStatus(ctx, "job_b", domain.JobPending, false, false); err != nil {
		t.Fatal(err)
	}
	job, err = jobs.Get(ctx, "job_b")
	if err != nil || job.ErrorLog != nil || job.CurrentStage != nil || job.Progress != 0 || job.StartedAt != nil || job.CompletedAt != nil || job.ProcessingOptions == nil || job.ProcessingOptions.AutoSubtitleEnabled {
		t.Fatalf("retry reset/preserve snapshot: %+v %v", job, err)
	}
	if err := jobs.SetStatus(ctx, "job_b", domain.JobFailed, false, false); err != nil {
		t.Fatal(err)
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
	catID := "cat_news"
	title := "News edited"
	cl, err := (&ClipRepo{DB: db}).UpdateMeta(ctx, "clp_a", &title, nil, nil, &catID)
	if err != nil || cl.CategoryID == nil || *cl.CategoryID != catID {
		t.Fatalf("clip category not persisted: %+v %v", cl, err)
	}
	reloaded, err := (&ClipRepo{DB: db}).Get(ctx, "clp_a")
	if err != nil || reloaded.CategoryID == nil || *reloaded.CategoryID != catID || reloaded.Title != title {
		t.Fatalf("clip edit reload: %+v %v", reloaded, err)
	}
	clips, err := (&ClipRepo{DB: db}).ListCMS(ctx, nil, nil, "News")
	if err != nil || len(clips) != 1 || clips[0].ViewCount != 1 || clips[0].CreatedByName == nil || clips[0].CategoryName == nil {
		t.Fatalf("clip metadata: %+v %v", clips, err)
	}
	if err := (&ClipRepo{DB: db}).SetStatus(ctx, "clp_deleted", domain.ClipRejected); err != nil {
		t.Fatal(err)
	}
	visible, err := (&ClipRepo{DB: db}).ListCMS(ctx, nil, nil, "")
	if err != nil || len(visible) != 1 {
		t.Fatalf("deleted source still in CMS clip catalog: %+v %v", visible, err)
	}
	// User decision 2026-11-02: a category referenced only by soft-deleted videos (and their clips) is deletable;
	// those references are cleared, live references above still conflict.
	if _, err := db.Exec(ctx, `INSERT INTO categories(id,name) VALUES('cat_deleted_only','Deleted only');UPDATE videos SET category_id='cat_deleted_only' WHERE id='vid_deleted';UPDATE clips SET category_id='cat_deleted_only' WHERE id='clp_deleted'`); err != nil {
		t.Fatal(err)
	}
	if err := cats.Delete(ctx, "cat_deleted_only"); err != nil {
		t.Fatalf("deleted-only category must be deletable: %v", err)
	}
	var videoRef, clipRef *string
	if err := db.QueryRow(ctx, `SELECT (SELECT category_id FROM videos WHERE id='vid_deleted'),(SELECT category_id FROM clips WHERE id='clp_deleted')`).Scan(&videoRef, &clipRef); err != nil || videoRef != nil || clipRef != nil {
		t.Fatalf("soft-deleted references not cleared: %v %v %v", videoRef, clipRef, err)
	}
	if v, err := videos.Get(ctx, "vid_a"); err != nil || v.CategoryID == nil || *v.CategoryID != "cat_news" {
		t.Fatalf("live video reference touched: %+v %v", v, err)
	}
	temporary, err := cats.Create(ctx, "Unused", nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if err := cats.Delete(ctx, temporary.ID); err != nil {
		t.Fatalf("unused delete: %v", err)
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

func TestCMSFreshSchemaAndSeed(t *testing.T) {
	db := integrationDB(t)
	ctx := context.Background()
	schema, err := os.ReadFile("../../../../infra/postgres/init/001_schema.sql")
	if err != nil {
		t.Fatal(err)
	}
	// Every CREATE targets session-local TEMP tables; existing extensions are read-only IF NOT EXISTS.
	if _, err := db.Exec(ctx, strings.ReplaceAll(string(schema), "CREATE TABLE ", "CREATE TEMP TABLE ")); err != nil {
		t.Fatal(err)
	}
	seed, err := os.ReadFile("../../../../infra/postgres/init/002_seed.sql")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec(ctx, string(seed)); err != nil {
		t.Fatal(err)
	}
	settings, err := (&SettingsRepo{DB: db}).Get(ctx)
	if err != nil || !settings.CategorySuggestionEnabled || settings.CategoryKeywordEnabled {
		t.Fatalf("fresh category defaults: %+v %v", settings, err)
	}
	repo := &VideoRepo{DB: db}
	v := &domain.Video{ID: "vid_fresh", Title: "Fresh", RawFilePath: "raw-videos/fresh.mp4", Status: domain.VideoUploaded}
	if err := repo.Create(ctx, v); err != nil {
		t.Fatal(err)
	}
	stored, err := repo.Get(ctx, v.ID)
	if err != nil || stored.EditorialPriority != "normal" {
		t.Fatalf("fresh schema read: %+v %v", stored, err)
	}
	job, err := (&JobRepo{DB: db}).Create(ctx, v.ID)
	if err != nil || job.ProcessingOptions != nil || len(job.SkippedStages) != 0 {
		t.Fatalf("fresh job defaults: %+v %v", job, err)
	}
}
