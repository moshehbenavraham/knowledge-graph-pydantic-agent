# Agentic GraphRAG System - Product Requirements Document

## Overview

Unified AI assistant with Agentic RAG (Retrieval Augmented Generation) capabilities, combining vector search (PostgreSQL/Supabase + pgvector), knowledge graph (Neo4j + Graphiti), and intelligent routing. Built with Pydantic AI, it provides comprehensive tooling for document retrieval, web search, image analysis, SQL queries, and code execution.

## Goals

1. Deliver a production-ready Agentic Graph RAG system with dual-database architecture
2. Provide intelligent query routing via intent analysis (VECTOR_HEAVY, GRAPH_HEAVY, HYBRID, TEMPORAL, ENTITY_FOCUSED)
3. Enable comprehensive document ingestion with knowledge extraction
4. Support multiple UI modes (Simple, Standard, Advanced) for different use cases
5. Maintain enterprise-grade security, authentication, and observability
6. Enable comprehensive QnA capabilities for temporal analysis and multi-document queries
7. Build fully connected entity-episode knowledge graph with dynamic importance scoring

## Non-Goals

- Real-time streaming ingestion (batch processing is sufficient for quarterly reports)
- Sub-second query latency for complex multi-hop queries (2-3 seconds acceptable)
- Automatic entity resolution without human review for high-importance mergers
- Support for non-English documents in initial implementation

## Users and Use Cases

### Primary Users

- **Financial Analysts**: Query quarterly earnings reports across companies and time periods
- **Research Teams**: Extract relationships and trends from document corpora
- **Knowledge Workers**: Ask natural language questions about ingested documents

### Key Use Cases

1. Multi-document temporal queries ("How has Apple's revenue changed over time?")
2. Cross-entity comparisons ("Compare Microsoft vs Intel revenue growth")
3. Entity-based fact retrieval ("What acquisitions did Intel make?")
4. Segment tracking ("Track AWS revenue across quarters")
5. Multi-hop reasoning ("Company acquired Subsidiary which produces Product")

## Requirements

### MVP Requirements (Implemented)

- Episode-entity linking via MENTIONED_IN relationships
- Dynamic importance scoring based on mentions and relationships
- Hybrid search with vector + graph retrieval
- Intent analysis for query routing

### Phase 01 Requirements (Knowledge Graph Improvements)

- Document reference population for cross-document entity tracking
- Temporal metadata extraction from document filenames (fiscal quarter, year, company)
- Entity deduplication with canonical name resolution
- Numeric fact extraction for queryable financial metrics
- Relationship strength scoring based on evidence
- Entity type hierarchy for semantic grouping

### Deferred Requirements

- Real-time document ingestion pipeline
- Automated entity merger without human review
- Custom entity type definitions per corpus
- Graph visualization dashboard

## Non-Functional Requirements

- **Performance**: Multi-doc RAG queries under 2 seconds, entity lookup under 500ms
- **Security**: SQL injection prevention, parameterized queries, input validation
- **Reliability**: Graceful degradation when graph unavailable, error recovery
- **Accessibility**: Clear error messages, structured JSON responses

## Constraints and Dependencies

- Neo4j Aura for knowledge graph storage (existing)
- PostgreSQL/Supabase for content and embeddings (existing)
- Graphiti library for entity extraction (existing dependency)
- Document corpus: 20 quarterly earnings reports (5,057 entities, 18,195 relationships, 11,521 episodes)

## Assumptions

- Document filenames follow pattern: "YYYY QN TICKER.pdf" (e.g., "2023 Q3 INTC.pdf")
- Entities extracted by Graphiti are accurate (focus on linking, not re-extraction)
- Chunk-to-document mapping exists in PostgreSQL

## Risks

- **Entity Merger Errors**: Incorrectly merging distinct entities - mitigate with manual review for high-importance mergers
- **Performance Degradation**: Adding episode-entity links could slow queries - mitigate with indexes on temporal properties
- **Temporal Parsing Failures**: Filename patterns may not cover edge cases - mitigate with fallback to document content parsing

## Phases

| Phase | Name | Sessions | Status |
|-------|------|----------|--------|
| 00 | Mature/Late MVP | TBD | Not Started |
| 01 | Knowledge Graph Improvements | 6 | Complete |
| 02 | Advanced Query Engine | 5 | Complete |
| 03 | Production Readiness & User Experience | 5 | Complete |

## Phase 00: Mature/Late MVP

### Objectives

1. Stabilize and harden existing MVP features
2. Address technical debt and performance optimizations
3. Enhance observability and production readiness
4. Improve user experience and error handling

### Sessions (To Be Defined)

Use `/nextsession` to get recommendations for sessions to implement.

## Phase 01: Knowledge Graph Improvements

### Overview

