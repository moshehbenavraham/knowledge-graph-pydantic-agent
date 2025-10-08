# Agentic RAG System with Knowledge Graph - Lean Architecture

## Executive Summary

This document outlines the plan for building an advanced Agentic RAG system that enhances the existing Supabase/pgvector infrastructure with a lightweight Neo4j knowledge graph layer. The key innovation is treating Neo4j as a **knowledge index** rather than a document store, eliminating redundancy while providing powerful graph-based reasoning capabilities.

## Implementation Status

### Phase 1: Database Infrastructure ✅ FULLY COMPLETED (2024-12-25)
- ✅ Enhanced PostgreSQL schema with multi-model embedding support
- ✅ Connection management with pooling and circuit breakers
- ✅ Configuration system with comprehensive settings
- ✅ Migration system with version tracking and rollback
- ✅ Zero content duplication architecture implemented
- ✅ PostgreSQL and Neo4j store operations
- ✅ Graphiti client wrapper for knowledge extraction
- ✅ Database initialization scripts (bash and Python)
- ✅ Comprehensive test suite with performance benchmarks

### Phase 2: Core Components ✅ FULLY COMPLETED (2024-12-25)
- ✅ Ingestion pipeline with semantic/simple chunking
- ✅ Knowledge extraction (entities, relationships, facts)
- ✅ Vector, graph, and hybrid search implementation
- ✅ Intent analysis and result ranking
- ✅ Comprehensive caching and optimization
- ✅ Full test coverage with performance benchmarks

### Phase 3: Agent Intelligence ✅ FULLY COMPLETED
- ✅ Pydantic AI agent with tool orchestration
- ✅ Intent analysis and query routing
- ✅ Response generation with citations
- ✅ Multi-strategy search coordination
- ✅ Confidence scoring and result ranking

### Phase 4-5: Pending
- ⏳ API & Performance optimization enhancements
- ⏳ Production deployment

### Additional Implementation Components
Beyond the core components documented in each phase, the implementation includes:

#### Enhanced Agent Components (`src/agentic_rag/agent/`)
- `config.py` - Agent-specific configuration management
- `providers.py` - LLM provider implementations
- `router.py` - Query routing and strategy selection

#### Legacy Integration (`EXAMPLE_agentic-rag-knowledge-graph/`)
- `agent/db_utils.py` - Database utility functions
- `agent/graph_utils.py` - Graph operations and utilities
- `agent/models.py` - Data model definitions
- `agent/providers.py` - Provider configurations
- `ingestion/graph_builder.py` - Knowledge graph construction
- `ingestion/ingest.py` - Document ingestion entry point

#### Testing
- `tests/test_rag.py` - Consolidated test suite covering all phases

## Core Architecture Principle

**PostgreSQL/Supabase = Content Storage | Neo4j/Graphiti = Knowledge Index**

- PostgreSQL remains the single source of truth for all document content
- Neo4j stores only extracted entities, relationships, and temporal facts
- No document content duplication between databases
- Cross-references maintain connectivity between systems

## System Architecture

### High-Level Design

