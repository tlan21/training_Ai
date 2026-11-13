package gen

import (
	"context"
	"testing"
)

func TestCMSPlanAContract(t *testing.T) {
	spec, err := GetSwagger()
	if err != nil {
		t.Fatal(err)
	}
	if err := spec.Validate(context.Background()); err != nil {
		t.Fatal(err)
	}
	if spec.Info.Version != "0.14.1" {
		t.Fatalf("version %s", spec.Info.Version)
	}
	if spec.Components.Schemas["SystemHealth"].Value.Properties["ai_models"] == nil || len(spec.Components.Schemas["AIModelCheckpoint"].Value.Required) != 3 {
		t.Fatal("missing SystemHealth.ai_models (0.12.0)")
	}
	put := spec.Paths.Find("/api/cms/videos/{id}").Put
	if put == nil || put.Responses.Status(422) == nil {
		t.Fatal("missing editorial update/validation response")
	}
	update := spec.Components.Schemas["VideoMetadataUpdate"].Value
	if len(update.Required) != 3 || update.Properties["hashtags"].Value.MaxItems == nil {
		t.Fatal("missing complete update/hashtag limits")
	}
	if spec.Components.Schemas["CategoryWrite"].Value.Properties["description"] == nil {
		t.Fatal("missing category description")
	}
	if spec.Paths.Find("/api/cms/categories").Post.Responses.Status(422) == nil || spec.Paths.Find("/api/cms/categories/{id}").Put.Responses.Status(409) == nil {
		t.Fatal("missing category validation/conflict responses")
	}
	for _, name := range []string{"width", "height", "fps", "hashtags"} {
		if spec.Components.Schemas["VideoDetail"].Value.AllOf[1].Value.Properties[name] == nil {
			t.Fatalf("missing %s", name)
		}
	}
}

func TestSingleCMSCapabilityContract(t *testing.T) {
	spec, err := GetSwagger()
	if err != nil {
		t.Fatal(err)
	}
	if spec.Paths.Find("/api/cms/users/{id}/role") != nil {
		t.Fatal("retired role-management route remains")
	}
	users := spec.Paths.Find("/api/cms/users").Get
	if users == nil || len(users.Parameters) != 2 {
		t.Fatal("missing read-only searchable user listing")
	}
}

func TestCMSOperationalContract(t *testing.T) {
	spec, err := GetSwagger()
	if err != nil {
		t.Fatal(err)
	}
	if spec.Paths.Find("/api/cms/videos/{id}/analysis").Put == nil {
		t.Fatal("missing persistent proposal review")
	}
	for _, key := range []string{"metrics", "storage", "ai_available", "cpu_util"} {
		if spec.Components.Schemas["SystemHealth"].Value.Properties[key] == nil {
			t.Fatal(key)
		}
	}
	for _, key := range []string{"processing_options", "skipped_stages", "video_title"} {
		if spec.Components.Schemas["Job"].Value.Properties[key] == nil {
			t.Fatal(key)
		}
	}
	if spec.Components.Schemas["CategoryWrite"].Value.Properties["keywords"] == nil {
		t.Fatal("missing keyword rules")
	}
}

func TestCMSReportedThresholdContract(t *testing.T) {
	spec, err := GetSwagger()
	if err != nil {
		t.Fatal(err)
	}
	field := spec.Components.Schemas["CmsAnalysis"].Value.Properties["clip_threshold"].Value
	if !field.Nullable || field.Min == nil || *field.Min != 0 || field.Max == nil || *field.Max != 100 {
		t.Fatal("threshold must allow unknown and constrain reported values")
	}
	if !spec.Components.Schemas["SettingsUpdate"].Value.Properties["highlight_threshold"].Value.Deprecated {
		t.Fatal("legacy setting must not claim AI control")
	}
}

