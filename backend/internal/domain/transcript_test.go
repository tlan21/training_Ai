package domain

import (
	"strings"
	"testing"
)

func TestTranscriptGuards(t *testing.T) {
	if Summarizable("R I") || Summarizable("  ") || !Summarizable(strings.Repeat("từ ", MinSummaryWords)) {
		t.Fatal("summary word floor")
	}
	if q, ok := TranscriptQuality("Bàn thắng, phút 90+2!"); !ok || q != 1 {
		t.Fatalf("vietnamese quality %v %v", q, ok)
	}
	if q, _ := TranscriptQuality("zidane mbappé magnifique incroyable quelle frappe"); q >= MinTranscriptQuality {
		t.Fatalf("foreign draft scored %v", q)
	}
	if _, ok := TranscriptQuality(" ... "); ok {
		t.Fatal("no words must be not ok")
	}
	if Summarizable(strings.Repeat("qwz ", MinSummaryWords)) {
		t.Fatal("low quality transcript summarized")
	}
	got := SpokenSegments([]Segment{{SegmentIndex: 0, Text: ""}, {SegmentIndex: 1, Text: " R "}, {SegmentIndex: 2, Text: " "}, {SegmentIndex: 3, Text: "bàn thắng"}})
	if len(got) != 2 || got[0].Text != " R " || got[0].SegmentIndex != 0 || got[1].SegmentIndex != 1 {
		t.Fatalf("spoken segments %+v", got)
	}
}
