# Testing TODO - Remaining Work Only

**Current State**: 3,789 tests | ~3,733 passed (98.5%) | 1 failing in Phase 4 | 106 skipped | ~77% coverage
**Target State**: 100% pass rate | <20 skipped | 80%+ coverage

**Completed Work**: See `/docs/a-changelogs/changelog_current.md` for details on Phases 1-3 (231 tests) and Phase 4 (10 tests)

---

## PHASE 4: Authentication System (1 test remaining)
**Priority**: MEDIUM
**Status**: 91% Complete (10/11 tests passing)

### Remaining Task:

**File**: `tests/auth/test_user_profile_ultra_comprehensive.py`

- [ ] Fix `test_render_user_profile_revoke_all_sessions`
  - Complex Streamlit `st.session_state` attribute mocking
  - Multi-button click simulation with `side_effect`
  - Requires precise `__contains__` and attribute access mocking
  - **Note**: Not blocking - core functionality works correctly

**Run**: `pytest tests/auth/test_user_profile_ultra_comprehensive.py::TestRenderUserProfile::test_render_user_profile_revoke_all_sessions -v`

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
pytest tests/auth/test_user_profile_ultra_comprehensive.py::TestRenderUserProfile::test_render_user_profile_revoke_all_sessions -v  # Phase 4 remaining
pytest tests/config/ -v                              # Phase 5 (Config)
pytest tests/agentic_rag/search/ -v                  # Phase 5 (Search)
pytest tests/utils/test_cache_comprehensive.py -v    # Phase 5 (Cache)

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

## Summary Status

| Phase | Description | Tests Remaining | Priority | Est. Time |
|-------|-------------|-----------------|----------|-----------|
| 4 | Authentication (final test) | 1 | MEDIUM | 30 min |
| 5 | Config & Small Groups | 21 | MEDIUM | 2-3 hrs |
| 6 | Miscellaneous | 11 | LOW | 1-2 hrs |
| 7 | Add Tests for 0% Coverage | N/A | HIGH | 6-8 hrs |
| 8 | Improve Low Coverage Files | N/A | MEDIUM | 8-10 hrs |
| 9 | Enable Skipped Tests | 103 | LOW | 4-6 hrs |
| 10 | Performance & Cleanup | N/A | LOW | 2-4 hrs |
| 11 | Final Verification | N/A | CRITICAL | 1 hr |

**Progress**:
- **Completed**: Phases 1-3 (231 tests) + Phase 4 (10 tests) = **241 tests fixed**
- **Remaining in Current Phases**: 33 tests (1 + 21 + 11)
- **Coverage Target**: 80%+ (currently ~77%)

**Next Step**: Complete Phase 4 final test OR start Phase 5 (Configuration & Small Test Groups)
