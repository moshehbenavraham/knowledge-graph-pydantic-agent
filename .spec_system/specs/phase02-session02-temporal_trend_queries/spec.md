# Session Specification

**Session ID**: `phase02-session02-temporal_trend_queries`
**Phase**: 02 - Advanced Query Engine
**Status**: Not Started
**Created**: 2025-12-30

---

## 1. Session Overview

This session enables temporal trend analysis queries using the fiscal_quarter and fiscal_year metadata established in Phase 01. Building on the multi-hop query engine from session 01, this session adds the temporal dimension to our query capabilities, allowing users to ask time-series questions like "How has Intel's revenue changed over time?" and "Compare Apple Q3 2023 vs Q3 2024".

The temporal query engine leverages two key Phase 01 deliverables: the temporal metadata extraction (session 02) which populated fiscal_quarter and fiscal_year properties on all episodes, and the numeric fact extraction (session 04) which captured financial metrics like revenue, earnings, and margins. By combining these capabilities, we enable powerful temporal aggregation, quarter-over-quarter (QoQ), and year-over-year (YoY) comparisons.

This session follows the established patterns from the multi-hop query engine, using Pydantic models for query parameters and results, a builder pattern for Cypher query construction, and async execution. The deliverables integrate seamlessly with the unified agent as a new `temporal_trend` tool, maintaining the project's single-agent architecture principle.

---

## 2. Objectives

1. Implement a temporal query engine that retrieves time-ordered data from the knowledge graph using fiscal_quarter and fiscal_year properties
2. Create quarter-over-quarter (QoQ) and year-over-year (YoY) comparison functions that calculate deltas and percentage changes
3. Add a `temporal_trend` tool to the unified agent enabling natural language time-series queries
4. Aggregate numeric facts over time periods with correct handling of missing quarters

---

## 3. Prerequisites

### Required Sessions
- [x] `phase01-session02-temporal_metadata_extraction` - Provides fiscal_quarter and fiscal_year properties on episodes
- [x] `phase01-session04-numeric_fact_extraction` - Provides numeric_facts on financial episodes
- [x] `phase02-session01-multi_hop_query_engine` - Provides query patterns and architecture

### Required Tools/Knowledge
- Neo4j Cypher temporal functions (date ordering, aggregation)
- Pydantic models with field validators (following multi-hop patterns)
- Async Python with structlog logging
- Knowledge graph schema (Entity, Episode, numeric_facts structure)

### Environment Requirements
- Neo4j Aura connection operational
- Episodes populated with fiscal_quarter and fiscal_year properties
- Numeric facts extracted on financial episodes

---

## 4. Scope

### In Scope (MVP)
- Temporal aggregation query builder (by quarter, by year, by company)
- Time-series result formatting with chronological ordering
- Quarter-over-quarter (QoQ) comparison function
- Year-over-year (YoY) comparison function
- Numeric fact aggregation over time periods
- `temporal_trend` agent tool for time-based queries
- Entity filtering by company with temporal constraints
- Unit tests covering temporal query logic

### Out of Scope (Deferred)
- Forecasting or trend prediction - *Reason: Analysis only for MVP, prediction is future enhancement*
- Custom date ranges beyond fiscal quarters - *Reason: Scope complexity, fiscal quarters sufficient for financial analysis*
- Real-time trend updates - *Reason: Batch analysis sufficient for MVP*
- Graphical trend visualization - *Reason: UI enhancement deferred to future phase*
- Moving averages or rolling calculations - *Reason: Advanced analytics deferred*

---

## 5. Technical Approach

### Architecture

The temporal query engine follows the established multi-hop query engine architecture:

```
TemporalQuery (Pydantic) -> TemporalQueryBuilder -> Cypher Query -> Neo4j
                                                        |
                                                        v
TrendResult (Pydantic) <- TrendResultParser <- Raw Records
```

**Key Components:**
1. `TemporalQuery` - Pydantic model for query parameters (entity, metric, time range)
2. `TrendResult` - Pydantic model for time-series results with data points
3. `TemporalQueryBuilder` - Builder pattern for Cypher query construction
4. `TrendResultParser` - Parser for Neo4j temporal records
5. `temporal_trend` - Agent tool wrapping the query engine

### Design Patterns
- **Builder Pattern**: For flexible Cypher query construction (same as multi-hop)
- **Pydantic Models**: For request/response validation and serialization
- **Async/Await**: For non-blocking Neo4j queries
- **Singleton Connection Manager**: Reuse existing connection infrastructure

### Technology Stack
- Python 3.11+ with async/await
- Neo4j 5.x (Cypher for temporal queries)
- Pydantic v2 for models
- structlog for structured logging

---

## 6. Deliverables

### Files to Create
| File | Purpose | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/graph/temporal_queries.py` | Temporal query engine with TemporalQuery, TrendResult, builder, parser, execute function | ~400 |
| `tests/agentic_rag/graph/test_temporal_queries.py` | Unit tests for temporal query logic | ~350 |

### Files to Modify
| File | Changes | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/graph/__init__.py` | Export temporal query components | ~5 |
| `src/tools/rag.py` | Add `temporal_trend` tool function | ~60 |
| `src/agent/unified_agent.py` | Register `temporal_trend` tool with agent | ~3 |

