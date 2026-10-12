package auth

import (
	"context"
	"testing"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

func TestAuth_RegisterLoginRefresh(t *testing.T) {
	ur := mocks.NewUserRepoMem()
	sr := mocks.NewSessionRepoMem()
	svc := New(ur, sr, NewJWT("test-secret-32-chars-minimum-xyz"))

	ctx := context.Background()
	u, access, refresh, err := svc.Register(ctx, "alice", "a@b.c", "password123")
	if err != nil || u == nil || access == "" || refresh == "" {
		t.Fatalf("register %v", err)
	}
	// duplicate email
	_, _, _, err = svc.Register(ctx, "bob", "a@b.c", "password123")
	if err != domain.ErrEmailTaken {
		t.Fatalf("want EMAIL_TAKEN got %v", err)
	}
	// login ok
	_, access2, refresh2, err := svc.Login(ctx, "a@b.c", "password123")
	if err != nil || access2 == "" || refresh2 == "" {
		t.Fatalf("login %v", err)
	}
	// login bad password
	_, _, _, err = svc.Login(ctx, "a@b.c", "wrong")
	if err == nil {
		t.Fatal("want unauthorized")
	}
	// refresh rotation: old token invalidated
	access3, refresh3, err := svc.Refresh(ctx, refresh2)
	if err != nil || access3 == "" || refresh3 == "" {
		t.Fatalf("refresh %v", err)
	}
	_, _, err = svc.Refresh(ctx, refresh2)
	if err == nil {
		t.Fatal("old refresh should be invalid after rotation")
	}
	// JWT verify
	claims, err := NewJWT("test-secret-32-chars-minimum-xyz").Verify(access3)
	if err != nil || claims.UserID != u.ID {
		t.Fatalf("jwt verify %v", err)
	}
	// logout invalidates
	_ = svc.Logout(ctx, refresh3)
	_, _, err = svc.Refresh(ctx, refresh3)
	if err == nil {
		t.Fatal("after logout refresh should fail")
	}
}
