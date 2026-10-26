package pg

import (
	"context"
	"strings"
	"testing"
)

func TestSettingsRepository_RealAtomicPatch(t *testing.T) {
	db := integrationDB(t)
	ctx := context.Background()
	// One connection + a temporary table isolates the live stack's configuration.
	if _, err := db.Exec(ctx, `CREATE TEMP TABLE system_settings (LIKE public.system_settings INCLUDING ALL);
		INSERT INTO system_settings(key,value) VALUES('highlight_threshold','75'),('asr_warning_threshold','65'),
		('auto_highlight_enabled','true'),('auto_subtitle_enabled','true'),('default_subtitle_lang','vi'),('ai_service_api_key','sk-local-test')`); err != nil {
		t.Fatal(err)
	}
	repo := &SettingsRepo{DB: db}
	if err := repo.Update(ctx, map[string]string{"highlight_threshold": "0", "auto_highlight_enabled": "false", "ai_service_api_key": "sk-local-test-updated"}); err != nil {
		t.Fatal(err)
	}
	stored, err := (&SettingsRepo{DB: db}).Get(ctx)
	if err != nil || stored.HighlightThreshold != 0 || stored.AutoHighlightEnabled || stored.ASRWarningThreshold != 65 || !stored.AutoSubtitleEnabled || stored.AIServiceAPIKey != "sk-local-test-updated" {
		t.Fatalf("patch not persisted: %v", err)
	}
	if err := repo.Update(ctx, map[string]string{"highlight_threshold": "42", strings.Repeat("z", 51): "bad"}); err == nil {
		t.Fatal("expected database constraint error")
	}
	stored, err = repo.Get(ctx)
	if err != nil || stored.HighlightThreshold != 0 {
		t.Fatalf("failed patch partially committed: %v", err)
	}
	if err := repo.Update(ctx, map[string]string{}); err != nil {
		t.Fatalf("empty patch failed: %v", err)
	}
}
