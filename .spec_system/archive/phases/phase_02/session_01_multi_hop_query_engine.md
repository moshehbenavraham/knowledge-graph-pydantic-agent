# Session 01: Multi-hop Query Engine

**Session ID**: `phase02-session01-multi_hop_query_engine`
**Status**: Not Started
**Estimated Tasks**: ~18-22
**Estimated Duration**: 3-4 hours

---

## Objective

Enable multi-hop reasoning queries that traverse multiple relationships in the knowledge graph, supporting patterns like "Company -> Acquisition -> Product" and "Executive -> Company -> Revenue".

---

## Scope

### In Scope (MVP)
- Multi-hop Cypher query builder with configurable depth (1-3 hops)
- Path traversal with relationship type filtering
- Relationship strength filtering (minimum threshold)
- Result ranking by path strength (product of relationship scores)
- New agent tool: `graph_traverse` for multi-hop queries
- Path result formatting with intermediate nodes
- Unit tests for query builder and traversal logic

### Out of Scope
- Visualization of paths (deferred to future phase)
- Arbitrary depth traversal (limited to 3 hops for performance)
- Weighted graph shortest path algorithms
- Real-time path updates during ingestion

---

## Prerequisites

- [ ] Phase 01 completed with relationship scoring operational
- [ ] Neo4j graph accessible with 18,195+ relationships
- [ ] Relationship strength scores populated (0.0-1.0)
- [ ] Type hierarchy functional for entity filtering

---

## Deliverables

1. `src/agentic_rag/graph/multi_hop.py` - Multi-hop query engine
2. `MultiHopQuery` Pydantic model for query parameters
3. `PathResult` Pydantic model for traversal results
4. `graph_traverse` tool added to unified agent
5. Integration with existing graph_search.py
6. Unit tests in `tests/agentic_rag/graph/test_multi_hop.py`
7. Documentation in CLAUDE.md for multi-hop query patterns

---

## Success Criteria

- [ ] 2-hop queries return correct paths (entity -> relationship -> entity -> relationship -> entity)
- [ ] 3-hop queries complete in under 2 seconds
- [ ] Relationship strength filtering excludes weak paths (< 0.3 threshold)
- [ ] Path ranking correctly orders by cumulative strength
- [ ] Type filtering limits traversal to specified entity types
- [ ] 30+ new tests covering multi-hop scenarios
- [ ] No performance regression in existing search operations
