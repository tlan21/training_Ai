-- Additive CMS metadata; preserve all existing rows and setting values.
BEGIN;
ALTER TABLE categories ADD COLUMN IF NOT EXISTS keywords text[] NOT NULL DEFAULT '{}';
ALTER TABLE videos ADD COLUMN IF NOT EXISTS editorial_priority varchar(8) NOT NULL DEFAULT 'normal';
ALTER TABLE video_processing_jobs ADD COLUMN IF NOT EXISTS processing_options jsonb;
ALTER TABLE video_processing_jobs ADD COLUMN IF NOT EXISTS skipped_stages text[] NOT NULL DEFAULT '{}';
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='videos_editorial_priority_check' AND conrelid='videos'::regclass) THEN
    ALTER TABLE videos ADD CONSTRAINT videos_editorial_priority_check CHECK(editorial_priority IN ('low','normal','high'));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='categories_keywords_count_check' AND conrelid='categories'::regclass) THEN
    ALTER TABLE categories ADD CONSTRAINT categories_keywords_count_check CHECK(cardinality(keywords)<=20);
  END IF;
END $$;
INSERT INTO system_settings(key,value) VALUES
 ('category_suggestion_enabled','true'),('category_keyword_enabled','false')
ON CONFLICT(key) DO NOTHING;
COMMIT;
