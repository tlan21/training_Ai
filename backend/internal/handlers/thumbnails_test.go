package handlers

import (
	"context"
	"errors"
	"testing"
	"time"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

type thumbnailStorage struct {
	*mocks.ObjectStorageMem
	bucket, key string
	ttl         time.Duration
	fail        bool
}

func (s *thumbnailStorage) GetPresigned(_ context.Context, bucket, key string, ttl time.Duration) (string, error) {
	s.bucket, s.key, s.ttl = bucket, key, ttl
	if s.fail {
		return "", errors.New("presigning unavailable")
	}
	return "http://minio.test/" + bucket + "/" + key + "?signature=test", nil
}
func TestVideoThumbnailsResolveOldRowsWithoutChangingMetadata(t *testing.T) {
	storage := &thumbnailStorage{ObjectStorageMem: mocks.NewObjectStorageMem()}
	v := &domain.Video{ID: "vid_existing", Status: domain.VideoProcessed}
	ref := VideoThumbnailReference(v)
	url := ThumbnailURL(ref, storage)
	if url == nil || *url != "http://minio.test/thumbnails/vid_existing/00000000.jpg?signature=test" || storage.bucket != "thumbnails" || storage.key != "vid_existing/00000000.jpg" || storage.ttl != time.Hour {
		t.Fatal(url, storage)
	}
	if v.ThumbnailURL != nil {
		t.Fatal("read mapping changed stored metadata")
	}
	explicit := "thumbnails/vid_existing/custom.jpg"
	v.ThumbnailURL = &explicit
	if *VideoThumbnailReference(v) != explicit {
		t.Fatal("custom reference overwritten")
	}
	v.Status = domain.VideoDeleted
	if VideoThumbnailReference(v) != nil {
		t.Fatal("deleted video thumbnail exposed")
	}
	v.Status = domain.VideoProcessed
	now := time.Now()
	v.DeletedAt = &now
	if VideoThumbnailReference(v) != nil {
		t.Fatal("soft deleted video exposed")
	}
	v.DeletedAt = nil
	v.ThumbnailURL = nil
	v.Status = domain.VideoProcessing
	if VideoThumbnailReference(v) != nil {
		t.Fatal("invented thumbnail before processing")
	}
}
func TestThumbnailSigningRejectsBadKeysAndDoesNotExposePrivateKeysOnFailure(t *testing.T) {
	storage := &thumbnailStorage{ObjectStorageMem: mocks.NewObjectStorageMem(), fail: true}
	for _, value := range []string{"", "raw-videos/video.mp4", "thumbnails/../raw-videos/video.mp4", "javascript:alert(1)", "thumbnails/vid_x/00000000.jpg"} {
		if ThumbnailURL(&value, storage) != nil {
			t.Fatal("unsafe or failed URL returned", value)
		}
	}
	if ThumbnailURL(nil, storage) != nil {
		t.Fatal("nil reference")
	}
	key := "thumbnails/vid_x/00000000.jpg"
	if ThumbnailURL(&key, nil) != nil {
		t.Fatal("unsigned private key exposed")
	}
	external := "https://cdn.test/cover.jpg"
	if result := ThumbnailURL(&external, nil); result == nil || *result != external {
		t.Fatal("legacy public URL lost")
	}
}
