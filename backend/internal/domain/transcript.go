package domain

import "strings"

// MinSummaryWords: MiniGPT invents news-style text from near-empty input (e.g. crowd noise, non-Vietnamese speech),
// so a summary is only requested when the transcript has real speech.
// ponytail: fixed word floor; make it a setting if editors need per-category tuning.
const MinSummaryWords = 20

func Summarizable(transcript string) bool { return len(strings.Fields(transcript)) >= MinSummaryWords }

// SpokenSegments drops ASR chunks without text (silence/crowd) and renumbers the rest, so editors see no empty rows
// carrying a confidence score.
func SpokenSegments(segments []Segment) []Segment {
	out := make([]Segment, 0, len(segments))
	for _, s := range segments {
		if strings.TrimSpace(s.Text) == "" {
			continue
		}
		s.SegmentIndex = len(out)
		out = append(out, s)
	}
	return out
}
