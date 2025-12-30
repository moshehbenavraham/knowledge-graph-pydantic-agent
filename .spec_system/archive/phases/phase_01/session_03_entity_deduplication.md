# Session 03: Entity Deduplication

**Session ID**: `phase01-session03-entity_deduplication`
**Status**: Not Started
**Estimated Tasks**: ~18-22
**Estimated Duration**: 4-5 hours

---

## Objective

Reduce entity fragmentation through canonical name resolution, merging duplicates like "Apple Inc.", "Apple", and "AAPL" into a single canonical entity while preserving merge history for potential rollback.

---

## Scope

### In Scope (MVP)
- Create `src/agentic_rag/entity_resolution/canonical_names.py` with mappings
- Implement multi-pass deduplication: exact match, fuzzy matching, context-based
- Create `scripts/merge_duplicate_entities.py` with dry-run mode
- Preserve merge history for potential rollback
- Update ingestion pipeline to use canonical names
- Handle company name variations (Inc., Corp., LLC, etc.)
- Handle ticker symbol to company name mappings

### Out of Scope
- Automatic entity resolution without human review for ambiguous cases
- Real-time deduplication during streaming ingestion
- Cross-company entity disambiguation (e.g., "Data Center" for Intel vs NVIDIA)
- UI for reviewing and approving merges

---

## Prerequisites

- [ ] Session 02 completed (temporal metadata populated)
- [ ] Entity list accessible via Cypher queries
- [ ] Relationship data preserved during merges
- [ ] Backup of current graph state available

---

## Deliverables

1. Canonical name mappings in `src/agentic_rag/entity_resolution/canonical_names.py`
2. Deduplication logic with multi-pass matching
3. Merge script `scripts/merge_duplicate_entities.py` with:
   - Dry-run mode (report only)
   - Interactive mode (confirm each merge)
   - Batch mode (apply all safe merges)
4. Merge history table/log for rollback capability
5. Updated ingestion pipeline to normalize names
6. Unit tests in `tests/rag_pipeline/test_entity_deduplication.py`
7. Documentation for canonical name maintenance

---

## Success Criteria

- [ ] 95%+ reduction in duplicate entities
- [ ] No incorrect mergers of distinct entities
- [ ] Merge history preserved for potential rollback
- [ ] Ingestion pipeline uses canonical names for new entities
- [ ] Dry-run mode accurately predicts merge outcomes
- [ ] All relationships preserved during merges
- [ ] New unit tests pass (target: 20+ tests)
- [ ] Existing tests still pass
- [ ] Manual review completed for high-importance entity merges
