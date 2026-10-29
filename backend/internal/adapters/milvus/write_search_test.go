package milvus

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"traning_ai/backend/internal/domain"
)

func TestFrameWriteSearchAndInvalidBatchPreservesData(t *testing.T) {
	paths := []string{}
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		paths = append(paths, r.URL.Path)
		var req map[string]any
		_ = json.NewDecoder(r.Body).Decode(&req)
		switch r.URL.Path {
		case "/v2/vectordb/entities/insert":
			row := req["data"].([]any)[0].(map[string]any)
			if row["payload"].(map[string]any)["video_id"] != "vid_test" {
				t.Error(req)
			}
			fmt.Fprint(w, `{"code":0}`)
		case "/v2/vectordb/entities/search":
			p := req["searchParams"].(map[string]any)
			if p["metricType"] != "COSINE" || p["params"].(map[string]any)["ef"] != float64(100) {
				t.Error(req)
			}
			payload := base64.StdEncoding.EncodeToString([]byte(`{"video_id":"vid_test","timestamp":2,"thumbnail_url":"thumbnails/vid_test/00000002.jpg"}`))
			fmt.Fprintf(w, `{"code":0,"data":[{"distance":1.00001,"payload":%q},{"distance":0.5,"payload":%q}]}`, payload, payload)
		default:
			fmt.Fprint(w, `{"code":0}`)
		}
	}))
	defer server.Close()
	s := NewFrames(server.URL, nil)
	v := make([]float32, 128)
	v[0] = 1
	if err := s.UpsertFrames(context.Background(), "vid_test", []domain.FrameEmbedding{{Vector: v}}); err != nil {
		t.Fatal(err)
	}
	hits, err := s.SearchFrames(context.Background(), v, 100, .75)
	if err != nil || len(hits) != 1 || hits[0].SimilarityScore != 1 || hits[0].Timestamp != 2 {
		t.Fatalf("search %+v %v", hits, err)
	}
	if len(paths) != 3 || paths[0] != "/v2/vectordb/entities/delete" || paths[1] != "/v2/vectordb/entities/insert" {
		t.Fatal(paths)
	}
	n := len(paths)
	if err := s.UpsertFrames(context.Background(), "vid_test", []domain.FrameEmbedding{{Vector: []float32{1}}}); err == nil || len(paths) != n {
		t.Fatal("invalid batch deleted prior data")
	}
	if hit, err := decodePayload(json.RawMessage(`{"video_id":"vid_object"}`)); err != nil || hit.VideoID != "vid_object" {
		t.Fatal(hit, err)
	}
}
