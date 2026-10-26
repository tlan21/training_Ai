package aihttp

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
	"traning_ai/backend/internal/domain"
)

type Client struct {
	baseURL, apiKey string
	http            *http.Client
	AllowStub       bool // Development only; real inference remains required by default.
}

func New(baseURL, apiKey string) *Client {
	return &Client{baseURL: baseURL, apiKey: apiKey, http: &http.Client{Timeout: 30 * time.Minute}}
}
func (c *Client) request(ctx context.Context, path string, input, output any) error {
	method := http.MethodGet
	var body bytes.Buffer
	if input != nil {
		method = http.MethodPost
		if err := json.NewEncoder(&body).Encode(input); err != nil {
			return err
		}
	}
	req, err := http.NewRequestWithContext(ctx, method, c.baseURL+path, &body)
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+c.apiKey)
	req.Header.Set("Content-Type", "application/json")
	response, err := c.http.Do(req)
	if err != nil {
		return err
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		var envelope struct {
			Error struct {
				Message string `json:"message"`
			} `json:"error"`
		}
		_ = json.NewDecoder(response.Body).Decode(&envelope)
		status := response.StatusCode
		if status >= 500 {
			status = http.StatusServiceUnavailable
		}
		return domain.NewError("AI_UNAVAILABLE", fmt.Sprintf("%s: HTTP %d: %s", path, response.StatusCode, envelope.Error.Message), status)
	}
	return json.NewDecoder(response.Body).Decode(output)
}
func (c *Client) Vision(ctx context.Context, paths []string) (*domain.VisionResult, error) {
	if len(paths) == 1 {
		frames, err := filepath.Glob(filepath.Join(paths[0], "*.jpg"))
		if err != nil {
			return nil, err
		}
		if len(frames) > 0 {
			paths = frames
		}
	}
	var result domain.VisionResult
	keyframes := make([]string, len(paths))
	for i, path := range paths {
		data, err := os.ReadFile(path)
		if err != nil {
			return nil, fmt.Errorf("read vision frame: %w", err)
		}
		keyframes[i] = "data:" + http.DetectContentType(data) + ";base64," + base64.StdEncoding.EncodeToString(data)
	}
	input := map[string]any{"keyframes": keyframes}
	if len(paths) > 0 {
		videoID := filepath.Base(filepath.Dir(paths[0]))
		if strings.HasPrefix(videoID, "vid_") {
			input["video_id"] = videoID
		}
	}
	err := c.request(ctx, "/v1/vision/completions", input, &result)
	return &result, err
}
func (c *Client) ASR(ctx context.Context, audioURL, language string) (*domain.ASRResult, error) {
	var result struct {
		FullTranscript string `json:"full_transcript"`
		Segments       []struct {
			ID         int     `json:"id"`
			StartTime  float64 `json:"start_time"`
			EndTime    float64 `json:"end_time"`
			Text       string  `json:"text"`
			Confidence float64 `json:"confidence"`
			Warning    *string `json:"warning"`
		} `json:"segments"`
	}
	if err := c.request(ctx, "/v1/asr/completions", map[string]string{"audio_url": audioURL, "language": language}, &result); err != nil {
		return nil, err
	}
	converted := &domain.ASRResult{FullTranscript: result.FullTranscript}
	for _, s := range result.Segments {
		converted.Segments = append(converted.Segments, domain.Segment{SegmentIndex: s.ID, StartTime: s.StartTime, EndTime: s.EndTime, Text: s.Text, Confidence: s.Confidence, Warning: s.Warning})
	}
	return converted, nil
}
func (c *Client) Highlight(ctx context.Context, videoID string, vision, audio [][]float32) (*domain.HighlightResult, error) {
	var result domain.HighlightResult
	err := c.request(ctx, "/v1/highlight/completions", map[string]any{"video_id": videoID, "features": map[string]any{"vision_embeddings": vision, "audio_spectrogram_features": audio}}, &result)
	return &result, err
}
func (c *Client) Search(ctx context.Context, image string, topK int, threshold float64) (*domain.SearchResult, error) {
	ctx, cancel := context.WithTimeout(ctx, 1800*time.Millisecond)
	defer cancel()
	var result struct {
		Hits []domain.FrameHit `json:"results"`
	}
	err := c.request(ctx, "/v1/search/completions", map[string]any{"image": image, "top_k": topK, "threshold": threshold}, &result)
	if err != nil {
		var de *domain.DomainError
		if errors.As(err, &de) && de.Status == 422 {
			err = domain.NewError("VALIDATION_ERROR", de.Message, 422)
		} else if !errors.As(err, &de) {
			err = domain.NewError("AI_UNAVAILABLE", "Visual search unavailable: "+err.Error(), 503)
		}
	}
	return &domain.SearchResult{Hits: result.Hits}, err
}
func (c *Client) Recommendation(ctx context.Context, userID string, limit int, meta map[string]string) (*domain.RecResult, error) {
	if meta == nil {
		meta = map[string]string{}
	}
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	var result struct {
		Hits               []domain.VideoHit `json:"recommendations"`
		RecommendationMode string            `json:"recommendation_mode"`
	}
	err := c.request(ctx, "/v1/recommendation/completions", map[string]any{"user_id": userID, "limit": limit, "context": meta}, &result)
	return &domain.RecResult{Hits: result.Hits, RecommendationMode: result.RecommendationMode}, err
}
func (c *Client) Summarize(ctx context.Context, prompt string, maxTokens int) (*domain.SummaryResult, error) {
	var result struct {
		Choices []struct {
			Text string `json:"text"`
		} `json:"choices"`
	}
	err := c.request(ctx, "/v1/completions", map[string]any{"prompt": prompt, "max_tokens": maxTokens, "temperature": 0.7}, &result)
	if err != nil {
		return nil, err
	}
	if len(result.Choices) == 0 {
		return nil, fmt.Errorf("AI completion returned no choices")
	}
	return &domain.SummaryResult{Text: result.Choices[0].Text}, nil
}
func (c *Client) Health(ctx context.Context) (*domain.AIHealth, error) {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	var result domain.AIHealth
	if err := c.request(ctx, "/health", nil, &result); err != nil {
		return nil, err
	}
	if result.StubMode && c.AllowStub {
		return &result, nil
	}
	if result.StubMode || len(result.ModelsLoaded) != 6 {
		return nil, fmt.Errorf("inference is not running all six real checkpoints")
	}
	return &result, nil
}
