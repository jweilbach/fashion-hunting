-- Backfill source_type for existing reports
-- Run this to update all existing reports with the correct source_type

-- Update social media reports
UPDATE reports
SET source_type = 'social'
WHERE source_type IS NULL
  AND provider IN ('INSTAGRAM', 'TIKTOK', 'TWITTER', 'YOUTUBE', 'LINKEDIN', 'FACEBOOK');

-- Update digital media reports
UPDATE reports
SET source_type = 'digital'
WHERE source_type IS NULL
  AND provider IN ('RSS', 'GOOGLE_SEARCH', 'GOOGLE_NEWS', 'WEB', 'ARTICLE');

-- Update broadcast media reports
UPDATE reports
SET source_type = 'broadcast'
WHERE source_type IS NULL
  AND provider IN ('TV', 'BROADCAST', 'TVEYES', 'PODCAST', 'RADIO');

-- Check results
SELECT
  source_type,
  provider,
  COUNT(*) as count
FROM reports
GROUP BY source_type, provider
ORDER BY source_type, provider;