func TestCompilationContract(t *testing.T) {
	spec, err := GetSwagger()
	if err != nil {
		t.Fatal(err)
	}
	post := spec.Paths.Find("/api/cms/clips").Post
	body := post.RequestBody.Value.Content["application/json"].Schema.Value
	if body.Properties["auto_highlights"] == nil || len(body.Required) != 2 || post.Responses.Status(422) == nil {
		t.Fatal("missing compilation create/validation contract")
	}
	if spec.Components.Schemas["Clip"].Value.Properties["source_segments"] == nil {
		t.Fatal("missing persisted source timeline")
	}
}

func TestVideoDeletionStorageContract(t *testing.T) {
	spec, err := GetSwagger()
	if err != nil {
		t.Fatal(err)
	}
	op := spec.Paths.Find("/api/cms/videos/{id}").Delete
	for _, code := range []int{204, 409, 503} {
		if op.Responses.Status(code) == nil {
			t.Fatalf("missing delete %d", code)
		}
	}
}

func TestDiscoveryCategoryContract(t *testing.T) {
	spec, err := GetSwagger()
	if err != nil {
		t.Fatal(err)
	}
	if spec.Paths.Find("/api/feed").Get.Parameters.GetByInAndName("query", "category_id") == nil {
		t.Fatal("feed category filter missing")
	}
	sort := spec.Paths.Find("/api/cms/videos").Get.Parameters.GetByInAndName("query", "sort")
	if sort == nil || len(sort.Schema.Value.Enum) != 2 {
		t.Fatal("CMS video sort missing")
	}
	assigned := spec.Components.Schemas["Video"].Value.Properties["category_assigned_at"]
	if assigned == nil || !assigned.Value.Nullable || !assigned.Value.ReadOnly {
		t.Fatal("category_assigned_at must be nullable read-only")
	}
}

func TestTranscriptQualityContract(t *testing.T) {
	spec, err := GetSwagger()
	if err != nil {
		t.Fatal(err)
	}
	q := spec.Components.Schemas["Subtitles"].Value.Properties["transcript_quality"]
	if q == nil || !q.Value.Nullable || !q.Value.ReadOnly || *q.Value.Max != 1 {
		t.Fatal("transcript_quality must be a nullable read-only 0..1 number")
	}
}

// INT-59: admin password reset + own-account security, no role/account lifecycle routes.
func TestAccountSecurityContract(t *testing.T) {
	spec, err := GetSwagger()
	if err != nil {
		t.Fatal(err)
	}
	reset := spec.Paths.Find("/api/cms/users/{id}/password")
	if reset == nil || reset.Post == nil || reset.Post.Responses.Status(409) == nil || reset.Post.Responses.Status(403) == nil {
		t.Fatal("missing admin password reset with self-reset conflict")
	}
	if spec.Paths.Find("/api/cms/users/{id}") != nil {
		t.Fatal("account deletion/lock route must not exist")
	}
	if p := spec.Paths.Find("/api/cms/me/password"); p == nil || p.Post.Responses.Status(422) == nil {
		t.Fatal("missing own password change")
	}
	if spec.Paths.Find("/api/cms/me/sessions/revoke-others") == nil {
		t.Fatal("missing revoke other sessions")
	}
	update := spec.Components.Schemas["SettingsUpdate"].Value
	for _, name := range []string{"system_name", "display_timezone", "notify_failed_jobs", "notify_uncategorized_videos", "session_ttl_days"} {
		if update.Properties[name] == nil || spec.Components.Schemas["Settings"].Value.Properties[name] == nil {
			t.Fatalf("missing setting %s", name)
		}
	}
	if *update.Properties["session_ttl_days"].Value.Max != 30 || spec.Components.Schemas["CmsMetrics"].Value.Properties["uncategorized_videos"] == nil {
		t.Fatal("session ttl bound / uncategorized metric")
	}
	// 0.11.1: AI key lives in the server environment; the settings field is deprecated and ignored.
	if !update.Properties["ai_service_api_key"].Value.Deprecated || !spec.Components.Schemas["Settings"].Value.Properties["ai_service_api_key"].Value.Deprecated {
		t.Fatal("ai_service_api_key must be deprecated")
	}
}
