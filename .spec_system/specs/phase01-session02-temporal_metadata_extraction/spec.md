# Session Specification

**Session ID**: `phase01-session02-temporal_metadata_extraction`
**Phase**: 01 - Knowledge Graph Improvements
**Status**: Not Started
**Created**: 2025-12-30

---

## 1. Session Overview

This session enables temporal queries in the Agentic GraphRAG system by extracting fiscal quarter and year metadata from document filenames and populating episode nodes with temporal properties. Financial documents follow a consistent naming pattern ("YYYY QN TICKER.pdf"), which provides reliable temporal context that can be systematically extracted and stored in the knowledge graph.

The temporal dimension is critical for answering time-sensitive queries such as "What facts are from Q3 2023?" or "Show Apple mentions by quarter." With 46 multi-document temporal QnA questions identified in the requirements, this capability directly supports a core use case of the system. The temporal metadata also enables entity timeline tracking, allowing users to trace how entities evolve across fiscal quarters.

Building on Session 01's document reference population, this session adds the temporal context that transforms static entity data into a queryable timeline. The fiscal quarter/year properties on episodes, combined with entity temporal span tracking, create the foundation for sophisticated temporal reasoning in subsequent sessions.

---

## 2. Objectives

1. Parse document filenames to extract fiscal quarter, year, and company ticker with 100% accuracy for the 20-document corpus
2. Populate all 11,521 episode nodes with `fiscal_quarter`, `fiscal_year`, `document_date`, and `company` properties
3. Enable entity temporal span tracking with `first_document_date` and `last_document_date` properties
4. Create idempotent backfill script that safely updates existing graph data

---

## 3. Prerequisites

### Required Sessions
- [x] `phase01-session01-document_reference_population` - Provides document_refs on entities, establishes filename-to-entity mapping pattern

### Required Tools/Knowledge
- Neo4j Cypher for property updates and batch operations
- Python regex for filename parsing
- Understanding of existing Neo4j schema (Episode, Entity nodes)

