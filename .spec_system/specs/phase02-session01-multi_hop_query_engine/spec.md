# Session Specification

**Session ID**: `phase02-session01-multi_hop_query_engine`
**Phase**: 02 - Advanced Query Engine
**Status**: Not Started
**Created**: 2025-12-30

---

## 1. Session Overview

This session implements a multi-hop query engine that enables relationship traversal across the knowledge graph. Currently, the system can search for entities and their immediate relationships, but lacks the ability to discover indirect connections through intermediate nodes. Multi-hop queries address patterns like "What products did companies acquired by Intel release?" (Company -> Acquisition -> Company -> Product) or "Which executives are connected through shared board memberships?" (Person -> Company -> Person).

The multi-hop engine builds directly on Phase 01's foundation: relationship strength scores (session 05) enable path quality ranking, type hierarchy (session 06) enables entity filtering during traversal, and document references (session 01) provide provenance for discovered paths. This is the first session of Phase 02 and serves as the foundation for subsequent sessions - temporal trend queries need path traversal, cross-entity comparison needs multi-hop to find shared relationships, and smart search enhancement will integrate multi-hop as a query strategy.

The implementation follows the unified agent principle by adding a new `graph_traverse` tool rather than creating a separate agent. All configuration uses centralized settings, and the query engine integrates with the existing `graph_search.py` and `neo4j_store.py` infrastructure.

---

## 2. Objectives

1. Implement a multi-hop Cypher query builder supporting 1-3 hop traversals with relationship type and strength filtering
2. Create Pydantic models (`MultiHopQuery`, `PathResult`, `PathNode`, `PathStep`) for type-safe query parameters and structured results
3. Add `graph_traverse` tool to the unified agent for multi-hop reasoning queries
4. Achieve sub-2-second response times for 3-hop queries with proper query optimization

---

## 3. Prerequisites

### Required Sessions
- [x] `phase01-session01-document_reference_population` - Provides document_refs on entities for path provenance
- [x] `phase01-session02-temporal_metadata_extraction` - Provides temporal context for path nodes
- [x] `phase01-session03-entity_deduplication` - Ensures clean entity graph without duplicates
- [x] `phase01-session04-numeric_fact_extraction` - Provides numeric facts linkable from paths
- [x] `phase01-session05-relationship_scoring` - Provides strength scores (0.0-1.0) for path ranking
- [x] `phase01-session06-type_hierarchy_and_testing` - Provides type hierarchy for entity filtering

### Required Tools/Knowledge
- Neo4j Cypher variable-length path syntax (`-[*1..3]-`)
- Pydantic model composition patterns
- asyncio for parallel query execution
- structlog for performance logging

### Environment Requirements
- Neo4j Aura database accessible with 18,195+ relationships
- Relationship strength scores populated on all edges
- Python 3.11+ with pydantic-ai installed

---

## 4. Scope

### In Scope (MVP)
- Multi-hop Cypher query builder with configurable depth (1-3 hops)
- Path traversal with relationship type filtering (include/exclude specific types)
- Relationship strength threshold filtering (default >= 0.3)
- Result ranking by cumulative path strength (product of edge scores)
- Entity type filtering using type hierarchy expansion
- Path result formatting with intermediate nodes and relationships
- `graph_traverse` agent tool with clear docstring and examples
- Unit tests for query builder, traversal logic, and path ranking

### Out of Scope (Deferred)
- Path visualization (D3.js/vis.js) - *Reason: UI enhancement, not core functionality*
- Arbitrary depth traversal beyond 3 hops - *Reason: Performance constraints, exponential complexity*
- Weighted shortest path algorithms (Dijkstra, A*) - *Reason: Requires graph algorithms library*
- Real-time path updates during ingestion - *Reason: Adds streaming complexity*
- Bidirectional path search - *Reason: Can be added later as optimization*

---

## 5. Technical Approach

### Architecture

```
User Query
    |
    v
graph_traverse tool (src/tools/rag.py)
    |
    v
MultiHopQueryBuilder (src/agentic_rag/graph/multi_hop.py)
    |-- Validates query parameters (depth, filters)
    |-- Builds parameterized Cypher query
    |-- Applies type hierarchy expansion
    v
Neo4jStore.execute_query() (existing)
    |
    v
PathResultParser
    |-- Parses Neo4j path records
    |-- Calculates cumulative path strength
    |-- Formats PathResult with nodes and steps
    v
Ranked PathResult list
```

The multi-hop module integrates with existing infrastructure:
- Uses `Neo4jStore.execute_query()` for Cypher execution
- Uses `TypeHierarchy.expand_type_filter()` for entity type filtering
- Follows the same dataclass pattern as `GraphSearchResult`

### Design Patterns
- **Builder Pattern**: `MultiHopQueryBuilder` constructs Cypher queries incrementally with optional filters
- **Strategy Pattern**: Different path ranking strategies (cumulative strength, shortest path, most recent)
- **Dataclass Models**: Immutable result structures matching existing `GraphFact`, `GraphEntity` patterns

