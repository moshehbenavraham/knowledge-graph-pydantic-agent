# Session Specification

**Session ID**: `phase01-session01-document_reference_population`
**Phase**: 01 - Knowledge Graph Improvements
**Status**: Not Started
**Created**: 2025-12-30

---

## 1. Session Overview

This session transforms the knowledge graph from isolated entity storage into a document-aware knowledge base by populating the `document_refs` property on all entities. Currently, entities are created with an empty `document_refs` array in `src/agentic_rag/storage/neo4j_store.py`, leaving a critical gap in cross-document querying capabilities.

By completing this session, the system will support queries like "Which entities appear in multiple documents?", "What entities are mentioned in INTC quarterly reports?", and "Show me all entities from Q4 2024 filings." This capability is foundational for all subsequent Phase 1 sessions, as temporal metadata extraction, entity deduplication, and relationship scoring all depend on understanding which documents reference each entity.

The implementation extends the existing `add_entities()` method to extract document metadata from chunk sources, creates an idempotent backfill script for the 5,057 existing entities, and adds Cypher query patterns for cross-document analysis.

---

## 2. Objectives

1. Populate `document_refs` property on all entities during ingestion with structured metadata (filename, company, quarter, year)
2. Create idempotent backfill script that populates `document_refs` for existing 5,057 entities without data loss
3. Enable cross-document entity queries with sub-500ms response time
4. Maintain 100% backward compatibility with existing entity queries and ingestion pipeline

---

## 3. Prerequisites

### Required Sessions
- [x] Phase 00 MVP - Existing entity extraction and MENTIONED_IN relationships functional

### Required Tools/Knowledge
- Neo4j Cypher query language
- Python async patterns with neo4j-driver
- PostgreSQL chunk metadata structure
- Pydantic models for structured data

### Environment Requirements
- Neo4j Aura connection stable (NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD configured)
- PostgreSQL/Supabase accessible with chunk-to-document mappings
- Python 3.11+ with .venv activated

---

## 4. Scope

### In Scope (MVP)
- Update `add_entities()` in `neo4j_store.py` to accept and store document metadata
- Create `DocumentReference` Pydantic model with filename, company, quarter, year, mention_count
- Create `scripts/backfill_document_refs.py` with batch processing, retry logic, progress tracking
- Add 5 Cypher query patterns for cross-document entity lookups
- Unit tests covering new functionality (target: 10+ tests)
- Update CLAUDE.md with new query patterns

### Out of Scope (Deferred)
- Temporal metadata extraction (timestamps, date ranges) - *Reason: Session 02*
- Entity deduplication (merging duplicate entities) - *Reason: Session 03*
- UI visualization of document references - *Reason: Not in Phase 1*
- Real-time streaming updates during ingestion - *Reason: MVP focuses on batch*

---

## 5. Technical Approach

### Architecture

The solution adds a document metadata layer between chunk ingestion and entity storage:

```
Chunk Metadata (PostgreSQL) --> DocumentReference Model --> Entity.document_refs (Neo4j)
```

Document metadata is extracted from chunk source paths and metadata fields, then stored as a list of structured objects on each entity node.

### Design Patterns
- **Pydantic Models**: Structured validation for DocumentReference data
- **Idempotent Operations**: Backfill script safe to run multiple times without duplication
- **Batch Processing**: Process entities in batches of 100 to avoid Neo4j timeouts
- **Async/Await**: All database operations use async patterns per CONVENTIONS.md

### Technology Stack
- Neo4j 5.x (Aura) with Cypher queries
- Python 3.11+ with neo4j-driver (async)
- Pydantic 2.x for data validation
- structlog for structured logging

---

## 6. Deliverables

### Files to Create
| File | Purpose | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/models/document_reference.py` | DocumentReference Pydantic model | ~40 |
| `scripts/backfill_document_refs.py` | Idempotent backfill script | ~200 |
| `tests/rag_pipeline/test_document_refs.py` | Unit tests for document refs | ~250 |

### Files to Modify
| File | Changes | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/storage/neo4j_store.py` | Update add_entities() to accept document_metadata param, populate document_refs | ~50 |
| `src/agentic_rag/ingestion/pipeline.py` | Extract document metadata from chunks, pass to add_entities() | ~30 |
| `CLAUDE.md` | Add cross-document query patterns documentation | ~20 |

---

## 7. Success Criteria

### Functional Requirements
- [ ] `add_entities()` accepts optional `document_metadata` parameter
- [ ] New entities created with populated `document_refs` property
- [ ] Existing entities (on MATCH) append new document refs without duplication
- [ ] Backfill script processes all 5,057 entities without errors
- [ ] Cross-document queries return correct entity sets

### Testing Requirements
- [ ] Unit tests for DocumentReference model validation
- [ ] Unit tests for add_entities() with document metadata
- [ ] Unit tests for backfill script batch processing
- [ ] Integration test for end-to-end document reference population
- [ ] Manual testing with sample Cypher queries

