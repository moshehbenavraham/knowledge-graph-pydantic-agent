# Task Checklist

**Session ID**: `phase01-session01-document_reference_population`
**Total Tasks**: 20
**Estimated Duration**: 6-8 hours
**Created**: 2025-12-30

---

## Legend

- `[x]` = Completed
- `[ ]` = Pending
- `[P]` = Parallelizable (can run with other [P] tasks)
- `[S0101]` = Session reference (Phase 01, Session 01)
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

- [x] T001 [S0101] Verify prerequisites met - Neo4j connection, PostgreSQL access, Python 3.11+ venv
- [x] T002 [S0101] Read existing neo4j_store.py and pipeline.py to understand current implementation
- [x] T003 [S0101] Create directory structure for new files (`src/agentic_rag/models/` if needed)

---

## Foundation (5 tasks)

Core structures and base implementations.

- [x] T004 [S0101] Create DocumentReference Pydantic model (`src/agentic_rag/models/document_reference.py`)
- [x] T005 [S0101] Add model exports to models __init__.py if applicable
- [x] T006 [S0101] Define type hints for add_entities() document_metadata parameter (`src/agentic_rag/storage/neo4j_store.py`)
- [x] T007 [S0101] [P] Create document metadata extraction helper function (`src/agentic_rag/ingestion/pipeline.py`)
- [x] T008 [S0101] [P] Create backfill script skeleton with CLI interface (`scripts/backfill_document_refs.py`)

---

## Implementation (8 tasks)

Main feature implementation.

- [x] T009 [S0101] Implement document_refs population in add_entities() on CREATE (`src/agentic_rag/storage/neo4j_store.py`)
- [x] T010 [S0101] Implement document_refs append on MATCH without duplication (`src/agentic_rag/storage/neo4j_store.py`)
- [x] T011 [S0101] Integrate document metadata extraction into ingestion pipeline (`src/agentic_rag/ingestion/pipeline.py`)
- [x] T012 [S0101] Implement backfill batch processing with configurable batch size (`scripts/backfill_document_refs.py`)
- [x] T013 [S0101] Add retry logic with exponential backoff to backfill script (`scripts/backfill_document_refs.py`)
- [x] T014 [S0101] Add progress tracking and structured logging to backfill script (`scripts/backfill_document_refs.py`)
- [x] T015 [S0101] Add idempotency checks to prevent duplicate document refs in backfill (`scripts/backfill_document_refs.py`)
- [x] T016 [S0101] Add error handling and graceful degradation for missing metadata (`src/agentic_rag/storage/neo4j_store.py`)

---

## Testing (4 tasks)

Verification and quality assurance.

- [x] T017 [S0101] [P] Write unit tests for DocumentReference model and add_entities() (`tests/rag_pipeline/test_document_refs.py`)
- [x] T018 [S0101] [P] Write unit tests for backfill script batch processing and idempotency (`tests/rag_pipeline/test_document_refs.py`)
- [x] T019 [S0101] Run full test suite, lint checks (ruff, black, mypy, bandit), and verify ASCII encoding
- [x] T020 [S0101] Update CLAUDE.md with cross-document Cypher query patterns (`CLAUDE.md`)

---

## Completion Checklist

Before marking session complete:

- [ ] All tasks marked `[x]`
- [ ] All 1,113+ tests passing
- [ ] All files ASCII-encoded (0-127 characters only)
- [ ] Unix LF line endings on all files
- [ ] ruff, black, mypy, bandit checks pass
- [ ] New tests achieve >90% coverage of new code
- [ ] implementation-notes.md updated
- [ ] Ready for `/validate`

---

## Notes

### Parallelization
Tasks marked `[P]` can be worked on simultaneously:
- T007 and T008 (metadata helper and backfill skeleton)
- T017 and T018 (unit test files)

### Task Timing
Target ~20-25 minutes per task.

### Dependencies
- T004 must complete before T006, T007, T009
- T006 must complete before T009, T010
- T009 must complete before T010
- T011 depends on T007, T009
- T012-T015 depend on T008
- T017-T018 depend on T009-T016
- T019 depends on all implementation and test tasks
- T020 can run in parallel with T19

### Key Files
| File | Action | Tasks |
|------|--------|-------|
| `src/agentic_rag/models/document_reference.py` | CREATE | T004, T005 |
| `src/agentic_rag/storage/neo4j_store.py` | MODIFY | T006, T009, T010, T016 |
| `src/agentic_rag/ingestion/pipeline.py` | MODIFY | T007, T011 |
| `scripts/backfill_document_refs.py` | CREATE | T008, T012-T015 |
| `tests/rag_pipeline/test_document_refs.py` | CREATE | T017, T018 |
| `CLAUDE.md` | MODIFY | T020 |

### Quality Reminders
- Use structlog for all logging (no print statements)
- Type hints required on all function signatures
- Google-style docstrings for all public functions
- No emojis, no Unicode - ASCII only (0-127)

---

## Next Steps

Run `/implement` to begin AI-led implementation.
