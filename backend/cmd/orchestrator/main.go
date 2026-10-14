package main

import (
	"context"
	"log"

	"traning_ai/backend/internal/config"
	"traning_ai/backend/internal/mocks"
	"traning_ai/backend/internal/orchestrator"
)

func main() {
	cfg := config.Load()

	videoRepo := mocks.NewVideoRepoMem()
	jobRepo := mocks.NewJobRepoMem()
	ana := mocks.NewAnalysisStoreMem()
	sub := mocks.NewSubtitleStoreMem()
	ai := &mocks.AIClientMem{}
	bus := mocks.NewEventBusMem()

	r := orchestrator.New(videoRepo, jobRepo, ana, sub, ai, bus)
	log.Printf("orchestrator ready kafka=%s (stub bus — wire kafka-go when needed)", cfg.KafkaBrokers)

	_ = bus.Consume(context.Background(), "video.uploaded", "orch-uploaded", r.HandleUploaded)
	_ = bus.Consume(context.Background(), "video.preprocessed", "orch-preprocessed", r.HandlePreprocessed)

	select {}
}