```
┌────────────────────────────────────────────────────────────────────────┐
│                           User Interface Layer                          │
│  ┌────────────┐     ┌────────────┐     ┌────────────┐                │
│  │    CLI     │     │   Web UI   │     │    API     │                │
│  └──────┬─────┘     └──────┬─────┘     └──────┬─────┘                │
│         └───────────────────┴───────────────────┘                      │
├────────────────────────────────────────────────────────────────────────┤
│                         Agent Orchestration                             │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │                    Pydantic AI Agent                          │     │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │     │
│  │  │ Query Intent │→ │ Tool Router  │→ │  Response    │      │     │
│  │  │   Analyzer   │  │              │  │  Generator   │      │     │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │     │
│  └──────────────────────────────────────────────────────────────┘     │
├────────────────────────────────────────────────────────────────────────┤
│                            Tool Layer                                   │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │  Vector Search  │  Graph Search  │  Hybrid Search  │ Timeline │     │
│  │       ↓              ↓                  ↓              ↓      │     │
│  │  PostgreSQL     Neo4j/Graphiti    Both Systems    Graphiti   │     │
│  └──────────────────────────────────────────────────────────────┘     │
├────────────────────────────────────────────────────────────────────────┤
│                         Storage Layer                                   │
│                                                                         │
│  PostgreSQL/Supabase                    Neo4j + Graphiti               │
│  ┌─────────────────────────┐           ┌─────────────────────────┐    │
│  │ Documents (Full Content)│           │ Entities (Name/Type)    │    │
│  │ Chunks (Text+Embeddings)│←─────────→│ Relationships           │    │
│  │ Sessions & Messages     │ Reference │ Episodes (Brief Facts)  │    │
│  │ Vector Index (pgvector) │   IDs     │ Temporal Properties     │    │
│  └─────────────────────────┘           └─────────────────────────┘    │
│         Source of Truth                    Knowledge Index             │
└────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Document Ingestion:
─────────────────
Document → Chunk → Embed → Store in PostgreSQL
            ↓
      Extract Knowledge
            ↓
    ┌───────┴────────┐
    ↓                ↓
Entities          Facts
(names only)    (summaries)
    ↓                ↓
    └───────┬────────┘
            ↓
     Store in Neo4j
     (with chunk_id references)

Query Processing:
────────────────
User Query → Intent Analysis → Tool Selection
                                      ↓
                    ┌─────────────────┼─────────────────┐
                    ↓                 ↓                 ↓
            Vector Search      Graph Search      Hybrid Search
            (PostgreSQL)         (Neo4j)           (Both)
                    ↓                 ↓                 ↓
                    └─────────────────┼─────────────────┘
                                      ↓
                              Result Merging
                                      ↓
                              Response Generation
```

## Implementation Plan

### Phase 1: Database Infrastructure (Days 1-3)

#### 1.1 PostgreSQL/Supabase Schema Enhancement

```sql
-- Existing tables remain unchanged
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536), -- Or 768 for different models
    chunk_index INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}', -- Will include entity_refs
    token_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- New index for entity references
CREATE INDEX idx_chunks_entity_refs ON chunks
    USING GIN ((metadata->'entity_refs'));

-- Enhanced search function
CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding vector(1536),
    query_text TEXT,
    entity_ids TEXT[] DEFAULT NULL,
    match_count INT DEFAULT 10
) RETURNS TABLE (
    chunk_id UUID,
    content TEXT,
    similarity FLOAT,
    entity_boost FLOAT,
    final_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.content,
        1 - (c.embedding <=> query_embedding) AS similarity,
        CASE
            WHEN entity_ids IS NOT NULL AND
                 c.metadata->'entity_refs' ?| entity_ids
            THEN 0.2
            ELSE 0.0
        END AS entity_boost,
        (1 - (c.embedding <=> query_embedding)) +
        CASE
            WHEN entity_ids IS NOT NULL AND
                 c.metadata->'entity_refs' ?| entity_ids
            THEN 0.2
            ELSE 0.0
        END AS final_score
    FROM chunks c
    ORDER BY final_score DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;
```

#### 1.2 Neo4j Schema Design

```cypher
// Lightweight entity nodes (no content)
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
    FOR (e:Entity) REQUIRE e.id IS UNIQUE;

// Entity structure
(:Entity {
    id: STRING,           // UUID
    name: STRING,         // Entity name
    type: STRING,         // company|person|technology|product
    first_seen: DATETIME,
    last_updated: DATETIME,
    chunk_refs: [STRING]  // References to PostgreSQL chunks
})

// Relationship structure
[:RELATED_TO {
    type: STRING,         // WORKS_AT|FOUNDED|USES|COMPETES_WITH
    confidence: FLOAT,
    valid_from: DATETIME,
    valid_to: DATETIME,
    source_chunks: [STRING]
}]

// Graphiti Episodes (temporal facts)
(:Episode {
    id: STRING,
    fact: STRING,         // Brief fact, max 500 chars
    timestamp: DATETIME,
    source_chunk: STRING, // Single chunk reference
    entities: [STRING]    // Entity IDs involved
})

// Indexes for performance
CREATE INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX episode_timestamp_index IF NOT EXISTS FOR (ep:Episode) ON (ep.timestamp);
```

