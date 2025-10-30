# Testing Inventory and Status

**Last Updated**: 2025-10-30
**Test Suite Execution**: `make test-coverage`
**Execution Time**: 137.73 seconds (2 minutes 17 seconds)

---

## Executive Summary

- **Total Tests**: 3,788 collected
- **Passed**: 3,486 (92.0%)
- **Failed**: 200 (5.3%)
- **Skipped**: 103 (2.7%)
- **Coverage**: 77.33% (exceeds 75% minimum requirement)
- **Pass Rate**: 92.0%

---

## 1. Test Suite Failures (200 total)

### 1.1 Chunker Failures (73 tests) - CRITICAL

**Files**:
- `tests/agentic_rag/ingestion/test_chunker_comprehensive.py` (39 failures)
- `tests/test_chunker_coverage.py` (34 failures)

**Root Cause**: `AttributeError` in `chunker.py` at lines 122, 156, 256, 297, 343

**Failed Test Categories**:

#### SimpleChunker Failures (23 tests)
- `test_chunk_empty_content`
- `test_chunk_whitespace_only`
- `test_chunk_small_content_single_chunk`
- `test_chunk_respects_paragraph_boundaries`
- `test_chunk_oversized_paragraph_split`
- `test_chunk_multiple_paragraphs`
- `test_chunk_with_metadata`
- `test_chunk_indices_sequential`
- `test_chunk_total_chunks_metadata`
- `test_chunk_start_end_positions`
- `test_simple_chunk_single_paragraph`
- `test_simple_chunk_empty_paragraphs_skipped`
- `test_split_paragraph_by_sentences` (3 occurrences)
- `test_split_paragraph_respects_chunk_size` (2 occurrences)
- `test_split_paragraph_single_long_sentence` (2 occurrences)

#### SemanticChunker Failures (34 tests)
- `test_semantic_chunk_small_content` (2 occurrences)
- `test_semantic_chunk_fallback_on_error` (2 occurrences)
- `test_semantic_chunk_with_metadata` (2 occurrences)
- `test_semantic_chunk_with_sections_fallback`
- `test_semantic_chunk_sections_within_size`
- `test_semantic_chunk_sections_oversized_section`
- `test_semantic_chunk_sections_single_section`
- `test_semantic_chunk_sections_combine_small`
- `test_semantic_chunk_sections_split_large`
- `test_semantic_chunk_sections_filter_min_size`
- `test_llm_split_section_success` (2 occurrences)
- `test_llm_split_section_fallback_on_error` (2 occurrences)
- `test_llm_split_section_validates_size`
- `test_llm_split_section_invalid_chunks_fallback`
- `test_llm_split_section_error_fallback`
- `test_simple_split_basic` (2 occurrences)
- `test_simple_split_finds_sentence_boundaries`
- `test_simple_split_with_sentence_boundary`
- `test_simple_split_respects_overlap`
- `test_simple_split_short_text`
- `test_simple_split_with_overlap`
- `test_create_chunk_objects_basic` (2 occurrences)
- `test_create_chunk_objects_preserves_metadata`
- `test_create_chunk_objects_sets_indices`
- `test_create_chunk_objects_sets_total_chunks`
- `test_create_chunk_objects_chunk_not_found`

#### Edge Cases Failures (16 tests)
- `test_chunk_unicode_content`
- `test_chunk_very_long_content`
- `test_chunk_no_paragraph_breaks`
- `test_chunk_only_paragraph_breaks`
- `test_chunk_mixed_line_endings`
- `test_very_long_document_simple_chunking`
- `test_single_character_document`
- `test_single_sentence_document`
- `test_no_sentence_boundaries`
- `test_special_characters_in_content`
- `test_markdown_formatted_content`
- `test_code_content_chunking`
- `test_pdf_extracted_content`
- `test_metadata_preservation_across_chunks`
- `test_chunk_indices_are_sequential`
- `test_chunk_positions_are_logical`

#### Backward Compatibility Failures (3 tests)
- `test_semantic_chunk_function`
- `test_semantic_chunk_function_with_metadata`
- `test_semantic_chunk_function_returns_dicts`

