-- =====================================================
-- Analytics Schema Migration - Core Infrastructure
-- =====================================================
-- This is NOT optional - it's foundational system infrastructure.
-- Creates comprehensive analytics tables with partitioning, indexes,
-- materialized views, and maintenance functions.
-- =====================================================

-- =====================================================
-- TABLE: search_analytics
-- =====================================================
-- Tracks all search operations with intent, strategy, and performance metrics

CREATE TABLE IF NOT EXISTS search_analytics (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    session_id UUID,  -- References sessions table (if exists)

    -- Query Details
    query_text TEXT NOT NULL,
    query_hash TEXT NOT NULL,  -- md5(query_text) for deduplication

    -- Intent & Strategy (REQUIRED - NOT NULL)
    detected_intent TEXT NOT NULL CHECK (detected_intent IN (
        'VECTOR_HEAVY', 'GRAPH_HEAVY', 'HYBRID', 'TEMPORAL', 'ENTITY_FOCUSED'
    )),
    strategy_used TEXT NOT NULL CHECK (strategy_used IN (
        'VECTOR_HEAVY', 'GRAPH_HEAVY', 'HYBRID', 'TEMPORAL', 'ENTITY_FOCUSED'
    )),

    -- Performance Metrics (REQUIRED - NOT NULL)
    total_latency_ms FLOAT NOT NULL CHECK (total_latency_ms >= 0),
    vector_latency_ms FLOAT NOT NULL DEFAULT 0 CHECK (vector_latency_ms >= 0),
    graph_latency_ms FLOAT NOT NULL DEFAULT 0 CHECK (graph_latency_ms >= 0),
    intent_analysis_latency_ms FLOAT NOT NULL DEFAULT 0 CHECK (intent_analysis_latency_ms >= 0),
    ranking_latency_ms FLOAT NOT NULL DEFAULT 0 CHECK (ranking_latency_ms >= 0),

    -- Results (REQUIRED - NOT NULL)
    chunks_returned INTEGER NOT NULL DEFAULT 0 CHECK (chunks_returned >= 0),
    cache_hit BOOLEAN NOT NULL DEFAULT FALSE,

    -- Graph Enrichment
    entities_found INTEGER NOT NULL DEFAULT 0 CHECK (entities_found >= 0),
    relationships_found INTEGER NOT NULL DEFAULT 0 CHECK (relationships_found >= 0),
    facts_found INTEGER NOT NULL DEFAULT 0 CHECK (facts_found >= 0),
    graph_boost_applied BOOLEAN NOT NULL DEFAULT FALSE,
    entity_boost_applied BOOLEAN NOT NULL DEFAULT FALSE,

    -- Context
    user_id TEXT,
    source TEXT NOT NULL DEFAULT 'ui' CHECK (source IN ('ui', 'api', 'cli')),
    metadata JSONB NOT NULL DEFAULT '{}',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create initial partition for current month
CREATE TABLE IF NOT EXISTS search_analytics_current PARTITION OF search_analytics
    FOR VALUES FROM (DATE_TRUNC('month', CURRENT_DATE)) TO (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month');

-- Indexes for search_analytics
CREATE INDEX IF NOT EXISTS idx_search_analytics_created ON search_analytics(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_search_analytics_intent ON search_analytics(detected_intent, strategy_used);
CREATE INDEX IF NOT EXISTS idx_search_analytics_session ON search_analytics(session_id) WHERE session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_search_analytics_hash ON search_analytics(query_hash, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_search_analytics_latency ON search_analytics(total_latency_ms DESC);

-- =====================================================
-- TABLE: tool_usage_analytics
-- =====================================================
-- Tracks tool execution metrics and errors

CREATE TABLE IF NOT EXISTS tool_usage_analytics (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    session_id UUID,  -- References sessions table (if exists)

    -- Tool Details (REQUIRED - NOT NULL)
    tool_name TEXT NOT NULL,
    execution_time_ms FLOAT NOT NULL CHECK (execution_time_ms >= 0),
    success BOOLEAN NOT NULL,

    -- Error Tracking
    error_type TEXT,
    error_message TEXT,

    -- Input/Output (truncated for storage)
    input_params JSONB,
    result_summary JSONB,

    -- Context (REQUIRED - NOT NULL)
    triggered_by TEXT NOT NULL DEFAULT 'agent' CHECK (triggered_by IN (
        'user_query', 'agent_decision', 'fallback', 'system'
    )),
    user_id TEXT,
    source TEXT NOT NULL DEFAULT 'ui' CHECK (source IN ('ui', 'api', 'cli')),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create initial partition for current month
CREATE TABLE IF NOT EXISTS tool_usage_analytics_current PARTITION OF tool_usage_analytics
    FOR VALUES FROM (DATE_TRUNC('month', CURRENT_DATE)) TO (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month');

-- Indexes for tool_usage_analytics
CREATE INDEX IF NOT EXISTS idx_tool_usage_created ON tool_usage_analytics(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tool_usage_tool ON tool_usage_analytics(tool_name, success);
CREATE INDEX IF NOT EXISTS idx_tool_usage_performance ON tool_usage_analytics(tool_name, execution_time_ms DESC);
CREATE INDEX IF NOT EXISTS idx_tool_usage_session ON tool_usage_analytics(session_id) WHERE session_id IS NOT NULL;

-- =====================================================
-- TABLE: agent_interactions
-- =====================================================
-- Tracks all agent-user interactions with feedback

CREATE TABLE IF NOT EXISTS agent_interactions (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,  -- Session tracking required

    -- Interaction Type (REQUIRED - NOT NULL)
    interaction_type TEXT NOT NULL CHECK (interaction_type IN (
        'query', 'feedback', 'correction', 'clarification', 'error'
    )),
    user_message TEXT NOT NULL,
    agent_response TEXT NOT NULL,

    -- Performance (REQUIRED - NOT NULL)
    response_time_ms FLOAT NOT NULL CHECK (response_time_ms >= 0),
    tokens_used INTEGER CHECK (tokens_used >= 0),
    model_used TEXT NOT NULL,

    -- Context Flags (REQUIRED - NOT NULL)
    tools_called TEXT[] NOT NULL DEFAULT '{}',
    memory_used BOOLEAN NOT NULL DEFAULT FALSE,
    rag_used BOOLEAN NOT NULL DEFAULT FALSE,

    -- Quality Metrics
    user_feedback TEXT CHECK (user_feedback IN ('thumbs_up', 'thumbs_down', NULL)),
    feedback_comment TEXT,
    feedback_at TIMESTAMPTZ,

    -- Context
    user_id TEXT,
    source TEXT NOT NULL DEFAULT 'ui' CHECK (source IN ('ui', 'api', 'cli')),
    metadata JSONB NOT NULL DEFAULT '{}',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create initial partition for current month
CREATE TABLE IF NOT EXISTS agent_interactions_current PARTITION OF agent_interactions
    FOR VALUES FROM (DATE_TRUNC('month', CURRENT_DATE)) TO (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month');

-- Indexes for agent_interactions
CREATE INDEX IF NOT EXISTS idx_agent_interactions_created ON agent_interactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_interactions_session ON agent_interactions(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_interactions_feedback ON agent_interactions(user_feedback) WHERE user_feedback IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_agent_interactions_model ON agent_interactions(model_used, response_time_ms);

-- =====================================================
-- TABLE: ingestion_analytics
-- =====================================================
-- Tracks document ingestion performance and results

CREATE TABLE IF NOT EXISTS ingestion_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,  -- References documents table

    -- Processing Metrics (REQUIRED - NOT NULL)
    total_processing_time_ms FLOAT NOT NULL CHECK (total_processing_time_ms >= 0),
    chunking_time_ms FLOAT NOT NULL DEFAULT 0 CHECK (chunking_time_ms >= 0),
    embedding_time_ms FLOAT NOT NULL DEFAULT 0 CHECK (embedding_time_ms >= 0),
    graph_extraction_time_ms FLOAT NOT NULL DEFAULT 0 CHECK (graph_extraction_time_ms >= 0),

    -- Results (REQUIRED - NOT NULL)
    chunks_created INTEGER NOT NULL DEFAULT 0 CHECK (chunks_created >= 0),
    entities_extracted INTEGER NOT NULL DEFAULT 0 CHECK (entities_extracted >= 0),
    relationships_extracted INTEGER NOT NULL DEFAULT 0 CHECK (relationships_extracted >= 0),
    facts_extracted INTEGER NOT NULL DEFAULT 0 CHECK (facts_extracted >= 0),

    -- Status (REQUIRED - NOT NULL)
    success BOOLEAN NOT NULL,
    error_message TEXT,

    -- File Context (REQUIRED - NOT NULL)
    file_size_bytes BIGINT NOT NULL CHECK (file_size_bytes >= 0),
    file_type TEXT NOT NULL,
    processing_mode TEXT NOT NULL CHECK (processing_mode IN (
        'full', 'incremental', 'reindex', 'update'
    )),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for ingestion_analytics (no partition needed - lower volume)
CREATE INDEX IF NOT EXISTS idx_ingestion_analytics_document ON ingestion_analytics(document_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_analytics_created ON ingestion_analytics(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ingestion_analytics_success ON ingestion_analytics(success, created_at DESC);

-- =====================================================
-- TABLE: system_metrics
-- =====================================================
-- Periodic snapshots of system health and performance

CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID NOT NULL DEFAULT gen_random_uuid(),

    -- Database Metrics (REQUIRED - NOT NULL)
    pg_active_connections INTEGER NOT NULL DEFAULT 0 CHECK (pg_active_connections >= 0),
    pg_idle_connections INTEGER NOT NULL DEFAULT 0 CHECK (pg_idle_connections >= 0),
    pg_total_queries BIGINT NOT NULL DEFAULT 0 CHECK (pg_total_queries >= 0),
    pg_failed_queries BIGINT NOT NULL DEFAULT 0 CHECK (pg_failed_queries >= 0),
    pg_avg_query_time_ms FLOAT NOT NULL DEFAULT 0 CHECK (pg_avg_query_time_ms >= 0),

    neo4j_active_connections INTEGER NOT NULL DEFAULT 0 CHECK (neo4j_active_connections >= 0),
    neo4j_idle_connections INTEGER NOT NULL DEFAULT 0 CHECK (neo4j_idle_connections >= 0),
    neo4j_total_queries BIGINT NOT NULL DEFAULT 0 CHECK (neo4j_total_queries >= 0),
    neo4j_failed_queries BIGINT NOT NULL DEFAULT 0 CHECK (neo4j_failed_queries >= 0),
    neo4j_avg_query_time_ms FLOAT NOT NULL DEFAULT 0 CHECK (neo4j_avg_query_time_ms >= 0),

    -- Cache Metrics (REQUIRED - NOT NULL)
    cache_hit_rate FLOAT NOT NULL DEFAULT 0 CHECK (cache_hit_rate >= 0 AND cache_hit_rate <= 1),
    cache_size_mb FLOAT NOT NULL DEFAULT 0 CHECK (cache_size_mb >= 0),

    -- Application Metrics (REQUIRED - NOT NULL)
    active_sessions INTEGER NOT NULL DEFAULT 0 CHECK (active_sessions >= 0),
    requests_per_minute FLOAT NOT NULL DEFAULT 0 CHECK (requests_per_minute >= 0),
    avg_response_time_ms FLOAT NOT NULL DEFAULT 0 CHECK (avg_response_time_ms >= 0),
    error_rate FLOAT NOT NULL DEFAULT 0 CHECK (error_rate >= 0 AND error_rate <= 1),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create initial partition for current month
CREATE TABLE IF NOT EXISTS system_metrics_current PARTITION OF system_metrics
    FOR VALUES FROM (DATE_TRUNC('month', CURRENT_DATE)) TO (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month');

-- Index for system_metrics
CREATE INDEX IF NOT EXISTS idx_system_metrics_created ON system_metrics(created_at DESC);

-- =====================================================
-- MATERIALIZED VIEWS FOR PERFORMANCE
-- =====================================================

-- Daily search summary (refreshed hourly)
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_search_summary AS
SELECT
    DATE(created_at) as date,
    COUNT(*) as total_searches,
    AVG(total_latency_ms) as avg_latency_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_latency_ms) as p50_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_latency_ms) as p95_latency_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY total_latency_ms) as p99_latency_ms,
    COUNT(*) FILTER (WHERE cache_hit = true) as cache_hits,
    COUNT(*) FILTER (WHERE graph_boost_applied = true) as graph_boosts,
    COUNT(DISTINCT session_id) as unique_sessions,
    AVG(chunks_returned) as avg_chunks_returned
FROM search_analytics
GROUP BY DATE(created_at)
ORDER BY date DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_search_summary_date ON daily_search_summary(date);

-- Intent distribution (last 7 days)
CREATE MATERIALIZED VIEW IF NOT EXISTS intent_distribution_7d AS
SELECT
    detected_intent,
    strategy_used,
    COUNT(*) as search_count,
    AVG(total_latency_ms) as avg_latency_ms,
    AVG(chunks_returned) as avg_chunks_returned,
    COUNT(*) FILTER (WHERE cache_hit = true) as cache_hits
FROM search_analytics
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY detected_intent, strategy_used
ORDER BY search_count DESC;

-- Tool performance (last 7 days)
CREATE MATERIALIZED VIEW IF NOT EXISTS tool_performance_7d AS
SELECT
    tool_name,
    COUNT(*) as total_calls,
    COUNT(*) FILTER (WHERE success = true) as successful_calls,
    COUNT(*) FILTER (WHERE success = false) as failed_calls,
    (COUNT(*) FILTER (WHERE success = true)::FLOAT / NULLIF(COUNT(*), 0))::FLOAT as success_rate,
    AVG(execution_time_ms) as avg_execution_time_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_ms) as p95_execution_time_ms,
    MAX(execution_time_ms) as max_execution_time_ms
FROM tool_usage_analytics
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY tool_name
ORDER BY total_calls DESC;

-- =====================================================
-- MAINTENANCE FUNCTIONS
-- =====================================================

-- Function to refresh materialized views (called by cron)
CREATE OR REPLACE FUNCTION refresh_analytics_views() RETURNS void AS $$
BEGIN
    -- Only daily_search_summary can be refreshed concurrently (has unique index)
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_search_summary;
    -- Others must be refreshed normally (no unique indexes)
    REFRESH MATERIALIZED VIEW intent_distribution_7d;
    REFRESH MATERIALIZED VIEW tool_performance_7d;
END;
$$ LANGUAGE plpgsql;

-- Function to create next month's partitions
CREATE OR REPLACE FUNCTION create_next_month_partitions() RETURNS void AS $$
DECLARE
    next_month DATE := DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month');
    month_after DATE := next_month + INTERVAL '1 month';
    partition_name TEXT;
BEGIN
    -- Search analytics partition
    partition_name := 'search_analytics_' || TO_CHAR(next_month, 'YYYY_MM');
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF search_analytics FOR VALUES FROM (%L) TO (%L)',
        partition_name,
        next_month,
        month_after
    );
    RAISE NOTICE 'Created partition: %', partition_name;

    -- Tool usage partition
    partition_name := 'tool_usage_analytics_' || TO_CHAR(next_month, 'YYYY_MM');
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF tool_usage_analytics FOR VALUES FROM (%L) TO (%L)',
        partition_name,
        next_month,
        month_after
    );
    RAISE NOTICE 'Created partition: %', partition_name;

    -- Agent interactions partition
    partition_name := 'agent_interactions_' || TO_CHAR(next_month, 'YYYY_MM');
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF agent_interactions FOR VALUES FROM (%L) TO (%L)',
        partition_name,
        next_month,
        month_after
    );
    RAISE NOTICE 'Created partition: %', partition_name;

    -- System metrics partition
    partition_name := 'system_metrics_' || TO_CHAR(next_month, 'YYYY_MM');
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF system_metrics FOR VALUES FROM (%L) TO (%L)',
        partition_name,
        next_month,
        month_after
    );
    RAISE NOTICE 'Created partition: %', partition_name;

    RAISE NOTICE 'All partitions created for %', TO_CHAR(next_month, 'YYYY-MM');
END;
$$ LANGUAGE plpgsql;

-- Function to drop old partitions (keep 90 days)
CREATE OR REPLACE FUNCTION drop_old_analytics_partitions(days_to_keep INTEGER DEFAULT 90) RETURNS void AS $$
DECLARE
    cutoff_date DATE := CURRENT_DATE - days_to_keep;
    partition_record RECORD;
    partition_date DATE;
BEGIN
    FOR partition_record IN
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename ~ '^(search_analytics|tool_usage_analytics|agent_interactions|system_metrics)_\d{4}_\d{2}$'
    LOOP
        -- Extract date from partition name (e.g., 'search_analytics_2025_01' -> '2025-01-01')
        BEGIN
            partition_date := TO_DATE(
                SUBSTRING(partition_record.tablename FROM '\d{4}_\d{2}$'),
                'YYYY_MM'
            );

            IF partition_date < cutoff_date THEN
                EXECUTE 'DROP TABLE IF EXISTS ' || partition_record.tablename;
                RAISE NOTICE 'Dropped partition: %', partition_record.tablename;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE WARNING 'Could not process partition %: %', partition_record.tablename, SQLERRM;
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- GRANT PERMISSIONS (if using specific roles)
-- =====================================================
-- Uncomment and adjust if you have specific database roles
-- GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO analytics_writer;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_reader;

-- =====================================================
-- MIGRATION COMPLETE
-- =====================================================
-- Analytics infrastructure is now in place.
-- Next steps:
-- 1. Initialize analytics logger in application startup
-- 2. Instrument search operations
-- 3. Instrument tool usage
-- 4. Set up cron jobs for:
--    - Refreshing materialized views (hourly)
--    - Creating next month's partitions (monthly)
--    - Dropping old partitions (monthly)
-- =====================================================
