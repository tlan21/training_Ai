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
	defer sub.Delete(ctx, id)
	defer analysis.Delete(ctx, id)
	if err := sub.Put(ctx, id, "vi", "xin chào", []domain.Segment{{SegmentIndex: 1, StartTime: 2, EndTime: 3, Text: "xin chào", Confidence: 0.9}}); err != nil {
		t.Fatal(err)
	}
	stored, err := sub.Get(ctx, id)
	if err != nil || stored.FullTranscript != "xin chào" || stored.Segments[0].StartTime != 2 {
		t.Fatalf("lost Vietnamese transcript: %+v %v", stored, err)
	}
	if err := analysis.Put(ctx, id, []domain.SecondScore{{Second: 2, Score: 80}}, nil, nil); err != nil {
		t.Fatal(err)
	}
	if err := analysis.SetSummary(ctx, id, "bản nháp", "draft"); err != nil {
		t.Fatal(err)
	}
	result, err := analysis.Get(ctx, id)
	if err != nil || *result.Summary != "bản nháp" || result.TimelineScores[0].Score != 80 {
		t.Fatalf("lost analysis: %+v %v", result, err)
	}
}
