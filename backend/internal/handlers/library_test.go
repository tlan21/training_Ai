package handlers

import (
	"context"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/ports"
)

type libraryFake struct {
	ports.LibraryRepository
	created bool
	states  []string
	names   []string
	err     error
}

func (f *libraryFake) SetMark(_ context.Context, _, _, _ string, on bool) (bool, string, error) {
	return f.created && on, "vid_x", f.err
}
func (f *libraryFake) ClipStates(_ context.Context, _ string, ids []string) ([]domain.ClipState, error) {
	f.states = ids
	return []domain.ClipState{{ClipID: ids[0], Liked: true}}, nil
}
func (f *libraryFake) CreateList(_ context.Context, _, name string) (*domain.UserList, error) {
	f.names = append(f.names, name)
	return &domain.UserList{ID: "lst_1", Name: name}, f.err
}

type eventsFake struct{ added []domain.Interaction }

func (e *eventsFake) Add(_ context.Context, i *domain.Interaction) error {
	e.added = append(e.added, *i)
	return nil
}

func libraryRouter(repo *libraryFake, events *eventsFake) *gin.Engine {
	h := NewLibraryHandlers(repo, events, nil)
	r := gin.New()
	r.Use(func(c *gin.Context) { c.Set("user_id", "usr_t") })
	r.PUT("/likes/:clip_id", h.Like)
	r.DELETE("/likes/:clip_id", h.Unlike)
	r.PUT("/saved/:clip_id", h.Save)
	r.GET("/clip-states", h.ClipStates)
	r.POST("/lists", h.CreateList)
	return r
}

func do(r *gin.Engine, method, path, body string) *httptest.ResponseRecorder {
	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest(method, path, strings.NewReader(body)))
	return w
}

func TestLibraryMarkLogsOneEventOnlyForANewMark(t *testing.T) {
	repo, events := &libraryFake{created: true}, &eventsFake{}
	r := libraryRouter(repo, events)
	if w := do(r, "PUT", "/likes/clp_1", ""); w.Code != 204 {
		t.Fatalf("like: %d %s", w.Code, w.Body)
	}
	if w := do(r, "PUT", "/saved/clp_1", ""); w.Code != 204 {
		t.Fatalf("save: %d", w.Code)
	}
	repo.created = false
	do(r, "PUT", "/likes/clp_1", "") // already liked: no second event
	do(r, "DELETE", "/likes/clp_1", "")
	if len(events.added) != 2 || events.added[0].InteractionType != "like" || events.added[1].InteractionType != "save" ||
		events.added[0].VideoID != "vid_x" || *events.added[0].ClipID != "clp_1" {
		t.Fatalf("events: %+v", events.added)
	}
	repo.err = domain.ErrClipNotFound
	if w := do(r, "PUT", "/likes/clp_draft", ""); w.Code != 404 || !strings.Contains(w.Body.String(), "CLIP_NOT_FOUND") {
		t.Fatalf("hidden clip: %d %s", w.Code, w.Body)
	}
}

func TestLibraryClipStatesValidation(t *testing.T) {
	repo := &libraryFake{}
	r := libraryRouter(repo, nil)
	if w := do(r, "GET", "/clip-states?clip_ids=", ""); w.Code != 422 {
		t.Fatalf("empty ids: %d", w.Code)
	}
	if w := do(r, "GET", "/clip-states?clip_ids="+strings.Repeat("a", 51), ""); w.Code != 422 {
		t.Fatalf("long id: %d", w.Code)
	}
	ids := make([]string, 51)
	for i := range ids {
		ids[i] = "c" + strconv.Itoa(i)
	}
	if w := do(r, "GET", "/clip-states?clip_ids="+strings.Join(ids, ","), ""); w.Code != 422 {
		t.Fatalf("51 ids: %d", w.Code)
	}
	w := do(r, "GET", "/clip-states?clip_ids=a,%20b,a,,b", "")
	if w.Code != 200 || strings.Join(repo.states, ",") != "a,b" || !strings.Contains(w.Body.String(), `"list_ids":[]`) {
		t.Fatalf("dedupe/shape: %d %v %s", w.Code, repo.states, w.Body)
	}
}

func TestLibraryListNameValidation(t *testing.T) {
	repo := &libraryFake{}
	r := libraryRouter(repo, nil)
	for _, body := range []string{`{}`, `{"name":"   "}`, `{"name":"` + strings.Repeat("ă", 61) + `"}`, `{"name":"a\u0001b"}`, `not json`} {
		if w := do(r, "POST", "/lists", body); w.Code != 422 {
			t.Fatalf("%s accepted: %d", body, w.Code)
		}
	}
	if w := do(r, "POST", "/lists", `{"name":"  `+strings.Repeat("ă", 60)+`  "}`); w.Code != 201 || repo.names[0] != strings.Repeat("ă", 60) {
		t.Fatalf("60 Vietnamese chars rejected/untrimmed: %d %v", w.Code, repo.names)
	}
	repo.err = domain.ErrListNameTaken
	if w := do(r, "POST", "/lists", `{"name":"Bóng đá"}`); w.Code != 409 || !strings.Contains(w.Body.String(), "LIST_NAME_TAKEN") {
		t.Fatalf("duplicate: %d %s", w.Code, w.Body)
	}
}
