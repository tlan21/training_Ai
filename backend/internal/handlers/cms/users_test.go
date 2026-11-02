package cms

import (
	"context"
	"encoding/json"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

func TestUserListSearchIsReadOnlyAndDoesNotExposeRolesOrSecrets(t *testing.T) {
	users := mocks.NewUserRepoMem()
	for _, u := range []*domain.User{{ID: "usr_manager", Username: "Quản lý", Email: "manager@local", Role: domain.RoleAdmin, PasswordHash: "private", CreatedAt: time.Now()}, {ID: "usr_viewer", Username: "Viewer", Email: "viewer@local", Role: domain.RoleClient, CreatedAt: time.Now()}} {
		if err := users.Create(context.Background(), u); err != nil {
			t.Fatal(err)
		}
	}
	r := gin.New()
	r.GET("/users", NewUserHandlers(users).List)
	response := httptest.NewRecorder()
	r.ServeHTTP(response, httptest.NewRequest("GET", "/users?q=MANAGER", nil))
	if response.Code != 200 {
		t.Fatal(response.Body.String())
	}
	var body struct {
		Items []map[string]any `json:"items"`
		Total int              `json:"total"`
	}
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body.Total != 1 || len(body.Items) != 1 || body.Items[0]["id"] != "usr_manager" || body.Items[0]["created_at"] == nil {
		t.Fatal(body)
	}
	if strings.Contains(response.Body.String(), "private") || body.Items[0]["role"] != nil {
		t.Fatal("list exposes credentials or editable role data")
	}
}
