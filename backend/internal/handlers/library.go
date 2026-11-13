package handlers

import (
	"context"
	"errors"
	"log"
	"net/http"
	"strings"
	"unicode/utf8"

	"github.com/gin-gonic/gin"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/ports"
)

// LibraryHandlers — INT-61 (API 0.13.0): like / watch-later state, history hiding, user lists.
type LibraryHandlers struct {
	repo    ports.LibraryRepository
	events  interactionAdder
	storage ports.ObjectStorage
}

type interactionAdder interface {
	Add(ctx context.Context, i *domain.Interaction) error
}

func NewLibraryHandlers(repo ports.LibraryRepository, events interactionAdder, storage ports.ObjectStorage) *LibraryHandlers {
	return &LibraryHandlers{repo: repo, events: events, storage: storage}
}

func (h *LibraryHandlers) mark(c *gin.Context, kind string, on bool) {
	uid, clipID := c.GetString("user_id"), c.Param("clip_id")
	created, videoID, err := h.repo.SetMark(c.Request.Context(), uid, clipID, kind, on)
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	if created && h.events != nil {
		// Two-Tower signal: one like/save event per new mark. The repo records events for role client only.
		event := &domain.Interaction{UserID: uid, VideoID: videoID, ClipID: &clipID, InteractionType: domain.InteractionType(kind)}
		if err := h.events.Add(c.Request.Context(), event); err != nil && !errors.Is(err, domain.ErrVideoNotFound) {
			log.Printf("library %s event for %s: %v", kind, clipID, err)
		}
	}
	c.Status(http.StatusNoContent)
}

func (h *LibraryHandlers) Like(c *gin.Context)   { h.mark(c, domain.MarkLike, true) }
func (h *LibraryHandlers) Unlike(c *gin.Context) { h.mark(c, domain.MarkLike, false) }
func (h *LibraryHandlers) Save(c *gin.Context)   { h.mark(c, domain.MarkSave, true) }
func (h *LibraryHandlers) Unsave(c *gin.Context) { h.mark(c, domain.MarkSave, false) }

func (h *LibraryHandlers) clipPage(c *gin.Context, clips []domain.Clip, next *string, err error) {
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	items := make([]gin.H, 0, len(clips))
	for i := range clips {
		items = append(items, toClipH(&clips[i], h.storage))
	}
	c.JSON(http.StatusOK, gin.H{"items": items, "next_cursor": next})
}

func cursorParam(c *gin.Context) *string {
	if v := c.Query("cursor"); v != "" {
		return &v
	}
	return nil
}

func (h *LibraryHandlers) Saved(c *gin.Context) {
	clips, next, err := h.repo.Marks(c.Request.Context(), c.GetString("user_id"), domain.MarkSave, cursorParam(c), parseLimit(c.Query("limit"), 10))
	h.clipPage(c, clips, next, err)
}

func (h *LibraryHandlers) ClipStates(c *gin.Context) {
	seen := map[string]bool{}
	ids := []string{}
	for _, id := range strings.Split(c.Query("clip_ids"), ",") {
		id = strings.TrimSpace(id)
		if id == "" || seen[id] {
			continue
		}
		if len(id) > 50 {
			handleDomainErr(c, domain.ErrValidation)
			return
		}
		seen[id] = true
		ids = append(ids, id)
	}
	if len(ids) == 0 || len(ids) > domain.MaxClipStateIDs {
		handleDomainErr(c, domain.ErrValidation)
		return
	}
	states, err := h.repo.ClipStates(c.Request.Context(), c.GetString("user_id"), ids)
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	items := make([]gin.H, 0, len(states))
	for _, s := range states {
		lists := s.ListIDs
		if lists == nil {
			lists = []string{}
		}
		items = append(items, gin.H{"clip_id": s.ClipID, "liked": s.Liked, "saved": s.Saved, "list_ids": lists})
	}
	c.JSON(http.StatusOK, gin.H{"items": items})
}

