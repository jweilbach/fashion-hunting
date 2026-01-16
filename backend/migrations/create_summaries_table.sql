-- Migration: Create summaries table
-- Date: 2026-01-15
-- Description: Stores AI-generated PDF summary documents

-- Create summaries table
CREATE TABLE IF NOT EXISTS summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    job_id UUID REFERENCES scheduled_jobs(id) ON DELETE SET NULL,
    execution_id UUID REFERENCES job_executions(id) ON DELETE SET NULL,

    -- Brands included in summary (array of UUIDs)
    brand_ids UUID[] DEFAULT '{}',

    -- Summary content
    title VARCHAR(500) NOT NULL,
    executive_summary TEXT,

    -- Time range covered
    period_start TIMESTAMP WITH TIME ZONE,
    period_end TIMESTAMP WITH TIME ZONE,

    -- File storage (Phase 1 - local filesystem)
    file_path VARCHAR(500),
    file_size_bytes INTEGER,

    -- Statistics
    report_count INTEGER DEFAULT 0,

    -- Generation status
    generation_status VARCHAR(50) DEFAULT 'pending' CHECK (generation_status IN ('pending', 'generating', 'completed', 'failed')),
    generation_error TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_summaries_tenant_id ON summaries(tenant_id);
CREATE INDEX IF NOT EXISTS idx_summaries_job_id ON summaries(job_id);
CREATE INDEX IF NOT EXISTS idx_summaries_execution_id ON summaries(execution_id);
CREATE INDEX IF NOT EXISTS idx_summaries_status ON summaries(generation_status);
CREATE INDEX IF NOT EXISTS idx_summaries_created_at ON summaries(created_at DESC);

-- GIN index for querying brand_ids array
CREATE INDEX IF NOT EXISTS idx_summaries_brand_ids ON summaries USING GIN (brand_ids);

-- Add comments for documentation
COMMENT ON TABLE summaries IS 'AI-generated PDF summary documents';
COMMENT ON COLUMN summaries.brand_ids IS 'Array of brand UUIDs included in this summary';
COMMENT ON COLUMN summaries.file_path IS 'Local filesystem path to PDF file (Phase 1). Will be migrated to S3 in Phase 2.';
COMMENT ON COLUMN summaries.generation_status IS 'Status of PDF generation: pending, generating, completed, failed';
