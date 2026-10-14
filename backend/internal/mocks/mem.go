package mocks

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"sync"
	"time"

	"traning_ai/backend/internal/domain"
)

// In-memory mocks cho 14 Ports — đủ chạy unit test + dev không cần Postgres/Mongo/Milvus/Kafka.
// Mỗi mock embed mutex để test song song an toàn.

type VideoRepoMem struct {
	mu sync.Mutex
	M  map[string]*domain.Video
}

func NewVideoRepoMem() *VideoRepoMem { return &VideoRepoMem{M: map[string]*domain.Video{}} }
func (r *VideoRepoMem) Create(_ context.Context, v *domain.Video) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.M[v.ID]; ok {
		return domain.ErrConflict
	}
	cp := *v
	r.M[v.ID] = &cp
	return nil
}
func (r *VideoRepoMem) Get(_ context.Context, id string) (*domain.Video, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok {
		return nil, domain.ErrVideoNotFound
	}
	cp := *v
	return &cp, nil
}
func (r *VideoRepoMem) GetProcessed(_ context.Context, id string) (*domain.Video, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok || v.Status != domain.VideoProcessed {
		return nil, domain.ErrVideoNotFound
	}
	cp := *v
	return &cp, nil
}
func (r *VideoRepoMem) List(_ context.Context, status *string, page, size int) ([]domain.Video, int, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	var all []domain.Video
	for _, v := range r.M {
		if status != nil && string(v.Status) != *status {
			continue
		}
		all = append(all, *v)
	}
	total := len(all)
	start := (page - 1) * size
	if start >= total {
		return nil, total, nil
	}
	end := start + size
	if end > total {
		end = total
	}
	return all[start:end], total, nil
}
func (r *VideoRepoMem) SetStatus(_ context.Context, id string, s domain.VideoStatus) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok {
		return domain.ErrVideoNotFound
	}
	v.Status = s
	return nil
}
func (r *VideoRepoMem) SetCategory(_ context.Context, id, catID string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok {
		return domain.ErrVideoNotFound
	}
	v.CategoryID = &catID
	return nil
}
func (r *VideoRepoMem) SetDuration(_ context.Context, id string, sec float64) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok {
		return domain.ErrVideoNotFound
	}
	v.DurationSeconds = sec
	return nil
}
func (r *VideoRepoMem) SoftDelete(_ context.Context, id string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok {
		return domain.ErrVideoNotFound
	}
	v.Status = domain.VideoDeleted
	now := time.Now()
	v.DeletedAt = &now
	return nil
}

// --- Clip ---

type ClipRepoMem struct {
	mu sync.Mutex
	M  map[string]*domain.Clip
}

func NewClipRepoMem() *ClipRepoMem { return &ClipRepoMem{M: map[string]*domain.Clip{}} }
func (r *ClipRepoMem) Create(_ context.Context, c *domain.Clip) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.M[c.ID] = c
	return nil
}
func (r *ClipRepoMem) Get(_ context.Context, id string) (*domain.Clip, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok {
		return nil, domain.ErrClipNotFound
	}
	cp := *v
	return &cp, nil
}
func (r *ClipRepoMem) GetPublished(_ context.Context, id string) (*domain.Clip, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok || v.Status != domain.ClipPublished {
		return nil, domain.ErrClipNotFound
	}
	cp := *v
	return &cp, nil
}
func (r *ClipRepoMem) ListPublishedByVideo(_ context.Context, vid string) ([]domain.Clip, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	var out []domain.Clip
	for _, v := range r.M {
		if v.VideoID == vid && v.Status == domain.ClipPublished {
			out = append(out, *v)
		}
	}
	return out, nil
}
func (r *ClipRepoMem) List(_ context.Context, videoID, status *string) ([]domain.Clip, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	var out []domain.Clip
	for _, v := range r.M {
		if videoID != nil && v.VideoID != *videoID {
			continue
		}
		if status != nil && string(v.Status) != *status {
			continue
		}
		out = append(out, *v)
	}
	return out, nil
}
func (r *ClipRepoMem) SetStatus(_ context.Context, id string, s domain.ClipStatus) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok {
		return domain.ErrClipNotFound
	}
	v.Status = s
	return nil
}
func (r *ClipRepoMem) SetFilePath(_ context.Context, id, p string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok {
		return domain.ErrClipNotFound
	}
	v.ClipFilePath = &p
	return nil
}
func (r *ClipRepoMem) UpdateMeta(_ context.Context, id string, title *string, start, end *float64) (*domain.Clip, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok {
		return nil, domain.ErrClipNotFound
	}
	if title != nil {
		v.Title = *title
	}
	if start != nil {
		v.StartTime = *start
	}
	if end != nil {
		v.EndTime = *end
	}
	cp := *v
	return &cp, nil
}
func (r *ClipRepoMem) HideByVideo(_ context.Context, vid string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	for _, v := range r.M {
		if v.VideoID == vid {
			v.Status = domain.ClipRejected
		}
	}
	return nil
}

