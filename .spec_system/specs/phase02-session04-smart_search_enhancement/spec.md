# Session Specification

**Session ID**: `phase02-session04-smart_search_enhancement`
**Phase**: 02 - Advanced Query Engine
**Status**: Not Started
**Created**: 2025-12-30

---

## 1. Session Overview

This session represents the critical integration point for all Phase 01 and Phase 02 improvements into the unified smart_search tool. With three specialized query engines now complete (multi-hop traversal, temporal trend analysis, and cross-entity comparison), users need a single intelligent entry point that automatically routes natural language queries to the appropriate engine.

The enhanced IntentAnalyzer will detect new intent types (MULTI_HOP, TEMPORAL_TREND, COMPARISON) and route queries accordingly. A result merger will handle heterogeneous results from different engines, and a unified ranking function will combine relationship strength, relevance scores, and temporal signals into coherent output.

This session transforms the smart_search tool from a basic vector/graph hybrid into a comprehensive query router that leverages all Phase 02 capabilities. It directly enables Session 05 (Query Performance and Validation) by providing the integrated system that needs optimization and benchmarking.

---

## 2. Objectives

1. Extend IntentAnalyzer with three new intent types (MULTI_HOP, TEMPORAL_TREND, COMPARISON) and their detection patterns
2. Implement intelligent query routing in smart_search tool to appropriate engine based on detected intent
3. Create result merger that normalizes and combines heterogeneous results from different query engines
4. Build unified ranking function incorporating relationship strength, relevance, and temporal signals

---

## 3. Prerequisites

### Required Sessions
- [x] `phase01-session01-document_reference_population` - Document references in entities
- [x] `phase01-session02-temporal_metadata_extraction` - Temporal metadata on entities/relationships
- [x] `phase01-session03-entity_deduplication` - Deduplicated entity graph
- [x] `phase01-session04-numeric_fact_extraction` - Numeric facts available
- [x] `phase01-session05-relationship_scoring` - Relationship strength scores
- [x] `phase01-session06-type_hierarchy_and_testing` - Type hierarchy for entity filtering
- [x] `phase02-session01-multi_hop_query_engine` - Multi-hop traversal capability
- [x] `phase02-session02-temporal_trend_queries` - Temporal trend analysis
- [x] `phase02-session03-cross_entity_comparison` - Entity comparison engine

### Required Tools/Knowledge
- Understanding of IntentAnalyzer scoring patterns
- Knowledge of HybridSearch routing logic
- Familiarity with multi-hop, temporal, and comparison query APIs

### Environment Requirements
- Neo4j Aura connection functional
- PostgreSQL/Supabase connection functional
- All Phase 01-02 tests passing

---

## 4. Scope

### In Scope (MVP)
- Three new SearchIntent enum values (MULTI_HOP, TEMPORAL_TREND, COMPARISON)
- Intent detection patterns for multi-hop queries (path-based, connection queries)
- Intent detection patterns for temporal trend queries (trend, change over time)
- Intent detection patterns for comparison queries (compare, versus, difference)
- Query routing logic in smart_search tool
- Result normalization for heterogeneous result types
- Unified ranking combining multiple signal sources
- Type hierarchy integration in search results
- Document reference enrichment in results
- Numeric fact highlighting when relevant
- Integration tests for end-to-end search flow

### Out of Scope (Deferred)
- Custom user-defined intent definitions - *Reason: Complexity, MVP first*
- User-configurable search weights - *Reason: Session 05 optimization scope*
- Search result caching - *Reason: Session 05 performance scope*
- A/B testing of search strategies - *Reason: Post-Phase 02 feature*

---

## 5. Technical Approach

### Architecture

The enhancement follows a layered approach:

1. **Intent Layer**: Extended SearchIntent enum + new scoring methods in IntentAnalyzer
2. **Routing Layer**: Decision logic in smart_search/HybridSearch to select engine
3. **Execution Layer**: Parallel or sequential query execution based on intent
4. **Merge Layer**: ResultMerger class to normalize and combine heterogeneous results
5. **Ranking Layer**: UnifiedRanker combining relationship_strength, relevance, temporal_recency

### Design Patterns
- **Strategy Pattern**: Query engines as interchangeable strategies selected by router
- **Adapter Pattern**: ResultMerger adapts different result types to common format
- **Facade Pattern**: smart_search remains single entry point hiding complexity

### Technology Stack
- Python 3.11+
- Pydantic for result models
- asyncio.gather for parallel execution
- structlog for structured logging

---

## 6. Deliverables

