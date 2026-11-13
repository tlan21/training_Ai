package domain

import (
	"net/http"
	"time"
)

// INT-61 (API 0.13.0): personal library state. user_interactions stays the append-only event log;
// these types are what the user currently sees (unlike / unsave / hide only change visibility).

const (
	MarkLike = "like"
	MarkSave = "save"

	MaxUserLists    = 50
	MaxListItems    = 500
	MaxListNameRune = 60
	MaxClipStateIDs = 50
)

type UserList struct {
	ID                string
	UserID            string
	Name              string
	ItemCount         int
	CoverThumbnailURL *string
	CreatedAt         time.Time
	UpdatedAt         time.Time
}

type ClipState struct {
	ClipID  string
	Liked   bool
	Saved   bool
	ListIDs []string
}

var (
	ErrListNotFound  = NewError("LIST_NOT_FOUND", "List not found", http.StatusNotFound)
	ErrListNameTaken = NewError("LIST_NAME_TAKEN", "A list with this name already exists", http.StatusConflict)
	ErrListLimit     = NewError("LIST_LIMIT", "List limit reached", http.StatusConflict)
	ErrListFull      = NewError("LIST_FULL", "List is full", http.StatusConflict)
)