This phase addresses 6 critical improvements to transform the knowledge graph from a disconnected entity index into a fully queryable temporal knowledge base. Based on analysis of 1,687 QnA questions requiring multi-document temporal analysis, cross-entity comparisons, and entity-based reasoning.

**Current State:**
- 5,057 entities extracted
- 18,195 relationships created
- 11,521 episode nodes (connected via MENTIONED_IN)
- 94% chunk coverage
- 2 of 8 planned improvements implemented (Episode-Entity Linking, Importance Scoring)

**Target State:**
- Document-level entity tracking (100% entities with document_refs)
- Temporal fact queries (fiscal_quarter, fiscal_year on all episodes)
- Canonical entity resolution (95%+ duplicate reduction)
- Numeric fact extraction for financial queries
- Dynamic relationship strength scoring

### Objectives

1. Enable cross-document entity queries ("Which documents mention Microsoft?")
2. Support temporal trend analysis ("Show Apple revenue by quarter")
3. Reduce entity fragmentation through deduplication
4. Extract queryable numeric facts from episode text
5. Improve relationship quality with evidence-based scoring

### Sessions

| Session | Name | Focus | Estimated Tasks |
|---------|------|-------|-----------------|
| 01 | Document Reference Population | Issue 3 | 12-15 |
| 02 | Temporal Metadata Extraction | Issue 4 | 15-18 |
| 03 | Entity Deduplication | Issue 5 | 18-22 |
| 04 | Numeric Fact Extraction | Enhancement 1 | 12-15 |
| 05 | Relationship Scoring | Enhancement 2 | 10-12 |
| 06 | Type Hierarchy and Testing | Enhancement 3 + Validation | 15-18 |

### Session 01: Document Reference Population

**Goal:** Enable cross-document entity queries by populating `document_refs` property.

**Key Deliverables:**
- Update `add_entities()` in `neo4j_store.py` to populate `document_refs` from chunk metadata
- Create `scripts/backfill_document_refs.py` for existing entities
- Add document metadata to entities (filename, company, quarter, year, mention_count)
- Enable queries like: "Entities mentioned in multiple documents"

**Success Criteria:**
- 100% of entities have populated `document_refs`
- Cross-document queries return correct results
- Backfill script completes without errors

### Session 02: Temporal Metadata Extraction

**Goal:** Enable temporal queries by extracting fiscal quarter/year from document filenames.

**Key Deliverables:**
- Parse document filenames: "2023 Q3 INTC.pdf" -> {quarter: Q3, year: 2023, company: Intel}
- Add episode properties: `fiscal_quarter`, `fiscal_year`, `document_date`, `company`
- Update entity temporal span tracking: `first_document_date`, `last_document_date`
- Create backfill script for existing episodes

**Success Criteria:**
- All episodes have `fiscal_quarter` and `fiscal_year` properties
- Queries like "Facts from Q3 2023" return correct results
- Entity timeline queries work across quarters

### Session 03: Entity Deduplication

**Goal:** Reduce entity fragmentation through canonical name resolution.

**Key Deliverables:**
- Create `src/agentic_rag/entity_resolution/canonical_names.py` with mappings
- Implement multi-pass deduplication: exact match, fuzzy matching, context-based
- Create `scripts/merge_duplicate_entities.py` for safe entity merging
- Update ingestion pipeline to use canonical names

**Success Criteria:**
- 95%+ reduction in duplicate entities (e.g., "Apple Inc." + "Apple" -> "Apple")
- No incorrect mergers of distinct entities
- Merge history preserved for potential rollback

### Session 04: Numeric Fact Extraction

**Goal:** Extract queryable numeric values from episode facts.

**Key Deliverables:**
- Parse numeric values from episode text: "revenue was $40,665 million" -> {value: 40665, unit: "million USD"}
- Add `numeric_facts` property to episodes with structured data
- Enable queries like "Find all revenue facts > $50B"

**Success Criteria:**
- Numeric facts extracted from 80%+ of financial episodes
- Queries on numeric values return correct results
- Unit normalization handles millions/billions consistently

### Session 05: Relationship Scoring

**Goal:** Replace static relationship strength with evidence-based scoring.

**Key Deliverables:**
- Implement `calculate_relationship_strength()` based on: chunk count, type priority, entity importance
- Update existing relationships with computed scores
- Add relationship scoring to ingestion pipeline

**Success Criteria:**
- All relationships have dynamic strength scores (0.0-1.0)
- High-evidence relationships score higher than low-evidence
- Search results weighted by relationship strength

### Session 06: Type Hierarchy and Testing

**Goal:** Add semantic entity type grouping and validate all improvements.

**Key Deliverables:**
- Implement `TYPE_HIERARCHY` for semantic grouping (organization -> company, department, subsidiary)
- Create comprehensive test suite for all improvements
- Benchmark query performance against targets
- Update documentation

