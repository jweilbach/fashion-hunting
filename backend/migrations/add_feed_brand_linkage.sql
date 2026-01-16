-- Migration: Add brand linkage to feed_configs table
-- Date: 2026-01-15
-- Description: Link feeds to brands and track auto-generated feeds

-- Add brand_id column (nullable - feeds can exist without brand association)
ALTER TABLE feed_configs
ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES brand_configs(id) ON DELETE SET NULL;

-- Add is_auto_generated flag to distinguish auto-created feeds from manual ones
ALTER TABLE feed_configs
ADD COLUMN IF NOT EXISTS is_auto_generated BOOLEAN DEFAULT FALSE;

-- Create index on brand_id for efficient lookups
CREATE INDEX IF NOT EXISTS idx_feed_configs_brand_id ON feed_configs(brand_id);

-- Create index for querying auto-generated feeds
CREATE INDEX IF NOT EXISTS idx_feed_configs_auto_generated ON feed_configs(brand_id, is_auto_generated) WHERE is_auto_generated = TRUE;

-- Add comments for documentation
COMMENT ON COLUMN feed_configs.brand_id IS 'FK to brand_configs - links auto-generated feeds to their source brand';
COMMENT ON COLUMN feed_configs.is_auto_generated IS 'True if feed was auto-created from brand social_profiles, false if manually created';
