# Task Checklist

**Session ID**: `phase02-session03-cross_entity_comparison`
**Total Tasks**: 20
**Estimated Duration**: 6-8 hours
**Created**: 2025-12-30

---

## Legend

- `[x]` = Completed
- `[ ]` = Pending
- `[P]` = Parallelizable (can run with other [P] tasks)
- `[S0203]` = Session reference (Phase 02, Session 03)
- `TNNN` = Task ID

---

## Progress Summary

| Category | Total | Done | Remaining |
|----------|-------|------|-----------|
| Setup | 2 | 2 | 0 |
| Foundation | 6 | 6 | 0 |
| Implementation | 7 | 7 | 0 |
| Testing | 5 | 5 | 0 |
| **Total** | **20** | **20** | **0** |

---

## Setup (2 tasks)

Initial configuration and environment preparation.

- [x] T001 [S0203] Verify prerequisites met - confirm Neo4j connection, TypeHierarchy module, and NumericFact structure available
- [x] T002 [S0203] Review existing patterns in `multi_hop.py` and `temporal_trends.py` to ensure consistency

---

## Foundation (6 tasks)

Core structures and base implementations.

- [x] T003 [S0203] [P] Create `ComparisonQuery` Pydantic model with entity names, metric, time filter, limit (`src/agentic_rag/graph/entity_comparison.py`)
- [x] T004 [S0203] [P] Create `EntityMetrics` Pydantic model for individual entity metric data (`src/agentic_rag/graph/entity_comparison.py`)
- [x] T005 [S0203] [P] Create `ComparisonResult` Pydantic model for side-by-side comparison results (`src/agentic_rag/graph/entity_comparison.py`)
- [x] T006 [S0203] Implement type compatibility validation using TypeHierarchy (`src/agentic_rag/graph/entity_comparison.py`)
- [x] T007 [S0203] [P] Implement growth rate calculation helpers - absolute delta, percentage change (`src/agentic_rag/graph/entity_comparison.py`)
- [x] T008 [S0203] [P] Implement QoQ and YoY growth rate helpers with temporal metadata (`src/agentic_rag/graph/entity_comparison.py`)

---

## Implementation (7 tasks)

Main feature implementation.

- [x] T009 [S0203] Implement `ComparisonQueryBuilder` class with fluent builder pattern (`src/agentic_rag/graph/entity_comparison.py`)
- [x] T010 [S0203] Implement Cypher query generation for multi-entity numeric fact retrieval (`src/agentic_rag/graph/entity_comparison.py`)
- [x] T011 [S0203] Implement `ComparisonResultParser` for Neo4j record parsing (`src/agentic_rag/graph/entity_comparison.py`)
- [x] T012 [S0203] Implement `execute_comparison` async function with connection manager (`src/agentic_rag/graph/entity_comparison.py`)
- [x] T013 [S0203] Add ranking functionality - sort entities by metric value ascending/descending (`src/agentic_rag/graph/entity_comparison.py`)
- [x] T014 [S0203] Add `compare_entities` tool function to RAG tools (`src/tools/rag.py`)
- [x] T015 [S0203] Register `compare_entities` tool with unified agent and update exports (`src/agent/unified_agent.py`, `src/agentic_rag/graph/__init__.py`)

---

## Testing (5 tasks)

Verification and quality assurance.

- [x] T016 [S0203] [P] Write unit tests for Pydantic models - ComparisonQuery, EntityMetrics, ComparisonResult (`tests/agentic_rag/graph/test_entity_comparison.py`)
- [x] T017 [S0203] [P] Write unit tests for type compatibility validation and growth rate helpers (`tests/agentic_rag/graph/test_entity_comparison.py`)
- [x] T018 [S0203] [P] Write unit tests for ComparisonQueryBuilder Cypher generation (`tests/agentic_rag/graph/test_entity_comparison.py`)
- [x] T019 [S0203] Write integration tests with mock Neo4j session (`tests/agentic_rag/graph/test_entity_comparison.py`)
- [x] T020 [S0203] Run full test suite, validate ASCII encoding, and verify all quality gates pass

---

## Completion Checklist

Before marking session complete:

- [x] All tasks marked `[x]`
- [x] All tests passing (84 new tests - exceeds 30+ target)
- [x] All files ASCII-encoded (no unicode characters)
- [x] Unix LF line endings verified
- [x] Black formatting applied (100 char line length)
- [x] Ruff linting passes
- [x] Bandit security check passes
- [x] implementation-notes.md updated
- [x] Ready for `/validate`

---

## Notes

### Parallelization
Tasks marked `[P]` can be worked on simultaneously:
- T003, T004, T005: Pydantic models are independent
- T007, T008: Growth rate helpers are independent
- T016, T017, T018: Test categories are independent

### Task Timing
Target ~20-25 minutes per task.

### Dependencies
- T006 depends on T003 (needs ComparisonQuery model)
- T009-T013 must be sequential (builder -> query -> parser -> execute -> ranking)
- T014 depends on T012 (needs execute_comparison)
- T015 depends on T014 (needs compare_entities tool)
- T019-T020 depend on all implementation tasks

### Key Implementation Details
1. **Type Compatibility**: Use `TypeHierarchy.get_parent_type()` to validate entities share same parent type
2. **Unit Normalization**: Use `value` field from NumericFact (already normalized), not `raw_value`
3. **Entity Count**: Support 2-5 entities, validate count in ComparisonQuery
4. **Missing Data**: Return None for missing metrics, do not fail entire comparison
5. **Zero Division**: Handle zero baseline in percentage calculations gracefully

### File References
- Pattern source: `src/agentic_rag/graph/multi_hop.py` (builder pattern)
- Pattern source: `src/agentic_rag/graph/temporal_trends.py` (growth calculations)
- Type hierarchy: `src/agentic_rag/graph/type_hierarchy.py`
- Connection manager: `src/agentic_rag/graph/connection.py`

---

## Session Complete

Implementation completed on 2025-12-30.
