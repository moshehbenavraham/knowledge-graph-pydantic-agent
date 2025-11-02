# Testing TODO - Phased Approach

**Goal**: Fix all test failures, enable skipped tests, and achieve 80%+ coverage
**Current State (Phase 1 Complete)**: 3,789 tests | 3,560 passed (94.0%) | 126 failed | 103 skipped | ~77% coverage
**Original State**: 3,788 tests | 3,486 passed (92.0%) | 200 failed | 103 skipped | 77.33% coverage
**Target State**: 100% pass rate | <20 skipped | 80%+ coverage
**Progress**: ✅ Fixed 74 test failures (37% reduction) in Phase 1

---

## PHASE 1: Critical Blocker - Chunker AttributeErrors ✅ 100% COMPLETED
**Priority**: CRITICAL - Blocks core ingestion functionality
**Estimated Time**: 2-4 hours (Actual: ~45 minutes)
**Files Fixed**:
- `src/agentic_rag/ingestion/chunker.py` (multiple fixes)
- `tests/test_chunker_coverage.py` (1 test expectation update)

### Tasks:
- [x] Investigate AttributeError at line 122 in chunker.py
- [x] Investigate AttributeError at line 156 in chunker.py
- [x] Investigate AttributeError at line 256 in chunker.py
- [x] Investigate AttributeError at line 297 in chunker.py
- [x] Investigate AttributeError at line 343 in chunker.py
- [x] Fix object attribute access patterns in SimpleChunker class
- [x] Fix object attribute access patterns in SemanticChunker class
- [x] Verify chunk object initialization and metadata handling
- [x] Fix remaining edge case tests
- [x] Run tests: `pytest tests/agentic_rag/ingestion/test_chunker_comprehensive.py -v`
- [x] Run tests: `pytest tests/test_chunker_coverage.py -v`
- [x] Verify all chunker tests pass

**Success Criteria**: ✅ 116 of 116 chunker tests passing (100% pass rate)

### What Was Fixed:
1. **AttributeError fixes**: Changed all `self.config` attribute access to dictionary access throughout both chunker classes
2. **Metadata handling**: Added proper chunk metadata (chunk_method, chunk_index, total_chunks) for single-chunk scenarios
3. **Edge case handling**:
   - Small sections below min_chunk_size now handled intelligently (keep largest if reasonable)
   - LLM mock chunks below min_size handled with lenient fallback
   - Text with no sentence boundaries now force-splits into chunks
4. **Test updates**: Updated one test expectation to allow chunk metadata additions

---

## PHASE 2: Integration Test Infrastructure (62 tests)
**Priority**: CRITICAL - API testing confidence
**Estimated Time**: 4-6 hours

### Tasks:

#### 2.1 Chat Endpoints Integration (35 tests)
**File**: `tests/integration/test_chat_endpoints_comprehensive.py`

- [ ] Review FastAPI test client setup
- [ ] Fix endpoint registration and routing issues
- [ ] Verify dependency injection in test environment
- [ ] Fix test database/service mocking
- [ ] Fix WebSocket endpoint tests
- [ ] Fix cache-related tests
- [ ] Fix metrics recording tests
- [ ] Fix streaming endpoint tests
- [ ] Fix feedback endpoint tests
- [ ] Run: `pytest tests/integration/test_chat_endpoints_comprehensive.py -v`

#### 2.2 API Main Integration (27 tests)
**File**: `tests/integration/test_api_main_comprehensive.py`

- [ ] Fix API app configuration in tests
- [ ] Fix middleware setup issues
- [ ] Fix CORS header tests
- [ ] Fix OpenAPI/Swagger tests
- [ ] Fix lifespan event tests
- [ ] Fix 404 handler tests
- [ ] Fix concurrent request tests
- [ ] Run: `pytest tests/integration/test_api_main_comprehensive.py -v`

**Success Criteria**: All 62 integration tests passing

---

## PHASE 3: API Endpoint Tests (18 tests)
**Priority**: HIGH
**Estimated Time**: 2-3 hours

