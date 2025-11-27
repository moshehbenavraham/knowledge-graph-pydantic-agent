# MyPy Fix Phase 04: Attr-Defined + Union-Attr Errors

**Status**: Complete
**Estimated Errors**: 58
**Files**: 22
**Prerequisites**: Phase 03 complete

---

## Objective

Re-enable `attr-defined` and `union-attr` error codes to catch attribute access errors on undefined or union types.

---

## Configuration Change

Update `pyproject.toml`:

```toml
[tool.mypy]
ignore_missing_imports = true
strict_optional = true
disallow_untyped_defs = false
check_untyped_defs = true
disable_error_code = ["operator", "method-assign", "index"]
# REMOVED: "attr-defined", "union-attr"
```

---

## Expected Errors

Run command to preview:
```bash
mypy src/ --ignore-missing-imports --check-untyped-defs --strict-optional --enable-error-code attr-defined --enable-error-code union-attr
```

### Files to Fix (by error count)

| File | Errors |
|------|--------|
| src/api/dependencies.py | 10 |
| src/ui/streamlit_app.py | 6 |
| src/auth/enforce_2fa.py | 6 |
| src/agentic_rag/ingestion/pipeline.py | 6 |
| src/agentic_rag/search/graph_search.py | 5 |
| src/api/main.py | 5 |
| src/auth/migrate_yaml_to_db.py | 4 |
| src/agentic_rag/storage/connection_manager.py | 4 |
| src/agentic_rag/ingestion/chunker.py | 4 |
| src/agentic_rag/search/hybrid_search.py | 3 |
| src/agentic_rag/search/intent_analyzer.py | 3 |
| src/api/endpoints/chat.py | 3 |
| src/constitution_validator/cli.py | 2 |
| src/clients/memory.py | 2 |
| src/constitution_validator/reporter.py | 1 |
| src/auth/streamlit_auth.py | 1 |
| src/auth/admin_2fa_management.py | 1 |
| src/agent/unified_agent.py | 1 |

---

## Error Types

### attr-defined (36 errors)
Attribute does not exist on type. Common fixes:
- Add missing attribute to class definition
- Use hasattr() check with type narrowing
- Fix typos in attribute names
- Use Protocol for duck typing
- Add type: ignore[attr-defined] for dynamic attributes

### union-attr (22 errors)
Attribute access on union type where not all members have it. Common fixes:
- Add type narrowing: `if isinstance(x, Type):`
- Use assert to narrow type: `assert x is not None`
- Use Optional properly and handle None case
- Use typing.cast() when type is known

---

## Fix Strategy by File Group

### API Module (api/)
- **dependencies.py** (10): Dependency injection attribute access
- **main.py** (5): App configuration attributes
- **endpoints/chat.py** (3): Request/response attributes

### UI Module (ui/)
- **streamlit_app.py** (6): Streamlit session state attributes

### Auth Module (auth/)
- **enforce_2fa.py** (6): 2FA enforcement logic
- **migrate_yaml_to_db.py** (4): Migration attribute access
- **streamlit_auth.py** (1): Auth handler attributes

### Agentic RAG (agentic_rag/)
- **ingestion/pipeline.py** (6): Pipeline object attributes
- **search/** (11 total): Search result attributes
- **storage/connection_manager.py** (4): Connection attributes

---

## Common Patterns

### Handling Optional Types
```python
# Before (error)
result = obj.attribute  # obj might be None

# After
if obj is not None:
    result = obj.attribute
# or
result = obj.attribute if obj else default
```

### Handling Union Types
```python
# Before (error)
if response.data:  # response is Union[SuccessResponse, ErrorResponse]

# After
if isinstance(response, SuccessResponse) and response.data:
    ...
```

---

## Verification

```bash
# After fixes:
mypy src/ --ignore-missing-imports --check-untyped-defs --strict-optional --enable-error-code attr-defined --enable-error-code union-attr

# Then update pyproject.toml and verify:
mypy src/
```

---

## Completion Checklist

- [x] Update pyproject.toml (remove attr-defined, union-attr from disabled)
- [x] Fix dependencies.py (6 errors)
- [x] Fix streamlit_app.py (6 errors)
- [x] Fix enforce_2fa.py (6 errors)
- [x] Fix ingestion/pipeline.py (6 errors)
- [x] Fix graph_search.py (5 errors)
- [x] Fix api/main.py (2 errors)
- [x] Fix remaining files (51 errors across 15 files total)
- [x] Run test suite
- [ ] Commit changes

---

## Notes

- union-attr often appears with Optional types
- attr-defined may indicate missing type stubs for libraries
- Some fixes require runtime type guards
