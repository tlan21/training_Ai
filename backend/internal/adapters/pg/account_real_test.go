package pg

import (
	"context"
	"testing"
	"time"

	"traning_ai/backend/internal/auth"
)

// INT-59 on real PostgreSQL. TEMP tables on one connection shadow public ones, so live accounts/settings are untouched.
func TestAccountSecurity_RealPostgres(t *testing.T) {
	db := integrationDB(t)
	ctx := context.Background()
	for _, table := range []string{"users", "user_sessions", "system_settings"} {
		if _, err := db.Exec(ctx, "CREATE TEMP TABLE "+table+" (LIKE public."+table+" INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES)"); err != nil {
			t.Fatal(err)
		}
	}
	settings := &SettingsRepo{DB: db}
	if _, err := db.Exec(ctx, `INSERT INTO system_settings(key,value) VALUES('highlight_threshold','75'),('asr_warning_threshold','65'),
		('auto_highlight_enabled','true'),('auto_subtitle_enabled','true'),('default_subtitle_lang','vi'),('ai_service_api_key','sk-local-test')`); err != nil {
		t.Fatal(err)
	}
	s, err := settings.Get(ctx)
	if err != nil || s.SystemName != "AI Video CMS" || s.DisplayTimezone != "Asia/Ho_Chi_Minh" || !s.NotifyFailedJobs || !s.NotifyUncategorizedVideos || s.SessionTTLDays != 7 {
		t.Fatalf("defaults without stored keys: %+v %v", s, err)
	}
	if err := settings.Update(ctx, map[string]string{"system_name": "Phòng biên tập", "display_timezone": "UTC", "notify_failed_jobs": "false", "session_ttl_days": "2"}); err != nil {
		t.Fatal(err)
	}
	if s, err = settings.Get(ctx); err != nil || s.SystemName != "Phòng biên tập" || s.DisplayTimezone != "UTC" || s.NotifyFailedJobs || !s.NotifyUncategorizedVideos || s.SessionTTLDays != 2 {
		t.Fatalf("stored settings: %+v %v", s, err)
	}

	users, sessions := &UserRepo{DB: db}, &SessionRepo{DB: db}
	svc := auth.New(users, sessions, auth.NewJWT("test-secret-32-chars-minimum-xyz")).WithSettings(settings)
	admin, _, current, err := svc.Register(ctx, "qa_admin", "qa_admin@int59.local", "oldpass123")
	if err != nil {
		t.Fatal(err)
	}
	var expires time.Time
	if err := db.QueryRow(ctx, `SELECT expires_at FROM user_sessions WHERE user_id=$1`, admin.ID).Scan(&expires); err != nil || time.Until(expires) > 48*time.Hour || time.Until(expires) < 47*time.Hour {
		t.Fatalf("session ttl from settings: %v %v", expires, err)
	}
	other, _, otherRefresh, _ := svc.Register(ctx, "qa_viewer", "qa_viewer@int59.local", "viewerpass1")
	_, _, _, _ = svc.Login(ctx, "qa_admin@int59.local", "oldpass123")
	_, _, _, _ = svc.Login(ctx, "qa_admin@int59.local", "oldpass123")

	var before string
	_ = db.QueryRow(ctx, `SELECT password_hash FROM users WHERE id=$1`, admin.ID).Scan(&before)
	if err := svc.ChangePassword(ctx, admin.ID, current, "oldpass123", "newpass123"); err != nil {
		t.Fatal(err)
	}
	var after string
	var left int
	if err := db.QueryRow(ctx, `SELECT password_hash,(SELECT count(*) FROM user_sessions WHERE user_id=$1) FROM users WHERE id=$1`, admin.ID).Scan(&after, &left); err != nil || after == before || after[:4] != "$2a$" || left != 1 {
		t.Fatalf("change: bcrypt=%q sessions=%d %v", after[:4], left, err)
	}
	if _, _, _, err := svc.Login(ctx, "qa_admin@int59.local", "newpass123"); err != nil {
		t.Fatal(err)
	}
	if n, err := svc.RevokeOtherSessions(ctx, admin.ID, current); err != nil || n != 1 {
		t.Fatalf("revoke others: %d %v", n, err)
	}
	if err := svc.AdminResetPassword(ctx, admin.ID, other.ID, "resetpass99"); err != nil {
		t.Fatal(err)
	}
	if err := db.QueryRow(ctx, `SELECT count(*) FROM user_sessions WHERE user_id=$1`, other.ID).Scan(&left); err != nil || left != 0 {
		t.Fatalf("target sessions left %d %v", left, err)
	}
	if _, _, err := svc.Refresh(ctx, otherRefresh); err == nil {
		t.Fatal("revoked refresh still accepted")
	}
	if _, _, _, err := svc.Login(ctx, "qa_viewer@int59.local", "resetpass99"); err != nil {
		t.Fatal(err)
	}
	if err := svc.AdminResetPassword(ctx, admin.ID, "usr_does_not_exist", "resetpass99"); err == nil {
		t.Fatal("missing user reset succeeded")
	}
}
