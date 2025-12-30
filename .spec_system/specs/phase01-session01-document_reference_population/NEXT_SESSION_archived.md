# NEXT_SESSION.md

## Session Recommendation

**Generated**: 2025-12-30
**Project State**: Phase 01 - Knowledge Graph Improvements
**Completed Sessions**: 0

---

## Recommended Next Session

**Session ID**: `phase01-session01-document_reference_population`
**Session Name**: Document Reference Population
**Estimated Duration**: 2-3 hours
**Estimated Tasks**: 12-15

---

## Why This Session Next?

### Prerequisites Met
- [x] Neo4j Aura connection stable and accessible (existing infrastructure)
- [x] PostgreSQL contains chunk-to-document mappings (existing data model)
- [x] Existing entities accessible via Cypher queries (5,057 entities available)
- [x] Document filenames available in chunk metadata (corpus ingested)

### Dependencies
- **Builds on**: Existing entity extraction and MENTIONED_IN relationships (MVP complete)
- **Enables**: Session 02 (Temporal Metadata), Session 03 (Entity Deduplication), and all subsequent Phase 1 sessions

### Project Progression
Phase 00 (Mature/Late MVP) has no defined sessions yet. Phase 01 has 6 well-specified sessions ready for implementation. Document Reference Population is the foundational session that enables cross-document entity queries - a prerequisite for temporal analysis, deduplication, and all subsequent improvements. Starting here establishes the document-entity linkage that all other Phase 1 features depend on.

---

## Session Overview

### Objective
Enable cross-document entity queries by populating the `document_refs` property on all entities, allowing queries like "Which entities are mentioned in multiple documents?" and "What entities appear in INTC reports?"

### Key Deliverables
1. Updated `add_entities()` method in `src/agentic_rag/graph/neo4j_store.py`
2. Backfill script `scripts/backfill_document_refs.py` (idempotent, resumable)
3. Cypher queries for cross-document entity lookups
4. Unit tests in `tests/rag_pipeline/test_document_refs.py`
5. Documentation updates in CLAUDE.md

### Scope Summary
- **In Scope (MVP)**: Update add_entities() to populate document_refs, create backfill script, add document metadata (filename, company, quarter, year, mention_count), create Cypher queries, add unit tests
- **Out of Scope**: Temporal metadata extraction (Session 02), entity deduplication (Session 03), UI visualization, real-time streaming updates

---

## Technical Considerations

### Technologies/Patterns
- Neo4j Cypher queries for graph updates
- Python async patterns for database operations
- Idempotent script design for safe re-runs
- Pydantic models for structured metadata

### Potential Challenges
- Ensuring backfill script handles 5,057 entities without timeouts
- Maintaining query performance (< 500ms) with new property
- Handling missing or malformed document metadata in chunks
- Neo4j connection stability during long-running backfill

### Relevant Considerations
- **External Dependency**: Neo4j Aura connection stability - ensure retry logic in backfill script
- **External Dependency**: Supabase API rate limits - batch chunk metadata queries
- **Architecture**: Unified agent principle - extend existing neo4j_store.py, don't create new files
- **What Worked**: Structured logging with structlog - add detailed logging to backfill script

---

## Alternative Sessions

If this session is blocked:
1. **Phase 00 Session Definition** - Define and implement production hardening sessions if Phase 1 requirements are unclear
2. **Session 02: Temporal Metadata** - Could theoretically start in parallel if document references already partially exist

---

## Success Criteria Checklist

- [ ] 100% of entities have populated `document_refs` property
- [ ] Cross-document queries return correct results (verified with test queries)
- [ ] Backfill script completes without errors on full corpus
- [ ] Backfill script is idempotent (safe to run multiple times)
- [ ] New unit tests pass (target: 10+ tests)
- [ ] Existing tests still pass (1,113 tests)
- [ ] No performance regression on entity queries (< 500ms)

---

## Next Steps

Run `/sessionspec` to generate the formal specification.
