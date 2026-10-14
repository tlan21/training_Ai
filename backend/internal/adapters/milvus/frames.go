// Package milvus supplies frame deletion; Siamese indexing/search live beside the model in Python.
package milvus

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"time"
	"traning_ai/backend/internal/ports"
)

type FrameStore struct {
	// shortcut: user/video recommendation vectors retain the existing adapter until Two-Tower integration.
	ports.VectorStore
	BaseURL string
	HTTP    *http.Client
}

func NewFrames(baseURL string, recommendations ports.VectorStore) *FrameStore {
	return &FrameStore{VectorStore: recommendations, BaseURL: baseURL, HTTP: &http.Client{Timeout: 5 * time.Second}}
}

func (s *FrameStore) DeleteFrames(ctx context.Context, videoID string) error {
	body, err := json.Marshal(map[string]string{"collectionName": "video_frame_embeddings",
		"filter": `payload["video_id"] == ` + strconv.Quote(videoID)})
	if err != nil {
		return err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, s.BaseURL+"/v2/vectordb/entities/delete", bytes.NewReader(body))
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
		Code    int    `json:"code"`
		Message string `json:"message"`
	}
	if err := json.NewDecoder(res.Body).Decode(&envelope); err != nil {
		return err
	}
	if res.StatusCode != 200 || envelope.Code != 0 {
		return fmt.Errorf("Milvus delete: HTTP %d, code %d: %s", res.StatusCode, envelope.Code, envelope.Message)
	}
	return nil
}
