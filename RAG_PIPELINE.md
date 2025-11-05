# RAG / GraphRAG Pipeline

## Ingestion Sources
- **LocalFileWatcher** loads config, watches directories, extracts MIME types, and submits files for processing via `process_file_for_rag` / `delete_document_by_file_id`.【F:src/rag_pipeline/sources/local_files.py†L17-L200】
- **GoogleDriveWatcher** (referenced in CLI) uses credentials paths from settings to poll Drive folders.【F:src/rag_pipeline/pipeline.py†L34-L48】

## Pipeline Orchestration
`DocumentIngestionPipeline` coordinates the end-to-end ingest flow.【F:src/agentic_rag/ingestion/pipeline.py†L70-L384】 Steps:
1. **Initialization** – loads chunking config, embedding generator, knowledge extractor, and (optionally) connection manager → Postgres/Neo4j stores & Graphiti client.【F:src/agentic_rag/ingestion/pipeline.py†L83-L166】
2. **Chunking** – selects semantic chunker (pydantic-ai agent) or simple rule-based chunker depending on config; metadata includes positional indexes.【F:src/agentic_rag/ingestion/chunker.py†L22-L190】
3. **Embedding** – `EmbeddingGenerator` batches requests to OpenAI/Ollama, caches results using MD5 keys, and supports fallback providers.【F:src/agentic_rag/ingestion/embedder.py†L23-L200】
4. **Storage** – `PostgresStore.store_document/store_chunks` insert documents and vectorized chunks, using pgvector format conversions.【F:src/agentic_rag/storage/postgres_store.py†L25-L102】
5. **Knowledge Extraction** – `KnowledgeExtractor` (pydantic-ai agent) extracts entities/relationships/facts while enforcing zero duplication; falls back to regex heuristics when no LLM client.【F:src/agentic_rag/ingestion/knowledge_extractor.py†L17-L200】
6. **Graph Sync** – Entities/relationships/facts passed to `GraphitiClient` → `Neo4jStore` for MERGE/relationship updates and importance scoring.【F:src/agentic_rag/storage/graphiti_client.py†L34-L80】【F:src/agentic_rag/storage/neo4j_store.py†L25-L166】
7. **Cross-references** – Postgres store updates chunk metadata with graph entity references and enqueues sync queue entries for later reconciliation.【F:src/agentic_rag/storage/postgres_store.py†L104-L205】【F:src/agentic_rag/storage/postgres_store.py†L370-L436】

## Vector & Hybrid Retrieval
- **VectorSearch** generates query embeddings via `EmbeddingGenerator`, runs `search_similar`/`hybrid_search_enhanced` SQL, and caches results per MD5 key.【F:src/agentic_rag/search/vector_search.py†L165-L199】【F:src/agentic_rag/storage/postgres_store.py†L150-L236】
- **GraphSearch** issues parallel fact/entity/relationship searches through Graphiti/Neo4j with chunk reference extraction for downstream fusion.【F:src/agentic_rag/search/graph_search.py†L147-L233】
- **HybridSearch** analyzes intent (`IntentAnalyzer`), runs vector and graph searches concurrently (when enabled), merges via `ResultRanker`, and logs analytics events.【F:src/agentic_rag/search/hybrid_search.py†L108-L194】
- **Cache Strategy** – Redis-backed `RedisCache` stores full search responses per `search_type` for 10 minutes, reducing duplicate work.【F:src/api/endpoints/search.py†L63-L107】【F:src/utils/cache.py†L1-L160】

## Re-ranking & Fusion
- `ResultRanker` (not shown above) reorders combined chunk results and applies boosting metrics recorded by hybrid search; final `SearchResponse` includes chunks plus optional graph entities/relationships.【F:src/agentic_rag/search/hybrid_search.py†L270-L315】
- Adaptive mode selects between pure vector and hybrid pipelines based on dominant intent (vector-heavy vs. graph oriented).【F:src/agentic_rag/search/hybrid_search.py†L133-L170】【F:src/api/endpoints/search.py†L83-L111】

## Answer Generation
- `super_agent` smart search tool wraps the pipeline, invoking hybrid search with intent analysis and packaging chunks/entities/facts for response synthesis.【F:src/agent/unified_agent.py†L156-L195】
- Chat responses include streaming (SSE/WebSocket) support and attach usage metrics (latency, tokens).【F:src/api/endpoints/chat.py†L38-L200】

## Retrieval Augmented Analytics
- Search analytics endpoints query partitioned analytics tables via `DashboardHandler`, enabling dashboards to monitor strategy mix, latency, tool usage, and feedback loops.【F:src/api/endpoints/analytics.py†L25-L258】【F:src/agentic_rag/storage/migrations/sql/004_analytics_schema.sql†L14-L355】
