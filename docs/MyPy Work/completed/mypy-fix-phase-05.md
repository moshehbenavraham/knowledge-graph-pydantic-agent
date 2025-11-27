# MyPy Fix Phase 05: Index + Operator + Method-Assign Errors

**Status**: Not Started
**Estimated Errors**: 31
**Files**: 10
**Prerequisites**: Phase 04 complete

---

## Objective

Re-enable remaining disabled error codes: `index`, `operator`, and `method-assign`. This completes the error code re-enablement.

---

## Configuration Change

Update `pyproject.toml`:

```toml
[tool.mypy]
ignore_missing_imports = true
strict_optional = true
disallow_untyped_defs = false
check_untyped_defs = true
# All error codes now enabled (remove disable_error_code entirely)
```

---

## Expected Errors

Run command to preview:
```bash
mypy src/ --ignore-missing-imports --check-untyped-defs --strict-optional --enable-error-code index --enable-error-code operator --enable-error-code method-assign
```

### Files to Fix (by error count)

| File | Errors | Error Type |
|------|--------|------------|
| src/agentic_rag/search/hybrid_search.py | 8 | operator |
| src/agentic_rag/ingestion/chunker.py | 8 | operator |
| src/auth/migrate_yaml_to_db.py | 3 | operator |
| src/api/main.py | 3 | index |
| src/constitution_validator/rules/principle_iv.py | 2 | operator |
| src/agentic_rag/search/intent_analyzer.py | 2 | operator |
| src/utils/monitoring.py | 2 | index |
| Plus misc files | ~3 | various |

---

## Error Types

### operator (19 errors)
Unsupported operand types for operator. Common fixes:
- Add type annotations to clarify operand types
- Use numeric type guards before arithmetic
- Handle None before operations
- Use Union[int, float] for numeric flexibility

### index (10 errors)
Invalid index type or no __getitem__ method. Common fixes:
- Ensure index is int for sequences
- Ensure key type matches dict key type
- Add proper typing for indexable objects
- Use TypedDict for dict with known keys

### method-assign (2 errors)
Cannot assign to a method. Common fixes:
- Use property setter instead of direct assignment
- Check if trying to reassign bound method
- May need to use setattr() for dynamic assignment

---

## Fix Strategy

### Operator Errors (hybrid_search.py, chunker.py)
Most common: arithmetic on Optional or Union types
```python
# Before
score = result.score + boost  # score might be None

# After
score = (result.score or 0.0) + boost
# or
if result.score is not None:
    score = result.score + boost
```

### Index Errors (main.py, monitoring.py)
Most common: accessing dict/list with wrong key type
```python
# Before
value = data[key]  # key type unclear

# After
value = data[str(key)]  # explicit conversion
# or add type annotation
data: dict[str, Any] = {...}
```

---

## Verification

```bash
# After fixes:
mypy src/ --ignore-missing-imports --check-untyped-defs --strict-optional --enable-error-code index --enable-error-code operator --enable-error-code method-assign

# Then update pyproject.toml (remove disable_error_code) and verify:
mypy src/
```

---

## Milestone

After this phase, the `disable_error_code` line can be removed entirely from pyproject.toml. This represents a major milestone - all error codes are now enabled.

---

## Completion Checklist

- [ ] Update pyproject.toml (remove disable_error_code line)
- [ ] Fix hybrid_search.py (8 errors)
- [ ] Fix chunker.py (8 errors)
- [ ] Fix migrate_yaml_to_db.py (3 errors)
- [ ] Fix api/main.py (3 errors)
- [ ] Fix principle_iv.py (2 errors)
- [ ] Fix intent_analyzer.py (2 errors)
- [ ] Fix monitoring.py (2 errors)
- [ ] Fix remaining files (~3 errors)
- [ ] Run test suite
- [ ] Commit changes

---

## Notes

- This is the final error code phase
- After this, all error codes are enabled
- Remaining phases focus on adding type annotations
