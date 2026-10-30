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
	if spec.Info.Version != "0.6.0" {
		t.Fatalf("version %s", spec.Info.Version)
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
