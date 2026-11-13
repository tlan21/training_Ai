package pg

import (
	"context"
	"encoding/json"

	"github.com/jackc/pgx/v5/pgxpool"
	"traning_ai/backend/internal/domain"
)

type SettingsRepo struct{ DB *pgxpool.Pool }

func (r *SettingsRepo) Get(ctx context.Context) (*domain.SystemSettings, error) {
	var s domain.SystemSettings
	err := r.DB.QueryRow(ctx, `SELECT
		(max(value) FILTER(WHERE key='highlight_threshold'))::int,
		(max(value) FILTER(WHERE key='asr_warning_threshold'))::int,
		(max(value) FILTER(WHERE key='auto_highlight_enabled'))::boolean,
		(max(value) FILTER(WHERE key='auto_subtitle_enabled'))::boolean,
		max(value) FILTER(WHERE key='default_subtitle_lang'),
 coalesce((max(value) FILTER(WHERE key='category_suggestion_enabled'))::boolean,true),
 coalesce((max(value) FILTER(WHERE key='category_keyword_enabled'))::boolean,false),
 coalesce(max(value) FILTER(WHERE key='system_name'),'AI Video CMS'),
 coalesce(max(value) FILTER(WHERE key='display_timezone'),'Asia/Ho_Chi_Minh'),
 coalesce((max(value) FILTER(WHERE key='notify_failed_jobs'))::boolean,true),
 coalesce((max(value) FILTER(WHERE key='notify_uncategorized_videos'))::boolean,true),
 coalesce((max(value) FILTER(WHERE key='session_ttl_days'))::int,7),
 coalesce((max(value) FILTER(WHERE key='category_auto_apply'))::boolean,true)
		FROM system_settings`).Scan(&s.HighlightThreshold, &s.ASRWarningThreshold, &s.AutoHighlightEnabled,
		&s.AutoSubtitleEnabled, &s.DefaultSubtitleLang, &s.CategorySuggestionEnabled, &s.CategoryKeywordEnabled,
		&s.SystemName, &s.DisplayTimezone, &s.NotifyFailedJobs, &s.NotifyUncategorizedVideos, &s.SessionTTLDays, &s.CategoryAutoApply)
	return &s, err
}

func (r *SettingsRepo) Update(ctx context.Context, values map[string]string) error {
	data, err := json.Marshal(values)
	if err != nil {
		return err
	}
	_, err = r.DB.Exec(ctx, `INSERT INTO system_settings(key,value)
		SELECT key,value FROM jsonb_each_text($1::jsonb) ORDER BY key
		ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=now()`, string(data))
	return err
}
