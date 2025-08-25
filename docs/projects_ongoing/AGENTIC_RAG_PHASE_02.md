# Phase 2: Core Components - Ingestion, Knowledge Extraction & Search (Days 4-6)

## Executive Summary

Phase 2 builds upon the robust database infrastructure established in Phase 1 to implement the core data processing pipeline. This phase focuses on document ingestion, intelligent chunking, knowledge extraction, and multi-modal search capabilities while maintaining the zero content duplication principle between PostgreSQL and Neo4j.

## Implementation Status: ✅ COMPLETED (2024-12-25)

### Phase 2 Components Overview

```
Document Ingestion Pipeline:
  Raw Document -> Chunking -> Embedding -> Knowledge Extraction
       |            |            |              |
  [Markdown]   [Semantic]    [Vectors]   [Entities/Facts]
                   or                           |
               [Simple]                 PostgreSQL + Neo4j

Search Architecture:
  User Query -> Intent Analysis -> Search Strategy Selection
       |              |                    |
  [Text Input]  [Classification]    [Vector/Graph/Hybrid]
                                           |
                                    Ranked Results
```

## Day 4: Ingestion Pipeline Development

### 4.1 Document Processing Pipeline

#### Main Pipeline Orchestrator (`src/agentic_rag/ingestion/pipeline.py`)

```python
class DocumentIngestionPipeline:
    """
    Orchestrates the complete document ingestion process.

    Key responsibilities:
    - Document discovery and reading
    - Chunking coordination
    - Embedding generation
    - Knowledge extraction
    - Dual-database storage
    - Error handling and recovery
    """

    def __init__(self, config: IngestionConfig):
        self.chunker = ChunkingStrategy(config)
        self.embedder = EmbeddingGenerator(config)
        self.extractor = KnowledgeExtractor(config)
        self.pg_store = PostgresStore()
        self.graph_store = GraphitiClient()

    async def ingest_document(self,
                             content: str,
                             title: str,
                             source: str,
                             metadata: dict) -> IngestionResult:
        """
        Main ingestion workflow:
        1. Chunk document based on strategy
        2. Generate embeddings for chunks
        3. Extract entities and facts
        4. Store in PostgreSQL
        5. Update knowledge graph
        6. Maintain cross-references
        """
        # Implementation with comprehensive error handling
        # Progress tracking and logging
        # Transaction management for consistency
```

### 4.2 Intelligent Document Chunking

#### Chunking System (`src/agentic_rag/ingestion/chunker.py`)

```python
@dataclass
class ChunkingConfig:
    chunk_size: int = 1000          # Target chunk size in characters
    chunk_overlap: int = 200        # Overlap between chunks
    max_chunk_size: int = 2000      # Maximum allowed chunk size
    min_chunk_size: int = 100       # Minimum viable chunk size
    use_semantic_splitting: bool = True
    preserve_structure: bool = True # Maintain markdown structure

class SemanticChunker:
    """
    LLM-powered semantic chunking for intelligent boundaries.

    Strategy:
    1. Identify structural boundaries (headers, sections)
    2. Use LLM to find semantic breakpoints
    3. Respect size constraints
    4. Maintain context overlap
    """

    async def chunk(self, content: str) -> List[DocumentChunk]:
        # Structural analysis
        sections = self._identify_sections(content)

        # Semantic boundary detection using LLM
        boundaries = await self._find_semantic_boundaries(sections)

        # Size optimization
        chunks = self._optimize_chunk_sizes(boundaries)

        return chunks

class SimpleChunker:
    """
    Rule-based chunking fallback.

    Strategy:
    1. Split on paragraph boundaries
    2. Respect sentence boundaries
    3. Maintain overlap
    4. Fast and deterministic
    """
```

**Chunking Strategy Decision Tree:**
```
Document Length > 2000 chars?
    ├─ Yes -> Semantic Chunking Available?
    │         ├─ Yes -> Use SemanticChunker
    │         └─ No -> Use SimpleChunker
    └─ No -> Single Chunk
```

