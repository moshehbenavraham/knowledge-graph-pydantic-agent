# NEXT_SESSION.md

## Session Recommendation

**Generated**: 2025-12-30
**Project State**: Phase 01 - Knowledge Graph Improvements
**Completed Sessions**: 1

---

## Recommended Next Session

**Session ID**: `phase01-session02-temporal_metadata_extraction`
**Session Name**: Temporal Metadata Extraction
**Estimated Duration**: 3-4 hours
**Estimated Tasks**: 15-18

---

## Why This Session Next?

### Prerequisites Met
- [x] Session 01 completed (document_refs populated on all entities)
- [x] Document filenames follow pattern: "YYYY QN TICKER.pdf"
- [x] Episode nodes accessible with chunk references
- [x] Neo4j graph store operational

### Dependencies
- **Builds on**: Session 01 (Document Reference Population) - uses document metadata structure
- **Enables**: Session 03 (Entity Deduplication) - temporal context helps identify duplicates across time periods

### Project Progression
Session 02 is the natural sequential next step after Session 01. The document references populated in Session 01 provide the foundation for temporal metadata extraction. This session adds the temporal dimension (fiscal quarter, year) that unlocks temporal queries like "What facts are from Q3 2023?" - a critical capability for the 46 multi-doc temporal QnA questions identified in requirements.

---

## Session Overview

### Objective
Enable temporal queries by extracting fiscal quarter/year from document filenames and populating episode properties, allowing queries like "What facts are from Q3 2023?" and "Show Apple mentions by quarter."

### Key Deliverables
1. Filename parser in `src/agentic_rag/graph/temporal_parser.py`
2. Updated episode creation logic in `neo4j_store.py` with temporal properties
3. Backfill script `scripts/backfill_temporal_metadata.py` (idempotent)
4. Company ticker-to-name mapping configuration
5. Cypher queries for temporal filtering
6. Unit tests in `tests/rag_pipeline/test_temporal_metadata.py`

### Scope Summary
- **In Scope (MVP)**: Parse filenames, add episode properties (fiscal_quarter, fiscal_year, document_date, company), entity temporal span tracking, backfill existing data
- **Out of Scope**: Document content parsing for temporal data, temporal visualization in UI, multi-year range queries, non-standard fiscal calendars

---

## Technical Considerations

### Technologies/Patterns
- Python regex for filename parsing
- Neo4j Cypher for property updates
- Idempotent backfill pattern (safe to re-run)
- Configuration-based ticker-to-name mapping

### Potential Challenges
- Edge cases in filename parsing (variations in naming conventions)
- Large-scale Neo4j property updates (11,521 episodes to backfill)
- Maintaining consistency between new ingestion and backfill logic

### Relevant Considerations
- **[External Dependency]** Neo4j Aura connection stability: Backfill script should handle connection timeouts gracefully with retry logic
- **[Architecture]** Centralized configuration: Ticker-to-name mapping should use `get_settings()` pattern
- **[Performance]** Test suite takes ~7-10 minutes: Plan for test execution time when validating changes

---

## Alternative Sessions

If this session is blocked:
1. **Session 04: Numeric Fact Extraction** - Does not strictly require temporal metadata, could be done in parallel
2. **Session 05: Relationship Scoring** - Independent of temporal properties, could proceed separately

---

## Next Steps

Run `/sessionspec` to generate the formal specification.
