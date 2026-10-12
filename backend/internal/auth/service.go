package auth

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"time"

	"golang.org/x/crypto/bcrypt"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/ports"
)

const (
	accessTTL  = 15 * time.Minute
	refreshTTL = 7 * 24 * time.Hour
)

type Service struct {
	users    ports.UserRepository
	sessions ports.SessionRepository
	jwt      *JWT
}

func New(users ports.UserRepository, sessions ports.SessionRepository, jwt *JWT) *Service {
	return &Service{users: users, sessions: sessions, jwt: jwt}
}

func (s *Service) Register(ctx context.Context, username, email, password string) (*domain.User, string, string, error) {
	hash, _ := bcrypt.GenerateFromPassword([]byte(password), 12)
	u := &domain.User{
		ID:           "usr_" + newID(),
		Username:     username,
		Email:        email,
		PasswordHash: string(hash),
		Role:         domain.RoleClient,
		CreatedAt:    time.Now(),
		UpdatedAt:    time.Now(),
	}
	if err := s.users.Create(ctx, u); err != nil {
		return nil, "", "", err
	}
	return s.issueTokens(ctx, u)
}

func (s *Service) Login(ctx context.Context, email, password string) (*domain.User, string, string, error) {
	u, err := s.users.GetByEmail(ctx, email)
	if err != nil {
		return nil, "", "", domain.ErrUnauthorized
	}
	if bcrypt.CompareHashAndPassword([]byte(u.PasswordHash), []byte(password)) != nil {
		return nil, "", "", domain.ErrUnauthorized
	}
	return s.issueTokens(ctx, u)
}

func (s *Service) Refresh(ctx context.Context, rawRefresh string) (string, string, error) {
	h := hashRefresh(rawRefresh)
	sess, err := s.sessions.GetByHash(ctx, h)
	if err != nil {
		return "", "", domain.ErrUnauthorized
	}
	if time.Now().After(sess.ExpiresAt) {
		_ = s.sessions.Delete(ctx, sess.ID)
		return "", "", domain.ErrUnauthorized
	}
	_ = s.sessions.Delete(ctx, sess.ID)
	u, err := s.users.Get(ctx, sess.UserID)
	if err != nil {
		return "", "", domain.ErrUnauthorized
	}
	_, access, refresh, err := s.issueTokens(ctx, u)
	return access, refresh, err
}

func (s *Service) Logout(ctx context.Context, rawRefresh string) error {
	if rawRefresh == "" {
		return nil
	}
	h := hashRefresh(rawRefresh)
	sess, err := s.sessions.GetByHash(ctx, h)
	if err != nil {
		return nil
	}
	return s.sessions.Delete(ctx, sess.ID)
}

func (s *Service) issueTokens(ctx context.Context, u *domain.User) (*domain.User, string, string, error) {
	access, err := s.jwt.Sign(u.ID, string(u.Role), accessTTL)
	if err != nil {
		return nil, "", "", err
	}
	raw := randomToken()
	h := hashRefresh(raw)
	_, err = s.sessions.Create(ctx, u.ID, h, time.Now().Add(refreshTTL))
	if err != nil {
		return nil, "", "", err
	}
	return u, access, raw, nil
}

func hashRefresh(s string) string {
	h := sha256.Sum256([]byte(s))
	return hex.EncodeToString(h[:])
}

func randomToken() string {
	b := make([]byte, 32)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

func newID() string {
	// short id; caller prefixes usr_/ses_ etc outside or here
	b := make([]byte, 8)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}