### 4.3 Embedding Generation

#### Embedding System (`src/agentic_rag/ingestion/embedder.py`)

```python
class EmbeddingGenerator:
    """
    Multi-model embedding generation with caching.

    Supported models:
    - OpenAI text-embedding-3-small (1536 dims)
    - OpenAI text-embedding-3-large (3072 dims)
    - Nomic embed-text (768 dims)
    - Local models via Ollama
    """

    def __init__(self, config: EmbeddingConfig):
        self.model = config.embedding_model
        self.dimension = config.embedding_dimension
        self.batch_size = config.batch_size
        self.cache = EmbeddingCache()

    async def embed_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """
        Generate embeddings with:
        - Batch processing for efficiency
        - Caching to avoid recomputation
        - Retry logic for API failures
        - Progress tracking
        """
        # Check cache first
        uncached_chunks = self._filter_uncached(chunks)

        # Batch generation
        for batch in self._create_batches(uncached_chunks):
            embeddings = await self._generate_batch(batch)
            self._update_cache(batch, embeddings)

        return self._attach_embeddings(chunks)
```

**Embedding Performance Optimizations:**
- Batch size: 100 chunks per API call
- Cache hit target: >80% for repeated content
- Parallel processing for large documents
- Automatic fallback to smaller models on failure

## Day 5: Knowledge Extraction System

### 5.1 Entity Extraction

#### Knowledge Extractor (`src/agentic_rag/ingestion/knowledge_extractor.py`)

```python
class KnowledgeExtractor:
    """
    Extract structured knowledge without content duplication.

    Extraction targets:
    - Entities: Names and types only
    - Relationships: Connections between entities
    - Facts: Brief temporal statements (<500 chars)
    - Events: Significant occurrences
    """

    async def extract_entities(self, chunk: DocumentChunk) -> List[Entity]:
        """
        Entity extraction strategy:
        1. Use NER for initial candidates
        2. LLM validation and typing
        3. Confidence scoring
        4. Deduplication
        """
        prompt = """
        Extract entities from this text.
        Return ONLY entity names and types.
        Do NOT include descriptions or content.

        Types: company|person|technology|product|location|event

        Format: {"name": "...", "type": "...", "confidence": 0.0-1.0}
        """

        entities = await self.llm.extract(prompt, chunk.content)
        return self._validate_entities(entities)

    async def extract_facts(self, chunk: DocumentChunk,
                          entities: List[Entity]) -> List[Fact]:
        """
        Extract temporal facts:
        - Maximum 500 characters
        - Self-contained statements
        - Include temporal markers
        - Reference entities
        """
        prompt = f"""
        Extract 3-5 key facts from this text.
        Each fact must be:
        - Under 500 characters
        - A complete statement
        - Not a content excerpt

        Example: "Microsoft invested $10B in OpenAI in January 2023"
        """

        facts = await self.llm.extract(prompt, chunk.content)
        return self._validate_facts(facts, max_length=500)
```

### 5.2 Relationship Identification

```python
class RelationshipExtractor:
    """
    Identify relationships between entities.
    """

    RELATIONSHIP_TYPES = {
        'WORKS_AT': ['employed', 'works', 'joined'],
        'FOUNDED': ['founded', 'created', 'established'],
        'INVESTED_IN': ['invested', 'funded', 'backed'],
        'ACQUIRED': ['acquired', 'bought', 'purchased'],
        'PARTNERS_WITH': ['partnered', 'collaborated', 'allied'],
        'COMPETES_WITH': ['competes', 'rivals', 'versus']
    }

    async def extract_relationships(self,
                                   chunk: DocumentChunk,
                                   entities: List[Entity]) -> List[Relationship]:
        """
        Relationship extraction:
        1. Pattern matching for known types
        2. LLM validation for complex relationships
        3. Confidence scoring
        4. Temporal markers
        """
        relationships = []

        # Pattern-based extraction
        for pattern_type, keywords in self.RELATIONSHIP_TYPES.items():
            matches = self._find_pattern_matches(chunk.content, keywords, entities)
            relationships.extend(matches)

        # LLM-based extraction for complex cases
        if len(entities) > 1:
            llm_relationships = await self._llm_extract_relationships(chunk, entities)
            relationships.extend(llm_relationships)

        return self._deduplicate_relationships(relationships)
```

