-- =====================================================
-- OAuth Analytics Views and Functions
-- =====================================================
-- Migration: 008_oauth_analytics.sql
-- Purpose: Add analytics views and functions for OAuth usage tracking
-- Dependencies: 005_auth_tables.sql (auth_oauth_accounts)
-- =====================================================

-- =====================================================
-- MATERIALIZED VIEW: OAuth Provider Statistics
-- =====================================================
-- Summary statistics for each OAuth provider

CREATE MATERIALIZED VIEW IF NOT EXISTS oauth_provider_stats AS
SELECT
    provider,
    COUNT(DISTINCT id) as total_accounts,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT CASE WHEN is_active = TRUE THEN id END) as active_accounts,
    COUNT(DISTINCT CASE WHEN is_active = FALSE THEN id END) as inactive_accounts,
    MIN(created_at) as first_linked_at,
    MAX(created_at) as last_linked_at,
    AVG(EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400)::INTEGER as avg_age_days
FROM auth_oauth_accounts
GROUP BY provider
ORDER BY total_accounts DESC;

-- Index for faster refresh
CREATE UNIQUE INDEX IF NOT EXISTS idx_oauth_provider_stats_provider
    ON oauth_provider_stats(provider);

-- =====================================================
-- MATERIALIZED VIEW: OAuth User Statistics
-- =====================================================
-- Per-user OAuth account linking statistics

CREATE MATERIALIZED VIEW IF NOT EXISTS oauth_user_stats AS
SELECT
    u.id as user_id,
    u.username,
    u.email,
    u.full_name,
    COUNT(o.id) as linked_accounts,
    COUNT(DISTINCT o.provider) as unique_providers,
    ARRAY_AGG(DISTINCT o.provider ORDER BY o.provider) as providers,
    MIN(o.created_at) as first_oauth_link_at,
    MAX(o.created_at) as last_oauth_link_at,
    MAX(o.last_login_at) as last_oauth_login_at
FROM auth_users u
LEFT JOIN auth_oauth_accounts o ON u.id = o.user_id AND o.is_active = TRUE
WHERE u.deleted_at IS NULL
GROUP BY u.id, u.username, u.email, u.full_name
ORDER BY linked_accounts DESC;

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_oauth_user_stats_user_id
    ON oauth_user_stats(user_id);

-- =====================================================
-- MATERIALIZED VIEW: OAuth Login Timeline
-- =====================================================
-- Daily OAuth login activity by provider

CREATE MATERIALIZED VIEW IF NOT EXISTS oauth_login_timeline AS
SELECT
    DATE(last_login_at) as login_date,
    provider,
    COUNT(DISTINCT id) as accounts_logged_in,
    COUNT(DISTINCT user_id) as users_logged_in
FROM auth_oauth_accounts
WHERE last_login_at IS NOT NULL
    AND last_login_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY DATE(last_login_at), provider
ORDER BY login_date DESC, provider;

-- Index for date-based queries
CREATE INDEX IF NOT EXISTS idx_oauth_login_timeline_date
    ON oauth_login_timeline(login_date DESC);

-- =====================================================
-- MATERIALIZED VIEW: OAuth Account Growth
-- =====================================================
-- Daily account linking growth by provider

CREATE MATERIALIZED VIEW IF NOT EXISTS oauth_account_growth AS
SELECT
    DATE(created_at) as link_date,
    provider,
    COUNT(id) as accounts_linked,
    COUNT(DISTINCT user_id) as users_linked,
    SUM(COUNT(id)) OVER (PARTITION BY provider ORDER BY DATE(created_at)) as cumulative_accounts
FROM auth_oauth_accounts
WHERE created_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY DATE(created_at), provider
ORDER BY link_date DESC, provider;

-- Index for date-based queries
CREATE INDEX IF NOT EXISTS idx_oauth_account_growth_date
    ON oauth_account_growth(link_date DESC);

-- =====================================================
-- RPC FUNCTION: Refresh OAuth Analytics Views
-- =====================================================

CREATE OR REPLACE FUNCTION refresh_oauth_analytics_views()
RETURNS TEXT AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY oauth_provider_stats;
    REFRESH MATERIALIZED VIEW CONCURRENTLY oauth_user_stats;
    REFRESH MATERIALIZED VIEW CONCURRENTLY oauth_login_timeline;
    REFRESH MATERIALIZED VIEW CONCURRENTLY oauth_account_growth;

    RETURN 'OAuth analytics views refreshed successfully';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- RPC FUNCTION: Get OAuth Provider Summary
-- =====================================================