### Phase 2: Core Components (Days 4-6)

#### 2.1 Project Structure

```
base_agent/
├── src/
│   ├── agentic_rag/
│   │   ├── __init__.py
│   │   ├── config.py                 # Configuration management
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py             # Pydantic AI agent
│   │   │   ├── tools.py             # Tool implementations
│   │   │   ├── prompts.py           # System prompts
│   │   │   └── intent_analyzer.py   # Query intent analysis
│   │   ├── ingestion/
│   │   │   ├── __init__.py
│   │   │   ├── pipeline.py          # Main pipeline
│   │   │   ├── chunker.py           # Document chunking
│   │   │   ├── embedder.py          # Embedding generation
│   │   │   └── knowledge_extractor.py # Entity/fact extraction
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   ├── postgres_store.py    # PostgreSQL operations
│   │   │   ├── neo4j_store.py       # Neo4j operations
│   │   │   └── graphiti_client.py   # Graphiti wrapper
│   │   ├── search/
│   │   │   ├── __init__.py
│   │   │   ├── vector_search.py     # pgvector search
│   │   │   ├── graph_search.py      # Neo4j queries
│   │   │   ├── hybrid_search.py     # Combined search
│   │   │   └── ranker.py            # Result ranking
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── app.py               # FastAPI app
│   │       ├── endpoints.py         # API endpoints
│   │       └── streaming.py         # SSE support
├── sql/
│   └── agentic_rag/
│       └── schema.sql               # PostgreSQL schema
└── tests/
    └── agentic_rag/
        ├── test_ingestion.py
        ├── test_search.py
        └── test_agent.py
```

#### 2.2 Ingestion Pipeline

```python
# src/agentic_rag/ingestion/pipeline.py
class IngestionPipeline:
    def __init__(self):
        self.chunker = SemanticChunker()
        self.embedder = EmbeddingGenerator()
        self.extractor = KnowledgeExtractor()
        self.pg_store = PostgresStore()
        self.graph_store = GraphitiClient()

    async def ingest_document(self,
                             content: str,
                             title: str,
                             source: str) -> IngestionResult:
        """
        Ingest document with knowledge extraction.
        No content duplication - Neo4j only gets facts.
        """
        # Step 1: Chunk document
        chunks = await self.chunker.chunk(content, {
            'title': title,
            'source': source
        })

        # Step 2: Generate embeddings
        for chunk in chunks:
            chunk.embedding = await self.embedder.embed(chunk.content)

        # Step 3: Store in PostgreSQL (full content + embeddings)
        doc_id = await self.pg_store.store_document(title, source, content)
        chunk_ids = await self.pg_store.store_chunks(doc_id, chunks)

        # Step 4: Extract knowledge (no content duplication)
        for chunk, chunk_id in zip(chunks, chunk_ids):
            # Extract entities (just names and types)
            entities = await self.extractor.extract_entities(chunk.content)

            # Extract facts (brief summaries, not full text)
            facts = await self.extractor.extract_facts(
                chunk.content,
                max_length=500  # Limit fact length
            )

            # Store in Neo4j with back-references
            entity_ids = await self.graph_store.add_entities(
                entities,
                source_chunk_id=chunk_id
            )

            await self.graph_store.add_episodes(
                facts,
                entity_ids=entity_ids,
                source_chunk_id=chunk_id
            )

            # Update PostgreSQL with entity references
            await self.pg_store.update_chunk_metadata(
                chunk_id,
                {'entity_refs': entity_ids}
            )

        return IngestionResult(
            document_id=doc_id,
            chunks_created=len(chunks),
            entities_extracted=len(entities),
            facts_extracted=len(facts)
        )
```

#### 2.3 Knowledge Extraction

