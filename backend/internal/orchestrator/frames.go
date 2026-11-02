package orchestrator

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/ports"
)

// IndexVideoFrames is shared by live ingest and the missing-vector backfill; it never changes metadata.
func IndexVideoFrames(ctx context.Context, ai ports.AIClient, storage ports.ObjectStorage, vectors ports.VectorStore, id, dir string) (*domain.VisionResult, error) {
	paths, err := filepath.Glob(filepath.Join(dir, "*.jpg"))
	if err != nil {
		return nil, err
	}
	if len(paths) == 0 {
		return nil, fmt.Errorf("No frames for %s", id)
	}
	res, err := ai.VisionV2(ctx, paths)
	if err != nil {
		return nil, err
	}
	if len(res.SiameseVectors) != len(paths) {
		return nil, fmt.Errorf("Frame/vector count mismatch")
	}
	items := make([]domain.FrameEmbedding, 0, len(paths))
	for i, path := range paths {
		file, err := os.Open(path)
		if err != nil {
			return nil, err
		}
		info, err := file.Stat()
		if err != nil {
			file.Close()
			return nil, err
		}
		key := fmt.Sprintf("%s/%08d.jpg", id, i)
		stored, err := storage.PutStream(ctx, "thumbnails", key, file, info.Size(), "image/jpeg")
		file.Close()
		if err != nil {
			return nil, err
		}
		items = append(items, domain.FrameEmbedding{VideoID: id, Timestamp: float64(i), Vector: res.SiameseVectors[i], ThumbnailURL: stored})
	}
	if err := vectors.UpsertFrames(ctx, id, items); err != nil {
		return nil, err
	}
	return res, nil
}