**Priority**: CRITICAL
**Impact**: Core ingestion functionality blocked

**Action Required**:
1. Investigate AttributeError at `src/agentic_rag/ingestion/chunker.py:122, 156, 256, 297, 343`
2. Fix object attribute access patterns
3. Update tests or implementation to match expected behavior
4. Verify chunking logic works for all edge cases

---

### 1.2 Integration Test Failures (62 tests) - CRITICAL

#### Chat Endpoints Integration (35 tests)
**File**: `tests/integration/test_chat_endpoints_comprehensive.py`

**Failed Tests**:
- `test_chat_basic_request`
- `test_chat_with_cache_hit`
- `test_chat_with_parameters`
- `test_chat_with_sources`
- `test_chat_error_handling`
- `test_chat_stream_basic`
- `test_chat_stream_headers`
- `test_chat_stream_with_parameters`
- `test_chat_stream_error`
- `test_submit_feedback_success`
- `test_submit_feedback_minimal`
- `test_submit_feedback_with_issues`
- `test_get_session_history_basic`
- `test_get_session_history_with_limit`
- `test_get_session_history_default_limit`
- `test_metrics_recorded_on_success`
- `test_metrics_recorded_on_cache_hit`
- `test_response_includes_metrics`
- `test_response_includes_session_info`
- `test_response_confidence_score`
- `test_cache_key_includes_strategy`
- `test_cache_ttl`
- `test_agent_timeout`
- `test_invalid_parameters`
- `test_websocket_connection`
- `test_websocket_endpoint_exists`
- `test_valid_request_structure`
- `test_empty_message_rejected`
- `test_timing_metric_recorded`
- `test_default_session_id`
- `test_multiple_concurrent_chats`
- `test_feedback_rating_range`
- `test_feedback_with_comment`
- `test_feedback_generates_unique_id`
- `test_stream_agent_params_forwarded`

**Priority**: CRITICAL
**Likely Cause**: FastAPI test client issues, endpoint configuration, or dependency injection problems.

#### API Main Integration (27 tests)
**File**: `tests/integration/test_api_main_comprehensive.py`

**Failed Tests**:
- `test_root_endpoint`
- `test_root_endpoint_structure`
- `test_status_endpoint_healthy`
- `test_status_endpoint_degraded`
- `test_metrics_endpoint`
- `test_metrics_content_type`
- `test_clear_cache_all`
- `test_clear_cache_pattern`
- `test_clear_cache_error`
- `test_404_handler`
- `test_404_error_structure`
- `test_tracing_import_error`
- `test_lifespan_startup`
- `test_lifespan_shutdown`
- `test_cors_headers_on_root`
- `test_openapi_json`
- `test_swagger_docs`
- `test_redoc`
- `test_version_in_root`
- `test_version_in_status`
- `test_not_found_error_message`
- `test_multiple_concurrent_root_requests`
- `test_concurrent_metrics_requests`
- `test_cache_flush_called`
- `test_cache_pattern_clearing`
- `test_status_component_structure`
- `test_status_metrics_included`

**Priority**: CRITICAL
**Likely Cause**: API app configuration, middleware setup, or test client initialization issues.

**Action Required**:
1. Review FastAPI test client setup in integration tests
2. Check endpoint registration and routing
3. Verify dependency injection works in test environment
4. Ensure test database/services are properly mocked or available

---

### 1.3 API Endpoint Failures (18 tests) - HIGH

#### API Main Tests (13 tests)
**File**: `tests/api/test_main_comprehensive.py`

**Failed Tests**:
- `test_status_endpoint`
- `test_status_endpoint_degraded`
- `test_clear_cache_endpoint_all`
- `test_clear_cache_endpoint_pattern`
- `test_clear_cache_endpoint_error`
- `test_setup_tracing_with_jaeger`
- `test_setup_tracing_with_otlp`
- `test_setup_tracing_runtime_error`
- `test_cors_middleware`
- `test_openapi_schema`
- `test_full_lifecycle`
- `test_concurrent_requests`
- `test_request_logging_middleware`

