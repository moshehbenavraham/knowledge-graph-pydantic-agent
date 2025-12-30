# Task Checklist

**Session ID**: `phase01-session04-numeric_fact_extraction`
**Total Tasks**: 22
**Estimated Duration**: 7-9 hours
**Created**: 2025-12-30

---

## Legend

- `[x]` = Completed
- `[ ]` = Pending
- `[P]` = Parallelizable (can run with other [P] tasks)
- `[S0104]` = Session reference (Phase 01, Session 04)
- `TNNN` = Task ID

---

## Progress Summary

| Category | Total | Done | Remaining |
|----------|-------|------|-----------|
| Setup | 3 | 3 | 0 |
| Foundation | 5 | 5 | 0 |
| Implementation | 9 | 9 | 0 |
| Testing | 5 | 5 | 0 |
| **Total** | **22** | **22** | **0** |

---

## Setup (3 tasks)

Initial configuration and environment preparation.

- [x] T001 [S0104] Verify Neo4j connection and existing Episode schema (`src/agentic_rag/graph/`)
- [x] T002 [S0104] Review existing graph module structure and imports (`src/agentic_rag/graph/__init__.py`)
- [x] T003 [S0104] Verify tests directory structure exists (`tests/rag_pipeline/`)

---

## Foundation (5 tasks)

Core structures and base implementations.

- [x] T004 [S0104] Create NumericFact Pydantic model with all fields (`src/agentic_rag/graph/numeric_parser.py`)
- [x] T005 [S0104] [P] Define regex patterns for currency formats: $40.6B, $40,665 million (`src/agentic_rag/graph/numeric_parser.py`)
- [x] T006 [S0104] [P] Define regex patterns for plain magnitude formats: 40 billion, 40.6B (`src/agentic_rag/graph/numeric_parser.py`)
- [x] T007 [S0104] [P] Define regex patterns for percentage formats: 50%, 50 percent (`src/agentic_rag/graph/numeric_parser.py`)
- [x] T008 [S0104] Define pattern priority ordering and MAGNITUDE_MAP constants (`src/agentic_rag/graph/numeric_parser.py`)

---

## Implementation (9 tasks)

Main feature implementation.

- [x] T009 [S0104] Implement magnitude normalization function: million->1e6, billion->1e9 (`src/agentic_rag/graph/numeric_parser.py`)
- [x] T010 [S0104] Implement currency symbol to ISO code mapping function (`src/agentic_rag/graph/numeric_parser.py`)
- [x] T011 [S0104] Implement percentage handling: raw value and normalized value (`src/agentic_rag/graph/numeric_parser.py`)
- [x] T012 [S0104] Implement core parse_numeric_facts function with pattern pipeline (`src/agentic_rag/graph/numeric_parser.py`)
- [x] T013 [S0104] Implement multiple fact extraction from single text block (`src/agentic_rag/graph/numeric_parser.py`)
- [x] T014 [S0104] Add structured logging with context parameters (`src/agentic_rag/graph/numeric_parser.py`)
- [x] T015 [S0104] Update graph module __init__.py with NumericParser exports (`src/agentic_rag/graph/__init__.py`)
- [x] T016 [S0104] Create backfill script structure with CLI arguments (`scripts/backfill_numeric_facts.py`)
- [x] T017 [S0104] Implement Neo4j batch processing with transaction batching (`scripts/backfill_numeric_facts.py`)

---

## Testing (5 tasks)

Verification and quality assurance.

- [x] T018 [S0104] [P] Write unit tests for currency pattern extraction (8+ test cases) (`tests/rag_pipeline/test_numeric_facts.py`)
- [x] T019 [S0104] [P] Write unit tests for magnitude and percentage patterns (8+ test cases) (`tests/rag_pipeline/test_numeric_facts.py`)
- [x] T020 [S0104] [P] Write unit tests for edge cases: empty, malformed, multiple currencies (`tests/rag_pipeline/test_numeric_facts.py`)
- [x] T021 [S0104] Write integration tests for backfill script with mock Neo4j (`tests/rag_pipeline/test_numeric_facts.py`)
- [x] T022 [S0104] Run full test suite, validate ASCII encoding, verify all checks pass (`make check`)

---

## Completion Checklist

Before marking session complete:

- [x] All tasks marked `[x]`
- [x] All tests passing (pytest) - 54/54 tests pass
- [x] All files ASCII-encoded (no unicode)
- [x] Code quality checks pass (ruff, black, bandit)
- [x] Type hints on all functions (MyPy strict)
- [x] implementation-notes.md updated
- [x] Ready for `/validate`

---

## Notes

### Parallelization

Tasks marked `[P]` can be worked on simultaneously:
- T005, T006, T007: Regex pattern definitions are independent
- T018, T019, T020: Unit test categories are independent

### Task Timing

Target ~20-25 minutes per task.

### Dependencies

- T004 must complete before T005-T008 (model needed for patterns)
- T005-T008 must complete before T009-T013 (patterns needed for implementation)
- T012-T014 must complete before T015 (exports depend on complete module)
- T015 must complete before T016-T017 (backfill imports parser)
- T016-T017 must complete before T21 (integration tests need backfill script)

### Key Technical Details

**Regex Pattern Order** (most specific first):
1. Currency with magnitude: `$40.6B`, `$40,665 million`
2. Plain magnitude: `40 billion`, `40.6B`
3. Percentages: `50%`, `50 percent`

**Normalization Examples**:
- `$40,665 million` -> value: 40665000000, raw_value: 40665
- `50%` -> value: 0.5, raw_value: 50
- `EUR 35B` -> value: 35000000000, unit: "EUR"

**Magnitude Map**:
- million/M: 1e6
- billion/B: 1e9
- thousand/K: 1e3

---

## Next Steps

Run `/validate` to verify session completeness.