```python
# src/agentic_rag/ingestion/knowledge_extractor.py
class KnowledgeExtractor:
    """Extract entities and facts without storing content."""

    async def extract_entities(self, text: str) -> List[Entity]:
        """Extract entity names and types only."""
        prompt = """
        Extract entities from this text.
        Return ONLY the entity name and type.
        Do NOT include descriptions or content.

        Types: company, person, technology, product

        Format: {"name": "...", "type": "..."}
        """

        response = await self.llm.extract(prompt, text)
        return [Entity(name=e['name'], type=e['type'])
                for e in response]

    async def extract_facts(self, text: str, max_length: int = 500) -> List[str]:
        """Extract brief facts, not full content."""
        prompt = f"""
        Extract 3-5 key facts from this text.
        Each fact must be:
        - Self-contained
        - Under {max_length} characters
        - A statement, not a full paragraph

        Example: "Microsoft invested $10B in OpenAI in January 2023"
        """

        facts = await self.llm.extract(prompt, text)
        return [f[:max_length] for f in facts]  # Enforce length limit
```

### Phase 3: Search Implementation (Days 7-9)

#### 3.1 Vector Search (PostgreSQL Only)

```python
# src/agentic_rag/search/vector_search.py
class VectorSearch:
    """Pure vector search using pgvector."""

    async def search(self,
                    query: str,
                    limit: int = 10) -> List[ChunkResult]:
        """
        Search PostgreSQL for similar chunks.
        No Neo4j involvement.
        """
        # Generate query embedding
        embedding = await self.embedder.embed(query)

        # Search PostgreSQL only
        results = await self.pg_store.search_similar(
            embedding=embedding,
            limit=limit
        )

        return [
            ChunkResult(
                chunk_id=r['id'],
                content=r['content'],
                score=r['similarity'],
                metadata=r['metadata']
            )
            for r in results
        ]
```

#### 3.2 Graph Search (Neo4j Only)

```python
# src/agentic_rag/search/graph_search.py
class GraphSearch:
    """Graph search for facts and relationships."""

    async def search(self, query: str) -> GraphSearchResult:
        """
        Search Neo4j for facts and relationships.
        Returns facts and chunk references, not content.
        """
        # Search for relevant facts
        facts = await self.graphiti.search(query)

        # Extract entities and relationships
        entities = await self.extract_entities_from_facts(facts)
        relationships = await self.get_relationships(entities)

        # Return structured result with chunk references
        return GraphSearchResult(
            facts=[{
                'fact': f.fact,
                'timestamp': f.timestamp,
                'source_chunk': f.source_chunk  # Reference only
            } for f in facts],
            entities=entities,
            relationships=relationships,
            chunk_refs=list(set(f.source_chunk for f in facts))
        )
```

#### 3.3 Hybrid Search (Intelligent Combination)

```python
# src/agentic_rag/search/hybrid_search.py
class HybridSearch:
    """Combines vector and graph search intelligently."""

    async def search(self,
                    query: str,
                    limit: int = 10) -> HybridSearchResult:
        """
        Parallel search with intelligent merging.
        Graph provides context for boosting vector results.
        """
        # Parallel execution
        vector_task = self.vector_search.search(query, limit * 2)
        graph_task = self.graph_search.search(query)

        vector_results, graph_results = await asyncio.gather(
            vector_task,
            graph_task
        )

        # Use graph results to boost relevant chunks
        boosted_results = await self.boost_with_graph_context(
            vector_results,
            graph_results.chunk_refs,
            graph_results.entities
        )

        # Combine and rank
        final_results = self.ranker.rank(
            chunks=boosted_results[:limit],
            facts=graph_results.facts,
            relationships=graph_results.relationships
        )

        return HybridSearchResult(
            chunks=final_results.chunks,
            facts=final_results.facts,
            relationships=final_results.relationships,
            search_strategy="hybrid"
        )

    async def boost_with_graph_context(self,
                                      vector_results: List[ChunkResult],
                                      relevant_chunk_ids: List[str],
                                      entities: List[str]) -> List[ChunkResult]:
        """Boost chunks that appear in graph results."""
        for result in vector_results:
            # Boost if chunk is referenced in graph
            if result.chunk_id in relevant_chunk_ids:
                result.score *= 1.3

            # Additional boost for entity matches
            chunk_entities = result.metadata.get('entity_refs', [])
            if any(e in entities for e in chunk_entities):
                result.score *= 1.2

        return sorted(vector_results, key=lambda x: x.score, reverse=True)
```

