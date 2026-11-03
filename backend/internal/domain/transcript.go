package domain

import (
	_ "embed"
	"strings"
	"unicode"
)

// MinSummaryWords: MiniGPT invents news-style text from near-empty input (e.g. crowd noise, non-Vietnamese speech),
// so a summary is only requested when the transcript has real speech.
// ponytail: fixed word floor; make it a setting if editors need per-category tuning.
const MinSummaryWords = 20

// MinTranscriptQuality: below this share of known Vietnamese syllables the ASR draft is mostly invented words
// (Vietnamese-only ASR on foreign-language or crowd audio), so it is flagged and not summarized.
const MinTranscriptQuality = 0.7

//go:embed vi_syllables.txt
var viSyllablesText string

// viSyllables: lowercase NFC syllable inventory from the VIVOS corpus transcripts.
var viSyllables = func() map[string]bool {
	m := map[string]bool{}
	for _, s := range strings.Fields(viSyllablesText) {
		m[s] = true
	}
	return m
}()

// TranscriptQuality returns the share of words that are known Vietnamese syllables (numbers count as known);
// ok is false when the text has no words.
// ponytail: no Unicode normalization; ASR output and browser input are NFC, add norm.NFC if NFD text shows up.
func TranscriptQuality(text string) (quality float64, ok bool) {
	known, total := 0, 0
	for _, w := range strings.Fields(strings.ToLower(text)) {
		w = strings.TrimFunc(w, func(r rune) bool { return !unicode.IsLetter(r) && !unicode.IsDigit(r) })
		if w == "" {
			continue
		}
		total++
		if viSyllables[w] || strings.IndexFunc(w, unicode.IsLetter) < 0 {
			known++
		}
	}
	if total == 0 {
		return 0, false
	}
	return float64(known) / float64(total), true
}

func Summarizable(transcript string) bool {
	q, _ := TranscriptQuality(transcript)
	return len(strings.Fields(transcript)) >= MinSummaryWords && q >= MinTranscriptQuality
}

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
