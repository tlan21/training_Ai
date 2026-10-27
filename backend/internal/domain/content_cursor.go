package domain

import (
	"encoding/base64"
	"encoding/json"
	"strings"
	"time"
)

// ContentCursor fixes ranking time while current publication visibility remains live.
type ContentCursor struct {
	Scope     string    `json:"scope"`
	Snapshot  time.Time `json:"snapshot"`
	Rank      int64     `json:"rank"`
	CreatedAt time.Time `json:"created_at"`
	ID        string    `json:"id"`
}

func ParseContentCursor(raw, scope string, limit int) (ContentCursor, error) {
	p := ContentCursor{Scope: scope, Snapshot: time.Now().UTC().Truncate(time.Microsecond)}
	if limit < 1 || limit > 50 || len(raw) > 2048 {
		return p, ErrValidation
	}
	if raw == "" {
		return p, nil
	}
	data, err := base64.RawURLEncoding.DecodeString(raw)
	p = ContentCursor{}
	if err != nil || json.Unmarshal(data, &p) != nil {
		return p, ErrValidation
	}
	prefix := "vid_"
	if scope == "feed" {
		prefix = "clp_"
	}
	if p.Scope != scope || p.Snapshot.IsZero() || p.Snapshot.After(time.Now().Add(time.Minute)) ||
		p.CreatedAt.IsZero() || p.CreatedAt.After(p.Snapshot) || p.Rank < 0 ||
		!strings.HasPrefix(p.ID, prefix) || len(p.ID) <= len(prefix) || len(p.ID) > 100 {
		return p, ErrValidation
	}
	return p, nil
}

func (p ContentCursor) Encode() (string, error) {
	data, err := json.Marshal(p)
	return base64.RawURLEncoding.EncodeToString(data), err
}

func (p ContentCursor) After(rank int64, created time.Time, id string) bool {
	return !created.After(p.Snapshot) && (p.ID == "" || rank < p.Rank ||
		(rank == p.Rank && (created.Before(p.CreatedAt) || (created.Equal(p.CreatedAt) && id < p.ID))))
}