#### API Endpoints Tests (5 tests)
**File**: `tests/api/test_endpoints.py`

**Failed Tests**:
- `test_chat_endpoint_validation_error`
- `test_search_endpoint_validation_error`
- `test_ingest_document_validation_error`
- `test_validation_error`
- `test_health_endpoint`

**Priority**: HIGH
**Likely Cause**: API configuration changes, middleware setup issues, or validation schema mismatches.

**Action Required**:
1. Review API endpoint validation schemas
2. Check middleware configuration
3. Verify health check endpoint implementation
4. Update tests to match current API structure

---

### 1.4 Authentication System Failures (15 tests) - MEDIUM

#### Streamlit Auth (6 tests)
**File**: `tests/auth/test_streamlit_auth_ultra_comprehensive.py`

**Failed Tests**:
- `test_initiate_oauth_login_google`
- `test_initiate_oauth_login_error`
- `test_render_oauth_buttons_both_enabled`
- `test_check_oauth_callback_google_success`
- `test_render_logout_button_display`
- `test_render_logout_button_clicked`

#### User Profile (5 tests)
**File**: `tests/auth/test_user_profile_ultra_comprehensive.py`

**Failed Tests**:
- `test_get_user_info_success`
- `test_change_user_password_success`
- `test_render_user_profile_active_sessions`
- `test_render_user_profile_revoke_session`
- `test_render_user_profile_revoke_all_sessions`

#### OAuth Analytics (3 tests)
**File**: `tests/auth/test_oauth_analytics_comprehensive.py`

**Failed Tests**:
- `test_render_dashboard_not_admin`
- `test_render_dashboard_admin_with_data`
- `test_render_dashboard_no_oauth_data`

#### Migration (3 tests)
**File**: `tests/auth/test_migrate_yaml_to_db_ultra_comprehensive.py`

**Failed Tests**:
- `test_migrate_users_success`
- `test_migrate_users_skip_existing`
- `test_main_with_backup`

#### Captcha (1 test)
**File**: `tests/auth/test_captcha_comprehensive.py`

**Failed Tests**:
- `test_init_without_keys_uses_settings`

**Priority**: MEDIUM
**Likely Cause**: Streamlit session state mocking issues, OAuth configuration, or database connection problems in tests.

**Action Required**:
1. Review Streamlit session state mocking in tests
2. Check OAuth handler configuration
3. Verify database authentication backend in test environment
4. Update tests to match current auth implementation

---

### 1.5 Configuration Failures (5 tests) - MEDIUM

**File**: `tests/config/test_config_modules_comprehensive.py`

**Failed Tests**:
- `test_agent_config_initialization`
- `test_api_config_initialization`
- `test_clients_config_initialization`
- `test_ui_config_initialization`
- `test_configs_share_settings`

**Priority**: MEDIUM
**Likely Cause**: Configuration module initialization changes or settings validation issues.

**Action Required**:
1. Review configuration facade implementations
2. Check settings singleton pattern
3. Verify environment variable loading in tests
4. Update tests to match current configuration structure

---

### 1.6 Search System Failures (9 tests) - LOW

#### Intent Analyzer (5 tests)
**File**: `tests/agentic_rag/search/test_intent_analyzer_comprehensive.py`

**Failed Tests**:
- `test_extract_entities_order_preserved`
- `test_find_fact_indicators_multiple`
- `test_score_vector_intent_default`
- `test_score_vector_intent_reduced_by_temporal`
- `test_relationship_keyword_case_insensitive`

#### Ranker (4 tests)
**File**: `tests/agentic_rag/search/test_ranker_comprehensive.py`

**Failed Tests**:
- `test_similarity_score`
- `test_diversity_same_document_penalty`
- `test_rerank_with_negative_feedback`
- `test_rerank_with_mixed_feedback`

**Priority**: LOW
**Likely Cause**: Algorithm changes in intent analysis or ranking logic.