CREATE OR REPLACE FUNCTION get_oauth_provider_summary()
RETURNS TABLE (
    provider TEXT,
    total_accounts BIGINT,
    unique_users BIGINT,
    active_accounts BIGINT,
    inactive_accounts BIGINT,
    avg_age_days INTEGER,
    first_linked_at TIMESTAMPTZ,
    last_linked_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ops.provider,
        ops.total_accounts,
        ops.unique_users,
        ops.active_accounts,
        ops.inactive_accounts,
        ops.avg_age_days,
        ops.first_linked_at,
        ops.last_linked_at
    FROM oauth_provider_stats ops
    ORDER BY ops.total_accounts DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- RPC FUNCTION: Get OAuth Login Activity (Last N Days)
-- =====================================================

CREATE OR REPLACE FUNCTION get_oauth_login_activity(days INTEGER DEFAULT 30)
RETURNS TABLE (
    login_date DATE,
    provider TEXT,
    accounts_logged_in BIGINT,
    users_logged_in BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        olt.login_date,
        olt.provider,
        olt.accounts_logged_in,
        olt.users_logged_in
    FROM oauth_login_timeline olt
    WHERE olt.login_date >= CURRENT_DATE - (days || ' days')::INTERVAL
    ORDER BY olt.login_date DESC, olt.provider;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- RPC FUNCTION: Get OAuth Account Growth (Last N Days)
-- =====================================================

CREATE OR REPLACE FUNCTION get_oauth_account_growth(days INTEGER DEFAULT 30)
RETURNS TABLE (
    link_date DATE,
    provider TEXT,
    accounts_linked BIGINT,
    users_linked BIGINT,
    cumulative_accounts BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        oag.link_date,
        oag.provider,
        oag.accounts_linked,
        oag.users_linked,
        oag.cumulative_accounts
    FROM oauth_account_growth oag
    WHERE oag.link_date >= CURRENT_DATE - (days || ' days')::INTERVAL
    ORDER BY oag.link_date DESC, oag.provider;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- RPC FUNCTION: Get Users with Multiple OAuth Providers
-- =====================================================

CREATE OR REPLACE FUNCTION get_multi_provider_users()
RETURNS TABLE (
    username TEXT,
    email TEXT,
    linked_accounts BIGINT,
    providers TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ous.username,
        ous.email,
        ous.linked_accounts,
        ous.providers
    FROM oauth_user_stats ous
    WHERE ous.linked_accounts > 1
    ORDER BY ous.linked_accounts DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- RPC FUNCTION: Get OAuth Provider Adoption Rate
-- =====================================================

CREATE OR REPLACE FUNCTION get_oauth_adoption_rate()
RETURNS TABLE (
    metric TEXT,
    value BIGINT,
    percentage NUMERIC
) AS $$
DECLARE
    total_users BIGINT;
    oauth_users BIGINT;
    password_users BIGINT;
    hybrid_users BIGINT;
BEGIN
    -- Count total active users
    SELECT COUNT(*) INTO total_users
    FROM auth_users
    WHERE deleted_at IS NULL AND is_active = TRUE;

    -- Count users with OAuth accounts
    SELECT COUNT(DISTINCT user_id) INTO oauth_users
    FROM auth_oauth_accounts
    WHERE is_active = TRUE;

    -- Count users with password auth only
    SELECT COUNT(*) INTO password_users
    FROM auth_users
    WHERE deleted_at IS NULL
        AND is_active = TRUE
        AND password_hash IS NOT NULL
        AND id NOT IN (SELECT DISTINCT user_id FROM auth_oauth_accounts WHERE is_active = TRUE);

    -- Count hybrid users (both password and OAuth)
    SELECT COUNT(*) INTO hybrid_users
    FROM auth_users
    WHERE deleted_at IS NULL
        AND is_active = TRUE
        AND password_hash IS NOT NULL
        AND id IN (SELECT DISTINCT user_id FROM auth_oauth_accounts WHERE is_active = TRUE);

    -- Return results
    RETURN QUERY
    SELECT 'Total Active Users'::TEXT, total_users, 100.0;

    RETURN QUERY
    SELECT 'OAuth Users'::TEXT, oauth_users,
           CASE WHEN total_users > 0 THEN (oauth_users::NUMERIC / total_users * 100)::NUMERIC ELSE 0 END;

    RETURN QUERY
    SELECT 'Password Only Users'::TEXT, password_users,
           CASE WHEN total_users > 0 THEN (password_users::NUMERIC / total_users * 100)::NUMERIC ELSE 0 END;

    RETURN QUERY
    SELECT 'Hybrid Users (Password + OAuth)'::TEXT, hybrid_users,
           CASE WHEN total_users > 0 THEN (hybrid_users::NUMERIC / total_users * 100)::NUMERIC ELSE 0 END;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- Initial View Refresh
-- =====================================================

SELECT refresh_oauth_analytics_views();

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON MATERIALIZED VIEW oauth_provider_stats IS
    'Summary statistics for each OAuth provider';

COMMENT ON MATERIALIZED VIEW oauth_user_stats IS
    'Per-user OAuth account linking statistics';

COMMENT ON MATERIALIZED VIEW oauth_login_timeline IS
    'Daily OAuth login activity by provider (last 90 days)';

COMMENT ON MATERIALIZED VIEW oauth_account_growth IS
    'Daily account linking growth by provider (last 90 days)';

COMMENT ON FUNCTION refresh_oauth_analytics_views() IS
    'Refresh all OAuth analytics materialized views';

COMMENT ON FUNCTION get_oauth_provider_summary() IS
    'Get summary statistics for all OAuth providers';

COMMENT ON FUNCTION get_oauth_login_activity(INTEGER) IS
    'Get OAuth login activity for the last N days';

COMMENT ON FUNCTION get_oauth_account_growth(INTEGER) IS
    'Get OAuth account linking growth for the last N days';

COMMENT ON FUNCTION get_multi_provider_users() IS
    'Get users who have linked multiple OAuth providers';

COMMENT ON FUNCTION get_oauth_adoption_rate() IS
    'Get OAuth adoption metrics and percentages';
