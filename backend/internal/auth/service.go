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
	resetTTL   = 30 * time.Minute
)

type Service struct {
	users    ports.UserRepository
	sessions ports.SessionRepository
	resets   ports.PasswordResetRepository
	settings ports.SettingsRepository
	jwt      *JWT
}

func New(users ports.UserRepository, sessions ports.SessionRepository, jwt *JWT) *Service {
	return &Service{users: users, sessions: sessions, jwt: jwt}
}

func NewWithResets(users ports.UserRepository, sessions ports.SessionRepository, resets ports.PasswordResetRepository, jwt *JWT) *Service {
	return &Service{users: users, sessions: sessions, resets: resets, jwt: jwt}
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

func (s *Service) ForgotPassword(ctx context.Context, email string) (string, error) {
	u, err := s.users.GetByEmail(ctx, email)
	if err != nil || u.Role != domain.RoleClient {
		// Public recovery never resets pre-provisioned CMS accounts or reveals whether they exist.
		return "", nil
	}
	raw := randomToken()
	h := hashRefresh(raw)
	if s.resets != nil {
		_, _ = s.resets.Create(ctx, u.ID, h, time.Now().Add(resetTTL))
	}
	return raw, nil
}

func (s *Service) ResetPassword(ctx context.Context, rawToken, newPassword string) error {
	if len(newPassword) < 8 {
		return domain.NewError("VALIDATION_ERROR", "new_password must be at least 8 chars", 400)
	}
	if s.resets == nil {
		return domain.NewError("UNAUTHORIZED", "Invalid or expired reset token", 401)
	}
	h := hashRefresh(rawToken)
	rec, err := s.resets.GetByHash(ctx, h)
	if err != nil {
		return domain.NewError("UNAUTHORIZED", "Invalid or expired reset token", 401)
	}
	if time.Now().After(rec.ExpiresAt) {
		_ = s.resets.Delete(ctx, rec.ID)
		return domain.NewError("UNAUTHORIZED", "Reset token expired", 401)
	}
	hash, _ := bcrypt.GenerateFromPassword([]byte(newPassword), 12)
	if err := s.users.UpdatePassword(ctx, rec.UserID, string(hash)); err != nil {
		return err
	}
	_ = s.resets.Delete(ctx, rec.ID)
	_ = s.sessions.DeleteByUser(ctx, rec.UserID)
	return nil
}

// WithSettings makes the refresh lifetime follow system_settings.session_ttl_days (INT-59).
func (s *Service) WithSettings(settings ports.SettingsRepository) *Service {
	s.settings = settings
	return s
}

// RefreshTTL is the lifetime of sessions created now; existing sessions keep their expiry.
func (s *Service) RefreshTTL(ctx context.Context) time.Duration {
	if s.settings != nil {
		if st, err := s.settings.Get(ctx); err == nil && st.SessionTTLDays >= 1 && st.SessionTTLDays <= 30 {
			return time.Duration(st.SessionTTLDays) * 24 * time.Hour
		}
	}
	return refreshTTL
}

func validNewPassword(p string) error {
	if len(p) < 8 || len(p) > 72 { // bcrypt ignores bytes past 72
		return domain.NewError("VALIDATION_ERROR", "new_password must be 8-72 bytes", 422)
	}
	return nil
}

func (s *Service) setPassword(ctx context.Context, userID, password string) error {
	hash, err := bcrypt.GenerateFromPassword([]byte(password), 12)
	if err != nil {
		return err
	}
	return s.users.UpdatePassword(ctx, userID, string(hash))
}

// ChangePassword updates the caller's own password and revokes every other session (the one behind rawRefresh stays).
// A wrong current password is 422, not 401, so the CMS does not treat it as an expired login.
func (s *Service) ChangePassword(ctx context.Context, userID, rawRefresh, current, next string) error {
	if err := validNewPassword(next); err != nil {
		return err
	}
	u, err := s.users.Get(ctx, userID)
	if err != nil {
		return err
	}
	if bcrypt.CompareHashAndPassword([]byte(u.PasswordHash), []byte(current)) != nil {
		return domain.NewError("INVALID_CURRENT_PASSWORD", "Current password is incorrect", 422)
	}
	if current == next {
		return domain.NewError("VALIDATION_ERROR", "new_password must differ from current_password", 422)
	}
	if err := s.setPassword(ctx, userID, next); err != nil {
		return err
	}
	_, err = s.sessions.DeleteByUserExcept(ctx, userID, hashRefresh(rawRefresh))
	return err
}

// AdminResetPassword sets another account's password and revokes all of that account's sessions.
func (s *Service) AdminResetPassword(ctx context.Context, actorID, targetID, next string) error {
	if actorID == targetID {
		return domain.NewError("SELF_PASSWORD_RESET", "Use the Security tab to change your own password", 409)
	}
	if err := validNewPassword(next); err != nil {
		return err
	}
	if _, err := s.users.Get(ctx, targetID); err != nil {
		return err
	}
	if err := s.setPassword(ctx, targetID, next); err != nil {
		return err
	}
	return s.sessions.DeleteByUser(ctx, targetID)
}

// RevokeOtherSessions signs the caller out everywhere except the session behind rawRefresh.
func (s *Service) RevokeOtherSessions(ctx context.Context, userID, rawRefresh string) (int, error) {
	return s.sessions.DeleteByUserExcept(ctx, userID, hashRefresh(rawRefresh))
}

func (s *Service) issueTokens(ctx context.Context, u *domain.User) (*domain.User, string, string, error) {
	access, err := s.jwt.Sign(u.ID, string(u.Role), accessTTL)
	if err != nil {
		return nil, "", "", err
	}
	raw := randomToken()
	h := hashRefresh(raw)
	_, err = s.sessions.Create(ctx, u.ID, h, time.Now().Add(s.RefreshTTL(ctx)))
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
