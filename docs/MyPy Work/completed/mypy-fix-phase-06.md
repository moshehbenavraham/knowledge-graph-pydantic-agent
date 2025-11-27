# MyPy Fix Phase 06: Type Annotations - utils/ Module

**Status**: COMPLETED
**Estimated Errors**: 45 (actual: 44)
**Files**: 6 (5 required changes)
**Prerequisites**: Phase 05 complete
**Completed**: 2025-11-27

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

- [x] Annotate resilience.py (18 functions) - Added ParamSpec/TypeVar, fixed decorators and async wrappers
- [x] Annotate monitoring.py (13 functions) - Added return types, context manager annotations
- [x] Annotate rate_limiting.py (10 functions) - Added class __init__ return types, decorator annotations
- [x] Annotate cache.py (4 functions) - Added ParamSpec/TypeVar for cache decorator
- [x] Annotate remaining utils files (health.py - 1 function)
- [x] Verify with mypy --disallow-untyped-defs - Success: no issues found in 6 source files
- [x] Run test suite - 266 tests passed in utils module
- [x] Commit changes

---

## Notes

- Focus on public API functions first
- Internal helpers can use simpler annotations
- Use Any sparingly - prefer specific types
- Decorators often need ParamSpec/TypeVar

## Summary of Changes

### resilience.py
- Added `ParamSpec("P")` and `TypeVar("T")` for decorator typing
- Fixed `call()` and `call_async()` method signatures with proper Callable types
- Added return type annotations to `_on_success()`, `_on_failure()`, `reset()`
- Fixed `circuit_breaker()` decorator with proper generic return type
- Fixed `retry()` decorator and inner wrappers
- Fixed `retry_on_network_error()` and `retry_on_database_error()` return types

### monitoring.py
- Added `ParamSpec`, `TypeVar`, `AsyncGenerator`, `Generator` imports
- Fixed `configure_logging()` return type
- Changed `_get_or_create_metric()` return type to `Any` (avoids union attribute issues)
- Added `__init__` return type and dict annotation for `active_requests`
- Fixed context manager return types (`Generator[None, None, None]`, `AsyncGenerator[None, None]`)
- Fixed `track_performance()` decorator with ParamSpec/TypeVar

### rate_limiting.py
- Added `ParamSpec`, `TypeVar`, `Callable` imports
- Fixed `__init__` return types for all classes
- Added `defaultdict[str, str]` annotation for `user_tiers`
- Fixed `rate_limit()` decorator with proper generic types

### cache.py
- Added `asyncio`, `ParamSpec`, `TypeVar` imports
- Fixed `_generate_key()` method with `*args: Any, **kwargs: Any`
- Fixed `cache()` decorator with proper generic types

### health.py
- Fixed `HealthChecker.__init__()` return type
- Added dict annotation for `component_checks`
- Added `datetime | None` annotation for `last_full_check`