### 5.3 Graph Integration

```python
class GraphBuilder:
    """
    Build knowledge graph without content duplication.
    """

    async def add_to_graph(self,
                          chunks: List[DocumentChunk],
                          document_id: str) -> GraphBuildResult:
        """
        Graph construction:
        1. Create entity nodes (names only)
        2. Create relationships
        3. Add temporal episodes
        4. Maintain chunk references
        """

        # Batch entity creation
        entity_map = {}
        for chunk in chunks:
            for entity in chunk.entities:
                if entity.name not in entity_map:
                    node_id = await self.create_entity_node(
                        name=entity.name,
                        type=entity.type,
                        chunk_refs=[chunk.id]
                    )
                    entity_map[entity.name] = node_id

        # Create relationships
        for chunk in chunks:
            for rel in chunk.relationships:
                await self.create_relationship(
                    source=entity_map[rel.source],
                    target=entity_map[rel.target],
                    type=rel.type,
                    properties={
                        'confidence': rel.confidence,
                        'source_chunk': chunk.id
                    }
                )

        # Add temporal facts as episodes
        for chunk in chunks:
            for fact in chunk.facts:
                await self.graphiti.add_episode(
                    content=fact.text[:500],  # Enforce limit
                    timestamp=fact.timestamp,
                    entity_ids=[entity_map[e] for e in fact.entities],
                    source_id=chunk.id
                )
```

## Day 6: Search Implementation

### 6.1 Vector Search

#### Vector Search Component (`src/agentic_rag/search/vector_search.py`)

```python
class VectorSearch:
    """
    High-performance vector similarity search.

    Performance targets:
    - <200ms for 10k chunks
    - <100ms with caching
    """

    async def search(self,
                    query_embedding: List[float],
                    limit: int = 10,
                    filters: dict = None) -> List[ChunkResult]:
        """
        Optimized vector search:
        1. Check cache
        2. Use prepared statements
        3. Apply metadata filters
        4. Score and rank results
        """

        # Cache check
        cache_key = self._generate_cache_key(query_embedding, filters)
        if cached := await self.cache.get(cache_key):
            return cached

        # Optimized query with IVFFlat index
        query = """
        SELECT
            c.id,
            c.content,
            c.metadata,
            1 - (c.embedding_1536 <=> $1::vector) as similarity,
            d.title,
            d.source
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.embedding_1536 IS NOT NULL
            AND ($2::jsonb IS NULL OR c.metadata @> $2::jsonb)
        ORDER BY c.embedding_1536 <=> $1::vector
        LIMIT $3
        """

        results = await self.pg_conn.fetch(query, query_embedding, filters, limit)

        # Cache results
        await self.cache.set(cache_key, results, ttl=3600)

        return self._format_results(results)
```

### 6.2 Graph Search

#### Graph Search Component (`src/agentic_rag/search/graph_search.py`)

```python
class GraphSearch:
    """
    Knowledge graph search for facts and relationships.

    Performance targets:
    - <500ms for complex traversals
    - <200ms for direct lookups
    """

    async def search(self, query: str) -> GraphSearchResult:
        """
        Multi-strategy graph search:
        1. Full-text search on facts
        2. Entity name matching
        3. Relationship traversal
        4. Temporal filtering
        """

        # Parallel search strategies
        results = await asyncio.gather(
            self._search_facts(query),
            self._search_entities(query),
            self._search_relationships(query),
            return_exceptions=True
        )

        # Combine and rank
        return GraphSearchResult(
            facts=results[0] if not isinstance(results[0], Exception) else [],
            entities=results[1] if not isinstance(results[1], Exception) else [],
            relationships=results[2] if not isinstance(results[2], Exception) else [],
            chunk_refs=self._extract_chunk_refs(results)
        )

    async def _search_facts(self, query: str) -> List[Fact]:
        """
        Search facts using Graphiti.
        """
        cypher = """
        MATCH (e:Episode)
        WHERE e.fact CONTAINS $query
        RETURN e.fact as fact,
               e.timestamp as timestamp,
               e.source_chunk as chunk_id,
               e.confidence as confidence
        ORDER BY e.timestamp DESC
        LIMIT 20
        """
        return await self.neo4j.run(cypher, query=query)
```

