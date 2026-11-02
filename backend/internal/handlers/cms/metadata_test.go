package cms

import (
	"context"
	"encoding/json"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"traning_ai/backend/internal/auth"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/handlers"
	"traning_ai/backend/internal/mocks"
)

func TestEditorialMetadataValidationAndRoleGuard(t *testing.T) {
	gin.SetMode(gin.TestMode)
	ctx := context.Background()
	videos := mocks.NewVideoRepoMem()
	_ = videos.Create(ctx, &domain.Video{ID: "vid_meta", Title: "Original", Status: domain.VideoProcessed, RawFilePath: "original.mp4"})
	h := NewVideoHandlers(videos, nil, nil, nil, nil, nil, nil, nil, nil, nil)
	jwt := auth.NewJWT("metadata-unit-test-key")
	r := gin.New()
	r.PUT("/api/cms/videos/:id", handlers.RequireAuth(jwt), handlers.RequireRole("admin", "editor"), h.UpdateMetadata)
	valid := `{"title":"Biên tập","description":"Mô tả","hashtags":["BóngĐá","AI_2026"]}`
	request := func(role, id, body string, status int) {
		t.Helper()
		req := httptest.NewRequest("PUT", "/api/cms/videos/"+id, strings.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		if role != "" {
			token, _ := jwt.Sign("usr_editor", role, time.Minute)
			req.Header.Set("Authorization", "Bearer "+token)
		}
		res := httptest.NewRecorder()
		r.ServeHTTP(res, req)
		if res.Code != status {
			t.Fatalf("%s %s: %d %s", role, body, res.Code, res.Body.String())
		}
	}
	request("", "vid_meta", valid, 401)
	request("client", "vid_meta", valid, 403)
	for _, body := range []string{`{}`, `null`, `{"title":"x","description":""}`, `{"title":" ","description":"","hashtags":[]}`, `{"title":"x","description":null,"hashtags":[]}`, `{"title":"x","description":"","hashtags":null}`, `{"title":"x","description":"","hashtags":["bad tag"]}`, `{"title":"x","description":"","hashtags":["#tag"]}`, `{"title":"x","description":"","hashtags":["AI","AI"]}`, `{"title":"x","description":"","hashtags":[],"status":"deleted"}`, valid + `{}`} {
		request("editor", "vid_meta", body, 422)
	}
	for _, oversized := range []any{map[string]any{"title": strings.Repeat("a", 256), "description": "", "hashtags": []string{}}, map[string]any{"title": "x", "description": strings.Repeat("a", 10001), "hashtags": []string{}}, map[string]any{"title": "x", "description": "", "hashtags": []string{strings.Repeat("a", 65)}}} {
		body, _ := json.Marshal(oversized)
		request("editor", "vid_meta", string(body), 422)
	}
	before, _ := videos.Get(ctx, "vid_meta")
	if before.Title != "Original" || before.Hashtags != nil {
		t.Fatal("invalid request mutated video")
	}
	request("editor", "vid_meta", valid, 200)
	after, _ := videos.Get(ctx, "vid_meta")
	if after.Title != "Biên tập" || len(after.Hashtags) != 2 || after.RawFilePath != "original.mp4" || after.Status != domain.VideoProcessed {
		t.Fatalf("wrong update: %+v", after)
	}
	request("admin", "vid_meta", `{"title":"Title","description":"","hashtags":[]}`, 200)
	after, _ = videos.Get(ctx, "vid_meta")
	if after.Hashtags == nil || len(after.Hashtags) != 0 || *after.Description != "" {
		t.Fatal("explicit empty values not preserved")
	}
	request("admin", "vid_missing", valid, 404)
	_ = videos.SoftDelete(ctx, "vid_meta")
	request("admin", "vid_meta", valid, 404)
}

func TestCategoryDescriptionBackwardCompatibility(t *testing.T) {
	gin.SetMode(gin.TestMode)
	ctx := context.Background()
	cats := mocks.NewCategoryRepoMem()
	cache := mocks.NewCacheMem()
	h := NewCategoryHandlers(cats, cache)
	r := gin.New()
	r.POST("/categories", h.Create)
	r.PUT("/categories/:id", h.Update)
	r.GET("/categories", h.List)
	request := func(method, path, body string, status int) string {
		t.Helper()
		req := httptest.NewRequest(method, path, strings.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		res := httptest.NewRecorder()
		r.ServeHTTP(res, req)
		if res.Code != status {
			t.Fatalf("%d %s", res.Code, res.Body)
		}
		return res.Body.String()
	}
	request("POST", "/categories", `{"name":"Sport","description":"Mô tả"}`, 201)
	_ = cache.Set(ctx, "categories:all", "stale", time.Minute)
	request("PUT", "/categories/cat_Sport", `{"name":"Sport2"}`, 200)
	items, _ := cats.List(ctx)
	if items[0].Description == nil || *items[0].Description != "Mô tả" {
		t.Fatal("name-only update erased description")
	}
	if _, ok, _ := cache.Get(ctx, "categories:all"); ok {
		t.Fatal("category cache not invalidated")
	}
	request("PUT", "/categories/cat_Sport", `{"name":"Sport2","description":null}`, 200)
	request("PUT", "/categories/cat_Sport", `{"name":"Sport2","description":""}`, 200)
	items, _ = cats.List(ctx)
	if *items[0].Description != "" {
		t.Fatal("description not cleared")
	}
	request("POST", "/categories", `{"name":"Legacy"}`, 201)
	request("POST", "/categories", `{"name":"Sport2"}`, 409)
	request("PUT", "/categories/cat_Legacy", `{"name":"Sport2"}`, 409)
	request("POST", "/categories", `{"name":" "}`, 422)
	request("POST", "/categories", `{"name":"X","unknown":1}`, 422)
	request("POST", "/categories", `{"name":"X","description":"`+strings.Repeat("a", 2001)+`"}`, 422)
	request("PUT", "/categories/missing", `{"name":"X"}`, 404)
}