### Phase 4: Agent Intelligence (Days 10-11)

#### 4.1 Intent Analysis

```python
# src/agentic_rag/agent/intent_analyzer.py
class IntentAnalyzer:
    """Analyze query to determine optimal search strategy."""

    def analyze(self, query: str) -> SearchIntent:
        """Determine the best search strategy."""

        # Relationship indicators
        relationship_keywords = [
            'related', 'connected', 'relationship',
            'works with', 'founded', 'acquired',
            'partnership', 'competitor'
        ]

        # Temporal indicators
        temporal_keywords = [
            'timeline', 'history', 'evolution',
            'changed', 'when', 'progression'
        ]

        # Fact-seeking indicators
        fact_keywords = [
            'fact', 'specifically', 'exactly',
            'precise', 'detail about'
        ]

        query_lower = query.lower()

        # Determine intent
        has_relationship = any(kw in query_lower for kw in relationship_keywords)
        has_temporal = any(kw in query_lower for kw in temporal_keywords)
        has_fact = any(kw in query_lower for kw in fact_keywords)

        if has_relationship or has_temporal:
            return SearchIntent.GRAPH_HEAVY
        elif has_fact:
            return SearchIntent.HYBRID
        else:
            return SearchIntent.VECTOR_HEAVY
```

#### 4.2 Agent Configuration

```python
# src/agentic_rag/agent/agent.py
from pydantic_ai import Agent, RunContext

class AgentDependencies:
    def __init__(self):
        self.intent_analyzer = IntentAnalyzer()
        self.vector_search = VectorSearch()
        self.graph_search = GraphSearch()
        self.hybrid_search = HybridSearch()

SYSTEM_PROMPT = """
You are an advanced RAG agent with specialized search capabilities.

Search Strategy:
- vector_search: For content discovery and semantic similarity
  Returns: Actual document chunks from PostgreSQL

- graph_search: For facts, relationships, and entity connections
  Returns: Extracted facts and relationships (not full documents)

- hybrid_search: For comprehensive understanding
  Returns: Document chunks + facts + relationships

The graph contains knowledge extracted from documents, not the documents themselves.
Always cite sources and indicate confidence levels.
"""

rag_agent = Agent(
    model=get_llm_model(),
    deps_type=AgentDependencies,
    system_prompt=SYSTEM_PROMPT
)

@rag_agent.tool
async def smart_search(ctx: RunContext[AgentDependencies],
                       query: str) -> dict:
    """Intelligently route to appropriate search."""
    intent = ctx.deps.intent_analyzer.analyze(query)

    if intent == SearchIntent.VECTOR_HEAVY:
        results = await ctx.deps.vector_search.search(query)
        return {"type": "vector", "results": results}

    elif intent == SearchIntent.GRAPH_HEAVY:
        results = await ctx.deps.graph_search.search(query)
        # Optionally fetch content for source chunks
        if results.chunk_refs:
            chunks = await ctx.deps.vector_search.get_chunks(
                results.chunk_refs[:5]
            )
            results.source_chunks = chunks
        return {"type": "graph", "results": results}

    else:  # HYBRID
        results = await ctx.deps.hybrid_search.search(query)
        return {"type": "hybrid", "results": results}
```

### Phase 5: API & Performance (Days 12-14)

#### 5.1 FastAPI Implementation

