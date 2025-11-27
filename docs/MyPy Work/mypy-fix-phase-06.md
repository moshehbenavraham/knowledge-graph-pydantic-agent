# MyPy Fix Phase 06: Type Annotations - utils/ Module

**Status**: Not Started
**Estimated Errors**: 45
**Files**: 6
**Prerequisites**: Phase 05 complete

---

## Objective

Add missing type annotations to the `src/utils/` module to prepare for `disallow_untyped_defs = true`.

---

## Configuration Change

No config change yet. First add annotations, then in Phase 15 enable the setting.

Test with:
```bash
mypy src/utils/ --ignore-missing-imports --disallow-untyped-defs
```

---

## Files to Annotate

| File | Missing Annotations |
|------|---------------------|
| src/utils/resilience.py | 17 |
| src/utils/monitoring.py | 12 |
| src/utils/rate_limiting.py | 10 |
| src/utils/cache.py | 4 |
| src/utils/health.py | ~2 |
| src/utils/validation.py | ~0 (if exists) |

---

## Annotation Patterns

### Function Return Types
```python
# Before
def get_cache_key(prefix, *args):
    return f"{prefix}:{':'.join(str(a) for a in args)}"

# After
def get_cache_key(prefix: str, *args: Any) -> str:
    return f"{prefix}:{':'.join(str(a) for a in args)}"
```

### Async Functions
```python
# Before
async def check_health():
    return {"status": "ok"}

# After
async def check_health() -> dict[str, str]:
    return {"status": "ok"}
```

### Class Methods
```python
# Before
class RateLimiter:
    def __init__(self, max_requests, window_seconds):
        self.max_requests = max_requests

    def is_allowed(self, key):
        ...

# After
class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests

    def is_allowed(self, key: str) -> bool:
        ...
```

### Decorators
```python
# Before
def retry(max_attempts, delay):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ...
        return wrapper
    return decorator

# After
from typing import TypeVar, Callable, ParamSpec

P = ParamSpec('P')
T = TypeVar('T')

def retry(max_attempts: int, delay: float) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            ...
        return wrapper
    return decorator
```

---

## File-by-File Strategy

### resilience.py (17 annotations)
- Circuit breaker patterns
- Retry decorators with exponential backoff
- Exception handling wrappers
- Focus on Callable types for decorators

### monitoring.py (12 annotations)
- Metrics collection functions
- Health check endpoints
- Status reporting
- Focus on dict return types

### rate_limiting.py (10 annotations)
- Rate limiter class methods
- Token bucket algorithm
- Key generation functions
- Focus on numeric types (int, float)

### cache.py (4 annotations)
- Cache key generation
- TTL handling
- Cache decorator
- Focus on generic types

---

## Verification

```bash
# Check specific file
mypy src/utils/resilience.py --ignore-missing-imports --disallow-untyped-defs

# Check entire module
mypy src/utils/ --ignore-missing-imports --disallow-untyped-defs
```

---

## Completion Checklist

- [ ] Annotate resilience.py (17 functions)
- [ ] Annotate monitoring.py (12 functions)
- [ ] Annotate rate_limiting.py (10 functions)
- [ ] Annotate cache.py (4 functions)
- [ ] Annotate remaining utils files
- [ ] Verify with mypy --disallow-untyped-defs
- [ ] Run test suite
- [ ] Commit changes

---

## Notes

- Focus on public API functions first
- Internal helpers can use simpler annotations
- Use Any sparingly - prefer specific types
- Decorators often need ParamSpec/TypeVar
