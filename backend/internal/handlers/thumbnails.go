package handlers

import (
	"log"
	"strings"
	"time"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/ports"
)

// Backend ingest always writes frame zero before a video can become processed.
// Resolve the canonical key for old rows too, without rewriting existing metadata.
func VideoThumbnailReference(v *domain.Video) *string {
	if v.Status == domain.VideoDeleted || v.DeletedAt != nil {
		return nil
	}
	if v.ThumbnailURL != nil && *v.ThumbnailURL != "" {
		return v.ThumbnailURL
	}
	if v.Status != domain.VideoProcessed {
		return nil
	}
	key := "thumbnails/" + v.ID + "/00000000.jpg"
	return &key
}

// Only signed URLs leave the API for private thumbnail object keys.
func ThumbnailURL(reference *string, storage ports.ObjectStorage) *string {
	if reference == nil || *reference == "" {
		return nil
	}
	if strings.HasPrefix(*reference, "https://") || strings.HasPrefix(*reference, "http://") {
		return reference
	}
	key, ok := strings.CutPrefix(*reference, "thumbnails/")
	if !ok || key == "" || strings.Contains(key, "..") || storage == nil {
		return nil
	}
	url, err := storage.GetPresigned(nil, "thumbnails", key, time.Hour)
	if err != nil {
		log.Printf("thumbnail URL unavailable: %v", err)
		return nil
	}
	return &url
}