// --- User / Session / Job / Category / Interaction ---

type UserRepoMem struct {
	mu sync.Mutex
	M  map[string]*domain.User
}

func NewUserRepoMem() *UserRepoMem { return &UserRepoMem{M: map[string]*domain.User{}} }
func (r *UserRepoMem) Create(_ context.Context, u *domain.User) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	for _, v := range r.M {
		if v.Email == u.Email {
			return domain.ErrEmailTaken
		}
		if v.Username == u.Username {
			return domain.ErrUsernameTaken
		}
	}
	cp := *u
	r.M[u.ID] = &cp
	return nil
}
func (r *UserRepoMem) Get(_ context.Context, id string) (*domain.User, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok {
		return nil, domain.ErrUserNotFound
	}
	cp := *v
	return &cp, nil
}
func (r *UserRepoMem) GetByEmail(_ context.Context, email string) (*domain.User, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	for _, v := range r.M {
		if v.Email == email {
			cp := *v
			return &cp, nil
		}
	}
	return nil, domain.ErrUserNotFound
}
func (r *UserRepoMem) UpdateProfile(_ context.Context, id string, username *string) (*domain.User, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok {
		return nil, domain.ErrUserNotFound
	}
	if username != nil {
		v.Username = *username
	}
	cp := *v
	return &cp, nil
}
func (r *UserRepoMem) UpdatePassword(_ context.Context, id string, newHash string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok {
		return domain.ErrUserNotFound
	}
	v.PasswordHash = newHash
	return nil
}
func (r *UserRepoMem) SetRole(_ context.Context, id string, role domain.Role) (*domain.User, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok {
		return nil, domain.ErrUserNotFound
	}
	v.Role = role
	cp := *v
	return &cp, nil
}
func (r *UserRepoMem) List(_ context.Context, page, size int) ([]domain.User, int, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	var all []domain.User
	for _, v := range r.M {
		all = append(all, *v)
	}
	total := len(all)
	start := (page - 1) * size
	if start >= total {
		return nil, total, nil
	}
	end := start + size
	if end > total {
		end = total
	}
	return all[start:end], total, nil
}

type SessionRepoMem struct {
	mu sync.Mutex
	M  map[string]*domain.Session
}

func NewSessionRepoMem() *SessionRepoMem { return &SessionRepoMem{M: map[string]*domain.Session{}} }
func (r *SessionRepoMem) Create(_ context.Context, uid, hash string, exp time.Time) (string, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	id := "ses_" + hash[:8]
	r.M[id] = &domain.Session{ID: id, UserID: uid, RefreshTokenHash: hash, ExpiresAt: exp}
	return id, nil
}
func (r *SessionRepoMem) GetByHash(_ context.Context, hash string) (*domain.Session, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	for _, v := range r.M {
		if v.RefreshTokenHash == hash {
			cp := *v
			return &cp, nil
		}
	}
	return nil, domain.ErrNotFound
}
func (r *SessionRepoMem) Delete(_ context.Context, id string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	delete(r.M, id)
	return nil
}
func (r *SessionRepoMem) DeleteByUser(_ context.Context, uid string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	for k, v := range r.M {
		if v.UserID == uid {
			delete(r.M, k)
		}
	}
	return nil
}