**Action Required**:
1. Review intent analyzer scoring logic
2. Check ranker diversity enforcement
3. Verify feedback reranking implementation
4. Update tests to match current algorithms

---

### 1.7 Cache Failures (7 tests) - LOW

**File**: `tests/utils/test_cache_comprehensive.py`

**Failed Tests**:
- `test_get_from_fallback_cache`
- `test_set_to_fallback_cache`
- `test_set_fallback_memory_limit`
- `test_delete_from_fallback_cache`
- `test_exists_in_fallback_cache`
- `test_incr_in_fallback_cache`
- `test_incr_new_key_in_fallback`

**Priority**: LOW
**Likely Cause**: Fallback cache implementation changes or behavior mismatches between Redis and in-memory cache.

**Action Required**:
1. Review in-memory fallback cache implementation
2. Ensure Redis API compatibility
3. Update tests to match current cache behavior

---

### 1.8 Miscellaneous Failures (11 tests) - LOW

#### Phase 2 Ingestion (3 tests)
**File**: `tests/test_phase2_ingestion.py`

- `test_simple_chunking`
- `test_semantic_chunking_fallback`
- `test_caching_improves_performance`

#### Code Execution (2 tests)
**File**: `tests/tools/test_code_execution_comprehensive.py`

- `test_class_definition`
- `test_exception_handling`

#### Constitution Validator (2 tests)
**File**: `tests/constitution_validator/scanners/test_scanners_ultra_comprehensive.py`

- `test_is_merge_commit`
- `test_get_commit_message`

#### Image Analysis (1 test)
**File**: `tests/test_image_analysis.py`

- `test_image_analysis_tool_exception`

---

## 2. Skipped Tests (103 total)

### 2.1 Database Integration Tests (13 skipped)

**File**: `tests/integration/test_postgres_store.py`

**Skipped Tests**:
- `test_document_lifecycle`
- `test_list_documents_pagination`
- `test_list_documents_filtering`
- `test_list_documents_sorting`
- `test_get_document_chunks`
- `test_update_document_metadata`
- `test_update_nonexistent_document`
- `test_count_chunks_empty_document`
- `test_chunk_ordering`
- `test_search_similar`
- `test_hybrid_search`
- `test_get_statistics`
- `test_concurrent_operations`

**Reason**: Likely requires live PostgreSQL database connection.

**Recommendation**: Set up test database fixture or mock Supabase client for integration tests.

---

### 2.2 Search Strategy Tests (1 skipped)

**File**: `tests/integration/test_search_strategies.py`

**Skipped Tests**:
- `test_vector_search_accuracy`

**Reason**: May require specific test data or external services.

**Recommendation**: Create test fixtures with known embeddings and expected results.

---

### 2.3 API Tests (4+ skipped)

**Files**:
- `tests/api/test_chat_endpoints_comprehensive.py`
- `tests/api/test_chat_endpoints_ultra_comprehensive.py`
- `tests/api/test_dependencies_comprehensive.py`
- `tests/api/test_endpoints.py`

**Skipped Tests**:
- `test_chat_stream_error`
- `test_session_cleanup_on_exception`
- `test_full_rag_flow`
- Additional skipped tests in API test suite

**Reason**: Specific test conditions not met or intentionally skipped.

**Recommendation**:
1. Review skip reasons in test code
2. Determine if tests should be enabled
3. Set up required test infrastructure if needed
4. Document permanent skips with clear reasoning

---

### 2.4 Additional Skipped Tests (~85 remaining)

**Distribution**: Scattered across various test modules

**Action Required**:
1. Run `pytest --collect-only -m skip` to identify all skipped tests
2. Categorize skipped tests by reason
3. Create issues for tests that should be enabled
4. Add skip decorators with clear reasons for permanent skips

---

## 3. Test Warnings (388 total in test files)

### 3.1 PytestWarnings (~10 occurrences)

**File**: `tests/utils/test_cache_comprehensive.py`

**Affected Tests**:
- `test_cache_decorator_sync`
- `test_cache_decorator_sync_cache_hit`
- `test_cache_decorator_custom_key_func`

