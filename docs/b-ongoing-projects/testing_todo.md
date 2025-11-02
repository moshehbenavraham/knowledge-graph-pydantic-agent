# Testing TODO - Remaining Work Only

**Current State**: ~3,900 tests | ~3,874 passed (99.3%) | 0 failing | 106 skipped | ~78% coverage
**Target State**: 100% pass rate | <20 skipped | 80%+ coverage

**Completed Work**: See `/docs/a-changelogs/changelog_current.md` for Phases 1-7 (345+ tests fixed)

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
- [ ] Verify 100% pass rate (all 3,900+ tests)
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

| Phase | Description | Priority | Est. Time |
|-------|-------------|----------|-----------|
| 8 | Improve Low Coverage Files | MEDIUM | 8-10 hrs |
| 9 | Enable Skipped Tests | LOW | 4-6 hrs |
| 10 | Performance & Cleanup | LOW | 2-4 hrs |
| 11 | Final Verification | CRITICAL | 1 hr |

**Progress**:
- **Completed**: Phases 1-7 (345+ tests added/fixed)
- **Remaining**: Phases 8-11 (coverage improvements, skipped tests, cleanup)
- **Coverage**: 78% (Target: 80%+)

**Next Step**: Phase 8 (Improve Low Coverage Files)
