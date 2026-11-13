package domain

import "time"

// INT-62 (API 0.14.0): in-app notification produced from the Kafka topic clip.published.
const (
	TopicClipPublished      = "clip.published"
	NotifyKindClipPublished = "clip_published"
	MaxNotificationReadIDs  = 100
)

// ClipPublishedEvent is the clip.published payload. Consumers re-read the clip from Postgres; the event only names it.
type ClipPublishedEvent struct {
	ClipID      string    `json:"clip_id"`
	VideoID     string    `json:"video_id"`
	PublishedAt time.Time `json:"published_at"`
}

type UserNotification struct {
	ID           int64
	Kind         string
	ClipID       string
	VideoID      string
	Title        string
	ThumbnailURL *string
	CreatedAt    time.Time
	Read         bool
}
