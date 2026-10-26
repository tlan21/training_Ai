package cms

import (
	"context"
	"errors"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"traning_ai/backend/internal/domain"
)

type settingsFixture struct {
	values map[string]string
	err    error
}

func (s *settingsFixture) Get(context.Context) (*domain.SystemSettings, error) {
	return &domain.SystemSettings{HighlightThreshold: 42, AIServiceAPIKey: "sk-local-private"}, s.err
}
func (s *settingsFixture) Update(_ context.Context, values map[string]string) error {
	s.values = values
	return s.err
}

func TestSettings_ValidationMaskAndPersistenceErrors(t *testing.T) {
	fixture := &settingsFixture{}
	h := NewSystemHandlers(nil, fixture)
	r := gin.New()
	r.GET("/settings", h.GetSettings)
	r.PUT("/settings", h.UpdateSettings)
	get := httptest.NewRecorder()
	r.ServeHTTP(get, httptest.NewRequest("GET", "/settings", nil))
	if get.Code != 200 || strings.Contains(get.Body.String(), "sk-local-private") || !strings.Contains(get.Body.String(), "sk-local-••••") {
		t.Fatalf("key not masked: %d %s", get.Code, get.Body)
	}
	for _, tc := range []struct {
		body   string
		status int
	}{
		{`{"highlight_threshold":0,"auto_highlight_enabled":false,"ai_service_api_key":"sk-local-••••"}`, 200},
		{`{"highlight_threshold":101}`, 422},
		{`{"asr_warning_threshold":-1}`, 422},
	} {
		w := httptest.NewRecorder()
		req := httptest.NewRequest("PUT", "/settings", strings.NewReader(tc.body))
		req.Header.Set("Content-Type", "application/json")
		r.ServeHTTP(w, req)
		if w.Code != tc.status {
			t.Fatalf("got %d want %d: %s", w.Code, tc.status, w.Body)
		}
	}
	if fixture.values["highlight_threshold"] != "0" || fixture.values["auto_highlight_enabled"] != "false" || len(fixture.values) != 2 {
		t.Fatalf("patch lost false/zero or saved masked key: %+v", fixture.values)
	}
	fixture.err = errors.New("database unavailable")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest("PUT", "/settings", strings.NewReader(`{}`)))
	if w.Code != 500 || !strings.Contains(w.Body.String(), `"error"`) {
		t.Fatalf("failed write reported success: %d %s", w.Code, w.Body)
	}
}
