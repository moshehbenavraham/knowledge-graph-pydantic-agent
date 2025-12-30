# PRD Phase 01: Knowledge Graph Improvements

**Status**: In Progress
**Sessions**: 6
**Estimated Duration**: 3-5 days

**Progress**: 2/6 sessions (33%)

---

## Overview

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
- Semantic entity type hierarchy

---

## Progress Tracker

| Session | Name | Status | Est. Tasks | Validated |
|---------|------|--------|------------|-----------|
| 01 | Document Reference Population | Complete | 20 | 2025-12-30 |
| 02 | Temporal Metadata Extraction | Complete | 20 | 2025-12-30 |
| 03 | Entity Deduplication | Not Started | ~18-22 | - |
| 04 | Numeric Fact Extraction | Not Started | ~12-15 | - |
| 05 | Relationship Scoring | Not Started | ~10-12 | - |
| 06 | Type Hierarchy and Testing | Not Started | ~15-18 | - |

---

## Completed Sessions

### Session 01: Document Reference Population (2025-12-30)
- Populated `document_refs` property on all entities with structured metadata (filename, company, quarter, year)
- Created DocumentReference Pydantic model with validation
- Extended `add_entities()` to accept document metadata parameter
- Built idempotent backfill script with batch processing and retry logic
- Added cross-document Cypher query patterns to CLAUDE.md
- 36 new tests, 98.57% coverage on new code, 87.92% overall

### Session 02: Temporal Metadata Extraction (2025-12-30)
- Implemented filename parser for "YYYY QN TICKER.pdf" format with TemporalMetadata dataclass
- Added fiscal_quarter, fiscal_year, document_date, company properties to episode creation
- Created idempotent backfill script with batch processing (500 episodes), retry logic, and dry-run mode
- Added entity temporal span tracking (first/last document dates)
- Ticker-to-company-name mapping configuration (AAPL, MSFT, NVDA, INTC, AMD)
- 39 new tests, all passing in 3.08 seconds

---

## Upcoming Sessions

- Session 03: Entity Deduplication

---

## Objectives

1. Enable cross-document entity queries ("Which documents mention Microsoft?")
2. Support temporal trend analysis ("Show Apple revenue by quarter")
3. Reduce entity fragmentation through deduplication (95%+ reduction)
4. Extract queryable numeric facts from episode text
5. Improve relationship quality with evidence-based scoring
6. Add semantic entity type grouping for hierarchical queries

---

## Prerequisites

- Phase 00 stabilization complete (or concurrent)
- Neo4j Aura connection stable and accessible
- PostgreSQL/Supabase with populated documents and chunks
- Graphiti entity extraction functioning correctly
- Document corpus: 20 quarterly earnings reports ingested

---

## Technical Considerations

### Architecture
- Extend existing `neo4j_store.py` - do not create new graph stores
- Maintain unified agent principle - add graph queries as tools
- Use centralized configuration for all new settings
- Backfill scripts must be idempotent and resumable

### Technologies
- Neo4j Aura (existing graph database)
- Graphiti library (entity extraction - extend, not replace)
- Python regex + optional LLM for numeric extraction
- Cypher queries for graph operations

### Risks
- **Entity Merger Errors**: Incorrectly merging distinct entities - mitigate with manual review for high-importance mergers and merge history for rollback
- **Performance Degradation**: Adding episode-entity links could slow queries - mitigate with indexes on temporal properties
- **Temporal Parsing Failures**: Filename patterns may not cover edge cases - mitigate with fallback to document content parsing
- **Data Loss**: Entity merging could lose information - mitigate with comprehensive merge history and dry-run mode

### Relevant Considerations
- [P00] **Neo4j Aura connection stability**: Cloud-hosted graph database may have connection issues - implement retry logic in backfill scripts
- [P00] **Unified agent principle**: Add graph query tools to existing agent, do not create sub-agents
- [P00] **Centralized configuration**: All new settings via `get_settings()`, never `os.getenv()`
- [P00] **Test suite execution time**: New graph tests should be efficient (target < 1 minute for full graph test suite)

---

## Success Criteria

Phase complete when:
- [ ] All 6 sessions completed and validated
- [ ] 100% of entities have populated document_refs
- [ ] All episodes have fiscal_quarter and fiscal_year properties
- [ ] 95%+ reduction in duplicate entities achieved
- [ ] Numeric facts extracted from 80%+ of financial episodes
- [ ] All relationships have dynamic strength scores (0.0-1.0)
- [ ] Type hierarchy queries functional
- [ ] 46 multi-doc temporal QnA questions answerable
- [ ] Multi-doc RAG queries under 2 seconds
- [ ] Entity lookup under 500ms
- [ ] All existing tests still pass (1,113 tests)
- [ ] No new security vulnerabilities introduced

---

## Dependencies

### Depends On
- Phase 00: Mature/Late MVP (concurrent or complete)
- Existing Neo4j graph with 5,057 entities, 18,195 relationships
- PostgreSQL with chunk-to-document mappings
- Document filename convention: "YYYY QN TICKER.pdf"

### Enables
- Advanced multi-document temporal analysis queries
- Cross-company comparison capabilities
- Financial metrics dashboards
- Entity relationship visualization (future phase)
