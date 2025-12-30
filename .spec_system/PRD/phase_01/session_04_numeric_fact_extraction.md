# Session 04: Numeric Fact Extraction

**Session ID**: `phase01-session04-numeric_fact_extraction`
**Status**: Not Started
**Estimated Tasks**: ~12-15
**Estimated Duration**: 2-3 hours

---

## Objective

Extract queryable numeric values from episode facts, enabling queries like "Find all revenue facts > $50B" and "What was Apple's Q3 2023 revenue?"

---

## Scope

### In Scope (MVP)
- Parse numeric values from episode text: "revenue was $40,665 million" -> {value: 40665000000, unit: "USD", original: "40,665 million"}
- Add `numeric_facts` property to episodes with structured data
- Support common financial formats (millions, billions, percentages)
- Create backfill script `scripts/backfill_numeric_facts.py`
- Add Cypher queries for numeric range filtering
- Handle currency symbols ($, EUR, etc.)

### Out of Scope
- LLM-based extraction (use regex patterns only for MVP)
- Non-financial numeric data (dates, counts, etc.)
- Currency conversion
- Comparison queries across entities (e.g., "Apple vs Microsoft revenue")

---

## Prerequisites

- [ ] Session 03 completed (entities deduplicated)
- [ ] Episode text accessible via Cypher queries
- [ ] Common financial patterns identified from corpus analysis

---

## Deliverables

1. Numeric parser in `src/agentic_rag/graph/numeric_parser.py`
2. Updated episode properties with `numeric_facts` structure
3. Backfill script `scripts/backfill_numeric_facts.py`
4. Cypher queries for numeric range filtering
5. Unit tests in `tests/rag_pipeline/test_numeric_facts.py`
6. Documentation for supported numeric formats

---

## Success Criteria

- [ ] Numeric facts extracted from 80%+ of financial episodes
- [ ] Queries on numeric values return correct results
- [ ] Unit normalization handles millions/billions consistently
- [ ] Currency symbols parsed correctly (USD, EUR, etc.)
- [ ] Percentages handled correctly (50% -> 0.5)
- [ ] Original text preserved alongside parsed value
- [ ] Backfill script completes without errors
- [ ] New unit tests pass (target: 15+ tests)
- [ ] Existing tests still pass
