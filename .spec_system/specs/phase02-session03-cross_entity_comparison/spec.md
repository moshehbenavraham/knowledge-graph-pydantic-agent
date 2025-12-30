# Session Specification

**Session ID**: `phase02-session03-cross_entity_comparison`
**Phase**: 02 - Advanced Query Engine
**Status**: Not Started
**Created**: 2025-12-30

---

## 1. Session Overview

This session enables cross-entity comparison queries that compare entities across documents and time periods, supporting questions like "Compare Microsoft vs Intel revenue growth" and "How do Apple and NVIDIA market caps differ?" Building on the foundation established in Phase 01 (numeric facts, type hierarchy, document references) and the query engines from Phase 02 sessions 01-02, this session adds the comparative analysis dimension to our knowledge graph capabilities.

The cross-entity comparison engine leverages three key Phase 01 deliverables: the numeric fact extraction (session 04) which captured financial metrics like revenue, earnings, and margins; the type hierarchy (session 06) which enables validation of comparable entity types; and document reference population (session 01) which provides source attribution. Additionally, it builds on the temporal trend queries (session 02) to support time-filtered comparisons with QoQ and YoY growth rate calculations.

This session follows the established patterns from multi-hop and temporal query engines, using Pydantic models for query parameters and results, a builder pattern for Cypher query construction, and async execution. The deliverables integrate seamlessly with the unified agent as a new `compare_entities` tool, maintaining the project's single-agent architecture principle.

---

## 2. Objectives

1. Implement a cross-entity comparison engine that retrieves and compares numeric facts from 2-5 entities in the knowledge graph
2. Create type compatibility validation using the type hierarchy to prevent invalid comparisons (e.g., person vs product)
3. Add growth rate calculation helpers (QoQ, YoY) that leverage temporal metadata for time-series comparisons
4. Add a `compare_entities` tool to the unified agent enabling natural language comparison queries

---

## 3. Prerequisites

### Required Sessions
- [x] `phase01-session01-document_reference_population` - Provides document_refs on entities for source attribution
- [x] `phase01-session04-numeric_fact_extraction` - Provides numeric_facts on episodes for metric comparisons
- [x] `phase01-session06-type_hierarchy_and_testing` - Provides type hierarchy for compatibility validation
- [x] `phase02-session02-temporal_trend_queries` - Provides temporal comparison patterns (QoQ, YoY)

### Required Tools/Knowledge
- Neo4j Cypher for multi-entity queries and aggregation
- Pydantic models with field validators (following existing patterns)
- Type hierarchy API (get_type_hierarchy, is_subtype_of, expand_type_filter)
- Numeric facts structure (value, unit, magnitude, fact_type)
- Async Python with structlog logging

### Environment Requirements
- Neo4j Aura connection operational
- Entities populated with document_refs property
- Episodes populated with numeric_facts property
- Type hierarchy module available

---

## 4. Scope

### In Scope (MVP)
- Entity comparison query builder with configurable metrics
- Side-by-side result formatting for 2-5 entities
- Type hierarchy filtering for comparable entities (same parent type)
- Numeric fact comparison across entities (revenue, profit, margin, etc.)
- Growth rate calculation helpers (absolute delta, percentage change, QoQ, YoY)
- `compare_entities` agent tool for comparison queries
- Ranking by comparison metric (growth rate, absolute value, etc.)
- Document reference attribution showing source documents
- Unit tests covering comparison logic

### Out of Scope (Deferred)
- Arbitrary entity count comparisons (>5 entities) - *Reason: Complexity and query performance concerns*
- Custom comparison formulas - *Reason: Scope complexity, standard metrics sufficient for MVP*
- Weighted comparison scoring - *Reason: Advanced analytics deferred to future enhancement*
- Visual comparison charts - *Reason: UI enhancement deferred to future phase*
- Cross-type comparisons (comparing person metrics to organization metrics) - *Reason: Semantic validity concerns*

---

## 5. Technical Approach

### Architecture

The cross-entity comparison engine follows the established query engine architecture:

```
ComparisonQuery (Pydantic) -> ComparisonQueryBuilder -> Cypher Query -> Neo4j
                                                            |
                                                            v
ComparisonResult (Pydantic) <- ComparisonResultParser <- Raw Records
```

**Key Components:**
1. `ComparisonQuery` - Pydantic model for query parameters (entities, metric, time filter)
2. `ComparisonResult` - Pydantic model for side-by-side comparison data
3. `EntityMetrics` - Pydantic model for individual entity's metric values
4. `ComparisonQueryBuilder` - Builder pattern for Cypher query construction
5. `ComparisonResultParser` - Parser for Neo4j comparison records
6. `compare_entities` - Agent tool wrapping the comparison engine

### Design Patterns
- **Builder Pattern**: For flexible Cypher query construction (same as multi-hop/temporal)
- **Pydantic Models**: For request/response validation and serialization
- **Type Validation**: Using TypeHierarchy to validate comparable entities
- **Async/Await**: For non-blocking Neo4j queries
- **Singleton Connection Manager**: Reuse existing connection infrastructure

### Technology Stack
- Python 3.11+ with async/await
- Neo4j 5.x (Cypher for multi-entity queries)
- Pydantic v2 for models
- structlog for structured logging
- TypeHierarchy from Phase 01 Session 06

---

## 6. Deliverables

### Files to Create
| File | Purpose | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/graph/entity_comparison.py` | Comparison engine with ComparisonQuery, ComparisonResult, EntityMetrics, builder, parser, execute function, growth rate helpers | ~450 |
| `tests/agentic_rag/graph/test_entity_comparison.py` | Unit tests for comparison logic | ~400 |

### Files to Modify
| File | Changes | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/graph/__init__.py` | Export comparison query components | ~15 |
| `src/tools/rag.py` | Add `compare_entities` tool function | ~80 |
| `src/agent/unified_agent.py` | Register `compare_entities` tool with agent | ~3 |

