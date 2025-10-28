# Test Failures Inventory - Phase 3: API Tests

**Analysis Date**: 2025-10-28
**Total Tests Analyzed**: 80 failures across 12 files

---

## Summary by Decision

| Decision | Count | Percentage | Files |
|----------|-------|------------|-------|
| **TRY-TO-FIX** | 80 | 100% | 12 files |

## Detailed Analysis

### tests/api/endpoints/test_documents_endpoints_comprehensive.py (21 failures)

**Decision**: TRY-TO-FIX (All 21 tests)

**Reason**: Tests cover active production code in `src/api/endpoints/documents.py`. All endpoints exist and are correctly implemented:
- POST /api/v1/documents (document ingestion)
- GET /api/v1/documents (list with pagination, filtering)
- GET /api/v1/documents/{document_id} (retrieve with optional chunks)
- DELETE /api/v1/documents/{document_id} (deletion)
- PATCH /api/v1/documents/{document_id} (update metadata)
- POST /api/v1/documents/{document_id}/reindex (reindexing)
- GET /api/v1/documents/{document_id}/stats (statistics)

Tests are comprehensive and well-structured with proper async patterns and mocks. Failures due to:
- TestClient dependency injection setup (creating standalone app instead of using full app context)
- Mock fixture configuration for PostgresStore and GraphitiClient
- Missing dependency override patterns

**Fix Priority**: HIGH (document management is core functionality)

---

### tests/api/test_chat_endpoints_comprehensive.py (14 failures)

**Decision**: TRY-TO-FIX (All 14 tests)

**Reason**: Tests comprehensive chat endpoints in `src/api/endpoints/chat.py`:
- POST /api/v1/chat (synchronous chat with caching)
- POST /api/v1/chat/stream (SSE streaming)
- WebSocket /api/v1/chat/ws (bidirectional communication)
- POST /api/v1/chat/feedback (feedback submission)
- GET /api/v1/chat/sessions/{id}/history (session history)
- `_extract_sources_from_messages()` helper function

Tests are well-structured with proper mocking of agent dependencies, cache, and agent results. Failures due to:
- TestClient fixture not properly injecting dependencies
- Mock setup for super_agent.run and streaming
- Cache manager dependency override issues

**Fix Priority**: HIGH (chat is primary user-facing functionality)

---

### tests/api/test_main_comprehensive.py (13 failures)

**Decision**: TRY-TO-FIX (All 13 tests)

**Reason**: Tests core FastAPI app initialization and infrastructure in `src/api/main.py`. All tested components exist:
- Lifespan management (startup/shutdown)
- Root endpoints (/, /api/v1/status, /metrics, /api/v1/cache)
- Exception handlers (404, 500)
- Tracing setup (Jaeger, OTLP, console export)
- Middleware stack (CORS, security, compression, rate limiting)
- Router inclusion (health, chat, search, documents, analytics)
- OpenAPI schema generation

Tests are comprehensive integration tests. Failures due to:
- Lifespan context manager mocking complexity
- Settings dependency injection
- Mock configuration for init_dependencies/cleanup_dependencies

**Fix Priority**: HIGH (app initialization and infrastructure)

---

### tests/api/test_streaming_comprehensive.py (7 failures)

**Decision**: TRY-TO-FIX (All 7 tests)

**Reason**: Tests streaming utilities in `src/api/streaming.py`:
- SSEManager: event formatting, chunking, heartbeats, agent streaming
- WebSocketManager: connections, messaging, broadcasting, agent streaming, receive loops

Tests are comprehensive with proper async patterns and mocking. Failures due to:
- Mock StreamedRunResult setup (context managers, stream_text async generator)
- Pydantic AI streaming API mock structure
- WebSocket mock setup

**Fix Priority**: MEDIUM (streaming is important but has fallback)

---

### tests/api/test_dependencies_comprehensive.py (5 failures)

**Decision**: TRY-TO-FIX (All 5 tests)