type PasswordResetRepoMem struct {
	mu sync.Mutex
	M  map[string]*domain.PasswordReset
}

func NewPasswordResetRepoMem() *PasswordResetRepoMem {
	return &PasswordResetRepoMem{M: map[string]*domain.PasswordReset{}}
}
func (r *PasswordResetRepoMem) Create(_ context.Context, uid, hash string, exp time.Time) (string, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	id := "rst_" + hash[:8]
	r.M[id] = &domain.PasswordReset{ID: id, UserID: uid, TokenHash: hash, ExpiresAt: exp, CreatedAt: time.Now()}
	return id, nil
}
func (r *PasswordResetRepoMem) GetByHash(_ context.Context, hash string) (*domain.PasswordReset, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	for _, v := range r.M {
		if v.TokenHash == hash {
			cp := *v
			return &cp, nil
		}
	}
	return nil, domain.ErrNotFound
}
func (r *PasswordResetRepoMem) Delete(_ context.Context, id string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	delete(r.M, id)
	return nil
}
func (r *PasswordResetRepoMem) DeleteByUser(_ context.Context, uid string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	for k, v := range r.M {
		if v.UserID == uid {
			delete(r.M, k)
		}
	}
	return nil
}

type JobRepoMem struct {
	mu sync.Mutex
	M  map[string]*domain.ProcessingJob
}

func NewJobRepoMem() *JobRepoMem { return &JobRepoMem{M: map[string]*domain.ProcessingJob{}} }
func (r *JobRepoMem) Create(_ context.Context, vid string) (*domain.ProcessingJob, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	j := &domain.ProcessingJob{ID: "job_" + vid, VideoID: vid, Status: domain.JobPending, QueueName: "video_ingest_queue"}
	r.M[j.ID] = j
	cp := *j
	return &cp, nil
}
func (r *JobRepoMem) Get(_ context.Context, id string) (*domain.ProcessingJob, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok {
		return nil, domain.ErrJobNotFound
	}
	cp := *v
	return &cp, nil
}
func (r *JobRepoMem) GetByVideo(_ context.Context, vid string) (*domain.ProcessingJob, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	for _, v := range r.M {
		if v.VideoID == vid {
			cp := *v
			return &cp, nil
		}
	}
	return nil, domain.ErrJobNotFound
}
func (r *JobRepoMem) List(_ context.Context, status *string) ([]domain.ProcessingJob, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	var out []domain.ProcessingJob
	for _, v := range r.M {
		if status != nil && string(v.Status) != *status {
			continue
		}
		out = append(out, *v)
	}
	return out, nil
}
func (r *JobRepoMem) SetStatus(_ context.Context, id string, s domain.JobStatus, started, completed bool) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok {
		return domain.ErrJobNotFound
	}
	v.Status = s
	now := time.Now()
	if started {
		v.StartedAt = &now
	}
	if completed {
		v.CompletedAt = &now
	}
	return nil
}
func (r *JobRepoMem) SetStage(_ context.Context, id string, stage domain.Stage) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok {
		return domain.ErrJobNotFound
	}
	v.CurrentStage = &stage
	if p, ok := domain.StageProgress[stage]; ok {
		v.Progress = p
	}
	return nil
}
func (r *JobRepoMem) SetError(_ context.Context, id, msg string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok {
		return domain.ErrJobNotFound
	}
	v.ErrorLog = &msg
	return nil
}