func (h *LibraryHandlers) HideHistory(c *gin.Context) {
	if err := h.repo.HideHistory(c.Request.Context(), c.GetString("user_id"), c.Param("clip_id")); err != nil {
		handleDomainErr(c, err)
		return
	}
	c.Status(http.StatusNoContent)
}

func (h *LibraryHandlers) ClearHistory(c *gin.Context) {
	if err := h.repo.ClearHistory(c.Request.Context(), c.GetString("user_id")); err != nil {
		handleDomainErr(c, err)
		return
	}
	c.Status(http.StatusNoContent)
}

func (h *LibraryHandlers) listH(l *domain.UserList) gin.H {
	return gin.H{"id": l.ID, "name": l.Name, "item_count": l.ItemCount, "cover_thumbnail_url": ThumbnailURL(l.CoverThumbnailURL, h.storage),
		"created_at": l.CreatedAt.UTC(), "updated_at": l.UpdatedAt.UTC()}
}

func (h *LibraryHandlers) Lists(c *gin.Context) {
	lists, err := h.repo.Lists(c.Request.Context(), c.GetString("user_id"))
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	items := make([]gin.H, 0, len(lists))
	for i := range lists {
		items = append(items, h.listH(&lists[i]))
	}
	c.JSON(http.StatusOK, gin.H{"items": items})
}

// listName: trimmed, 1–60 characters (runes — Vietnamese text), no control characters.
func listName(c *gin.Context) (string, bool) {
	var body struct {
		Name *string `json:"name"`
	}
	if err := c.ShouldBindJSON(&body); err != nil || body.Name == nil {
		return "", false
	}
	name := strings.TrimSpace(*body.Name)
	n := utf8.RuneCountInString(name)
	if n < 1 || n > domain.MaxListNameRune || !utf8.ValidString(name) || strings.ContainsFunc(name, func(r rune) bool { return r < 0x20 || r == 0x7f }) {
		return "", false
	}
	return name, true
}

func (h *LibraryHandlers) CreateList(c *gin.Context) {
	name, ok := listName(c)
	if !ok {
		handleDomainErr(c, domain.ErrValidation)
		return
	}
	l, err := h.repo.CreateList(c.Request.Context(), c.GetString("user_id"), name)
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	c.JSON(http.StatusCreated, h.listH(l))
}

func (h *LibraryHandlers) RenameList(c *gin.Context) {
	name, ok := listName(c)
	if !ok {
		handleDomainErr(c, domain.ErrValidation)
		return
	}
	l, err := h.repo.RenameList(c.Request.Context(), c.GetString("user_id"), c.Param("list_id"), name)
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	c.JSON(http.StatusOK, h.listH(l))
}

func (h *LibraryHandlers) DeleteList(c *gin.Context) {
	if err := h.repo.DeleteList(c.Request.Context(), c.GetString("user_id"), c.Param("list_id")); err != nil {
		handleDomainErr(c, err)
		return
	}
	c.Status(http.StatusNoContent)
}

func (h *LibraryHandlers) ListItems(c *gin.Context) {
	clips, next, err := h.repo.ListItems(c.Request.Context(), c.GetString("user_id"), c.Param("list_id"), cursorParam(c), parseLimit(c.Query("limit"), 10))
	h.clipPage(c, clips, next, err)
}

func (h *LibraryHandlers) setListItem(c *gin.Context, on bool) {
	if err := h.repo.SetListItem(c.Request.Context(), c.GetString("user_id"), c.Param("list_id"), c.Param("clip_id"), on); err != nil {
		handleDomainErr(c, err)
		return
	}
	c.Status(http.StatusNoContent)
}

func (h *LibraryHandlers) AddListItem(c *gin.Context)    { h.setListItem(c, true) }
func (h *LibraryHandlers) RemoveListItem(c *gin.Context) { h.setListItem(c, false) }
