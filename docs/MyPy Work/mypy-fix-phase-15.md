# MyPy Fix Phase 15: Final Cleanup + Enable disallow_untyped_defs

**Status**: Not Started
**Estimated Errors**: Variable (cleanup)
**Files**: All remaining
**Prerequisites**: Phases 01-14 complete

---

## Objective

Enable `disallow_untyped_defs = true` in pyproject.toml and fix any remaining type annotation issues. This is the final phase that completes 100% MyPy strict mode compliance.

---

## Final Configuration

Update `pyproject.toml` to target state:

```toml
[tool.mypy]
ignore_missing_imports = true
strict_optional = true
disallow_untyped_defs = true     # FINAL CHANGE
check_untyped_defs = true
warn_redundant_casts = true
warn_unused_ignores = true       # Can now enable
# No disable_error_code line
```

---

## Pre-Flight Checklist

Before enabling `disallow_untyped_defs`, verify all previous phases:

```bash
# Phase 01-05 verification (all error codes enabled)
mypy src/ --ignore-missing-imports --check-untyped-defs --strict-optional
# Should pass with 0 errors

# Check annotation coverage
mypy src/ --ignore-missing-imports --disallow-untyped-defs 2>&1 | wc -l
# Should be close to 0
```

---

## Cleanup Tasks

### 1. Fix Any Remaining Untyped Functions

```bash
# Find remaining untyped functions
mypy src/ --ignore-missing-imports --disallow-untyped-defs 2>&1 | grep "Function is missing"
```

### 2. Remove Unnecessary type: ignore Comments

```bash
# Find all type: ignore comments
grep -r "# type: ignore" src/ | wc -l

# Review each one - some may no longer be needed
```

### 3. Enable warn_unused_ignores

After cleaning up, enable this to catch stale ignores:
```toml
warn_unused_ignores = true
```

### 4. Review Any Remaining Errors

Common remaining issues:
- Third-party library type stubs
- Dynamic attribute access
- Callback type mismatches
- Overload resolution

---

## Common Final Fixes

### Missing Return Type on __init__
```python
# Before (error)
def __init__(self, value):
    self.value = value

# After
def __init__(self, value: str) -> None:
    self.value = value
```

### Lambda Functions
```python
# Before (error - lambda can't have annotations)
sorter = lambda x: x.score

# After
def sorter(x: Result) -> float:
    return x.score
```

### Property Decorators
```python
# Before (might be missing return type)
@property
def name(self):
    return self._name

# After
@property
def name(self) -> str:
    return self._name
```

### Class Variables
```python
# Before
class Config:
    DEBUG = True

# After
class Config:
    DEBUG: bool = True
```

---

## Verification Commands

```bash
# Full strict mode check
mypy src/ --ignore-missing-imports --disallow-untyped-defs --strict-optional --check-untyped-defs

# Final verification (should match pyproject.toml)
mypy src/

# Expected output
# Success: no issues found in 126 source files
```

---

## Post-Completion Tasks

### 1. Update Documentation
- Update dev_tooling_todo.md to mark complete
- Update CLAUDE.md if needed

### 2. Run Full Test Suite
```bash
make test-coverage
```

### 3. Verify Pre-commit Hooks
```bash
pre-commit run mypy --all-files
```

### 4. Create Completion Commit
```bash
git add -A
git commit -m "Complete MyPy strict mode compliance

- Enable disallow_untyped_defs = true
- Enable check_untyped_defs = true
- Enable strict_optional = true
- Remove all disabled error codes
- All 126 source files pass strict type checking"
```

---

## Success Criteria

1. `mypy src/` passes with zero errors
2. `disallow_untyped_defs = true` in pyproject.toml
3. `check_untyped_defs = true` in pyproject.toml
4. `strict_optional = true` in pyproject.toml
5. No `disable_error_code` line in pyproject.toml
6. Pre-commit hooks pass
7. CI/CD pipeline passes
8. Test suite passes with no regressions

---

## Completion Checklist

- [ ] Verify all previous phases complete
- [ ] Enable disallow_untyped_defs in pyproject.toml
- [ ] Fix any remaining errors
- [ ] Remove unnecessary type: ignore comments
- [ ] Enable warn_unused_ignores
- [ ] Run full test suite
- [ ] Verify pre-commit hooks
- [ ] Update documentation
- [ ] Create completion commit
- [ ] Celebrate!

---

## Notes

- This phase may be quick if previous phases were thorough
- Some type: ignore comments for third-party libs are acceptable
- Consider adding py.typed marker for library consumers
- Document any intentional type: ignore comments
