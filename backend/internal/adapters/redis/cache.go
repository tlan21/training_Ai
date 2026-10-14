package redis

import (
	"context"
	"errors"
	redissdk "github.com/redis/go-redis/v9"
	"time"
)

type Client struct{ db *redissdk.Client }

func New(ctx context.Context, addr string) (*Client, error) {
	db := redissdk.NewClient(&redissdk.Options{Addr: addr})
	if err := db.Ping(ctx).Err(); err != nil {
		_ = db.Close()
		return nil, err
	}
	return &Client{db: db}, nil
}
func (c *Client) Get(ctx context.Context, key string) (string, bool, error) {
	value, err := c.db.Get(ctx, key).Result()
	if errors.Is(err, redissdk.Nil) {
		return "", false, nil
	}
	return value, err == nil, err
}
func (c *Client) Set(ctx context.Context, key, value string, ttl time.Duration) error {
	return c.db.Set(ctx, key, value, ttl).Err()
}
func (c *Client) Delete(ctx context.Context, keys ...string) error {
	return c.db.Del(ctx, keys...).Err()
}