### Tasks:

#### 3.1 Main API Tests (13 tests)
**File**: `tests/api/test_main_comprehensive.py`

- [ ] Update validation schemas to match current API
- [ ] Fix middleware configuration tests
- [ ] Fix tracing setup tests
- [ ] Fix health/status endpoint tests
- [ ] Fix cache clearing endpoint tests
- [ ] Run: `pytest tests/api/test_main_comprehensive.py -v`

#### 3.2 Endpoint Validation Tests (5 tests)
**File**: `tests/api/test_endpoints.py`

- [ ] Fix validation error handling tests
- [ ] Update request/response schemas
- [ ] Fix health endpoint implementation
- [ ] Run: `pytest tests/api/test_endpoints.py -v`

**Success Criteria**: All 18 API tests passing

---

## PHASE 4: Authentication System (15 tests)
**Priority**: MEDIUM
**Estimated Time**: 2-3 hours

### Tasks:

#### 4.1 Streamlit Auth (6 tests)
**File**: `tests/auth/test_streamlit_auth_ultra_comprehensive.py`

- [ ] Fix Streamlit session state mocking
- [ ] Fix OAuth handler configuration in tests
- [ ] Fix logout button rendering tests
- [ ] Run: `pytest tests/auth/test_streamlit_auth_ultra_comprehensive.py -v`

#### 4.2 User Profile (5 tests)
**File**: `tests/auth/test_user_profile_ultra_comprehensive.py`

- [ ] Fix database backend mocking
- [ ] Fix session management tests
- [ ] Run: `pytest tests/auth/test_user_profile_ultra_comprehensive.py -v`

#### 4.3 OAuth Analytics (3 tests)
**File**: `tests/auth/test_oauth_analytics_comprehensive.py`

- [ ] Fix admin role checking in tests
- [ ] Fix dashboard rendering tests
- [ ] Run: `pytest tests/auth/test_oauth_analytics_comprehensive.py -v`

#### 4.4 Other Auth Tests (2 tests)
- [ ] Fix migration tests in `test_migrate_yaml_to_db_ultra_comprehensive.py`
- [ ] Fix captcha test in `test_captcha_comprehensive.py`

**Success Criteria**: All 15 auth tests passing

---

## PHASE 5: Configuration and Small Test Groups
**Priority**: MEDIUM
**Estimated Time**: 2-3 hours

### Tasks:

#### 5.1 Configuration Tests (5 tests)
**File**: `tests/config/test_config_modules_comprehensive.py`

- [ ] Review configuration facade implementations
- [ ] Fix settings singleton pattern in tests
- [ ] Verify environment variable loading
- [ ] Update tests for current config structure
- [ ] Run: `pytest tests/config/test_config_modules_comprehensive.py -v`

#### 5.2 Search System Tests (9 tests)
- [ ] Fix intent analyzer tests (5 tests)
  - [ ] Update scoring logic tests
  - [ ] Fix entity extraction tests
  - [ ] Run: `pytest tests/agentic_rag/search/test_intent_analyzer_comprehensive.py -v`
- [ ] Fix ranker tests (4 tests)
  - [ ] Update diversity enforcement tests
  - [ ] Fix feedback reranking tests
  - [ ] Run: `pytest tests/agentic_rag/search/test_ranker_comprehensive.py -v`

#### 5.3 Cache Tests (7 tests)
**File**: `tests/utils/test_cache_comprehensive.py`

- [ ] Fix fallback cache implementation
- [ ] Ensure Redis API compatibility
- [ ] Update memory limit tests
- [ ] Run: `pytest tests/utils/test_cache_comprehensive.py -v`

**Success Criteria**: All 21 tests passing

---

## PHASE 6: Miscellaneous Test Fixes (11 tests)
**Priority**: LOW
**Estimated Time**: 1-2 hours

### Tasks:
- [ ] Fix Phase 2 ingestion tests (3 tests)
  - [ ] `test_simple_chunking`
  - [ ] `test_semantic_chunking_fallback`
  - [ ] `test_caching_improves_performance`
