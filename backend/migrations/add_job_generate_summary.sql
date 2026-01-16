-- Migration: Add generate_summary column to scheduled_jobs table
-- Date: 2026-01-15
-- Description: Flag to trigger AI summary generation after job execution

-- Add generate_summary column
ALTER TABLE scheduled_jobs
ADD COLUMN IF NOT EXISTS generate_summary BOOLEAN DEFAULT FALSE;

-- Add comment for documentation
COMMENT ON COLUMN scheduled_jobs.generate_summary IS 'When true, generates an AI-powered PDF summary after job completes successfully';