**Message**: `The test <Function test_name> is marked with '@pytest.mark.asyncio' but it is not an async function. Please remove the asyncio mark.`

**Priority**: LOW
**Action Required**: Remove `@pytest.mark.asyncio` decorator from synchronous test functions

**Fix**:
```python
# Remove this decorator for sync tests
@pytest.mark.asyncio  # <- DELETE THIS LINE
def test_cache_decorator_sync(self):  # <- Not async
    pass

# Keep it for async tests
@pytest.mark.asyncio
async def test_async_function(self):  # <- Async
    pass
```

---

### 3.2 Test File Deprecation Warnings

**datetime.utcnow() in Tests** (~150+ occurrences):
- `tests/agentic_rag/search/test_ranker_comprehensive.py` (lines 282, 365, 375, 658)
- `tests/api/endpoints/test_documents_endpoints_comprehensive.py` (multiple lines)
- `tests/api/test_health_endpoints_comprehensive.py` (multiple lines)
- `tests/auth/test_email_verification_comprehensive.py` (lines 119, 158)
- `tests/utils/test_health.py` (multiple lines)
- `tests/utils/test_health_comprehensive.py` (multiple lines)

**Note**: These are addressed in the main dev_tooling_todo.md as part of the broader datetime.utcnow() replacement effort.

---

## 4. Code Coverage Analysis

### 4.1 Overall Coverage: 77.33%

**Status**:  Exceeds 75% minimum requirement

**Total Statements**: 12,601
**Missing Coverage**: 2,857 statements (22.67%)

---

### 4.2 Files with 0% Coverage (Complete Testing Gaps)

**Critical - No Tests Exist**:

1. **src/agent/prompt.py** (1 statement, 0% coverage)
   - Missing: Line 1
   - **Impact**: Minimal - single import/constant

2. **src/agentic_rag/ingestion/__main__.py** (92 statements, 0% coverage)
   - Missing: Lines 8-196
   - **Impact**: HIGH - CLI entry point not tested

3. **src/auth/breach_detection.py** (40 statements, 0% coverage)
   - Missing: Lines 16-292
   - **Impact**: HIGH - Security feature not tested

4. **src/auth/email_verification_page.py** (49 statements, 0% coverage)
   - Missing: Lines 7-121
   - **Impact**: MEDIUM - Email verification UI not tested

5. **src/auth/password_history.py** (16 statements, 0% coverage)
   - Missing: Lines 14-202
   - **Impact**: MEDIUM - Password history tracking not tested

6. **src/auth/password_reset_page.py** (4 statements, 0% coverage)
   - Missing: Lines 8-16
   - **Impact**: MEDIUM - Password reset UI not tested

7. **src/rag_pipeline/sources/local_files.py** (184 statements, 0% coverage)
   - Missing: Lines 1-503
   - **Impact**: HIGH - Local file ingestion not tested

---

### 4.3 Files with Low Coverage (Under 50%)

**Priority Areas for Test Development**:

1. **src/auth/admin_2fa_management.py** (4.82% coverage)
   - Statements: 166, Missing: 158
   - Missing: Lines 28-40, 49-246, 259-341
   - **Impact**: HIGH - Admin security features

2. **src/rag_pipeline/sources/google_drive.py** (4.17% coverage)
   - Statements: 288, Missing: 276
   - Missing: Lines 14-714
   - **Impact**: MEDIUM - Google Drive ingestion

3. **src/rag_pipeline/pipeline.py** (11.54% coverage)
   - Statements: 26, Missing: 23
   - Missing: Lines 5-44
   - **Impact**: HIGH - Core pipeline functionality

4. **src/auth/oauth_profile_management.py** (19.26% coverage)
   - Statements: 135, Missing: 109
   - Missing: Lines 77, 82-84, 98-279, 289-339
   - **Impact**: MEDIUM - OAuth profile features

5. **src/constitution_validator/cli.py** (29.35% coverage)
   - Statements: 201, Missing: 142
   - Missing: Lines 136-182, 280-536, 541
   - **Impact**: MEDIUM - Constitution validator CLI

