package cutter

import (
	"context"
	"encoding/json"
	"fmt"
	"math"
	"os/exec"
	"path/filepath"
	"testing"
	"time"
	"traning_ai/backend/internal/domain"
)

func TestCompilationRealFFmpeg(t *testing.T) {
	if _, err := exec.LookPath("ffmpeg"); err != nil {
		t.Skip("real ffmpeg required")
	}
	ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
	defer cancel()
	in, out := filepath.Join(t.TempDir(), "in.mp4"), filepath.Join(t.TempDir(), "out.mp4")
	cmd := exec.CommandContext(ctx, "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=25:duration=6", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=6", "-c:v", "libx264", "-threads", "1", "-c:a", "aac", "-shortest", in)
	if data, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("fixture %v %s", err, data)
	}
	for _, audio := range []bool{true, false} {
		source := in
		if !audio {
			source = filepath.Join(t.TempDir(), "silent.mp4")
			if data, err := exec.CommandContext(ctx, "ffmpeg", "-y", "-v", "error", "-i", in, "-an", "-c:v", "copy", source).CombinedOutput(); err != nil {
				t.Fatalf("silent %v %s", err, data)
			}
		}
		if err := realCompilation(ctx, source, out, []domain.ClipSourceSegment{{StartTime: 0.5, EndTime: 1.5}, {StartTime: 4, EndTime: 5}}); err != nil {
			t.Fatal(err)
		}
		data, err := exec.CommandContext(ctx, "ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", out).Output()
		if err != nil {
			t.Fatal(err)
		}
		var probe struct {
			Format struct {
				Duration string `json:"duration"`
			} `json:"format"`
			Streams []struct {
				CodecType string `json:"codec_type"`
				Duration  string `json:"duration"`
			} `json:"streams"`
		}
		if err := json.Unmarshal(data, &probe); err != nil {
			t.Fatal(err)
		}
		var duration float64
		if _, err := fmt.Sscan(probe.Format.Duration, &duration); err != nil || math.Abs(duration-2) > 0.1 {
			t.Fatalf("wrong duration %s", data)
		}
		hasAudio := false
		for _, s := range probe.Streams {
			hasAudio = hasAudio || s.CodecType == "audio"
		}
		if hasAudio != audio {
			t.Fatalf("audio mismatch %s", data)
		}
		for _, pair := range [][2]string{{"0.8", "0.3"}, {"4.5", "1.5"}} {
			frame := func(file, at string) []byte {
				b, e := exec.CommandContext(ctx, "ffmpeg", "-v", "error", "-ss", at, "-i", file, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-").Output()
				if e != nil {
					t.Fatal(e)
				}
				return b
			}
			a, b := frame(source, pair[0]), frame(out, pair[1])
			if len(a) == 0 || len(a) != len(b) {
				t.Fatal("decoded frames missing")
			}
			diff := 0.0
			for i := range a {
				diff += math.Abs(float64(a[i]) - float64(b[i]))
			}
			if diff/float64(len(a)) > 15 {
				t.Fatalf("wrong retained source frame: MAE %f", diff/float64(len(a)))
			}
		}
		t.Logf("audio=%t duration=%.3f, both retained source frames match", audio, duration)
	}
}
