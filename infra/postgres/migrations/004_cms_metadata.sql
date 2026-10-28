-- PlanA: additive/idempotent; legacy metadata remains unknown, AI proposals stay in Mongo.
BEGIN;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS width INTEGER CHECK (width > 0);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS height INTEGER CHECK (height > 0);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS fps DOUBLE PRECISION CHECK (fps > 0 AND fps < 'Infinity'::float8);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS hashtags TEXT[] CHECK (cardinality(hashtags) <= 30);
ALTER TABLE categories ADD COLUMN IF NOT EXISTS description TEXT CHECK (char_length(description) <= 2000);
COMMIT;