---

## 7. Success Criteria

### Functional Requirements
- [ ] Time-series queries return chronologically ordered results (oldest to newest)
- [ ] Quarter-over-quarter comparisons calculate correct deltas and percentage changes
- [ ] Year-over-year comparisons handle missing quarters gracefully (return None for missing data)
- [ ] Numeric fact aggregation produces correct sums/averages per time period
- [ ] Entity filtering by company works with temporal constraints
- [ ] `temporal_trend` tool returns structured TrendResult to agent

### Testing Requirements
- [ ] Unit tests written and passing (target: 25+ new tests)
- [ ] QoQ comparison tests with edge cases (missing quarters, negative deltas)
- [ ] YoY comparison tests with edge cases (partial years, different companies)
- [ ] Empty result handling tested
- [ ] Manual testing with real knowledge graph data

### Quality Gates
- [ ] All files ASCII-encoded (no unicode characters)
- [ ] Unix LF line endings
- [ ] Code follows project conventions (CONVENTIONS.md)
- [ ] Black formatting applied (100 char line length)
- [ ] Ruff linting passes
- [ ] MyPy strict mode passes (full type hints)
- [ ] Temporal queries complete in under 1 second

---

## 8. Implementation Notes

### Key Considerations
- Fiscal year boundaries: Q4 of year N precedes Q1 of year N+1 in chronological order
- Quarter representation: Use "Q1", "Q2", "Q3", "Q4" string format consistently
- Null handling: Missing numeric facts should not break aggregations
- Company isolation: Queries must filter by entity to avoid cross-company confusion

### Potential Challenges
- **Missing Quarters**: Some companies may not have data for all quarters - *Mitigation: Return None for missing periods, document gaps in results*
- **Fiscal Year Ordering**: Q4 2023 < Q1 2024 for sorting - *Mitigation: Use (year, quarter_num) tuple for ordering, convert Q1-Q4 to 1-4*
- **Unit Normalization**: Numeric facts may have different units (millions vs billions) - *Mitigation: Store unit in metadata, normalize at query time or document units*
- **Query Performance**: Complex temporal aggregations could be slow - *Mitigation: Limit time range, use indexed properties*

### Relevant Considerations
- [P00] **Unified agent principle**: Add `temporal_trend` tool to existing unified agent in `unified_agent.py`, do not create separate agent
- [P00] **Centralized configuration**: Any configuration values (e.g., default time ranges) via `get_settings()`, never `os.getenv()`
- [P00] **Neo4j Aura connection stability**: Implement proper error handling and connection reuse through ConnectionManager
- [P01] **Temporal metadata**: Build queries on fiscal_quarter/fiscal_year properties populated in Phase 01 Session 02
- [P01] **Numeric facts**: Aggregate numeric_facts from Phase 01 Session 04 for financial metrics

### ASCII Reminder
All output files must use ASCII-only characters (0-127). No unicode quotes, dashes, or special characters.

---

## 9. Testing Strategy

### Unit Tests
- TemporalQuery model validation (valid/invalid parameters)
- TemporalQueryBuilder Cypher generation (single quarter, quarter range, year range)
- TrendResultParser parsing (complete data, partial data, empty results)
- QoQ calculation (positive delta, negative delta, missing baseline)
- YoY calculation (full year comparison, partial year, cross-year boundary)

### Integration Tests
- Execute temporal query against mock Neo4j session
- End-to-end query flow from TemporalQuery to TrendResult

### Manual Testing
- Query "How has Intel's revenue changed over time?" - verify chronological ordering
- Query "Compare Apple Q3 2023 vs Q3 2024" - verify QoQ delta calculation
- Query "Show AMD revenue YoY 2023 vs 2024" - verify YoY comparison
- Test with entity that has missing quarters - verify graceful handling

### Edge Cases
- Empty result set (no data for entity/time range)
- Single data point (no trend possible)
- All quarters missing except one
- Negative numeric values (losses)
- Zero values (avoid division by zero in percentage calculations)

---

## 10. Dependencies

### External Libraries
- neo4j: 5.x (async driver)
- pydantic: 2.x (models)
- structlog: 24.x (logging)

### Other Sessions
- **Depends on**:
  - `phase01-session02-temporal_metadata_extraction` (fiscal_quarter, fiscal_year properties)
  - `phase01-session04-numeric_fact_extraction` (numeric_facts on episodes)
  - `phase02-session01-multi_hop_query_engine` (query patterns, architecture)
- **Depended by**:
  - `phase02-session03-cross_entity_comparison` (temporal filtering for comparisons)
  - `phase02-session04-smart_search_enhancement` (temporal intent routing)

---

## Next Steps

Run `/tasks` to generate the implementation task checklist.
