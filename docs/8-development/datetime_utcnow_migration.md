# datetime.utcnow() Migration Guide

## Overview

Python 3.12+ deprecates `datetime.utcnow()` in favor of timezone-aware alternatives. This document tracks the migration from `datetime.utcnow()` to `datetime.now(timezone.utc)`.

## Why This Change?

- `datetime.utcnow()` returns a naive datetime object without timezone information
- `datetime.now(timezone.utc)` returns a timezone-aware datetime object
- Timezone-aware datetimes prevent ambiguity and bugs in distributed systems
- The deprecation warning was added in Python 3.12 (PEP 702)

## Replacement Pattern

```python
# OLD (deprecated)
from datetime import datetime
timestamp = datetime.utcnow()

# NEW (recommended)
from datetime import datetime, timezone
timestamp = datetime.now(timezone.utc)
```

## Current Status

**Total Occurrences**: 4 in Python source files

### Files Requiring Updates

| File | Line | Current Code | Priority |
|------|------|--------------|----------|
| `src/constitution_validator/models.py` | 86 | `default_factory=datetime.utcnow` | Medium |
| `src/constitution_validator/models.py` | 335 | `default_factory=datetime.utcnow` | Medium |
| `src/api/models.py` | 88 | `default_factory=datetime.utcnow` | Medium |
| `src/api/models.py` | 229 | `default_factory=datetime.utcnow` | Medium |

### Implementation Plan

1. **Update imports** in affected files:
   ```python
   from datetime import datetime, timezone
   ```

2. **Replace default_factory** in Pydantic models:
   ```python
   # Before
   timestamp: datetime = Field(default_factory=datetime.utcnow)

   # After
   timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
   ```

3. **Update tests** to use timezone-aware datetimes

4. **Verify compatibility** with database timestamp columns

## Testing Considerations

### Database Compatibility

- PostgreSQL: `TIMESTAMP WITH TIME ZONE` columns handle timezone-aware datetimes correctly
- Supabase: Built on PostgreSQL, supports timezone-aware datetimes
- Neo4j: ISO 8601 format with timezone information is supported

### Test Updates

When updating tests, ensure:
- Mock datetime functions return timezone-aware objects
- Assertions compare timezone-aware datetimes
- Time comparisons account for timezone differences

Example test pattern:
```python
from datetime import datetime, timezone
from unittest.mock import patch

def test_with_timezone_aware_datetime():
    fixed_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = fixed_time
        # Test code here
```

## Migration Checklist

- [ ] Update `src/constitution_validator/models.py` (2 occurrences)
- [ ] Update `src/api/models.py` (2 occurrences)
- [ ] Run full test suite to verify no breakage
- [ ] Update any broken tests
- [ ] Verify database compatibility
- [ ] Check API response formats
- [ ] Update documentation if timestamp format changes

## Breaking Changes

**None expected** - The change is internal to the application. External APIs should continue to work as:
- ISO 8601 format strings remain the same
- JSON serialization handles timezone-aware datetimes
- Database storage is compatible

## References

- [PEP 702 - Deprecation of datetime.utcnow()](https://peps.python.org/pep-0702/)
- [Python datetime documentation](https://docs.python.org/3/library/datetime.html)
- [Timezone-aware datetime best practices](https://docs.python.org/3/library/datetime.html#aware-and-naive-objects)

## Rollout Plan

**Phase 1**: Code updates (Low risk)
- Update model definitions
- Estimated time: 30 minutes

**Phase 2**: Testing (Medium risk)
- Run full test suite
- Fix any test failures
- Estimated time: 1-2 hours

**Phase 3**: Deployment (Low risk)
- Deploy to staging
- Verify no timestamp issues
- Deploy to production
- Estimated time: 30 minutes

**Total estimated time**: 2-3 hours