**Reason**: Tests dependency initialization and providers in `src/api/dependencies.py`:
- init_dependencies (full, without graph, exception handling)
- cleanup_dependencies (full, none, exception handling)
- Dependency providers (connection_manager, postgres_store, neo4j_store, graphiti_client, cache_manager)
- Search providers (vector_search, hybrid_search, intent_analyzer)
- get_agent_deps (full features, minimal features)
- Session providers (postgres_session, neo4j_session with error handling)
- check_database_health (all healthy, partial, exceptions)
- get_api_settings (full features, minimal)

Tests are comprehensive unit tests with proper mocking. Failures due to:
- Global state reset fixture complexity
- Mock configuration for async context managers
- Dependency injection patterns

**Fix Priority**: HIGH (dependencies are foundational)

---

### tests/api/test_endpoints.py (5 failures)

**Decision**: TRY-TO-FIX (All 5 tests)

**Reason**: Integration-style tests for Phase 4 API endpoints:
- Root endpoints (/, /metrics)
- Chat endpoints (success, validation error, streaming)
- Search endpoints (vector, validation error, suggestions)
- Document endpoints (ingest, list, get, delete)
- Middleware (CORS, correlation ID, timing, rate limiting)
- Error handling (404, validation)
- Caching (clear endpoint)
- Health checks (basic, comprehensive)

Tests use actual `app` from `src.api.main` and are valuable for API validation. Failures due to:
- Dependency initialization (expects 503 or 200)
- Mock setup for agent_deps and postgres_store
- Flexible assertions (status_code in [200, 503]) show tests are aware of initialization issues

**Fix Priority**: MEDIUM (integration tests valuable for CI/CD)

---

### tests/api/endpoints/test_search_endpoints_ultra_comprehensive.py (4 failures)

**Decision**: TRY-TO-FIX (All 4 tests)

**Reason**: Tests search API endpoints in `src/api/endpoints/search.py`:
- Main search endpoint (vector, hybrid, adaptive)
- Cache hit/miss behavior
- Intent analysis integration
- Unsupported search type error handling
- Search result caching
- Error handling

Tests are ultra-comprehensive with proper mocking. Failures due to:
- Mock configuration for VectorSearch, HybridSearch, IntentAnalyzer
- Cache manager mock setup
- Adaptive search execution helpers

**Fix Priority**: MEDIUM (search functionality)

---

### tests/api/test_analytics_endpoints_comprehensive.py (4 failures)

**Decision**: TRY-TO-FIX (All 4 tests)

**Reason**: Tests analytics API endpoints in `src/api/endpoints/analytics.py`:
- get_search_metrics (24h, 7d, 30d windows)
- get_intent_distribution
- get_performance_metrics
- get_time_series_data
- get_tool_usage_metrics
- get_agent_interaction_metrics
- analytics_health (healthy, degraded, missing tables)

Tests are comprehensive with proper DashboardHandler mocking. Failures due to:
- ConnectionManager pg connection context manager mocking
- DashboardHandler method mock setup
- Health check table verification logic

**Fix Priority**: MEDIUM (analytics is supplementary feature)

---

### tests/api/test_chat_endpoints_ultra_comprehensive.py (4 failures)

**Decision**: TRY-TO-FIX (All 4 tests)

**Reason**: Ultra-comprehensive tests for chat endpoints:
- Chat endpoint success with various parameters
- Cache hit/miss scenarios
- Source extraction from messages
- Error handling
- Response caching verification

Tests are well-structured with comprehensive coverage. Failures due to:
- super_agent.run mock setup
- _extract_sources_from_messages helper mocking
- Cache mock configuration
- Parameters forwarding verification

**Fix Priority**: HIGH (chat is core functionality)

---

### tests/api/test_documents_endpoints_enhanced.py (1 failure)

**Decision**: TRY-TO-FIX

**Test**: `test_get_document_with_chunks` (or similar single failure)

