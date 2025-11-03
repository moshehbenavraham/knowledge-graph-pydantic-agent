# Test Suite Failures Report

**Generated**: 2025-11-03
**Test Execution Time**: 3m 41s
**Total Tests**: 4,194
**Failure Rate**: 5.4% (194 failed + 16 errors)

---

## PHASE 1 COMPLETE (2025-11-03)

**Status**: FIXED
**Files Modified**:
- `tests/agentic_rag/storage/test_connection_manager_comprehensive.py` (4 instances fixed)

**Issue Fixed**: AsyncMock coroutine warnings caused by `return_value=asyncio.sleep(0)` pattern

**Solution Applied**: Changed `AsyncMock(return_value=asyncio.sleep(0))` to `AsyncMock(return_value=None)` since AsyncMock already returns awaitable mocks by default.

**Verification**:
- 207 tests passed with no async coroutine warnings
- All storage tests (145 tests) passing cleanly
- No RuntimeWarning about unawaited coroutines

**Root Cause Analysis**: The warning was caused by creating coroutine objects immediately (`asyncio.sleep(0)`) and assigning them as return values. These coroutines were never awaited, leading to RuntimeWarnings. The fix ensures AsyncMock uses its default behavior of returning awaitable mocks that resolve to None.

---

## Critical Issue: Async Mock Warning

**Priority**: P0 - BLOCKING (RESOLVED)

```
/usr/lib/python3.12/ast.py:52: RuntimeWarning:
coroutine 'AsyncMockMixin._execute_mock_call' was never awaited
```

**Impact**: This warning appears at the top and indicates widespread improper handling of async mocks throughout the test suite. Many test failures may stem from this root cause.

**Root Cause**: Tests are creating async mock objects but not awaiting their coroutine calls, leading to:
- Mock calls not executing properly
- State not being set correctly in tests
- Unreliable test results
- Potential memory leaks from unawaited coroutines

**Fix Strategy**:
1. Search all test files for `AsyncMock` usage
2. Ensure all async mock calls are properly awaited
3. Use `AsyncMock` return values correctly (e.g., `mock.return_value` should be the actual value, not a coroutine)
4. Consider using `pytest-asyncio` fixtures properly

---

## Category 1: Authentication System Failures (76 tests)

**Priority**: P1 - HIGH
**Files Affected**: `tests/auth/*`

### 1.1 Database Authentication Core (12 failures)

**File**: `tests/auth/test_db.py`

```
FAILED tests/auth/test_db.py::TestDBAuthCore::test_create_user_success
FAILED tests/auth/test_db.py::TestDBAuthCore::test_create_user_duplicate_username
FAILED tests/auth/test_db.py::TestDBAuthCore::test_create_user_duplicate_email
FAILED tests/auth/test_db.py::TestDBAuthCore::test_get_user_success
FAILED tests/auth/test_db.py::TestDBAuthCore::test_get_user_not_found
FAILED tests/auth/test_db.py::TestDBAuthCore::test_update_user_success
FAILED tests/auth/test_db.py::TestDBAuthCore::test_delete_user_success
FAILED tests/auth/test_db.py::TestDBAuthCore::test_verify_password_success
FAILED tests/auth/test_db.py::TestDBAuthCore::test_verify_password_failure
FAILED tests/auth/test_db.py::TestDBAuthCore::test_update_password_success
FAILED tests/auth/test_db.py::TestDBAuthCore::test_list_users_pagination
FAILED tests/auth/test_db.py::TestDBAuthCore::test_user_roles_management
```

**Likely Cause**:
- Database connection mocks not properly awaited
- Supabase client async calls not being handled correctly
- Missing database setup/teardown for test isolation

**Required Investigation**:
- Check if Supabase test client is properly mocked
- Verify async database operations are awaited
- Confirm test database state cleanup

### 1.2 OAuth Authentication (20 failures)

**File**: `tests/auth/test_oauth_handler.py`

