# Testing TODO - Remaining Work Only

**Current State**: 4,116 tests collected | 78% coverage
**Target State**: 100% pass rate | 80%+ coverage

**Historical Work**: See `/docs/a-changelogs/changelog_current.md` for completed phases

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
| 9 | NOT STARTED | LOW | 4-6 hrs |
| 10 | NOT STARTED | LOW | 2-4 hrs |
| 11 | NOT STARTED | CRITICAL | 1 hr |

**Next Action**: Enable skipped tests (Phase 9)
