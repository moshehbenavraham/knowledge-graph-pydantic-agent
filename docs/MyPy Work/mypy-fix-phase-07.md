# MyPy Fix Phase 07: Type Annotations - api/ Module

**Status**: Not Started
**Estimated Errors**: 50
**Files**: 8
**Prerequisites**: Phase 06 complete

---

## Objective

Add missing type annotations to the `src/api/` module.

---

## Files to Annotate

| File | Missing Annotations |
|------|---------------------|
| src/api/main.py | 11 |
| src/api/health_endpoints.py | 10 |
| src/api/streaming.py | 8 |
| src/api/endpoints/documents.py | 8 |
| src/api/endpoints/chat.py | 6 |
| src/api/endpoints/search.py | 5 |
| src/api/telemetry.py | 7 |
| src/api/dependencies.py | ~5 |

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

---

## File-by-File Strategy

### main.py (11 annotations)
- App factory function
- Lifespan handlers
- Middleware setup
- Exception handlers

### health_endpoints.py (10 annotations)
- Health check functions
- Component status checks
- Readiness/liveness probes

### streaming.py (8 annotations)
- SSE generators
- Stream formatting
- Event serialization

### endpoints/documents.py (8 annotations)
- CRUD operations
- File upload handlers
- Search endpoints

### endpoints/chat.py (6 annotations)
- Chat completion
- Streaming chat
- Message formatting

### endpoints/search.py (5 annotations)
- Search query handlers
- Filter processing
- Result formatting

### telemetry.py (7 annotations)
- Metrics collection
- Tracing setup
- Span creation

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

- [ ] Annotate main.py (11 functions)
- [ ] Annotate health_endpoints.py (10 functions)
- [ ] Annotate streaming.py (8 functions)
- [ ] Annotate endpoints/documents.py (8 functions)
- [ ] Annotate endpoints/chat.py (6 functions)
- [ ] Annotate endpoints/search.py (5 functions)
- [ ] Annotate telemetry.py (7 functions)
- [ ] Annotate dependencies.py
- [ ] Verify with mypy --disallow-untyped-defs
- [ ] Run test suite
- [ ] Commit changes

---

## Notes

- FastAPI endpoints should have explicit return types
- Use response_model for OpenAPI documentation
- Streaming functions need AsyncGenerator annotations
- Depend on Pydantic models for request/response types