type CategoryRepoMem struct {
	mu sync.Mutex
	M  map[string]*domain.Category
}

func NewCategoryRepoMem() *CategoryRepoMem { return &CategoryRepoMem{M: map[string]*domain.Category{}} }
func (r *CategoryRepoMem) List(_ context.Context) ([]domain.Category, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	var out []domain.Category
	for _, v := range r.M {
		out = append(out, *v)
	}
	return out, nil
}
func (r *CategoryRepoMem) Create(_ context.Context, name string) (*domain.Category, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	for _, v := range r.M {
		if v.Name == name {
			return nil, domain.ErrConflict
		}
	}
	c := &domain.Category{ID: "cat_" + name, Name: name}
	r.M[c.ID] = c
	return c, nil
}
func (r *CategoryRepoMem) Update(_ context.Context, id, name string) (*domain.Category, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	v, ok := r.M[id]
	if !ok {
		return nil, domain.ErrCategoryNotFound
	}
	v.Name = name
	cp := *v
	return &cp, nil
}
func (r *CategoryRepoMem) Delete(_ context.Context, id string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.M[id]; !ok {
		return domain.ErrCategoryNotFound
	}
	delete(r.M, id)
	return nil
}

type InteractionRepoMem struct {
	mu    sync.Mutex
	Items []domain.Interaction
	Clips map[string]*domain.Clip
}

func NewInteractionRepoMem() *InteractionRepoMem {
	return &InteractionRepoMem{Clips: map[string]*domain.Clip{}}
}
func (r *InteractionRepoMem) Add(_ context.Context, i *domain.Interaction) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.Items = append(r.Items, *i)
	return nil
}
func (r *InteractionRepoMem) History(_ context.Context, uid string, _ *string, limit int) ([]domain.HistoryItem, *string, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	var out []domain.HistoryItem
	for _, it := range r.Items {
		if it.UserID != uid {
			continue
		}
		cl, ok := r.Clips[it.VideoID]
		if !ok {
			continue
		}
		out = append(out, domain.HistoryItem{Clip: *cl, WatchedAt: it.CreatedAt, DurationWatched: it.DurationWatched})
		if len(out) >= limit {
			break
		}
	}
	return out, nil, nil
}
func (r *InteractionRepoMem) Likes(_ context.Context, uid string, _ *string, limit int) ([]domain.Clip, *string, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	var out []domain.Clip
	for _, it := range r.Items {
		if it.UserID != uid || it.InteractionType != domain.InteractLike {
			continue
		}
		if cl, ok := r.Clips[it.VideoID]; ok {
			out = append(out, *cl)
		}
		if len(out) >= limit {
			break
		}
	}
	return out, nil, nil
}
func (r *InteractionRepoMem) PopularityTop(_ context.Context, limit int) ([]string, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	cnt := map[string]int{}
	for _, it := range r.Items {
		cnt[it.VideoID]++
	}
	type kv struct {
		k string
		v int
	}
	var kvs []kv
	for k, v := range cnt {
		kvs = append(kvs, kv{k, v})
	}
	// simple sort by count desc
	for i := 0; i < len(kvs); i++ {
		for j := i + 1; j < len(kvs); j++ {
			if kvs[j].v > kvs[i].v {
				kvs[i], kvs[j] = kvs[j], kvs[i]
			}
		}
	}
	var out []string
	for i := 0; i < len(kvs) && i < limit; i++ {
		out = append(out, kvs[i].k)
	}
	return out, nil
}

// --- Stores ---

type AnalysisStoreMem struct {
	mu sync.Mutex
	M  map[string]*domain.VideoAnalysis
}

