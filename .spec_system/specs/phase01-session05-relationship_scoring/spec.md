# Session Specification

**Session ID**: `phase01-session05-relationship_scoring`
**Phase**: 01 - Knowledge Graph Improvements
**Status**: Not Started
**Created**: 2025-12-30

---

## 1. Session Overview

This session implements evidence-based dynamic relationship scoring for the knowledge graph, replacing static relationship strength values with computed scores based on multiple evidence factors. The scoring function considers chunk count (more mentions across different chunks indicates stronger evidence), relationship type priority (e.g., ACQUIRED relationships are stronger than MENTIONED_IN), and entity importance scores (relationships between high-importance entities score higher).

The relationship scoring system is the final data enrichment layer in Phase 01 before comprehensive testing in Session 06. It builds upon the foundation established by Sessions 01-04: document references enable cross-document tracking, temporal metadata enables time-based queries, entity deduplication reduces fragmentation, and numeric facts enable structured queries. Now, relationship scoring adds quality-weighted edges to the graph.

This enhancement directly improves search quality in `hybrid_search.py` by enabling the ranker to weight graph results based on relationship evidence strength. Queries traversing highly-scored relationships will return more relevant results than those following weakly-evidenced connections.

---

## 2. Objectives

1. Implement `calculate_relationship_strength()` function that computes scores (0.0-1.0) based on chunk count, relationship type priority, and entity importance
2. Integrate relationship scoring into the ingestion pipeline so new relationships receive computed scores automatically
3. Create a backfill script that efficiently scores all 18,195 existing relationships in the Neo4j database
4. Update search weighting in `hybrid_search.py` to incorporate relationship strength into result ranking

---

## 3. Prerequisites

### Required Sessions
- [x] `phase01-session01-document_reference_population` - Entities have document_refs for cross-document tracking
- [x] `phase01-session02-temporal_metadata_extraction` - Episodes have temporal metadata
- [x] `phase01-session03-entity_deduplication` - Entity fragmentation reduced
- [x] `phase01-session04-numeric_fact_extraction` - Structured numeric data extracted

### Required Tools/Knowledge
- Neo4j Cypher query language (relationship property updates)
- Python async patterns (batch processing)
- Understanding of existing `neo4j_store.py` relationship creation logic
- Familiarity with `hybrid_search.py` boosting mechanisms