### 6.3 Hybrid Search

#### Hybrid Search Orchestrator (`src/agentic_rag/search/hybrid_search.py`)

```python
class HybridSearch:
    """
    Intelligent combination of vector and graph search.
    """

    def __init__(self):
        self.vector_search = VectorSearch()
        self.graph_search = GraphSearch()
        self.intent_analyzer = IntentAnalyzer()
        self.ranker = ResultRanker()

    async def search(self, query: str, limit: int = 10) -> HybridSearchResult:
        """
        Hybrid search workflow:
        1. Analyze query intent
        2. Determine search strategy
        3. Execute parallel searches
        4. Merge and rank results
        """

        # Intent analysis
        intent = self.intent_analyzer.analyze(query)

        # Strategy selection
        strategy = self._select_strategy(intent)

        if strategy == SearchStrategy.VECTOR_ONLY:
            vector_results = await self.vector_search.search(query, limit)
            return HybridSearchResult(chunks=vector_results)

        elif strategy == SearchStrategy.GRAPH_ONLY:
            graph_results = await self.graph_search.search(query)
            return HybridSearchResult(facts=graph_results.facts)

        else:  # HYBRID
            # Parallel execution
            vector_task = self.vector_search.search(query, limit * 2)
            graph_task = self.graph_search.search(query)

            vector_results, graph_results = await asyncio.gather(
                vector_task, graph_task
            )

            # Intelligent merging
            merged = await self._merge_results(
                vector_results,
                graph_results,
                intent
            )

            # Final ranking
            ranked = self.ranker.rank(merged, limit)

            return HybridSearchResult(
                chunks=ranked.chunks,
                facts=ranked.facts,
                relationships=ranked.relationships,
                strategy=strategy
            )
```

### 6.4 Result Ranking

#### Ranking System (`src/agentic_rag/search/ranker.py`)

```python
class ResultRanker:
    """
    Multi-factor result ranking system.
    """

    def rank(self, results: SearchResults, limit: int) -> RankedResults:
        """
        Ranking factors:
        1. Semantic similarity (40%)
        2. Entity overlap (20%)
        3. Temporal relevance (20%)
        4. Source authority (10%)
        5. Result diversity (10%)
        """

        scored_results = []

        for result in results.chunks:
            score = self._calculate_score(
                result,
                factors={
                    'similarity': result.similarity * 0.4,
                    'entity_overlap': self._entity_score(result) * 0.2,
                    'recency': self._recency_score(result) * 0.2,
                    'authority': self._authority_score(result) * 0.1,
                    'diversity': self._diversity_score(result, scored_results) * 0.1
                }
            )
            scored_results.append((score, result))

        # Sort and limit
        scored_results.sort(key=lambda x: x[0], reverse=True)

        return RankedResults(
            chunks=[r[1] for r in scored_results[:limit]],
            facts=results.facts[:10],  # Limit facts
            relationships=results.relationships[:10]
        )
```

## Testing Strategy

### Testing

Tests are consolidated in `tests/test_rag.py` which includes:

- **Unit Tests**:
  - Semantic and simple chunking strategies
  - Entity and knowledge extraction
  - Vector and graph search performance
  - Confidence scoring and ranking

- **Integration Tests**:
  - End-to-end document ingestion pipeline
  - Dual-write consistency between PostgreSQL and Neo4j
  - Error recovery and resilience
  - Batch processing capabilities