```python
# src/agentic_rag/api/app.py
from fastapi import FastAPI, HTTPException
from sse_starlette.sse import EventSourceResponse

app = FastAPI(title="Agentic RAG API")

@app.post("/ingest")
async def ingest_document(request: IngestRequest):
    """Ingest document into both stores."""
    pipeline = IngestionPipeline()

    try:
        result = await pipeline.ingest_document(
            content=request.content,
            title=request.title,
            source=request.source
        )

        return {
            "status": "success",
            "document_id": result.document_id,
            "chunks": result.chunks_created,
            "entities": result.entities_extracted,
            "facts": result.facts_extracted
        }
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat with the agent."""
    result = await rag_agent.run(request.message)

    return {
        "response": result.data,
        "search_type": result.metadata.get("search_type"),
        "sources": result.metadata.get("sources", [])
    }

@app.get("/search/{mode}")
async def search(mode: str, q: str, limit: int = 10):
    """Direct search access."""
    if mode == "vector":
        search_engine = VectorSearch()
    elif mode == "graph":
        search_engine = GraphSearch()
    elif mode == "hybrid":
        search_engine = HybridSearch()
    else:
        raise HTTPException(status_code=400, detail="Invalid search mode")

    results = await search_engine.search(q, limit)
    return results

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream responses with SSE."""
    async def generate():
        async with rag_agent.run_stream(request.message) as stream:
            async for chunk in stream:
                if chunk.type == "tool_use":
                    yield {
                        "event": "tool",
                        "data": json.dumps({
                            "tool": chunk.tool_name,
                            "args": chunk.tool_args
                        })
                    }
                elif chunk.type == "content":
                    yield {
                        "event": "content",
                        "data": json.dumps({"text": chunk.text})
                    }

    return EventSourceResponse(generate())
```

#### 5.2 Performance Optimization

```python
# src/agentic_rag/config.py
from functools import lru_cache
from cachetools import TTLCache
import asyncio

class PerformanceConfig:
    # Caching
    EMBEDDING_CACHE_SIZE = 1000
    EMBEDDING_CACHE_TTL = 3600  # 1 hour

    GRAPH_CACHE_SIZE = 500
    GRAPH_CACHE_TTL = 1800  # 30 minutes

    # Batching
    EMBEDDING_BATCH_SIZE = 100
    GRAPH_BATCH_SIZE = 10

    # Connection pools
    PG_POOL_MIN = 5
    PG_POOL_MAX = 20
    NEO4J_MAX_CONNECTIONS = 10

    # Timeouts
    VECTOR_SEARCH_TIMEOUT = 2.0
    GRAPH_SEARCH_TIMEOUT = 3.0

    # Feature flags
    ENABLE_GRAPH = True
    ENABLE_CACHING = True
    ENABLE_PARALLEL_SEARCH = True

class OptimizedSearch:
    def __init__(self):
        self.embedding_cache = TTLCache(
            maxsize=PerformanceConfig.EMBEDDING_CACHE_SIZE,
            ttl=PerformanceConfig.EMBEDDING_CACHE_TTL
        )
        self.graph_cache = TTLCache(
            maxsize=PerformanceConfig.GRAPH_CACHE_SIZE,
            ttl=PerformanceConfig.GRAPH_CACHE_TTL
        )

    async def cached_embed(self, text: str) -> List[float]:
        """Cache embeddings to avoid recomputation."""
        cache_key = hashlib.md5(text.encode()).hexdigest()

        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]

        embedding = await self.embedder.embed(text)
        self.embedding_cache[cache_key] = embedding
        return embedding

    async def parallel_search(self, query: str) -> dict:
        """Execute searches in parallel with timeout."""
        tasks = []

        # Vector search task
        tasks.append(
            asyncio.create_task(
                asyncio.wait_for(
                    self.vector_search(query),
                    timeout=PerformanceConfig.VECTOR_SEARCH_TIMEOUT
                )
            )
        )

        # Graph search task (if enabled)
        if PerformanceConfig.ENABLE_GRAPH:
            tasks.append(
                asyncio.create_task(
                    asyncio.wait_for(
                        self.graph_search(query),
                        timeout=PerformanceConfig.GRAPH_SEARCH_TIMEOUT
                    )
                )
            )

        # Wait for all with graceful timeout handling
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return self.merge_results(results)
```

## Configuration

### Environment Variables