- [ ] Fix code execution tests (2 tests)
  - [ ] `test_class_definition`
  - [ ] `test_exception_handling`
- [ ] Fix constitution validator scanner tests (2 tests)
  - [ ] `test_is_merge_commit`
  - [ ] `test_get_commit_message`
- [ ] Fix image analysis test (1 test)
  - [ ] `test_image_analysis_tool_exception`
- [ ] Remove incorrect asyncio decorators (3 tests in cache_comprehensive.py)

**Success Criteria**: All 11 miscellaneous tests passing

---

## PHASE 7: Add Tests for 0% Coverage Files
**Priority**: HIGH
**Estimated Time**: 6-8 hours

### Tasks:

#### 7.1 Critical Files (HIGH Impact)
- [ ] Create tests for `src/agentic_rag/ingestion/__main__.py` (92 statements)
  - [ ] Test CLI argument parsing
  - [ ] Test main entry point
  - [ ] Test error handling
- [ ] Create tests for `src/auth/breach_detection.py` (40 statements)
  - [ ] Test breach detection logic
  - [ ] Test security checks
- [ ] Create tests for `src/rag_pipeline/sources/local_files.py` (184 statements)
  - [ ] Test file ingestion
  - [ ] Test various file formats
  - [ ] Test error handling

#### 7.2 Medium Priority Files
- [ ] Create tests for `src/auth/email_verification_page.py` (49 statements)
- [ ] Create tests for `src/auth/password_history.py` (16 statements)
- [ ] Create tests for `src/auth/password_reset_page.py` (4 statements)

**Success Criteria**: All new test files created and passing

---

## PHASE 8: Improve Low Coverage Files
**Priority**: MEDIUM
**Estimated Time**: 8-10 hours

### Tasks:

#### 8.1 Critical Security Features (<35% coverage)
- [ ] Improve `src/auth/admin_2fa_management.py` (4.82% -> 80%)
- [ ] Improve `src/auth/enforce_2fa.py` (34.64% -> 80%)

#### 8.2 Core Pipeline (<30% coverage)
- [ ] Improve `src/rag_pipeline/pipeline.py` (11.54% -> 80%)
- [ ] Improve `src/constitution_validator/cli.py` (29.35% -> 80%)

#### 8.3 UI Components (<50% coverage)
- [ ] Improve `src/ui/streamlit_app.py` (43.14% -> 70%)
- [ ] Improve `src/auth/streamlit_auth.py` (45.22% -> 70%)

#### 8.4 Other Low Coverage Files
- [ ] Improve `src/rag_pipeline/sources/google_drive.py` (4.17% -> 50%)
- [ ] Improve `src/auth/oauth_profile_management.py` (19.26% -> 60%)
- [ ] Improve `src/constitution_validator/reporter.py` (32.94% -> 70%)
- [ ] Improve `src/auth/oauth_analytics_dashboard.py` (42.01% -> 60%)

**Success Criteria**: All files above minimum coverage thresholds

---

## PHASE 9: Enable Skipped Tests
**Priority**: LOW
**Estimated Time**: 4-6 hours

### Tasks:

#### 9.1 Database Integration Tests (13 skipped)
**File**: `tests/integration/test_postgres_store.py`

- [ ] Set up test database fixture
- [ ] Mock Supabase client for unit tests
- [ ] Create test data fixtures
- [ ] Enable and fix each test:
  - [ ] `test_document_lifecycle`
  - [ ] `test_list_documents_pagination`
  - [ ] `test_list_documents_filtering`
  - [ ] `test_list_documents_sorting`
  - [ ] `test_get_document_chunks`
  - [ ] `test_update_document_metadata`
  - [ ] `test_update_nonexistent_document`
  - [ ] `test_count_chunks_empty_document`
  - [ ] `test_chunk_ordering`
  - [ ] `test_search_similar`
  - [ ] `test_hybrid_search`
  - [ ] `test_get_statistics`
  - [ ] `test_concurrent_operations`

