# NEXT_SESSION.md

## Session Recommendation

**Generated**: 2025-12-30
**Project State**: Phase 02 - Advanced Query Engine
**Completed Sessions**: 7

---

## Recommended Next Session

**Session ID**: `phase02-session02-temporal_trend_queries`
**Session Name**: Temporal Trend Queries
**Estimated Duration**: 2-3 hours
**Estimated Tasks**: 15-18

---

## Why This Session Next?

### Prerequisites Met
- [x] Phase 01 Session 02 completed (temporal metadata extraction)
- [x] Phase 01 Session 04 completed (numeric fact extraction)
- [x] All episodes have fiscal_quarter and fiscal_year properties
- [x] Numeric facts populated on financial episodes
- [x] Phase 02 Session 01 completed (multi-hop query engine)

### Dependencies
- **Builds on**: Multi-hop Query Engine (session 01) - uses graph traversal patterns
- **Enables**: Cross-Entity Comparison (session 03) - provides temporal filtering for comparisons

### Project Progression
Temporal Trend Queries is the natural next step after Multi-hop Query Engine. While session 01 enabled relationship traversal across entities, this session adds the temporal dimension - allowing queries like "How has Apple's revenue changed over time?" and "Compare Intel Q3 2023 vs Q3 2024". This leverages the fiscal_quarter/fiscal_year metadata from Phase 01 Session 02 and the numeric_facts from Phase 01 Session 04 to enable time-series financial analysis.

---

## Session Overview

### Objective
Enable temporal trend analysis queries using fiscal_quarter and fiscal_year metadata, supporting time-series questions and quarter-over-quarter/year-over-year comparisons.

### Key Deliverables
1. `src/agentic_rag/graph/temporal_queries.py` - Temporal query engine with time-series capabilities
2. `TemporalQuery` and `TrendResult` Pydantic models for structured query/response
3. `temporal_trend` tool added to unified agent for time-based queries
4. Quarter-over-quarter (QoQ) and year-over-year (YoY) comparison functions
5. Unit tests in `tests/agentic_rag/graph/test_temporal_queries.py`

### Scope Summary
- **In Scope (MVP)**: Temporal aggregation query builder, time-series formatting, QoQ/YoY helpers, numeric fact aggregation, `temporal_trend` agent tool
- **Out of Scope**: Forecasting/prediction, custom date ranges beyond fiscal quarters, real-time updates, graphical visualization

---

## Technical Considerations

### Technologies/Patterns
- Neo4j Cypher temporal queries using fiscal_quarter/fiscal_year properties
- Pydantic models for query parameters and results (consistent with multi-hop patterns)
- Async query execution matching existing graph query patterns
- Integration with numeric_facts for financial aggregation

### Potential Challenges
- Handling missing quarters gracefully in YoY comparisons
- Chronological ordering with fiscal year boundaries (Q4 -> Q1 transitions)
- Aggregating numeric facts with different units (millions vs billions)
- Query performance target: under 1 second for temporal queries

### Relevant Considerations
- **Unified Agent Principle**: Add `temporal_trend` tool to existing unified agent, don't create separate agent
- **Centralized Configuration**: Use `get_settings()` for any configuration values, never `os.getenv()`
- **Intent-Based Routing**: Temporal queries will integrate with intent analyzer for TEMPORAL intent type

---

## Alternative Sessions

If this session is blocked:
1. **phase02-session03-cross_entity_comparison** - Could be implemented first if temporal trends are not priority, but would lack temporal filtering capability
2. **phase02-session04-smart_search_enhancement** - Could integrate existing features, but would miss temporal and comparison capabilities

---

## Next Steps

Run `/sessionspec` to generate the formal specification.
