# Google Drive Deployment - Todo List

**Source Document:** `docs/6-deployment/google_drive_deployment.md` (360 lines)
**Last Updated:** 2025-11-02
**Total Items:** 45 actionable todos across 8 categories

---

## High Priority - Critical for Production

- [ ] **Add Google Drive Dependencies to pyproject.toml** - Create optional dependency group `[google_drive]` with google-api-python-client, google-auth, google-auth-oauthlib, google-auth-httplib2 (Section 6.2, 17.1.1)
- [ ] **Implement Pagination for Large Folders** - Add `nextPageToken` handling in `get_folder_contents()` to support folders with >100 files (Section 16.1.6, 17.1.2)
- [ ] **Add Health Check HTTP Endpoint** - Create FastAPI endpoint at `/health/google-drive` returning authentication status, last check time, and known files count (Section 13.3, 17.1.3)
- [ ] **Implement Retry Logic with Exponential Backoff** - Use tenacity library for API calls with 3 attempts and exponential wait (Section 10.4, 17.1.4)
- [x] **Fix Configuration Mismatch** - Environment variables `GOOGLE_DRIVE_FOLDER_ID` and `GOOGLE_DRIVE_CREDENTIALS_PATH` are defined but not consumed by `google_drive.py` (Section 4.2) ✅ COMPLETED 2025-11-02

---

## Medium Priority - Important Improvements

- [ ] **Implement Async/Concurrent File Processing** - Use asyncio.gather() to process multiple files in parallel instead of sequential processing (Section 14.3, 17.2.5)
- [ ] **Add Webhook Support for Real-Time Sync** - Implement Drive Activity API push notifications to replace polling-based architecture (Section 16.1.1, 17.2.6)
- [ ] **Add Shared Drive Support** - Implement `supportsAllDrives=True` and `includeItemsFromAllDrives=True` parameters for team drives (Section 16.1.2, 17.2.7)
- [ ] **Implement Multi-Folder Configuration** - Support watching multiple folders via `watch_folders` array in config (Section 16.3.1, 17.2.8)
- [ ] **Add File Filtering Capabilities** - Implement include/exclude patterns, name-based filters (regex/glob), and max file size filters (Section 16.3.2, 17.2.9)
- [ ] **Optimize Deletion Detection** - Replace O(N) API calls per cycle with Drive Activity API for bulk deletion detection (Section 14.3, 16.2.2)
- [ ] **Add Batch Processing for Embeddings** - Implement batching for large documents to avoid exceeding OpenAI's ~8,191 token limit (Section 14.3)
- [ ] **Implement LRU Cache for known_files** - Prevent unbounded memory growth for large folder counts (Section 16.2.4)

---

## Low Priority - Nice to Have Enhancements

- [ ] **Integrate OCR for Scanned PDFs** - Use Google Cloud Vision API or Tesseract for scanned PDFs and images (Section 16.1.4, 17.3.10)
- [ ] **Implement Semantic Chunking** - Replace fixed character-based chunking with sentence-transformer based semantic chunking (Section 16.3.3, 17.3.11)
- [ ] **Add Neo4j Knowledge Graph Integration** - Extract entities and relationships from Google Drive documents into Neo4j (Section 5.1, 17.3.12)
- [ ] **Create Analytics Dashboard** - Track files processed over time, latency trends, error rates by file type, storage usage (Section 17.3.13)
- [ ] **Implement Multi-Tenancy Support** - Create GoogleDriveWatcherPool to manage multiple user accounts (Section 16.4.1, 17.3.14)
- [ ] **Support Multi-Sheet Google Sheets Export** - Currently exports first sheet only; add support for all sheets (Section 16.1.3)
- [ ] **Add Version Control Tracking** - Track Google Drive revision history instead of only processing latest version (Section 16.1.5)
- [ ] **Implement Rate Limiting Protection** - Add rate limiter to prevent exceeding Google Drive API quotas (Section 16.2.3)

---

## Security & Configuration

