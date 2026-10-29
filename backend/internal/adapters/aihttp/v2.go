package aihttp

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"math"
	"mime/multipart"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
	"traning_ai/backend/internal/domain"
)

func validateVector(v []float32, dim int, normalized bool) error {
	if len(v) != dim {
		return fmt.Errorf("AI vector dimension: got %d want %d", len(v), dim)
	}
	norm := 0.0
	for _, x := range v {
		if math.IsNaN(float64(x)) || math.IsInf(float64(x), 0) {
			return fmt.Errorf("AI vector is not finite")
		}
		norm += float64(x) * float64(x)
	}
	if normalized && math.Abs(norm-1) > 0.01 {
		return fmt.Errorf("AI vector is not normalized")
	}
	return nil
}

// VisionV2 preserves frame order and sums logits, rather than voting on batch labels.
func (c *Client) VisionV2(ctx context.Context, paths []string) (*domain.VisionResult, error) {
	if len(paths) == 1 {
		if info, err := os.Stat(paths[0]); err == nil && info.IsDir() {
			var err error
			paths, err = filepath.Glob(filepath.Join(paths[0], "*.jpg"))
			if err != nil {
				return nil, err
			}
		}
	}
	if len(paths) == 0 {
		return nil, domain.NewError("VALIDATION_ERROR", "No video frames", 422)
	}
	result := &domain.VisionResult{CategoryLogitSums: map[string]float64{}}
	for start := 0; start < len(paths); start += 600 {
		end := min(start+600, len(paths))
		frames := make([]string, 0, end-start)
		for _, path := range paths[start:end] {
			data, err := os.ReadFile(path)
			if err != nil {
				return nil, err
			}
			frames = append(frames, "data:"+http.DetectContentType(data)+";base64,"+base64.StdEncoding.EncodeToString(data))
		}
		var batch domain.VisionResult
		if err := c.request(ctx, "/v2/vision/completions", map[string]any{"keyframes": frames}, &batch); err != nil {
			return nil, err
		}
		if len(batch.Embeddings256) != len(frames) || len(batch.SiameseVectors) != len(frames) || len(batch.CategoryLogitSums) != 4 {
			return nil, fmt.Errorf("AI v2 vision shape mismatch")
		}
		for i, v := range batch.SiameseVectors {
			if err := validateVector(v, 128, true); err != nil {
				return nil, err
			}
			if err := validateVector(batch.Embeddings256[i], 256, false); err != nil {
				return nil, err
			}
		}
		for label, value := range batch.CategoryLogitSums {
			if math.IsNaN(value) || math.IsInf(value, 0) {
				return nil, fmt.Errorf("AI logits not finite")
			}
			result.CategoryLogitSums[label] += value
		}
		result.Embeddings256 = append(result.Embeddings256, batch.Embeddings256...)
		result.SiameseVectors = append(result.SiameseVectors, batch.SiameseVectors...)
	}
	// Stable order also makes ties deterministic.
	for _, label := range []string{"bong_da", "ca_nhac", "the_thao", "tin_tuc"} {
		value, ok := result.CategoryLogitSums[label]
		if !ok {
			return nil, fmt.Errorf("AI category missing: %s", label)
		}
		if result.CategorySuggestion == "" || value > result.CategoryLogitSums[result.CategorySuggestion] {
			result.CategorySuggestion = label
		}
	}
	return result, nil
}
func (c *Client) SearchEmbedding(ctx context.Context, image string) ([]float32, error) {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()
	var result struct {
		Vector     []float32 `json:"vector"`
		Dim        int       `json:"dim"`
		Metric     string    `json:"metric"`
		Normalized bool      `json:"normalized"`
	}
	if err := c.request(ctx, "/v2/search/embeddings", map[string]string{"image": image}, &result); err != nil {
		var de *domain.DomainError
		if !errors.As(err, &de) {
			err = domain.NewError("AI_UNAVAILABLE", "Search embedding unavailable", 503)
		}
		return nil, err
	}
	if result.Dim != 128 || result.Metric != "COSINE" || !result.Normalized {
		return nil, domain.NewError("AI_UNAVAILABLE", "AI search vector metadata mismatch", 503)
	}
	if err := validateVector(result.Vector, 128, true); err != nil {
		return nil, domain.NewError("AI_UNAVAILABLE", err.Error(), 503)
	}
	return result.Vector, nil
}
func (c *Client) RecommendationEmbeddings(ctx context.Context, features domain.RecommendationFeatures) (*domain.RecommendationEmbeddings, error) {
	var result domain.RecommendationEmbeddings
	err := c.request(ctx, "/v2/recommendation/embeddings", features, &result)
	return &result, err
}

