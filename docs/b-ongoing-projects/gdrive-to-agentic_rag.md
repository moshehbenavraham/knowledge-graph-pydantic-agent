# Google Drive to Agentic RAG Integration

## Objective
Replace legacy RAG processing in Google Drive watcher with full Agentic RAG pipeline (knowledge extraction + Neo4j graph).

## Status
- Phase 1 (Local File Watcher): Complete
- Phase 2 (Google Drive Watcher): Pending
- Phase 3 (Cleanup): Pending

## Remaining Work

### Phase 2: Google Drive Watcher Integration

**File**: src/rag_pipeline/sources/google_drive.py

**Required Changes**:
1. Update imports (line 11-12):
   - Remove: from src.rag_pipeline.common.db_handler import process_file_for_rag
   - Add: from src.rag_pipeline.adapters.agentic_rag_adapter import process_file_with_agentic_rag_sync

2. Update process_file() method (approximately line 507-513):
   - Delete existing records before ingestion: delete_document_by_file_id(file_id)
   - Replace process_file_for_rag call with process_file_with_agentic_rag_sync
   - Pass parameters: text, file_id, file_name (as file_title), web_view_link (as file_url), mime_type

**Testing**:
- Unit tests: Update test_google_drive.py to mock new adapter
- Integration test: Upload test file to Google Drive, verify processing
- Verify entities/facts/relationships extracted and stored in Neo4j
- Check PostgreSQL for document and chunks

**Deployment**:
- Test in dev environment first
- Monitor API rate limits (Google Drive + OpenAI + Neo4j)
- Consider increasing polling interval if processing slower (60s to 120s)

### Phase 3: Cleanup and Documentation

**Code Cleanup**:
- Remove legacy process_file_for_rag() function from src/rag_pipeline/common/db_handler.py
- Verify no other code references process_file_for_rag
- Remove unused imports

**Documentation Updates**:
- Update docs/0-RAG/ingestion-systems.md with new Google Drive/Local File flow
- Document performance differences (2-5s to 8-15s per file)
- Document new metadata structure (file_id, source_type, mime_type)

**Configuration** (Optional):
- Add WATCHER_ENABLE_GRAPH to .env.example if needed
- Add WATCHER_USE_SEMANTIC_CHUNKING to .env.example if needed

## Success Criteria

Remaining items:
- [ ] Google Drive files processed through full Agentic RAG pipeline
- [ ] Knowledge extracted (entities, facts, relationships) visible in Neo4j
- [ ] Processing time under 20s per file
- [ ] Unit tests updated for Google Drive watcher
- [ ] Legacy process_file_for_rag() removed
- [ ] Documentation updated

Completed:
- [x] Local File Watcher uses Agentic RAG adapter
- [x] Documents stored in PostgreSQL with chunks table
- [x] Cross-references (entity_refs) populated
- [x] Adapter unit tests passing (9/9)

## Performance Notes

Current measurements from Local File Watcher:
- Processing time: ~42s for 925 character document (includes LLM calls)
- Entities extracted: 9
- Relationships created: 10
- Facts captured: 5
- Chunks created: 1

Legacy RAG:
- Processing time: 2-5s per file
- No knowledge extraction

Trade-off: 5-10x slower but significantly richer data for retrieval.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Slower processing (5-10x) | Files pile up in queue | Increase polling interval to 120s |
| Higher API costs (LLM calls) | Budget overrun | Use gpt-4o-mini for extraction (already configured) |
| Neo4j connection failures | Graph not populated | Graceful degradation (already built-in) |
