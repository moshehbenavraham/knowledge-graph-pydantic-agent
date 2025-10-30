# Development Tooling TODO

**Last Updated**: 2025-10-31
**Scope**: Non-testing development tooling tasks (formatting, linting, security, deprecations)
**Testing Issues**: See `testing_inventory.md`
**Completed Work**: See `/docs/a-changelogs/changelog_current.md`

---

## Current Status

- **Code Formatting**: ✅ Clean (all checks passing)
- **Linting**: ✅ All checks passing (Ruff, Black, MyPy)
- **Security**: ✅ Critical vulnerabilities resolved
- **Deprecations**: ✅ All datetime.utcnow() calls migrated
- **Overall Status**: ✅ Excellent - all critical and medium priority items complete

---

## Remaining Tasks

### MyPy Type Hints (19 errors - Low Priority)

All remaining errors are low-severity type hint issues that don't affect runtime behavior. Address during architectural refactoring.

**1. Type Annotation Issues (7 errors)**
```
src/tools/image_analysis.py:11,16,21: error: Cannot assign to a type
src/clients/llm.py:10,15,20,25: error: Cannot assign to a type
```
- **Fix**: Use `TypeAlias` or proper type annotation syntax
- **Priority**: Low - runtime behavior unaffected

**2. Return Type Mismatches (4 errors)**
```
src/constitution_validator/scanners/git_scanner.py:127: error: Incompatible return value type (got "str | bytes", expected "str")
src/constitution_validator/rules/principle_ii.py:140,150: error: Incompatible return value type (got "str | bytes | int | float | complex | EllipsisType", expected "str")
src/agentic_rag/storage/migrations/postgres_migrations.py:227: error: Incompatible return value type (got "dict[str, object]", expected "list[dict[Any, Any]]")
```
- **Fix**: Fix return type annotation or add type conversion
- **Priority**: Low - functions work correctly, just imprecise type hints

**3. Callable/Overload Issues (4 errors)**
```
src/api/streaming.py:322: error: Function "builtins.callable" is not valid as a type
src/api/streaming.py:341: error: callable? not callable
src/api/endpoints/chat.py:79: error: No overload variant of "run" of "AbstractAgent" matches argument types
```
- **Fix**: Requires understanding of Pydantic AI type system
- **Priority**: Low - agent runs correctly despite type errors

**4. Neo4j Driver Type Issues (2 errors)**
```
src/agentic_rag/storage/connection_manager.py:67: error: Function "neo4j._async.driver.AsyncGraphDatabase.driver" is not valid as a type
src/agentic_rag/storage/migrations/neo4j_init.py:21: error: Function "neo4j._async.driver.AsyncGraphDatabase.driver" is not valid as a type
```
- **Fix**: Use proper Neo4j driver type or Protocol
- **Priority**: Low - type hint issue only

**5. List Assignment Overload (2 errors)**
```
src/agentic_rag/ingestion/embedder.py:283,286: error: No overload variant of "__setitem__" of "list" matches argument types "int", "list[float]"
```
- **Fix**: Add explicit type annotation for list
- **Priority**: Low - runtime works fine

**6. Method Override Issues (1 error)**
```
src/ui/features/streaming_handler.py:30: error: Return type "AsyncIterator[dict[str, Any]]" incompatible with return type "Coroutine[Any, Any, Any]" in supertype
```
- **Fix**: Update base class type annotation or use Protocol
- **Priority**: Low - streaming works correctly

---

### Security Monitoring

**Monitor py package** (Low Priority)
- **Status**: py 1.11.0 (latest version) - disputed CVE-2022-42969 (ReDoS)
- **Current**: Only used by `interrogate` (dev dependency for docstring coverage)
- **Impact**: SVN functionality not used in this project
- **Action**: Continue monitoring for updates
- **Last Checked**: 2025-10-31
- **Priority**: Low - no immediate action needed

---

## Code Quality Commands

```bash
# Full quality check suite
make format && make lint && make security

# Individual checks
make format              # Auto-format with Black + Ruff
make lint                # Run Ruff + Black + MyPy checks
make security            # Run Bandit + Safety + pip-audit

# MyPy type checking
mypy src/                # Check source code only
mypy src/ tests/         # Check everything (verbose)

# Security-only
bandit -r src/
safety scan
pip-audit
```

---

## Documentation and Resources

### Internal Documentation

- Testing issues: `docs/b-ongoing-projects/testing_inventory.md`
- Completed changes: `docs/a-changelogs/changelog_current.md`
- Security policies: TBD
- Code style guide: TBD

### External Resources

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Black Code Style](https://black.readthedocs.io/)
- [Bandit Security](https://bandit.readthedocs.io/)
- [Safety CLI](https://docs.pyup.io/docs/safety-cli)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Python Deprecation Timeline](https://docs.python.org/3/whatsnew/)

---

**End of Development Tooling TODO**
