# Test Failures Inventory - Phase 2: UI Tests

**Analysis Date**: 2025-10-28
**Total Tests Analyzed**: 83 failures across 12 files

---

## Summary by Decision

| Decision | Count | Percentage | Files |
|----------|-------|------------|-------|
| **TRY-TO-FIX** | 71 | 85.5% | 11 files |
| **DELETE & CREATE-FROM-SCRATCH** | 12 | 14.5% | 1 file |

## Detailed Analysis

### tests/ui/features/test_memory_handler_edge_cases.py (18 failures)

**Decision**: TRY-TO-FIX (All 18 tests)

**Reason**: Tests cover current active code in `src/ui/features/memory_handler.py`. All methods tested (`get_memories()`, `add_memory()`, `run_agent()`, `_setup_hook()`) exist in current implementation. Test logic is sound - comprehensive edge case coverage including:
- Exception handling
- Unicode content
- Empty/malformed results
- Memory limit boundary conditions
- Long content handling
- Integration workflows

**Issue**: Tests use fragile mocking pattern `handler.__class__.__bases__[0]` to mock parent class (StreamingHandler). This breaks with minor inheritance changes. Fix requires updating mock strategy to be more robust.

**Fix Priority**: HIGH (comprehensive edge case coverage)

---

### tests/ui/features/test_memory_handler_ultra_comprehensive.py (12 failures)

**Decision**: DELETE & CREATE-FROM-SCRATCH (All 12 tests)

**Reason**: Tests are for **completely different API** that no longer exists:
- Tests `retrieve_memories()` method - actual code has `get_memories()`
- Tests `store_memory()` method - actual code has `add_memory()`
- Tests `handle()` method - actual code has `run_agent()`
- Expected method signatures don't match current implementation
- Return types and async patterns are different

These tests were written for an older version of MemoryHandler that has been refactored. Current code structure and API are fundamentally different.

**Fix Priority**: LOW (tests are obsolete, DELETE recommended)

---

### tests/ui/features/test_memory_handler.py (11 failures)

**Decision**: TRY-TO-FIX (All 11 tests)

**Reason**: Tests current active code in `src/ui/features/memory_handler.py`. All tested functionality exists:
- `get_memories()` with search, empty results, exceptions, custom limits
- `add_memory()` with success, no response, empty response, exceptions
- `run_agent()` with memory retrieval, storage, error handling, streaming accumulation

Tests are well-structured with proper fixtures, mocking, and async patterns.

**Issue**: Same mocking issue as edge_cases tests - uses `handler.__class__.__bases__[0]` pattern which is fragile. Need better parent class mocking.

**Fix Priority**: HIGH (good coverage of core memory functionality)

---

### tests/ui/features/test_streaming_handler.py (10 failures)

**Decision**: TRY-TO-FIX (All 10 tests)

**Reason**: Tests active streaming code in `src/ui/features/streaming_handler.py`. Comprehensive coverage of:
- Text streaming events (start, delta, complete)
- Tool call/return events
- Multiple nodes processing
- Event counting and logging
- Error handling with event tracking
- Analytics integration

Tests mock Pydantic AI's streaming API correctly but need adjustments for current event structure.

**Issue**: Complex mocking of `super_agent.iter()`, node streaming, and event types. Mock setup is detailed but may not match latest Pydantic AI event structure. Tests create custom MockPartStartEvent/MockPartDeltaEvent classes.

**Fix Priority**: HIGH (core streaming functionality)

---

### tests/ui/test_streamlit_app_core.py (10 failures)

**Decision**: TRY-TO-FIX (All 10 tests)

**Reason**: Tests current code in `src/ui/streamlit_app.py`:
- `make_json_safe()` utility function - exists and matches test expectations
- `UIConfig` class - exists with correct structure
- Mode-based feature flags (SIMPLE/STANDARD/ADVANCED) - matches implementation
- Handler selection logic (`get_handler()`) - correct

Tests are clean, well-organized, and match current code structure.

**Issue**: Likely fixture/import issues or Streamlit mocking problems. Tests may need `@patch("streamlit")` decorators.

**Fix Priority**: MEDIUM (UI configuration is stable)

---

### tests/ui/features/test_upload_handler_edge_cases.py (9 failures)

**Decision**: TRY-TO-FIX (All 9 tests)

**Reason**: Tests edge cases for active upload functions in `src/ui/features/upload_handler.py`:
- `process_document_upload()` - exists, tests empty files, large files, decode errors, chunking/embedding/database errors, unicode
- `process_image_upload()` - likely exists (pattern matches)
- `process_tabular_upload()` - likely exists (pattern matches)

