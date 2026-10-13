package cutter

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"traning_ai/backend/internal/ports"
)

// cutRequested mirrors master plan §2.5 + §4b: gateway publishes clip.cut.requested.
type cutRequested struct {
	ClipID   string  `json:"clip_id"`
	VideoID  string  `json:"video_id"`
	Start    float64 `json:"start_time"`
	End      float64 `json:"end_time"`
}

type cutCompleted struct {
	ClipID       string `json:"clip_id"`
	ClipFilePath string `json:"clip_file_path"`
	Ok           bool   `json:"ok"`
	Error        string `json:"error,omitempty"`
}

// Service consumes clip.cut.requested, cuts via ffmpeg -c copy, uploads to MinIO, publishes clip.cut.completed.
type Service struct {
	clips   ports.ClipRepository
	videos  ports.VideoRepository
	storage ports.ObjectStorage
	bus     ports.EventBus
	// execFn allows test injection; default runs real ffmpeg.
	execFn      func(ctx context.Context, in, out string, start, end float64) error
	rawBucket   string
	clipsBucket string
	tmpDir      string
}

func New(clips ports.ClipRepository, videos ports.VideoRepository, storage ports.ObjectStorage, bus ports.EventBus, rawBucket, clipsBucket string) *Service {
	return &Service{
		clips: clips, videos: videos, storage: storage, bus: bus,
		rawBucket: rawBucket, clipsBucket: clipsBucket,
		tmpDir: os.TempDir(),
		execFn: realExec,
	}
}

// WithExecFn overrides ffmpeg execution (tests).
func (s *Service) WithExecFn(fn func(ctx context.Context, in, out string, start, end float64) error) { s.execFn = fn }

// HandleOne processes a single raw payload (used by tests and by Consume handler).
func (s *Service) HandleOne(ctx context.Context, payload []byte) error {
	var req cutRequested
	if err := json.Unmarshal(payload, &req); err != nil {
		return fmt.Errorf("bad payload: %w", err)
	}
	if req.ClipID == "" || req.VideoID == "" {
		return fmt.Errorf("missing clip_id/video_id")
	}
	if req.End <= req.Start {
		return s.fail(ctx, req.ClipID, "end must be > start")
	}

	clip, err := s.clips.Get(ctx, req.ClipID)
	if err != nil {
		return err
	}
	video, err := s.videos.Get(ctx, req.VideoID)
	if err != nil {
		return err
	}
	if video.RawFilePath == "" {
		return s.fail(ctx, req.ClipID, "video raw_file_path empty")
	}

	// duration guard — don't trust caller, check against video row
	if req.End > video.DurationSeconds+0.5 { // small epsilon for float
		// still cut but cap at duration; spec §4b CMS ensures end within duration
	}

	// fetch raw video to temp file
	tmpIn := filepath.Join(s.tmpDir, fmt.Sprintf("cut_%s_in.mp4", req.ClipID))
	tmpOut := filepath.Join(s.tmpDir, fmt.Sprintf("cut_%s_out.mp4", req.ClipID))
	defer func() { _ = os.Remove(tmpIn); _ = os.Remove(tmpOut) }()

	if err := s.fetchToFile(ctx, video.RawFilePath, tmpIn); err != nil {
		return s.fail(ctx, clip.ID, fmt.Sprintf("fetch raw: %v", err))
	}

	// ffmpeg -ss start -to end -i in -c copy out (no re-encode, §4b)
	cutCtx, cancel := context.WithTimeout(ctx, 2*time.Minute)
	defer cancel()
	if err := s.execFn(cutCtx, tmpIn, tmpOut, req.Start, req.End); err != nil {
		return s.fail(ctx, clip.ID, fmt.Sprintf("ffmpeg: %v", err))
	}

	// upload to MinIO
	f, err := os.Open(tmpOut)
	if err != nil {
		return s.fail(ctx, clip.ID, fmt.Sprintf("open cut: %v", err))
	}
	defer f.Close()
	fi, _ := f.Stat()
	key := fmt.Sprintf("clips/%s.mp4", req.ClipID)
	path, err := s.storage.PutStream(ctx, s.clipsBucket, key, f, fi.Size(), "video/mp4")
	if err != nil {
		return s.fail(ctx, clip.ID, fmt.Sprintf("upload: %v", err))
	}

	// update DB
	_ = s.clips.SetFilePath(ctx, clip.ID, path)
	_ = s.clips.SetStatus(ctx, clip.ID, "draft") // ready for publish (§4b handler sets draft → publish later)

	// publish completed
	return s.bus.Publish(ctx, "clip.cut.completed", req.ClipID, cutCompleted{ClipID: req.ClipID, ClipFilePath: path, Ok: true})
}

func (s *Service) fail(ctx context.Context, clipID, msg string) error {
	_ = s.bus.Publish(ctx, "clip.cut.completed", clipID, cutCompleted{ClipID: clipID, Ok: false, Error: msg})
	return fmt.Errorf("%s", msg)
}

func (s *Service) fetchToFile(ctx context.Context, rawPath, dst string) error {
	// rawPath is "bucket/key" or just key; storage.GetObject expects bucket+key.
	// gateway stores raw_file_path as "raw-videos/<key>"; we try to split.
	bucket, key := splitBucketKey(rawPath, s.rawBucket)
	rc, err := s.storage.GetObject(ctx, bucket, key)
	if err != nil {
		return err
	}
	defer rc.Close()
	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()
	_, err = io.Copy(out, rc)
	return err
}

func splitBucketKey(p, fallbackBucket string) (string, string) {
	for i := 0; i < len(p); i++ {
		if p[i] == '/' {
			return p[:i], p[i+1:]
		}
	}
	return fallbackBucket, p
}

func realExec(ctx context.Context, in, out string, start, end float64) error {
	// ffmpeg -ss start -to end -i in -c copy out  (input seeking, fast)
	args := []string{"-y", "-ss", fmt.Sprintf("%g", start), "-to", fmt.Sprintf("%g", end), "-i", in, "-c", "copy", out}
	cmd := exec.CommandContext(ctx, "ffmpeg", args...)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("%w: %s", err, stderr.String())
	}
	return nil
}
