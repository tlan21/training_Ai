package pg

import (
	"context"
	"os"
	"strconv"
	"testing"
	"time"
	"traning_ai/backend/internal/domain"
)

func TestJobRepository_RealTransitions(t *testing.T) {
	dsn := os.Getenv("TEST_POSTGRES_DSN")
	if dsn == "" {
		t.Skip("set TEST_POSTGRES_DSN to test real PostgreSQL")
	}
	ctx := context.Background()
	db, err := New(ctx, dsn)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	id := "vid_test_" + strconv.FormatInt(time.Now().UnixNano(), 36)
	defer db.Exec(ctx, `DELETE FROM videos WHERE id=$1`, id)
	videos := &VideoRepo{DB: db}
	jobs := &JobRepo{DB: db}
	if err := videos.Create(ctx, &domain.Video{ID: id, Title: "test", RawFilePath: "raw-videos/test.mp4", Status: domain.VideoUploaded}); err != nil {
		t.Fatal(err)
	}
	job, err := jobs.Create(ctx, id)
	if err != nil {
		t.Fatal(err)
	}
	if err := jobs.SetStatus(ctx, job.ID, domain.JobRunning, true, false); err != nil {
		t.Fatalf("SetStatus: %v", err)
	}
	if err := jobs.SetStage(ctx, job.ID, domain.StageSplittingFrames); err != nil {
		t.Fatal(err)
	}
	stored, err := jobs.GetByVideo(ctx, id)
	if err != nil {
		t.Fatalf("GetByVideo with non-null stage: %v", err)
	}
	if stored.Status != domain.JobRunning || stored.StartedAt == nil || stored.CurrentStage == nil {
		t.Fatalf("lost transition: %+v", stored)
	}
	if err := jobs.SetStatus(ctx, job.ID, domain.JobCompleted, false, true); err != nil {
		t.Fatal(err)
	}
	stored, err = jobs.Get(ctx, job.ID)
	if err != nil || stored.Status != domain.JobCompleted || stored.CompletedAt == nil {
		t.Fatalf("lost completion: %+v, %v", stored, err)
	}
}
