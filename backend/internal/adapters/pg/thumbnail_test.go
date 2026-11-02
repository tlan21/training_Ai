package pg

import (
	"context"
	"testing"
	"traning_ai/backend/internal/domain"
)

func TestClipThumbnailReferenceRealPersistence(t *testing.T) {
	db := integrationDB(t)
	ctx := context.Background()
	if _, err := db.Exec(ctx, `CREATE TEMP TABLE clips (LIKE public.clips INCLUDING ALL)`); err != nil {
		t.Fatal(err)
	}
	key := "thumbnails/vid_thumbnail/00000000.jpg"
	clip := &domain.Clip{ID: "clp_thumbnail", VideoID: "vid_thumbnail", Title: "thumbnail reference", StartTime: 0, EndTime: 2, Status: domain.ClipDraft, ThumbnailURL: &key, SourceSegments: []domain.ClipSourceSegment{{StartTime: 1, EndTime: 2}, {StartTime: 4, EndTime: 5}}}
	if err := (&ClipRepo{DB: db}).Create(ctx, clip); err != nil {
		t.Fatal(err)
	}
	stored, err := (&ClipRepo{DB: db}).Get(ctx, clip.ID)
	if err != nil || stored.ThumbnailURL == nil || *stored.ThumbnailURL != key {
		t.Fatalf("persistent reference %+v %v", stored, err)
	}
	if len(stored.SourceSegments) != 2 || stored.SourceSegments[1].StartTime != 4 {
		t.Fatalf("source map lost: %+v", stored)
	}
}
