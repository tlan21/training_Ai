package domain

import (
	"math"
	"reflect"
	"testing"
)

func TestCompilationSegments(t *testing.T) {
	proposals := []AIClip{{StartTime: 8, EndTime: 20}, {StartTime: 1, EndTime: 3}, {StartTime: 2, EndTime: 4}, {StartTime: -1, EndTime: 1}, {StartTime: math.NaN(), EndTime: 9}, {StartTime: 6, EndTime: 5}}
	got := CompilationSegments(proposals, 10)
	want := []ClipSourceSegment{{0, 4}, {8, 10}}
	if !reflect.DeepEqual(got, want) || !ValidSourceSegments(got, 10) {
		t.Fatalf("got %+v", got)
	}
	if len(CompilationSegments(nil, 10)) != 0 {
		t.Fatal("must not invent highlights")
	}
	for _, ranges := range [][]ClipSourceSegment{nil, {{2, 1}}, {{-1, 2}}, {{0, 11}}, {{4, 6}, {5, 8}}, {{0, math.Inf(1)}}, make([]ClipSourceSegment, 101)} {
		if ValidSourceSegments(ranges, 10) {
			t.Fatalf("accepted invalid %+v", ranges)
		}
	}
}