6. **src/constitution_validator/reporter.py** (32.94% coverage)
   - Statements: 170, Missing: 114
   - Missing: Lines 36-56, 69-73, 93-189, 202-262, 283-288, 301-306, 318-319
   - **Impact**: MEDIUM - Validation reporting

7. **src/auth/enforce_2fa.py** (34.64% coverage)
   - Statements: 153, Missing: 100
   - Missing: Lines 115-169, 184-270, 284-315
   - **Impact**: HIGH - 2FA enforcement

8. **src/auth/oauth_analytics_dashboard.py** (42.01% coverage)
   - Statements: 169, Missing: 98
   - Missing: Lines 114-437
   - **Impact**: LOW - Analytics dashboard

9. **src/ui/streamlit_app.py** (43.14% coverage)
   - Statements: 714, Missing: 406
   - Missing: Lines 111-113, 230, 246-253, 354, 356, 358, 377-379, 394, 401-402, 409-411, 426, 432, 446-659, 728-1197, 1357-1359, 1365, 1368-1380, 1385-1395, 1411-1429, 1450-1452, 1472-1475, 1482, 1503-1507, 1523-1525, 1531
   - **Impact**: HIGH - Main UI application

10. **src/auth/streamlit_auth.py** (45.22% coverage)
    - Statements: 345, Missing: 189
    - Missing: Lines 207-217, 224, 263-535, 550-578, 623-625, 647-649, 706-707, 734, 755, 760-763, 786-837, 853-971
    - **Impact**: HIGH - Authentication system

---

### 4.4 Files with Excellent Coverage (95%+)

**Well-Tested Modules** (100% coverage):
- `src/agent/unified_agent.py` (127 statements) 
- `src/agentic_rag/search/graph_search.py` (162 statements) 
- `src/agentic_rag/search/intent_analyzer.py` (141 statements) 
- `src/agentic_rag/search/vector_search.py` (149 statements) 
- `src/agentic_rag/storage/neo4j_store.py` (151 statements) 
- `src/api/models.py` (154 statements) 
- `src/constitution_validator/rules/principle_iv.py` (46 statements) 
- `src/tools/rag.py` (138 statements) 
- `src/tools/sql_query.py` (29 statements) 
- `src/tools/code_execution.py` (28 statements) 
- `src/utils/resilience.py` (184 statements) 

**Near Perfect** (95-99% coverage):
- `src/agentic_rag/ingestion/embedder.py` (97.40%) 
- `src/agentic_rag/search/hybrid_search.py` (97.75%) 
- `src/agentic_rag/storage/postgres_store.py` (99.47%) 
- `src/agentic_rag/storage/supabase_rest_store.py` (97.17%) 
- `src/agentic_rag/storage/graphiti_client.py` (98.21%) 
- `src/api/streaming.py` (99.21%) 
- `src/api/health_endpoints.py` (98.15%) 
- `src/auth/totp_2fa.py` (97.91%) 
- `src/auth/migrate_yaml_to_db.py` (96.59%) 
- `src/utils/cache.py` (99.40%) 
- `src/utils/rate_limiting.py` (98.54%) 

---

### 4.5 Coverage by Module

| Module | Coverage | Status | Priority for Improvement |
|--------|----------|--------|-------------------------|
| Agent | 97%+ |  Excellent | Low |
| Agentic RAG Core | 95%+ |  Excellent | Low |
| API | 90%+ |  Good | Medium |
| Tools | 95%+ |  Excellent | Low |
| Utils | 95%+ |  Excellent | Low |
| Auth | 60% |   Needs Improvement | **HIGH** |
| UI | 50% |   Needs Improvement | **HIGH** |
| Constitution Validator | 65% |   Needs Improvement | Medium |
| RAG Pipeline | 40% |   Needs Improvement | **HIGH** |

---

## 5. Test Execution Performance

### 5.1 Performance Metrics