### Technology Stack
- Neo4j Cypher with variable-length paths (`MATCH path = (a)-[*1..3]-(b)`)
- Pydantic for request/response validation
- structlog for query performance logging
- asyncio for async Neo4j driver compatibility

---

## 6. Deliverables

### Files to Create
| File | Purpose | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/graph/multi_hop.py` | Multi-hop query engine with builder pattern | ~300 |
| `tests/agentic_rag/graph/test_multi_hop.py` | Unit tests for multi-hop functionality | ~400 |

### Files to Modify
| File | Changes | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/graph/__init__.py` | Export multi-hop classes and functions | ~10 |
| `src/tools/rag.py` | Add `graph_traverse` tool function | ~60 |
| `src/agent/unified_agent.py` | Register `graph_traverse` tool | ~5 |
| `CLAUDE.md` | Document multi-hop query patterns and examples | ~40 |

---

## 7. Success Criteria

### Functional Requirements
- [ ] 1-hop queries return direct relationships between entities
- [ ] 2-hop queries return correct paths (entity -> relationship -> entity -> relationship -> entity)
- [ ] 3-hop queries complete in under 2 seconds for typical graph density
- [ ] Relationship strength filtering excludes paths with any edge below threshold (default 0.3)
- [ ] Path ranking correctly orders by cumulative strength (product of edge scores)
- [ ] Entity type filtering uses type hierarchy expansion (e.g., "organization" matches "company")
- [ ] Empty results handled gracefully with informative message

### Testing Requirements
- [ ] Unit tests for MultiHopQueryBuilder with various filter combinations
- [ ] Unit tests for path strength calculation logic
- [ ] Unit tests for PathResult parsing from Neo4j records
- [ ] Integration test with real Neo4j connection (marked for optional skip)
- [ ] Edge case tests: no results, single node, circular paths
- [ ] 30+ tests total covering multi-hop scenarios

### Quality Gates
- [ ] All files ASCII-encoded (no unicode characters)
- [ ] Unix LF line endings
- [ ] Code follows CONVENTIONS.md (type hints, docstrings, async patterns)
- [ ] MyPy strict mode passes
- [ ] Ruff linting passes
- [ ] 75% test coverage on new code
- [ ] No new Bandit security warnings

---

## 8. Implementation Notes

### Key Considerations
- Use parameterized Cypher queries to prevent injection (no string interpolation)
- Limit result set size before calculating path strength to avoid memory issues
- Log query execution time with structlog for performance monitoring
- Handle Neo4j connection errors gracefully with retry logic

### Potential Challenges
- **Query Complexity**: Multi-hop queries can timeout for highly connected entities - Mitigation: Hard limit of 3 hops, LIMIT clause, and query timeout parameter
- **Result Explosion**: 3-hop queries can return thousands of paths - Mitigation: Apply strength threshold early, limit to top 50 paths
- **Circular Paths**: Entities may connect back to themselves - Mitigation: Use Cypher's `DISTINCT` and filter self-loops

### Relevant Considerations
- [P00] **Neo4j Aura connection stability**: Implement retry logic with exponential backoff for query execution; use connection pooling from ConnectionManager
- [P00] **Unified agent principle**: Add `graph_traverse` as tool to existing super_agent, no new agent classes
- [P00] **Centralized configuration**: Any new settings (max depth, default threshold) go in Settings class
- [P01] **Relationship scoring**: Use existing strength scores for path ranking; paths with any edge < 0.3 are filtered

### ASCII Reminder
All output files must use ASCII-only characters (0-127). No unicode arrows, checkmarks, or special symbols in code.

---

## 9. Testing Strategy

### Unit Tests
- `test_multi_hop_query_builder_single_hop`: Verify 1-hop Cypher generation
- `test_multi_hop_query_builder_with_type_filter`: Verify type hierarchy expansion in query
- `test_multi_hop_query_builder_with_strength_threshold`: Verify WHERE clause for strength
- `test_path_strength_calculation`: Verify product of edge scores
- `test_path_result_parsing`: Verify Neo4j record to PathResult conversion
- `test_path_ranking_order`: Verify strongest paths ranked first

### Integration Tests
- `test_graph_traverse_tool_integration`: Full tool call with mocked Neo4j
- `test_multi_hop_with_real_graph`: Optional test with actual Neo4j (skipif no connection)

### Manual Testing
- Query "Intel -> acquired companies -> their products" and verify 2-hop paths
- Query executives connected through shared companies
- Verify UI displays paths correctly in agent response

### Edge Cases
- Empty result set (no matching paths)
- Single entity with no relationships
- Circular path (A -> B -> A)
- Path with one weak edge (below threshold)
- Query with non-existent entity type

---

## 10. Dependencies

### External Libraries
- neo4j (async driver): Already installed, version >= 5.0
- pydantic: Already installed, version >= 2.0
- structlog: Already installed, version >= 24.0

### Other Sessions
- **Depends on**: All Phase 01 sessions (completed)
- **Depended by**: phase02-session02 (temporal trends), phase02-session03 (cross-entity), phase02-session04 (smart search)

---

## Next Steps

Run `/tasks` to generate the implementation task checklist.
