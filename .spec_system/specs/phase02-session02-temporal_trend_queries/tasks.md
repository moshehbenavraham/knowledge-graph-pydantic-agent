# Task Checklist

**Session ID**: `phase02-session02-temporal_trend_queries`
**Total Tasks**: 20
**Estimated Duration**: 6-8 hours
**Created**: 2025-12-30

---

## Legend

- `[x]` = Completed
- `[ ]` = Pending
- `[P]` = Parallelizable (can run with other [P] tasks)
- `[S0202]` = Session reference (Phase 02, Session 02)
- `TNNN` = Task ID

---

## Progress Summary

| Category | Total | Done | Remaining |
|----------|-------|------|-----------|
| Setup | 2 | 2 | 0 |
| Foundation | 5 | 5 | 0 |
| Implementation | 8 | 8 | 0 |
| Testing | 5 | 5 | 0 |
| **Total** | **20** | **20** | **0** |

---

## Setup (2 tasks)

Initial verification and environment preparation.

- [x] T001 [S0202] Verify prerequisites: fiscal_quarter/fiscal_year properties exist on episodes, numeric_facts populated (`make neo4j-init` if needed)
- [x] T002 [S0202] Verify multi-hop patterns available: confirm `src/agentic_rag/graph/multi_hop.py` exists as reference architecture

---

## Foundation (5 tasks)

Core dataclasses and Pydantic models following multi-hop patterns.

- [x] T003 [S0202] Create `src/agentic_rag/graph/temporal_queries.py` with module docstring and imports (structlog, pydantic, typing, dataclasses)
- [x] T004 [S0202] [P] Define `DataPoint` dataclass - single time-series data point with quarter, year, value, unit, entity properties
- [x] T005 [S0202] [P] Define `TrendResult` dataclass - collection of DataPoints with trend metadata (direction, percent_change, time_span)
- [x] T006 [S0202] [P] Define `ComparisonResult` dataclass - QoQ/YoY comparison with baseline, current, delta, percent_change, missing_data flags
- [x] T007 [S0202] Define `TemporalQuery` Pydantic model - entity, metric, start_year, end_year, start_quarter, end_quarter, comparison_type fields with validators

---

## Implementation (8 tasks)

Main temporal query engine implementation.

- [x] T008 [S0202] Implement `TemporalQueryBuilder` class - builder pattern with fluent methods: `for_entity()`, `with_metric()`, `in_range()`, `with_comparison()`
- [x] T009 [S0202] Implement `TemporalQueryBuilder.build()` - generate Cypher query for temporal aggregation using fiscal_quarter/fiscal_year properties
- [x] T010 [S0202] Implement `TrendResultParser` class - parse Neo4j records into DataPoint and TrendResult objects with chronological ordering
- [x] T011 [S0202] Implement `_quarter_to_int()` and `_int_to_quarter()` helper functions for Q1-Q4 to 1-4 conversion and sorting
- [x] T012 [S0202] Implement `calculate_qoq_comparison()` function - quarter-over-quarter delta and percent change with null handling
- [x] T013 [S0202] Implement `calculate_yoy_comparison()` function - year-over-year delta and percent change with missing quarter handling
- [x] T014 [S0202] Implement `execute_temporal_query()` async function - main entry point using ConnectionManager, builds query, executes, parses results
- [x] T015 [S0202] Implement convenience functions: `get_entity_trend()`, `compare_quarters()`, `compare_years()` wrapping execute_temporal_query

---

## Testing (5 tasks)

Unit tests and quality verification.

- [x] T016 [S0202] [P] Write unit tests for Pydantic models - TemporalQuery validation (valid/invalid parameters, edge cases)
- [x] T017 [S0202] [P] Write unit tests for TemporalQueryBuilder - Cypher generation for single quarter, quarter range, year range, with/without metric filter
- [x] T018 [S0202] [P] Write unit tests for comparison functions - QoQ/YoY with positive delta, negative delta, zero baseline, missing data, null handling
- [x] T019 [S0202] Update `src/agentic_rag/graph/__init__.py` exports and add `temporal_trend_tool` to `src/tools/rag.py` and register in `src/agent/unified_agent.py`
- [x] T020 [S0202] Run full test suite (`make test`), validate ASCII encoding, run linting (`make lint`), manual testing with knowledge graph

---

## Completion Checklist

Before marking session complete:

- [ ] All tasks marked `[x]`
- [ ] All 25+ new tests passing
- [ ] All files ASCII-encoded (no unicode)
- [ ] Black formatting applied (100 char line length)
- [ ] Ruff linting passes
- [ ] MyPy strict mode passes (full type hints)
- [ ] Temporal queries complete in under 1 second
- [ ] implementation-notes.md updated
- [ ] Ready for `/validate`

---

## Notes

### Parallelization
Tasks marked `[P]` can be worked on simultaneously:
- T004, T005, T006: Dataclass definitions are independent
- T016, T017, T018: Unit test files can be written in parallel

### Architecture Reference
Follow patterns from `src/agentic_rag/graph/multi_hop.py`:
- Dataclasses for results (PathNode, PathStep, PathResult -> DataPoint, TrendResult, ComparisonResult)
- Pydantic model for query params (MultiHopQuery -> TemporalQuery)
- Builder pattern for Cypher (MultiHopQueryBuilder -> TemporalQueryBuilder)
- Parser class (PathResultParser -> TrendResultParser)
- Async execute function (execute_multi_hop -> execute_temporal_query)

### Fiscal Quarter Ordering
Q4 2023 < Q1 2024 in chronological order. Use (year, quarter_num) tuple for sorting:
- Q1 -> 1, Q2 -> 2, Q3 -> 3, Q4 -> 4
- Sort key: (year * 10 + quarter_num) or (year, quarter_num) tuple

### Dependencies
Complete tasks in order unless marked `[P]`. Key dependencies:
- T003 must complete before T004-T007 (file must exist)
- T004-T007 must complete before T008-T015 (models needed for builder/parser)
- T008-T015 must complete before T019 (core implementation before integration)

---

## Next Steps

Run `/implement` to begin AI-led implementation.
