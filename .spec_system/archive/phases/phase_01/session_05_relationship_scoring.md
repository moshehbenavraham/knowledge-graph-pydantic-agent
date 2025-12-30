# Session 05: Relationship Scoring

**Session ID**: `phase01-session05-relationship_scoring`
**Status**: Not Started
**Estimated Tasks**: ~10-12
**Estimated Duration**: 2-3 hours

---

## Objective

Replace static relationship strength with evidence-based dynamic scoring, enabling higher-quality search results by weighting relationships based on evidence strength.

---

## Scope

### In Scope (MVP)
- Implement `calculate_relationship_strength()` based on:
  - Chunk count (more mentions = stronger)
  - Relationship type priority (e.g., ACQUIRED > MENTIONED_IN)
  - Entity importance scores (relationships between important entities score higher)
- Update existing relationships with computed scores
- Add relationship scoring to ingestion pipeline
- Create backfill script `scripts/backfill_relationship_scores.py`
- Update search weighting to use relationship strength

### Out of Scope
- Temporal recency weighting (newer evidence weighted higher)
- User feedback-based scoring
- Relationship type inference/reclassification
- Graph neural network approaches

---

## Prerequisites

- [ ] Session 04 completed (numeric facts extracted)
- [ ] Entity importance scores calculated (from existing Episode-Entity Linking)
- [ ] Relationship types defined and consistent

---

## Deliverables

1. Scoring function in `src/agentic_rag/graph/relationship_scoring.py`
2. Updated relationship creation logic in `neo4j_store.py`
3. Backfill script `scripts/backfill_relationship_scores.py`
4. Updated search weighting in `hybrid_search.py`
5. Unit tests in `tests/rag_pipeline/test_relationship_scoring.py`
6. Documentation for scoring algorithm

---

## Success Criteria

- [ ] All relationships have dynamic strength scores (0.0-1.0)
- [ ] High-evidence relationships score higher than low-evidence
- [ ] Search results weighted by relationship strength
- [ ] Scoring function is deterministic and reproducible
- [ ] Backfill script completes without errors
- [ ] New unit tests pass (target: 10+ tests)
- [ ] Existing tests still pass
- [ ] No performance regression on relationship queries
