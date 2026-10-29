package mocks

import (
	"context"
	"traning_ai/backend/internal/domain"
)

func (m *AIClientMem) VisionV2(ctx context.Context, p []string) (*domain.VisionResult, error) {
	return m.Vision(ctx, p)
}
func (m *AIClientMem) ASRV2(ctx context.Context, p, l string) (*domain.ASRResult, error) {
	return m.ASR(ctx, p, l)
}
func (m *AIClientMem) SearchEmbedding(_ context.Context, image string) ([]float32, error) {
	if m.SearchEmbeddingFn != nil {
		return m.SearchEmbeddingFn(image)
	}
	v := make([]float32, 128)
	v[0] = 1
	return v, nil
}
