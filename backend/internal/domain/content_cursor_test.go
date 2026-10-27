package domain

import (
	"encoding/base64"
	"strings"
	"testing"
	"time"
)

func TestContentCursorValidationAndStableOrdering(t *testing.T) {
	p, err := ParseContentCursor("", "feed", 2)
	if err != nil || p.Snapshot.IsZero() {
		t.Fatal(p, err)
	}
	p.Rank, p.CreatedAt, p.ID = 3, p.Snapshot.Add(-time.Hour), "clp_anchor"
	raw, err := p.Encode()
	if err != nil {
		t.Fatal(err)
	}
	got, err := ParseContentCursor(raw, "feed", 5)
	if err != nil || got != p {
		t.Fatal(got, err)
	}
	for _, test := range []struct {
		rank    int64
		created time.Time
		id      string
		want    bool
	}{
		{2, p.CreatedAt, "clp_z", true}, {4, p.CreatedAt, "clp_z", false},
		{3, p.CreatedAt.Add(-time.Second), "clp_z", true}, {3, p.CreatedAt.Add(time.Second), "clp_z", false},
		{3, p.CreatedAt, "clp_a", true}, {3, p.CreatedAt, "clp_z", false}, {3, p.CreatedAt, p.ID, false},
		{0, p.Snapshot.Add(time.Second), "clp_new", false},
	} {
		if got.After(test.rank, test.created, test.id) != test.want {
			t.Fatalf("ordering %+v", test)
		}
	}
	for _, scope := range []string{"videos/newest/", "videos/trending/cat_x"} {
		if _, err := ParseContentCursor(raw, scope, 2); err != ErrValidation {
			t.Fatal("cross-scope cursor accepted")
		}
	}
	for _, value := range []string{"not-base64!", "e30", strings.Repeat("a", 2049), base64.RawURLEncoding.EncodeToString([]byte(`{"id":"clp_missing_scope","created_at":"2026-01-01T00:00:00Z"}`))} {
		if _, err := ParseContentCursor(value, "feed", 2); err != ErrValidation {
			t.Fatal("invalid cursor accepted", value)
		}
	}
	for _, limit := range []int{0, -1, 51} {
		if _, err := ParseContentCursor("", "feed", limit); err != ErrValidation {
			t.Fatal("invalid limit accepted")
		}
	}
	for _, mutate := range []func(*ContentCursor){
		func(p *ContentCursor) { p.Rank = -1 }, func(p *ContentCursor) { p.ID = "vid_wrong" },
		func(p *ContentCursor) { p.Snapshot = time.Now().Add(time.Hour) },
		func(p *ContentCursor) { p.CreatedAt = p.Snapshot.Add(time.Second) },
		func(p *ContentCursor) { p.CreatedAt = time.Time{} },
	} {
		bad := p
		mutate(&bad)
		value, err := bad.Encode()
		if err != nil {
			t.Fatal(err)
		}
		if _, err := ParseContentCursor(value, "feed", 2); err != ErrValidation {
			t.Fatalf("accepted invalid position %+v", bad)
		}
	}
}
