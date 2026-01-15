-- Migration: Add source_type column to reports table
-- Date: 2025-11-19
-- Description: Add source_type field to delineate between digital, social, and broadcast media

-- Add source_type column
ALTER TABLE reports
ADD COLUMN IF NOT EXISTS source_type VARCHAR(20);

-- Create index on source_type for efficient filtering
CREATE INDEX IF NOT EXISTS idx_reports_source_type ON reports(source_type);

-- Backfill existing data based on provider
-- Digital: RSS, GOOGLE_SEARCH
-- Social: INSTAGRAM, TIKTOK, TWITTER, YOUTUBE, LINKEDIN
UPDATE reports
SET source_type = CASE
    WHEN provider IN ('RSS', 'GOOGLE_SEARCH') THEN 'digital'
    WHEN provider IN ('INSTAGRAM', 'TIKTOK', 'TWITTER', 'YOUTUBE', 'LINKEDIN') THEN 'social'
    WHEN provider IN ('TV', 'BROADCAST', 'TVEYES') THEN 'broadcast'
    ELSE 'digital'  -- default to digital for unknown providers
END
WHERE source_type IS NULL;

-- Add comment to column for documentation
COMMENT ON COLUMN reports.source_type IS 'Type of media source: digital (news articles), social (social media), or broadcast (TV/radio)';