---

## 7. Success Criteria

### Functional Requirements
- [ ] Entity comparisons return side-by-side metrics for 2-5 entities
- [ ] Type hierarchy prevents invalid comparisons (person vs product returns error)
- [ ] Numeric fact comparisons calculate correct deltas and ratios
- [ ] Growth rate calculations (QoQ, YoY) produce accurate percentage changes
- [ ] Document reference attribution shows source documents for each entity's metrics
- [ ] Ranking by metric value sorts entities correctly (ascending/descending)
- [ ] `compare_entities` tool returns structured ComparisonResult to agent

### Testing Requirements
- [ ] Unit tests written and passing (target: 30+ new tests)
- [ ] Type compatibility tests (valid comparisons, invalid comparisons)
- [ ] Growth rate calculation tests (positive delta, negative delta, zero baseline)
- [ ] Multi-entity comparison tests (2, 3, 4, 5 entities)
- [ ] Empty result handling tested
- [ ] Manual testing with real knowledge graph data

### Quality Gates
- [ ] All files ASCII-encoded (no unicode characters)
- [ ] Unix LF line endings
- [ ] Code follows project conventions (CONVENTIONS.md)
- [ ] Black formatting applied (100 char line length)
- [ ] Ruff linting passes
- [ ] MyPy strict mode passes (full type hints)
- [ ] Comparison queries complete in under 1.5 seconds

---

## 8. Implementation Notes

### Key Considerations
- Type compatibility: Only entities with matching parent types should be comparable (e.g., company vs company, not company vs person)
- Metric alignment: When comparing entities, match metrics by fact_type and unit
- Missing data handling: Some entities may not have all metrics - return None for missing values
- Unit normalization: Numeric facts may have different magnitudes (millions vs billions) - normalize before comparison
- Time filtering: Support optional fiscal_quarter/fiscal_year filters for temporal comparisons

### Potential Challenges
- **Type Compatibility Validation**: Preventing invalid comparisons (person vs product) - *Mitigation: Use TypeHierarchy.get_parent_type() to validate entities share parent type before querying*
- **Numeric Unit Normalization**: Handling millions/billions consistently across entities - *Mitigation: Use normalized `value` field from NumericFact, not raw_value*
- **Performance**: Multi-entity queries (5 entities) may require optimization - *Mitigation: Use UNION queries or parallel execution, set reasonable limits*
- **Missing Metrics**: Entities with missing numeric facts for requested metrics - *Mitigation: Return None for missing data, document gaps in results*
- **Ambiguous Entity Names**: Entity name may match multiple entities - *Mitigation: Support entity_type filter to disambiguate*

### Relevant Considerations
- [Architecture] **Unified agent principle**: Add `compare_entities` tool to existing unified agent in `unified_agent.py`, do not create separate agent
- [Architecture] **Centralized configuration**: Any configuration values (e.g., max entities, default metrics) via `get_settings()`, never `os.getenv()`
- [Performance] **Test suite time**: New tests add to ~7-10 minute suite; keep tests focused and use mocking
- [External Dependencies] **Neo4j Aura connection stability**: Implement proper error handling and connection reuse through ConnectionManager

### ASCII Reminder
All output files must use ASCII-only characters (0-127). No unicode quotes, dashes, or special characters.

---

## 9. Testing Strategy

### Unit Tests
- ComparisonQuery model validation (valid/invalid parameters, entity count limits)
- ComparisonQueryBuilder Cypher generation (2 entities, 5 entities, with time filter)
- ComparisonResultParser parsing (complete data, partial data, empty results)
- Type compatibility validation (same parent type, different parent types)
- Growth rate calculation (positive delta, negative delta, zero baseline, missing baseline)
- Delta calculation (absolute difference, percentage change)
- Unit normalization (millions to billions conversion)

### Integration Tests
- Execute comparison query against mock Neo4j session
- End-to-end query flow from ComparisonQuery to ComparisonResult
- Type validation integration with TypeHierarchy singleton

### Manual Testing
- Query "Compare Intel vs AMD revenue" - verify side-by-side results
- Query "Compare Microsoft vs Apple vs Google market cap" - verify 3-entity comparison
- Query "Compare Intel vs Tim Cook revenue" - verify type validation error (company vs person)
- Query with entity missing metrics - verify graceful handling
- Query with time filter "Compare Intel vs AMD Q3 2024" - verify temporal filtering

### Edge Cases
- Empty result set (no data for entities)
- Single metric across multiple entities (sparse data)
- All entities missing the requested metric
- Zero values (avoid division by zero in percentage calculations)
- Negative values (losses in financial metrics)
- Entity name matches multiple entities (disambiguation)
- Maximum entity count (5 entities)

---

## 10. Dependencies

### External Libraries
- neo4j: 5.x (async driver)
- pydantic: 2.x (models)
- structlog: 24.x (logging)

### Other Sessions
- **Depends on**:
  - `phase01-session01-document_reference_population` (document_refs for attribution)
  - `phase01-session04-numeric_fact_extraction` (numeric_facts on episodes)
  - `phase01-session06-type_hierarchy_and_testing` (TypeHierarchy for validation)
  - `phase02-session02-temporal_trend_queries` (temporal comparison patterns)
- **Depended by**:
  - `phase02-session04-smart_search_enhancement` (comparison intent routing)

---

## Next Steps

Run `/tasks` to generate the implementation task checklist.