### Files to Create
| File | Purpose | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/search/result_merger.py` | Merge heterogeneous query results | ~200 |
| `src/agentic_rag/search/unified_ranker.py` | Unified ranking combining all signals | ~150 |
| `tests/integration/test_smart_search_enhanced.py` | End-to-end integration tests | ~400 |

### Files to Modify
| File | Changes | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/search/intent_analyzer.py` | Add 3 new intents + detection methods | ~120 |
| `src/agentic_rag/search/hybrid_search.py` | Add routing to Phase 02 engines | ~150 |
| `src/agentic_rag/search/__init__.py` | Export new classes | ~10 |
| `src/tools/rag.py` | Update smart_search tool routing | ~80 |
| `CLAUDE.md` | Document search enhancement | ~50 |

---

## 7. Success Criteria

### Functional Requirements
- [ ] IntentAnalyzer correctly identifies multi-hop queries (e.g., "How is Intel connected to Mobileye?")
- [ ] IntentAnalyzer correctly identifies temporal trend queries (e.g., "How has Intel's revenue changed over time?")
- [ ] IntentAnalyzer correctly identifies comparison queries (e.g., "Compare Intel and AMD's market share")
- [ ] smart_search routes to multi_hop engine for MULTI_HOP intent
- [ ] smart_search routes to temporal_queries engine for TEMPORAL_TREND intent
- [ ] smart_search routes to entity_comparison engine for COMPARISON intent
- [ ] Result merger produces coherent combined results from multiple engines
- [ ] Unified ranking orders results by combined relevance score

### Testing Requirements
- [ ] 35+ new tests covering search enhancement
- [ ] Unit tests for each new intent detection method
- [ ] Unit tests for result merger normalization
- [ ] Unit tests for unified ranking function
- [ ] Integration tests for end-to-end query flow

### Quality Gates
- [ ] All files ASCII-encoded with Unix LF line endings
- [ ] Code follows CONVENTIONS.md (structlog, type hints, async patterns)
- [ ] No new Ruff/Black/MyPy warnings
- [ ] End-to-end search latency under 2 seconds
- [ ] Test coverage maintained at 75%+

---

## 8. Implementation Notes

### Key Considerations
- Extend existing SearchIntent enum rather than creating new enum
- Use centralized configuration via get_settings() for any thresholds
- Follow async patterns for all query engine calls
- Use asyncio.gather with return_exceptions=True for parallel execution

### Potential Challenges
- **Heterogeneous results**: PathResult vs EntityComparison vs TrendResult have different structures
  - *Mitigation*: Create normalized SearchResultItem dataclass with common fields
- **Ranking signal balance**: Relationship strength, relevance, temporal recency need weighting
  - *Mitigation*: Start with equal weights, tune in Session 05
- **Latency**: Multiple engine calls could exceed 2s target
  - *Mitigation*: Use parallel execution, short-circuit on high-confidence single intent

### Relevant Considerations
- [P01] **Unified agent principle**: All enhancements extend smart_search, no new tools
- [P01] **Intent-based routing**: Extend proven pattern from existing IntentAnalyzer
- [P01] **Centralized configuration**: Use get_settings() for scoring thresholds

### ASCII Reminder
All output files must use ASCII-only characters (0-127). No emojis, no unicode, no special characters.

---

## 9. Testing Strategy

### Unit Tests
- Test MULTI_HOP intent detection with path-seeking queries
- Test TEMPORAL_TREND intent detection with trend queries
- Test COMPARISON intent detection with versus/compare queries
- Test result merger with each result type (PathResult, TrendResult, ComparisonResult)
- Test unified ranker score calculation

### Integration Tests
- Test full query flow from smart_search to multi-hop engine
- Test full query flow from smart_search to temporal engine
- Test full query flow from smart_search to comparison engine
- Test hybrid query routing when intent is ambiguous

### Manual Testing
- Query "How is Intel connected to Mobileye?" and verify path results
- Query "How has Intel's revenue changed from 2020 to 2024?" and verify trend results
- Query "Compare Intel and AMD on revenue and market share" and verify comparison results

### Edge Cases
- Query with no clear intent (should fallback to HYBRID)
- Query mentioning entities that don't exist (graceful error handling)
- Query combining multiple intent signals (e.g., temporal + comparison)
- Empty query handling

---

## 10. Dependencies

### External Libraries
- pydantic: >=2.0 (result models)
- structlog: >=24.0.0 (logging)
- asyncio: stdlib (parallel execution)

### Other Sessions
- **Depends on**: phase02-session01, phase02-session02, phase02-session03
- **Depended by**: phase02-session05 (Query Performance and Validation)

---

## Next Steps

Run `/tasks` to generate the implementation task checklist.
