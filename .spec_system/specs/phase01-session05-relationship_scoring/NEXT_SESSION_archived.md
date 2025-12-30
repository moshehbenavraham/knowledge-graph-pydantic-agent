# NEXT_SESSION.md

## Session Recommendation

**Generated**: 2025-12-30
**Project State**: Phase 01 - Knowledge Graph Improvements
**Completed Sessions**: 4 of 6

---

## Recommended Next Session

**Session ID**: `phase01-session05-relationship_scoring`
**Session Name**: Relationship Scoring
**Estimated Duration**: 2-3 hours
**Estimated Tasks**: 10-12

---

## Why This Session Next?

### Prerequisites Met
- [x] Session 04 completed (numeric facts extracted)
- [x] Entity importance scores calculated (from existing Episode-Entity Linking)
- [x] Relationship types defined and consistent

### Dependencies
- **Builds on**: Session 04 (Numeric Fact Extraction) - entities now have structured data
- **Enables**: Session 06 (Type Hierarchy and Testing) - which requires sessions 01-05 complete

### Project Progression
Session 05 is the natural next step in the Phase 01 sequence. Sessions 01-04 have progressively built the knowledge graph foundation:
1. Document references enable cross-document tracking
2. Temporal metadata enables time-based queries
3. Entity deduplication reduces fragmentation
4. Numeric facts enable structured queries

Session 05 adds the final data enrichment layer - relationship scoring - before Session 06 validates the entire phase with comprehensive testing. The session is focused (10-12 tasks) and does not depend on Session 06's type hierarchy work.

---

## Session Overview

### Objective
Replace static relationship strength with evidence-based dynamic scoring, enabling higher-quality search results by weighting relationships based on evidence strength.

### Key Deliverables
1. Scoring function in `src/agentic_rag/graph/relationship_scoring.py`
2. Updated relationship creation logic in `neo4j_store.py`
3. Backfill script `scripts/backfill_relationship_scores.py`
4. Updated search weighting in `hybrid_search.py`
5. Unit tests in `tests/rag_pipeline/test_relationship_scoring.py`
6. Documentation for scoring algorithm

### Scope Summary
- **In Scope (MVP)**: `calculate_relationship_strength()` based on chunk count, relationship type priority, and entity importance scores; relationship update during ingestion; backfill script; search weighting integration
- **Out of Scope**: Temporal recency weighting, user feedback-based scoring, relationship type inference, graph neural network approaches

---

## Technical Considerations

### Technologies/Patterns
- Neo4j Cypher for relationship queries and updates
- Python scoring algorithm with configurable weights
- Batch processing for backfill (avoid timeouts on 18,195 relationships)
- Integration with existing `hybrid_search.py` weighting

### Potential Challenges
- Determining optimal weight coefficients for scoring factors
- Ensuring backfill script handles large relationship counts efficiently
- Avoiding performance regression in search queries
- Maintaining determinism in scoring algorithm

### Relevant Considerations
- **Unified agent principle**: Updates to search weighting must go through `hybrid_search.py`, not new files
- **Neo4j Aura connection stability**: Backfill script should handle connection drops gracefully
- **Structured logging with structlog**: Add logging for scoring calculations and backfill progress

---

## Alternative Sessions

If this session is blocked:
1. **Session 06 (Type Hierarchy)** - Could start type hierarchy implementation, but testing portion requires Session 05 complete
2. **Phase 00 session** - Return to MVP hardening if graph database is unavailable

---

## Next Steps

Run `/sessionspec` to generate the formal specification.
