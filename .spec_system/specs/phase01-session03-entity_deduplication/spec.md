# Session Specification

**Session ID**: `phase01-session03-entity_deduplication`
**Phase**: 01 - Knowledge Graph Improvements
**Status**: Not Started
**Created**: 2025-12-30

---

## 1. Session Overview

This session addresses the critical problem of entity fragmentation in the Neo4j knowledge graph. Currently, the graph contains 5,057 entities with many duplicates representing the same real-world entity under different names (e.g., "Apple Inc.", "Apple", "AAPL" all referring to Apple Inc.). This fragmentation degrades query accuracy, inflates graph size, and complicates relationship analysis.

The solution implements a multi-pass entity deduplication system with canonical name resolution. The system will use exact matching, fuzzy string matching (via rapidfuzz), and context-based disambiguation using document references from Session 01 and temporal metadata from Session 02. A merge script with dry-run, interactive, and batch modes ensures safe operation with full rollback capability through merge history logging.

This session is foundational for subsequent graph improvements. Clean, deduplicated entities enable accurate numeric fact extraction (Session 04), meaningful relationship scoring (Session 05), and proper type hierarchy validation (Session 06). The estimated 95%+ reduction in entities will dramatically improve query performance and result relevance.

---

## 2. Objectives

1. Create canonical name mapping infrastructure that handles company variations (Inc., Corp., LLC) and ticker symbols (AAPL -> Apple Inc.)
2. Implement multi-pass deduplication logic: exact match, fuzzy matching (90%+ threshold), and context-based disambiguation
3. Build a merge script with dry-run, interactive, and batch modes that preserves all entity relationships
4. Update the ingestion pipeline to normalize entity names using canonical mappings before graph storage

---

## 3. Prerequisites

### Required Sessions
- [x] `phase01-session01-document_reference_population` - Provides document_refs property for context-based disambiguation
- [x] `phase01-session02-temporal_metadata_extraction` - Provides temporal context for entity disambiguation

### Required Tools/Knowledge
- Neo4j Cypher query language for entity queries and relationship merging
- Python fuzzy string matching (rapidfuzz library)
- Graphiti library patterns for entity operations
- Understanding of existing entity extraction flow in ingestion pipeline

### Environment Requirements
- Neo4j Aura connection configured and accessible
- Backup/snapshot of current graph state before running merge operations
- Python 3.11+ with rapidfuzz installed

---

## 4. Scope

### In Scope (MVP)
- Canonical name mappings module with company suffix normalization
- Ticker symbol to company name mappings (configurable dictionary)
- Multi-pass deduplication: exact match -> fuzzy match -> context-based
- Merge script with three modes: dry-run, interactive, batch
- Merge history logging for rollback capability
- Ingestion pipeline integration for new entity normalization
- Relationship preservation during merges (transfer all edges to canonical)
- Unit tests for all deduplication logic (20+ tests)

### Out of Scope (Deferred)
- Automatic resolution for ambiguous cases - *Reason: Requires human judgment; defer to interactive mode*
- Real-time streaming deduplication - *Reason: Batch processing sufficient for current use case*
- Cross-company disambiguation (e.g., "Data Center") - *Reason: Requires deeper semantic analysis*
- Merge approval UI - *Reason: CLI interactive mode sufficient for MVP*

---

## 5. Technical Approach

### Architecture

The entity resolution system follows a three-tier architecture:

1. **Canonical Name Registry** (`canonical_names.py`): Static mappings for company suffixes, ticker symbols, and known aliases. Loaded at startup, used by both deduplication and ingestion.

2. **Deduplication Engine** (`deduplication.py`): Multi-pass algorithm that processes entities in order of confidence:
   - Pass 1: Exact match after normalization (strip suffixes, lowercase)
   - Pass 2: Fuzzy match using rapidfuzz (threshold: 90%+ similarity)
   - Pass 3: Context-based using document_refs company field

3. **Merge Executor** (`merge_duplicate_entities.py`): Script that applies deduplication results to Neo4j, handling relationship transfer and history logging.

### Design Patterns
- **Strategy Pattern**: Different matching strategies (exact, fuzzy, context) as interchangeable algorithms
- **Command Pattern**: Merge operations as reversible commands with history
- **Facade Pattern**: Single entry point for entity resolution used by ingestion pipeline

### Technology Stack
- Python 3.11+ (project standard)
- rapidfuzz 3.x for fuzzy string matching (faster than fuzzywuzzy)
- Neo4j Python driver for Cypher operations
- structlog for logging (project standard)
- Pydantic for data validation

---

## 6. Deliverables

