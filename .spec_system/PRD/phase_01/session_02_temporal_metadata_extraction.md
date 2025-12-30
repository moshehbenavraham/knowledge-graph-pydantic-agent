# Session 02: Temporal Metadata Extraction

**Session ID**: `phase01-session02-temporal_metadata_extraction`
**Status**: Not Started
**Estimated Tasks**: ~15-18
**Estimated Duration**: 3-4 hours

---

## Objective

Enable temporal queries by extracting fiscal quarter/year from document filenames and populating episode properties, allowing queries like "What facts are from Q3 2023?" and "Show Apple mentions by quarter."

---

## Scope

### In Scope (MVP)
- Parse document filenames: "2023 Q3 INTC.pdf" -> {quarter: Q3, year: 2023, company: Intel}
- Add episode properties: `fiscal_quarter`, `fiscal_year`, `document_date`, `company`
- Update entity temporal span tracking: `first_document_date`, `last_document_date`
- Create backfill script `scripts/backfill_temporal_metadata.py`
- Add Cypher queries for temporal filtering
- Handle edge cases (missing filenames, malformed patterns)

### Out of Scope
- Document content parsing for temporal data (fallback for edge cases only)
- Temporal visualization in UI
- Date range queries spanning multiple fiscal years
- Non-standard fiscal calendars (all documents use calendar quarters)

---

## Prerequisites

- [ ] Session 01 completed (document_refs populated)
- [ ] Document filenames follow pattern: "YYYY QN TICKER.pdf"
- [ ] Episode nodes accessible with chunk references
- [ ] Company ticker-to-name mapping available

---

## Deliverables

1. Filename parser in `src/agentic_rag/graph/temporal_parser.py`
2. Updated episode creation logic in `neo4j_store.py`
3. Backfill script `scripts/backfill_temporal_metadata.py` (idempotent)
4. Cypher queries for temporal filtering
5. Company ticker-to-name mapping configuration
6. Unit tests in `tests/rag_pipeline/test_temporal_metadata.py`
7. Documentation updates

---

## Success Criteria

- [ ] All episodes have `fiscal_quarter` and `fiscal_year` properties
- [ ] Queries like "Facts from Q3 2023" return correct results
- [ ] Entity timeline queries work across quarters
- [ ] Filename parser handles all 20 documents in corpus
- [ ] Edge cases handled gracefully (fallback to null, not error)
- [ ] Backfill script completes without errors
- [ ] New unit tests pass (target: 15+ tests)
- [ ] Existing tests still pass
