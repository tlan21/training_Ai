package auth

import (
	"context"
	"errors"
	"testing"
	"time"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

type ttlSettings struct{ days int }

func (s ttlSettings) Get(context.Context) (*domain.SystemSettings, error) {
	return &domain.SystemSettings{SessionTTLDays: s.days}, nil
}
func (ttlSettings) Update(context.Context, map[string]string) error { return nil }

func status(err error) int {
	var de *domain.DomainError
	if errors.As(err, &de) {
		return de.Status
	}
	return 0
}

func TestAccountSecurity_ChangeResetRevoke(t *testing.T) {
	ctx := context.Background()
	users, sessions := mocks.NewUserRepoMem(), mocks.NewSessionRepoMem()
	svc := New(users, sessions, NewJWT("test-secret-32-chars-minimum-xyz"))
	admin, _, _, err := svc.Register(ctx, "admin", "admin@local", "oldpass123")
	if err != nil {
		t.Fatal(err)
	}
	other, _, otherRefresh, _ := svc.Register(ctx, "viewer", "viewer@local", "viewerpass1")
	_, _, current, _ := svc.Login(ctx, "admin@local", "oldpass123")
	_, _, device2, _ := svc.Login(ctx, "admin@local", "oldpass123")

	// own change: wrong current is 422 (never 401), same/short password rejected, nothing changed
	for _, tc := range []struct{ cur, next string }{{"wrong-pass", "newpass123"}, {"oldpass123", "oldpass123"}, {"oldpass123", "short"}} {
		if got := status(svc.ChangePassword(ctx, admin.ID, current, tc.cur, tc.next)); got != 422 {
			t.Fatalf("%+v: status %d", tc, got)
		}
	}
	if err := svc.ChangePassword(ctx, admin.ID, current, "oldpass123", "newpass123"); err != nil {
		t.Fatal(err)
	}
	if _, _, _, err := svc.Login(ctx, "admin@local", "oldpass123"); err == nil {
		t.Fatal("old password still works")
	}
	if _, _, err := svc.Refresh(ctx, device2); err == nil {
		t.Fatal("other device session survived password change")
	}
	current2, current, err := svc.Refresh(ctx, current)
	if err != nil || current2 == "" {
		t.Fatalf("current session was revoked: %v", err)
	}

	// admin reset: not self, target must exist, all target sessions revoked
	if got := status(svc.AdminResetPassword(ctx, admin.ID, admin.ID, "whatever12")); got != 409 {
		t.Fatalf("self reset status %d", got)
	}
	if got := status(svc.AdminResetPassword(ctx, admin.ID, "usr_missing", "whatever12")); got != 404 {
		t.Fatalf("missing user status %d", got)
	}
	if got := status(svc.AdminResetPassword(ctx, admin.ID, other.ID, "short")); got != 422 {
		t.Fatalf("short password status %d", got)
	}
	if err := svc.AdminResetPassword(ctx, admin.ID, other.ID, "resetpass99"); err != nil {
		t.Fatal(err)
	}
	if _, _, err := svc.Refresh(ctx, otherRefresh); err == nil {
		t.Fatal("target session survived reset")
	}
	if _, _, _, err := svc.Login(ctx, "viewer@local", "resetpass99"); err != nil {
		t.Fatalf("new password rejected: %v", err)
	}

	// revoke others keeps only the current session
	_, _, _, _ = svc.Login(ctx, "admin@local", "newpass123")
	_, _, _, _ = svc.Login(ctx, "admin@local", "newpass123")
	n, err := svc.RevokeOtherSessions(ctx, admin.ID, current)
	if err != nil || n != 2 {
		t.Fatalf("revoked %d %v", n, err)
	}
	if _, _, err := svc.Refresh(ctx, current); err != nil {
		t.Fatal("current session revoked")
	}
}

func TestRefreshTTLFollowsSettings(t *testing.T) {
	ctx := context.Background()
	sessions := mocks.NewSessionRepoMem()
	svc := New(mocks.NewUserRepoMem(), sessions, NewJWT("test-secret-32-chars-minimum-xyz"))
	if svc.RefreshTTL(ctx) != 7*24*time.Hour {
		t.Fatal("default ttl")
	}
	svc.WithSettings(ttlSettings{days: 0})
	if svc.RefreshTTL(ctx) != 7*24*time.Hour {
		t.Fatal("invalid stored value must fall back to 7 days")
	}
	svc.WithSettings(ttlSettings{days: 2})
	if _, _, _, err := svc.Register(ctx, "u", "u@local", "password123"); err != nil {
		t.Fatal(err)
	}
	for _, s := range sessions.M {
		if d := time.Until(s.ExpiresAt); d < 47*time.Hour || d > 48*time.Hour {
			t.Fatalf("session expiry %v, want 2 days", d)
		}
	}
}
