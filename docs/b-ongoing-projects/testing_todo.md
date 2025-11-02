# Testing TODO - Remaining Work Only

**Current State**: 4,116 tests collected | 78% coverage
**Target State**: 100% pass rate | 80%+ coverage

**Historical Work**: See `/docs/a-changelogs/changelog_current.md` for completed phases

---

## PHASE 8: Fix Test Execution and Improve Coverage

**Priority**: CRITICAL
**Status**: IN PROGRESS (3 of 9 files complete)
**Estimated Remaining Time**: 4-6 hours

### Tasks Remaining

#### 8.1 Core Pipeline
- [ ] Fix `src/constitution_validator/cli.py` (14.85% -> 80%)
  - File: `tests/constitution_validator/test_cli_comprehensive.py`

#### 8.2 UI Components
- [ ] Fix `src/ui/streamlit_app.py` (0.00% -> 70%)
  - Files: Multiple test files in `tests/ui/`
- [ ] Fix `src/auth/streamlit_auth.py` (0.00% -> 70%)
  - Files: `test_streamlit_auth_comprehensive.py`, `test_streamlit_auth_ultra_comprehensive.py`

#### 8.3 Other Low Coverage Files
- [ ] Fix `src/rag_pipeline/sources/google_drive.py` (0.00% -> 95%)
  - Files: `test_google_drive.py`, `test_google_drive_comprehensive.py`
- [ ] Fix `src/auth/oauth_profile_management.py` (0.00% -> 60%)
  - File: `tests/auth/test_oauth_profile_comprehensive.py`
- [ ] Fix `src/auth/oauth_analytics_dashboard.py` (0.00% -> 60%)
  - File: `tests/auth/test_oauth_analytics_comprehensive.py`

---

## PHASE 9: Enable Skipped Tests

**Priority**: LOW
**Estimated Time**: 4-6 hours

### 9.1 Database Integration Tests (13 skipped)
File: `tests/integration/test_postgres_store.py`

- [ ] Set up test database fixture
- [ ] Mock Supabase client for unit tests
- [ ] Enable all 13 skipped integration tests

### 9.2 Other Skipped Tests (~90 remaining)
- [ ] Categorize by skip reason
- [ ] Enable tests with available infrastructure
- [ ] Document permanent skips with clear reasons

**Success Criteria**: <20 skipped tests (only permanent skips)

---

## PHASE 10: Performance and Cleanup

**Priority**: LOW
**Estimated Time**: 2-4 hours

### 10.1 Test Performance
- [ ] Identify slowest tests (`pytest --durations=20`)
- [ ] Optimize tests >1 second
- [ ] Add parallel execution (pytest-xdist)
- [ ] Target: <2 minute total execution time

### 10.2 Warning Cleanup
- [ ] Document datetime.utcnow() replacements (150+ occurrences)

### 10.3 CI/CD Setup
- [ ] Configure GitHub Actions
- [ ] Enforce 75% minimum coverage
- [ ] Add test result reporting

---

## PHASE 11: Final Verification

**Priority**: CRITICAL
**Estimated Time**: 1 hour

- [ ] Run full test suite: `make test-coverage`
- [ ] Verify 100% pass rate
- [ ] Verify coverage >80%
- [ ] Update documentation

---

## Quick Commands

```bash
# Run all tests with coverage
make test-coverage

# Run specific module tests
pytest tests/constitution_validator/ -v --cov=src/constitution_validator

# Run failed tests only
pytest --lf

# Check coverage for specific file
pytest --cov=src/constitution_validator/reporter --cov-report=term-missing

# Identify slow tests
pytest --durations=20

# Find skipped tests
pytest --collect-only -q -m skip
```

---

## Status Summary

| Phase | Status | Priority | Time Remaining |
|-------|--------|----------|----------------|
| 8 | IN PROGRESS | CRITICAL | 4-6 hrs |
| 9 | NOT STARTED | LOW | 4-6 hrs |
| 10 | NOT STARTED | LOW | 2-4 hrs |
| 11 | NOT STARTED | CRITICAL | 1 hr |

**Next Action**: Fix `src/constitution_validator/cli.py` tests (14.85% -> 80%)
