# Session 01: Document Reference Population

**Session ID**: `phase01-session01-document_reference_population`
**Status**: Not Started
**Estimated Tasks**: ~12-15
**Estimated Duration**: 2-3 hours

---

## Objective

Enable cross-document entity queries by populating the `document_refs` property on all entities, allowing queries like "Which entities are mentioned in multiple documents?" and "What entities appear in INTC reports?"

---

## Scope

### In Scope (MVP)
- Update `add_entities()` in `neo4j_store.py` to populate `document_refs` from chunk metadata
- Create `scripts/backfill_document_refs.py` for existing entities
- Add document metadata to entities (filename, company, quarter, year, mention_count)
- Create Cypher queries for cross-document entity lookups
- Add unit tests for document reference functionality

### Out of Scope
- Temporal metadata extraction (Session 02)
- Entity deduplication (Session 03)
- UI visualization of document references
- Real-time document reference updates during streaming ingestion

---

## Prerequisites

- [ ] Neo4j Aura connection stable and accessible
- [ ] PostgreSQL contains chunk-to-document mappings
- [ ] Existing entities accessible via Cypher queries
- [ ] Document filenames available in chunk metadata

---

## Deliverables

1. Updated `add_entities()` method in `src/agentic_rag/graph/neo4j_store.py`
2. Backfill script `scripts/backfill_document_refs.py` (idempotent, resumable)
3. Cypher queries for cross-document entity lookups
4. Unit tests in `tests/rag_pipeline/test_document_refs.py`
5. Documentation updates in CLAUDE.md

---

## Success Criteria

- [ ] 100% of entities have populated `document_refs` property
- [ ] Cross-document queries return correct results (verified with test queries)
- [ ] Backfill script completes without errors on full corpus
- [ ] Backfill script is idempotent (safe to run multiple times)
- [ ] New unit tests pass (target: 10+ tests)
- [ ] Existing tests still pass (1,113 tests)
- [ ] No performance regression on entity queries (< 500ms)
