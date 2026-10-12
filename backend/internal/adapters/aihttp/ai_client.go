package aihttp

import (
	"context"
	"net/http"
	"time"

	"traning_ai/backend/internal/domain"
)

// ponytail: minimal http client — real :8001 calls when T2.1.7 needs AI
type Client struct {
	baseURL string
	apiKey  string
	http    *http.Client
}

func New(baseURL, apiKey string) *Client {
	return &Client{
		baseURL: baseURL,
		apiKey:  apiKey,
		http:    &http.Client{Timeout: 30 * time.Second},
	}
}

func (c *Client) Vision(_ context.Context, _ []string) (*domain.VisionResult, error) {
	return nil, domain.ErrAIUnavailable
}
func (c *Client) ASR(_ context.Context, _, _ string) (*domain.ASRResult, error) {
	return nil, domain.ErrAIUnavailable
}
func (c *Client) Highlight(_ context.Context, _ string, _ [][]float32, _ [][]float32) (*domain.HighlightResult, error) {
	return nil, domain.ErrAIUnavailable
}
func (c *Client) Search(_ context.Context, _ string, _ int, _ float64) (*domain.SearchResult, error) {
	return nil, domain.ErrAIUnavailable
}
func (c *Client) Recommendation(_ context.Context, _ string, _ int, _ map[string]string) (*domain.RecResult, error) {
	return nil, domain.ErrAIUnavailable
}
func (c *Client) Summarize(_ context.Context, _ string, _ int) (*domain.SummaryResult, error) {
	return nil, domain.ErrAIUnavailable
}
func (c *Client) Health(_ context.Context) (*domain.AIHealth, error) {
	return nil, domain.ErrAIUnavailable
}