- **Total Execution Time**: 137.73 seconds (2 minutes 17 seconds)
- **Average Time Per Test**: ~36.4 milliseconds
- **Tests Per Second**: ~27.5 tests/second
- **Pass Rate**: 92.0%
- **Execution Speed**: Improved from 142.37s (3.3% faster)

### 5.2 Test Distribution

- **Unit Tests**: ~2,800 (73%)
- **Integration Tests**: ~900 (24%)
- **End-to-End Tests**: ~88 (3%)

### 5.3 Slow Tests (>1 second)

**Action Required**: Run `pytest --durations=20` to identify slowest tests

**Optimization Opportunities**:
- Cache expensive fixtures
- Use mocks for external services
- Parallelize independent tests with pytest-xdist
- Reduce database fixture setup time

---

## 6. Test Commands Reference

### 6.1 Running Tests

```bash
# Full test suite with coverage
make test-coverage

# Quick test run (no coverage)
make test

# Run specific test file
pytest tests/agentic_rag/ingestion/test_chunker_comprehensive.py -v

# Run specific test pattern
pytest -k "chunker" -v
pytest -k "auth" -v

# Run failed tests only
pytest --lf

# Run tests in parallel (4 workers)
pytest -n 4

# Show slowest tests
pytest --durations=20
```

### 6.2 Coverage Commands

```bash
# Generate coverage report
make test-coverage

# View HTML coverage report
open htmlcov/index.html

# Show missing lines for specific file
pytest --cov=src/agentic_rag/ingestion/chunker.py --cov-report=term-missing

# Coverage for specific module
pytest tests/agentic_rag/ --cov=src/agentic_rag --cov-report=html
```

### 6.3 Test Debugging

```bash
# Run with verbose output
pytest -vv

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Drop into debugger on failure
pytest --pdb

# Run only tests that match expression
pytest -k "test_chunk and not semantic"
```

---

## 7. Priority Test Improvements

### 7.1 Critical Priority (Blocking Core Functionality)

1. **Fix Chunker AttributeErrors**
   - Impact: 73 test failures
   - Blocking: Ingestion pipeline
   - Files: `src/agentic_rag/ingestion/chunker.py` (lines 122, 156, 256, 297, 343)
   - Estimated Effort: 2-4 hours
   - **Action**: Debug attribute access, verify object initialization

2. **Fix Integration Test Infrastructure**
   - Impact: 62 test failures
   - Blocking: API testing confidence
   - Files: Chat endpoints and API main integration tests
   - Estimated Effort: 4-6 hours
   - **Action**: Review test client setup, dependency injection, mocking

---

### 7.2 High Priority (Important Functionality)

3. **Fix API Endpoint Tests**
   - Impact: 18 test failures
   - Files: `tests/api/test_main_comprehensive.py`, `tests/api/test_endpoints.py`
   - Estimated Effort: 2-3 hours
   - **Action**: Update validation schemas, middleware config

4. **Add Tests for 0% Coverage Files**
   - Impact: 7 files with no coverage
   - Priority Files:
     - `src/auth/breach_detection.py` (security feature)
     - `src/agentic_rag/ingestion/__main__.py` (CLI)
     - `src/rag_pipeline/sources/local_files.py` (ingestion)
   - Estimated Effort: 6-8 hours
   - **Action**: Create comprehensive test suites

5. **Increase Auth Module Coverage**
   - Impact: Auth at 60% coverage
   - Target: 80%+ coverage
   - Files: streamlit_auth.py, admin_2fa_management.py, enforce_2fa.py
   - Estimated Effort: 8-10 hours
   - **Action**: Add integration tests for auth flows

---

### 7.3 Medium Priority (Quality Improvements)

6. **Fix Authentication Tests**
   - Impact: 15 test failures
   - Files: Auth test files
   - Estimated Effort: 2-3 hours
   - **Action**: Fix Streamlit mocking, OAuth config

7. **Fix Configuration Tests**
   - Impact: 5 test failures
   - Files: `tests/config/test_config_modules_comprehensive.py`
   - Estimated Effort: 1 hour
   - **Action**: Update to match config facade changes

