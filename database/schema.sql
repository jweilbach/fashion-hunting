-- PR Automation Multi-Tenant Database Schema
-- PostgreSQL 12+
-- Enhanced version with deduplication, better indexing, and provider metadata

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto"; -- For encryption functions

-- ============================================================================
-- TENANTS TABLE
-- ============================================================================
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL, -- URL-friendly identifier

    -- Contact info
    email VARCHAR(255) NOT NULL UNIQUE,
    company_name VARCHAR(255),

    -- Configuration
    settings JSONB DEFAULT '{}'::jsonb, -- Stores feeds.yaml + settings.yaml equivalent

    -- Rate limiting per tenant
    rate_limit_config JSONB DEFAULT '{
        "openai_rpm": 15,
        "fetch_concurrency": 5
    }'::jsonb,

    -- Subscription/billing
    plan VARCHAR(50) DEFAULT 'free', -- free, starter, professional, enterprise
    status VARCHAR(50) DEFAULT 'active', -- active, suspended, cancelled

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_report_run TIMESTAMP WITH TIME ZONE
);

-- Indexes for fast tenant lookup
CREATE INDEX idx_tenants_slug ON tenants(slug);
CREATE INDEX idx_tenants_email ON tenants(email);
CREATE INDEX idx_tenants_status ON tenants(status);

-- ============================================================================
-- PROVIDER CREDENTIALS TABLE (separated for security)
-- ============================================================================
CREATE TABLE provider_credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Provider info
    provider VARCHAR(50) NOT NULL, -- openai, google, tiktok, etc.

    -- Encrypted credentials (use application-level encryption)
    credentials_encrypted TEXT NOT NULL,

    -- Metadata
    is_active BOOLEAN DEFAULT true,
    last_verified TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(tenant_id, provider)
);

CREATE INDEX idx_provider_credentials_tenant ON provider_credentials(tenant_id);
CREATE INDEX idx_provider_credentials_active ON provider_credentials(is_active);

-- ============================================================================
-- REPORTS TABLE (main content storage)
-- ============================================================================
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Deduplication key (hash of link + tenant_id)
    dedupe_key VARCHAR(64) NOT NULL,

    -- Report metadata
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source VARCHAR(500), -- e.g., "RSS", "TikTok (@username)"
    provider VARCHAR(50) NOT NULL, -- RSS, TikTok, Instagram, etc.
    source_type VARCHAR(20), -- digital, social, broadcast

    -- Content
    brands TEXT[] DEFAULT '{}', -- Array of brand names mentioned
    title TEXT NOT NULL,
    link TEXT NOT NULL,
    summary TEXT,
    full_text TEXT, -- Full extracted article text

    -- Analysis results
    sentiment VARCHAR(50), -- positive, neutral, negative, mixed
    topic VARCHAR(100), -- product, influencer, lifestyle, trend, corporate
    est_reach INTEGER DEFAULT 0,

    -- Additional metadata
    raw_data JSONB DEFAULT '{}'::jsonb, -- Store provider-specific data (video stats, etc.)

    -- Processing status
    processing_status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure no duplicate links per tenant
    UNIQUE(tenant_id, dedupe_key)
);

-- Indexes for performance
CREATE INDEX idx_reports_tenant_id ON reports(tenant_id);
CREATE INDEX idx_reports_timestamp ON reports(timestamp DESC);
CREATE INDEX idx_reports_tenant_timestamp ON reports(tenant_id, timestamp DESC);
CREATE INDEX idx_reports_sentiment ON reports(sentiment);
CREATE INDEX idx_reports_provider ON reports(provider);
CREATE INDEX idx_reports_source_type ON reports(source_type);
CREATE INDEX idx_reports_status ON reports(processing_status);
CREATE INDEX idx_reports_brands ON reports USING GIN(brands); -- GIN index for array searches
CREATE INDEX idx_reports_dedupe ON reports(dedupe_key);

-- Composite indexes for common queries
CREATE INDEX idx_reports_tenant_status_timestamp ON reports(tenant_id, processing_status, timestamp DESC);
CREATE INDEX idx_reports_tenant_provider_timestamp ON reports(tenant_id, provider, timestamp DESC);

-- Full-text search index on title and summary
CREATE INDEX idx_reports_fulltext ON reports USING GIN(
    to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(summary, ''))
);

