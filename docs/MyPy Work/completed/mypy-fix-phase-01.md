# MyPy Fix Phase 01: Foundation Settings

**Status**: COMPLETED
**Actual Errors Fixed**: 14
**Files**: 9
**Completed**: 2025-11-27
**Commit**: 426d884

---

## Objective

Enable `check_untyped_defs = true` and `strict_optional = true` to catch type errors in untyped function bodies and enable stricter None handling.

---

## Configuration Change

Update `pyproject.toml`:

```toml
[tool.mypy]
ignore_missing_imports = true
strict_optional = true           # CHANGE: false -> true
disallow_untyped_defs = false
check_untyped_defs = true        # CHANGE: false -> true
disable_error_code = ["call-arg", "attr-defined", "assignment", "operator", "method-assign", "arg-type", "union-attr", "var-annotated", "index"]
```

---

## Expected Errors

Run command to see current errors:
```bash
mypy src/ --ignore-missing-imports --check-untyped-defs --strict-optional
```

### Files to Fix

| File | Errors | Error Types |
|------|--------|-------------|
| src/agentic_rag/ingestion/chunker.py | 4 | call-overload |
| src/api/main.py | 3 | list-item |
| src/utils/resilience.py | 2 | misc |
| src/utils/monitoring.py | 2 | used-before-def |
| src/auth/breach_detection.py | 2 | return-value |
| src/ui/streamlit_app.py | 1 | return-value |
| src/tools/image_analysis.py | 1 | truthy-function |
| src/clients/llm.py | 1 | truthy-function |
| src/agentic_rag/storage/neo4j_store.py | 1 | return-value |

---

## Fix Strategies

### call-overload (chunker.py)
- Check Agent class signature and provide correct arguments
- May need type: ignore comment if third-party type stubs are incomplete

### list-item (api/main.py)
- Ensure dictionary matches ComponentStatus type
- Add explicit type casting or fix dict structure

### misc (resilience.py)
- Exception classes must derive from BaseException
- Fix exception class inheritance

### used-before-def (monitoring.py)
- Variable used before assignment in code path
- Initialize variable before use

### return-value (breach_detection.py, streamlit_app.py, neo4j_store.py)
- Return type doesn't match annotation
- Fix return statements or update annotations

### truthy-function (image_analysis.py, llm.py)
- Function object used in boolean context (always true)
- Call the function or fix the condition logic

---

## Verification

```bash
# After fixes, this should pass:
mypy src/ --ignore-missing-imports --check-untyped-defs --strict-optional

# Update pyproject.toml and verify:
mypy src/
```

---

## Completion Checklist

- [x] Update pyproject.toml with new settings
- [x] Fix chunker.py errors (type: ignore for pydantic-ai stubs)
- [x] Fix api/main.py errors (ComponentStatus instances)
- [x] Fix resilience.py errors (exception typing)
- [x] Fix monitoring.py errors (status initialization)
- [x] Fix breach_detection.py errors (message fallbacks)
- [x] Fix streamlit_app.py errors (handler type annotation)
- [x] Fix image_analysis.py errors (is None check)
- [x] Fix llm.py errors (is None check)
- [x] Fix neo4j_store.py errors (return type annotation)
- [x] Run full test suite (3976 passed)
- [x] Commit changes (426d884)

---

## Notes

- This phase establishes the foundation for stricter checking
- Low error count makes this a quick win
- Once complete, proceed to Phase 02
