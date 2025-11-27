# MyPy Fix Phase 07: Type Annotations - api/ Module

**Status**: Completed
**Actual Errors Fixed**: 60
**Files**: 9 (including middleware.py which was not in original estimate)
**Prerequisites**: Phase 06 complete

---

## Objective

Add missing type annotations to the `src/api/` module.

---

## Files Annotated

| File | Annotations Added |
|------|---------------------|
| src/api/main.py | 9 |
| src/api/health_endpoints.py | 10 |
| src/api/streaming.py | 7 |
| src/api/endpoints/documents.py | 5 |
| src/api/endpoints/chat.py | 6 |
| src/api/endpoints/search.py | 5 |
| src/api/telemetry.py | 7 |
| src/api/dependencies.py | 2 |
| src/api/middleware.py | 3 |

---

## FastAPI-Specific Patterns

### Endpoint Functions
```python
# Before
@router.get("/health")
async def health_check():
    return {"status": "ok"}

# After
from fastapi import Response

@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
```

### With Dependencies
```python
# Before
@router.post("/chat")
async def chat(request: ChatRequest, deps = Depends(get_deps)):
    ...

# After
@router.post("/chat")
async def chat(
    request: ChatRequest,
    deps: AgentDeps = Depends(get_deps)
) -> ChatResponse:
    ...
```

### Response Models
```python
# Before
@router.get("/documents")
async def list_documents():
    return documents

# After
@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents() -> list[DocumentResponse]:
    return documents
```

### Streaming Responses
```python
# Before
async def stream_response(request):
    async def generate():
        yield "data"
    return StreamingResponse(generate())

# After
from collections.abc import AsyncGenerator

async def stream_response(request: ChatRequest) -> StreamingResponse:
    async def generate() -> AsyncGenerator[str, None]:
        yield "data"
    return StreamingResponse(generate())
```

### Union Return Types with FastAPI
```python
# IMPORTANT: FastAPI doesn't support Union return types in response models
# Use response_model=None to disable automatic response model generation

# Before (causes FastAPIError)
@router.get("/readiness")
async def readiness_check() -> dict[str, Any] | JSONResponse:
    ...

# After (works correctly)
@router.get("/readiness", response_model=None)
async def readiness_check() -> dict[str, Any] | JSONResponse:
    ...
```

---

## Verification

```bash
# Check specific file
mypy src/api/main.py --ignore-missing-imports --disallow-untyped-defs

# Check entire module
mypy src/api/ --ignore-missing-imports --disallow-untyped-defs
```

---

## Completion Checklist

- [x] Annotate main.py (9 functions)
- [x] Annotate health_endpoints.py (10 functions)
- [x] Annotate streaming.py (7 functions)
- [x] Annotate endpoints/documents.py (5 functions)
- [x] Annotate endpoints/chat.py (6 functions)
- [x] Annotate endpoints/search.py (5 functions)
- [x] Annotate telemetry.py (7 functions)
- [x] Annotate dependencies.py (2 functions)
- [x] Annotate middleware.py (3 functions)
- [x] Verify with mypy --disallow-untyped-defs
- [x] Run test suite

---

## Notes

- FastAPI endpoints should have explicit return types
- Use `response_model=None` for endpoints that return Union types (e.g., `dict | JSONResponse`)
- Streaming functions need AsyncGenerator annotations
- Depend on Pydantic models for request/response types
- Nested functions (like inner generators) also need type annotations for `--disallow-untyped-defs`
- Middleware classes need typed `__init__` methods with `ASGIApp` for app parameter
