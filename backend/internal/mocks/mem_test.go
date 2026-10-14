package mocks

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"strings"
	"testing"

	"traning_ai/backend/internal/domain"
)

func TestEventBusMem_DeliversPayloadAndNestedEvent(t *testing.T) {
	ctx := context.Background()
	bus := NewEventBusMem()
	var got string
	_ = bus.Consume(ctx, "next", "test", func(_ context.Context, raw []byte) error {
		return json.Unmarshal(raw, &got)
	})
	_ = bus.Consume(ctx, "uploaded", "test", func(ctx context.Context, raw []byte) error {
		var payload map[string]string
		if err := json.Unmarshal(raw, &payload); err != nil {
			return err
		}
		return bus.Publish(ctx, "next", "vid_test", payload["video_id"])
	})
	if err := bus.Publish(ctx, "uploaded", "vid_test", map[string]string{"video_id": "vid_test"}); err != nil {
		t.Fatal(err)
	}
	if got != "vid_test" || len(bus.Events) != 2 {
		t.Fatalf("lost payload/event: %q, %d", got, len(bus.Events))
	}
	want := errors.New("consumer failed")
	_ = bus.Consume(ctx, "failed", "test", func(context.Context, []byte) error { return want })
	if err := bus.Publish(ctx, "failed", "", nil); !errors.Is(err, want) {
		t.Fatalf("lost consumer error: %v", err)
	}
	if err := bus.Publish(ctx, "invalid", "", make(chan int)); err == nil {
		t.Fatal("unserializable event accepted")
	}
}

func TestObjectStorageMem_RoundTripAndMissing(t *testing.T) {
	ctx := context.Background()
	store := NewObjectStorageMem()
	if _, err := store.PutStream(ctx, "raw-videos", "vid_test.mp4", strings.NewReader("video bytes"), 11, "video/mp4"); err != nil {
		t.Fatal(err)
	}
	raw, err := store.GetObject(ctx, "raw-videos", "vid_test.mp4")
	if err != nil {
		t.Fatal(err)
	}
	defer raw.Close()
	data, err := io.ReadAll(raw)
	if err != nil || string(data) != "video bytes" {
		t.Fatalf("lost stored data: %q, %v", data, err)
	}
	_ = store.Delete(ctx, "raw-videos", "vid_test.mp4")
	if _, err := store.GetObject(ctx, "raw-videos", "vid_test.mp4"); !errors.Is(err, domain.ErrNotFound) {
		t.Fatalf("deleted file still accessible: %v", err)
	}
}

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