func NewAnalysisStoreMem() *AnalysisStoreMem {
	return &AnalysisStoreMem{M: map[string]*domain.VideoAnalysis{}}
}
func (s *AnalysisStoreMem) Put(_ context.Context, vid string, scores []domain.SecondScore, clips []domain.AIClip, cat *string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	va, ok := s.M[vid]
	if !ok {
		va = &domain.VideoAnalysis{VideoID: vid}
		s.M[vid] = va
	}
	va.TimelineScores = scores
	va.AIClips = clips
	va.CategorySuggestion = cat
	return nil
}
func (s *AnalysisStoreMem) Get(_ context.Context, vid string) (*domain.VideoAnalysis, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	v, ok := s.M[vid]
	if !ok {
		return nil, domain.ErrNotFound
	}
	cp := *v
	return &cp, nil
}
func (s *AnalysisStoreMem) SetSummary(_ context.Context, vid, summary, status string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	v, ok := s.M[vid]
	if !ok {
		v = &domain.VideoAnalysis{VideoID: vid}
		s.M[vid] = v
	}
	v.Summary = &summary
	v.SummaryStatus = &status
	return nil
}
func (s *AnalysisStoreMem) Delete(_ context.Context, vid string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.M, vid)
	return nil
}

type SubtitleStoreMem struct {
	mu sync.Mutex
	M  map[string]*domain.Subtitle
}

func NewSubtitleStoreMem() *SubtitleStoreMem {
	return &SubtitleStoreMem{M: map[string]*domain.Subtitle{}}
}
func (s *SubtitleStoreMem) Put(_ context.Context, vid, lang, full string, segs []domain.Segment) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.M[vid] = &domain.Subtitle{VideoID: vid, Language: lang, FullTranscript: full, Segments: segs}
	return nil
}
func (s *SubtitleStoreMem) Get(_ context.Context, vid string) (*domain.Subtitle, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	v, ok := s.M[vid]
	if !ok {
		return nil, domain.ErrNotFound
	}
	cp := *v
	return &cp, nil
}
func (s *SubtitleStoreMem) UpdateSegments(_ context.Context, vid string, segs []domain.Segment) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	v, ok := s.M[vid]
	if !ok {
		return domain.ErrNotFound
	}
	v.Segments = segs
	return nil
}
func (s *SubtitleStoreMem) TextSearch(_ context.Context, q string) ([]domain.SubtitleMatch, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var out []domain.SubtitleMatch
	for _, v := range s.M {
		for _, seg := range v.Segments {
			if len(q) > 0 && contains(seg.Text, q) {
				out = append(out, domain.SubtitleMatch{VideoID: v.VideoID, Timestamp: seg.StartTime, Text: seg.Text})
			}
		}
	}
	return out, nil
}
func (s *SubtitleStoreMem) Delete(_ context.Context, vid string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.M, vid)
	return nil
}

