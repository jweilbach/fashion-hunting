-- Migration: Split full_name into first_name and last_name
-- Date: 2025-01-14
-- Description: Add first_name and last_name columns, migrate data from full_name

-- Add new columns
ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name VARCHAR(100);

-- Migrate existing data from full_name
-- Split on first space: everything before = first_name, everything after = last_name
UPDATE users SET
    first_name = CASE
        WHEN full_name IS NOT NULL AND full_name != '' THEN
            SPLIT_PART(full_name, ' ', 1)
        ELSE NULL
    END,
    last_name = CASE
        WHEN full_name IS NOT NULL AND POSITION(' ' IN full_name) > 0 THEN
            SUBSTRING(full_name FROM POSITION(' ' IN full_name) + 1)
        ELSE NULL
    END
WHERE first_name IS NULL;

-- Note: We keep full_name column for backwards compatibility
-- It will be computed as first_name + ' ' + last_name in the model
