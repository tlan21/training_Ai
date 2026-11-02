// Package milvus owns frame persistence and ANN search (AI-API v2 / D24).
package milvus

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"math"
	"net/http"
	"strconv"
	"time"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/ports"
)

type FrameStore struct {
	ports.VectorStore
	BaseURL string
	HTTP    *http.Client
}

func NewFrames(baseURL string, recommendations ports.VectorStore) *FrameStore {
	return &FrameStore{VectorStore: recommendations, BaseURL: baseURL, HTTP: &http.Client{Timeout: 15 * time.Second}}
}
func (s *FrameStore) request(ctx context.Context, path string, body any, out any) error {
	b, err := json.Marshal(body)
	if err != nil {
		return err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, s.BaseURL+"/v2/vectordb/"+path, bytes.NewReader(b))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	res, err := s.HTTP.Do(req)
	if err != nil {
		return err
	}
	defer res.Body.Close()
	var envelope struct {
		Code    int             `json:"code"`
		Message string          `json:"message"`
		Data    json.RawMessage `json:"data"`
	}
	if err = json.NewDecoder(res.Body).Decode(&envelope); err != nil {
		return err
	}
	if res.StatusCode != 200 || envelope.Code != 0 {
		return fmt.Errorf("Milvus %s: HTTP %d code %d: %s", path, res.StatusCode, envelope.Code, envelope.Message)
	}
	if out != nil {
		return json.Unmarshal(envelope.Data, out)
	}
	return nil
}
func (s *FrameStore) DeleteFrames(ctx context.Context, id string) error {
	return s.request(ctx, "entities/delete", map[string]any{"collectionName": "video_frame_embeddings", "filter": `payload["video_id"] == ` + strconv.Quote(id)}, nil)
}
func (s *FrameStore) UpsertFrames(ctx context.Context, id string, items []domain.FrameEmbedding) error {
	rows := make([]map[string]any, 0, len(items))
	for _, v := range items {
		if len(v.Vector) != 128 || v.Timestamp < 0 || math.IsNaN(v.Timestamp) || math.IsInf(v.Timestamp, 0) {
			return fmt.Errorf("Invalid frame embedding")
		}
		for _, x := range v.Vector {
			if math.IsNaN(float64(x)) || math.IsInf(float64(x), 0) {
				return fmt.Errorf("Invalid frame vector")
			}
		}
		rows = append(rows, map[string]any{"vector": v.Vector, "payload": map[string]any{"video_id": id, "timestamp": v.Timestamp, "thumbnail_url": v.ThumbnailURL}})
	}
	// Validate the entire batch before deleting a previous index. A failed insert is retried by the job.
	if err := s.DeleteFrames(ctx, id); err != nil {
		return err
	}
	for start := 0; start < len(rows); start += 600 {
		if err := s.request(ctx, "entities/insert", map[string]any{"collectionName": "video_frame_embeddings", "data": rows[start:min(start+600, len(rows))]}, nil); err != nil {
			return err
		}
	}
	return nil
}

// Milvus 2.4 REST serializes JSON payload bytes as base64, while newer versions return an object.
func decodePayload(raw json.RawMessage) (domain.FrameHit, error) {
	var result domain.FrameHit
	if len(raw) > 0 && raw[0] == '"' {
		var encoded string
		if err := json.Unmarshal(raw, &encoded); err != nil {
			return result, err
		}
		decoded, err := base64.StdEncoding.DecodeString(encoded)
		if err != nil {
			return result, err
		}
		raw = decoded
	}
	err := json.Unmarshal(raw, &result)
	return result, err
}
func (s *FrameStore) SearchFrames(ctx context.Context, vector []float32, topK int, threshold float64) ([]domain.FrameHit, error) {
	if len(vector) != 128 || topK < 1 || topK > 1000 || threshold < 0 || threshold > 1 || math.IsNaN(threshold) {
		return nil, fmt.Errorf("Invalid frame search parameters")
	}
	var rows []struct {
		Distance float64         `json:"distance"`
		Payload  json.RawMessage `json:"payload"`
	}
	err := s.request(ctx, "entities/search", map[string]any{"collectionName": "video_frame_embeddings", "data": [][]float32{vector}, "annsField": "vector", "limit": topK, "outputFields": []string{"payload"}, "consistencyLevel": "Session", "searchParams": map[string]any{"metricType": "COSINE", "params": map[string]int{"ef": max(64, topK)}}}, &rows)
	if err != nil {
		return nil, err
	}
	hits := []domain.FrameHit{}
	for _, row := range rows {
		if row.Distance < threshold {
			continue
		}
		hit, err := decodePayload(row.Payload)
		if err != nil {
			return nil, fmt.Errorf("Milvus payload: %w", err)
		}
		hit.SimilarityScore = math.Max(0, math.Min(1, row.Distance))
		hits = append(hits, hit)
	}
	return hits, nil
}
func (s *FrameStore) Health(ctx context.Context) error {
	return s.request(ctx, "collections/describe", map[string]string{"collectionName": "video_frame_embeddings"}, nil)
}

// FrameInventory is used by the non-destructive backfill command, not a product endpoint.
func (s *FrameStore) FrameInventory(ctx context.Context) (map[string]int, error) {
	counts := map[string]int{}
	for offset := 0; ; offset += 1000 {
		var rows []struct {
			Payload json.RawMessage `json:"payload"`
		}
		if err := s.request(ctx, "entities/query", map[string]any{"collectionName": "video_frame_embeddings", "filter": "id >= 0", "outputFields": []string{"payload"}, "limit": 1000, "offset": offset, "consistencyLevel": "Strong"}, &rows); err != nil {
			return nil, err
		}
		for _, row := range rows {
			hit, err := decodePayload(row.Payload)
			if err != nil {
				return nil, err
			}
			counts[hit.VideoID]++
		}
		if len(rows) < 1000 {
			return counts, nil
		}
	}
}
