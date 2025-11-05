# Database Schemas

## PostgreSQL (pgvector)
Primary schema defined in `001_enhanced_schema.sql` enables vector search, metadata tracking, and graph sync queue.【F:src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql†L1-L200】 Key tables:

### `documents`
- `id UUID PK`, `title`, `source`, `content`, `content_hash`, `metadata JSONB`, soft-delete fields, and sync status columns.【F:src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql†L16-L30】

### `chunks`
- Holds chunk text, md5 hash, `embedding_1536 vector(1536)`, `embedding_768 vector(768)`, positional metadata, token counts, and graph references (`entity_refs`, `graph_episode_id`).【F:src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql†L32-L48】
- Indexed with IVF FLAT over both embedding dimensions and GIN indexes for entity refs and text search.【F:src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql†L116-L148】

### `chunk_entities`
- Junction table linking chunks to Neo4j entity ids with confidence/metadata.【F:src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql†L50-L60】

### `search_cache`
- pgvector-backed cache for hybrid results, storing embeddings, chunk ids, scores, TTL fields.【F:src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql†L62-L75】

### Sessions & Messages
- `sessions` and `messages` track chat history with expirations.【F:src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql†L77-L95】

### `graph_sync_queue`
- Persistent queue for Neo4j synchronization with retry counters and payloads.【F:src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql†L97-L110】

### `hybrid_search_enhanced` Function
- Combines vector similarity, text similarity, and entity boosting; performs cache lookups before running query over `chunks`/`documents`.【F:src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql†L155-L200】

### Additional Schemas
- `document_rows` table (tabular ingestion) defined separately.【F:src/agentic_rag/storage/migrations/sql/002_document_rows_table.sql†L1-L20】
- Analytics partitioned tables for search/tool usage/system metrics with monthly partition helpers.【F:src/agentic_rag/storage/migrations/sql/004_analytics_schema.sql†L14-L355】
- Auth/2FA/email verification tables for Streamlit UI authentication flows.【F:src/agentic_rag/storage/migrations/sql/005_auth_tables.sql†L17-L227】【F:src/agentic_rag/storage/migrations/sql/006_email_verification.sql†L12-L80】【F:src/agentic_rag/storage/migrations/sql/007_2fa_and_password_history.sql†L12-L138】

## Neo4j / Graphiti
### Constraints & Indexes
- `Neo4jInitializer` creates Graphiti-style unique constraints for `Entity`, `Episode`, `Concept`, `Event` nodes and adds custom indexes, including full-text indexes for `Entity` and `Episode` search.【F:src/agentic_rag/storage/migrations/neo4j_init.py†L17-L124】

### Core Nodes & Relationships
- `Neo4jStore.add_entities` merges `Entity` nodes keyed by name/type, tracking mention counts and chunk references without storing raw content.【F:src/agentic_rag/storage/neo4j_store.py†L25-L76】
- `Neo4jStore.add_relationships` creates `RELATED_TO` relationships between entities with confidence/strength properties and maintains relationship counts.【F:src/agentic_rag/storage/neo4j_store.py†L78-L166】
- `Neo4jStore.add_episodes` (not fully shown above) persists temporal facts linking episodes to entities and documents, enforcing 500-character limits.【F:src/agentic_rag/storage/neo4j_store.py†L168-L240】
- Entities carry importance scores updated after knowledge extraction; episodes contain timestamps and entity references.【F:src/agentic_rag/storage/neo4j_store.py†L150-L240】【F:src/agentic_rag/storage/graphiti_client.py†L34-L80】

### Knowledge Extraction Contract
- `GraphitiClient.extract_and_store_knowledge` orchestrates entity extraction, relationship linking, and episode creation, returning counts for analytics while deferring actual Graphiti ingestion to the custom client.【F:src/agentic_rag/storage/graphiti_client.py†L34-L80】

### Sync & Queueing
- Postgres `graph_sync_queue` records operations (`create`, `update`, `delete`) for downstream Neo4j synchronization; Postgres store exposes helpers to enqueue and track status.【F:src/agentic_rag/storage/postgres_store.py†L370-L436】

## Redis Cache
- Redis acts as shared cache for search/chat responses, obtained via `get_cache()` inside dependencies; configuration toggled via settings (`enable_redis_cache`).【F:src/api/dependencies.py†L33-L131】【F:src/config/settings.py†L147-L155】 Specific schema is dynamic (key/value); TTLs defined in code (`RedisCache` in `src/utils/cache.py`).

## Supabase REST Fallback
- `SupabaseRestStore` provides REST-based persistence when direct Postgres access is unavailable, mapping the same logical schema via Supabase APIs.【F:src/agentic_rag/storage/supabase_rest_store.py†L1-L200】
