package cms

import (
	"context"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/handlers"
)

type accountFake struct{ actor, target, refresh string }

func (f *accountFake) ChangePassword(_ context.Context, userID, rawRefresh, current, next string) error {
	f.actor, f.refresh = userID, rawRefresh
	if current != "right-pass" {
		return domain.NewError("INVALID_CURRENT_PASSWORD", "Current password is incorrect", 422)
	}
	return nil
}
func (f *accountFake) AdminResetPassword(_ context.Context, actorID, targetID, next string) error {
	f.actor, f.target = actorID, targetID
	return nil
}
func (f *accountFake) RevokeOtherSessions(_ context.Context, userID, rawRefresh string) (int, error) {
	f.actor, f.refresh = userID, rawRefresh
	return 3, nil
}

// router mirrors cmd/gateway wiring: CMS group admin|editor, user management admin-only.
func accountRouter(role string, fake *accountFake, settings *settingsFixture) *gin.Engine {
	r := gin.New()
	g := r.Group("/cms", func(c *gin.Context) { c.Set("user_id", "usr_me"); c.Set("user_role", role) }, handlers.RequireRole("admin", "editor"))
	acc := NewAccountHandlers(fake)
	sys := NewSystemHandlers(nil, settings)
	g.PUT("/settings", sys.UpdateSettings)
	g.POST("/me/password", acc.ChangePassword)
	g.POST("/me/sessions/revoke-others", acc.RevokeOtherSessions)
	admin := g.Group("", handlers.RequireRole("admin"))
	admin.POST("/users/:id/password", acc.ResetUserPassword)
	return r
}

func do(r *gin.Engine, method, path, body string) *httptest.ResponseRecorder {
	w := httptest.NewRecorder()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Cookie", "refresh=raw-cookie")
	r.ServeHTTP(w, req)
	return w
}

func TestAccountRoutes_RolesAndErrors(t *testing.T) {
	fake := &accountFake{}
	editor := accountRouter("editor", fake, &settingsFixture{})
	if w := do(editor, "POST", "/cms/users/usr_x/password", `{"new_password":"password99"}`); w.Code != 403 || fake.target != "" {
		t.Fatalf("editor reset: %d", w.Code)
	}
	if w := do(editor, "POST", "/cms/me/password", `{"current_password":"wrong","new_password":"password99"}`); w.Code != 422 || !strings.Contains(w.Body.String(), "INVALID_CURRENT_PASSWORD") {
		t.Fatalf("wrong current: %d %s", w.Code, w.Body)
	}
	if w := do(editor, "POST", "/cms/me/password", `{"current_password":"right-pass","new_password":"password99"}`); w.Code != 204 || fake.actor != "usr_me" || fake.refresh != "raw-cookie" {
		t.Fatalf("own change: %d %+v", w.Code, fake)
	}
	if w := do(editor, "POST", "/cms/me/password", `{"new_password":"password99"}`); w.Code != 422 {
		t.Fatalf("missing current: %d", w.Code)
	}
	if w := do(editor, "POST", "/cms/me/sessions/revoke-others", ``); w.Code != 200 || strings.TrimSpace(w.Body.String()) != `{"revoked":3}` {
		t.Fatalf("revoke: %d %s", w.Code, w.Body)
	}
	if w := do(accountRouter("client", fake, &settingsFixture{}), "POST", "/cms/me/password", `{}`); w.Code != 403 {
		t.Fatalf("client reached CMS: %d", w.Code)
	}
	admin := accountRouter("admin", fake, &settingsFixture{})
	if w := do(admin, "POST", "/cms/users/usr_x/password", `{"new_password":"password99"}`); w.Code != 204 || fake.actor != "usr_me" || fake.target != "usr_x" {
		t.Fatalf("admin reset: %d %+v", w.Code, fake)
	}
	if w := do(admin, "POST", "/cms/users/usr_x/password", `{}`); w.Code != 422 {
		t.Fatalf("empty reset body: %d", w.Code)
	}
}

func TestSettings_AdminOnlyFields(t *testing.T) {
	editorStore := &settingsFixture{}
	editor := accountRouter("editor", &accountFake{}, editorStore)
	if w := do(editor, "PUT", "/cms/settings", `{"auto_highlight_enabled":false,"session_ttl_days":3}`); w.Code != 403 || editorStore.values != nil {
		t.Fatalf("editor wrote admin field: %d %+v", w.Code, editorStore.values)
	}
	if w := do(editor, "PUT", "/cms/settings", `{"auto_highlight_enabled":false}`); w.Code != 200 || editorStore.values["auto_highlight_enabled"] != "false" {
		t.Fatalf("editor AI flag regression: %d", w.Code)
	}
	store := &settingsFixture{}
	admin := accountRouter("admin", &accountFake{}, store)
	for _, body := range []string{`{"system_name":"   "}`, `{"system_name":"` + strings.Repeat("a", 61) + `"}`, `{"display_timezone":"Europe/Paris"}`, `{"session_ttl_days":0}`, `{"session_ttl_days":31}`} {
		if w := do(admin, "PUT", "/cms/settings", body); w.Code != 422 || store.values != nil {
			t.Fatalf("%s: %d %+v", body, w.Code, store.values)
		}
	}
	w := do(admin, "PUT", "/cms/settings", `{"system_name":"  Phòng biên tập  ","display_timezone":"UTC","notify_failed_jobs":false,"notify_uncategorized_videos":true,"session_ttl_days":30}`)
	want := map[string]string{"system_name": "Phòng biên tập", "display_timezone": "UTC", "notify_failed_jobs": "false", "notify_uncategorized_videos": "true", "session_ttl_days": "30"}
	if w.Code != 200 || len(store.values) != len(want) {
		t.Fatalf("admin save: %d %+v", w.Code, store.values)
	}
	for k, v := range want {
		if store.values[k] != v {
			t.Fatalf("%s=%q want %q", k, store.values[k], v)
		}
	}
}
