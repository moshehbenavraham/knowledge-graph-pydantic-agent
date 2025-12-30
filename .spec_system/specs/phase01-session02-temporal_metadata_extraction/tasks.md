# Task Checklist

**Session ID**: `phase01-session02-temporal_metadata_extraction`
**Total Tasks**: 20
**Estimated Duration**: 6-8 hours
**Created**: 2025-12-30

---

## Legend

- `[x]` = Completed
- `[ ]` = Pending
- `[P]` = Parallelizable (can run with other [P] tasks)
- `[S0102]` = Session reference (Phase 01, Session 02)
- `TNNN` = Task ID

---

## Progress Summary

| Category | Total | Done | Remaining |
|----------|-------|------|-----------|
| Setup | 3 | 3 | 0 |
| Foundation | 5 | 5 | 0 |
| Implementation | 8 | 8 | 0 |
| Testing | 4 | 4 | 0 |
| **Total** | **20** | **20** | **0** |

---

## Setup (3 tasks)

Initial configuration and environment preparation.

- [x] T001 [S0102] Verify prerequisites met (Neo4j connection, Session 01 complete)
- [x] T002 [S0102] Add TICKER_TO_COMPANY_MAP setting to configuration (`src/config/settings.py`)
- [x] T003 [S0102] Create temporal_parser module file structure (`src/agentic_rag/graph/temporal_parser.py`)

---

## Foundation (5 tasks)

Core structures and base implementations.

- [x] T004 [S0102] Define TemporalMetadata dataclass with validation (`src/agentic_rag/graph/temporal_parser.py`)
- [x] T005 [S0102] Implement filename regex pattern for "YYYY QN TICKER.pdf" format (`src/agentic_rag/graph/temporal_parser.py`)
- [x] T006 [S0102] Implement parse_filename function with edge case handling (`src/agentic_rag/graph/temporal_parser.py`)
- [x] T007 [S0102] Add ticker-to-company-name resolution function (`src/agentic_rag/graph/temporal_parser.py`)
- [x] T008 [S0102] Export temporal_parser from graph module (`src/agentic_rag/graph/__init__.py`)

---

## Implementation (8 tasks)

Main feature implementation.

- [x] T009 [S0102] Update episode creation in neo4j_store to include temporal properties (`src/agentic_rag/storage/neo4j_store.py`)
- [x] T010 [S0102] Create backfill script skeleton with CLI arguments (`scripts/backfill_temporal_metadata.py`)
- [x] T011 [S0102] Implement Neo4j connection with retry logic in backfill script (`scripts/backfill_temporal_metadata.py`)
- [x] T012 [S0102] Implement batch episode fetching (500 per batch) (`scripts/backfill_temporal_metadata.py`)
- [x] T013 [S0102] Implement temporal metadata population for episodes (`scripts/backfill_temporal_metadata.py`)
- [x] T014 [S0102] Implement entity temporal span calculation (first/last document dates) (`scripts/backfill_temporal_metadata.py`)
- [x] T015 [S0102] Add progress logging and summary statistics to backfill script (`scripts/backfill_temporal_metadata.py`)
- [x] T016 [S0102] Add idempotency verification and dry-run mode (`scripts/backfill_temporal_metadata.py`)

---

## Testing (4 tasks)

Verification and quality assurance.

- [x] T017 [S0102] [P] Write unit tests for temporal parser (15+ test cases) (`tests/rag_pipeline/test_temporal_metadata.py`)
- [x] T018 [S0102] [P] Write unit tests for neo4j_store temporal integration (`tests/rag_pipeline/test_temporal_metadata.py`)
- [x] T019 [S0102] Write integration tests for backfill script (`tests/rag_pipeline/test_temporal_metadata.py`)
- [x] T020 [S0102] Run full test suite, validate ASCII encoding, lint checks

---

## Completion Checklist

Before marking session complete:

- [x] All tasks marked `[x]`
- [x] All tests passing (pytest) - 39 tests pass
- [x] All files ASCII-encoded (no Unicode/emojis)
- [x] Code quality checks pass (ruff, black, bandit)
- [x] Type hints on all functions (MyPy strict)
- [x] implementation-notes.md updated
- [x] Ready for `/validate`

---

## Notes

### Parallelization
Tasks T017 and T018 can be worked on simultaneously as they test independent components.

### Task Timing
Target ~20-25 minutes per task.

### Dependencies
- T004-T008 must complete before T009 (parser needed for neo4j_store integration)
- T003-T008 must complete before T010-T016 (parser needed for backfill script)
- T009-T016 must complete before T017-T019 (implementation needed for testing)

### Key Technical Details
- Batch size: 500 episodes per transaction
- Retry logic: Exponential backoff for Neo4j connection issues
- Ticker mapping: AAPL, MSFT, NVDA, INTC, AMD
- Target: 11,521 episodes to update

### Cypher Query Templates
```cypher
-- Verify temporal properties
MATCH (e:Episode) WHERE e.fiscal_quarter IS NOT NULL RETURN count(e)

-- Query by quarter
MATCH (e:Episode) WHERE e.fiscal_quarter = 'Q3' AND e.fiscal_year = 2023 RETURN e

-- Entity temporal span
MATCH (e:Entity) RETURN e.name, e.first_document_date, e.last_document_date
```

---

## Next Steps

Run `/implement` to begin AI-led implementation.