```bash
# .env configuration

# === Existing Supabase Configuration ===
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key

# === Neo4j Configuration (New) ===
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# === LLM Configuration ===
LLM_PROVIDER=openai  # openai|ollama|openrouter|gemini
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-key
LLM_MODEL=gpt-4o-mini

# === Embedding Configuration ===
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536  # 768 for nomic-embed-text

# === Performance Settings ===
ENABLE_GRAPH=true  # Can disable for vector-only mode
ENABLE_CACHING=true
PARALLEL_SEARCH=true
BATCH_SIZE=10
MAX_WORKERS=4

# === Ingestion Settings ===
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_ENTITIES_PER_CHUNK=10
MAX_FACT_LENGTH=500
EXTRACTION_MODEL=gpt-4o-mini  # Smaller model for extraction

# === API Settings ===
API_PORT=8058
API_HOST=0.0.0.0
CORS_ORIGINS=["http://localhost:3000"]
```

### Installation & Setup

```bash
# 1. Clone and setup
cd base_agent
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 2. Install dependencies
pip install -r requirements.txt
pip install neo4j graphiti-core pydantic-ai

# 3. Setup PostgreSQL schema
psql $SUPABASE_URL < sql/agentic_rag/schema.sql

# 4. Setup Neo4j
# Option A: Local Neo4j
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# Option B: Neo4j Aura (cloud)
# Get connection details from console

# 5. Initialize knowledge graph
python -m agentic_rag.storage.graphiti_client init

# 6. Run ingestion (optional - with existing documents)
python -m agentic_rag.ingestion.pipeline \
  --input documents/ \
  --batch-size 10

# 7. Start API server
uvicorn agentic_rag.api.app:app --reload --port 8058

# 8. Test the system
curl -X POST http://localhost:8058/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the relationship between Microsoft and OpenAI?"}'
```

## Storage Analysis

### Storage Comparison

| Component | PostgreSQL | Neo4j | Savings |
|-----------|------------|-------|---------|
| Document (10MB) | 10MB | 0 | 100% |
| Chunks (1000) | 2MB | 0 | 100% |
| Embeddings | 6MB | 0 | 100% |
| Entities | 0 | 10KB | - |
| Relationships | 0 | 20KB | - |
| Facts/Episodes | 0 | 50KB | - |
| **Total** | **18MB** | **80KB** | **99.6%** |

### Query Performance

| Query Type | PostgreSQL | Neo4j | Combined |
|------------|------------|-------|----------|
| Vector Search | 150ms | - | 150ms |
| Entity Lookup | - | 50ms | 50ms |
| Relationship Traversal | - | 100ms | 100ms |
| Hybrid Search | 150ms | 100ms | 200ms (parallel) |
| Temporal Query | - | 150ms | 150ms |

## Monitoring & Observability

### Key Metrics

```python
# src/agentic_rag/monitoring.py
from prometheus_client import Counter, Histogram, Gauge

# Search metrics
search_latency = Histogram(
    'search_latency_seconds',
    'Search latency by type',
    ['search_type']
)

search_requests = Counter(
    'search_requests_total',
    'Total search requests',
    ['search_type', 'status']
)

# Ingestion metrics
documents_ingested = Counter(
    'documents_ingested_total',
    'Total documents ingested'
)

entities_extracted = Counter(
    'entities_extracted_total',
    'Total entities extracted',
    ['entity_type']
)

# Cache metrics
cache_hits = Counter(
    'cache_hits_total',
    'Cache hit count',
    ['cache_type']
)

# System metrics
active_connections = Gauge(
    'active_connections',
    'Active database connections',
    ['database']
)
```

### Logging Strategy

```python
import structlog

logger = structlog.get_logger()

# Structured logging with correlation IDs
logger.info(
    "search_completed",
    search_id=search_id,
    query=query,
    search_type=search_type,
    latency_ms=latency,
    results_count=len(results),
    cache_hit=cache_hit
)
```

## Testing Strategy

### Test Coverage

