package cutter

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"strings"
	"traning_ai/backend/internal/domain"
)

func realCompilation(ctx context.Context, in, out string, ranges []domain.ClipSourceSegment) error {
	var probe struct {
		Streams []struct {
			CodecType string `json:"codec_type"`
		} `json:"streams"`
	}
	metadata, err := exec.CommandContext(ctx, "ffprobe", "-v", "error", "-show_streams", "-of", "json", in).Output()
	if err != nil {
		return fmt.Errorf("probe source: %w", err)
	}
	if err := json.Unmarshal(metadata, &probe); err != nil {
		return err
	}
	audio, video := false, false
	for _, stream := range probe.Streams {
		audio = audio || stream.CodecType == "audio"
		video = video || stream.CodecType == "video"
	}
	if !video {
		return fmt.Errorf("source has no video stream")
	}
	if len(ranges) == 0 || len(ranges) > 100 {
		return fmt.Errorf("invalid compilation range count")
	}
	var filters, inputs strings.Builder
	fmt.Fprintf(&filters, "[0:v:0]split=%d", len(ranges))
	for i := range ranges {
		fmt.Fprintf(&filters, "[v%d]", i)
	}
	filters.WriteString(";")
	if audio {
		fmt.Fprintf(&filters, "[0:a:0]asplit=%d", len(ranges))
		for i := range ranges {
			fmt.Fprintf(&filters, "[a%d]", i)
		}
		filters.WriteString(";")
	}
	for i, r := range ranges {
		fmt.Fprintf(&filters, "[v%d]trim=start=%g:end=%g,setpts=PTS-STARTPTS[vc%d];", i, r.StartTime, r.EndTime, i)
		fmt.Fprintf(&inputs, "[vc%d]", i)
		if audio {
			fmt.Fprintf(&filters, "[a%d]atrim=start=%g:end=%g,asetpts=PTS-STARTPTS[ac%d];", i, r.StartTime, r.EndTime, i)
			fmt.Fprintf(&inputs, "[ac%d]", i)
		}
	}
	audioCount := 0
	if audio {
		audioCount = 1
	}
	fmt.Fprintf(&filters, "%sconcat=n=%d:v=1:a=%d[vout]", inputs.String(), len(ranges), audioCount)
	if audio {
		filters.WriteString("[aout]")
	}
	args := []string{"-y", "-v", "error", "-filter_complex_threads", "1", "-i", in, "-filter_complex", filters.String(), "-map", "[vout]"}
	if audio {
		args = append(args, "-map", "[aout]", "-c:a", "aac")
	}
	args = append(args, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-threads", "2", "-movflags", "+faststart", out)
	cmd := exec.CommandContext(ctx, "ffmpeg", args...)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("%w: %s", err, stderr.String())
	}
	return nil
}
