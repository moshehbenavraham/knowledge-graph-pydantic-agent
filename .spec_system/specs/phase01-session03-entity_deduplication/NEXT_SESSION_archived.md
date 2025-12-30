# NEXT_SESSION.md

## Session Recommendation

**Generated**: 2025-12-30
**Project State**: Phase 01 - Knowledge Graph Improvements
**Completed Sessions**: 2 of 6

---

## Recommended Next Session

**Session ID**: `phase01-session03-entity_deduplication`
**Session Name**: Entity Deduplication
**Estimated Duration**: 4-5 hours
**Estimated Tasks**: 18-22

---

## Why This Session Next?

### Prerequisites Met
- [x] Session 02 completed (temporal metadata populated on all episodes)
- [x] Entity list accessible via Cypher queries
- [x] Relationship data preserved during merges (via Graphiti)
- [x] Backup of current graph state available (Neo4j Aura snapshots)

### Dependencies
- **Builds on**: Session 02 (Temporal Metadata Extraction) - uses temporal context for entity disambiguation
- **Enables**: Session 04 (Numeric Fact Extraction) - requires deduplicated entities for accurate fact attribution

### Project Progression
Session 03 is the natural next step in Phase 01's sequential improvement plan. With document references (Session 01) and temporal metadata (Session 02) now complete, the knowledge graph has the contextual foundation needed for intelligent entity deduplication. Merging duplicates like "Apple Inc.", "Apple", and "AAPL" into canonical entities will reduce the current 5,057 entity count by an estimated 95%+, directly improving query accuracy and enabling cleaner numeric fact extraction in Session 04.

---

## Session Overview

### Objective
Reduce entity fragmentation through canonical name resolution, merging duplicates while preserving merge history for potential rollback.

### Key Deliverables
1. Canonical name mappings in `src/agentic_rag/entity_resolution/canonical_names.py`
2. Multi-pass deduplication logic (exact match, fuzzy matching, context-based)
3. Merge script `scripts/merge_duplicate_entities.py` with dry-run, interactive, and batch modes
4. Merge history log for rollback capability
5. Updated ingestion pipeline to normalize entity names
6. Unit tests in `tests/rag_pipeline/test_entity_deduplication.py`

### Scope Summary
- **In Scope (MVP)**: Canonical name mappings, multi-pass matching, merge script with dry-run mode, merge history, ingestion pipeline updates, company name variations (Inc., Corp., LLC), ticker symbol mappings
- **Out of Scope**: Automatic resolution for ambiguous cases, real-time streaming deduplication, cross-company disambiguation, merge approval UI

---

## Technical Considerations

### Technologies/Patterns
- Neo4j Cypher for entity queries and relationship merging
- Fuzzy string matching (rapidfuzz or fuzzywuzzy)
- Centralized configuration via `get_settings()` (per architecture principles)
- Async patterns for database operations

### Potential Challenges
- **Relationship preservation**: Merging entities must transfer all incoming/outgoing relationships to the canonical entity without data loss
- **Ambiguous names**: "Data Center" could refer to Intel's or NVIDIA's segment - requires company context from document_refs
- **Performance**: Deduplication across 5,057 entities with 18,195 relationships requires efficient batch operations
- **Rollback complexity**: Merge history must capture enough state to enable clean reversal

### Relevant Considerations
- **External Dependencies**: Neo4j Aura connection stability - ensure retry logic for merge operations
- **Architecture**: Follow unified agent principle - entity resolution is a utility, not a separate agent
- **Performance**: Test suite already takes 7-10 minutes - ensure new tests are efficient

---

## Alternative Sessions

If this session is blocked:
1. **Session 05: Relationship Scoring** - Independent of entity deduplication, focuses on dynamic strength calculation. Lower priority as it benefits from deduplicated entities.
2. **Session 06: Type Hierarchy and Testing** - Could partially start type hierarchy work, but validation phase depends on all prior sessions.

---

## Next Steps

Run `/sessionspec` to generate the formal specification.