```
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_init_disabled
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_init_enabled
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_get_authorization_url_google
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_get_authorization_url_github
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_get_authorization_url_invalid_provider
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_handle_oauth_callback_google_success
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_handle_oauth_callback_github_success
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_handle_oauth_callback_error
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_exchange_code_for_token_google
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_exchange_code_for_token_github
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_get_user_info_google
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_get_user_info_github
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_create_or_update_user
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_store_oauth_tokens
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_refresh_access_token
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_revoke_token
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_link_oauth_account
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_unlink_oauth_account
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_get_linked_accounts
FAILED tests/auth/test_oauth_handler.py::TestOAuthHandler::test_encryption_decryption
```

**Likely Cause**:
- HTTP client mocks (httpx) not properly configured for async
- OAuth provider API responses not mocked correctly
- Token encryption/decryption mocks failing
- Database operations for OAuth accounts not awaited

**Required Investigation**:
- Check httpx AsyncClient mocking
- Verify Fernet encryption mocks
- Review database OAuth account operations
- Confirm state parameter handling in OAuth flow

### 1.3 Password Reset Flow (8 failures)

**File**: `tests/auth/test_password_reset.py`

```
FAILED tests/auth/test_password_reset.py::TestPasswordReset::test_generate_reset_token
FAILED tests/auth/test_password_reset.py::TestPasswordReset::test_verify_reset_token_valid
FAILED tests/auth/test_password_reset.py::TestPasswordReset::test_verify_reset_token_expired
FAILED tests/auth/test_password_reset.py::TestPasswordReset::test_verify_reset_token_invalid
FAILED tests/auth/test_password_reset.py::TestPasswordReset::test_send_reset_email
FAILED tests/auth/test_password_reset.py::TestPasswordReset::test_reset_password_success
FAILED tests/auth/test_password_reset.py::TestPasswordReset::test_reset_password_invalid_token
FAILED tests/auth/test_password_reset.py::TestPasswordReset::test_cleanup_expired_tokens
```

**Likely Cause**:
- Email sending mocks (SMTP) not configured
- Token generation/validation async operations
- Database token storage/retrieval not awaited
- Time-based expiration logic failing in tests

**Required Investigation**:
- Check SMTP client mocking
- Verify bcrypt token hashing operations
- Review token expiration datetime handling
- Confirm database cleanup operations

### 1.4 User Profile Management (12 failures)

**File**: `tests/auth/test_user_profile.py`

```
FAILED tests/auth/test_user_profile.py::TestUserProfile::test_get_user_profile_database_mode
FAILED tests/auth/test_user_profile.py::TestUserProfile::test_get_user_profile_yaml_mode
FAILED tests/auth/test_user_profile.py::TestUserProfile::test_update_profile_success
FAILED tests/auth/test_user_profile.py::TestUserProfile::test_change_password_success
FAILED tests/auth/test_user_profile.py::TestUserProfile::test_change_password_wrong_current
FAILED tests/auth/test_user_profile.py::TestUserProfile::test_get_active_sessions
FAILED tests/auth/test_user_profile.py::TestUserProfile::test_revoke_session_success
FAILED tests/auth/test_user_profile.py::TestUserProfile::test_revoke_all_sessions
FAILED tests/auth/test_user_profile.py::TestUserProfile::test_render_profile_ui_database
FAILED tests/auth/test_user_profile.py::TestUserProfile::test_render_profile_ui_yaml
FAILED tests/auth/test_user_profile.py::TestUserProfile::test_profile_analytics_logging
FAILED tests/auth/test_user_profile.py::TestUserProfile::test_profile_error_handling
```

**Likely Cause**:
- Streamlit session state mocking issues
- Database profile operations not awaited
- Session management database queries failing
- Analytics logging mocks not configured

**Required Investigation**:
- Check Streamlit mock configuration
- Verify session database operations
- Review password change flow
- Confirm analytics logger mocking

### 1.5 Security & Rate Limiting (12 failures)

**File**: `tests/auth/test_security.py`

