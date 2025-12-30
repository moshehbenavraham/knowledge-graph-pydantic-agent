# NEXT_SESSION.md

## Session Recommendation

**Generated**: 2025-12-30
**Project State**: Phase 02 - Advanced Query Engine
**Completed Sessions**: 6 (all Phase 01 sessions)

---

## Recommended Next Session

**Session ID**: `phase02-session01-multi_hop_query_engine`
**Session Name**: Multi-hop Query Engine
**Estimated Duration**: 3-4 hours
**Estimated Tasks**: 18-22

---

## Why This Session Next?

### Prerequisites Met
- [x] Phase 01 completed with relationship scoring operational (session 05)
- [x] Neo4j graph accessible with 18,195+ relationships
- [x] Relationship strength scores populated (0.0-1.0)
- [x] Type hierarchy functional for entity filtering (session 06)
- [x] All entities have document_refs (session 01)
- [x] Temporal metadata on episodes (session 02)
- [x] Entity deduplication completed (session 03)
- [x] Numeric facts extracted (session 04)

### Dependencies
- **Builds on**: All Phase 01 improvements (document refs, temporal metadata, deduplication, numeric facts, relationship scoring, type hierarchy)
- **Enables**: Sessions 02-05 of Phase 02 (temporal trends, cross-entity comparison, smart search enhancement, performance validation)

### Project Progression
Phase 01 is complete - the knowledge graph has been transformed from a disconnected entity index into a fully queryable temporal knowledge base. Phase 02 leverages these improvements to deliver advanced query capabilities. Multi-hop Query Engine is the foundational session that enables relationship traversal, which is essential for subsequent sessions:
- Temporal Trend Queries need path traversal to follow entities across time
- Cross-Entity Comparison needs multi-hop to find shared relationships
- Smart Search Enhancement integrates multi-hop as a query strategy

---

## Session Overview

### Objective
Enable multi-hop reasoning queries that traverse multiple relationships in the knowledge graph, supporting patterns like "Company -> Acquisition -> Product" and "Executive -> Company -> Revenue".

### Key Deliverables
1. `src/agentic_rag/graph/multi_hop.py` - Multi-hop query engine
2. `MultiHopQuery` Pydantic model for query parameters
3. `PathResult` Pydantic model for traversal results
4. `graph_traverse` tool added to unified agent
5. Integration with existing graph_search.py
6. Unit tests in `tests/agentic_rag/graph/test_multi_hop.py`
7. Documentation in CLAUDE.md for multi-hop query patterns

### Scope Summary
- **In Scope (MVP)**: Multi-hop Cypher query builder (1-3 hops), relationship type/strength filtering, result ranking by path strength, `graph_traverse` agent tool, unit tests
- **Out of Scope**: Path visualization, arbitrary depth traversal, weighted shortest path algorithms, real-time path updates

---

## Technical Considerations

### Technologies/Patterns
- Neo4j Cypher for multi-hop traversal queries
- Pydantic models for request/response schemas
- Python async/await for query execution
- structlog for query performance logging
- Extend existing neo4j_store.py and graph_search.py patterns

### Potential Challenges
- **Query Complexity**: Multi-hop queries may timeout for deeply connected entities - mitigate with depth limits (max 3 hops) and query planning
- **Result Relevance**: Multi-hop results may include irrelevant paths - mitigate with relationship strength filtering (>= 0.3 threshold)
- **Performance**: Complex joins could slow search - benchmark against 2-second target

### Relevant Considerations
- [P00] **Neo4j Aura connection stability**: Implement connection pooling and retry logic for complex queries
- [P00] **Unified agent principle**: Add `graph_traverse` tool to existing unified agent, do not create sub-agents
- [P00] **Centralized configuration**: All new settings via `get_settings()`, never `os.getenv()`
- [P01] **Relationship scoring**: Use strength scores (0.0-1.0) to filter and rank multi-hop paths

---

## Alternative Sessions

If this session is blocked:
1. **phase02-session02-temporal_trend_queries** - Could implement if only temporal queries needed (less dependent on multi-hop)
2. **phase02-session05-query_performance_and_validation** - Could start performance benchmarking with existing queries

---

## Next Steps

Run `/sessionspec` to generate the formal specification.
