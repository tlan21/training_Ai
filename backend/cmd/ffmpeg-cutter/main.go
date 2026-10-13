package main

import (
	"context"
	"log"

	"traning_ai/backend/internal/config"
	"traning_ai/backend/internal/cutter"
	"traning_ai/backend/internal/mocks"
)

func main() {
	cfg := config.Load()

	// T2.4: mem mocks; T2.1.7 real adapters (kafka/minio/pg) thay khi cần.
	videoRepo := mocks.NewVideoRepoMem()
	clipRepo := mocks.NewClipRepoMem()
	store := mocks.NewObjectStorageMem()
	bus := mocks.NewEventBusMem()

	svc := cutter.New(clipRepo, videoRepo, store, bus, cfg.MinioBucket, "clips")
	log.Printf("ffmpeg-cutter ready raw=%s clips=clips kafka=%s (stub bus — wire kafka-go when needed)", cfg.MinioBucket, cfg.KafkaBrokers)

	// Stub consume: EventBusMem.Consume is no-op; real bus would block here.
	// Keep process alive so binary is runnable; replace with real kafka consumer when T2.1.7 wired.
	_ = svc
	_ = bus.Consume(context.Background(), "clip.cut.requested", "ffmpeg-cutter", func(ctx context.Context, payload []byte) error {
		return svc.HandleOne(ctx, payload)
	})
	select {}
}
