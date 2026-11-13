package handlers

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/ports"
)

// NotificationHandlers — INT-62 (API 0.14.0): the user's in-app inbox.
type NotificationHandlers struct {
	repo    ports.NotificationRepository
	storage ports.ObjectStorage
}

func NewNotificationHandlers(repo ports.NotificationRepository, storage ports.ObjectStorage) *NotificationHandlers {
	return &NotificationHandlers{repo: repo, storage: storage}
}

func (h *NotificationHandlers) List(c *gin.Context) {
	items, next, unread, err := h.repo.List(c.Request.Context(), c.GetString("user_id"), cursorParam(c), parseLimit(c.Query("limit"), 20))
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	out := make([]gin.H, 0, len(items))
	for _, n := range items {
		out = append(out, gin.H{"id": strconv.FormatInt(n.ID, 10), "kind": n.Kind, "clip_id": n.ClipID, "video_id": n.VideoID, "title": n.Title,
			"thumbnail_url": ThumbnailURL(n.ThumbnailURL, h.storage), "created_at": n.CreatedAt.UTC(), "read": n.Read})
	}
	c.JSON(http.StatusOK, gin.H{"items": out, "unread_count": unread, "next_cursor": next})
}

func (h *NotificationHandlers) MarkRead(c *gin.Context) {
	var body struct {
		IDs []string `json:"ids"`
	}
	if c.Request.ContentLength != 0 {
		if err := c.ShouldBindJSON(&body); err != nil {
			handleDomainErr(c, domain.ErrValidation)
			return
		}
	}
	if len(body.IDs) > domain.MaxNotificationReadIDs {
		handleDomainErr(c, domain.ErrValidation)
		return
	}
	ids := make([]int64, 0, len(body.IDs))
	for _, raw := range body.IDs {
		id, err := strconv.ParseInt(raw, 10, 64)
		if err != nil || id <= 0 {
			handleDomainErr(c, domain.ErrValidation)
			return
		}
		ids = append(ids, id)
	}
	if err := h.repo.MarkRead(c.Request.Context(), c.GetString("user_id"), ids); err != nil {
		handleDomainErr(c, err)
		return
	}
	c.Status(http.StatusNoContent)
}

// ClipPublishedConsumer handles Kafka clip.published for the consumer group gateway-notifications.
// Malformed events are dropped (logged) instead of blocking the partition; DB errors are returned and logged by the pipeline.
func ClipPublishedConsumer(repo ports.NotificationRepository) func(context.Context, []byte) error {
	return func(ctx context.Context, payload []byte) error {
		var ev domain.ClipPublishedEvent
		if err := json.Unmarshal(payload, &ev); err != nil || !strings.HasPrefix(ev.ClipID, "clp_") || len(ev.ClipID) > 50 {
			log.Printf("%s: dropped malformed event %.200q", domain.TopicClipPublished, payload)
			return nil
		}
		created, err := repo.FanOutClipPublished(ctx, ev.ClipID)
		if err != nil {
			return err
		}
		log.Printf("%s %s: %d notifications", domain.TopicClipPublished, ev.ClipID, created)
		return nil
	}
}
