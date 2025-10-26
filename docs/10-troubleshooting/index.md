# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Luminari Agent system, including Phase 3 Agent Intelligence Layer components.

## Table of Contents

- [Recently Fixed Issues (v1.2.3+)](#recently-fixed-issues-v123)
- [Quick Diagnostics](#quick-diagnostics)
- [Phase 3 Specific Issues](#phase-3-specific-issues)
- [Installation Issues](#installation-issues)
- [Configuration Problems](#configuration-problems)
- [Runtime Errors](#runtime-errors)
- [Performance Issues](#performance-issues)
- [Database Problems](#database-problems)
- [API Integration Issues](#api-integration-issues)
- [Memory System Issues](#memory-system-issues)
- [Agentic RAG Issues](#agentic-rag-issues)
- [Docker Issues](#docker-issues)
- [Monitoring and Debugging](#monitoring-and-debugging)

## Recently Fixed Issues (v1.2.4+)

These issues have been resolved in recent versions. If you're still experiencing them, ensure you're running the latest version:

### PostgreSQL Pool Not Initialized

**Symptoms:**
```
ConnectionError: PostgreSQL pool not initialized. Call await connection_manager.initialize() first.
```

**Fixed in v1.2.3:**
- Race condition in singleton pattern resolved with async lock
- Failed initialization now allows retry instead of permanent breakage
- Analytics logger initialization fixed (RAG tools now use singleton)

**Solution:** Upgrade to v1.2.3+. The connection manager now properly handles concurrent initialization and retries on failure.

### Neo4j Circuit Breaker Warnings

**Symptoms:**
```
WARNING: Neo4j circuit breaker is closed. Last error: None
```

**Fixed in v1.2.3:**
- Circuit breaker states were inverted (CLOSED should be healthy, not broken)
- Updated 9 locations to follow standard circuit breaker pattern
- Error messages now clearly indicate state: "OPEN - blocking requests" vs "CLOSED (healthy)"

**Solution:** Upgrade to v1.2.3+. Circuit breaker now correctly allows requests when CLOSED (healthy) and blocks when OPEN (broken).

### Analytics Logger Not Initialized

**Symptoms:**
```
WARNING: Failed to log search analytics: Analytics logger not initialized
```

**Fixed in v1.2.3:**
- RAG tools were creating their own ConnectionManager instances, bypassing analytics initialization
- Now use `get_connection_manager()` singleton which properly initializes analytics

**Solution:** Upgrade to v1.2.3+. Analytics automatically initialize with the connection manager.

### Supabase Deprecation Warnings

**Symptoms:**
```
DeprecationWarning: The 'timeout' parameter is deprecated
DeprecationWarning: The 'verify' parameter is deprecated
```

**Fixed in v1.2.3:**
- Updated Supabase client to use httpx client configuration
- Added warning filters for internal library warnings

**Solution:** Upgrade to v1.2.3+. No more deprecation warnings.

### Tool Returns Not Visible in UI

**Symptoms:**
- Tool calls shown but no tool results displayed
- Logs show `"tool_return": 0` despite tools executing successfully

**Fixed in v1.2.3:**
- Added post-stream extraction of tool returns from new_messages
- Results now displayed in collapsible expanders: "📥 Tool Result: {tool_name}"
- Smart truncation for long results (>2000 chars)

**Solution:** Upgrade to v1.2.3+. Tool returns now visible after streaming completes.

### SQL Query Syntax Errors (v1.2.4)

**Symptoms:**
```
Error executing SQL query: syntax error at or near ";"
```

**Fixed in v1.2.4:**
- Supabase RPC `execute_sql` function doesn't accept trailing semicolons
- LLM generates standard SQL with semicolons (e.g., `SELECT 1 as test_limit;`)
- Tool now automatically strips trailing semicolons before execution

**Solution:** Upgrade to v1.2.4+. Both `execute_sql` and `query_tabular_data` tools now handle semicolons correctly.

### Mem0 Memory Initialization Error (v1.2.4)

**Symptoms:**
```
ValidationError: A valid PostgreSQL connection string must be provided
ERROR: Failed to initialize Mem0 client
```

**Fixed in v1.2.4:**
- Mem0 client was receiving `SUPABASE_URL` (HTTPS endpoint) instead of `DATABASE_URL` (PostgreSQL connection)
- Changed `src/clients/memory.py` to use correct `database_url` configuration

**Solution:**
1. Upgrade to v1.2.4+
2. Ensure `.env` has both variables set:
   ```bash
   SUPABASE_URL=https://xxx.supabase.co          # For REST API
   DATABASE_URL=postgresql://postgres.xxx:...    # For Mem0 memory
   ```

### Tool Arguments Showing "No Arguments" (v1.2.4)

**Symptoms:**
- During streaming, tool calls show confusing "No arguments" message
- Arguments not visible until streaming completes

**Fixed in v1.2.4:**
- Replaced complex JSON parsing with clear pending state
- Now displays: "⏳ Tool executing... (result will appear below when complete)"

**Technical Note:** This is a Pydantic AI limitation - tool arguments aren't fully available during streaming.

**Solution:** Upgrade to v1.2.4+. UX now sets clear expectations about pending tool execution.

### MCP Deprecation Warning (v1.2.4)

**Symptoms:**
```
DeprecationWarning: `run_mcp_servers` is deprecated, use `async with agent:` instead
```

**Fixed in v1.2.4:**
- Updated MCP handler to use modern Pydantic AI v1.0.15 API
- Changed from `async with super_agent.run_mcp_servers():` to `async with super_agent:`

**Solution:** Upgrade to v1.2.4+. No more MCP deprecation warnings.

---

## Quick Diagnostics

### Health Check Commands

```bash
# Check system health
curl http://localhost:8501/health

# Detailed health check (if FastAPI endpoints are running)
curl http://localhost:8058/health/detailed

# Check individual components
curl http://localhost:8058/health/components/database
curl http://localhost:8058/health/components/llm
curl http://localhost:8058/health/components/embedding
```

### Environment Validation

```bash
# Check Python version
python --version  # Should be 3.11+

# Verify virtual environment
which python
pip list | grep -E "(streamlit|pydantic-ai|supabase)"

# Check environment variables
env | grep -E "(SUPABASE|LLM|EMBEDDING|NEO4J)"
```

## Phase 3 Specific Issues

### Intent Analysis Problems

#### 1. Poor Intent Classification Accuracy

**Error:** Intent classification below 90% accuracy threshold

**Diagnosis:**
```python
# Test intent analysis directly
from src.agentic_rag.agent.intent_analyzer import IntentAnalyzer

analyzer = IntentAnalyzer()
test_queries = [
    "What is the capital of France?",
    "How is Microsoft related to OpenAI?",
    "When did AI research begin?",
    "Compare Python and JavaScript",
    "What are emerging AI trends?"
]

for query in test_queries:
    result = await analyzer.analyze(query)
    print(f"Query: {query}")
    print(f"Intent: {result.primary_intent}")
    print(f"Confidence: {result.confidence}")
    print("---")
```

**Solution:**
```bash
# Check intent analysis configuration
export INTENT_ANALYSIS_TIMEOUT=2.0
export CONFIDENCE_THRESHOLD=0.7

# Update intent patterns if needed
# Review src/agentic_rag/agent/intent_analyzer.py

# Retrain or adjust intent scoring weights
```

#### 2. Entity Extraction Failures

**Error:** `Entity extraction returned empty results`

**Diagnosis:**
```python
# Test entity extraction
query = "What is the relationship between Microsoft and OpenAI in 2023?"
result = await analyzer.analyze(query)

print(f"Entities found: {len(result.entities)}")
for entity in result.entities:
    print(f"  {entity.name} ({entity.type})")

print(f"Temporal context: {result.temporal_context}")
```

**Solution:**
```bash
# Check entity extraction model
export EXTRACTION_MODEL=gpt-4o-mini

# Verify entity patterns in configuration
# Update entity type mappings if needed
```

### Search Strategy Issues

#### 1. Poor Search Strategy Selection

**Error:** Suboptimal search strategy chosen (below 88% accuracy)

**Diagnosis:**
```python
# Test search routing
from src.agentic_rag.agent.router import SearchRouter

router = SearchRouter()
test_cases = [
    ("What is machine learning?", "vector_search"),
    ("How is Tesla related to SpaceX?", "graph_search"),
    ("Compare AI frameworks", "hybrid_search"),
    ("AI trends in healthcare", "comprehensive_search")
]

for query, expected_strategy in test_cases:
    intent_result = await analyzer.analyze(query)
    selected_strategy = await router.route_query(query, intent_result)

    print(f"Query: {query}")
    print(f"Expected: {expected_strategy}")
    print(f"Selected: {selected_strategy}")
    print(f"Match: {expected_strategy == selected_strategy}")
    print("---")
```

**Solution:**
```python
# Adjust routing thresholds in configuration
ROUTING_CONFIG = {
    "complexity_threshold": 0.8,
    "relationship_confidence": 0.85,
    "temporal_confidence": 0.8,
    "comparison_confidence": 0.85
}

# Review routing logic in src/agentic_rag/agent/router.py
```

#### 2. Search Performance Below Targets

**Error:** Search latency exceeds performance targets

**Diagnosis:**
```python
# Performance test individual search strategies
import time
from src.agentic_rag.agent.tools import vector_search, graph_search, hybrid_search

async def test_search_performance():
    query = "artificial intelligence applications"

    # Vector search target: <150ms
    start = time.time()
    vector_result = await vector_search(query)
    vector_time = (time.time() - start) * 1000
    print(f"Vector search: {vector_time:.2f}ms (target: <150ms)")

    # Graph search target: <500ms
    start = time.time()
    graph_result = await graph_search(query)
    graph_time = (time.time() - start) * 1000
    print(f"Graph search: {graph_time:.2f}ms (target: <500ms)")

    # Hybrid search target: <300ms
    start = time.time()
    hybrid_result = await hybrid_search(query)
    hybrid_time = (time.time() - start) * 1000
    print(f"Hybrid search: {hybrid_time:.2f}ms (target: <300ms)")

await test_search_performance()
```

**Solution:**
```bash
# Optimize database indexes
# Check pgvector index configuration
# Verify Neo4j indexes for entities and relationships

# Adjust timeout settings
export VECTOR_SEARCH_TIMEOUT=2.0
export GRAPH_SEARCH_TIMEOUT=3.0

# Enable caching
export ENABLE_CACHING=true
export GRAPH_CACHE_SIZE=500
export EMBEDDING_CACHE_SIZE=1000
```

### Knowledge Graph Integration Issues

#### 1. Neo4j Connection Problems

**Error:** `Neo4j connection failed` or `Database not available`

**Diagnosis:**
```bash
# Test Neo4j connectivity
curl http://localhost:7474/
curl -u neo4j:password http://localhost:7474/db/data/

# Test from Python
python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687',
                             auth=('neo4j', 'password'))
with driver.session() as session:
    result = session.run('RETURN 1 as test')
    print('Neo4j connection OK:', result.single()['test'])
driver.close()
"
```

**Solution:**
```bash
# Start Neo4j if not running
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# Verify environment variables
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=password

# Initialize knowledge graph
python -m src.agentic_rag.storage.neo4j_store init
```

#### 2. Knowledge Extraction Issues

**Error:** `Entity extraction failed` or `Relationship mapping error`

**Diagnosis:**
```python
# Test knowledge extraction pipeline
from src.agentic_rag.ingestion.knowledge_extractor import KnowledgeExtractor

extractor = KnowledgeExtractor()
test_text = "Microsoft invested $10 billion in OpenAI in 2023."

entities = await extractor.extract_entities(test_text)
relationships = await extractor.extract_relationships(test_text)
facts = await extractor.extract_facts(test_text)

print(f"Entities: {len(entities)}")
print(f"Relationships: {len(relationships)}")
print(f"Facts: {len(facts)}")

# Verify each extraction
for entity in entities:
    print(f"Entity: {entity.name} ({entity.type})")
```

**Solution:**
```bash
# Check extraction model configuration
export EXTRACTION_MODEL=gpt-4o-mini
export MAX_ENTITIES_PER_CHUNK=10
export MAX_FACT_LENGTH=500

# Verify Graphiti integration
pip install --upgrade graphiti-ai

# Check extraction prompts and update if needed
```

### Response Generation Issues

#### 1. Missing Citations

**Error:** Response lacks required source citations (below 100% target)

**Diagnosis:**
```python
# Test response generation
from src.agentic_rag.agent.response_generator import ResponseGenerator

generator = ResponseGenerator()
query = "What is machine learning?"
mock_results = [
    {"content": "ML is a subset of AI", "source": "ai_guide.pdf", "confidence": 0.9}
]

response = await generator.generate_response(query, mock_results)

print(f"Answer: {response.answer}")
print(f"Sources: {len(response.sources)}")
print(f"Citations included: {len(response.sources) > 0}")

for source in response.sources:
    print(f"  - {source.get('source', 'NO SOURCE')}")
```

**Solution:**
```python
# Update response generation to enforce citations
# Check src/agentic_rag/agent/response_generator.py

# Ensure all search results include source metadata
# Verify citation extraction logic
```

#### 2. Poor Confidence Scoring

**Error:** Confidence scores not in expected 0.0-1.0 range or inaccurate

**Diagnosis:**
```python
# Test confidence calculation
response = await generator.generate_response(query, mock_results)

print(f"Confidence: {response.confidence}")
print(f"Type: {type(response.confidence)}")
print(f"In range [0,1]: {0.0 <= response.confidence <= 1.0}")

# Test with multiple source qualities
low_quality = [{"content": "basic info", "confidence": 0.3}]
high_quality = [{"content": "detailed info", "confidence": 0.95}]

low_response = await generator.generate_response(query, low_quality)
high_response = await generator.generate_response(query, high_quality)

print(f"Low quality confidence: {low_response.confidence}")
print(f"High quality confidence: {high_response.confidence}")
```

**Solution:**
```python
# Review confidence calculation algorithm
# Adjust confidence weighting factors
# Ensure proper source quality assessment
```

## Agentic RAG Issues

### Dual Database Sync Problems

#### 1. Content Duplication in Neo4j

**Error:** Content found in Neo4j (violates zero duplication principle)

**Diagnosis:**
```cypher
// Check for content in Neo4j nodes
MATCH (n)
WHERE EXISTS(n.content) AND length(n.content) > 100
RETURN count(n) as nodes_with_content,
       avg(length(n.content)) as avg_content_length
```

**Solution:**
```cypher
// Remove content from Neo4j nodes
MATCH (n)
WHERE EXISTS(n.content)
REMOVE n.content
```

#### 2. Reference ID Mismatches

**Error:** Chunk references in Neo4j don't match PostgreSQL IDs

**Diagnosis:**
```python
# Verify reference integrity
from src.agentic_rag.storage.postgres_store import PostgresStore
from src.agentic_rag.storage.neo4j_store import Neo4jStore

postgres_store = PostgresStore()
neo4j_store = Neo4jStore()

# Get sample chunk IDs from PostgreSQL
pg_chunk_ids = await postgres_store.get_chunk_ids(limit=10)

# Check if they exist in Neo4j references
for chunk_id in pg_chunk_ids:
    neo4j_refs = await neo4j_store.get_chunk_references(chunk_id)
    print(f"Chunk {chunk_id}: {len(neo4j_refs)} Neo4j references")
```

**Solution:**
```python
# Rebuild reference integrity
await neo4j_store.rebuild_chunk_references()

# Verify storage efficiency
efficiency = await calculate_storage_efficiency()
print(f"Storage efficiency: {efficiency:.1%} (target: >99%)")
```

### Search Result Merging Issues

#### 1. Poor Hybrid Search Results

**Error:** Hybrid search performs worse than individual strategies

**Diagnosis:**
```python
# Compare individual vs hybrid results
vector_results = await vector_search(query)
graph_results = await graph_search(query)
hybrid_results = await hybrid_search(query)

print(f"Vector results: {len(vector_results.results)}")
print(f"Graph results: {len(graph_results.results)}")
print(f"Hybrid results: {len(hybrid_results.results)}")
print(f"Hybrid quality: {hybrid_results.quality_score}")
```

**Solution:**
```python
# Adjust result merging weights
MERGE_CONFIG = {
    "vector_weight": 0.6,
    "graph_weight": 0.4,
    "boost_factor": 0.2,
    "diversity_threshold": 0.8
}

# Review merging algorithm in tools.py
```

### Ingestion Pipeline Issues

#### 1. Import Errors in Ingestion Module

**Error:** `ImportError: cannot import name 'ChunkingConfig' from 'src.agentic_rag.ingestion.chunker'`

**Root Cause:**
- The ingestion `__init__.py` was importing classes that don't exist
- Functions like `get_chunking_config()` and `get_embedding_config()` were used instead of classes

**Solution:**

Already fixed in codebase. If you encounter this:

```python
# src/agentic_rag/ingestion/__init__.py should import:
from .chunker import DocumentChunk, SemanticChunker, SimpleChunker, get_chunking_config
from .embedder import EmbeddingGenerator, get_embedding_config

# NOT these (they don't exist):
# from .chunker import ChunkingConfig, ChunkingStrategy  # ❌ Wrong
# from .embedder import EmbeddingConfig  # ❌ Wrong
```

**Verification:**
```bash
python -c "from src.agentic_rag.ingestion.pipeline import DocumentIngestionPipeline; print('✅ Import successful')"
```

#### 2. Missing CLI Interface

**Error:** Module cannot be run as `python -m src.agentic_rag.ingestion.pipeline`

**Solution:**

CLI interface created at `src/agentic_rag/ingestion/__main__.py`:

```bash
# Run ingestion with default path
make ingest

# Run with custom path
python -m src.agentic_rag.ingestion.pipeline ingest --path /path/to/docs

# Run with verbose logging
python -m src.agentic_rag.ingestion.pipeline ingest --verbose

# Test connection first
python test_db_connection.py
```

**Available options:**
- `--path` - Directory containing markdown files (default: docs/example_big_tech_docs_for_ingestion_testing)
- `--clean` - Clean existing data before ingestion
- `--verbose` / `-v` - Enable debug logging

#### 3. ConnectionManager Not Initialized (CRITICAL - FIXED 2025-10-09)

**Error:** `ConnectionError: PostgreSQL pool not initialized. Call await connection_manager.initialize() first.`

**Root Cause:**
The ingestion pipeline was creating `ConnectionManager()` but never calling `await connection_manager.initialize()`, leaving all connection pools as `None`.

**Status:** ✅ **FIXED** in Phase 2 core infrastructure updates.

**Solution (already applied):**
- `DocumentIngestionPipeline` now has proper async initialization
- Use `async with DocumentIngestionPipeline() as pipeline` pattern
- Automatic cleanup via context manager

**Verification:**
```bash
python -m src.agentic_rag.ingestion ingest --path docs/example_docs
```

If you still see this error, ensure you're using the latest code with the async context manager pattern.

#### 4. Neo4j Authentication Failure (Updated 2025-10-09)

**Error:**
```
neo4j.exceptions.AuthError: {neo4j_code: Neo.ClientError.Security.Unauthorized}
{message: The client is unauthorized due to authentication failure.}
```

**Common Causes:**
1. **Instance paused** - Neo4j Aura free tier auto-pauses after 3 days of inactivity
2. **Password expired or changed**
3. **Using "Aura" instead of "neo4j" as username**
4. **Configuration masking bug** - `ConnectionManager` receiving masked password (FIXED in 2025-10-09)

**Solution Steps:**

1. **Login to Neo4j Aura Console:**
   ```
   https://neo4j.com/cloud/aura-free
   ```

2. **Check Instance Status:**
   - Find your instance (e.g., `f5c57870.databases.neo4j.io`)
   - If status shows "Paused" → Click "Resume" button
   - Wait 30-60 seconds for instance to start

3. **Reset Password (if needed):**
   - Click instance → "Reset Password"
   - Copy new password (shown only once!)
   - Save to password manager

4. **Update `.env` file:**
   ```bash
   NEO4J_URI=neo4j+s://YOUR_INSTANCE_ID.databases.neo4j.io
   NEO4J_USER=neo4j  # MUST be "neo4j", NOT "Aura"
   NEO4J_PASSWORD=YOUR_NEW_PASSWORD
   NEO4J_DATABASE=neo4j
   ```

5. **Test Connection:**
   ```bash
   python scripts/init_neo4j.py
   ```

**Important Notes:**
- Use URI scheme `neo4j+s://` (encryption embedded in URI)
- Username is always `neo4j` for Aura instances
- Free tier instances auto-pause after 3 days - resume before use

**Diagnostic Tool:**
Run the comprehensive connection test to identify specific issues:
```bash
python scripts/test_neo4j_connection.py
```

This will perform 7 validation steps and provide specific troubleshooting guidance.

#### 4a. Configuration Masking Bug (FIXED 2025-10-09)

**Error:** Neo4j authentication fails even with correct credentials

**Root Cause:**
The `Settings.to_dict()` method in `src/config/settings.py` was masking sensitive values (including `neo4j_password`) by replacing them with `"***MASKED***"` for security. When `ConnectionManager` called `get_config().dict()`, it received the masked password instead of the actual password, causing authentication to always fail.

**Symptoms:**
- Direct Neo4j driver test works (using `os.getenv()`)
- `ConnectionManager` initialization fails with auth error
- Password is correct in `.env` file
- Simple scripts succeed, but ingestion pipeline fails

**Diagnosis:**
```python
# Check if you have the fix
from src.config import get_settings

settings = get_settings()

# This should show masked values (for logging safety)
masked = settings.to_dict(mask_sensitive=True)
print(f"Masked password: {masked['neo4j_password']}")  # Should be "***MASKED***"

# This should show real values (for internal use)
unmasked = settings.to_dict(mask_sensitive=False)
print(f"Real password length: {len(unmasked['neo4j_password'])}")  # Should be actual length
```

**Solution:**
This was fixed on 2025-10-09. Update to the latest code:

1. **File: `src/config/settings.py:516-543`**
   - Added `mask_sensitive` parameter to `to_dict()` method
   - Defaults to `True` for logging safety
   - Can be set to `False` for internal use

2. **File: `src/agentic_rag/config.py:161`**
   - Updated `Config.dict()` to use `mask_sensitive=False`
   - Ensures `ConnectionManager` gets real credentials

3. **Verify the fix:**
   ```bash
   # Should work now
   python scripts/init_neo4j.py
   ```

**Impact:**
- Security maintained: Logging still masks sensitive values
- Internal code gets actual credentials: ConnectionManager can authenticate
- No `.env` changes needed: Fix is in the code, not configuration

#### 5. Document Ingestion Failing

**Error:** Various errors during document ingestion

**Diagnosis:**
```bash
# Check if databases are accessible
python test_db_connection.py

# Test with single document (using proper async pattern)
python -c "
import asyncio
from pathlib import Path
from src.agentic_rag.ingestion.pipeline import DocumentIngestionPipeline

async def test():
    async with DocumentIngestionPipeline() as pipeline:
        result = await pipeline.ingest_document(
            content='Test content',
            title='Test',
            source='test.md'
        )
        print(f'Success: {result.success}')
        print(f'Chunks: {result.chunks_created}')
        print(f'Entities: {result.entities_extracted}')

asyncio.run(test())
"
```

**Common causes and solutions:**

1. **Database connection issues** - See DATABASE_URL Configuration Errors above
2. **OpenAI API key invalid** - Check `LLM_API_KEY` and `EMBEDDING_API_KEY` in `.env`
3. **Neo4j unavailable** - Disable graph features temporarily:
   ```env
   ENABLE_GRAPH=false
   ENABLE_GRAPH_SEARCH=false
   ```
4. **Out of memory** - Reduce batch sizes:
   ```env
   INGESTION_BATCH_SIZE=5
   MAX_CONCURRENT_EMBEDDINGS=10
   MAX_CONCURRENT_EXTRACTIONS=5
   ```

#### 6. Entity Extraction JSON Parsing Error (FIXED 2025-10-14)

**Error:** `KeyError: '"name"'` during entity extraction

**Root Cause:**
JSON example in prompt had unescaped curly braces: `{"name": "...", "type": "..."}` caused Python f-string to try interpolating variables.

**Status:** ✅ **FIXED** in Phase 7 entity extraction updates.

**Solution (already applied):**
```python
# src/agentic_rag/ingestion/knowledge_extractor.py:248
# Escaped curly braces by doubling them
{{\"name\": \"Company\", \"type\": \"ORGANIZATION\"}}
```

**Verification:**
Entity extraction now working perfectly - extracting 50-100+ entities per document.

#### 7. Relationship Storage KeyError (FIXED 2025-10-14)

**Error:** `KeyError: 'entity1_id'` when storing relationships

**Root Cause:**
Key mismatch - pipeline passed entity names (`source`, `target`) but Neo4j store expected entity IDs (`entity1_id`, `entity2_id`).

**Status:** ✅ **FIXED** in Phase 7 relationship linking fix.

**Solution (already applied):**
- Modified `add_relationships()` to accept entity names and lookup IDs internally
- Added backward compatibility for both naming conventions
- Changed Cypher: `MATCH (e1:Entity) WHERE e1.name = $entity1_name`
- Location: `src/agentic_rag/storage/neo4j_store.py:65-141`

**Verification:**
```bash
# Test ingestion now works without KeyError
python -m src.agentic_rag.ingestion ingest --path docs/example_docs/light
```

#### 8. Neo4j v5+ Deprecated size() Function (FIXED 2025-10-14)

**Error:** `A pattern expression should only be used... an alternative is to replace size() with COUNT {}`

**Root Cause:**
`size()` function deprecated in Neo4j v5+ for pattern expressions.

**Status:** ✅ **FIXED** in Phase 7 Neo4j compatibility update.

**Solution (already applied):**
```cypher
# Before (Neo4j v4):
size((e)-[:RELATED_TO]-())

# After (Neo4j v5+):
COUNT { (e)-[:RELATED_TO]-() }
```

**Locations:** `src/agentic_rag/storage/neo4j_store.py:134, 371-372`

#### 9. Vector Search Embedding Format (FIXED 2025-10-14)

**Error:** `TypeError: expected str, got list` during vector search

**Root Cause:**
PostgreSQL pgvector expects embeddings as strings `"[1.0,2.0,3.0]"`, but embedder returns Python lists.

**Status:** ✅ **FIXED** in Phase 7 vector search validation.

**Solution (already applied):**
```python
# src/agentic_rag/search/vector_search.py:247-254
if isinstance(query_embedding, list):
    query_embedding = "[" + ",".join(str(x) for x in query_embedding) + "]"
```

**Verification:**
```bash
# Test vector search
python scripts/test_search_strategies.py
# Should show: Vector Search: ✅ PASS
```

#### 10. Event Loop Compatibility Issues (FIXED 2025-10-13)

**Error:** `RuntimeError: Task <Task pending> attached to a different loop` or similar event loop errors

**Root Cause:**
asyncpg pool created in module-scoped loop, tests ran in function-scoped loops.

**Status:** ✅ **FIXED** in Phase 7 testing infrastructure.

**Solution (already applied - 5 parts):**
1. Added `@pytest.mark.asyncio(loop_scope="module")` to test class
2. Set `asyncio_default_fixture_loop_scope = "module"` in pyproject.toml
3. Module-scoped `event_loop` fixture in conftest.py
4. Module-scoped `connection_manager` fixture
5. Explicit loop binding in `asyncpg.create_pool()`

**Verification:**
```bash
pytest tests/test_phase1_infrastructure.py -v
# Previously failing event loop tests now run correctly
```

#### 11. Storage Backend Selection (PostgreSQL vs REST API)

**Issue:** Confused about which storage backend to use

**Decision Tree:**

```
Do PostgreSQL ports (5432/6543) work?
├─ YES → Use PostgreSQL (default, automatic)
│  └─ Benefits: Faster, connection pooling, full SQL features
│  └─ Command: python -m src.agentic_rag.ingestion ingest
│
└─ NO (ports blocked by firewall/VPN/WSL2) → Use REST API
   └─ Benefits: Works over HTTPS (443), no network config needed
   └─ Command: python -m src.agentic_rag.ingestion ingest --rest-api
```

**Automatic Fallback (Recommended):**

The system automatically tries PostgreSQL first and falls back to REST API on failure:

```bash
# Default - intelligent fallback
make ingest
python -m src.agentic_rag.ingestion ingest

# Output shows which backend is used:
# → Attempting direct PostgreSQL connection...
# ⚠️  PostgreSQL connection failed: [Errno 101] Network is unreachable
# → Falling back to Supabase REST API...
```

**Force REST API Mode:**

```bash
# Skip PostgreSQL attempt, go straight to REST API
python -m src.agentic_rag.ingestion ingest --rest-api
```

**Test Connectivity:**

```bash
# Test PostgreSQL
python test_db_connection.py
# Should output: ✅ Database connected!

# Test REST API
python test_supabase_rest.py
# Should output: ✅ Supabase REST API is working!
```

**Performance Comparison:**

| Feature | PostgreSQL (Primary) | REST API (Fallback) |
|---------|---------------------|---------------------|
| Speed | ⚡ Fast | 🐌 Slower (REST overhead) |
| Connection Pooling | ✅ Yes (5-20 connections) | ❌ No |
| Network Requirements | Direct port 5432/6543 | HTTPS port 443 |
| Firewall Compatibility | ⚠️ Often blocked | ✅ Rarely blocked |
| Feature Support | ✅ Full SQL features | ⚠️ Basic operations |
| Best For | Production, local dev | Restrictive networks, WSL2 |

**When to Use Each:**

- **PostgreSQL**: Default choice when network allows
  - Local development
  - Production deployments
  - Docker containers
  - Networks without restrictions

- **REST API**: Fallback when PostgreSQL fails
  - Corporate VPNs/firewalls
  - WSL2 with IPv6 issues
  - Public Wi-Fi networks
  - Restrictive security policies

**Current Known Issues:**

1. **WSL2 + Supabase**: Direct DB is IPv6-only, WSL2 doesn't support IPv6 well
   - **Solution**: REST API fallback works perfectly

2. **Corporate VPNs**: Often block PostgreSQL ports
   - **Solution**: Use `--rest-api` flag

3. **Connection Pooler**: May have IPv4 support
   - **Try**: Update DATABASE_URL to use pooler (port 6543)

## Installation Issues

### Common Installation Problems

#### 1. Python Version Compatibility

**Error:** `Python 3.11+ required`

**Solution:**
```bash
# Install Python 3.11 or higher
pyenv install 3.11.0
pyenv local 3.11.0

# Or use conda
conda create -n luminari python=3.11
conda activate luminari
```

#### 2. Dependency Conflicts

**Error:** `pip install fails with dependency conflicts`

**Solution:**
```bash
# Clean installation
pip uninstall -y -r requirements.txt
pip cache purge
pip install -r requirements.txt

# Alternative: Use pip-tools
pip install pip-tools
pip-compile requirements.in
pip install -r requirements.txt
```

#### 3. System Dependencies Missing

**Error:** `gcc: command not found` or similar build errors

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install build-essential python3-dev

# macOS
xcode-select --install

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
sudo yum install python3-devel
```

### Installation Verification

```bash
# Run setup
make setup

# Verify installation
python -c "import streamlit, pydantic_ai, supabase; print('All imports successful')"

# Test basic functionality
python -c "from src.clients.database import get_supabase_client; print('Database client OK')"
```

## Configuration Problems

### Environment Variables

#### 1. Missing Required Variables

**Error:** `KeyError: 'SUPABASE_URL'`

**Solution:**
```bash
# Copy example configuration
cp .env.example .env

# Edit with your values
nano .env

# Verify variables are loaded
python -c "import os; print(os.getenv('SUPABASE_URL'))"
```

#### 2. Invalid API Keys

**Error:** `Authentication failed` or `Invalid API key`

**Diagnosis:**
```bash
# Test Supabase connection
python -c "
from src.clients.database import get_supabase_client
client = get_supabase_client()
result = client.table('documents').select('*').limit(1).execute()
print('Supabase OK' if result else 'Supabase Failed')
"

# Test LLM API
python -c "
import asyncio
from src.clients.llm import get_llm_client
async def test():
    client = get_llm_client()
    response = await client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{'role': 'user', 'content': 'test'}],
        max_tokens=5
    )
    print('LLM OK')
asyncio.run(test())
"
```

#### 3. Database Schema Issues

**Error:** `relation "documents" does not exist`

**Solution:**
```bash
# Run SQL setup scripts
# Run in Supabase SQL Editor:
# Copy contents of src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql
# Paste into SQL Editor and click "Run"

# Or via psql (if you have direct database access):
psql -h your-supabase-host -U postgres -d postgres -f src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql

# Or use Supabase dashboard to run the scripts
```

## Runtime Errors

### Common Runtime Issues

#### 1. Streamlit Connection Errors

**Error:** `ConnectionError: Failed to connect to Streamlit`

**Diagnosis:**
```bash
# Check if port is in use
lsof -i :8501

# Check Streamlit logs
streamlit run src/ui/streamlit_app.py --logger.level debug
```

**Solution:**
```bash
# Use different port
streamlit run src/ui/streamlit_app.py --server.port 8502

# Clear Streamlit cache
rm -rf ~/.streamlit/
```

#### 2. Import Errors

**Error:** `ModuleNotFoundError: No module named 'src'`

**Solution:**
```bash
# Install in development mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Verify Python path
python -c "import sys; print(sys.path)"
```

#### 3. Async/Await Issues

**Error:** `RuntimeError: This event loop is already running`

**Solution:**
```python
# In Jupyter notebooks, use nest_asyncio
import nest_asyncio
nest_asyncio.apply()

# Or use asyncio.create_task() instead of asyncio.run()
```

## Performance Issues

### Slow Response Times

#### 1. Database Query Optimization

**Diagnosis:**
```sql
-- Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check index usage
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE tablename = 'documents';
```

**Solution:**
```sql
-- Add indexes for common queries
CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING gin (metadata);
```

#### 2. Memory Usage Optimization

**Diagnosis:**
```bash
# Monitor memory usage
htop
# Or
ps aux | grep python | head -10

# Check Python memory usage
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

**Solution:**
```python
# In your .env file
STREAMLIT_SERVER_MAX_UPLOAD_SIZE=200
STREAMLIT_SERVER_MAX_MESSAGE_SIZE=200

# Optimize batch sizes
EMBEDDING_BATCH_SIZE=10
RAG_CHUNK_SIZE=1000
```

#### 3. API Rate Limiting

**Error:** `Rate limit exceeded`

**Solution:**
```python
# Check rate limit status
curl http://localhost:8058/health/rate-limits/your-user-id

# Adjust rate limits in configuration
# Edit src/utils/rate_limiting.py
```

## Database Problems

### Connection Issues

#### 1. Supabase Connection Timeout

**Error:** `Connection timeout`

**Diagnosis:**
```bash
# Test network connectivity
ping your-supabase-host.supabase.co

# Test database connection
psql "postgresql://postgres:password@your-host:5432/postgres" -c "SELECT 1;"
```

**Solution:**
```bash
# Check firewall settings
# Verify Supabase project is not paused
# Check connection pooling settings
```

#### 2. DATABASE_URL Configuration Errors

**Error:** `KeyError: 'DATABASE_URL'` or `invalid DSN: scheme is expected to be either "postgresql" or "postgres", got 'https'`

**Root Causes:**
1. DATABASE_URL contains HTTPS URL instead of PostgreSQL connection string
2. Password contains special characters that need URL encoding
3. Shell environment variable overrides .env file
4. Config dict keys using wrong case (uppercase vs lowercase)

**Solution:**

1. **Correct DATABASE_URL format** in `.env`:
```env
# WRONG - This is the API URL:
DATABASE_URL=https://your-project.supabase.co

# CORRECT - PostgreSQL connection string with URL-encoded password:
DATABASE_URL=postgresql://postgres:your%3Fpass%24word@db.your-project.supabase.co:5432/postgres

# URL encoding for special characters:
#   ? becomes %3F
#   $ becomes %24
#   @ becomes %40
#   & becomes %26
```

2. **Clear cached environment variables:**
```bash
# Check if DATABASE_URL is set in shell
env | grep DATABASE_URL

# Unset if needed
unset DATABASE_URL

# Or restart terminal session
```

3. **Test configuration:**
```bash
python -c "from src.config import get_settings; print(get_settings().database_url)"
# Should output: postgresql://postgres:...
```

**Get correct connection string from Supabase:**
1. Go to **Project Settings → Database**
2. Find **Connection string** section
3. Select **URI** tab
4. Copy and URL-encode the password
5. Add to `.env`

**Alternative: Use connection pooler** (recommended for WSL2):
```env
# Session pooler (port 5432) - recommended for WSL2 and IPv4-only networks
DATABASE_URL=postgresql://postgres.your-project:[password]@aws-1-us-east-2.pooler.supabase.com:5432/postgres

# Transaction pooler (port 6543) - may timeout on WSL2
DATABASE_URL=postgresql://postgres.your-project:[password]@aws-1-us-east-2.pooler.supabase.com:6543/postgres

# Note: Get correct region from Supabase dashboard → Settings → Database → Connection string
```

#### 3. WSL2 Network Connectivity Issues

**Error:** `OSError: [Errno 101] Network is unreachable` when connecting to Supabase

**Symptoms:**
```
Failed to initialize PostgreSQL: [Errno 101] Network is unreachable
ping: connect: Network is unreachable
```

**Quick Fixes (try in order):**

1. **Restart WSL2** (from Windows PowerShell as Administrator):
```powershell
wsl --shutdown
# Wait 10 seconds, then reopen WSL2
```

2. **Check basic connectivity:**
```bash
# Test internet
ping -c 2 8.8.8.8

# Test DNS
nslookup db.your-project.supabase.co

# Test database port
nc -zv db.your-project.supabase.co 5432
```

3. **Fix WSL2 DNS:**
```bash
# Check current DNS
cat /etc/resolv.conf

# Fix if needed
sudo nano /etc/wsl.conf
# Add:
[network]
generateResolvConf = false

# Set DNS manually
sudo rm /etc/resolv.conf
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf

# Restart WSL2
```

4. **Use Session pooler** (port 5432 - recommended for WSL2):
```env
# Session pooler works reliably on WSL2
DATABASE_URL=postgresql://postgres.your-project:password@aws-1-us-east-2.pooler.supabase.com:5432/postgres

# Note: Transaction pooler (port 6543) may timeout on WSL2
```

5. **Environment variable caching** - Shell may have cached DATABASE_URL:
```bash
# Check if DATABASE_URL is exported in shell
env | grep DATABASE_URL

# Unset if it exists
unset DATABASE_URL

# Or start a new terminal session
```

#### 4. Vector Extension Issues

**Error:** `extension "vector" does not exist`

**Solution:**
```sql
-- Enable pgvector extension in Supabase dashboard
-- Or run in SQL editor:
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### Data Issues

#### 1. Embedding Dimension Mismatch

**Error:** `vector dimension mismatch`

**Solution:**
```sql
-- Check current dimensions
SELECT embedding <-> '[0,0,0]'::vector FROM documents LIMIT 1;

-- Update table schema if needed
ALTER TABLE documents ALTER COLUMN embedding TYPE vector(1536);

-- For Ollama (768 dimensions)
ALTER TABLE documents ALTER COLUMN embedding TYPE vector(768);
```

## API Integration Issues

### LLM Provider Issues

#### 1. OpenAI API Errors

**Error:** `Invalid API key` or `Rate limit exceeded`

**Diagnosis:**
```bash
# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Check usage
curl https://api.openai.com/v1/usage \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

#### 2. Ollama Connection Issues

**Error:** `Connection refused to localhost:11434`

**Solution:**
```bash
# Start Ollama service
ollama serve

# Check if running
curl http://localhost:11434/api/tags

# Pull required models
ollama pull llama3.1
ollama pull nomic-embed-text
```

### Web Search Issues

#### 1. Brave API Problems

**Error:** `Brave API authentication failed`

**Solution:**
```bash
# Test Brave API
curl -H "X-Subscription-Token: $BRAVE_API_KEY" \
  "https://api.search.brave.com/res/v1/web/search?q=test"

# Check API quota
# Visit Brave API dashboard
```

#### 2. SearXNG Fallback Issues

**Error:** `SearXNG instance not responding`

**Solution:**
```bash
# Test SearXNG instance
curl "$SEARXNG_BASE_URL/search?q=test&format=json"

# Start local SearXNG with Docker
docker run -d -p 8080:8080 searxng/searxng
```

## Memory System Issues

### Mem0 Integration Problems

#### 1. Memory Service Connection

**Error:** `Failed to connect to memory service`

**Diagnosis:**
```python
# Test mem0 connection
from src.clients.memory import get_mem0_client
client = get_mem0_client()
result = client.add("test memory", user_id="test")
print(result)
```

**Solution:**
```bash
# Check mem0 configuration
# Verify vector store connection
# Check embedding service
```

#### 2. Memory Retrieval Issues

**Error:** `No memories found` or `Memory search failed`

**Solution:**
```python
# Check memory storage
client = get_mem0_client()
memories = client.get_all(user_id="your-user-id")
print(f"Found {len(memories)} memories")

# Test memory search
results = client.search("test query", user_id="your-user-id")
print(results)
```

## Docker Issues

### Container Problems

#### 1. Build Failures

**Error:** `Docker build failed`

**Solution:**
```bash
# Clean Docker cache
docker system prune -a

# Rebuild with no cache
docker-compose build --no-cache

# Check Docker logs
docker-compose logs app
```

#### 2. Service Communication

**Error:** `Service unavailable` between containers

**Solution:**
```bash
# Check network connectivity
docker-compose exec app ping supabase

# Verify service names in docker-compose.yml
# Check port mappings
docker-compose ps
```

## Monitoring and Debugging

### Enable Debug Logging

```bash
# Set environment variables
export LOG_LEVEL=DEBUG
export STREAMLIT_LOGGER_LEVEL=debug

# Run with verbose logging
streamlit run src/ui/streamlit_app.py --logger.level debug
```

### Performance Monitoring

```bash
# Check metrics endpoint
curl http://localhost:8058/metrics

# Monitor system resources
htop
iotop
```

### Debug Tools

```python
# Add debugging to your code
from src.utils.monitoring import logger

logger.debug("Debug message", extra_data="value")
logger.info("Info message", user_id="123")
logger.error("Error occurred", error=str(e))
```

## Getting Help

### Log Collection

```bash
# Collect system information
python -c "
import sys, platform, pkg_resources
print(f'Python: {sys.version}')
print(f'Platform: {platform.platform()}')
print('Packages:')
for pkg in pkg_resources.working_set:
    if pkg.project_name in ['streamlit', 'pydantic-ai', 'supabase']:
        print(f'  {pkg.project_name}: {pkg.version}')
"

# Collect logs
journalctl -u your-service --since "1 hour ago" > system.log
docker-compose logs > docker.log
```

### Health Check Report

```bash
# Generate comprehensive health report
curl http://localhost:8058/health/detailed > health_report.json

# Check all components
for component in database llm embedding memory web_search; do
    echo "=== $component ==="
    curl http://localhost:8058/health/components/$component
    echo
done
```

### Support Information

When reporting issues, please include:

1. **System Information:**
   - Operating system and version
   - Python version
   - Package versions

2. **Configuration:**
   - Environment variables (sanitized)
   - Configuration files
   - Docker setup (if applicable)

3. **Error Details:**
   - Full error messages
   - Stack traces
   - Steps to reproduce

4. **Logs:**
   - Application logs
   - System logs
   - Health check results

5. **Context:**
   - What you were trying to do
   - Expected vs actual behavior
   - Recent changes to the system
