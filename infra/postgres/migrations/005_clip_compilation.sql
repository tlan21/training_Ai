-- Additive: legacy clips have no source map; existing source times remain unchanged.
BEGIN;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS source_segments JSONB NOT NULL DEFAULT '[]'::jsonb
    CHECK (jsonb_typeof(source_segments) = 'array' AND jsonb_array_length(source_segments) <= 100);
COMMIT;