### Quality Gates
- [ ] All files ASCII-encoded (0-127 characters only)
- [ ] Unix LF line endings
- [ ] Code follows CONVENTIONS.md (type hints, docstrings, structlog)
- [ ] Passes ruff, black, mypy, bandit checks
- [ ] Existing 1,113 tests still pass
- [ ] New tests achieve >90% coverage of new code

---

## 8. Implementation Notes

### Key Considerations
- Chunk metadata structure varies by source (file upload vs web scrape vs API)
- Document filenames may contain special characters requiring sanitization
- Company/quarter/year extraction uses heuristics (INTC_Q4_2024.pdf pattern)
- Neo4j list property updates require careful CASE expressions to avoid duplicates

### Potential Challenges
- **5,057 entity backfill timeout**: Mitigate with batch processing (100 entities/batch) and retry logic
- **Missing document metadata in chunks**: Gracefully handle with default values, log warnings
- **Neo4j connection stability**: Implement exponential backoff retry (3 attempts)
- **Performance regression**: Monitor query latency, add index on document_refs if needed

### Relevant Considerations
<!-- From CONSIDERATIONS.md -->
- [External Dependency] **Neo4j Aura connection stability**: Implement retry logic with exponential backoff in backfill script
- [External Dependency] **Supabase API rate limits**: Batch chunk metadata queries (50 per request)
- [Architecture] **Unified agent principle**: Extend neo4j_store.py, do not create new store implementations
- [What Worked] **Structured logging with structlog**: Add detailed progress logging to backfill script

### ASCII Reminder
All output files must use ASCII-only characters (0-127). No emojis, no Unicode, no special characters.

---

## 9. Testing Strategy

### Unit Tests
- DocumentReference model validation (valid/invalid inputs)
- add_entities() with document_metadata parameter
- add_entities() without document_metadata (backward compatibility)
- Document ref deduplication logic (same doc mentioned twice)
- Batch processing edge cases (empty batch, single entity, max batch)

### Integration Tests
- Full ingestion pipeline with document metadata extraction
- Backfill script against test Neo4j instance
- Cross-document query execution and result validation

### Manual Testing
- Run backfill script on dev environment
- Execute sample Cypher queries:
  - `MATCH (e:Entity) WHERE size(e.document_refs) > 1 RETURN e.name, size(e.document_refs) as doc_count`
  - `MATCH (e:Entity) WHERE ANY(d IN e.document_refs WHERE d.company = 'INTC') RETURN e.name`
- Verify query latency < 500ms

### Edge Cases
- Entity with no chunk metadata (orphaned entity)
- Chunk with malformed filename (no company/quarter pattern)
- Entity mentioned 100+ times in same document (mention_count aggregation)
- Unicode characters in document filenames (sanitization)

---

## 10. Dependencies

### External Libraries
- neo4j-driver: 5.x (async driver for Neo4j)
- pydantic: 2.x (model validation)
- structlog: 24.x (structured logging)
- asyncio: stdlib (async patterns)

### Other Sessions
- **Depends on**: None (foundational session)
- **Depended by**: Session 02 (Temporal Metadata), Session 03 (Entity Deduplication), Session 04 (Numeric Facts), Session 05 (Relationship Scoring), Session 06 (Type Hierarchy)

---

## Cypher Query Patterns (Reference)

```cypher
-- Entities mentioned in multiple documents
MATCH (e:Entity)
WHERE size(e.document_refs) > 1
RETURN e.name, e.type, size(e.document_refs) as doc_count
ORDER BY doc_count DESC
LIMIT 20

-- Entities from a specific company
MATCH (e:Entity)
WHERE ANY(d IN e.document_refs WHERE d.company = 'INTC')
RETURN e.name, e.type, e.mention_count

-- Entities from Q4 2024 filings
MATCH (e:Entity)
WHERE ANY(d IN e.document_refs WHERE d.quarter = 'Q4' AND d.year = 2024)
RETURN e.name, e.type

-- Cross-document entity co-occurrence
MATCH (e1:Entity), (e2:Entity)
WHERE e1 <> e2
  AND ANY(d1 IN e1.document_refs WHERE ANY(d2 IN e2.document_refs WHERE d1.filename = d2.filename))
RETURN e1.name, e2.name,
  [d IN e1.document_refs WHERE ANY(d2 IN e2.document_refs WHERE d.filename = d2.filename)] as shared_docs

-- Document reference statistics
MATCH (e:Entity)
RETURN
  count(e) as total_entities,
  avg(size(e.document_refs)) as avg_docs_per_entity,
  max(size(e.document_refs)) as max_docs
```

---

## Next Steps

Run `/tasks` to generate the implementation task checklist.
