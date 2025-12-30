# NEXT_SESSION.md

## Session Recommendation

**Generated**: 2025-12-30
**Project State**: Phase 02 - Advanced Query Engine
**Completed Sessions**: 8 (6 Phase 01 + 2 Phase 02)

---

## Recommended Next Session

**Session ID**: `phase02-session03-cross_entity_comparison`
**Session Name**: Cross-Entity Comparison
**Estimated Duration**: 2-3 hours
**Estimated Tasks**: 15-18

---

## Why This Session Next?

### Prerequisites Met
- [x] Phase 01 Session 01 completed (document reference population)
- [x] Phase 01 Session 04 completed (numeric fact extraction)
- [x] Phase 01 Session 06 completed (type hierarchy)
- [x] Entities have populated document_refs
- [x] Numeric facts available for comparison metrics

### Dependencies
- **Builds on**: Phase 01 numeric facts, type hierarchy, and Phase 02 temporal trends
- **Enables**: Session 04 (Smart Search Enhancement) which requires comparison capabilities

### Project Progression
Cross-Entity Comparison is the logical next step because:
1. All prerequisites are satisfied from Phase 01 and earlier Phase 02 sessions
2. It directly blocks Session 04 (Smart Search Enhancement) which needs comparison integration
3. Completes the "query engine trio" (multi-hop, temporal, comparison) before unification
4. Addresses key use case: "Compare Microsoft vs Intel revenue growth"

---

## Session Overview

### Objective
Enable cross-entity comparison queries that compare entities across documents and time periods, supporting questions like "Compare Microsoft vs Intel revenue growth" and "How do Apple and NVIDIA market caps differ?"

### Key Deliverables
1. `src/agentic_rag/graph/entity_comparison.py` - Comparison engine with query builder
2. `ComparisonQuery` and `ComparisonResult` Pydantic models
3. `compare_entities` tool added to unified agent
4. Growth rate calculation helpers (QoQ, YoY)
5. Type compatibility validation using type hierarchy
6. Unit tests in `tests/agentic_rag/graph/test_entity_comparison.py`

### Scope Summary
- **In Scope (MVP)**: Entity comparison query builder, side-by-side formatting, type hierarchy filtering, numeric fact comparison, 2-5 entity comparisons, document reference attribution
- **Out of Scope**: Arbitrary entity counts, custom comparison formulas, visual charts

---

## Technical Considerations

### Technologies/Patterns
- Neo4j Cypher for entity retrieval and comparison
- Pydantic models for type-safe query/result handling
- Type hierarchy from Phase 01 Session 06 for valid comparisons
- Numeric facts from Phase 01 Session 04 for metric comparisons
- Async patterns consistent with existing tools

### Potential Challenges
- Type compatibility validation: Preventing invalid comparisons (person vs product)
- Numeric unit normalization: Handling millions/billions consistently across entities
- Performance: Multi-entity queries may require optimization for 5-entity comparisons
- Edge cases: Entities with missing numeric facts for requested metrics

### Relevant Considerations
- [Architecture] **Unified agent principle**: Add compare_entities as tool extension, not new agent
- [Architecture] **Centralized configuration**: Use get_settings() for any comparison thresholds
- [Performance] **Test suite time**: New tests add to ~7-10 minute suite; keep tests focused

---

## Alternative Sessions

If this session is blocked:
1. **phase02-session04-smart_search_enhancement** - Only if comparison can be stubbed/mocked for integration
2. **Phase 00 session** - Technical debt/hardening if graph unavailable

---

## Next Steps

Run `/sessionspec` to generate the formal specification.