### Environment Requirements
- Neo4j Aura connection configured (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
- Python 3.11+ with project dependencies installed
- Access to run Cypher queries against Neo4j database

---

## 4. Scope

### In Scope (MVP)
- Scoring function with three factors: chunk_count, type_priority, entity_importance
- Configurable weight coefficients for each scoring factor
- Integration with `add_relationships()` in neo4j_store.py
- Batch backfill script with progress logging and connection retry handling
- Search weight integration in `_boost_with_graph_context()` method
- Unit tests covering scoring formula, edge cases, and determinism

### Out of Scope (Deferred)
- Temporal recency weighting - *Reason: Requires additional temporal analysis infrastructure*
- User feedback-based scoring - *Reason: No feedback collection mechanism exists yet*
- Relationship type inference/reclassification - *Reason: Out of scope for scoring session*
- Graph neural network approaches - *Reason: Adds ML complexity beyond MVP needs*
- Real-time score updates on entity importance changes - *Reason: Performance implications need separate analysis*

---

## 5. Technical Approach

### Architecture

The scoring system uses a weighted linear combination approach:

```
strength = (w1 * chunk_factor) + (w2 * type_factor) + (w3 * importance_factor)
```

Where:
- `chunk_factor` = min(1.0, chunk_count / MAX_CHUNKS) normalized by configurable MAX_CHUNKS threshold
- `type_factor` = priority score from TYPE_PRIORITIES dict (e.g., ACQUIRED=1.0, MENTIONED_IN=0.3)
- `importance_factor` = average importance_score of the two connected entities

Default weights: w1=0.4, w2=0.3, w3=0.3 (configurable)

### Design Patterns
- **Strategy Pattern**: Configurable weight coefficients allow tuning without code changes
- **Batch Processing**: Backfill script processes relationships in configurable batch sizes to avoid Neo4j timeouts
- **Singleton**: Scoring function is stateless and can be called from any context

### Technology Stack
- Python 3.11+ (async/await for Neo4j operations)
- Neo4j Driver (async session for batch updates)
- structlog (structured logging for progress tracking)
- pytest + pytest-asyncio (unit testing)

---

## 6. Deliverables

### Files to Create
| File | Purpose | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/graph/relationship_scoring.py` | Scoring function and type priority constants | ~80 |
| `scripts/backfill_relationship_scores.py` | Batch backfill script with progress logging | ~120 |
| `tests/rag_pipeline/test_relationship_scoring.py` | Unit tests for scoring function | ~150 |

### Files to Modify
| File | Changes | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/storage/neo4j_store.py` | Call scoring function in add_relationships() | ~15 |
| `src/agentic_rag/search/hybrid_search.py` | Add relationship strength to boost calculation | ~20 |
| `src/agentic_rag/graph/__init__.py` | Export scoring function | ~2 |

---

## 7. Success Criteria

### Functional Requirements
- [ ] All existing relationships (18,195) have dynamic strength scores between 0.0 and 1.0
- [ ] High-chunk-count relationships score higher than low-chunk-count relationships
- [ ] ACQUIRED/OWNS relationships score higher than MENTIONED_IN relationships
- [ ] Relationships between high-importance entities score higher
- [ ] New relationships created during ingestion receive computed scores
- [ ] Search results are boosted by relationship strength

### Testing Requirements
- [ ] Unit tests written and passing (target: 12+ tests)
- [ ] Tests cover: formula correctness, edge cases (0 chunks, missing entities), determinism
- [ ] Integration test: backfill script completes without errors on test database
- [ ] Manual testing: verify scores in Neo4j Browser with sample queries

### Quality Gates
- [ ] All files ASCII-encoded with Unix LF line endings
- [ ] Code follows project conventions (CONVENTIONS.md)
- [ ] ruff lint, black format, mypy type check pass
- [ ] No performance regression on relationship queries (< 100ms added latency)
- [ ] Existing tests still pass (1,113 tests)

---

## 8. Implementation Notes

### Key Considerations
- Relationship type priorities should be defined as constants, not hardcoded in queries
- Scoring function must be pure/deterministic (same inputs = same output)
- Backfill script should be idempotent (safe to run multiple times)
- Entity importance scores range 0.0-1.0 (default 0.5 for entities without explicit scores)

### Potential Challenges
- **Large batch processing**: 18,195 relationships - use batch sizes of 500-1000 with progress logging
- **Connection stability**: Neo4j Aura may drop connections - implement retry logic with exponential backoff
- **Weight tuning**: Initial coefficients may need adjustment - make configurable via environment variables
- **Missing entity scores**: Some entities may lack importance_score - use fallback default of 0.5

### Relevant Considerations
- [Architecture] **Unified agent principle**: All search changes go through hybrid_search.py boosting mechanism
- [External Dependencies] **Neo4j Aura connection stability**: Backfill script must handle connection drops gracefully
- [What Worked] **Structured logging with structlog**: Add detailed logging for scoring calculations and backfill progress
- [What to Avoid] **Blocking operations in async contexts**: Use async Neo4j session for all database operations

### ASCII Reminder
All output files must use ASCII-only characters (0-127). No Unicode arrows, emojis, or special characters.

---

## 9. Testing Strategy

### Unit Tests
- Test `calculate_relationship_strength()` with known inputs/outputs
- Test chunk_factor normalization (0, 1, MAX_CHUNKS, > MAX_CHUNKS)
- Test type_factor lookup for all defined relationship types
- Test importance_factor averaging with edge cases (0.0, 1.0, missing)
- Test overall formula produces values in [0.0, 1.0] range
- Test determinism (same inputs always produce same output)

### Integration Tests
- Test scoring integration in neo4j_store.add_relationships()
- Test backfill script on small test dataset (10-20 relationships)
- Test hybrid_search boost with mocked relationship strengths

### Manual Testing
- Run backfill script on development database
- Query Neo4j Browser: `MATCH ()-[r:RELATED_TO]->() RETURN r.strength ORDER BY r.strength DESC LIMIT 10`
- Verify high-evidence relationships (many chunks, important entities) score higher
- Execute sample searches and verify relationship-boosted results

### Edge Cases
- Relationship with 0 source_chunks (should handle gracefully, minimum score)
- Relationship between entities with no importance_score (use default 0.5)
- Unknown relationship type (use default type_priority of 0.5)
- Self-referential relationships (entity1 == entity2, should still score)

---

## 10. Dependencies

### External Libraries
- neo4j (async driver): >=5.0.0
- structlog: >=24.0.0
- pytest: >=7.0.0
- pytest-asyncio: >=0.21.0

### Other Sessions
- **Depends on**: phase01-session01 through phase01-session04 (completed)
- **Depended by**: phase01-session06-type_hierarchy_and_testing (comprehensive testing requires scoring)

---

## Next Steps

Run `/tasks` to generate the implementation task checklist.