- [x] **Add OAuth Credentials to .gitignore** - Explicitly add `credentials.json`, `token.json`, `config/google_credentials.json`, `config/google_token.json`, and source directory variants (Section 3.3, 15.1) ✅ COMPLETED 2025-11-02
- [ ] **Set File Permissions on Credentials** - Set `chmod 600` on credentials.json and token.json files (Section 15.1)
- [ ] **Add Configuration for File Content Storage** - Implement `store_file_contents: false` option to exclude base64 file content from metadata for privacy (Section 15.3)
- [ ] **Implement Access Control on RAG Queries** - Add authorization checks to prevent unauthorized access to file metadata (Section 15.3)
- [ ] **Configure TLS for Database Connection** - Enable TLS for Supabase PostgreSQL connection (Section 15.4)
- [ ] **Set Up SIEM Integration** - Send structured logs to Splunk/ELK for compliance (Section 15.5)
- [ ] **Implement Audit Log Table** - Create database table for file access audit trail (Section 15.5)
- [ ] **Add Compliance Metadata to Logs** - Include GDPR/HIPAA compliance fields in structlog output (Section 15.5)

---

## Testing & Documentation

- [ ] **Add Coverage for Edge Cases** - Test pagination with >100 files, multi-sheet spreadsheets, rate limiting scenarios (Section 11)
- [ ] **Create Deployment Documentation** - Document systemd service setup, Docker deployment, monitoring configuration (Section 12)
- [ ] **Document Troubleshooting Procedures** - Expand Appendix D with more common issues and solutions (Section Appendix D)
- [ ] **Add Performance Benchmarks** - Document actual performance metrics for various folder sizes and file types (Section 14)

---

## Infrastructure & Monitoring

- [ ] **Implement Prometheus Metrics** - Add counters for files_processed_total, processing_duration_seconds, api_calls_total, watch_cycles_total, known_files gauge (Section 13.2)
- [ ] **Set Up Critical Alerts** - Configure alerts for authentication failure, consecutive processing failures >10, API quota exceeded, database connection failures (Section 13.4)
- [ ] **Set Up Warning Alerts** - Configure alerts for processing latency >2 min, no files processed in 24h, unexpected known_files decrease (Section 13.4)
- [ ] **Add Transaction Wrapping** - Wrap delete+insert operations in database transactions to prevent partial failures (Section 9.2)
- [ ] **Implement Error Recovery Queue** - Add retry queue for files that fail processing (Section 10.4)
- [ ] **Add Circuit Breaker** - Implement circuit breaker pattern for repeated API failures (Section 10.4)

---

## Documentation Updates Needed

- [ ] **Update README with Google Drive Setup** - Add comprehensive setup instructions for Google Cloud Console, OAuth credentials, and first-time authentication (Section 12.1)
- [ ] **Create Makefile Targets** - Add `make run-gdrive`, `make gdrive-auth`, `make gdrive-status` commands (Section 12)
- [ ] **Document Polling Interval Recommendations** - Provide guidance on choosing appropriate polling intervals based on folder size and activity (Section 14.1)
- [ ] **Add API Quota Management Guide** - Document quota usage calculation and optimization strategies (Section 14.1)

---

## Progress Tracking

**Completed:** 2/45 (4.4%)
**High Priority:** 1/5 (20%)
**Medium Priority:** 0/8
**Low Priority:** 0/8
**Security:** 1/8 (12.5%)
**Testing:** 0/4
**Infrastructure:** 0/6
**Documentation:** 0/4

---

## Quick Reference - Implementation Order

**Phase 1 - Foundation (Week 1-2):**
1. Add dependencies to pyproject.toml
2. Fix configuration mismatch
3. Add credentials to .gitignore
4. Set file permissions

**Phase 2 - Production Readiness (Week 3-4):**
1. Implement pagination
2. Add retry logic
3. Add health check endpoint
4. Implement Prometheus metrics

**Phase 3 - Scale & Performance (Week 5-6):**
1. Async/concurrent processing
2. Optimize deletion detection
3. Add batch processing for embeddings
4. Implement LRU cache

**Phase 4 - Advanced Features (Week 7-8):**
1. Webhook support
2. Shared drive support
3. Multi-folder configuration
4. File filtering capabilities

**Phase 5 - Security & Compliance (Week 9-10):**
1. Configure TLS
2. Implement audit logging
3. Set up alerts
4. Add transaction wrapping

---

## Notes

- All section references point to `docs/6-deployment/google_drive_deployment.md`
- Items are ordered by impact and dependency within each category
- Checkboxes can be marked with `[x]` when completed
- Update progress tracking section as items are completed
- Some items may be combined or split during implementation
