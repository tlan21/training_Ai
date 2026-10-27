package minio

import (
	"context"
	miniosdk "github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
	"io"
	"strings"
	"time"
	"traning_ai/backend/internal/startup"
)

type Client struct{ internal, public *miniosdk.Client }

func New(ctx context.Context, endpoint, publicEndpoint, access, secret string) (*Client, error) {
	options := &miniosdk.Options{Creds: credentials.NewStaticV4(access, secret, ""), Region: "us-east-1"}
	internal, err := miniosdk.New(endpoint, options)
	if err != nil {
		return nil, err
	}
	public, err := miniosdk.New(publicEndpoint, options)
	if err != nil {
		return nil, err
	}
	for _, bucket := range []string{"raw-videos", "clips"} {
		if err := startup.Wait(ctx, "MinIO "+bucket, func(probe context.Context) error {
			exists, err := internal.BucketExists(probe, bucket)
			if err != nil || exists {
				return err
			}
			return internal.MakeBucket(probe, bucket, miniosdk.MakeBucketOptions{})
		}); err != nil {
			return nil, err
		}
	}
	return &Client{internal: internal, public: public}, nil
}
func (c *Client) PutStream(ctx context.Context, bucket, key string, reader io.Reader, size int64, contentType string) (string, error) {
	_, err := c.internal.PutObject(ctx, bucket, key, reader, size, miniosdk.PutObjectOptions{ContentType: contentType, PartSize: 8 * 1024 * 1024, NumThreads: 1})
	return bucket + "/" + key, err
}
func (c *Client) GetPresigned(ctx context.Context, bucket, key string, ttl time.Duration) (string, error) {
	if ctx == nil {
		ctx = context.Background()
	}
	url, err := c.public.PresignedGetObject(ctx, bucket, strings.TrimPrefix(key, bucket+"/"), ttl, nil)
	if err != nil {
		return "", err
	}
	return url.String(), nil
}
func (c *Client) GetObject(ctx context.Context, bucket, key string) (io.ReadCloser, error) {
	obj, err := c.internal.GetObject(ctx, bucket, key, miniosdk.GetObjectOptions{})
	if err != nil {
		return nil, err
	}
	if _, err := obj.Stat(); err != nil {
		_ = obj.Close()
		return nil, err
	}
	return obj, nil
}
func (c *Client) Delete(ctx context.Context, bucket, key string) error {
	return c.internal.RemoveObject(ctx, bucket, key, miniosdk.RemoveObjectOptions{})
}