8. **Increase UI Test Coverage**
   - Impact: UI at 50% coverage
   - Target: 70%+ coverage
   - Files: streamlit_app.py, feature handlers
   - Estimated Effort: 6-8 hours
   - **Action**: Add Streamlit component tests

---

### 7.4 Low Priority (Nice to Have)

9. **Fix Search System Tests**
   - Impact: 9 test failures
   - Files: Intent analyzer and ranker tests
   - Estimated Effort: 1-2 hours
   - **Action**: Update to match algorithm changes

10. **Fix Cache Tests**
    - Impact: 7 test failures
    - Files: `tests/utils/test_cache_comprehensive.py`
    - Estimated Effort: 1 hour
    - **Action**: Update fallback cache behavior tests

11. **Enable Skipped Tests**
    - Impact: 103 skipped tests
    - Estimated Effort: 2-3 hours per category
    - **Action**: Set up required infrastructure, remove unnecessary skips

12. **Optimize Test Performance**
    - Impact: Reduce 2min 17sec execution time
    - Target: Under 2 minutes
    - Estimated Effort: 2-4 hours
    - **Action**: Parallelize tests, optimize fixtures

---

## 8. Testing Best Practices Checklist

### 8.1 Test Development

- [ ] All new features have corresponding tests
- [ ] Test coverage for new code is >80%
- [ ] Edge cases and error conditions are tested
- [ ] Integration tests verify component interactions
- [ ] Tests are independent and can run in any order
- [ ] Fixtures are reusable and well-documented

### 8.2 Test Maintenance

- [ ] Failed tests are investigated within 24 hours
- [ ] Flaky tests are fixed or marked with xfail
- [ ] Skipped tests have documented reasons
- [ ] Test data fixtures are version controlled
- [ ] Mocks are updated when implementations change

### 8.3 Test Quality

- [ ] Tests follow AAA pattern (Arrange, Act, Assert)
- [ ] Test names clearly describe what is being tested
- [ ] Assertions include helpful error messages
- [ ] Tests run in under 1 second each (unit tests)
- [ ] Integration tests have clear setup/teardown

### 8.4 Coverage Goals

- [ ] Overall coverage >75% (current: 77.33% )
- [ ] Critical modules >90% coverage
- [ ] All public APIs have tests
- [ ] Security features have comprehensive tests
- [ ] Error handling paths are tested

---

## 9. Test Infrastructure TODO

### 9.1 Missing Test Infrastructure

- [ ] Database fixtures for integration tests
- [ ] Mock Supabase client for unit tests
- [ ] Test data generators for RAG content
- [ ] Streamlit component testing framework
- [ ] OAuth mock server for auth tests

### 9.2 CI/CD Integration

- [ ] Run tests on every PR
- [ ] Enforce 75% minimum coverage
- [ ] Run security tests (Bandit, Safety)
- [ ] Generate coverage reports
- [ ] Fail CI on test failures

### 9.3 Test Monitoring

- [ ] Track test execution time trends
- [ ] Monitor flaky test frequency
- [ ] Coverage trend reporting
- [ ] Test failure alerts

---

## 10. Recent Changes and Notes

### 10.1 Test Suite Improvements

- **Pass Rate**: Stable at 92.0%
- **Failed Tests**: 200 (same as previous run)
- **Coverage**: 77.33% (exceeds 75% minimum) 
- **Execution Time**: 137.73s (improved from 142.37s - 3.3% faster)

### 10.2 Known Issues

1. **Chunker Module**: Critical AttributeError blocking 73 tests
2. **Integration Tests**: Systematic failures in API test client
3. **UI Coverage**: Streamlit components under-tested (43%)
4. **Auth Coverage**: Authentication features need more tests (60%)
5. **Skipped Tests**: 103 tests need infrastructure or review

### 10.3 Next Steps

1. **Immediate**: Fix chunker AttributeErrors
2. **This Week**: Fix integration test infrastructure
3. **This Sprint**: Add tests for 0% coverage files
4. **This Month**: Increase auth and UI coverage to 80%

---

**End of Testing Inventory**
