package handlers

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"traning_ai/backend/internal/domain"
)

// INT-63: Client and CMS sessions live in separate cookies, so a login/logout in one app never touches the other.
type sessionsFake struct{ revoked []string }

func (f *sessionsFake) Register(context.Context, string, string, string) (*domain.User, string, string, error) {
	return nil, "", "", nil
}
func (f *sessionsFake) Login(_ context.Context, email, _ string) (*domain.User, string, string, error) {
	return &domain.User{ID: "usr_" + email, Role: domain.RoleClient}, "access-" + email, "raw-" + email, nil
}
func (f *sessionsFake) Refresh(_ context.Context, raw string) (string, string, error) {
	return "access-" + raw, raw + "-next", nil
}
func (f *sessionsFake) Logout(_ context.Context, raw string) error {
	f.revoked = append(f.revoked, raw)
	return nil
}
func (f *sessionsFake) ForgotPassword(context.Context, string) (string, error) { return "", nil }
func (f *sessionsFake) ResetPassword(context.Context, string, string) error    { return nil }
func (f *sessionsFake) RefreshTTL(context.Context) time.Duration               { return time.Hour }

type prefsFake struct{}

func (prefsFake) Get(context.Context, string) ([]string, error)     { return nil, nil }
func (prefsFake) Replace(context.Context, string, []string) error { return nil }

func TestRefreshCookieIsScopedPerApp(t *testing.T) {
	svc := &sessionsFake{}
	h := NewAuthHandlers(svc, nil, prefsFake{}, nil, nil, nil)
	r := gin.New()
	r.POST("/login", h.Login)
	r.POST("/refresh", h.Refresh)
	r.POST("/logout", h.Logout)
	call := func(path, app, body string, cookies ...*http.Cookie) *httptest.ResponseRecorder {
		req := httptest.NewRequest("POST", path, strings.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		if app != "" {
			req.Header.Set("X-App", app)
		}
		for _, ck := range cookies {
			req.AddCookie(ck)
		}
		w := httptest.NewRecorder()
		r.ServeHTTP(w, req)
		return w
	}
	cookie := func(w *httptest.ResponseRecorder) *http.Cookie {
		cs := w.Result().Cookies()
		if len(cs) != 1 {
			t.Fatalf("want exactly one Set-Cookie, got %v (%d %s)", cs, w.Code, w.Body)
		}
		return cs[0]
	}
	client := cookie(call("/login", "", `{"email":"viewer","password":"x"}`))
	cms := cookie(call("/login", "cms", `{"email":"admin","password":"x"}`))
	if client.Name != "refresh" || cms.Name != "cms_refresh" || !client.HttpOnly || !cms.HttpOnly {
		t.Fatalf("cookie names/flags: client %+v cms %+v", client, cms)
	}
	// The browser sends both cookies to both apps; each app must use only its own.
	if got := cookie(call("/refresh", "cms", "", client, cms)); got.Name != "cms_refresh" || got.Value != "raw-admin-next" {
		t.Fatalf("CMS refresh used the wrong session: %+v", got)
	}
	if got := cookie(call("/refresh", "", "", client, cms)); got.Name != "refresh" || got.Value != "raw-viewer-next" {
		t.Fatalf("Client refresh used the wrong session: %+v", got)
	}
	// CMS logout revokes and clears only the CMS session.
	if got := cookie(call("/logout", "cms", "", client, cms)); got.Name != "cms_refresh" || got.MaxAge >= 0 {
		t.Fatalf("CMS logout cleared %+v", got)
	}
	if len(svc.revoked) != 1 || svc.revoked[0] != "raw-admin" {
		t.Fatalf("CMS logout revoked %v", svc.revoked)
	}
	if got := cookie(call("/logout", "", "", client, cms)); got.Name != "refresh" || svc.revoked[1] != "raw-viewer" {
		t.Fatalf("Client logout: %+v %v", got, svc.revoked)
	}
}