#### 9.2 Other Skipped Tests (~90 remaining)
- [ ] Run `pytest --collect-only -q -m skip` to identify all skipped tests
- [ ] Categorize by skip reason
- [ ] Create issues for tests that should be enabled
- [ ] Add proper skip decorators with clear reasons for permanent skips
- [ ] Enable tests with available infrastructure

**Success Criteria**: <20 skipped tests remaining (only permanently skipped)

---

## PHASE 10: Performance and Cleanup
**Priority**: LOW
**Estimated Time**: 2-4 hours

### Tasks:

#### 10.1 Test Performance
- [ ] Run `pytest --durations=20` to identify slowest tests
- [ ] Optimize tests taking >1 second
- [ ] Cache expensive fixtures
- [ ] Add pytest-xdist for parallel execution
- [ ] Target: <2 minute total execution time

#### 10.2 Warning Cleanup
- [ ] Remove incorrect `@pytest.mark.asyncio` decorators (10 occurrences)
- [ ] Document datetime.utcnow() replacements needed (150+ occurrences)

#### 10.3 CI/CD Setup
- [ ] Configure GitHub Actions for test runs
- [ ] Enforce 75% minimum coverage in CI
- [ ] Add test result reporting
- [ ] Set up coverage badge

**Success Criteria**:
- Test suite runs in <2 minutes
- Zero test warnings
- CI/CD pipeline configured

---

## PHASE 11: Final Verification
**Priority**: CRITICAL
**Estimated Time**: 1 hour

### Tasks:
- [ ] Run full test suite: `make test-coverage`
- [ ] Verify 100% pass rate (all 3,788+ tests)
- [ ] Verify coverage >80%
- [ ] Verify <20 skipped tests
- [ ] Document any remaining issues
- [ ] Update testing inventory with final status

**Success Criteria**:
- All tests passing
- Coverage >80%
- Documentation updated
- CI/CD passing

---

## Quick Commands Reference

```bash
# Run specific phase tests
pytest tests/agentic_rag/ingestion/ -v              # Phase 1
pytest tests/integration/ -v                         # Phase 2
pytest tests/api/ -v                                 # Phase 3
pytest tests/auth/ -v                                # Phase 4

# Run all tests
make test-coverage

# Run failed tests only
pytest --lf

# Check coverage for specific module
pytest --cov=src/agentic_rag/ingestion --cov-report=term-missing

# Identify slow tests
pytest --durations=20

# Find skipped tests
pytest --collect-only -q -m skip
```

---

## Progress Tracking

| Phase | Description | Tests Fixed | Status | Date Completed |
|-------|-------------|-------------|--------|----------------|
| 1 | Chunker AttributeErrors | 116/116 (100%) | [x] Completed | 2025-11-02 |
| 2 | Integration Infrastructure | 0/62 | [ ] Not Started | - |
| 3 | API Endpoints | 0/18 | [ ] Not Started | - |
| 4 | Authentication | 0/15 | [ ] Not Started | - |
| 5 | Config & Small Groups | 0/21 | [ ] Not Started | - |
| 6 | Miscellaneous | 0/11 | [ ] Not Started | - |
| 7 | 0% Coverage Files | 0/7 | [ ] Not Started | - |
| 8 | Low Coverage Files | 0/10 | [ ] Not Started | - |
| 9 | Skipped Tests | 0/103 | [ ] Not Started | - |
| 10 | Performance | - | [ ] Not Started | - |
| 11 | Final Verification | - | [ ] Not Started | - |

**Total Tests to Fix**: 126 (was 200, reduced by 74 in Phase 1)
**Total Skipped to Enable**: 103
**Files Needing Coverage**: 17

---

**Notes**:
- Start with Phase 1 as it blocks the most functionality
- Phases 1-3 are critical and should be completed first
- Phases can be worked on by different team members in parallel after Phase 1
- Each phase is designed to be completed within a single work session