```
FAILED tests/auth/test_security.py::TestRateLimiting::test_rate_limit_enforcement
FAILED tests/auth/test_security.py::TestRateLimiting::test_rate_limit_lockout
FAILED tests/auth/test_security.py::TestRateLimiting::test_rate_limit_reset
FAILED tests/auth/test_security.py::TestRateLimiting::test_rate_limit_cleanup
FAILED tests/auth/test_security.py::TestSecurityValidation::test_password_strength_weak
FAILED tests/auth/test_security.py::TestSecurityValidation::test_password_strength_strong
FAILED tests/auth/test_security.py::TestSecurityValidation::test_username_validation
FAILED tests/auth/test_security.py::TestSecurityValidation::test_email_validation
FAILED tests/auth/test_security.py::TestSecurityAnalytics::test_login_success_logging
FAILED tests/auth/test_security.py::TestSecurityAnalytics::test_login_failure_logging
FAILED tests/auth/test_security.py::TestSecurityAnalytics::test_lockout_logging
FAILED tests/auth/test_security.py::TestSecurityAnalytics::test_password_change_logging
```

**Likely Cause**:
- Time-based rate limiting logic failing
- In-memory rate limit storage not isolated between tests
- Analytics logging mocks not working
- Validation regex patterns not matching

**Required Investigation**:
- Check time.time() or datetime mocking
- Verify rate limit state cleanup between tests
- Review analytics event logging
- Confirm validation function implementations

### 1.6 Streamlit Auth Integration (12 failures)

**File**: `tests/auth/test_streamlit_auth.py`

```
FAILED tests/auth/test_streamlit_auth.py::TestStreamlitAuth::test_require_authentication_success
FAILED tests/auth/test_streamlit_auth.py::TestStreamlitAuth::test_require_authentication_failure
FAILED tests/auth/test_streamlit_auth.py::TestStreamlitAuth::test_render_login_form
FAILED tests/auth/test_streamlit_auth.py::TestStreamlitAuth::test_render_logout_button
FAILED tests/auth/test_streamlit_auth.py::TestStreamlitAuth::test_oauth_button_rendering
FAILED tests/auth/test_streamlit_auth.py::TestStreamlitAuth::test_password_reset_flow
FAILED tests/auth/test_streamlit_auth.py::TestStreamlitAuth::test_session_management
FAILED tests/auth/test_streamlit_auth.py::TestStreamlitAuth::test_cookie_handling
FAILED tests/auth/test_streamlit_auth.py::TestStreamlitAuth::test_mode_switching_database_yaml
FAILED tests/auth/test_streamlit_auth.py::TestStreamlitAuth::test_analytics_integration
FAILED tests/auth/test_streamlit_auth.py::TestStreamlitAuth::test_error_handling
FAILED tests/auth/test_streamlit_auth.py::TestStreamlitAuth::test_authentication_flow_complete
```

**Likely Cause**:
- Streamlit session state mocking complex
- Cookie handling mocks not working
- Authentication flow state transitions failing
- streamlit-authenticator library mocking issues

**Required Investigation**:
- Review Streamlit mocking strategy
- Check cookie manager mocks
- Verify authentication state transitions
- Confirm session state persistence

---

## Category 2: UI/Streamlit Tests (25 failures)

**Priority**: P1 - HIGH
**Files Affected**: `tests/ui/*`

### 2.1 Comprehensive Streamlit App Tests (25 failures)

**File**: `tests/ui/test_streamlit_app_comprehensive.py`