func contains(s, sub string) bool { return len(s) >= len(sub) && searchStr(s, sub) }
func searchStr(s, sub string) bool {
	for i := 0; i+len(sub) <= len(s); i++ {
		if s[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}

type VectorStoreMem struct {
	mu     sync.Mutex
	Frames map[string][]domain.FrameEmbedding
	Users  map[string][]float32
	Videos map[string][]float32
}

func NewVectorStoreMem() *VectorStoreMem {
	return &VectorStoreMem{Frames: map[string][]domain.FrameEmbedding{}, Users: map[string][]float32{}, Videos: map[string][]float32{}}
}
func (v *VectorStoreMem) UpsertFrames(_ context.Context, vid string, items []domain.FrameEmbedding) error {
	v.mu.Lock()
	defer v.mu.Unlock()
	v.Frames[vid] = items
	return nil
}
func (v *VectorStoreMem) SearchFrames(_ context.Context, q []float32, topK int, _ float64) ([]domain.FrameHit, error) {
	v.mu.Lock()
	defer v.mu.Unlock()
	var hits []domain.FrameHit
	for vid, embs := range v.Frames {
		for _, e := range embs {
			hits = append(hits, domain.FrameHit{VideoID: vid, Timestamp: e.Timestamp, SimilarityScore: 0.9, ThumbnailURL: e.ThumbnailURL})
			if len(hits) >= topK {
				break
			}
		}
		if len(hits) >= topK {
			break
		}
	}
	return hits, nil
}
func (v *VectorStoreMem) DeleteFrames(_ context.Context, vid string) error {
	v.mu.Lock()
	defer v.mu.Unlock()
	delete(v.Frames, vid)
	return nil
}
func (v *VectorStoreMem) UpsertUser(_ context.Context, uid string, vec []float32, _ []string) error {
	v.mu.Lock()
	defer v.mu.Unlock()
	v.Users[uid] = vec
	return nil
}
func (v *VectorStoreMem) UpsertVideoVec(_ context.Context, vid string, vec []float32, _ []string) error {
	v.mu.Lock()
	defer v.mu.Unlock()
	v.Videos[vid] = vec
	return nil
}
func (v *VectorStoreMem) SearchVideosForUser(_ context.Context, uid string, limit int) ([]domain.VideoHit, error) {
	v.mu.Lock()
	defer v.mu.Unlock()
	var hits []domain.VideoHit
	for vid := range v.Videos {
		hits = append(hits, domain.VideoHit{VideoID: vid, Score: 0.9})
		if len(hits) >= limit {
			break
		}
	}
	return hits, nil
}

// --- Infra mocks ---

type EventBusMem struct {
	mu       sync.Mutex
	handlers map[string][]func(context.Context, []byte) error
	Events   []struct {
		Topic string
		Key   string
		Raw   []byte
	}
}

func NewEventBusMem() *EventBusMem { return &EventBusMem{} }
func (b *EventBusMem) Publish(ctx context.Context, topic, key string, payload any) error {
	raw, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	b.mu.Lock()
	b.Events = append(b.Events, struct {
		Topic string
		Key   string
		Raw   []byte
	}{Topic: topic, Key: key, Raw: raw})
	handlers := append([]func(context.Context, []byte) error(nil), b.handlers[topic]...)
	b.mu.Unlock()
	// Unlock before delivery: a consumer may publish the next pipeline event.
	for _, handler := range handlers {
		if err := handler(ctx, raw); err != nil {
			return err
		}
	}
	return nil
}
func (b *EventBusMem) Consume(_ context.Context, topic, _ string, handler func(context.Context, []byte) error) error {
	b.mu.Lock()
	defer b.mu.Unlock()
	if b.handlers == nil {
		b.handlers = make(map[string][]func(context.Context, []byte) error)
	}
	b.handlers[topic] = append(b.handlers[topic], handler)
	return nil
}

type ObjectStorageMem struct {
	mu   sync.Mutex
	Objs map[string][]byte // key: bucket/key
}

func NewObjectStorageMem() *ObjectStorageMem { return &ObjectStorageMem{Objs: map[string][]byte{}} }
func (s *ObjectStorageMem) PutStream(_ context.Context, bucket, key string, r io.Reader, _ int64, _ string) (string, error) {
	b, err := io.ReadAll(r)
	if err != nil {
		return "", err
	}
	s.mu.Lock()
	s.Objs[bucket+"/"+key] = b
	s.mu.Unlock()
	return bucket + "/" + key, nil
}
func (s *ObjectStorageMem) GetPresigned(_ context.Context, _, key string, _ time.Duration) (string, error) {
	return "https://storage.local/" + key, nil
}
func (s *ObjectStorageMem) GetObject(_ context.Context, bucket, key string) (io.ReadCloser, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	b, ok := s.Objs[bucket+"/"+key]
	if !ok {
		return nil, domain.ErrNotFound
	}
	return io.NopCloser(bytes.NewReader(b)), nil
}
func (s *ObjectStorageMem) Delete(_ context.Context, bucket, key string) error {
	s.mu.Lock()
	delete(s.Objs, bucket+"/"+key)
	s.mu.Unlock()
	return nil
}

// shortcut: memory cache ignores TTL; wire Redis before cache/load benchmarks.
type CacheMem struct {
	mu sync.Mutex
	M  map[string]string
}

func NewCacheMem() *CacheMem { return &CacheMem{M: map[string]string{}} }
func (c *CacheMem) Get(_ context.Context, k string) (string, bool, error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	v, ok := c.M[k]
	return v, ok, nil
}
func (c *CacheMem) Set(_ context.Context, k, v string, _ time.Duration) error {
	c.mu.Lock()
	c.M[k] = v
	c.mu.Unlock()
	return nil
}
func (c *CacheMem) Delete(_ context.Context, keys ...string) error {
	c.mu.Lock()
	for _, k := range keys {
		delete(c.M, k)
	}
	c.mu.Unlock()
	return nil
}

type AIClientMem struct {
	VisionFn         func([]string) (*domain.VisionResult, error)
	ASRFn            func(string, string) (*domain.ASRResult, error)
	HighlightFn      func(string, [][]float32, [][]float32) (*domain.HighlightResult, error)
	SearchFn         func(string, int, float64) (*domain.SearchResult, error)
	RecommendationFn func(string, int, map[string]string) (*domain.RecResult, error)
	SummarizeFn      func(string, int) (*domain.SummaryResult, error)
	HealthFn         func() (*domain.AIHealth, error)
}

func (m *AIClientMem) Vision(_ context.Context, paths []string) (*domain.VisionResult, error) {
	if m.VisionFn != nil {
		return m.VisionFn(paths)
	}
	return &domain.VisionResult{CategorySuggestion: "cat_bongda", Embeddings256: [][]float32{{0.1, 0.2}}}, nil
}
func (m *AIClientMem) ASR(_ context.Context, url, lang string) (*domain.ASRResult, error) {
	if m.ASRFn != nil {
		return m.ASRFn(url, lang)
	}
	return &domain.ASRResult{FullTranscript: "stub transcript", Segments: []domain.Segment{{Text: "stub", Confidence: 0.9}}}, nil
}
func (m *AIClientMem) Highlight(_ context.Context, vid string, ve [][]float32, af [][]float32) (*domain.HighlightResult, error) {
	if m.HighlightFn != nil {
		return m.HighlightFn(vid, ve, af)
	}
	return &domain.HighlightResult{TimelineScores: []domain.SecondScore{{Second: 0, Score: 90}}, RecommendedClips: []domain.AIClip{{StartTime: 0, EndTime: 5, AverageScore: 90}}}, nil
}
func (m *AIClientMem) Search(_ context.Context, b64 string, k int, th float64) (*domain.SearchResult, error) {
	if m.SearchFn != nil {
		return m.SearchFn(b64, k, th)
	}
	return &domain.SearchResult{Hits: []domain.FrameHit{{VideoID: "vid_1", SimilarityScore: 0.8}}}, nil
}
func (m *AIClientMem) Recommendation(_ context.Context, uid string, limit int, meta map[string]string) (*domain.RecResult, error) {
	if m.RecommendationFn != nil {
		return m.RecommendationFn(uid, limit, meta)
	}
	return &domain.RecResult{Hits: []domain.VideoHit{{VideoID: "vid_1", Score: 0.9}}}, nil
}
func (m *AIClientMem) Summarize(_ context.Context, p string, n int) (*domain.SummaryResult, error) {
	if m.SummarizeFn != nil {
		return m.SummarizeFn(p, n)
	}
	return &domain.SummaryResult{Text: "stub summary", Title: "stub title"}, nil
}
func (m *AIClientMem) Health(_ context.Context) (*domain.AIHealth, error) {
	if m.HealthFn != nil {
		return m.HealthFn()
	}
	return &domain.AIHealth{GpuVramUsed: 100, GpuUtil: 10, ModelsLoaded: []string{"vit"}, StubMode: false}, nil
}
