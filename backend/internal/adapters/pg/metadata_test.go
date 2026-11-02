package pg

import (
	"context"
	"encoding/json"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v5/pgxpool"
	"traning_ai/backend/internal/auth"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/gen"
	"traning_ai/backend/internal/handlers"
	"traning_ai/backend/internal/handlers/cms"
)

func applyMetadataMigration(t *testing.T, db *pgxpool.Pool) {
	t.Helper()
	data, err := os.ReadFile("../../../../infra/postgres/migrations/004_cms_metadata.sql")
	if err != nil {
		t.Fatal(err)
	}
	if _, err = db.Exec(context.Background(), string(data)); err != nil {
		t.Fatal(err)
	}
}

func TestCMSMetadataRealPersistenceAndMigration(t *testing.T) {
	db := integrationDB(t)
	ctx := context.Background()
	// Shadow both ALTER targets: the migration never touches product tables or rows.
	for _, table := range []string{"videos", "categories", "video_processing_jobs", "system_settings"} {
		if _, err := db.Exec(ctx, "CREATE TEMP TABLE "+table+" (LIKE public."+table+" INCLUDING DEFAULTS INCLUDING INDEXES)"); err != nil {
			t.Fatal(err)
		}
	}
	applyMetadataMigration(t, db)
	migration, err := os.ReadFile("../../../../infra/postgres/migrations/006_cms_operations.sql")
	if err != nil {
		t.Fatal(err)
	}
	if _, err = db.Exec(ctx, string(migration)); err != nil {
		t.Fatal(err)
	}
	_, err = db.Exec(ctx, `INSERT INTO videos(id,title,raw_file_path,duration_seconds,status,training_origin) VALUES('vid_meta','Legacy','',8,'processed','test')`)
	if err != nil {
		t.Fatal(err)
	}
	repo := &VideoRepo{DB: db}
	v, err := repo.Get(ctx, "vid_meta")
	if err != nil || v.Width != nil || v.Hashtags != nil {
		t.Fatalf("unknown legacy values: %+v %v", v, err)
	}
	w, h, fps := 1920, 1080, 29.97
	if err := repo.SetMediaMetadata(ctx, v.ID, 8, &w, &h, &fps); err != nil {
		t.Fatal(err)
	}
	gin.SetMode(gin.TestMode)
	jwt := auth.NewJWT("pg-editorial-fixture-key")
	handler := cms.NewVideoHandlers(repo, nil, nil, nil, nil, nil, nil, nil, nil, nil)
	router := gin.New()
	router.Use(handlers.RequireAuth(jwt), handlers.RequireRole("admin", "editor"))
	router.PUT("/videos/:id", handler.UpdateMetadata)
	router.GET("/videos/:id", handler.Get)
	token, _ := jwt.Sign("usr_fixture", "editor", time.Minute)
	for _, method := range []string{"PUT", "GET"} {
		req := httptest.NewRequest(method, "/videos/vid_meta", strings.NewReader(`{"title":"Edited","description":"Description","hashtags":["BóngĐá"]}`))
		req.Header.Set("Authorization", "Bearer "+token)
		req.Header.Set("Content-Type", "application/json")
		res := httptest.NewRecorder()
		router.ServeHTTP(res, req)
		var detail gen.VideoDetail
		if res.Code != 200 || json.Unmarshal(res.Body.Bytes(), &detail) != nil || detail.Width == nil || *detail.Width != 1920 || detail.Hashtags == nil || len(*detail.Hashtags) != 1 {
			t.Fatalf("%s persisted HTTP detail: %d %s", method, res.Code, res.Body.String())
		}
	}
	applyMetadataMigration(t, db)
	fresh := &VideoRepo{DB: db}
	v, err = fresh.Get(ctx, v.ID)
	if err != nil || v.Title != "Edited" || *v.Width != 1920 || *v.Height != 1080 || *v.FPS != fps || len(v.Hashtags) != 1 {
		t.Fatalf("not persisted across repository/migration: %+v %v", v, err)
	}
	if err := fresh.SetMediaMetadata(ctx, v.ID, 8, nil, nil, nil); err != nil {
		t.Fatal(err)
	}
	v, _ = fresh.Get(ctx, v.ID)
	if *v.Width != 1920 || v.Hashtags[0] != "BóngĐá" {
		t.Fatal("legacy preprocessing erased metadata/editorial tags")
	}
	var origin string
	_ = db.QueryRow(ctx, `SELECT training_origin FROM videos WHERE id=$1`, v.ID).Scan(&origin)
	if origin != "test" {
		t.Fatal("metadata edit changed data provenance")
	}
	if _, err := fresh.UpdateMetadata(ctx, v.ID, "Edited", "", []string{}, nil); err != nil {
		t.Fatal(err)
	}
	v, _ = fresh.Get(ctx, v.ID)
	if v.Hashtags == nil || len(v.Hashtags) != 0 || *v.Description != "" {
		t.Fatal("empty editorial override lost")
	}
	if err := fresh.SoftDelete(ctx, v.ID); err != nil {
		t.Fatal(err)
	}
	if _, err := fresh.UpdateMetadata(ctx, v.ID, "Undelete", "", []string{}, nil); err != domain.ErrVideoNotFound {
		t.Fatalf("deleted video editable: %v", err)
	}
	cats := &CategoryRepo{DB: db}
	desc := "Category description"
	cat, err := cats.Create(ctx, "Temporary category", &desc, nil)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = cats.Update(ctx, cat.ID, "Renamed", nil, nil); err != nil {
		t.Fatal(err)
	}
	list, err := (&CategoryRepo{DB: db}).List(ctx)
	if err != nil || len(list) != 1 || *list[0].Description != desc {
		t.Fatalf("category not persisted: %+v %v", list, err)
	}
	empty := ""
	if _, err = cats.Update(ctx, cat.ID, "Renamed", &empty, nil); err != nil {
		t.Fatal(err)
	}
	list, _ = cats.List(ctx)
	if *list[0].Description != "" {
		t.Fatal("category description not cleared")
	}
}
