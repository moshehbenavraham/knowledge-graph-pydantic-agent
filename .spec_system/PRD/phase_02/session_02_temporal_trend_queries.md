# Session 02: Temporal Trend Queries

**Session ID**: `phase02-session02-temporal_trend_queries`
**Status**: Not Started
**Estimated Tasks**: ~15-18
**Estimated Duration**: 2-3 hours

---

## Objective

Enable temporal trend analysis queries using the fiscal_quarter and fiscal_year metadata from Phase 01, supporting time-series questions like "How has Apple's revenue changed over time?" and "Compare Intel Q3 2023 vs Q3 2024".

---

## Scope

### In Scope (MVP)
- Temporal aggregation query builder (by quarter, by year, by company)
- Time-series result formatting with chronological ordering
- Quarter-over-quarter and year-over-year comparison helpers
- Numeric fact aggregation over time periods
- New agent tool: `temporal_trend` for time-based queries
- Integration with numeric_facts for financial time-series
- Unit tests for temporal query logic

### Out of Scope
- Forecasting or trend prediction (analysis only)
- Custom date ranges (limited to fiscal quarters/years)
- Real-time trend updates
- Graphical trend visualization

---

## Prerequisites

- [ ] Phase 01 Session 02 completed (temporal metadata extraction)
- [ ] Phase 01 Session 04 completed (numeric fact extraction)
- [ ] All episodes have fiscal_quarter and fiscal_year properties
- [ ] Numeric facts populated on financial episodes

---

## Deliverables

1. `src/agentic_rag/graph/temporal_queries.py` - Temporal query engine
2. `TemporalQuery` Pydantic model for query parameters
3. `TrendResult` Pydantic model with time-series data
4. `temporal_trend` tool added to unified agent
5. Quarter-over-quarter comparison function
6. Year-over-year comparison function
7. Unit tests in `tests/agentic_rag/graph/test_temporal_queries.py`

---

## Success Criteria

- [ ] Time-series queries return chronologically ordered results
- [ ] Quarter-over-quarter comparisons calculate correct deltas
- [ ] Year-over-year comparisons handle missing quarters gracefully
- [ ] Numeric fact aggregation produces correct sums/averages
- [ ] Entity filtering by company works with temporal queries
- [ ] 25+ new tests covering temporal scenarios
- [ ] Temporal queries complete in under 1 second