- **Performance Tests**:
  - Vector search latency (<200ms target)
  - Graph search latency (<500ms target)
  - Hybrid search latency (<300ms average)
  - Concurrent search capacity

## Configuration

### Environment Variables

```bash
# ===== Ingestion Configuration =====
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_CHUNK_SIZE=2000
MIN_CHUNK_SIZE=100
USE_SEMANTIC_CHUNKING=true
SEMANTIC_CHUNKING_MODEL=gpt-4o-mini

# ===== Embedding Configuration =====
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
EMBEDDING_BATCH_SIZE=100
ENABLE_EMBEDDING_CACHE=true

# ===== Extraction Configuration =====
EXTRACT_ENTITIES=true
EXTRACT_RELATIONSHIPS=true
EXTRACT_FACTS=true
MAX_ENTITIES_PER_CHUNK=10
MAX_FACTS_PER_CHUNK=5
EXTRACTION_CONFIDENCE_THRESHOLD=0.7
EXTRACTION_MODEL=gpt-4o-mini

# ===== Search Configuration =====
DEFAULT_SEARCH_LIMIT=10
VECTOR_SEARCH_THRESHOLD=0.7
ENABLE_SEARCH_CACHE=true
SEARCH_CACHE_TTL=3600
PARALLEL_SEARCH_TIMEOUT=5

# ===== Performance Tuning =====
INGESTION_BATCH_SIZE=10
INGESTION_WORKERS=4
MAX_CONCURRENT_EMBEDDINGS=20
MAX_CONCURRENT_EXTRACTIONS=10
```

## Performance Targets & Metrics

### Ingestion Performance
| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Document throughput | 100+ docs/hour | Time 100 document batch |
| Chunking speed | <1s per document | Profile chunker.chunk() |
| Embedding generation | <500ms per chunk | Measure API latency |
| Entity extraction | <2s per chunk | Profile extractor.extract() |
| Graph update | <1s per document | Measure Neo4j writes |

### Search Performance
| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Vector search latency | <200ms | 95th percentile query time |
| Graph search latency | <500ms | 95th percentile query time |
| Hybrid search latency | <300ms | Average of 100 queries |
| Cache hit rate | >80% | Monitor cache statistics |
| Concurrent capacity | 100+ QPS | Load testing |

### Quality Metrics
| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Chunk coherence | 95%+ | Manual review sample |
| Entity precision | 90%+ | Compare to gold standard |
| Entity recall | 80%+ | Compare to gold standard |
| Fact accuracy | 95%+ | Manual validation |
| Search relevance | 85%+ P@10 | User feedback/testing |

## Risk Analysis & Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| LLM API failures | High | Medium | Implement fallback to simple chunking; Add retry logic with exponential backoff |
| Slow knowledge extraction | Medium | High | Add timeouts; Make extraction optional; Process in background queue |
| Memory exhaustion | High | Low | Stream processing; Batch documents; Monitor memory usage |
| Search performance degradation | High | Medium | Implement caching; Add circuit breakers; Scale horizontally |
| Entity extraction errors | Medium | Medium | Confidence thresholds; Human-in-the-loop validation |

### Operational Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Data inconsistency | High | Low | Transaction management; Sync verification; Rollback capability |
| Cost overruns (LLM APIs) | Medium | Medium | Monitor usage; Set quotas; Use cheaper models for extraction |
| Storage growth | Medium | High | Implement retention policies; Archive old data; Monitor disk usage |

## Success Criteria

### Phase 2 Completion Checklist

- [x] **Ingestion Pipeline**
  - [x] Semantic chunking implemented
  - [x] Simple chunking fallback working
  - [x] Embedding generation with caching
  - [x] Batch processing capability
  - [x] Error recovery mechanisms

- [x] **Knowledge Extraction**
  - [x] Entity extraction (names only)
  - [x] Relationship identification
  - [x] Fact extraction (<500 chars)
  - [x] Confidence scoring
  - [x] Zero content duplication verified

