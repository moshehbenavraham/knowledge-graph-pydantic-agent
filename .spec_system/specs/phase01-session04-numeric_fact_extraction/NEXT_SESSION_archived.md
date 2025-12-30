# NEXT_SESSION.md

## Session Recommendation

**Generated**: 2025-12-30
**Project State**: Phase 01 - Knowledge Graph Improvements
**Completed Sessions**: 3 of 6

---

## Recommended Next Session

**Session ID**: `phase01-session04-numeric_fact_extraction`
**Session Name**: Numeric Fact Extraction
**Estimated Duration**: 2-3 hours
**Estimated Tasks**: 12-15

---

## Why This Session Next?

### Prerequisites Met
- [x] Session 03 completed (entities deduplicated)
- [x] Episode text accessible via Cypher queries
- [x] Common financial patterns identified from corpus analysis

### Dependencies
- **Builds on**: Session 03 (Entity Deduplication) - clean, deduplicated entities enable accurate numeric fact attribution
- **Enables**: Session 05 (Relationship Scoring) - requires numeric facts for enhanced evidence-based scoring

### Project Progression
This is the natural sequential step in Phase 01. Sessions 01-03 established the foundation:
1. Document references (Session 01) - know which documents contain entities
2. Temporal metadata (Session 02) - know when facts occurred
3. Entity deduplication (Session 03) - clean entity graph

Session 04 adds the "what" - extracting queryable numeric values from episode facts. This enables financial queries like "Find all revenue facts > $50B" and "What was Apple's Q3 2023 revenue?" - core use cases for financial analysts.

---

## Session Overview

### Objective
Extract queryable numeric values from episode facts, enabling queries like "Find all revenue facts > $50B" and "What was Apple's Q3 2023 revenue?"

### Key Deliverables
1. Numeric parser in `src/agentic_rag/graph/numeric_parser.py`
2. Updated episode properties with `numeric_facts` structure
3. Backfill script `scripts/backfill_numeric_facts.py`
4. Cypher queries for numeric range filtering
5. Unit tests in `tests/rag_pipeline/test_numeric_facts.py`
6. Documentation for supported numeric formats

### Scope Summary
- **In Scope (MVP)**: Parse numeric values from episode text, add `numeric_facts` property to episodes, support common financial formats (millions, billions, percentages), handle currency symbols ($, EUR)
- **Out of Scope**: LLM-based extraction (regex only for MVP), non-financial numeric data, currency conversion, cross-entity comparison queries

---

## Technical Considerations

### Technologies/Patterns
- Regex-based parsing for numeric extraction
- Neo4j property updates for storing structured numeric facts
- JSON-like structure for numeric_facts property
- Unit normalization (millions -> actual value)

### Potential Challenges
- **Pattern coverage**: Financial text has many formats ("$40.6B", "40,665 million", "40.6 billion USD")
- **Unit normalization**: Converting millions/billions consistently
- **Currency handling**: Multiple symbols and formats
- **Percentages**: Handling 50% as 0.5 vs 50

### Relevant Considerations
- **[P00] Dual-database architecture**: Numeric facts stored in Neo4j episodes, not PostgreSQL
- **[P00] Unified agent principle**: Parser should be a utility function, not a new agent
- **[P00] Centralized config**: Use `get_settings()` for any configuration values

---

## Alternative Sessions

If this session is blocked:
1. **No valid alternatives** - Sessions 05-06 have unmet prerequisites (depend on Session 04)
2. **Phase 00 sessions** - Could pivot to MVP stabilization if Session 04 is blocked by external factors

Note: Session 05 (Relationship Scoring) requires Session 04 completion. Session 06 (Type Hierarchy and Testing) requires all prior sessions. There are no skip-ahead options within Phase 01.

---

## Next Steps

Run `/sessionspec` to generate the formal specification.
