package domain

import (
	"math"
	"sort"
)

// CompilationSegments keeps each source moment once, in chronological order.
func CompilationSegments(proposals []AIClip, duration float64) []ClipSourceSegment {
	var ranges []ClipSourceSegment
	for _, p := range proposals {
		start, end := math.Max(0, p.StartTime), math.Min(duration, p.EndTime)
		if math.IsNaN(start) || math.IsNaN(end) || math.IsInf(start, 0) || math.IsInf(end, 0) || end <= start {
			continue
		}
		ranges = append(ranges, ClipSourceSegment{start, end})
	}
	sort.Slice(ranges, func(i, j int) bool { return ranges[i].StartTime < ranges[j].StartTime })
	merged := make([]ClipSourceSegment, 0, len(ranges))
	for _, r := range ranges {
		if len(merged) > 0 && r.StartTime <= merged[len(merged)-1].EndTime {
			merged[len(merged)-1].EndTime = math.Max(merged[len(merged)-1].EndTime, r.EndTime)
		} else {
			merged = append(merged, r)
		}
	}
	return merged
}

func ValidSourceSegments(ranges []ClipSourceSegment, duration float64) bool {
	if len(ranges) == 0 || len(ranges) > 100 || duration <= 0 || math.IsNaN(duration) || math.IsInf(duration, 0) {
		return false
	}
	previous := -1.0
	for _, r := range ranges {
		if math.IsNaN(r.StartTime) || math.IsNaN(r.EndTime) || math.IsInf(r.StartTime, 0) || math.IsInf(r.EndTime, 0) || r.StartTime < 0 || r.EndTime <= r.StartTime || r.EndTime > duration || r.StartTime < previous {
			return false
		}
		previous = r.EndTime
	}
	return true
}