**Success Criteria:**
- Type hierarchy queries work correctly
- All 46 multi-doc temporal questions from QnA dataset answerable
- Query performance meets targets (multi-doc < 2s, entity lookup < 500ms)

## Phase 02: Advanced Query Engine

### Overview

This phase leverages the improved knowledge graph from Phase 01 to deliver advanced query capabilities. Building on document references, temporal metadata, entity deduplication, numeric facts, relationship scoring, and type hierarchy, Phase 02 enables the key use cases: multi-document temporal queries, cross-entity comparisons, entity-based fact retrieval, segment tracking, and multi-hop reasoning.

### Objectives

1. Enable multi-hop reasoning queries that traverse multiple relationships
2. Support temporal trend analysis using Phase 01 temporal metadata
3. Provide cross-entity comparison capabilities across documents and time periods
4. Integrate all Phase 01 improvements into the unified search pipeline
5. Optimize query performance to meet production targets

### Sessions

| Session | Name | Focus | Estimated Tasks |
|---------|------|-------|-----------------|
| 01 | Multi-hop Query Engine | Relationship traversal | 18-22 |
| 02 | Temporal Trend Queries | Time-series analysis | 15-18 |
| 03 | Cross-Entity Comparison | Entity comparisons | 15-18 |
| 04 | Smart Search Enhancement | Search integration | 18-22 |
| 05 | Query Performance and Validation | Caching and validation | 12-15 |

### Session 01: Multi-hop Query Engine

**Goal:** Enable multi-hop reasoning queries that traverse multiple relationships.

**Key Deliverables:**
- Multi-hop Cypher query builder with configurable depth (1-3 hops)
- Path traversal with relationship type and strength filtering
- Result ranking by cumulative path strength
- New agent tool: `graph_traverse`

**Success Criteria:**
- 2-3 hop queries return correct paths
- 3-hop queries complete in under 2 seconds
- Relationship strength filtering excludes weak paths

### Session 02: Temporal Trend Queries

**Goal:** Enable temporal trend analysis using fiscal_quarter and fiscal_year metadata.

**Key Deliverables:**
- Temporal aggregation query builder
- Time-series result formatting
- Quarter-over-quarter and year-over-year comparison helpers
- New agent tool: `temporal_trend`

**Success Criteria:**
- Time-series queries return chronologically ordered results
- QoQ/YoY comparisons calculate correct deltas
- Temporal queries complete in under 1 second

### Session 03: Cross-Entity Comparison

**Goal:** Enable cross-entity comparison queries across documents and time periods.

**Key Deliverables:**
- Entity comparison query builder
- Side-by-side result formatting
- Type hierarchy filtering for comparable entities
- New agent tool: `compare_entities`

**Success Criteria:**
- Entity comparisons return side-by-side metrics
- Type hierarchy prevents invalid comparisons
- Comparison queries complete in under 1.5 seconds

### Session 04: Smart Search Enhancement

**Goal:** Integrate all Phase 01 and Phase 02 improvements into unified search.

**Key Deliverables:**
- Enhanced intent analyzer with new intent types
- Smart routing to appropriate query engine
- Result merging from multiple query types
- Unified ranking using all signals

**Success Criteria:**
- Intent analyzer correctly identifies query types
- Smart routing selects appropriate engine
- End-to-end search latency under 2 seconds

### Session 05: Query Performance and Validation

**Goal:** Optimize performance and validate against 46 multi-doc temporal QnA questions.

**Key Deliverables:**
- Query result caching with TTL
- Neo4j index optimization
- Performance benchmark suite
- QnA validation against 46 questions

**Success Criteria:**
- Caching reduces repeat query latency by 80%+
- Multi-doc queries under 2 seconds
- 46 QnA questions pass validation
- All existing tests still pass

## Phase 03: Production Readiness & User Experience

### Overview

This phase focuses on production hardening, enhanced observability, and user experience improvements. Building on the robust knowledge graph (Phase 01) and advanced query capabilities (Phase 02), Phase 03 delivers the polish and reliability required for production deployment. Key deliverables include comprehensive error handling, performance monitoring, UI/UX enhancements, graph visualization dashboard, and developer documentation.

### Objectives

1. Harden error handling with graceful degradation and comprehensive retry logic
2. Implement production-grade performance monitoring and profiling capabilities
3. Enhance user experience with improved streaming feedback and error messages
4. Deliver graph visualization dashboard for visual entity/relationship exploration
5. Create comprehensive developer documentation and debugging tools

### Sessions

| Session | Name | Focus | Estimated Tasks |
|---------|------|-------|-----------------|
| 01 | Error Handling & Resilience | Graceful degradation | 15-18 |
| 02 | Performance Monitoring & Profiling | Observability | 12-15 |
| 03 | UI/UX Enhancements | User experience | 18-22 |
| 04 | Graph Visualization Dashboard | Visual exploration | 20-25 |
| 05 | Documentation & Developer Tools | Developer experience | 12-15 |