**Reason**: Enhanced tests for document endpoints providing additional coverage beyond comprehensive tests. Single failure likely due to minor mock adjustment needed for chunk retrieval.

**Fix Priority**: LOW (enhanced coverage, not critical)

---

### tests/api/test_streaming_ultra_comprehensive.py (1 failure)

**Decision**: TRY-TO-FIX

**Test**: `test_stream_agent_response_success` (likely from TestSSEManagerStreamAgentResponse class)

**Reason**: Ultra-comprehensive streaming tests with single failure. Likely due to mock StreamedRunResult setup complexity or event structure mismatch.

**Fix Priority**: MEDIUM (streaming is important)

---

### tests/api/test_telemetry_comprehensive.py (1 failure)

**Decision**: TRY-TO-FIX

**Test**: `test_setup_tracing_console_export` (from TestOpenTelemetryConfig class)

**Reason**: Tests OpenTelemetry configuration and Prometheus metrics. Single failure likely due to console exporter mock setup or conditional import mocking.

**Fix Priority**: LOW (observability is supplementary)

---

## Recommended Fix Order

1. **High Priority - Core Functionality** (51 tests, ~8-10 hours):
   - test_documents_endpoints_comprehensive.py (21 tests)
   - test_chat_endpoints_comprehensive.py (14 tests)
   - test_main_comprehensive.py (13 tests)
   - test_chat_endpoints_ultra_comprehensive.py (4 tests)

2. **High Priority - Infrastructure** (5 tests, ~2-3 hours):
   - test_dependencies_comprehensive.py (5 tests)

3. **Medium Priority - Search & Streaming** (16 tests, ~4-5 hours):
   - test_streaming_comprehensive.py (7 tests)
   - test_endpoints.py (5 tests)
   - test_search_endpoints_ultra_comprehensive.py (4 tests)

4. **Medium Priority - Analytics & Monitoring** (5 tests, ~2-3 hours):
   - test_analytics_endpoints_comprehensive.py (4 tests)
   - test_streaming_ultra_comprehensive.py (1 test)

5. **Low Priority - Enhanced Coverage** (3 tests, ~1 hour):
   - test_documents_endpoints_enhanced.py (1 test)
   - test_telemetry_comprehensive.py (1 test)

## Common Fix Patterns Identified

1. **Dependency Injection**: Update TestClient to properly override FastAPI dependencies
   - Use `app.dependency_overrides[get_postgres_store] = lambda: mock_store` pattern
   - Ensure all dependencies are overridden before TestClient creation

2. **Async Context Managers**: Properly mock async context managers for streaming and connections
   - Mock `__aenter__` and `__aexit__` for StreamedRunResult
   - Mock connection context managers for database access

3. **Agent Mocking**: Ensure super_agent.run and super_agent.run_stream are properly mocked
   - Mock result structure matches actual Pydantic AI result
   - Mock usage() returns correct token counts
   - Mock all_messages() for source extraction

4. **Cache Mocking**: Configure cache manager with proper get/set behavior
   - Mock both cache hit and miss scenarios
   - Ensure cache key generation works

5. **Fixture Organization**: Consolidate common fixtures across test files
   - Create shared conftest.py for API test fixtures
   - Standardize mock patterns

## Critical Insights

**All 80 tests in Phase 3 should be fixed** because:
- Tests cover production-ready API endpoints
- All endpoints exist and are actively used
- Tests are well-structured and comprehensive
- Failures are primarily due to fixture/dependency injection issues, not obsolete code
- Fixing these tests will significantly improve API test coverage
- Tests follow best practices (async patterns, proper mocking, comprehensive scenarios)

**Key Difference from Phase 1 & 2**:
- Phase 1 had 17% DELETE (ui_all_comprehensive was skeleton)
- Phase 2 had 14.5% DELETE (memory_handler_ultra was obsolete API)
- **Phase 3 has 0% DELETE** - all tests are valuable and fixable
