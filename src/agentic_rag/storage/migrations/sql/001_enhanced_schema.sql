-- ========================================
-- Enhanced PostgreSQL Schema for Agentic RAG
-- Phase 1: Database Infrastructure
-- ========================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ========================================
-- CORE TABLES
-- ========================================

-- Documents table with enhanced metadata
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT GENERATED ALWAYS AS (md5(content)) STORED,
    metadata JSONB DEFAULT '{}',
    graph_sync_status TEXT DEFAULT 'pending' CHECK (graph_sync_status IN ('pending', 'syncing', 'synced', 'failed')),
    graph_sync_at TIMESTAMPTZ,
    graph_sync_error TEXT,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chunks with multi-model embedding support
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    content_hash TEXT GENERATED ALWAYS AS (md5(content)) STORED,
    embedding_1536 vector(1536),  -- OpenAI text-embedding-3-small
    embedding_768 vector(768),     -- Nomic/other models
    chunk_index INTEGER NOT NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    entity_refs TEXT[] DEFAULT '{}',  -- Array of entity UUIDs from Neo4j
    graph_episode_id TEXT,            -- Reference to Graphiti episode
    token_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Entity reference junction table for efficient lookups
CREATE TABLE IF NOT EXISTS chunk_entities (
    chunk_id UUID REFERENCES chunks(id) ON DELETE CASCADE,
    entity_id TEXT NOT NULL,          -- Neo4j entity UUID
    entity_name TEXT NOT NULL,        -- Denormalized for quick access
    entity_type TEXT NOT NULL,        -- company|person|technology|product|location|event
    confidence FLOAT DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    extraction_method TEXT DEFAULT 'llm', -- llm|ner|regex|manual
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (chunk_id, entity_id)
);

-- Search cache for frequently used queries
CREATE TABLE IF NOT EXISTS search_cache (
    query_hash TEXT PRIMARY KEY,
    query_text TEXT NOT NULL,
    embedding_1536 vector(1536),
    embedding_768 vector(768),
    result_chunk_ids UUID[],
    result_scores FLOAT[],
    search_type TEXT NOT NULL CHECK (search_type IN ('vector', 'hybrid', 'graph')),
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '1 hour'),
    last_accessed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sessions table for conversation history
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours')
);

-- Messages table for conversation context
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Graph sync queue for reliable processing
CREATE TABLE IF NOT EXISTS graph_sync_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_id UUID REFERENCES chunks(id) ON DELETE CASCADE,
    operation TEXT NOT NULL CHECK (operation IN ('create', 'update', 'delete')),
    payload JSONB NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

-- ========================================
-- INDEXES
-- ========================================

-- Primary search indexes
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_1536 ON chunks
    USING ivfflat (embedding_1536 vector_cosine_ops) WITH (lists = 100)
    WHERE embedding_1536 IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_chunks_embedding_768 ON chunks
    USING ivfflat (embedding_768 vector_cosine_ops) WITH (lists = 100)
    WHERE embedding_768 IS NOT NULL;