-- ============================================================================
-- FEED CONFIGURATIONS TABLE
-- ============================================================================
CREATE TABLE feed_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Feed details
    provider VARCHAR(50) NOT NULL, -- RSS, TikTok, Instagram
    feed_type VARCHAR(50), -- hashtag, keyword, user, rss_url
    feed_value TEXT NOT NULL, -- The actual URL, hashtag, username, etc.

    -- Configuration
    enabled BOOLEAN DEFAULT true,
    fetch_count INTEGER DEFAULT 30, -- How many items to fetch
    config JSONB DEFAULT '{}'::jsonb, -- Provider-specific settings

    -- Metadata
    label VARCHAR(255), -- User-friendly name
    last_fetched TIMESTAMP WITH TIME ZONE,
    last_error TEXT,
    fetch_count_success INTEGER DEFAULT 0,
    fetch_count_failed INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_feed_configs_tenant_id ON feed_configs(tenant_id);
CREATE INDEX idx_feed_configs_enabled ON feed_configs(enabled);
CREATE INDEX idx_feed_configs_provider ON feed_configs(provider);
CREATE INDEX idx_feed_configs_tenant_enabled ON feed_configs(tenant_id, enabled);

-- ============================================================================
-- SCHEDULED JOBS TABLE
-- ============================================================================
CREATE TABLE scheduled_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Job configuration
    job_type VARCHAR(50) NOT NULL, -- fetch_reports, send_digest, generate_slides
    schedule_cron VARCHAR(100) NOT NULL, -- Cron expression (e.g., "0 9 * * *")
    enabled BOOLEAN DEFAULT true,

    -- Job settings
    config JSONB DEFAULT '{}'::jsonb,

    -- Execution tracking
    last_run TIMESTAMP WITH TIME ZONE,
    last_status VARCHAR(50), -- success, failed, running
    last_error TEXT,
    next_run TIMESTAMP WITH TIME ZONE,
    run_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_scheduled_jobs_tenant_id ON scheduled_jobs(tenant_id);
CREATE INDEX idx_scheduled_jobs_next_run ON scheduled_jobs(next_run) WHERE enabled = true;
CREATE INDEX idx_scheduled_jobs_enabled ON scheduled_jobs(enabled);
CREATE INDEX idx_scheduled_jobs_tenant_enabled ON scheduled_jobs(tenant_id, enabled);

-- ============================================================================
-- JOB EXECUTION HISTORY TABLE
-- ============================================================================
CREATE TABLE job_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES scheduled_jobs(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Execution details
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL, -- running, success, failed, partial

    -- Results
    items_processed INTEGER DEFAULT 0,
    items_failed INTEGER DEFAULT 0,
    error_message TEXT,
    execution_log TEXT,

    -- Progress tracking
    total_items INTEGER DEFAULT 0,
    current_item_index INTEGER DEFAULT 0,
    current_item_title VARCHAR(500),
    celery_task_id VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_job_executions_job_id ON job_executions(job_id);
CREATE INDEX idx_job_executions_tenant_id ON job_executions(tenant_id);
CREATE INDEX idx_job_executions_started_at ON job_executions(started_at DESC);
CREATE INDEX idx_job_executions_status ON job_executions(status);
CREATE INDEX idx_job_executions_celery_task_id ON job_executions(celery_task_id);

-- ============================================================================
-- BRAND CONFIGURATIONS TABLE
-- ============================================================================
CREATE TABLE brand_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Brand details
    brand_name VARCHAR(255) NOT NULL,
    aliases TEXT[] DEFAULT '{}', -- Alternative names/spellings

    -- Filtering
    is_known_brand BOOLEAN DEFAULT true,
    should_ignore BOOLEAN DEFAULT false,

    -- Metadata
    category VARCHAR(100), -- client, competitor, industry
    notes TEXT,

    -- Stats (denormalized for performance)
    mention_count INTEGER DEFAULT 0,
    last_mentioned TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(tenant_id, brand_name)
);

-- Indexes
CREATE INDEX idx_brand_configs_tenant_id ON brand_configs(tenant_id);
CREATE INDEX idx_brand_configs_known ON brand_configs(is_known_brand);
CREATE INDEX idx_brand_configs_tenant_known ON brand_configs(tenant_id, is_known_brand);
CREATE INDEX idx_brand_configs_aliases ON brand_configs USING GIN(aliases);

