-- ========================================
-- Execute SQL RPC Function
-- ========================================
-- This function allows the AI agent to execute READ-ONLY SQL queries
-- Security: Only SELECT statements are allowed

CREATE OR REPLACE FUNCTION execute_sql(query TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result JSONB;
    query_lower TEXT;
    query_cleaned TEXT;
BEGIN
    -- Normalize query: remove leading/trailing whitespace and newlines
    query_cleaned := REGEXP_REPLACE(query, '^\s+', '', 'g');
    query_cleaned := REGEXP_REPLACE(query_cleaned, '\s+$', '', 'g');
    query_lower := LOWER(query_cleaned);

    -- Security: Only allow SELECT statements
    IF NOT (query_lower LIKE 'select%' OR query_lower LIKE 'with%') THEN
        RAISE EXCEPTION 'Only SELECT queries are allowed. Query must start with SELECT or WITH.';
    END IF;

    -- Additional security checks
    IF query_lower LIKE '%drop%'
        OR query_lower LIKE '%delete%'
        OR query_lower LIKE '%update%'
        OR query_lower LIKE '%insert%'
        OR query_lower LIKE '%alter%'
        OR query_lower LIKE '%create%'
        OR query_lower LIKE '%truncate%' THEN
        RAISE EXCEPTION 'Potentially dangerous SQL keywords detected';
    END IF;

    -- Execute query and return as JSONB array
    EXECUTE 'SELECT json_agg(row_to_json(t)) FROM (' || query || ') t' INTO result;

    -- Return empty array if no results
    RETURN COALESCE(result, '[]'::JSONB);

EXCEPTION
    WHEN OTHERS THEN
        -- Return error as JSON
        RETURN jsonb_build_object(
            'error', TRUE,
            'message', SQLERRM,
            'detail', SQLSTATE
        );
END;
$$;

-- Comment for documentation
COMMENT ON FUNCTION execute_sql(TEXT) IS 'Execute read-only SQL queries (SELECT only) and return results as JSONB';

-- Grant execute permission to authenticated users (adjust as needed)
GRANT EXECUTE ON FUNCTION execute_sql(TEXT) TO authenticated, anon, service_role;
