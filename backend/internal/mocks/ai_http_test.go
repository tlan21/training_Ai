package mocks_test

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"traning_ai/backend/internal/adapters/aihttp"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

func TestAIHTTPClientRoundTrip(t *testing.T) {
	server := httptest.NewServer(mocks.NewAIHTTP("sk-local-test"))
	defer server.Close()
	client := aihttp.New(server.URL, "sk-local-test")
	ctx := context.Background()
	if _, err := client.Health(ctx); err == nil {
		t.Fatal("default client accepted mock as real inference")
	}
	client.AllowStub = true
	health, err := client.Health(ctx)
	if err != nil || !health.StubMode || len(health.ModelsLoaded) != 0 {
		t.Fatalf("mock health: %+v %v", health, err)
	}
	frame := filepath.Join(t.TempDir(), "frame.jpg")
	if err := os.WriteFile(frame, []byte("mock frame fixture"), 0600); err != nil {
		t.Fatal(err)
	}
	vision, err := client.Vision(ctx, []string{frame, frame})
	if err != nil || vision.CategorySuggestion != "bong_da" || len(vision.Embeddings256) != 2 || len(vision.Embeddings256[0]) != 256 {
		t.Fatalf("vision: %+v %v", vision, err)
	}
	asr, err := client.ASR(ctx, "audio.wav", "vi")
	if err != nil || len(asr.Segments) != 1 || !strings.Contains(asr.FullTranscript, "MOCK_ONLY") {
		t.Fatalf("asr: %+v %v", asr, err)
	}
	highlight, err := client.Highlight(ctx, "vid_test", vision.Embeddings256, [][]float32{make([]float32, 64), make([]float32, 64)})
	if err != nil || len(highlight.TimelineScores) != 2 || highlight.RecommendedClips[0].EndTime != 2 {
		t.Fatalf("highlight: %+v %v", highlight, err)
	}
	search, err := client.Search(ctx, "fixture.png", 5, 0.75)
	if err != nil || len(search.Hits) != 0 {
		t.Fatalf("search: %+v %v", search, err)
	}
	recommendation, err := client.Recommendation(ctx, "usr_test", 10, nil)
	if err == nil || err.(*domain.DomainError).Status != 503 || len(recommendation.Hits) != 0 {
		t.Fatalf("recommendation: %+v %v", recommendation, err)
	}
	summary, err := client.Summarize(ctx, "transcript", 150)
	if err != nil || !strings.Contains(summary.Text, "MOCK_ONLY") {
		t.Fatalf("summary: %+v %v", summary, err)
	}
}

func TestAIHTTPValidationAndEnvelopes(t *testing.T) {
	handler := mocks.NewAIHTTP("sk-local-test")
	for _, tc := range []struct {
		path, body, key, code string
		status                int
	}{
		{"/v1/vision/completions", `{}`, "", "UNAUTHORIZED", 401},
		{"/v1/vision/completions", `{}`, "wrong", "UNAUTHORIZED", 401},
		{"/v1/vision/completions", `{}`, "sk-local-test", "VALIDATION_ERROR", 422},
		{"/v1/asr/completions", `{"audio_url":"a","language":"en"}`, "sk-local-test", "VALIDATION_ERROR", 422},
		{"/v1/highlight/completions", `{"video_id":"vid_test","features":{"vision_embeddings":[[1]],"audio_spectrogram_features":[[1]]}}`, "sk-local-test", "AI_UNAVAILABLE", 503},
		{"/v1/search/completions", `{"image":"a","top_k":101}`, "sk-local-test", "VALIDATION_ERROR", 422},
		{"/v1/search/completions", `{"image":"a","threshold":1.1}`, "sk-local-test", "VALIDATION_ERROR", 422},
		{"/v1/recommendation/completions", `{"user_id":"usr_test","limit":0}`, "sk-local-test", "VALIDATION_ERROR", 422},
		{"/v1/completions", `{"prompt":"a","max_tokens":0}`, "sk-local-test", "VALIDATION_ERROR", 422},
		{"/missing", `{}`, "sk-local-test", "HTTP_ERROR", 404},
	} {
		t.Run(tc.path+tc.body+tc.key, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodPost, tc.path, bytes.NewBufferString(tc.body))
			req.Header.Set("Content-Type", "application/json")
			if tc.key != "" {
				req.Header.Set("Authorization", "Bearer "+tc.key)
			}
			w := httptest.NewRecorder()
			handler.ServeHTTP(w, req)
			var envelope struct {
				Error struct{ Code, Message string }
			}
			if err := json.Unmarshal(w.Body.Bytes(), &envelope); err != nil || w.Code != tc.status || envelope.Error.Code != tc.code || envelope.Error.Message == "" {
				t.Fatalf("got %d %s, want %d %s: %v", w.Code, w.Body, tc.status, tc.code, err)
			}
		})
	}
}