### Session 01: Error Handling & Resilience

**Goal:** Implement comprehensive error handling with graceful degradation and retry logic.

**Key Deliverables:**
- Error handling middleware for async operations
- Retry logic with exponential backoff
- Graceful degradation for Neo4j/Supabase failures
- Circuit breaker pattern for external services

**Success Criteria:**
- Neo4j failures result in graceful degradation
- Transient failures retry with exponential backoff
- Circuit breaker trips after 5 consecutive failures

### Session 02: Performance Monitoring & Profiling

**Goal:** Implement production-grade performance monitoring and profiling capabilities.

**Key Deliverables:**
- Enhanced Prometheus metrics by query type
- Latency histograms for all search operations
- Cache hit/miss rate tracking
- Performance profiling utilities

**Success Criteria:**
- Query latency tracked by intent type
- Cache hit/miss rates visible in metrics
- Performance profiling available via decorator

### Session 03: UI/UX Enhancements

**Goal:** Enhance user experience with improved streaming feedback and error messages.

**Key Deliverables:**
- Improved streaming progress indicators
- Contextual loading messages
- Better error message formatting
- Query intent feedback to users

**Success Criteria:**
- Tool execution shows real-time status
- Error messages include actionable guidance
- Query intent visible to users

### Session 04: Graph Visualization Dashboard

**Goal:** Deliver graph visualization dashboard for visual entity/relationship exploration.

**Key Deliverables:**
- Entity search and exploration interface
- Interactive graph visualization component
- Entity detail panel with relationships
- Temporal filtering for facts

**Success Criteria:**
- Users can search entities by name/type
- Graph visualization renders entities and relationships
- Performance acceptable for graphs up to 100 nodes

### Session 05: Documentation & Developer Tools

**Goal:** Create comprehensive developer documentation and debugging tools.

**Key Deliverables:**
- API documentation for all endpoints
- Enhanced developer setup guide
- Debug utility scripts
- Updated CLAUDE.md with Phase 03 additions

**Success Criteria:**
- All public API endpoints documented
- Developer can set up project following guide
- CLAUDE.md accurate and up-to-date

## Technical Stack

- **Language**: Python 3.11+
- **AI Framework**: Pydantic AI >= 0.1.2
- **Vector Database**: PostgreSQL/Supabase + pgvector (1536d OpenAI, 768d Ollama)
- **Knowledge Graph**: Neo4j Aura + Graphiti
- **UI Framework**: Streamlit >= 1.44.0
- **Authentication**: streamlit-authenticator >= 0.4.2, bcrypt, OAuth 2.0
- **Memory**: mem0ai >= 0.0.10
- **Observability**: structlog >= 24.0.0, PostgreSQL analytics

## Architecture Highlights

- **Unified Agent**: Single agent in `src/agent/unified_agent.py` - no sub-agents
- **Centralized Config**: `src/config/settings.py` - never use `os.getenv()` directly
- **Dual-Database RAG**: PostgreSQL for content/embeddings, Neo4j for entities/relationships
- **Tool System**: Async tools in `src/tools/` with dependency injection
- **Handler-Based UI**: Feature handlers in `src/ui/features/` for modularity

## Success Criteria

### System-Wide

- [ ] All existing tests pass (1,113 tests, 75% coverage minimum)
- [ ] Zero security vulnerabilities (Bandit, Safety, pip-audit clean)
- [ ] Production deployment via ngrok with two-layer authentication
- [ ] Analytics system capturing all search operations and tool usage
- [ ] Documentation complete and accurate

### Phase 01: Knowledge Graph Improvements

- [ ] 100% of entities have populated document_refs
- [ ] All episodes have fiscal_quarter and fiscal_year properties
- [ ] 95%+ reduction in duplicate entities
- [ ] Numeric facts extracted from 80%+ of financial episodes
- [ ] All relationships have dynamic strength scores
- [ ] Type hierarchy queries functional
- [ ] 46 multi-doc temporal QnA questions answerable
- [ ] Multi-doc RAG queries under 2 seconds
- [ ] Entity lookup under 500ms

## Open Questions

1. Should entity deduplication be automatic or require human review for high-importance entities?
2. What fallback strategy if document filename parsing fails (extract from content? prompt user?)?
3. Should numeric fact extraction use regex patterns or LLM-based extraction?
4. How to handle entity name conflicts across companies (e.g., "Data Center" for Intel vs NVIDIA)?
5. Should relationship scoring consider temporal recency (newer evidence weighted higher)?
6. What retention policy for merge history (permanent? 90 days? configurable?)
