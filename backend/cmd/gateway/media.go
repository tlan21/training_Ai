package main

import (
	"context"
	"os"
	"time"

	"traning_ai/backend/internal/ports"
)

// The host AI process cannot read Docker scratch paths; use the existing MinIO HTTP contract.
func uploadAIAudio(ctx context.Context, storage ports.ObjectStorage, path, key string) (string, error) {
	file, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer file.Close()
	info, err := file.Stat()
	if err != nil {
		return "", err
	}
	if _, err := storage.PutStream(ctx, "raw-videos", key, file, info.Size(), "audio/wav"); err != nil {
		return "", err
	}
	return storage.GetPresigned(ctx, "raw-videos", key, 2*time.Hour)
}
