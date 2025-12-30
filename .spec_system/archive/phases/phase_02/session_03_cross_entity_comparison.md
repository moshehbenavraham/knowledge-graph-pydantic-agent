# Session 03: Cross-Entity Comparison

**Session ID**: `phase02-session03-cross_entity_comparison`
**Status**: Not Started
**Estimated Tasks**: ~15-18
**Estimated Duration**: 2-3 hours

---

## Objective

Enable cross-entity comparison queries that compare entities across documents and time periods, supporting questions like "Compare Microsoft vs Intel revenue growth" and "How do Apple and NVIDIA market caps differ?"

---

## Scope

### In Scope (MVP)
- Entity comparison query builder with configurable metrics
- Side-by-side result formatting for multiple entities
- Type hierarchy filtering for comparable entities
- Numeric fact comparison across entities
- New agent tool: `compare_entities` for comparison queries
- Ranking by comparison metric (growth rate, absolute value, etc.)
- Integration with document_refs for source attribution
- Unit tests for comparison logic

### Out of Scope
- Arbitrary entity count comparisons (limited to 2-5 entities)
- Custom comparison formulas
- Weighted comparison scoring
- Visual comparison charts

---

## Prerequisites

- [ ] Phase 01 Session 01 completed (document reference population)
- [ ] Phase 01 Session 04 completed (numeric fact extraction)
- [ ] Phase 01 Session 06 completed (type hierarchy)
- [ ] Entities have populated document_refs
- [ ] Numeric facts available for comparison metrics

---

## Deliverables

1. `src/agentic_rag/graph/entity_comparison.py` - Comparison engine
2. `ComparisonQuery` Pydantic model for query parameters
3. `ComparisonResult` Pydantic model with side-by-side data
4. `compare_entities` tool added to unified agent
5. Growth rate calculation helpers
6. Type compatibility validation
7. Unit tests in `tests/agentic_rag/graph/test_entity_comparison.py`

---

## Success Criteria

- [ ] Entity comparisons return side-by-side metrics
- [ ] Type hierarchy prevents invalid comparisons (person vs product)
- [ ] Numeric fact comparisons calculate correct deltas/ratios
- [ ] Document reference attribution shows source documents
- [ ] Multiple entity comparisons (3-5) work correctly
- [ ] 25+ new tests covering comparison scenarios
- [ ] Comparison queries complete in under 1.5 seconds
