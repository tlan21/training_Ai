package main

import (
	"context"
	"os"

	"traning_ai/backend/internal/ports"
)

// Backend stores and re-reads audio bytes; inference never receives a storage URL.
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
	return "raw-videos/" + key, nil
}