```
FAILED tests/ui/test_streamlit_app_comprehensive.py::TestInitializeSessionState::test_initialize_session_state_creates_messages
FAILED tests/ui/test_streamlit_app_comprehensive.py::TestInitializeSessionState::test_initialize_session_state_creates_mode
FAILED tests/ui/test_streamlit_app_comprehensive.py::TestInitializeSessionState::test_initialize_session_state_creates_tool_visibility
FAILED tests/ui/test_streamlit_app_comprehensive.py::TestInitializeSessionState::test_initialize_session_state_creates_theme
FAILED tests/ui/test_streamlit_app_comprehensive.py::TestInitializeSessionState::test_initialize_session_state_creates_current_page
FAILED tests/ui/test_streamlit_app_comprehensive.py::TestDisplayMessagePart::test_display_message_part_tool_call_with_args
FAILED tests/ui/test_streamlit_app_comprehensive.py::TestDisplayMessagePart::test_display_message_part_tool_return
FAILED tests/ui/test_streamlit_app_comprehensive.py::TestDisplayMessagePart::test_display_message_part_tool_visibility_off
FAILED tests/ui/test_streamlit_app_comprehensive.py::TestExportConversation::test_export_conversation_creates_json
FAILED tests/ui/test_streamlit_app_comprehensive.py::TestExportConversation::test_export_conversation_includes_timestamp
FAILED tests/ui/test_streamlit_app_comprehensive.py::TestExportConversation::test_export_conversation_empty_messages
FAILED tests/ui/test_streamlit_app_comprehensive.py::TestHandleUserInput::test_handle_user_input_simple_mode
FAILED tests/ui/test_streamlit_app_comprehensive.py::TestHandleUserInput::test_handle_user_input_streaming_mode
FAILED tests/ui/test_streamlit_app_comprehensive.py::TestEdgeCases::test_uiconfig_with_missing_config
```

**Likely Cause**:
- Streamlit session_state mocking not persisting across test functions
- Handler class mocks (BaseHandler, StreamingHandler) not configured correctly
- Streamlit UI components (st.chat_message, st.write) not mocked properly
- Session initialization race conditions

**Required Investigation**:
- Review `@patch("streamlit.session_state")` usage
- Check handler instantiation mocks
- Verify UI component call assertions
- Confirm session state initialization order

**Common Pattern**: Many failures involve `initialize_session_state()` not properly setting up the session state dictionary that persists across the test.

---

## Category 3: Constitution Validator CLI (79 failures)

**Priority**: P2 - MEDIUM
**Files Affected**: `tests/unit/constitution_validator/*`

### 3.1 CLI Quiet Mode (14 failures)

**File**: `tests/unit/constitution_validator/test_cli.py`

```
TestQuietMode section (4 tests):
FAILED test_quiet_flag_outputs_only_counts
FAILED test_quiet_mode_exit_code_on_violations
FAILED test_quiet_mode_exit_code_on_success
FAILED test_quiet_mode_suitable_for_scripting
```

**Likely Cause**:
- CLI argument parsing for `--quiet` flag not working
- stdout/stderr capture not configured correctly
- Exit code assertions failing
- Output format not matching expected counts

**Required Investigation**:
- Check argparse mock or actual CLI invocation
- Verify subprocess calls or direct function calls
- Review stdout redirection strategy
- Confirm exit code handling

### 3.2 CLI Dry Run Mode (3 failures)

```
TestDryRunMode section (3 tests):
FAILED test_dry_run_shows_files_to_check
FAILED test_dry_run_shows_rules_to_execute
FAILED test_dry_run_output_format
```

**Likely Cause**:
- Dry run flag not preventing actual validation
- File discovery output not captured
- Rule listing output format mismatch
- Mock filesystem not set up correctly

**Required Investigation**:
- Check `--dry-run` argument handling
- Verify file discovery is mocked
- Review rule registry output format
- Confirm no actual validation runs

### 3.3 Pre-Commit Hook Integration (5 failures)

```
TestPreCommitHookIntegration section (5 tests):
FAILED test_hook_blocks_commit_with_violations
FAILED test_hook_allows_commit_without_violations
FAILED test_incremental_validation_performance
FAILED test_hook_shows_violation_summary_on_failure
FAILED test_hook_exit_code_matches_validation_result
```

**Likely Cause**:
- Git hook execution environment not mocked
- File staging detection not working
- Exit codes not propagating correctly
- Performance timing assertions too strict

**Required Investigation**:
- Check subprocess.run mocking for git commands
- Verify staged file detection logic
- Review exit code return path
- Adjust performance timing tolerances

