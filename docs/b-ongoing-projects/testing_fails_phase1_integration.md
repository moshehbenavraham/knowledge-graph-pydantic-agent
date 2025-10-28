# Test Failures Inventory - Phase 1: Integration Tests

**Analysis Date**: 2025-10-28
**Total Tests Analyzed**: 99 failures across 7 files

---

## Summary by Decision

| Decision | Count | Percentage | Files |
|----------|-------|------------|-------|
| **TRY-TO-FIX** | 82 | 82.8% | 6 files |
| **DELETE & CREATE-FROM-SCRATCH** | 17 | 17.2% | 1 file |

## Detailed Analysis

### tests/integration/test_chat_endpoints_comprehensive.py (38 failures)

**Decision**: TRY-TO-FIX (All 38 tests)

**Reason**: Tests cover active production code in `src/api/endpoints/chat.py`. All endpoints exist and are correctly implemented:
- POST /api/v1/chat (synchronous)
- POST /api/v1/chat/stream (SSE streaming)
- WebSocket /api/v1/chat/ws
- POST /api/v1/chat/feedback
- GET /api/v1/chat/sessions/{id}/history

Tests are well-structured with proper async patterns and mocks. Failures due to:
- Fixture/dependency injection setup issues
- TestClient vs actual HTTP client behavioral differences
- Cache mock configuration problems
- Minor API response structure mismatches

**Fix Priority**: HIGH (core functionality)

---

### tests/integration/test_api_main_comprehensive.py (25 failures)

**Decision**: TRY-TO-FIX (All 25 tests)

**Reason**: Tests core FastAPI app initialization and infrastructure in `src/api/main.py`. All tested components exist:
- App metadata (version 0.8.0 matches)
- Middleware stack (CORS, Security, Compression, RateLimit, etc.)
- Root endpoints (/, /api/v1/status, /metrics, /api/v1/cache)
- Documentation (OpenAPI, Swagger, ReDoc)
- Exception handlers (404, 500)
- Lifespan management

Failures due to minor mock/fixture configuration issues with:
- Lifespan context manager mocking
- Settings dependency injection
- Cache manager dependency override
- Health check function mocking

**Fix Priority**: HIGH (app initialization)

---

### tests/integration/test_ui_all_comprehensive.py (17 failures)

**Decision**: DELETE & CREATE-FROM-SCRATCH (All 17 tests)

**Reason**: This is a **skeleton test file with incomplete placeholder implementations**:
- Most test bodies contain only `pass` statements
- Lines 308-352 literally say "# Add 100+ more tests" with empty methods
- Tests like `test_theme_switching`, `test_layout_responsiveness`, `test_session_persistence` are not implemented
- File provides ZERO actual test coverage despite existing

These tests were scaffolded but never completed. Starting fresh with targeted, properly implemented UI tests would be more effective than trying to fix non-existent test logic.

**Fix Priority**: LOW (rewrite when time permits)

---

### tests/integration/test_rag_tools_comprehensive.py (14 failures)

**Decision**: TRY-TO-FIX (All 14 tests)

**Reason**: Tests active RAG tools in `src/tools/rag.py` with comprehensive coverage:
- `get_hybrid_search()` singleton pattern
- `get_intent_analyzer()` singleton
- `retrieve_relevant_documents_tool()` main search function
- `smart_search_tool()` with intent analysis
- `graph_query_tool()` for entity queries
- Document listing and content retrieval

Tests are well-structured with proper async patterns, fixtures, and mocks. Failures due to:
- ConnectionManager initialization mocking issues
- HybridSearch event loop handling in tests
- Mock result structure mismatches
- Async fixture configuration

**Fix Priority**: MEDIUM (search functionality)

---

### tests/integration/test_health_utils_comprehensive.py (3 failures)

**Decision**: TRY-TO-FIX (All 3 tests)

**Tests**:
1. `test_web_search_brave_healthy`
2. `test_web_search_searxng_healthy`
3. `test_web_search_degraded`

**Reason**: All tests fail due to **same root cause** - async context manager syntax error in `src/utils/health.py`:

Lines 271-273 and 301-303:
```python
async with (
    httpx.AsyncClient()  # Missing 'as client'
):
```

Should be:
```python
async with httpx.AsyncClient() as client:
```

This is a **simple fix** in the source code that will resolve all 3 failures immediately.

**Fix Priority**: HIGHEST (quick win, simple fix)

---

### tests/integration/test_additional_coverage.py (1 failure)

**Decision**: TRY-TO-FIX

**Test**: `test_search_intent_enum` (line 417)

**Reason**: Simple enum import test that verifies `SearchIntent` enum exists. The enum is defined in codebase but may not be properly exported in `src/config/__init__.py`. Simple fix:
- Verify `SearchIntent` is imported and re-exported in config module
- Update import path if needed

**Fix Priority**: HIGHEST (quick win)

---

### tests/integration/test_web_search_tools_comprehensive.py (1 failure)

**Decision**: TRY-TO-FIX

**Test**: `test_web_search_fallback_chain` (line 418)

**Reason**: Tests the provider fallback logic (Jina → Brave → SearXNG) that exists in source code. Mock setup issue where exceptions aren't propagating correctly through the fallback chain. Need to ensure:
- Mock side_effect exceptions are properly raised
- Fallback logic catches and continues as expected
- Final provider mock returns successfully

**Fix Priority**: MEDIUM (web search resilience)

---

## Recommended Fix Order

1. **Quick Wins First** (4 tests, <30 min):
   - ✅ test_health_utils (3 tests) - Single async syntax fix
   - ✅ test_additional_coverage (1 test) - Import path fix

2. **High Value** (63 tests, ~4-6 hours):
   - ✅ test_chat_endpoints (38 tests) - Core chat functionality
   - ✅ test_api_main (25 tests) - App initialization

3. **Medium Value** (15 tests, ~2-3 hours):
   - ✅ test_rag_tools (14 tests) - Search functionality
   - ✅ test_web_search_tools (1 test) - Fallback chain

4. **Later** (17 tests, rewrite required):
   - 🗑️ test_ui_all (17 tests) - Delete and rewrite from scratch

## Common Fix Patterns Identified

1. **Async Context Managers**: Fix missing 'as' clauses in health checks
2. **Dependency Injection**: Update TestClient fixture overrides for FastAPI dependencies
3. **Mock Structure**: Ensure mock objects match actual API response structures
4. **Event Loop Handling**: Properly handle asyncio event loop changes in RAG tools
5. **Import Paths**: Verify enum and class exports in `__init__.py` files
