# MyPy Fix Phase 02: Assignment + Var-Annotated Errors

**Status**: COMPLETED
**Estimated Errors**: 75
**Files**: 26
**Prerequisites**: Phase 01 complete

---

## Objective

Re-enable `assignment` and `var-annotated` error codes to catch type assignment mismatches and untyped variable declarations.

---

## Configuration Change

Update `pyproject.toml`:

```toml
[tool.mypy]
ignore_missing_imports = true
strict_optional = true
disallow_untyped_defs = false
check_untyped_defs = true
disable_error_code = ["call-arg", "attr-defined", "operator", "method-assign", "arg-type", "union-attr", "index"]
# REMOVED: "assignment", "var-annotated"
```

---

## Expected Errors

Run command to preview:
```bash
mypy src/ --ignore-missing-imports --check-untyped-defs --strict-optional --enable-error-code assignment --enable-error-code var-annotated
```

### Files to Fix (by error count)

| File | Errors |
|------|--------|
| src/agentic_rag/ingestion/pipeline.py | 10 |
| src/auth/admin_2fa_management.py | 6 |
| src/agentic_rag/search/ranker.py | 6 |
| src/agentic_rag/storage/graphiti_client.py | 5 |
| src/agentic_rag/search/graph_search.py | 5 |
| src/agentic_rag/analytics/logger.py | 5 |
| src/agentic_rag/search/vector_search.py | 4 |
| src/utils/rate_limiting.py | 3 |
| src/ui/streamlit_app.py | 3 |
| src/constitution_validator/cli.py | 2 |
| src/auth/db_cli.py | 2 |
| src/api/endpoints/search.py | 2 |
| src/api/endpoints/chat.py | 2 |
| src/agentic_rag/ingestion/embedder.py | 2 |
| src/agent/unified_agent.py | 2 |
| src/ui/features/base_handler.py | 1 |
| src/tools/image_analysis.py | 1 |
| src/rag_pipeline/pipeline.py | 1 |
| src/auth/streamlit_auth.py | 1 |
| src/auth/oauth_profile_management.py | 1 |
| src/api/endpoints/documents.py | 1 |
| src/agentic_rag/storage/postgres_store.py | 1 |

---

## Error Types

### assignment (45 errors)
Incompatible types in assignment. Common fixes:
- Add explicit type annotations
- Use Optional[T] for nullable values
- Cast values: `cast(Type, value)`
- Use Union types where multiple types possible

### var-annotated (30 errors)
Need type annotation for variable. Common fixes:
- Add type annotation: `var: Type = value`
- For complex types: `var: dict[str, Any] = {}`
- For class variables: add in __init__ or class body

---

## Fix Strategy by File Group

### High Priority (10+ errors)
- **pipeline.py**: Core ingestion logic, ensure proper typing for document processing
- **admin_2fa_management.py**: Auth module, careful with security-related typing

### Medium Priority (5-9 errors)
- **ranker.py, graph_search.py, vector_search.py**: Search module consistency
- **graphiti_client.py, analytics/logger.py**: Storage/analytics typing

### Lower Priority (1-4 errors)
- Fix remaining files in any order
- Many are single-line annotation additions

---

## Verification

```bash
# After fixes:
mypy src/ --ignore-missing-imports --check-untyped-defs --strict-optional --enable-error-code assignment --enable-error-code var-annotated

# Then update pyproject.toml and verify:
mypy src/
```

---

## Completion Checklist

- [x] Update pyproject.toml (remove assignment, var-annotated from disabled)
- [x] Fix pipeline.py (10 errors)
- [x] Fix admin_2fa_management.py (6 errors)
- [x] Fix ranker.py (6 errors)
- [x] Fix graphiti_client.py (5 errors)
- [x] Fix graph_search.py (5 errors)
- [x] Fix analytics/logger.py (5 errors)
- [x] Fix vector_search.py (4 errors)
- [x] Fix remaining files (21 errors across 15 files)
- [x] Run test suite
- [x] Commit changes

---

## Notes

- This phase has the most variety in fix types
- Focus on consistency within modules
- Some errors may cascade (fixing one reveals another)
