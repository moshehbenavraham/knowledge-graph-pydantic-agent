# Session Specification

**Session ID**: `phase01-session06-type_hierarchy_and_testing`
**Phase**: 01 - Knowledge Graph Improvements
**Status**: Not Started
**Created**: 2025-12-30

---

## 1. Session Overview

This is the final session of Phase 01 (Knowledge Graph Improvements). It adds semantic entity type grouping through a type hierarchy system that enables hierarchical queries (e.g., "all organizations" includes companies, departments, and subsidiaries). This capability transforms entity searches from exact type matching to semantic category matching.

More critically, this session serves as the validation gate for all Phase 01 improvements. We will create a comprehensive test suite covering document references, temporal metadata, entity deduplication, numeric facts, and relationship scoring. The 46 QnA multi-document temporal questions will serve as integration tests to validate the complete knowledge graph pipeline.

Completing this session marks the end of Phase 01 and enables transition to Phase 00 (Mature/Late MVP). All foundational knowledge graph capabilities will be validated and production-ready.

---

## 2. Objectives

1. Implement type hierarchy module with semantic entity groupings (organization, financial_metric, product, person)
2. Create Cypher query templates that leverage type hierarchy for hierarchical entity searches
3. Validate all Phase 01 improvements with comprehensive unit tests (70+ new tests)
4. Benchmark query performance against targets (Multi-doc RAG < 2s, Entity lookup < 500ms)

---

## 3. Prerequisites

### Required Sessions
- [x] `phase01-session01-document_reference_population` - Provides document reference population for entities
- [x] `phase01-session02-temporal_metadata_extraction` - Provides temporal metadata parsing
- [x] `phase01-session03-entity_deduplication` - Provides entity deduplication logic
- [x] `phase01-session04-numeric_fact_extraction` - Provides numeric fact extraction
- [x] `phase01-session05-relationship_scoring` - Provides relationship confidence scoring

### Required Tools/Knowledge
- Neo4j Cypher query language
- pytest and pytest-asyncio for async testing
- Python typing and Pydantic models

### Environment Requirements
- Neo4j Aura connection (stable for performance benchmarks)
- PostgreSQL/Supabase for vector search validation
- Python 3.11+ with dev and rag dependencies installed

---

## 4. Scope

### In Scope (MVP)
- TYPE_HIERARCHY constant with semantic groupings:
  - `organization` -> company, department, subsidiary, division
  - `financial_metric` -> revenue, profit, margin, growth_rate, eps, ebitda
  - `product` -> hardware, software, service, platform
  - `person` -> executive, analyst, employee, ceo, cfo, cto
- `TypeHierarchy` class with methods: `get_subtypes()`, `get_parent_type()`, `is_subtype_of()`
- Cypher query builder for hierarchical type matching
- Type hierarchy unit tests (15+ tests)
- Phase 01 integration test suite covering all 5 previous sessions
- Performance benchmark tests with timing assertions
- QnA dataset integration tests (if dataset available)

### Out of Scope (Deferred)
- Custom type definitions per corpus - *Reason: Requires user-facing configuration UI*
- Type inference from entity context - *Reason: ML complexity beyond current scope*
- Graph visualization dashboard - *Reason: Phase 02 feature*
- Type hierarchy UI editor - *Reason: Requires frontend development*

---

## 5. Technical Approach

### Architecture

The type hierarchy will be implemented as a standalone module that integrates with the existing graph infrastructure:

```
src/agentic_rag/graph/
    __init__.py          # Updated exports
    type_hierarchy.py    # NEW: Type hierarchy implementation
    temporal_parser.py   # Existing
    numeric_parser.py    # Existing
    relationship_scoring.py  # Existing
```

The hierarchy is defined as a static mapping (no database storage) since the type categories are domain-invariant. The Cypher query builder will accept either specific types or parent types and expand them accordingly.

### Design Patterns
- **Static Registry Pattern**: Type hierarchy defined as class constants for fast lookup
- **Builder Pattern**: Cypher query construction for type-aware searches
- **Facade Pattern**: Clean API surface hiding Cypher complexity

### Technology Stack
- Python 3.11+ (typing, dataclasses)
- Neo4j driver for Cypher execution
- pytest + pytest-asyncio for async test execution
- structlog for logging

---

## 6. Deliverables

