package main

import (
	"context"
	"io"
	"os"
	"path/filepath"
	"testing"
	"time"

	"traning_ai/backend/internal/mocks"
)

type audioStorage struct {
	*mocks.ObjectStorageMem
	ttl time.Duration
}

func (s *audioStorage) GetPresigned(ctx context.Context, bucket, key string, ttl time.Duration) (string, error) {
	s.ttl = ttl
	return s.ObjectStorageMem.GetPresigned(ctx, bucket, key, ttl)
}

func TestUploadAIAudioStreamsBytesAndPresignsForJobLifetime(t *testing.T) {
	storage := &audioStorage{ObjectStorageMem: mocks.NewObjectStorageMem()}
	file := filepath.Join(t.TempDir(), "audio.wav")
	if err := os.WriteFile(file, []byte("WAV fixture"), 0600); err != nil {
		t.Fatal(err)
	}
	url, err := uploadAIAudio(context.Background(), storage, file, "audio/vid_test.wav")
	if err != nil || url != "https://storage.local/audio/vid_test.wav" || storage.ttl != 2*time.Hour {
		t.Fatalf("bad remote audio reference: %q %v", url, err)
	}
	object, err := storage.GetObject(context.Background(), "raw-videos", "audio/vid_test.wav")
	if err != nil {
		t.Fatal(err)
	}
	defer object.Close()
	data, err := io.ReadAll(object)
	if err != nil || string(data) != "WAV fixture" {
		t.Fatalf("audio changed in transport: %v", err)
	}
	if _, err := uploadAIAudio(context.Background(), storage, file+"missing", "audio/vid_missing.wav"); !os.IsNotExist(err) {
		t.Fatalf("missing audio file error lost: %v", err)
	}
}