### Environment Requirements
- Neo4j Aura connection configured (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
- Access to document corpus for filename validation
- Python 3.11+ with project dependencies installed

---

## 4. Scope

### In Scope (MVP)
- Filename parser: "2023 Q3 INTC.pdf" -> {quarter: "Q3", year: 2023, company: "Intel Corporation"}
- Episode properties: `fiscal_quarter` (str), `fiscal_year` (int), `document_date` (str YYYY-QN), `company` (str)
- Entity temporal span: `first_document_date`, `last_document_date` properties
- Backfill script with batch processing and retry logic
- Ticker-to-company-name mapping configuration
- Cypher query templates for temporal filtering
- Unit tests for parser and backfill logic

### Out of Scope (Deferred)
- Document content parsing for temporal data - *Reason: Filename pattern is reliable; content parsing adds complexity without benefit*
- Temporal visualization in UI - *Reason: Session 06 covers integration testing*
- Multi-year date range queries - *Reason: Phase 02 advanced queries*
- Non-standard fiscal calendars - *Reason: All documents use calendar quarters*

---

## 5. Technical Approach

### Architecture

The temporal metadata system consists of three components:

1. **Temporal Parser Module** (`temporal_parser.py`): Stateless parser that extracts temporal metadata from filenames using regex patterns. Returns a `TemporalMetadata` dataclass with quarter, year, company, and derived date string.

2. **Neo4j Store Integration** (`neo4j_store.py`): Updated episode creation logic that automatically populates temporal properties during ingestion. Uses the temporal parser to extract metadata from source document names.

3. **Backfill Script** (`backfill_temporal_metadata.py`): Idempotent batch processor that updates existing episodes with temporal metadata. Processes in batches of 500 with retry logic for connection stability.

### Design Patterns
- **Strategy Pattern**: Parser returns structured metadata, allowing different extraction strategies if needed
- **Idempotent Updates**: Backfill uses MERGE/SET pattern - safe to re-run without duplicating data
- **Configuration-Driven**: Ticker mapping in settings allows easy extension for new companies

### Technology Stack
- Python 3.11+ with dataclasses for structured metadata
- Neo4j Python driver for graph operations
- Regular expressions for filename parsing
- structlog for operation logging
- pytest for unit testing

---

## 6. Deliverables

### Files to Create
| File | Purpose | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/graph/temporal_parser.py` | Filename parser with TemporalMetadata dataclass | ~120 |
| `scripts/backfill_temporal_metadata.py` | Idempotent batch backfill script | ~200 |
| `tests/rag_pipeline/test_temporal_metadata.py` | Unit tests for parser and integration | ~250 |

### Files to Modify
| File | Changes | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/graph/neo4j_store.py` | Add temporal properties to episode creation | ~40 |
| `src/config/settings.py` | Add TICKER_TO_COMPANY_MAP setting | ~20 |
| `src/agentic_rag/graph/__init__.py` | Export temporal_parser module | ~5 |

---

## 7. Success Criteria

### Functional Requirements
- [ ] Filename parser correctly extracts metadata from all 20 corpus documents
- [ ] All 11,521 episodes have fiscal_quarter and fiscal_year properties
- [ ] Query "MATCH (e:Episode) WHERE e.fiscal_quarter = 'Q3' RETURN count(e)" returns correct count
- [ ] Entity temporal spans reflect first/last document dates
- [ ] Edge cases (malformed filenames) return null values, not errors

### Testing Requirements
- [ ] Unit tests for filename parser (15+ test cases including edge cases)
- [ ] Integration test for backfill script
- [ ] Regression tests for neo4j_store changes
- [ ] Manual testing of temporal Cypher queries

### Quality Gates
- [ ] All files ASCII-encoded with Unix LF line endings
- [ ] Code passes ruff, black, bandit checks
- [ ] Type hints on all function signatures (MyPy strict)
- [ ] Google-style docstrings on public functions
- [ ] Structured logging with context parameters

---

## 8. Implementation Notes

### Key Considerations
- Batch size of 500 episodes balances memory usage and transaction efficiency
- Connection retry logic handles Neo4j Aura intermittent timeouts
- Parser should be stateless and easily testable in isolation
- Ticker mapping covers all companies in current corpus: AAPL, MSFT, NVDA, INTC, AMD

### Potential Challenges
- **Large-scale Neo4j updates**: 11,521 episodes require batched processing to avoid memory issues. Mitigation: Process in 500-episode batches with progress logging.
- **Filename variations**: Some documents may have slight naming variations. Mitigation: Regex pattern handles common variations; fallback to null for unrecognized patterns.
- **Connection stability**: Neo4j Aura may have intermittent connection issues during long operations. Mitigation: Retry logic with exponential backoff.

### Relevant Considerations
- **[External Dependency] Neo4j Aura connection stability**: Backfill script must implement retry logic with exponential backoff for connection timeouts
- **[Architecture] Centralized configuration**: Ticker-to-company mapping uses `get_settings()` pattern, stored in Settings class
- **[Performance] Test suite execution time**: New tests should be efficient; mock Neo4j connections where possible

### ASCII Reminder
All output files must use ASCII-only characters (0-127). No emojis, special Unicode characters, or Windows line endings.

---

## 9. Testing Strategy

### Unit Tests
- Filename parser with valid patterns: "2023 Q3 INTC.pdf", "2024 Q1 AAPL.pdf"
- Edge cases: lowercase tickers, extra spaces, missing components
- TemporalMetadata dataclass validation
- Ticker-to-company-name mapping resolution

### Integration Tests
- Backfill script execution on test Neo4j instance
- Episode property verification after backfill
- Entity temporal span calculation accuracy

### Manual Testing
- Run Cypher query for Q3 2023 episodes, verify count matches expected
- Query entity with known temporal span, verify first/last dates
- Execute backfill twice, verify idempotency (no duplicates)

### Edge Cases
- Filename without year: "Q3 INTC.pdf" -> returns null values
- Unknown ticker: "2023 Q3 UNKNOWN.pdf" -> company = null, other fields populated
- Malformed quarter: "2023 Q5 INTC.pdf" -> returns null values
- Empty filename: "" -> returns null values gracefully

---

## 10. Dependencies

### External Libraries
- neo4j (Python driver): existing version in pyproject.toml
- structlog: existing version for logging
- pytest, pytest-asyncio: existing for testing

### Other Sessions
- **Depends on**: `phase01-session01-document_reference_population` (document_refs structure)
- **Depended by**: `phase01-session03-entity_deduplication` (temporal context helps identify cross-quarter duplicates)

---

## Next Steps

Run `/tasks` to generate the implementation task checklist.
