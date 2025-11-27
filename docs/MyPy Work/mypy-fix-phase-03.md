# MyPy Fix Phase 03: Arg-Type + Call-Arg Errors

**Status**: Not Started
**Estimated Errors**: 76
**Files**: 25
**Prerequisites**: Phase 02 complete

---

## Objective

Re-enable `arg-type` and `call-arg` error codes to catch function call argument type mismatches.

---

## Configuration Change

Update `pyproject.toml`:

```toml
[tool.mypy]
ignore_missing_imports = true
strict_optional = true
disallow_untyped_defs = false
check_untyped_defs = true
disable_error_code = ["attr-defined", "operator", "method-assign", "union-attr", "index"]
# REMOVED: "call-arg", "arg-type"
```

---

## Expected Errors

Run command to preview:
```bash
mypy src/ --ignore-missing-imports --check-untyped-defs --strict-optional --enable-error-code call-arg --enable-error-code arg-type
```

### Files to Fix (by error count)

| File | Errors |
|------|--------|
| src/auth/admin_2fa_management.py | 11 |
| src/agentic_rag/search/graph_search.py | 10 |
| src/api/endpoints/documents.py | 9 |
| src/api/dependencies.py | 8 |
| src/agentic_rag/ingestion/chunker.py | 4 |
| src/api/main.py | 3 |
| src/agentic_rag/search/vector_search.py | 2 |
| src/api/endpoints/chat.py | 2 |
| src/constitution_validator/rules/principle_vi.py | 1 |
| src/constitution_validator/rules/base.py | 1 |
| src/clients/llm.py | 1 |
| src/auth/oauth_profile_management.py | 1 |
| src/auth/oauth_handler.py | 1 |
| src/auth/db_cli.py | 1 |
| src/auth/db.py | 1 |
| src/agentic_rag/storage/postgres_store.py | 1 |
| src/agentic_rag/ingestion/pipeline.py | 1 |
| src/agentic_rag/ingestion/knowledge_extractor.py | 1 |
| src/agentic_rag/ingestion/embedder.py | 1 |

---

## Error Types

### arg-type (64 errors)
Argument has incompatible type. Common fixes:
- Fix the value being passed to match expected type
- Update function signature if argument type is too restrictive
- Use type guards for runtime type narrowing
- Add overloads for functions accepting multiple types

### call-arg (12 errors)
Too many/few arguments or unexpected keyword argument. Common fixes:
- Add missing required arguments
- Remove extra arguments
- Check function signature matches call site
- Update function to accept **kwargs if needed

---

## Fix Strategy by File Group

### API Module (api/)
- **dependencies.py** (8): Dependency injection types
- **endpoints/documents.py** (9): Document endpoint handlers
- **endpoints/chat.py** (2): Chat endpoint handlers
- **main.py** (3): FastAPI app setup

### Auth Module (auth/)
- **admin_2fa_management.py** (11): 2FA admin functions
- **oauth_* files**: OAuth handler argument types
- **db.py, db_cli.py**: Database operation types

### Agentic RAG (agentic_rag/)
- **search/graph_search.py** (10): Graph query arguments
- **search/vector_search.py** (2): Vector search parameters
- **ingestion/** (7 total): Document processing arguments

---

## Verification

```bash
# After fixes:
mypy src/ --ignore-missing-imports --check-untyped-defs --strict-optional --enable-error-code call-arg --enable-error-code arg-type

# Then update pyproject.toml and verify:
mypy src/
```

---

## Completion Checklist

- [ ] Update pyproject.toml (remove call-arg, arg-type from disabled)
- [ ] Fix admin_2fa_management.py (11 errors)
- [ ] Fix graph_search.py (10 errors)
- [ ] Fix endpoints/documents.py (9 errors)
- [ ] Fix dependencies.py (8 errors)
- [ ] Fix chunker.py (4 errors)
- [ ] Fix remaining files (34 errors across 14 files)
- [ ] Run test suite
- [ ] Commit changes

---

## Notes

- arg-type is the most common error type (64 errors)
- Many fixes require understanding the function signatures
- Some may require updating both caller and callee
