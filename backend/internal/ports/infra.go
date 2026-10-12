package ports

import (
	"context"
	"io"
	"time"
)

// 02_backend_plan.md §2.11–2.13 — infra.

type EventBus interface {
	Publish(ctx context.Context, topic string, key string, payload any) error
	Consume(ctx context.Context, topic, groupID string, handler func(ctx context.Context, payload []byte) error) error
}

type ObjectStorage interface {
	PutStream(ctx context.Context, bucket, key string, r io.Reader, size int64, contentType string) (string, error)
	GetPresigned(ctx context.Context, bucket, key string, ttl time.Duration) (string, error)
	GetObject(ctx context.Context, bucket, key string) (io.ReadCloser, error)
	Delete(ctx context.Context, bucket, key string) error
}

type Cache interface {
	Get(ctx context.Context, key string) (string, bool, error)
	Set(ctx context.Context, key, value string, ttl time.Duration) error
	Delete(ctx context.Context, keys ...string) error
}
