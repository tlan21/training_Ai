package mocks

import (
	"context"
	"testing"

	"traning_ai/backend/internal/domain"
)

func TestVideoRepoMem_CRUD(t *testing.T) {
	r := NewVideoRepoMem()
	v := &domain.Video{ID: "vid_1", Title: "T", Status: domain.VideoUploaded}
	if err := r.Create(context.Background(), v); err != nil {
		t.Fatal(err)
	}
	got, _ := r.Get(context.Background(), "vid_1")
	if got.Title != "T" {
		t.Fatal("mismatch")
	}
	_ = r.SetStatus(context.Background(), "vid_1", domain.VideoProcessed)
	got2, _ := r.GetProcessed(context.Background(), "vid_1")
	if got2 == nil || got2.Status != domain.VideoProcessed {
		t.Fatal("setstatus/getprocessed")
	}
	_ = r.SoftDelete(context.Background(), "vid_1")
	got3, _ := r.Get(context.Background(), "vid_1")
	if got3.Status != domain.VideoDeleted {
		t.Fatal("softdelete")
	}
}

func TestJobRepoMem_Stage(t *testing.T) {
	r := NewJobRepoMem()
	j, _ := r.Create(context.Background(), "vid_1")
	if err := r.SetStage(context.Background(), j.ID, domain.StageSplittingFrames); err != nil {
		t.Fatal(err)
	}
	got, _ := r.Get(context.Background(), j.ID)
	if got.CurrentStage == nil || *got.CurrentStage != domain.StageSplittingFrames {
		t.Fatal("stage")
	}
	if got.Progress != 20 {
		t.Fatalf("progress %d want 20", got.Progress)
	}
}

func TestAIClientMem_Stub(t *testing.T) {
	c := &AIClientMem{}
	r, err := c.Vision(context.Background(), nil)
	if err != nil || r == nil {
		t.Fatal("vision stub")
	}
	h, _ := c.Health(context.Background())
	if h == nil || len(h.ModelsLoaded) == 0 {
		t.Fatal("health stub")
	}
}
