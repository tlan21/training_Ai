-- 0.9.0: when the current category was assigned to a video. Additive and repeatable; existing rows stay NULL
-- (assignment time was never recorded before, so it is not backfilled or guessed).
ALTER TABLE videos ADD COLUMN IF NOT EXISTS category_assigned_at timestamptz;