-- ============================================================================
-- USERS TABLE (for multi-user access within tenants)
-- ============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- User info
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),

    -- Permissions
    role VARCHAR(50) DEFAULT 'viewer', -- admin, editor, viewer
    is_active BOOLEAN DEFAULT true,

    -- Auth
    last_login TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(tenant_id, email)
);

-- Indexes
CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_users_tenant_active ON users(tenant_id, is_active);

-- ============================================================================
-- ANALYTICS CACHE TABLE (for dashboard performance)
-- ============================================================================
CREATE TABLE analytics_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Cache metadata
    metric_type VARCHAR(100) NOT NULL, -- daily_mentions, sentiment_trend, top_brands, etc.
    time_period VARCHAR(50) NOT NULL, -- today, week, month, year
    filters JSONB DEFAULT '{}'::jsonb, -- Additional filter context

    -- Cached data
    data JSONB NOT NULL,

    -- Cache management
    cached_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,

    UNIQUE(tenant_id, metric_type, time_period, filters)
);

-- Indexes
CREATE INDEX idx_analytics_cache_tenant_id ON analytics_cache(tenant_id);
CREATE INDEX idx_analytics_cache_expires_at ON analytics_cache(expires_at);

-- ============================================================================
-- AUDIT LOG TABLE (for security and compliance)
-- ============================================================================
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Action details
    action VARCHAR(100) NOT NULL, -- login, create_report, update_feed, etc.
    resource_type VARCHAR(100), -- tenant, report, feed, etc.
    resource_id UUID,

    -- Context
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_audit_logs_tenant_id ON audit_logs(tenant_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- Partition audit logs by month for better performance (optional, for high-volume)
-- ALTER TABLE audit_logs PARTITION BY RANGE (created_at);

-- ============================================================================
-- LISTS TABLE (for organizing reports and other objects)
-- ============================================================================
CREATE TABLE lists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- List metadata
    name VARCHAR(255) NOT NULL,
    list_type VARCHAR(50) NOT NULL, -- report, contact, editor, etc.
    description TEXT,

    -- Ownership
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_lists_tenant_id ON lists(tenant_id);
CREATE INDEX idx_lists_list_type ON lists(list_type);
CREATE INDEX idx_lists_created_by ON lists(created_by);
CREATE INDEX idx_lists_tenant_type ON lists(tenant_id, list_type);

-- ============================================================================
-- LIST ITEMS TABLE (items within lists)
-- ============================================================================
CREATE TABLE list_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    list_id UUID NOT NULL REFERENCES lists(id) ON DELETE CASCADE,

    -- Generic item reference
    item_id UUID NOT NULL, -- References reports.id, contacts.id, etc.

    -- Tracking
    added_by UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Timestamps
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure no duplicates within a list
    UNIQUE(list_id, item_id)
);

-- Indexes
CREATE INDEX idx_list_items_list_id ON list_items(list_id);
CREATE INDEX idx_list_items_item_id ON list_items(item_id);
CREATE INDEX idx_list_items_added_by ON list_items(added_by);

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reports_updated_at BEFORE UPDATE ON reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_feed_configs_updated_at BEFORE UPDATE ON feed_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_scheduled_jobs_updated_at BEFORE UPDATE ON scheduled_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_brand_configs_updated_at BEFORE UPDATE ON brand_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_provider_credentials_updated_at BEFORE UPDATE ON provider_credentials
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_lists_updated_at BEFORE UPDATE ON lists
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_list_items_updated_at BEFORE UPDATE ON list_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- TRIGGER FOR DEDUPE_KEY GENERATION
-- ============================================================================
CREATE OR REPLACE FUNCTION generate_dedupe_key()
RETURNS TRIGGER AS $$
BEGIN
    -- Generate SHA256 hash of tenant_id + link
    NEW.dedupe_key = encode(digest(NEW.tenant_id::text || NEW.link, 'sha256'), 'hex');
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER generate_reports_dedupe_key BEFORE INSERT ON reports
    FOR EACH ROW EXECUTE FUNCTION generate_dedupe_key();

