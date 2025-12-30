# Task Checklist

**Session ID**: `phase01-session03-entity_deduplication`
**Total Tasks**: 21
**Estimated Duration**: 7-9 hours
**Created**: 2025-12-30

---

## Legend

- `[x]` = Completed
- `[ ]` = Pending
- `[P]` = Parallelizable (can run with other [P] tasks)
- `[S0103]` = Session reference (Phase 01, Session 03)
- `TNNN` = Task ID

---

## Progress Summary

| Category | Total | Done | Remaining |
|----------|-------|------|-----------|
| Setup | 3 | 3 | 0 |
| Foundation | 6 | 6 | 0 |
| Implementation | 8 | 8 | 0 |
| Testing | 4 | 4 | 0 |
| **Total** | **21** | **21** | **0** |

---

## Setup (3 tasks)

Initial configuration and environment preparation.

- [x] T001 [S0103] Verify prerequisites: Neo4j connection, Session 01/02 complete, Python 3.11+
- [x] T002 [S0103] Add rapidfuzz dependency to pyproject.toml (`pyproject.toml`)
- [x] T003 [S0103] Create entity_resolution package directory structure (`src/agentic_rag/entity_resolution/`)

---

## Foundation (6 tasks)

Core structures and base implementations.

- [x] T004 [S0103] Create package __init__.py with public exports (`src/agentic_rag/entity_resolution/__init__.py`)
- [x] T005 [S0103] Define company suffix normalization constants and patterns (`src/agentic_rag/entity_resolution/canonical_names.py`)
- [x] T006 [S0103] Implement ticker symbol to canonical name mappings (`src/agentic_rag/entity_resolution/canonical_names.py`)
- [x] T007 [S0103] Implement normalize_entity_name() function with suffix stripping (`src/agentic_rag/entity_resolution/canonical_names.py`)
- [x] T008 [S0103] Create merge history data models with Pydantic (`src/agentic_rag/entity_resolution/merge_history.py`)
- [x] T009 [S0103] Implement merge history logging and retrieval functions (`src/agentic_rag/entity_resolution/merge_history.py`)

---

## Implementation (8 tasks)

Main feature implementation.

- [x] T010 [S0103] Implement exact match pass (normalized string comparison) (`src/agentic_rag/entity_resolution/deduplication.py`)
- [x] T011 [S0103] Implement fuzzy match pass with rapidfuzz (90% threshold) (`src/agentic_rag/entity_resolution/deduplication.py`)
- [x] T012 [S0103] Implement context-based match pass using document_refs (`src/agentic_rag/entity_resolution/deduplication.py`)
- [x] T013 [S0103] Create EntityResolver facade combining all passes (`src/agentic_rag/entity_resolution/deduplication.py`)
- [x] T014 [S0103] Build merge script with dry-run mode (`scripts/merge_duplicate_entities.py`)
- [x] T015 [S0103] Add interactive and batch modes to merge script (`scripts/merge_duplicate_entities.py`)
- [x] T016 [S0103] Implement relationship transfer logic with rollback (`scripts/merge_duplicate_entities.py`)
- [x] T017 [S0103] Integrate canonical name normalization into ingestion pipeline (`src/agentic_rag/ingestion/pipeline.py`, `src/agentic_rag/ingestion/knowledge_extractor.py`)

---

## Testing (4 tasks)

Verification and quality assurance.

- [x] T018 [S0103] [P] Write unit tests for canonical_names.py (normalization, ticker lookup) (`tests/rag_pipeline/test_entity_deduplication.py`)
- [x] T019 [S0103] [P] Write unit tests for deduplication.py (all matching passes) (`tests/rag_pipeline/test_entity_deduplication.py`)
- [x] T020 [S0103] [P] Write unit tests for merge_history.py (logging, retrieval) (`tests/rag_pipeline/test_entity_deduplication.py`)
- [x] T021 [S0103] Run full test suite, verify no regressions, validate ASCII encoding (`make check`)

---

## Completion Checklist

Before marking session complete:

- [x] All tasks marked `[x]`
- [x] All tests passing (66 new tests)
- [x] All files ASCII-encoded (0-127 only)
- [x] implementation-notes.md updated
- [x] 75%+ test coverage maintained
- [x] Ready for `/validate`

---

## Notes

### Parallelization
Tasks T018, T019, T020 (unit test writing) can be worked on simultaneously.

### Task Timing
Target ~20-25 minutes per task.

### Dependencies
- T001-T003 must complete before T004+
- T004-T009 (Foundation) must complete before T010+ (Implementation)
- T010-T013 must complete before T014-T016 (merge script needs deduplication engine)
- T017 (pipeline integration) can start after T007 (normalization function)
- T018-T020 can start after their respective modules are complete

### Key Technical Notes
- Merge operations must be atomic with rollback capability
- Exclude generic terms ("The Company", "Management", "Board") from fuzzy matching
- Use batch operations to avoid N+1 queries on 5,057 entities
- All Cypher operations need retry logic with exponential backoff

### Ticker Symbol Examples
```
AAPL -> Apple Inc.
INTC -> Intel Corporation
MSFT -> Microsoft Corporation
GOOGL -> Alphabet Inc.
AMZN -> Amazon.com Inc.
```

### Company Suffix Patterns
```
Inc., Inc, Incorporated
Corp., Corp, Corporation
LLC, L.L.C.
Ltd., Ltd, Limited
Co., Co, Company
```

---

## Session Complete

All 21 tasks completed successfully on 2025-12-30.
