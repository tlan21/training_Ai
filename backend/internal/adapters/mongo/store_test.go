package mongo

import (
	"context"
	"os"
	"strconv"
	"testing"
	"time"
	"traning_ai/backend/internal/domain"
)

func TestStores_RealVietnameseRoundTrip(t *testing.T) {
	uri := os.Getenv("TEST_MONGO_URI")
	if uri == "" {
		t.Skip("set TEST_MONGO_URI to test real MongoDB")
	}
	ctx := context.Background()
	db, err := New(ctx, uri, "video_ai")
	if err != nil {
		t.Fatal(err)
	}
	id := "vid_test_" + strconv.FormatInt(time.Now().UnixNano(), 36)
	sub := &SubtitleStore{Collection: db.Collection("subtitles")}
	analysis := &AnalysisStore{Collection: db.Collection("video_analyses")}
	defer func() {
		if err := sub.Delete(ctx, id); err != nil {
			t.Errorf("temporary subtitle cleanup: %v", err)
		}
		if err := analysis.Delete(ctx, id); err != nil {
			t.Errorf("temporary analysis cleanup: %v", err)
		}
	}()
	if err := sub.Put(ctx, id, "vi", "xin chào", []domain.Segment{{SegmentIndex: 1, StartTime: 2, EndTime: 3, Text: "xin chào", Confidence: 0.9}}); err != nil {
		t.Fatal(err)
	}
	stored, err := sub.Get(ctx, id)
	if err != nil || stored.FullTranscript != "xin chào" || stored.Segments[0].StartTime != 2 {
		t.Fatalf("lost Vietnamese transcript: %+v %v", stored, err)
	}
	threshold := 51.0
	if err := analysis.Put(ctx, id, []domain.SecondScore{{Second: 2, Score: 80}}, nil, nil, &threshold); err != nil {
		t.Fatal(err)
	}
	if err := analysis.SetSummary(ctx, id, "bản nháp", "draft"); err != nil {
		t.Fatal(err)
	}
	result, err := analysis.Get(ctx, id)
	if err != nil || *result.Summary != "bản nháp" || result.TimelineScores[0].Score != 80 || result.ClipThreshold == nil || *result.ClipThreshold != 51 {
		t.Fatalf("lost analysis: %+v %v", result, err)
	}
	for _, threshold := range []*float64{new(float64), nil} {
		if err := analysis.Put(ctx, id, nil, nil, nil, threshold); err != nil {
			t.Fatal(err)
		}
		stored, err := analysis.Get(ctx, id)
		if err != nil || (stored.ClipThreshold == nil) != (threshold == nil) {
			t.Fatalf("unknown/zero conflated: %+v %v", stored, err)
		}
		if threshold != nil && *stored.ClipThreshold != 0 {
			t.Fatal("zero lost")
		}
	}
}
