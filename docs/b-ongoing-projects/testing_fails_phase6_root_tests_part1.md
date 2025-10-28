# Test Failures Inventory - Phase 6: Root Level Tests Part 1

**Analysis Date**: 2025-10-28
**Total Tests Analyzed**: 72 failures across 5 files

---

## Summary by Decision

| Decision | Count | Percentage | Files |
|----------|-------|------------|-------|
| **TRY-TO-FIX** | 72 | 100% | 5 files |

## Detailed Analysis

### tests/test_integration.py (20 failures)

**Decision**: TRY-TO-FIX (All 20 tests)

**Reason**: Tests cover integration scenarios for RAG, database, tools, memory, and end-to-end workflows. All tested functionality exists but tests use **outdated architecture patterns**:

- Tests import `retrieve_relevant_documents_tool`, `list_documents_tool`, `execute_sql_query_tool` - ALL exist in current `src/tools/rag.py` ✓
- Tests use direct mocks of `supabase_client` and `embedding_client` passed as parameters
- **Architecture changed**: Current RAG tools use `HybridSearch` + `ConnectionManager` internally (singleton pattern), not direct client injection
- Function signature changed: `retrieve_relevant_documents_tool(supabase, embedding_client, user_query, strategy=None, limit=10)` - parameters are now legacy/unused
- Tests create manual mocks: `mock_supabase.rpc.return_value.execute.return_value.data = [...]`
- **Current implementation**: Uses `await get_hybrid_search()` which manages ConnectionManager and databases internally

**Key Issues**:
- Tests bypass modern architecture by mocking low-level database calls
- Need to mock `get_hybrid_search()` singleton and `HybridSearch.search()` method instead
- Need to mock `ConnectionManager` initialization
- Agent imports test legacy parameter patterns

**What's Correct**:
- All functions being tested exist and are actively used
- Test scenarios (RAG retrieval, document listing, SQL execution, error handling, security) are valid and valuable
- Test structure (fixtures, async patterns, assertions) is sound

**Fix Priority**: HIGH (integration tests validate cross-component functionality)

**Fix Strategy**: Update mocks to match new HybridSearch architecture while keeping test scenarios intact.

---

### tests/test_user_profile.py (18 failures)

**Decision**: TRY-TO-FIX (All 18 tests)

**Reason**: Tests cover user profile functionality (password changes, session management) that exists in current `src/auth/user_profile.py`. **Critical issue: async/sync mismatch**:

**Tests expect ASYNC**:
```python
await user_profile.get_user_info("testuser")
await user_profile.change_user_password(username, current_password, new_password)
```

**Actual functions are SYNC**:
```python
def get_user_info(username: str) -> dict | None:
    try:
        user = get_user_by_username(username)  # Sync call
        return user
    except Exception as e:
        logger.error("Failed to get user info", username=username, error=str(e))
        return None

def change_user_password(username: str, current_password: str, new_password: str) -> tuple[bool, str]:
    try:
        from src.auth.db import verify_user_password
        user = verify_user_password(username, current_password)  # Sync call
        if not user:
            return (False, "Current password is incorrect.")
        update_user_password(user["id"], new_password)  # Sync call
        return (True, "Password changed successfully!")
```

**Additional Issues**:
- Tests use `AsyncMock` for `verify_user_password`, `update_user_password` - but these are SYNC functions
- Tests use `@pytest.mark.asyncio` decorator - should be removed
- Tests use `new_callable=AsyncMock` in patches - should use regular `MagicMock`

**What's Correct**:
- All functions being tested exist: `get_user_info()`, `change_user_password()`, session management functions
- Function signatures match (except async/sync)
- Test scenarios are valid (password validation, session revocation, error handling)
- Comprehensive edge case coverage

**Fix Priority**: HIGH (authentication is critical, tests are well-structured)

**Fix Strategy**: Remove all `async`/`await`, change `AsyncMock` to `MagicMock`, remove `@pytest.mark.asyncio` decorators. Keep all test logic intact.

---

### tests/test_e2e.py (16 failures)

**Decision**: TRY-TO-FIX (All 16 tests)

**Reason**: Tests cover end-to-end workflows, Streamlit UI functionality, error handling, and edge cases. **Complex Streamlit mocking challenges**:

**What Exists**:
- `src/ui/streamlit_app.py` - main UI module ✓
- `display_message_part()` function tested - exists at line 147 ✓
- Agent streaming via `agent.iter()` - current pattern ✓
- UI modes (SIMPLE, STANDARD, ADVANCED) - current architecture ✓

**Issues**:
- Tests mock Streamlit at module level: `sys.modules["streamlit"] = streamlit_mock` (lines 52-61)
- Complex agent response mocking with streaming generators
- Tests import tools conditionally with try/except (lines 16-25) - some may fail to import
- Mock async context managers for agent streaming
- Session state management complexity

**Test Quality**:
- Comprehensive E2E scenarios (research workflow, document analysis, code execution, multi-tool workflows)
- Error handling workflows (database failure, embedding service failure, memory service degradation)
- Edge cases (empty queries, long queries, special characters, concurrent sessions)
- Performance workflows (high load, memory intensive, streaming performance)

**Fix Priority**: MEDIUM-HIGH (E2E tests are valuable but complex to maintain)

**Fix Strategy**: Update Streamlit mocking patterns, fix tool imports, adjust agent streaming mocks to match current Pydantic AI patterns.

