-- Migration: Add social_profiles column to brand_configs table
-- Date: 2026-01-15
-- Description: Add JSONB column for flexible per-provider social media configuration

-- Add social_profiles column
ALTER TABLE brand_configs
ADD COLUMN IF NOT EXISTS social_profiles JSONB DEFAULT '{}';

-- Add GIN index for querying inside JSONB
CREATE INDEX IF NOT EXISTS idx_brand_configs_social_profiles ON brand_configs USING GIN (social_profiles);

-- Add comment to column for documentation
COMMENT ON COLUMN brand_configs.social_profiles IS 'Per-provider social media configuration. Structure: {"instagram": {"enabled": true, "handle": "...", "searches": [...]}, ...}';