-- ============================================================================
-- TRIGGER FOR BRAND MENTION COUNT UPDATE
-- ============================================================================
CREATE OR REPLACE FUNCTION update_brand_mention_counts()
RETURNS TRIGGER AS $$
BEGIN
    -- Update mention counts for all brands in the new report
    IF NEW.processing_status = 'completed' AND NEW.brands IS NOT NULL THEN
        UPDATE brand_configs
        SET
            mention_count = mention_count + 1,
            last_mentioned = GREATEST(last_mentioned, NEW.timestamp)
        WHERE
            tenant_id = NEW.tenant_id
            AND brand_name = ANY(NEW.brands);
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_brand_counts AFTER INSERT ON reports
    FOR EACH ROW EXECUTE FUNCTION update_brand_mention_counts();

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Recent reports with brand count
CREATE OR REPLACE VIEW v_reports_summary AS
SELECT
    r.id,
    r.tenant_id,
    r.timestamp,
    r.source,
    r.provider,
    r.title,
    r.link,
    r.summary,
    r.sentiment,
    r.topic,
    r.est_reach,
    array_length(r.brands, 1) as brand_count,
    r.brands,
    r.processing_status,
    r.created_at
FROM reports r;

-- Tenant statistics
CREATE OR REPLACE VIEW v_tenant_stats AS
SELECT
    t.id as tenant_id,
    t.name as tenant_name,
    t.slug,
    t.status,
    t.plan,
    COUNT(DISTINCT r.id) as total_reports,
    COUNT(DISTINCT CASE WHEN r.timestamp >= NOW() - INTERVAL '7 days' THEN r.id END) as reports_last_7_days,
    COUNT(DISTINCT CASE WHEN r.timestamp >= NOW() - INTERVAL '30 days' THEN r.id END) as reports_last_30_days,
    COUNT(DISTINCT fc.id) as feed_count,
    COUNT(DISTINCT CASE WHEN fc.enabled = true THEN fc.id END) as active_feed_count,
    MAX(r.timestamp) as last_report_timestamp,
    t.last_report_run
FROM tenants t
LEFT JOIN reports r ON r.tenant_id = t.id AND r.processing_status = 'completed'
LEFT JOIN feed_configs fc ON fc.tenant_id = t.id
GROUP BY t.id, t.name, t.slug, t.status, t.plan, t.last_report_run;

-- Daily report counts by tenant
CREATE OR REPLACE VIEW v_daily_report_counts AS
SELECT
    tenant_id,
    DATE(timestamp) as report_date,
    provider,
    COUNT(*) as report_count,
    AVG(est_reach)::INTEGER as avg_reach,
    (SELECT COUNT(DISTINCT brand) FROM unnest(array_agg(brands)) AS brand) as unique_brands
FROM reports
WHERE processing_status = 'completed'
GROUP BY tenant_id, DATE(timestamp), provider;

-- Brand performance view
CREATE OR REPLACE VIEW v_brand_performance AS
SELECT
    bc.tenant_id,
    bc.brand_name,
    bc.category,
    bc.mention_count,
    bc.last_mentioned,
    COUNT(DISTINCT r.id) as actual_mentions, -- Verify against denormalized count
    AVG(r.est_reach)::INTEGER as avg_reach,
    COUNT(CASE WHEN r.sentiment = 'positive' THEN 1 END) as positive_mentions,
    COUNT(CASE WHEN r.sentiment = 'neutral' THEN 1 END) as neutral_mentions,
    COUNT(CASE WHEN r.sentiment = 'negative' THEN 1 END) as negative_mentions
FROM brand_configs bc
LEFT JOIN reports r ON r.tenant_id = bc.tenant_id
    AND bc.brand_name = ANY(r.brands)
    AND r.processing_status = 'completed'
GROUP BY bc.tenant_id, bc.brand_name, bc.category, bc.mention_count, bc.last_mentioned;

-- Recent job executions with details
CREATE OR REPLACE VIEW v_job_execution_summary AS
SELECT
    je.id,
    je.tenant_id,
    t.name as tenant_name,
    sj.job_type,
    je.started_at,
    je.completed_at,
    je.status,
    je.items_processed,
    je.items_failed,
    EXTRACT(EPOCH FROM (je.completed_at - je.started_at))::INTEGER as duration_seconds,
    je.error_message