### Files to Create
| File | Purpose | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/entity_resolution/__init__.py` | Package initialization, exports | ~20 |
| `src/agentic_rag/entity_resolution/canonical_names.py` | Canonical mappings and normalization functions | ~150 |
| `src/agentic_rag/entity_resolution/deduplication.py` | Multi-pass deduplication logic | ~250 |
| `src/agentic_rag/entity_resolution/merge_history.py` | Merge history logging and rollback | ~100 |
| `scripts/merge_duplicate_entities.py` | CLI script for running deduplication | ~200 |
| `tests/rag_pipeline/test_entity_deduplication.py` | Unit tests for deduplication | ~400 |

### Files to Modify
| File | Changes | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/ingestion/pipeline.py` | Add canonical name normalization before entity storage | ~30 |
| `src/agentic_rag/ingestion/entity_extractor.py` | Integrate canonical name lookup | ~20 |
| `pyproject.toml` | Add rapidfuzz dependency | ~2 |

---

## 7. Success Criteria

### Functional Requirements
- [ ] Canonical name normalization correctly handles: Inc., Corp., LLC, Ltd., Co., Corporation
- [ ] Ticker symbols map to canonical company names (AAPL -> Apple Inc., INTC -> Intel Corporation)
- [ ] Fuzzy matching identifies variations with 90%+ similarity
- [ ] Context-based matching uses document_refs.company for disambiguation
- [ ] Merge script dry-run accurately predicts all merges without side effects
- [ ] Interactive mode prompts for confirmation on each merge
- [ ] Batch mode applies all merges with progress reporting
- [ ] All relationships transfer to canonical entity without data loss

### Testing Requirements
- [ ] Unit tests for canonical_names.py (normalization, suffix removal, ticker lookup)
- [ ] Unit tests for deduplication.py (each matching pass, edge cases)
- [ ] Unit tests for merge_history.py (logging, retrieval)
- [ ] Integration test for full deduplication pipeline
- [ ] Existing tests still pass (no regressions)

### Quality Gates
- [ ] All files ASCII-encoded (0-127 characters only)
- [ ] Unix LF line endings
- [ ] Code follows project conventions (CONVENTIONS.md)
- [ ] Type hints on all functions (MyPy strict)
- [ ] Docstrings on all public functions (Google style)
- [ ] No Bandit security warnings without justification
- [ ] 75%+ test coverage maintained

---

## 8. Implementation Notes

### Key Considerations
- Entity merging must be atomic: if any relationship transfer fails, rollback the entire merge
- Preserve entity properties from the most complete/authoritative source
- Handle case where merged entity has higher mention_count than sum of sources
- Log sufficient context in merge history to enable clean rollback

### Potential Challenges
- **Relationship preservation**: Neo4j APOC merge procedures may not handle all edge cases; implement custom Cypher for relationship transfer
- **Performance at scale**: 5,057 entities with 18,195 relationships requires batch operations; avoid N+1 queries
- **Ambiguous names**: Generic terms like "The Company", "Management", "Board" should be excluded from fuzzy matching
- **Ticker conflicts**: Handle edge cases where ticker symbols overlap (e.g., historical reuse)

### Relevant Considerations
<!-- From CONSIDERATIONS.md -->
- **Neo4j Aura connection stability**: Implement retry logic with exponential backoff for all merge operations
- **Unified agent principle**: Entity resolution is a utility module, not a separate agent; integrate as tool if needed
- **Test suite performance**: Keep new tests efficient; batch assertions where possible to minimize 7-10 min baseline

### ASCII Reminder
All output files must use ASCII-only characters (0-127). No emojis, no Unicode special characters.

---

## 9. Testing Strategy

### Unit Tests
- `test_normalize_company_name()`: Verify suffix removal (Inc., Corp., LLC variations)
- `test_ticker_to_canonical()`: Verify ticker symbol lookups
- `test_exact_match_pass()`: Test exact matching after normalization
- `test_fuzzy_match_pass()`: Test fuzzy matching with various similarity thresholds
- `test_context_match_pass()`: Test document_refs-based disambiguation
- `test_merge_history_logging()`: Verify merge operations logged correctly
- `test_merge_history_retrieval()`: Verify history query functions

### Integration Tests
- `test_full_deduplication_pipeline()`: End-to-end with mock Neo4j
- `test_relationship_preservation()`: Verify all edges transfer correctly
- `test_dry_run_mode()`: Verify no side effects in dry-run

### Manual Testing
- Run dry-run on production graph, verify predicted merges are sensible
- Test interactive mode with sample merges
- Execute batch merge on test subset, verify relationships preserved
- Query deduplicated entities to confirm canonical names

### Edge Cases
- Entity with no relationships (orphan merge)
- Entity with 100+ relationships (stress test transfer)
- Circular relationships between merge candidates
- Entity name is only whitespace or punctuation
- Ticker symbol that matches a company name substring

---

## 10. Dependencies

### External Libraries
- rapidfuzz: 3.x (fuzzy string matching, faster than fuzzywuzzy)
- neo4j: existing project dependency
- structlog: existing project dependency

### Other Sessions
- **Depends on**: `phase01-session01-document_reference_population`, `phase01-session02-temporal_metadata_extraction`
- **Depended by**: `phase01-session04-numeric_fact_extraction`, `phase01-session05-relationship_scoring`, `phase01-session06-type_hierarchy_testing`

---

## Next Steps

Run `/tasks` to generate the implementation task checklist.
