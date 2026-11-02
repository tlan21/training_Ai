// frame-backfill indexes only processed videos missing vectors; it never rewrites existing vectors or metadata.
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
	"traning_ai/backend/internal/adapters/aihttp"
	"traning_ai/backend/internal/adapters/milvus"
	"traning_ai/backend/internal/adapters/minio"
	"traning_ai/backend/internal/adapters/pg"
	"traning_ai/backend/internal/config"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/orchestrator"
)

func main() {
	apply := flag.Bool("apply", false, "Index missing processed videos (default: inventory only)")
	flag.Parse()
	if err := run(*apply); err != nil {
		log.Fatal(err)
	}
}
func run(apply bool) error {
	cfg := config.Load()
	ctx, cancel := context.WithTimeout(context.Background(), 6*time.Hour)
	defer cancel()
	db, err := pg.New(ctx, cfg.PostgresDSN)
	if err != nil {
		return err
	}
	defer db.Close()
	vectors := milvus.NewFrames("http://"+cfg.MilvusHost+":"+cfg.MilvusPort, nil)
	before, err := vectors.FrameInventory(ctx)
	if err != nil {
		return err
	}
	storage, err := minio.New(ctx, cfg.MinioEndpoint, cfg.MinioPublicEndpoint, cfg.MinioAccess, cfg.MinioSecret)
	if err != nil {
		return err
	}
	ai := aihttp.New(cfg.AIBaseURL, cfg.AIServiceKey)
	if _, err = ai.Health(ctx); err != nil {
		return err
	}
	repo := &pg.VideoRepo{DB: db}
	status := "processed"
	missing := []domain.Video{}
	for page := 1; ; page++ {
		items, total, err := repo.List(ctx, &status, page, 100)
		if err != nil {
			return err
		}
		for _, v := range items {
			if before[v.ID] == 0 {
				missing = append(missing, v)
			}
		}
		if page*100 >= total {
			break
		}
	}
	report := map[string]any{"apply": apply, "before": before, "missing": []string{}, "backfilled": []string{}}
	ids := []string{}
	for _, v := range missing {
		ids = append(ids, v.ID)
	}
	report["missing"] = ids
	_ = json.NewEncoder(os.Stdout).Encode(report)
	if !apply {
		return nil
	}
	done := []string{}
	for _, v := range missing {
		if err := backfill(ctx, v, ai, storage, vectors); err != nil {
			return fmt.Errorf("backfill %s (prior data preserved): %w", v.ID, err)
		}
		done = append(done, v.ID)
	}
	after, err := vectors.FrameInventory(ctx)
	if err != nil {
		return err
	}
	for id, n := range before {
		if after[id] != n {
			return fmt.Errorf("Existing vector count changed: %s", id)
		}
	}
	report["after"], report["backfilled"] = after, done
	return json.NewEncoder(os.Stdout).Encode(report)
}
func backfill(ctx context.Context, v domain.Video, ai *aihttp.Client, storage *minio.Client, vectors *milvus.FrameStore) error {
	dir, err := os.MkdirTemp("", "frame-backfill-")
	if err != nil {
		return err
	}
	defer os.RemoveAll(dir)
	object, err := storage.GetObject(ctx, "raw-videos", strings.TrimPrefix(v.RawFilePath, "raw-videos/"))
	if err != nil {
		return err
	}
	source := filepath.Join(dir, "source.mp4")
	file, err := os.Create(source)
	if err != nil {
		object.Close()
		return err
	}
	_, copyErr := io.Copy(file, object)
	closeErr := file.Close()
	object.Close()
	if copyErr != nil {
		return copyErr
	}
	if closeErr != nil {
		return closeErr
	}
	if output, err := exec.CommandContext(ctx, "ffmpeg", "-v", "error", "-nostdin", "-i", source, "-vf", "fps=1,scale=224:224", "-q:v", "2", "-start_number", "0", filepath.Join(dir, "%08d.jpg")).CombinedOutput(); err != nil {
		return fmt.Errorf("extract frames: %v %s", err, output)
	}
	_, err = orchestrator.IndexVideoFrames(ctx, ai, storage, vectors, v.ID, dir)
	return err
}
