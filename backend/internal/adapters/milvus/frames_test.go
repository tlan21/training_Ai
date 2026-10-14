package milvus

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
)

func TestDeleteFramesExpressionAndMilvusErrors(t *testing.T) {
	videoID := `vid_quote" or id > 0`
	for _, body := range []string{`{"code":0}`, `{"code":1800,"message":"unavailable"}`} {
		server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if r.URL.Path != "/v2/vectordb/entities/delete" || r.Method != "POST" {
				t.Error(r.URL)
			}
			var req map[string]string
			if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
				t.Fatal(err)
			}
			if req["collectionName"] != "video_frame_embeddings" || req["filter"] != `payload["video_id"] == `+strconv.Quote(videoID) {
				t.Fatal(req)
			}
			_, _ = w.Write([]byte(body))
		}))
		err := NewFrames(server.URL, nil).DeleteFrames(context.Background(), videoID)
		server.Close()
		if (err == nil) != (body == `{"code":0}`) {
			t.Fatalf("body=%s err=%v", body, err)
		}
	}
}