### 3.4 CLI Argument Parsing (2 failures)

```
TestCLIArgumentParsing section (2 tests):
FAILED test_accepts_file_paths
FAILED test_accepts_directory_paths
```

**Likely Cause**:
- argparse configuration not handling file/directory paths
- Path validation failing
- Mock filesystem paths not recognized
- OS path separator issues

**Required Investigation**:
- Check argparse setup for positional arguments
- Verify pathlib or os.path usage
- Review mock filesystem structure
- Confirm cross-platform path handling

### 3.5 Principle II Rule Tests (2 failures)

**File**: `tests/unit/constitution_validator/test_rules_principle_ii.py`

```
FAILED test_inline_suppression_with_noqa
FAILED test_inline_suppression_without_reason
```

**Likely Cause**:
- AST parsing of inline suppression comments failing
- Regex pattern for `# noqa` comments not matching
- Suppression reason extraction logic broken
- Test fixtures not providing correct code samples

**Required Investigation**:
- Check AST visitor implementation for comments
- Verify regex pattern for suppression syntax
- Review comment extraction from AST
- Confirm test input code formatting

### 3.6 Additional Constitution Validator Failures (53 failures)

These appear to span multiple test files in the constitution validator suite. Common patterns likely include:

- **AST parsing issues**: Python 3.12 AST changes may have broken some visitors
- **Rule execution**: Rule registry or rule execution engine issues
- **File I/O mocking**: Validation reading files that don't exist in test environment
- **Validation logic**: Core validation algorithms producing unexpected results

**Required Investigation**:
- Run individual test files to identify specific failure patterns
- Check Python 3.12 AST compatibility
- Review mock filesystem setup across all tests
- Verify rule registry initialization

---

## Category 4: Google Drive Integration (16 errors)

**Priority**: P3 - LOW
**File**: `tests/rag_pipeline/sources/test_google_drive.py`

**All 16 tests in this file errored out completely** (not just failed):

```
ERROR tests/rag_pipeline/sources/test_google_drive.py::TestGoogleDriveWatcher::test_init_and_load_config
ERROR tests/rag_pipeline/sources/test_google_drive.py::TestGoogleDriveWatcher::test_save_last_check_time
ERROR tests/rag_pipeline/sources/test_google_drive.py::TestGoogleDriveWatcher::test_authenticate_no_token
ERROR tests/rag_pipeline/sources/test_google_drive.py::TestGoogleDriveWatcher::test_authenticate_valid_token
ERROR tests/rag_pipeline/sources/test_google_drive.py::TestGoogleDriveWatcher::test_authenticate_expired_token_refresh_success
ERROR tests/rag_pipeline/sources/test_google_drive.py::TestGoogleDriveWatcher::test_authenticate_expired_token_refresh_failure
ERROR tests/rag_pipeline/sources/test_google_drive.py::TestGoogleDriveWatcher::test_get_folder_contents_recursive
ERROR tests/rag_pipeline/sources/test_google_drive.py::TestGoogleDriveWatcher::test_get_changes_with_folder_id
ERROR tests/rag_pipeline/sources/test_google_drive.py::TestGoogleDriveWatcher::test_get_changes_no_folder_id
ERROR tests/rag_pipeline/sources/test_google_drive.py::TestGoogleDriveWatcher::test_download_file_regular
ERROR tests/rag_pipeline/sources/test_google_drive.py::TestGoogleDriveWatcher::test_download_file_google_workspace
ERROR tests/rag_pipeline/sources/test_google_drive.py::TestGoogleDriveWatcher::test_process_file_trashed
ERROR tests/rag_pipeline/sources/test_google_drive.py::TestGoogleDriveWatcher::test_process_file_unsupported_mime_type
ERROR tests/rag_pipeline/sources/test_google_drive.py::TestGoogleDriveWatcher::test_process_file_success
ERROR tests/rag_pipeline/sources/test_google_drive.py::TestGoogleDriveWatcher::test_check_for_deleted_files
ERROR tests/rag_pipeline/sources/test_google_drive.py::TestGoogleDriveWatcher::test_watch_for_changes_initial_scan_and_loop
```