FROM job_executions je
JOIN tenants t ON t.id = je.tenant_id
JOIN scheduled_jobs sj ON sj.id = je.job_id
ORDER BY je.started_at DESC;

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to clean up expired analytics cache
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM analytics_cache WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get or create tenant by slug
CREATE OR REPLACE FUNCTION get_or_create_tenant(
    p_slug VARCHAR(100),
    p_name VARCHAR(255),
    p_email VARCHAR(255)
)
RETURNS UUID AS $$
DECLARE
    v_tenant_id UUID;
BEGIN
    SELECT id INTO v_tenant_id FROM tenants WHERE slug = p_slug;

    IF v_tenant_id IS NULL THEN
        INSERT INTO tenants (slug, name, email)
        VALUES (p_slug, p_name, p_email)
        RETURNING id INTO v_tenant_id;
    END IF;

    RETURN v_tenant_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SAMPLE DATA (for testing)
-- ============================================================================

-- Insert a sample tenant
INSERT INTO tenants (name, slug, email, company_name, settings) VALUES
(
    'ABMC Demo',
    'abmc-demo',
    'demo@alisonbrod.com',
    'Alison Brod Marketing + Communications',
    '{
        "known_brands": ["Glossier", "Maybelline", "Target", "Revlon"],
        "ignore_brand_exact": ["Google News", "CNN"],
        "recap_max_items": 8
    }'::jsonb
);

-- Get the tenant ID for further inserts
DO $$
DECLARE
    demo_tenant_id UUID;
BEGIN
    SELECT id INTO demo_tenant_id FROM tenants WHERE slug = 'abmc-demo';

    -- Insert sample feed configs
    INSERT INTO feed_configs (tenant_id, provider, feed_type, feed_value, label) VALUES
    (demo_tenant_id, 'RSS', 'rss_url', 'https://news.google.com/rss/search?q=Glossier', 'Glossier News'),
    (demo_tenant_id, 'RSS', 'rss_url', 'https://news.google.com/rss/search?q=Maybelline', 'Maybelline News');

    -- Insert sample brand configs
    INSERT INTO brand_configs (tenant_id, brand_name, is_known_brand, category) VALUES
    (demo_tenant_id, 'Glossier', true, 'client'),
    (demo_tenant_id, 'Maybelline', true, 'client'),
    (demo_tenant_id, 'Target', true, 'client'),
    (demo_tenant_id, 'Revlon', true, 'competitor');

    -- Insert sample scheduled job
    INSERT INTO scheduled_jobs (tenant_id, job_type, schedule_cron, config) VALUES
    (demo_tenant_id, 'fetch_reports', '0 9 * * *', '{"max_items_per_run": 30}'::jsonb);

    -- Insert sample user (password: demo123 - use proper hashing in production)
    INSERT INTO users (tenant_id, email, password_hash, full_name, role) VALUES
    (demo_tenant_id, 'admin@alisonbrod.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5Ln4N1L7z8cQ2', 'Demo Admin', 'admin');
END $$;

-- ============================================================================
-- HELPFUL QUERIES (commented out - use as reference)
-- ============================================================================

-- Get all reports for a tenant in the last 7 days
-- SELECT * FROM v_reports_summary
-- WHERE tenant_id = 'YOUR_TENANT_ID'
-- AND timestamp >= NOW() - INTERVAL '7 days'
-- ORDER BY timestamp DESC;

-- Get brand mention frequency for a tenant
-- SELECT unnest(brands) as brand, COUNT(*) as mention_count
-- FROM reports
-- WHERE tenant_id = 'YOUR_TENANT_ID' AND processing_status = 'completed'
-- GROUP BY brand
-- ORDER BY mention_count DESC;

-- Get sentiment breakdown by provider
-- SELECT provider, sentiment, COUNT(*) as count
-- FROM reports
-- WHERE tenant_id = 'YOUR_TENANT_ID' AND processing_status = 'completed'
-- GROUP BY provider, sentiment;

-- Search reports by brand
-- SELECT * FROM reports
-- WHERE tenant_id = 'YOUR_TENANT_ID'
-- AND 'Glossier' = ANY(brands)
-- ORDER BY timestamp DESC;

-- Full-text search
-- SELECT * FROM reports
-- WHERE to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(summary, ''))
--       @@ to_tsquery('english', 'fashion & beauty')
-- ORDER BY timestamp DESC;
