package orchestrator

import (
	"context"
	"os"
	"path/filepath"
	"testing"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

func TestIndexVideoFramesPersistsBothStoresAndIsIdempotent(t *testing.T) {
	ctx := context.Background()
	dir := t.TempDir()
	_ = os.WriteFile(filepath.Join(dir, "00000000.jpg"), []byte("jpeg0"), 0600)
	_ = os.WriteFile(filepath.Join(dir, "00000001.jpg"), []byte("jpeg1"), 0600)
	ai := &mocks.AIClientMem{VisionFn: func(paths []string) (*domain.VisionResult, error) {
		if len(paths) != 2 {
			t.Fatal(paths)
		}
		return &domain.VisionResult{SiameseVectors: [][]float32{make([]float32, 128), make([]float32, 128)}}, nil
	}}
	storage, vec := mocks.NewObjectStorageMem(), mocks.NewVectorStoreMem()
	for range 2 {
		if _, err := IndexVideoFrames(ctx, ai, storage, vec, "vid_owned", dir); err != nil {
			t.Fatal(err)
		}
	}
	if len(storage.Objs) != 2 || string(storage.Objs["thumbnails/vid_owned/00000001.jpg"]) != "jpeg1" || len(vec.Frames["vid_owned"]) != 2 || vec.Frames["vid_owned"][1].Timestamp != 1 {
		t.Fatal("backend persistence mismatch")
	}
}