-- Multi-column indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_chunks_document_index ON chunks(document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_chunks_entity_refs ON chunks USING GIN(entity_refs);
CREATE INDEX IF NOT EXISTS idx_chunk_entities_entity ON chunk_entities(entity_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_chunk_entities_chunk ON chunk_entities(chunk_id, confidence DESC);

-- Partial indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_active ON documents(created_at DESC)
    WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_documents_pending_sync ON documents(id)
    WHERE graph_sync_status = 'pending';
CREATE INDEX IF NOT EXISTS idx_graph_sync_queue_pending ON graph_sync_queue(created_at)
    WHERE status = 'pending';

-- BRIN indexes for time-series data (space-efficient for large tables)
CREATE INDEX IF NOT EXISTS idx_chunks_created_brin ON chunks USING BRIN(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_created_brin ON messages USING BRIN(created_at);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_documents_title_trgm ON documents USING GIN (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_chunks_content_fts ON chunks USING GIN (to_tsvector('english', content));

-- Cache optimization
CREATE INDEX IF NOT EXISTS idx_search_cache_expires ON search_cache(expires_at)
    WHERE expires_at > NOW();
CREATE INDEX IF NOT EXISTS idx_search_cache_popular ON search_cache(hit_count DESC, last_accessed_at DESC);

-- ========================================
-- FUNCTIONS
-- ========================================

-- Enhanced hybrid search with entity boosting and caching
CREATE OR REPLACE FUNCTION hybrid_search_enhanced(
    query_embedding_1536 vector(1536),
    query_embedding_768 vector(768),
    query_text TEXT,
    entity_ids TEXT[] DEFAULT NULL,
    match_count INT DEFAULT 10,
    use_cache BOOLEAN DEFAULT TRUE,
    similarity_threshold FLOAT DEFAULT 0.7
) RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    document_title TEXT,
    document_source TEXT,
    content TEXT,
    combined_score FLOAT,
    vector_similarity FLOAT,
    text_similarity FLOAT,
    entity_boost FLOAT,
    metadata JSONB
) AS $$
DECLARE
    cache_key TEXT;
    cached_results RECORD;
BEGIN
    -- Generate cache key
    cache_key := md5(
        query_text ||
        COALESCE(array_to_string(entity_ids, ','), '') ||
        match_count::TEXT
    );

    -- Check cache if enabled
    IF use_cache THEN
        SELECT * INTO cached_results
        FROM search_cache
        WHERE query_hash = cache_key
            AND expires_at > NOW();

        IF FOUND THEN
            -- Update cache hit statistics
            UPDATE search_cache
            SET hit_count = hit_count + 1,
                last_accessed_at = NOW()
            WHERE query_hash = cache_key;

            -- Return cached results
            RETURN QUERY
            SELECT
                c.id,
                c.document_id,
                d.title,
                d.source,
                c.content,
                scores.score,
                scores.score,
                0.0::FLOAT,
                0.0::FLOAT,
                c.metadata
            FROM unnest(
                cached_results.result_chunk_ids,
                cached_results.result_scores
            ) AS scores(chunk_id, score)
            JOIN chunks c ON c.id = scores.chunk_id
            JOIN documents d ON d.id = c.document_id
            ORDER BY scores.score DESC;
            RETURN;
        END IF;
    END IF;

    -- Perform actual search
    RETURN QUERY
    WITH vector_results AS (
        SELECT
            c.id,
            c.document_id,
            c.content,
            c.metadata,
            CASE
                WHEN query_embedding_1536 IS NOT NULL AND c.embedding_1536 IS NOT NULL THEN
                    1 - (c.embedding_1536 <=> query_embedding_1536)
                WHEN query_embedding_768 IS NOT NULL AND c.embedding_768 IS NOT NULL THEN
                    1 - (c.embedding_768 <=> query_embedding_768)
                ELSE 0.0
            END AS vec_sim
        FROM chunks c
        WHERE (c.embedding_1536 IS NOT NULL OR c.embedding_768 IS NOT NULL)
    ),
    text_results AS (
        SELECT
            c.id,
            ts_rank_cd(
                to_tsvector('english', c.content),
                plainto_tsquery('english', query_text)
            ) AS text_sim
        FROM chunks c
        WHERE to_tsvector('english', c.content) @@ plainto_tsquery('english', query_text)
    ),
    entity_boosted AS (
        SELECT
            v.id,
            v.document_id,
            v.content,
            v.metadata,
            v.vec_sim,
            COALESCE(t.text_sim, 0.0) AS text_sim,
            CASE
                WHEN entity_ids IS NOT NULL AND EXISTS (
                    SELECT 1 FROM chunk_entities ce
                    WHERE ce.chunk_id = v.id
                        AND ce.entity_id = ANY(entity_ids)
                        AND ce.confidence > 0.5
                ) THEN 0.3
                ELSE 0.0
            END AS entity_boost
        FROM vector_results v
        LEFT JOIN text_results t ON v.id = t.id
        WHERE v.vec_sim >= similarity_threshold
    ),
    final_results AS (
        SELECT
            eb.id,
            eb.document_id,
            d.title,
            d.source,
            eb.content,
            (eb.vec_sim * 0.7 + eb.text_sim * 0.3 + eb.entity_boost) AS combined_score,
            eb.vec_sim,
            eb.text_sim,
            eb.entity_boost,
            eb.metadata
        FROM entity_boosted eb
        JOIN documents d ON d.id = eb.document_id
        WHERE d.is_deleted = FALSE
        ORDER BY combined_score DESC
        LIMIT match_count
    )
    SELECT * FROM final_results;

    -- Cache results if enabled and we have results
    IF use_cache AND EXISTS (SELECT 1 FROM final_results LIMIT 1) THEN
        INSERT INTO search_cache (
            query_hash,
            query_text,
            embedding_1536,
            embedding_768,
            result_chunk_ids,
            result_scores,
            search_type
        )
        SELECT
            cache_key,
            query_text,
            query_embedding_1536,
            query_embedding_768,
            array_agg(f.chunk_id ORDER BY f.combined_score DESC),
            array_agg(f.combined_score ORDER BY f.combined_score DESC),
            'hybrid'
        FROM final_results f
        GROUP BY cache_key, query_text, query_embedding_1536, query_embedding_768
        ON CONFLICT (query_hash) DO UPDATE
        SET expires_at = NOW() + INTERVAL '1 hour',
            last_accessed_at = NOW(),
            hit_count = search_cache.hit_count + 1;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to clean expired cache entries
CREATE OR REPLACE FUNCTION clean_expired_cache() RETURNS void AS $$
BEGIN
    DELETE FROM search_cache WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- VIEWS
-- ========================================

-- Document summaries view
CREATE OR REPLACE VIEW document_summaries AS
SELECT
    d.id,
    d.title,
    d.source,
    d.created_at,
    d.updated_at,
    d.metadata,
    d.graph_sync_status,
    COUNT(c.id) AS chunk_count,
    COUNT(DISTINCT ce.entity_id) AS entity_count,
    AVG(c.token_count) AS avg_tokens_per_chunk,
    SUM(c.token_count) AS total_tokens
FROM documents d
LEFT JOIN chunks c ON d.id = c.document_id
LEFT JOIN chunk_entities ce ON c.id = ce.chunk_id
WHERE d.is_deleted = FALSE
GROUP BY d.id, d.title, d.source, d.created_at, d.updated_at, d.metadata, d.graph_sync_status;

-- Pending sync queue view
CREATE OR REPLACE VIEW pending_sync_items AS
SELECT
    q.id,
    q.operation,
    q.status,
    q.retry_count,
    q.created_at,
    d.title AS document_title,
    c.chunk_index
FROM graph_sync_queue q
LEFT JOIN documents d ON q.document_id = d.id
LEFT JOIN chunks c ON q.chunk_id = c.id
WHERE q.status IN ('pending', 'processing')
ORDER BY q.created_at;

-- ========================================
-- MAINTENANCE PROCEDURES
-- ========================================

-- Procedure to optimize vector indexes
CREATE OR REPLACE PROCEDURE optimize_vector_indexes() AS $$
BEGIN
    -- Reindex vector columns for better performance
    REINDEX INDEX idx_chunks_embedding_1536;
    REINDEX INDEX idx_chunks_embedding_768;

    -- Update statistics
    ANALYZE chunks;
END;
$$ LANGUAGE plpgsql;

-- Procedure to clean up old data
CREATE OR REPLACE PROCEDURE cleanup_old_data(days_to_keep INTEGER DEFAULT 90) AS $$
BEGIN
    -- Clean expired cache
    DELETE FROM search_cache WHERE expires_at < NOW();

    -- Clean old sessions
    DELETE FROM sessions WHERE expires_at < NOW();

    -- Clean old sync queue items
    DELETE FROM graph_sync_queue
    WHERE status = 'completed'
    AND processed_at < NOW() - INTERVAL '7 days';

    -- Mark old deleted documents for permanent removal
    DELETE FROM documents
    WHERE is_deleted = TRUE
    AND deleted_at < NOW() - (days_to_keep || ' days')::INTERVAL;
END;
$$ LANGUAGE plpgsql;