---

### tests/test_password_reset.py (16 failures)

**Decision**: TRY-TO-FIX (All 16 tests)

**Reason**: Tests cover password reset flow (email sending, token validation, password strength) for active code in `src/auth/password_reset.py`. **All functions match test expectations**:

**Verified Functions** (all ASYNC as expected):
- `async def send_reset_email_smtp(email, reset_token, reset_url)` ✓
- `async def send_reset_email(email, reset_token, reset_url)` ✓
- `async def request_password_reset(username_or_email, reset_url, client_ip=None)` ✓
- `async def validate_reset_token(token)` ✓
- `async def reset_password_with_token(token, new_password, client_ip=None)` ✓
- `def is_password_strong(password)` ✓ (sync utility function)

**Issues**:
- Tests patch module-level variables: `src.auth.password_reset.SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, etc.
- **Actual implementation**: Uses `settings = get_settings()` and accesses `settings.smtp_host`, `settings.smtp_port`, etc.
- SMTP server mocking is complex with context manager patterns
- Tests use both `patch.dict("os.environ", {...})` and `patch("src.auth.password_reset.VARIABLE")`

**What's Correct**:
- All async/await patterns match current implementation
- Function signatures are identical
- Test scenarios comprehensive (SMTP success/failure, token validation, password strength, complete flows)
- Error handling coverage is thorough

**Fix Priority**: MEDIUM-HIGH (password reset is important security feature)

**Fix Strategy**: Update patches to mock `get_settings()` return value instead of module variables. Keep all async patterns and test scenarios intact.

---

### tests/test_config.py (12 failures)

**Decision**: TRY-TO-FIX (All 12 tests)

**Reason**: Tests cover centralized configuration system in `src/config/`. **All tested components exist and are current**:

**Verified Imports** (from `src/config/__init__.py`):
- `Settings` class ✓
- `get_settings()` function ✓
- `reload_settings()` function ✓
- Enums: `Environment`, `UIMode`, `LLMProvider`, `EmbeddingProvider`, `WebSearchProvider`, `SearchStrategy`, `ChunkingStrategy` ✓

**Verified Facades**:
- `src.config.agent.agent_config` ✓
- `src.config.api.api_config` ✓
- `src.config.clients.clients_config` ✓
- `src.config.ui.ui_config` ✓

**Test Coverage**:
- Settings loading from environment variables
- Pydantic validation (database, Redis, pool sizes, chunk overlap, production API keys)
- CORS origins parsing
- Enum value loading
- Sensitive value masking (`to_dict()` method)
- Production validation warnings
- Facade property access (agent, API, clients, UI config)
- Singleton caching behavior

**Issues**:
- Tests use `patch.dict(os.environ, {...})` extensively
- Some tests expect validation errors that may have changed
- Singleton reset between tests may need adjustment
- Test isolation issues (shared settings instance across tests)

**Fix Priority**: HIGH (configuration is foundational)

**Fix Strategy**: Verify Pydantic validation rules match current Settings class, ensure proper singleton reset in fixtures, update any changed property names/types.

---

## Recommended Fix Order

1. **High Priority - Authentication & Config** (30 tests, ~5-6 hours):
   - test_user_profile.py (18 tests) - Remove async/await, simple sync fix
   - test_config.py (12 tests) - Configuration is foundational

2. **High Priority - Core Workflows** (20 tests, ~4-5 hours):
   - test_integration.py (20 tests) - Update to HybridSearch architecture

3. **Medium Priority - Security & E2E** (32 tests, ~5-7 hours):
   - test_password_reset.py (16 tests) - Update settings mocking
   - test_e2e.py (16 tests) - Complex Streamlit mocking

## Common Fix Patterns Identified

1. **Async/Sync Mismatch**: Remove async/await from user_profile tests, change AsyncMock to MagicMock
2. **Settings Mocking**: Replace module variable patches with `get_settings()` mock
3. **Architecture Updates**: Mock HybridSearch/ConnectionManager instead of raw database clients
4. **Streamlit Mocking**: Update UI test mocking patterns for current Streamlit patterns
5. **Singleton Management**: Properly reset singletons between tests (settings, HybridSearch)

## Critical Insights

**All 72 tests in Phase 6 should be fixed** because:
- Tests cover critical functionality (RAG, auth, config, E2E workflows)
- All tested code exists and is actively maintained
- Tests are comprehensive with good coverage
- Failures are due to architecture evolution and mocking patterns, not obsolete code
- Test scenarios and assertions are valid and valuable

**Key Difference from Previous Phases**:
- Phase 1 had 17% DELETE (skeleton tests)
- Phase 2 had 14.5% DELETE (obsolete API)
- Phase 3 had 0% DELETE (all valuable API tests)
- Phase 4 had 0% DELETE (all valuable RAG tests)
- Phase 5 had 0% DELETE (all valuable auth/config tests)
- **Phase 6 has 0% DELETE** - all tests are valuable

**Strategic Importance**:
Phase 6 tests validate **integration across the entire system**:
- test_integration.py: Cross-component integration (RAG + DB + tools + memory)
- test_user_profile.py: Authentication UI integration
- test_e2e.py: Complete user workflows from UI to response
- test_password_reset.py: Security flow integration
- test_config.py: Configuration system used by everything

Fixing Phase 6 tests will provide high-confidence integration test coverage across all major system components.

---