### Files to Create
| File | Purpose | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/graph/type_hierarchy.py` | Type hierarchy implementation with subtypes, parent lookup, Cypher builder | ~150 |
| `tests/rag_pipeline/test_type_hierarchy.py` | Unit tests for type hierarchy module | ~200 |
| `tests/rag_pipeline/test_phase01_integration.py` | Integration tests for all Phase 01 components | ~300 |
| `tests/rag_pipeline/test_performance_benchmarks.py` | Performance timing tests with assertions | ~150 |

### Files to Modify
| File | Changes | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/graph/__init__.py` | Export TypeHierarchy class | ~5 |
| `src/agentic_rag/search/hybrid_search.py` | Integrate type hierarchy in entity queries | ~30 |
| `CLAUDE.md` | Document type hierarchy usage patterns | ~40 |

---

## 7. Success Criteria

### Functional Requirements
- [ ] `TypeHierarchy.get_subtypes("organization")` returns `["company", "department", "subsidiary", "division"]`
- [ ] `TypeHierarchy.is_subtype_of("company", "organization")` returns `True`
- [ ] `TypeHierarchy.get_parent_type("revenue")` returns `"financial_metric"`
- [ ] Cypher query builder generates valid hierarchical type matching queries
- [ ] Type hierarchy queries return entities of all subtypes when parent type specified

### Testing Requirements
- [ ] Type hierarchy unit tests written and passing (15+ tests)
- [ ] Phase 01 integration tests passing (all 5 session components)
- [ ] Performance benchmark tests passing (< 2s multi-doc, < 500ms entity lookup)
- [ ] All existing 1,113 tests still passing
- [ ] 75% minimum test coverage maintained

### Quality Gates
- [ ] All files ASCII-encoded with Unix LF line endings
- [ ] Code follows project conventions (CONVENTIONS.md)
- [ ] No new Bandit security warnings
- [ ] Full type hints with MyPy strict mode passing
- [ ] Structured logging with context parameters

---

## 8. Implementation Notes

### Key Considerations
- Type hierarchy is static - no runtime modifications needed
- Subtypes are case-insensitive for matching flexibility
- Parent type lookup should handle unknown types gracefully (return None)
- Cypher queries must use parameterized values to prevent injection

### Potential Challenges
- **Neo4j connection stability**: Performance benchmarks require consistent connection; use connection pooling and retries
- **Test execution time**: Adding 70+ tests to existing 1,113 may push suite to 10+ minutes; consider pytest-xdist for parallelization
- **QnA dataset format**: May need parsing/normalization before use in integration tests

### Relevant Considerations
- **[Architecture]** Centralized configuration: Use `get_settings()` for any configuration needs, never `os.getenv()`
- **[Performance]** Test suite timeout: Use generous timeouts (15+ minutes) when running full suite
- **[External]** Neo4j Aura: Cloud-hosted connection may have variable latency; benchmark tests should allow for variance
- **[Lesson]** Async patterns: All I/O operations must be async; use `asyncio.gather` for parallel test setup

### ASCII Reminder
All output files must use ASCII-only characters (0-127). No emojis, no unicode special characters.

---

## 9. Testing Strategy

### Unit Tests
- TypeHierarchy class instantiation and configuration
- `get_subtypes()` for all parent types (organization, financial_metric, product, person)
- `get_parent_type()` for known and unknown subtypes
- `is_subtype_of()` relationship validation
- Case-insensitivity testing
- Edge cases: empty strings, None values, unknown types

### Integration Tests
- Document reference population end-to-end
- Temporal metadata extraction accuracy
- Entity deduplication merge behavior
- Numeric fact extraction precision
- Relationship scoring confidence values
- Type hierarchy query expansion in search pipeline

### Performance Tests
- Multi-document RAG query latency (< 2 seconds)
- Entity lookup latency (< 500 milliseconds)
- Type hierarchy expansion overhead (< 10ms)
- Concurrent query handling

### Edge Cases
- Unknown type passed to hierarchy methods
- Empty entity type in graph
- Circular type definitions (should not occur with static config)
- Very long type names
- Special characters in type names

---

## 10. Dependencies

### External Libraries
- neo4j: >=5.0 (async driver support)
- pytest: >=7.0 (asyncio support)
- pytest-asyncio: >=0.21 (async test fixtures)
- pytest-timeout: (test execution guards)

### Other Sessions
- **Depends on**: phase01-session01 through phase01-session05 (all must be complete)
- **Depended by**: Phase 00 sessions (enables phase transition)

---

## Next Steps

Run `/tasks` to generate the implementation task checklist.