**Likely Cause**:
- Import errors (Google Drive dependencies not installed)
- Test setup/teardown errors in class fixture
- Missing Google API credentials/mocks causing immediate failure
- Class initialization failing before any test runs

**Required Investigation**:
- Check if `google-api-python-client` is in test dependencies
- Review test class `setup_method` or `teardown_method`
- Verify Google OAuth mock configuration
- Check for missing test fixtures or conftest.py setup

**Note**: "ERROR" status means the test didn't even run - it failed during collection or setup. This is more severe than "FAILED".

---

## Summary Statistics

| Category | Failed | Errors | Total Issues | Priority |
|----------|--------|--------|--------------|----------|
| Async Mock Warning | - | 1 | 1 | P0 |
| Authentication System | 76 | 0 | 76 | P1 |
| UI/Streamlit Tests | 25 | 0 | 25 | P1 |
| Constitution Validator | 79 | 0 | 79 | P2 |
| Google Drive Integration | 0 | 16 | 16 | P3 |
| **TOTAL** | **180** | **17** | **197** | - |

## Recommended Fix Order

### Phase 1: Foundation (P0)
1. **Fix async mock warning** - This is likely causing cascading failures
   - Search for all `AsyncMock` usage in tests
   - Ensure proper `await` patterns
   - Update test fixtures to handle async properly
   - **Estimated Impact**: May resolve 30-50% of failures automatically

### Phase 2: High Priority (P1) - 101 failures
2. **Authentication system** (76 failures)
   - Start with core database operations (test_db.py)
   - Then OAuth handler (test_oauth_handler.py)
   - Then Streamlit integration (test_streamlit_auth.py)
   - Finally security, password reset, and user profile

3. **UI tests** (25 failures)
   - Fix session state mocking strategy first
   - Then handler instantiation
   - Finally UI component assertions

### Phase 3: Medium Priority (P2) - 79 failures
4. **Constitution validator CLI**
   - Fix argument parsing first (foundation)
   - Then quiet mode and dry-run
   - Then pre-commit hook integration
   - Finally individual rule tests

### Phase 4: Low Priority (P3) - 16 errors
5. **Google Drive integration**
   - Fix import/setup errors
   - Add proper dependency management
   - Update test fixtures

---

## Testing Infrastructure Improvements Needed

1. **Async Test Pattern Standardization**
   - Create standard fixtures for async mocks
   - Document async testing patterns
   - Use `pytest-asyncio` consistently

2. **Streamlit Mocking Strategy**
   - Create reusable Streamlit session state fixtures
   - Mock UI components consistently
   - Document Streamlit testing approach

3. **Test Isolation**
   - Ensure database state cleanup between tests
   - Reset global state (rate limiters, caches)
   - Use test-specific temp directories

4. **Test Performance**
   - Suite ran in 3m 41s (much faster than expected 10-15m)
   - May indicate tests not running properly or skipping slow operations
   - Review if integration tests are actually hitting databases

5. **Continuous Integration**
   - Set up test result tracking over time
   - Add failure notifications
   - Consider running subsets in parallel

---

## Next Steps

1. Run individual failing test files with verbose output to get full error messages
2. Fix async mock warning first (highest ROI)
3. Create fix branches for each category
4. Update test documentation with patterns discovered
5. Add test coverage for fixed areas to prevent regressions

---

## Investigation Commands

```bash
# Run specific failing test with full output
pytest tests/auth/test_db.py::TestDBAuthCore::test_create_user_success -vv

# Run entire auth test suite
pytest tests/auth/ -v

# Run with warnings enabled
pytest tests/auth/ -v -W all

# Run and capture print statements
pytest tests/auth/ -v -s

# Run and stop on first failure
pytest tests/auth/ -x

# Run specific category
pytest tests/ui/ -v
pytest tests/unit/constitution_validator/ -v
pytest tests/rag_pipeline/sources/test_google_drive.py -v
```