// ASRV2 converts locally and splits at 600s (a multiple of the model's 20s window).
func (c *Client) ASRV2(ctx context.Context, path, language string) (*domain.ASRResult, error) {
	if language != "vi" {
		return nil, domain.NewError("VALIDATION_ERROR", "Only Vietnamese audio supported", 422)
	}
	dir, err := os.MkdirTemp("", "asr-v2-")
	if err != nil {
		return nil, err
	}
	defer os.RemoveAll(dir)
	pattern := filepath.Join(dir, "%06d.wav")
	cmd := exec.CommandContext(ctx, "ffmpeg", "-v", "error", "-nostdin", "-i", path, "-vn", "-af", "aresample=16000,asetnsamples=n=320:p=0", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", "-f", "segment", "-segment_time", "600", "-reset_timestamps", "1", pattern)
	if output, err := cmd.CombinedOutput(); err != nil {
		return nil, domain.NewError("VALIDATION_ERROR", fmt.Sprintf("Audio decode: %s (%v)", output, err), 422)
	}
	files, err := filepath.Glob(filepath.Join(dir, "*.wav"))
	if err != nil {
		return nil, err
	}
	sort.Strings(files)
	if len(files) == 0 {
		return nil, domain.NewError("VALIDATION_ERROR", "Audio is empty", 422)
	}
	result := &domain.ASRResult{}
	for i, file := range files {
		part, err := c.asrChunk(ctx, file, language, float64(i*600))
		if err != nil {
			return nil, err
		}
		if part.FullTranscript != "" {
			result.FullTranscript = strings.TrimSpace(result.FullTranscript + " " + part.FullTranscript)
		}
		for _, s := range part.Segments {
			s.SegmentIndex = len(result.Segments)
			result.Segments = append(result.Segments, s)
		}
	}
	return result, nil
}
func (c *Client) asrChunk(ctx context.Context, path, language string, offset float64) (*domain.ASRResult, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	info, err := file.Stat()
	if err != nil {
		return nil, err
	}
	if info.Size() > 64<<20 {
		return nil, domain.NewError("PAYLOAD_TOO_LARGE", "Audio chunk exceeds 64 MiB", 413)
	}
	var body bytes.Buffer
	writer := multipart.NewWriter(&body)
	part, err := writer.CreateFormFile("file", "audio.wav")
	if err != nil {
		return nil, err
	}
	if _, err = io.Copy(part, file); err != nil {
		return nil, err
	}
	if err = writer.WriteField("language", language); err != nil {
		return nil, err
	}
	if err = writer.WriteField("offset_seconds", strconv.FormatFloat(offset, 'f', -1, 64)); err != nil {
		return nil, err
	}
	if err = writer.Close(); err != nil {
		return nil, err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/v2/asr/completions", &body)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+c.apiKey)
	req.Header.Set("Content-Type", writer.FormDataContentType())
	log.Printf("AI HTTP POST /v2/asr/completions offset_seconds=%g", offset)
	res, err := c.http.Do(req)
	if err != nil {
		return nil, err
	}
	defer res.Body.Close()
	if res.StatusCode != 200 {
		return nil, aiHTTPError(req.URL.Path, res)
	}
	var raw struct {
		FullTranscript string `json:"full_transcript"`
		Segments       []struct {
			ID         int     `json:"id"`
			Start      float64 `json:"start_time"`
			End        float64 `json:"end_time"`
			Text       string  `json:"text"`
			Confidence float64 `json:"confidence"`
			Warning    *string `json:"warning"`
		} `json:"segments"`
	}
	if err = json.NewDecoder(res.Body).Decode(&raw); err != nil {
		return nil, err
	}
	result := &domain.ASRResult{FullTranscript: raw.FullTranscript}
	for _, s := range raw.Segments {
		if s.Start < offset || s.End < s.Start || math.IsNaN(s.Start) || math.IsNaN(s.End) {
			return nil, fmt.Errorf("AI ASR invalid timestamps")
		}
		result.Segments = append(result.Segments, domain.Segment{SegmentIndex: s.ID, StartTime: s.Start, EndTime: s.End, Text: s.Text, Confidence: s.Confidence, Warning: s.Warning})
	}
	return result, nil
}
func aiHTTPError(path string, res *http.Response) error {
	var envelope struct {
		Error struct {
			Code    string `json:"code"`
			Message string `json:"message"`
		} `json:"error"`
	}
	_ = json.NewDecoder(io.LimitReader(res.Body, 1<<20)).Decode(&envelope)
	status := res.StatusCode
	if status >= 500 {
		status = 503
	}
	code := envelope.Error.Code
	if code == "" {
		code = "AI_UNAVAILABLE"
	}
	return domain.NewError(code, fmt.Sprintf("%s: HTTP %d: %s", path, res.StatusCode, envelope.Error.Message), status)
}