- [x] **Search Implementation**
  - [x] Vector search <200ms
  - [x] Graph search <500ms
  - [x] Hybrid search working
  - [x] Result ranking algorithm
  - [x] Search caching

- [x] **Integration**
  - [x] PostgreSQL integration
  - [x] Neo4j/Graphiti integration
  - [x] Cache layer working
  - [x] Monitoring/metrics

- [x] **Testing**
  - [x] Unit tests passing
  - [x] Integration tests passing
  - [x] Performance benchmarks met
  - [x] Load testing completed

## Implementation Timeline

### Day 4: Ingestion Pipeline (8 hours)
- **Hours 1-2**: Pipeline orchestrator structure
- **Hours 3-4**: Semantic chunking implementation
- **Hours 5-6**: Simple chunking fallback
- **Hours 7-8**: Embedding generation with batching

### Day 5: Knowledge Extraction (8 hours)
- **Hours 1-2**: Entity extraction
- **Hours 3-4**: Relationship identification
- **Hours 5-6**: Fact extraction with limits
- **Hours 7-8**: Graphiti integration

### Day 6: Search Implementation (8 hours)
- **Hours 1-2**: Vector search optimization
- **Hours 3-4**: Graph search queries
- **Hours 5-6**: Hybrid search orchestration
- **Hours 7-8**: Result ranking and caching

## Dependencies & Prerequisites

### Required from Phase 1
- ConnectionManager for database access
- PostgreSQL schema with vector support
- Neo4j with Graphiti initialization
- Migration system
- Configuration management

### External Dependencies
```txt
# requirements.txt additions
pydantic>=2.0.0
pydantic-ai>=0.0.9
tiktoken>=0.5.0  # Token counting
nltk>=3.8.0  # Text processing
spacy>=3.7.0  # NER
numpy>=1.24.0  # Numerical operations
scikit-learn>=1.3.0  # Text similarity
```

## Next Steps (Phase 3 Preview)

With Phase 2 complete, the system will have full ingestion and search capabilities. Phase 3 will add:

1. **Agent Intelligence**
   - Query intent analysis
   - Tool orchestration
   - Multi-step reasoning
   - Context management

2. **API Layer**
   - FastAPI endpoints
   - Request validation
   - Response streaming
   - Rate limiting

3. **User Interface**
   - Chat interface
   - Search interface
   - Document upload
   - Results visualization

## Implementation Summary

### ✅ Phase 2 Successfully Completed (2024-12-25)

Phase 2 has been fully implemented, establishing the core data processing pipeline that transforms raw documents into searchable, knowledge-enhanced content. All components maintain the zero content duplication principle while providing powerful search capabilities.

#### Key Achievements:
- **Quality**: Semantic chunking with LLM-powered boundary detection and fallback to rule-based chunking
- **Performance**: All latency targets met (<200ms vector, <500ms graph, <300ms hybrid)
- **Reliability**: Comprehensive error handling with fallback strategies for all components
- **Maintainability**: Clean architecture with modular design and extensive test coverage

#### Components Delivered:
1. **Ingestion Pipeline** (`src/agentic_rag/ingestion/`)
   - Document chunking (semantic and simple strategies)
   - Embedding generation with caching
   - Knowledge extraction (entities, relationships, facts)
   - Pipeline orchestration with error recovery

2. **Search System** (`src/agentic_rag/search/`)
   - Vector search with pgvector optimization
   - Graph search for facts and relationships
   - Hybrid search with intelligent orchestration
   - Intent analysis and result ranking

3. **Testing & Configuration**
   - Comprehensive unit and integration tests
   - Performance benchmarks validated
   - Complete environment configuration template

### Ready for Phase 3

The system is now fully prepared for Phase 3's agent intelligence layer, which will leverage these core components to provide:
- Sophisticated query understanding
- Multi-step reasoning
- Tool orchestration
- Context management
- Response generation with citations

All Phase 2 success criteria have been met, and the implementation provides a solid foundation for the advanced agent capabilities to come.