```python
# tests/agentic_rag/test_integration.py
import pytest
from agentic_rag import IngestionPipeline, AgentSearch

class TestAgenticRAG:
    @pytest.mark.asyncio
    async def test_no_content_duplication(self):
        """Verify Neo4j doesn't store document content."""
        # Ingest document
        pipeline = IngestionPipeline()
        result = await pipeline.ingest_document(
            content="Test document content",
            title="Test",
            source="test.md"
        )

        # Check PostgreSQL has content
        pg_chunks = await postgres.get_chunks(result.document_id)
        assert all(chunk.content for chunk in pg_chunks)

        # Check Neo4j only has facts
        neo4j_facts = await neo4j.get_facts(result.document_id)
        assert all(len(fact.fact) < 500 for fact in neo4j_facts)
        assert not any("Test document content" in fact.fact
                      for fact in neo4j_facts)

    @pytest.mark.asyncio
    async def test_search_performance(self):
        """Test search meets performance targets."""
        search = AgentSearch()

        # Vector search < 200ms
        start = time.time()
        await search.vector_search("test query")
        assert (time.time() - start) < 0.2

        # Graph search < 500ms
        start = time.time()
        await search.graph_search("relationship query")
        assert (time.time() - start) < 0.5

    @pytest.mark.asyncio
    async def test_intelligent_routing(self):
        """Test agent routes queries correctly."""
        agent = rag_agent

        # Semantic query → vector search
        result = await agent.run("What does the document say about AI?")
        assert result.metadata['search_type'] == 'vector'

        # Relationship query → graph search
        result = await agent.run("How is Microsoft related to OpenAI?")
        assert result.metadata['search_type'] in ['graph', 'hybrid']
```

## Migration Path

### Phased Rollout

1. **Phase 1: Vector-Only Mode**
   - Deploy with `ENABLE_GRAPH=false`
   - Existing Supabase functionality unchanged
   - Test and validate base system

2. **Phase 2: Graph Infrastructure**
   - Set up Neo4j instance
   - Enable graph ingestion for new documents
   - Keep graph search disabled

3. **Phase 3: Hybrid Search**
   - Enable `ENABLE_GRAPH=true`
   - Backfill existing documents gradually
   - Monitor performance and costs

4. **Phase 4: Full Production**
   - Enable all features
   - Optimize based on usage patterns
   - Scale infrastructure as needed

## Risk Mitigation

### Technical Risks

| Risk | Mitigation |
|------|------------|
| Neo4j complexity | Start with simple queries, optimize gradually |
| Ingestion speed | Batch processing, parallel execution, optional graph |
| Cache invalidation | TTL-based caching, manual invalidation endpoints |
| Graph query performance | Query optimization, result limiting, caching |

### Operational Risks

| Risk | Mitigation |
|------|------------|
| Neo4j downtime | Fallback to vector-only mode |
| Cost scaling | Monitor usage, implement quotas |
| Data consistency | Transaction support, validation checks |
| Version compatibility | Comprehensive testing, gradual updates |

## Success Criteria

### Technical Metrics
- ✅ No content duplication between databases
- ✅ Vector search latency < 200ms
- ✅ Graph search latency < 500ms
- ✅ Storage overhead < 1% for graph layer
- ✅ 90%+ cache hit rate for common queries

### Business Metrics
- ✅ Improved answer quality vs pure vector search
- ✅ Successful relationship discovery
- ✅ Temporal reasoning capability
- ✅ Source attribution for all responses
- ✅ Reduced hallucinations through fact validation

## Conclusion

This lean architecture provides the benefits of knowledge graphs without the overhead of content duplication. By treating Neo4j as a knowledge index rather than a document store, we achieve:

1. **Efficiency**: 99%+ storage savings in Neo4j
2. **Performance**: Fast searches with intelligent routing
3. **Flexibility**: Can disable graph for pure vector search
4. **Scalability**: Each database handles what it does best
5. **Maintainability**: Clear separation of concerns

The system enhances the existing Supabase infrastructure without replacing it, providing a smooth migration path and the ability to fall back to vector-only search when needed.
