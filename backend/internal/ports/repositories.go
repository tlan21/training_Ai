package ports

import (
	"context"
	"time"

	"traning_ai/backend/internal/domain"
)

// 02_backend_plan.md §2.1–2.7 — 7 repository Postgres.

type VideoRepository interface {
	Create(ctx context.Context, v *domain.Video) error
	Get(ctx context.Context, id string) (*domain.Video, error)
	GetProcessed(ctx context.Context, id string) (*domain.Video, error)
	List(ctx context.Context, status *string, page, size int) ([]domain.Video, int, error)
	SetStatus(ctx context.Context, id string, s domain.VideoStatus) error
	SetCategory(ctx context.Context, id, categoryID string) error
	SetDuration(ctx context.Context, id string, seconds float64) error
	SoftDelete(ctx context.Context, id string) error
}

type ClipRepository interface {
	Create(ctx context.Context, c *domain.Clip) error
	Get(ctx context.Context, id string) (*domain.Clip, error)
	GetPublished(ctx context.Context, id string) (*domain.Clip, error)
	ListPublishedByVideo(ctx context.Context, videoID string) ([]domain.Clip, error)
	List(ctx context.Context, videoID, status *string) ([]domain.Clip, error)
	SetStatus(ctx context.Context, id string, s domain.ClipStatus) error
	SetFilePath(ctx context.Context, id, path string) error
	UpdateMeta(ctx context.Context, id string, title *string, start, end *float64) (*domain.Clip, error)
	HideByVideo(ctx context.Context, videoID string) error
}

type UserRepository interface {
	Create(ctx context.Context, u *domain.User) error
	Get(ctx context.Context, id string) (*domain.User, error)
	GetByEmail(ctx context.Context, email string) (*domain.User, error)
	UpdateProfile(ctx context.Context, id string, username *string) (*domain.User, error)
	UpdatePassword(ctx context.Context, id string, newHash string) error
	SetRole(ctx context.Context, id string, r domain.Role) (*domain.User, error)
	List(ctx context.Context, page, size int) ([]domain.User, int, error)
}

type PasswordResetRepository interface {
	Create(ctx context.Context, userID, tokenHash string, expiresAt time.Time) (string, error)
	GetByHash(ctx context.Context, tokenHash string) (*domain.PasswordReset, error)
	Delete(ctx context.Context, id string) error
	DeleteByUser(ctx context.Context, userID string) error
}

type SessionRepository interface {
	Create(ctx context.Context, userID, refreshHash string, expiresAt time.Time) (string, error)
	GetByHash(ctx context.Context, refreshHash string) (*domain.Session, error)
	Delete(ctx context.Context, sessionID string) error
	DeleteByUser(ctx context.Context, userID string) error
}

type JobRepository interface {
	Create(ctx context.Context, videoID string) (*domain.ProcessingJob, error)
	Get(ctx context.Context, id string) (*domain.ProcessingJob, error)
	GetByVideo(ctx context.Context, videoID string) (*domain.ProcessingJob, error)
	List(ctx context.Context, status *string) ([]domain.ProcessingJob, error)
	SetStatus(ctx context.Context, id string, s domain.JobStatus, started, completed bool) error
	SetStage(ctx context.Context, id string, stage domain.Stage) error
	SetError(ctx context.Context, id, errorLog string) error
}

type InteractionRepository interface {
	Add(ctx context.Context, i *domain.Interaction) error
	History(ctx context.Context, userID string, cursor *string, limit int) ([]domain.HistoryItem, *string, error)
	Likes(ctx context.Context, userID string, cursor *string, limit int) ([]domain.Clip, *string, error)
	PopularityTop(ctx context.Context, limit int) ([]string, error)
}

type SettingsRepository interface {
	Get(ctx context.Context) (*domain.SystemSettings, error)
	Update(ctx context.Context, values map[string]string) error
}

type PreferenceRepository interface {
	Get(ctx context.Context, userID string) ([]string, error)
	Replace(ctx context.Context, userID string, categoryIDs []string) error
}

type CategoryRepository interface {
	List(ctx context.Context) ([]domain.Category, error)
	Create(ctx context.Context, name string) (*domain.Category, error)
	Update(ctx context.Context, id, name string) (*domain.Category, error)
	Delete(ctx context.Context, id string) error
}
