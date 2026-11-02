package handlers

import (
	"context"
	"encoding/json"
	"errors"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

type preferenceFixture struct {
	ids    []string
	writes int
	err    error
}

func (p *preferenceFixture) Get(context.Context, string) ([]string, error) { return p.ids, p.err }
func (p *preferenceFixture) Replace(_ context.Context, _ string, ids []string) error {
	p.writes++
	if p.err == nil {
		p.ids = append([]string{}, ids...)
	}
	return p.err
}

func TestPreferencesValidateDistinctIDsAndReturnStoredValues(t *testing.T) {
	prefs := &preferenceFixture{}
	categories := mocks.NewCategoryRepoMem()
	for _, id := range []string{"cat_one", "cat_two", "cat_three"} {
		categories.M[id] = &domain.Category{ID: id, Name: "Name " + id}
	}
	users := mocks.NewUserRepoMem()
	if err := users.Create(context.Background(), &domain.User{ID: "usr_test", Username: "tester", Email: "test@example.test"}); err != nil {
		t.Fatal(err)
	}
	h := NewAuthHandlers(nil, users, prefs, categories, nil, nil)
	r := gin.New()
	r.Use(func(c *gin.Context) { c.Set("user_id", "usr_test") })
	r.PUT("/preferences", h.UpdatePreferences)
	r.GET("/me", h.GetMe)
	for _, body := range []string{
		`{"category_ids":["cat_one","cat_one","cat_one"]}`,
		`{"category_ids":["cat_one","cat_two","missing"]}`,
		`{"category_ids":["Name cat_one","Name cat_two","Name cat_three"]}`,
	} {
		w := httptest.NewRecorder()
		r.ServeHTTP(w, httptest.NewRequest("PUT", "/preferences", strings.NewReader(body)))
		if w.Code != 422 || prefs.writes != 0 {
			t.Fatalf("invalid preferences wrote data: %d %s", w.Code, w.Body)
		}
	}
	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest("PUT", "/preferences", strings.NewReader(`{"category_ids":["cat_one","cat_two","cat_three"]}`)))
	if w.Code != 200 || prefs.writes != 1 {
		t.Fatalf("valid preferences lost: %d %s", w.Code, w.Body)
	}
	w = httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest("GET", "/me", nil))
	var user struct {
		Preferences []string `json:"preferences"`
	}
	if err := json.Unmarshal(w.Body.Bytes(), &user); err != nil || w.Code != 200 || len(user.Preferences) != 3 {
		t.Fatalf("stored preferences not returned: %d %s", w.Code, w.Body)
	}
	prefs.err = errors.New("storage unavailable")
	w = httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest("PUT", "/preferences", strings.NewReader(`{"category_ids":["cat_one","cat_two","cat_three"]}`)))
	if w.Code != 500 {
		t.Fatalf("failed preference write reported success: %d", w.Code)
	}
}
