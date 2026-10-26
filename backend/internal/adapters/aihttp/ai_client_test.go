package aihttp

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"traning_ai/backend/internal/domain"
)

func TestClient_DecodesRealSchemasAndBearer(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer sk-local-test" {
			t.Error("missing bearer key")
		}
		w.Header().Set("Content-Type", "application/json")
		switch r.URL.Path {
		case "/v1/vision/completions":
			var body struct {
				Keyframes []string `json:"keyframes"`
				VideoID   string   `json:"video_id"`
			}
			if err := json.NewDecoder(r.Body).Decode(&body); err != nil || len(body.Keyframes) != 1 || body.VideoID != "vid_test" || body.Keyframes[0] != "data:text/plain; charset=utf-8;base64,"+base64.StdEncoding.EncodeToString([]byte("frame fixture")) {
				t.Errorf("vision must send file bytes, not a Docker path: %+v %v", body, err)
			}
			_, _ = w.Write([]byte(`{"category_suggestion":"bong_da","embeddings_256":[[0.1,0.2]]}`))
		case "/v1/asr/completions":
			_, _ = w.Write([]byte(`{"full_transcript":"xin chào","segments":[{"id":3,"start_time":1.5,"end_time":2.5,"text":"xin chào","confidence":0.8}]}`))
		case "/v1/highlight/completions":
			_, _ = w.Write([]byte(`{"timeline_scores":[{"second":0,"score":82.5}],"recommended_clips":[{"start_time":0,"end_time":3,"average_score":82.5}]}`))
		case "/health":
			_, _ = w.Write([]byte(`{"stub_mode":false,"models_loaded":["vit","siamese","asr_ctc","highlight_fusion","minigpt","two_tower"],"device":"cpu"}`))
		default:
			t.Errorf("unexpected request %s", r.URL.Path)
		}
	}))
	defer server.Close()
	client := New(server.URL, "sk-local-test")
	ctx := context.Background()
	directory := filepath.Join(t.TempDir(), "vid_test")
	if err := os.Mkdir(directory, 0700); err != nil {
		t.Fatal(err)
	}
	frame := filepath.Join(directory, "00000000.jpg")
	if err := os.WriteFile(frame, []byte("frame fixture"), 0600); err != nil {
		t.Fatal(err)
	}
	vision, err := client.Vision(ctx, []string{directory})
	if err != nil || vision.CategorySuggestion != "bong_da" || len(vision.Embeddings256) != 1 {
		t.Fatalf("vision: %+v, %v", vision, err)
	}
	asr, err := client.ASR(ctx, "a.wav", "vi")
	if err != nil || asr.FullTranscript != "xin chào" || asr.Segments[0].SegmentIndex != 3 || asr.Segments[0].StartTime != 1.5 {
		t.Fatalf("asr: %+v, %v", asr, err)
	}
	highlight, err := client.Highlight(ctx, "vid_test", vision.Embeddings256, [][]float32{{1}})
	if err != nil || highlight.TimelineScores[0].Score != 82.5 || highlight.RecommendedClips[0].EndTime != 3 {
		t.Fatalf("highlight: %+v, %v", highlight, err)
	}
	if _, err := client.Health(ctx); err != nil {
		t.Fatal(err)
	}
}

func TestVisionMissingFileDoesNotSendRequest(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { t.Error("missing file sent to AI") }))
	defer server.Close()
	_, err := New(server.URL, "sk-local-test").Vision(context.Background(), []string{filepath.Join(t.TempDir(), "missing.jpg")})
	if !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("lost file error: %v", err)
	}
}

func TestClient_RejectsStubHealthAndPreservesHTTPError(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/health" {
			_, _ = w.Write([]byte(`{"stub_mode":true,"models_loaded":[]}`))
			return
		}
		w.WriteHeader(401)
		_, _ = w.Write([]byte(`{"error":{"message":"bad key"}}`))
	}))
	defer server.Close()
	client := New(server.URL, "sk-local-test")
	if _, err := client.Health(context.Background()); err == nil {
		t.Fatal("stub accepted as real AI")
	}
	client.AllowStub = true
	if health, err := client.Health(context.Background()); err != nil || !health.StubMode {
		t.Fatalf("explicit development stub rejected: %+v %v", health, err)
	}
	_, err := client.Vision(context.Background(), nil)
	var de *domain.DomainError
	if !errors.As(err, &de) || de.Status != 401 {
		t.Fatalf("HTTP status lost: %v", err)
	}
}
