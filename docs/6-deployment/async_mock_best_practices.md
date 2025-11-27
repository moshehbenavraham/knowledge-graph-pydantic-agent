# AsyncMock Best Practices for Test Suite

**Created**: 2025-11-03
**Purpose**: Guidelines for proper async mock usage to prevent coroutine warnings and test failures

---

## Common Anti-Patterns and Fixes

### 1. Incorrect: Creating Unawaited Coroutines

**Problem**:
```python
# DON'T DO THIS
mock_obj.close = AsyncMock(return_value=asyncio.sleep(0))
```

**Why it's wrong**: `asyncio.sleep(0)` immediately creates a coroutine object that's never awaited, causing RuntimeWarning.

**Correct approach**:
```python
# DO THIS
mock_obj.close = AsyncMock(return_value=None)  # AsyncMock already returns awaitable
# OR simply:
mock_obj.close = AsyncMock()  # Defaults to None
```

---

### 2. Async Context Manager Mocking

**Correct pattern for async context managers**:
```python
# Pattern 1: Using MagicMock with AsyncMock methods
mock_instance = MagicMock()
mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
mock_instance.__aexit__ = AsyncMock()
mock_instance.async_method = AsyncMock(return_value=expected_value)

# Pattern 2: Using AsyncMock directly (if supported)
mock_instance = AsyncMock()
mock_instance.async_method = AsyncMock(return_value=expected_value)
```

**Example from codebase** (`test_oauth_handler.py:316-320`):
```python
with patch("src.auth.oauth_handler.AsyncOAuth2Client") as mock_client:
    mock_instance = MagicMock()
    mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_instance.__aexit__ = AsyncMock()
    mock_instance.fetch_token = AsyncMock(return_value=mock_oauth_token)
    mock_client.return_value = mock_instance
```

---

### 3. AsyncMock Return Values

**Correct patterns**:
```python
# Simple value return
mock.async_method = AsyncMock(return_value=42)
# Returns 42 when awaited

# Dictionary return
mock.async_method = AsyncMock(return_value={"key": "value"})

# None return (default)
mock.async_method = AsyncMock()  # Defaults to None
mock.async_method = AsyncMock(return_value=None)  # Explicit None

# Exception raising
mock.async_method = AsyncMock(side_effect=Exception("Error"))

# Multiple calls with different returns
mock.async_method = AsyncMock(side_effect=[result1, result2, result3])
```

**Incorrect patterns**:
```python
# DON'T: Passing a coroutine object
mock.async_method = AsyncMock(return_value=asyncio.sleep(0))  # Creates unawaited coroutine

# DON'T: Passing a coroutine function
async def coro():
    return 42
mock.async_method = AsyncMock(return_value=coro())  # Creates unawaited coroutine

# DO: Just return the value
mock.async_method = AsyncMock(return_value=42)
```

---

### 4. Using side_effect Correctly

**Correct for async functions**:
```python
# Exception raising
mock.async_method = AsyncMock(side_effect=Exception("Error"))

# Multiple return values
mock.async_method = AsyncMock(side_effect=[value1, value2, value3])

# Custom async function
async def custom_behavior(*args, **kwargs):
    # Custom logic here
    return result

mock.async_method = AsyncMock(side_effect=custom_behavior)
```

**Common in codebase** (from `test_hybrid_search_comprehensive.py:418`):
```python
hybrid_search.vector_search.search = AsyncMock(
    side_effect=[good_chunks, sample_chunks]
)
```

---

## Testing Checklist

When writing async tests:

- [ ] All async functions are marked with `@pytest.mark.asyncio`
- [ ] All async mocks use `AsyncMock`, not `MagicMock`
- [ ] No `return_value=asyncio.sleep(...)` or similar coroutine creation
- [ ] Async context managers have both `__aenter__` and `__aexit__` as `AsyncMock`
- [ ] All calls to async mocked methods are awaited in the test
- [ ] Test runs without RuntimeWarning about unawaited coroutines

---

## Running Tests with Warning Detection

```bash
# Run tests with all warnings enabled
pytest tests/ -v -W all

# Run tests and stop on first warning
pytest tests/ -v -W error::RuntimeWarning

# Filter for async-related warnings
pytest tests/ -v -W all 2>&1 | grep -E "(RuntimeWarning|coroutine.*never awaited)"
```

---

## Common Warning Messages and Causes

### "RuntimeWarning: coroutine 'sleep' was never awaited"
**Cause**: `asyncio.sleep()` called but result not awaited
**Fix**: Don't use `asyncio.sleep()` in return_value, use `None` instead

### "RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited"
**Cause**: AsyncMock method called without await
**Fix**: Ensure all async mock calls in test code use `await`

---

## Fixed Issues (Phase 1)

**File**: `tests/agentic_rag/storage/test_connection_manager_comprehensive.py`

**Lines Fixed**: 420, 424, 428, 446

**Pattern Fixed**:
```python
# Before (WRONG)
mock_pool.close = AsyncMock(return_value=asyncio.sleep(0))

# After (CORRECT)
mock_pool.close = AsyncMock(return_value=None)
```

**Result**: 207 tests passing with no async warnings

---

## References

- Python unittest.mock AsyncMock docs: https://docs.python.org/3/library/unittest.mock.html#unittest.mock.AsyncMock
- pytest-asyncio plugin: https://pytest-asyncio.readthedocs.io/
- Python asyncio docs: https://docs.python.org/3/library/asyncio.html

---

## Future Improvements

1. Consider creating custom pytest fixtures for common async mock patterns
2. Add pre-commit hook to check for `return_value=asyncio.` patterns
3. Create helper functions for async context manager mocking
4. Document all async mock patterns used in the codebase
