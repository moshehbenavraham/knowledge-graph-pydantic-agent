# NEXT_SESSION.md

## Session Recommendation

**Generated**: 2025-12-30
**Project State**: Phase 02 - Advanced Query Engine
**Completed Sessions**: 9 (Phase 01: 6/6, Phase 02: 3/5)

---

## Recommended Next Session

**Session ID**: `phase02-session04-smart_search_enhancement`
**Session Name**: Smart Search Enhancement
**Estimated Duration**: 3-4 hours
**Estimated Tasks**: 18-22

---

## Why This Session Next?

### Prerequisites Met
- [x] Session 01 completed (multi-hop query engine)
- [x] Session 02 completed (temporal trend queries)
- [x] Session 03 completed (cross-entity comparison)
- [x] Existing smart_search tool functional
- [x] Intent analyzer operational

### Dependencies
- **Builds on**: Sessions 01-03 (all query engines)
- **Enables**: Session 05 (Query Performance and Validation)

### Project Progression
This is the **integration session** that unifies all Phase 01 and Phase 02 improvements into the smart_search tool. With three specialized query engines now complete (multi-hop, temporal trends, cross-entity comparison), they need to be accessible through a single intelligent entry point. Users should be able to ask natural language questions and have the system automatically route to the appropriate query engine.

Session 05 explicitly depends on Session 04 being complete before it can validate and optimize query performance.

---

## Session Overview

### Objective
Integrate all Phase 01 and Phase 02 improvements into the unified smart_search tool and hybrid search pipeline, enabling seamless access to multi-hop, temporal, and comparison capabilities through natural language queries.

### Key Deliverables
1. Enhanced `IntentAnalyzer` with new intent types (MULTI_HOP, TEMPORAL_TREND, COMPARISON)
2. Updated `smart_search` tool with query routing to appropriate engine
3. Result merger for heterogeneous query results
4. Unified ranking function incorporating all signals
5. Updated hybrid_search.py with Phase 02 integrations
6. Integration tests in `tests/integration/test_smart_search.py`
7. Updated CLAUDE.md with search enhancement documentation

### Scope Summary
- **In Scope (MVP)**: Enhanced intent detection, smart routing, result merging, unified ranking, type hierarchy integration, document reference enrichment, numeric fact highlighting, integration tests
- **Out of Scope**: Custom intent definitions, user-defined search weights, caching (Session 05), A/B testing

---

## Technical Considerations

### Technologies/Patterns
- Intent-based query routing (extends existing IntentAnalyzer)
- Result normalization and merging across query types
- Unified ranking using relationship strength, relevance, and temporal signals
- Async parallel query execution for multi-source results

### Potential Challenges
- Merging heterogeneous results from different query engines (paths vs entities vs comparisons)
- Balancing ranking signals from multiple sources without over-weighting any single factor
- Maintaining sub-2-second latency when routing to multiple query engines

### Relevant Considerations
- [P01] **Unified agent principle**: All enhancements go into existing smart_search, no new tools
- [P01] **Intent-based routing**: Proven pattern from existing search, extend for new intents
- [P01] **Centralized configuration**: Use get_settings() for any new config values

---

## Alternative Sessions

If this session is blocked:
1. **None available** - Session 05 requires Session 04 to be complete first
2. **Phase 03 planning** - Could begin planning next phase while waiting on blockers

---

## Next Steps

Run `/sessionspec` to generate the formal specification.
