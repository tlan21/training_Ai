package cutter

import (
	"context"
	"encoding/json"
	"os"
	"testing"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

func TestCutter_HandleOne_Happy(t *testing.T) {
	clipRepo := mocks.NewClipRepoMem()
	videoRepo := mocks.NewVideoRepoMem()
	store := mocks.NewObjectStorageMem()
	bus := &captureBus{EventBusMem: mocks.NewEventBusMem()}

	vid := &domain.Video{ID: "vid_1", RawFilePath: "raw-videos/vid_1.mp4", DurationSeconds: 600, Status: domain.VideoProcessed}
	_ = videoRepo.Create(context.Background(), vid)
	_ = clipRepo.Create(context.Background(), &domain.Clip{ID: "clp_1", VideoID: "vid_1", Title: "c", StartTime: 2, EndTime: 12, Status: domain.ClipProcessing})

	// seed raw object so fetch works
	store.Objs["raw-videos/vid_1.mp4"] = []byte("fake-mp4")
	svc := New(clipRepo, videoRepo, store, bus, "raw-videos", "clips")
	svc.tmpDir = os.TempDir()
	svc.WithExecFn(func(ctx context.Context, in, out string, start, end float64) error {
		if start != 2 || end != 12 {
			t.Fatalf("bad range %v %v", start, end)
		}
		// simulate ffmpeg output
		return os.WriteFile(out, []byte("cut-mp4"), 0644)
	})

	payload, _ := json.Marshal(cutRequested{ClipID: "clp_1", VideoID: "vid_1", Start: 2, End: 12})
	if err := svc.HandleOne(context.Background(), payload); err != nil {
		t.Fatalf("HandleOne: %v", err)
	}
	cl, _ := clipRepo.Get(context.Background(), "clp_1")
	if cl.ClipFilePath == nil || *cl.ClipFilePath == "" {
		t.Fatal("clip_file_path not set")
	}
	if len(bus.Published) == 0 || bus.Published[len(bus.Published)-1].Topic != "clip.cut.completed" {
		t.Fatal("expected clip.cut.completed publish")
	}
}

func TestCutter_HandleOne_BadRange(t *testing.T) {
	svc := New(mocks.NewClipRepoMem(), mocks.NewVideoRepoMem(), mocks.NewObjectStorageMem(), mocks.NewEventBusMem(), "raw-videos", "clips")
	payload, _ := json.Marshal(cutRequested{ClipID: "clp_1", VideoID: "vid_1", Start: 10, End: 5})
	if err := svc.HandleOne(context.Background(), payload); err == nil {
		t.Fatal("expected error for end<=start")
	}
}

// helpers

type captureBus struct {
	*mocks.EventBusMem
	Published []struct {
		Topic, Key string
		Raw        []byte
	}
}

func (c *captureBus) Publish(ctx context.Context, topic, key string, payload any) error {
	raw, _ := json.Marshal(payload)
	c.Published = append(c.Published, struct {
		Topic, Key string
		Raw        []byte
	}{Topic: topic, Key: key, Raw: raw})
	return c.EventBusMem.Publish(ctx, topic, key, payload)
}
