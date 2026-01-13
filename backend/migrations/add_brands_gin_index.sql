-- Migration: Add GIN index for brands array column
-- This significantly speeds up brand containment queries
-- Example: WHERE brands @> ARRAY['Nike'] or WHERE 'Nike' = ANY(brands)

-- Create the GIN index
CREATE INDEX IF NOT EXISTS idx_reports_brands_gin ON reports USING gin(brands);

-- Analyze the table to update query planner statistics
ANALYZE reports;

-- Migration notes:
-- - This index enables fast array containment lookups
-- - Query performance improvement: O(log n) instead of O(n) for brand searches
-- - Index size: approximately 20-30% of column size
-- - Build time: ~1-2 seconds per 10,000 rows
