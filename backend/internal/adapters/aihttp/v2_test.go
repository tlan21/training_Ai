package aihttp_test

import (
	"bytes"
	"context"
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"traning_ai/backend/internal/adapters/aihttp"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

func TestV2MockRoundTrip(t *testing.T) {
	s := httptest.NewServer(mocks.NewAIHTTP("test"))
	defer s.Close()
	c := aihttp.New(s.URL, "test")
	ctx := context.Background()
	frame := filepath.Join(t.TempDir(), "f.jpg")
	_ = os.WriteFile(frame, []byte("frame"), 0600)
	paths := make([]string, 601)
	for i := range paths {
		paths[i] = frame
	}
	v, err := c.VisionV2(ctx, paths)
	if err != nil || len(v.SiameseVectors) != 601 || v.CategoryLogitSums["bong_da"] != 601 {
		t.Fatalf("batched vision %v", err)
	}
	vec, err := c.SearchEmbedding(ctx, "ZnJhbWU=")
	if err != nil || len(vec) != 128 {
		t.Fatal(err)
	}
	rec, err := c.RecommendationEmbeddings(ctx, domain.RecommendationFeatures{Videos: []domain.RecommendationVideo{{VideoID: "vid_test"}}, Users: []domain.RecommendationUser{{UserID: "usr_test", PositiveVideoIDs: []string{"vid_test"}}}})
	if err != nil || rec.FeatureVersion != "ttv2-features-v1" || len(rec.Videos) != 1 {
		t.Fatalf("rec %+v %v", rec, err)
	}
	_, err = c.RecommendationEmbeddings(ctx, domain.RecommendationFeatures{Users: []domain.RecommendationUser{{UserID: "usr_test", PositiveVideoIDs: []string{"vid_missing"}}}})
	var de *domain.DomainError
	if !errors.As(err, &de) || de.Status != 422 || de.Code != "VALIDATION_ERROR" {
		t.Fatalf("422 %v", err)
	}
}
func TestV2AggregatesLogitsNotMajority(t *testing.T) {
	calls := 0
	s := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v2/vision/completions" || r.Header.Get("Authorization") != "Bearer test" {
			t.Error("transport")
		}
		var req struct {
			Keyframes []string `json:"keyframes"`
		}
		_ = json.NewDecoder(r.Body).Decode(&req)
		calls++
		v := domain.VisionResult{CategoryLogitSums: map[string]float64{"bong_da": 0, "ca_nhac": 0, "the_thao": 0, "tin_tuc": 0}}
		if calls == 1 {
			v.CategoryLogitSums["bong_da"] = 1
		} else {
			v.CategoryLogitSums["tin_tuc"] = 100
		}
		for range req.Keyframes {
			a, b := make([]float32, 256), make([]float32, 128)
			a[0], b[0] = 2, 1
			v.Embeddings256 = append(v.Embeddings256, a)
			v.SiameseVectors = append(v.SiameseVectors, b)
		}
		_ = json.NewEncoder(w).Encode(v)
	}))
	defer s.Close()
	file := filepath.Join(t.TempDir(), "a.jpg")
	_ = os.WriteFile(file, []byte("a"), 0600)
	paths := make([]string, 601)
	for i := range paths {
		paths[i] = file
	}
	v, err := aihttp.New(s.URL, "test").VisionV2(context.Background(), paths)
	if err != nil || v.CategorySuggestion != "tin_tuc" || calls != 2 {
		t.Fatalf("aggregation %v %v", v, err)
	}
}
func TestV2ASRSplits600SecondsAndOffsets(t *testing.T) {
	if _, err := exec.LookPath("ffmpeg"); err != nil {
		t.Fatal(err)
	}
	file := filepath.Join(t.TempDir(), "audio.wav")
	if out, err := exec.Command("ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "600.1", "-c:a", "pcm_s16le", file).CombinedOutput(); err != nil {
		t.Fatalf("fixture %v %s", err, out)
	}
	calls := 0
	s := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v2/asr/completions" || r.Header.Get("Authorization") != "Bearer test" {
			t.Error("ASR transport")
		}
		_ = r.ParseMultipartForm(1 << 20)
		defer r.MultipartForm.RemoveAll()
		f, h, err := r.FormFile("file")
		if err != nil {
			t.Error(err)
			return
		}
		defer f.Close()
		data, _ := io.ReadAll(f)
		pos := bytes.Index(data, []byte("data"))
		if pos < 0 {
			t.Fatal("not WAV")
		}
		if calls == 0 && binary.LittleEndian.Uint32(data[pos+4:pos+8]) != 600*16000*2 {
			t.Errorf("first chunk is not exactly 600 seconds")
		}
		if h.Size > 64<<20 || r.FormValue("offset_seconds") != fmt.Sprint(calls*600) || r.FormValue("language") != "vi" {
			t.Error("chunk/offset")
		}
		fmt.Fprintf(w, `{"full_transcript":"hello","segments":[{"id":99,"start_time":%d,"end_time":%d,"text":"hello","confidence":0.8}]}`, calls*600, calls*600+1)
		calls++
	}))
	defer s.Close()
	v, err := aihttp.New(s.URL, "test").ASRV2(context.Background(), file, "vi")
	if err != nil || calls != 2 || v.FullTranscript != "hello hello" || v.Segments[1].SegmentIndex != 1 || v.Segments[1].StartTime != 600 {
		t.Fatalf("ASR %+v %v calls=%d", v, err, calls)
	}
}
func TestV2PreservesModelNotReady(t *testing.T) {
	s := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(503)
		fmt.Fprint(w, `{"error":{"code":"MODEL_NOT_READY","message":"AI-12"}}`)
	}))
	defer s.Close()
	_, err := aihttp.New(s.URL, "test").RecommendationEmbeddings(context.Background(), domain.RecommendationFeatures{})
	var de *domain.DomainError
	if !errors.As(err, &de) || de.Status != 503 || de.Code != "MODEL_NOT_READY" {
		t.Fatal(err)
	}
}
