-- INT-22: exact004 DDL wrapped with bounded locks and before/after data assertions.
-- Backup/source SHA256 recorded in INT-22-backup.json. No product DML or backfill.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL search_path = public;
DO $target$
BEGIN
  IF current_database() <> 'video_ai' THEN RAISE EXCEPTION 'Wrong migration target'; END IF;
END $target$;
LOCK TABLE public.videos, public.categories IN ACCESS EXCLUSIVE MODE;
CREATE TEMP TABLE int22_before ON COMMIT DROP AS
  SELECT 'videos'::text AS table_name, count(*) AS row_count,
    md5(coalesce(string_agg(jsonb_strip_nulls(to_jsonb(v))::text, E'\n' ORDER BY v.id),'')) AS row_hash FROM public.videos v
  UNION ALL
  SELECT 'categories', count(*),
    md5(coalesce(string_agg(jsonb_strip_nulls(to_jsonb(c))::text, E'\n' ORDER BY c.id),'')) FROM public.categories c;
-- PlanA: additive/idempotent; legacy metadata remains unknown, AI proposals stay in Mongo.
ALTER TABLE videos ADD COLUMN IF NOT EXISTS width INTEGER CHECK (width > 0);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS height INTEGER CHECK (height > 0);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS fps DOUBLE PRECISION CHECK (fps > 0 AND fps < 'Infinity'::float8);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS hashtags TEXT[] CHECK (cardinality(hashtags) <= 30);
ALTER TABLE categories ADD COLUMN IF NOT EXISTS description TEXT CHECK (char_length(description) <= 2000);

DO $verify$
DECLARE
  expected record;
  actual_count bigint;
  actual_hash text;
BEGIN
  FOR expected IN SELECT * FROM pg_temp.int22_before LOOP
    IF expected.table_name = 'videos' THEN
      SELECT count(*), md5(coalesce(string_agg(jsonb_strip_nulls(to_jsonb(v))::text, E'\n' ORDER BY v.id),''))
        INTO actual_count,actual_hash FROM public.videos v;
    ELSE
      SELECT count(*), md5(coalesce(string_agg(jsonb_strip_nulls(to_jsonb(c))::text, E'\n' ORDER BY c.id),''))
        INTO actual_count,actual_hash FROM public.categories c;
    END IF;
    IF actual_count IS DISTINCT FROM expected.row_count OR actual_hash IS DISTINCT FROM expected.row_hash THEN
      RAISE EXCEPTION 'Data preservation failed for %', expected.table_name;
    END IF;
    RAISE NOTICE 'INT22 preserved %: rows=%, fingerprint=%', expected.table_name,actual_count,actual_hash;
  END LOOP;
  IF (SELECT count(*) FROM information_schema.columns c JOIN (VALUES
      ('videos','width','int4'),('videos','height','int4'),('videos','fps','float8'),
      ('videos','hashtags','_text'),('categories','description','text')) AS e(tbl,col,typ)
      ON c.table_schema='public' AND c.table_name=e.tbl AND c.column_name=e.col AND c.udt_name=e.typ
      WHERE c.is_nullable='YES' AND c.column_default IS NULL) <> 5 THEN
    RAISE EXCEPTION 'Metadata column shape mismatch';
  END IF;
  IF (SELECT count(*) FROM pg_constraint WHERE conrelid IN ('public.videos'::regclass,'public.categories'::regclass)
      AND conname IN ('videos_width_check','videos_height_check','videos_fps_check','videos_hashtags_check','categories_description_check')
      AND contype='c' AND convalidated) <> 5 THEN
    RAISE EXCEPTION 'Metadata checks missing or not validated';
  END IF;
  RAISE NOTICE 'INT22 five nullable columns and five validated checks verified';
END $verify$;
COMMIT;