Tests cover important error paths and boundary conditions.

**Issue**: Likely async mocking issues or import path problems. Tests use complex mock chains for Supabase client.

**Fix Priority**: MEDIUM (upload error handling)

---

### tests/ui/test_streamlit_app_ultra_comprehensive.py (6 failures)

**Decision**: TRY-TO-FIX (All 6 tests)

**Reason**: Tests for core Streamlit app functions:
- `handle_user_input()` in different modes
- `initialize_session_state()`
- `render_dashboard()`
- Main chat page flow

These are integration-style tests of actual UI workflow.

**Issue**: Streamlit mocking complexity - session state, widgets, chat messages. May need better Streamlit test fixtures.

**Fix Priority**: MEDIUM (integration tests are valuable but complex to fix)

---

### tests/ui/features/test_mcp_handler_comprehensive.py (3 failures)

**Decision**: TRY-TO-FIX (All 3 tests)

**Tests**:
1. `test_init_with_mcp_enabled`
2. `test_init_inherits_from_memory_handler`
3. `test_run_agent_error_logging`

**Reason**: MCPHandler exists and inherits from MemoryHandler. Tests are checking correct inheritance and initialization. Likely simple fixture/mock issues.

**Fix Priority**: MEDIUM (MCP integration tests)

---

### tests/ui/features/test_dashboard_utils_comprehensive.py (1 failure)

**Decision**: TRY-TO-FIX

**Test**: `test_create_pyvis_graph_circular`

**Reason**: Tests `create_pyvis_graph()` function which is actively used. Single test failure likely due to minor parameter mismatch or pyvis API change.

**Fix Priority**: LOW (single test, dashboard feature)

---

### tests/ui/features/test_streaming_handler_ultra_comprehensive.py (1 failure)

**Decision**: TRY-TO-FIX

**Test**: `test_stream_response`

**Reason**: Tests core streaming functionality. Single failure likely due to minor mock adjustment needed.

**Fix Priority**: MEDIUM (streaming is core)

---

### tests/ui/features/test_upload_handler_render_section.py (1 failure)

**Decision**: TRY-TO-FIX

**Test**: `test_render_upload_section_file_size_display`

**Reason**: Tests `render_upload_section()` which exists. Single test likely has Streamlit mocking issue.

**Fix Priority**: LOW (UI rendering test)

---

### tests/ui/features/test_dashboard_handler.py (1 failure)

**Decision**: TRY-TO-FIX

**Test**: `test_get_performance_metrics_includes_percentiles`

**Reason**: Tests DashboardHandler metrics functionality. Single failure likely minor assertion mismatch.

**Fix Priority**: LOW (dashboard metrics)

---

## Recommended Fix Order

1. **Quick Delete** (<5 min):
   - 🗑️ test_memory_handler_ultra_comprehensive.py (12 tests) - Obsolete API, DELETE file

2. **High Value Fixes** (39 tests, ~6-8 hours):
   - ✅ test_memory_handler_edge_cases.py (18 tests) - Fix parent class mocking
   - ✅ test_memory_handler.py (11 tests) - Fix parent class mocking
   - ✅ test_streaming_handler.py (10 tests) - Adjust Pydantic AI event mocks

3. **Medium Value Fixes** (20 tests, ~3-4 hours):
   - ✅ test_streamlit_app_core.py (10 tests) - Fix Streamlit mocking
   - ✅ test_upload_handler_edge_cases.py (9 tests) - Fix async/Supabase mocks
   - ✅ test_mcp_handler_comprehensive.py (3 tests) - Fix inheritance/init tests

4. **Integration & Low Priority** (12 tests, ~2-3 hours):
   - ✅ test_streamlit_app_ultra_comprehensive.py (6 tests) - Fix integration mocks
   - ✅ Single-failure tests (4 tests across 4 files) - Quick fixes

## Common Fix Patterns Identified

1. **Parent Class Mocking**: Replace `handler.__class__.__bases__[0]` with explicit parent class imports and mocking
2. **Streamlit Mocking**: Add proper `@patch("streamlit")` decorators and session_state fixtures
3. **Async Context Managers**: Ensure proper async/await patterns in test fixtures
4. **Pydantic AI Events**: Update mock event structures to match current Pydantic AI streaming API
5. **Supabase Mocking**: Fix mock chains for `.table().insert().execute()` patterns
