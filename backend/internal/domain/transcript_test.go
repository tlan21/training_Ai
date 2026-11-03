package domain

import (
	"strings"
	"testing"
)

func TestTranscriptGuards(t *testing.T) {
	if Summarizable("R I") || Summarizable("  ") || !Summarizable(strings.Repeat("từ ", MinSummaryWords)) {
		t.Fatal("summary word floor")
	}
	got := SpokenSegments([]Segment{{SegmentIndex: 0, Text: ""}, {SegmentIndex: 1, Text: " R "}, {SegmentIndex: 2, Text: " "}, {SegmentIndex: 3, Text: "bàn thắng"}})
	if len(got) != 2 || got[0].Text != " R " || got[0].SegmentIndex != 0 || got[1].SegmentIndex != 1 {
		t.Fatalf("spoken segments %+v", got)
	}
}
