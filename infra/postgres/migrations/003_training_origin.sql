-- Additive, repeatable. Historical/seed records stay unknown and are excluded from training exports.
BEGIN;
ALTER TABLE users ADD COLUMN IF NOT EXISTS training_origin TEXT NOT NULL DEFAULT 'unknown'
    CHECK (training_origin IN ('unknown', 'product', 'test'));
ALTER TABLE videos ADD COLUMN IF NOT EXISTS training_origin TEXT NOT NULL DEFAULT 'unknown'
    CHECK (training_origin IN ('unknown', 'product', 'test'));
COMMIT;
