# MyPy 100% Pass - Master Plan

**Created**: 2025-11-27
**Goal**: Achieve full MyPy strict mode compliance with zero errors

---

## Current State

```toml
[tool.mypy]
ignore_missing_imports = true
strict_optional = false
disallow_untyped_defs = false
check_untyped_defs = false
disable_error_code = ["call-arg", "attr-defined", "assignment", "operator", "method-assign", "arg-type", "union-attr", "var-annotated", "index"]
```

**Result**: `Success: no issues found in 126 source files`

---

## Target State

```toml
[tool.mypy]
ignore_missing_imports = true
strict_optional = true
disallow_untyped_defs = true
check_untyped_defs = true
# No disabled error codes
```

---

## Error Analysis Summary

| Category | Error Count | Files Affected |
|----------|-------------|----------------|
| check_untyped_defs + strict_optional | 17 | 9 |
| assignment | 45 | ~20 |
| var-annotated | 30 | ~15 |
| arg-type | 64 | ~25 |
| call-arg | 12 | ~10 |
| attr-defined | 36 | ~18 |
| union-attr | 22 | ~12 |
| index | 10 | ~8 |
| operator | 19 | ~6 |
| method-assign | 2 | ~2 |
| disallow_untyped_defs | 266 | ~50 |
| **TOTAL** | **~520** | **54 unique files** |

---

## Phase Structure

### Foundation Phases (1-2)
Enable core type checking settings

### Error Code Phases (3-6)
Re-enable disabled error codes progressively

### Type Annotation Phases (7-15)
Add missing function type annotations by module

---

## Phase Index

| Phase | Focus | Est. Errors | Files |
|-------|-------|-------------|-------|
| 01 | Foundation: check_untyped_defs + strict_optional | 17 | 9 |
| 02 | Error codes: assignment + var-annotated | 75 | 26 |
| 03 | Error codes: arg-type + call-arg | 76 | 25 |
| 04 | Error codes: attr-defined + union-attr | 58 | 22 |
| 05 | Error codes: index + operator | 29 | 10 |
| 06 | Type annotations: utils/ module | ~45 | 6 |
| 07 | Type annotations: api/ module | ~50 | 8 |
| 08 | Type annotations: agentic_rag/storage/ | ~35 | 6 |
| 09 | Type annotations: agentic_rag/search/ | ~25 | 5 |
| 10 | Type annotations: agentic_rag/ingestion/ | ~30 | 4 |
| 11 | Type annotations: auth/ module | ~25 | 8 |
| 12 | Type annotations: ui/ module | ~25 | 6 |
| 13 | Type annotations: clients/ + config/ | ~15 | 5 |
| 14 | Type annotations: constitution_validator/ | ~15 | 6 |
| 15 | Final cleanup + verification | ~5 | misc |

---

## Success Criteria

1. `mypy src/` passes with zero errors
2. All disabled error codes re-enabled
3. `check_untyped_defs = true`
4. `strict_optional = true`
5. `disallow_untyped_defs = true`
6. Pre-commit hooks pass
7. CI/CD pipeline passes

---

## Execution Protocol

For each phase:
1. Read the phase document
2. Update pyproject.toml as specified
3. Run `mypy src/` to see errors
4. Fix errors file by file
5. Run tests to verify no regressions
6. Commit changes
7. Mark phase complete

---

## Verification Commands

```bash
# Check current status
mypy src/

# Run with specific settings
mypy src/ --check-untyped-defs --strict-optional

# Enable specific error code
mypy src/ --enable-error-code assignment

# Full strict mode
mypy src/ --strict --ignore-missing-imports
```

---

## Notes

- Tests directory (`tests/`) has `ignore_errors = true` - not in scope
- `ignore_missing_imports = true` stays enabled (third-party libs)
- Each phase is designed for a single Claude Code session
- Phases can be done in order or cherry-picked by priority
