# Development Tooling TODO - Remaining Work Only

**Current State**: MyPy integrated, 19 low-priority type errors remaining
**Target State**: Full type safety, zero MyPy errors

---

## Remaining MyPy Type Errors (19 total)

### Low Priority - Type Annotation Issues (9 errors)
- `src/config/settings.py:160` - Cannot assign to a type (Literal["none"])
- `src/config/settings.py:162` - Cannot assign to a type (Literal["gemini-flash"])
- `src/config/settings.py:164` - Cannot assign to a type (Literal["gemini-pro"])
- `src/config/settings.py:166` - Cannot assign to a type (Literal["gpt-4o"])
- `src/config/settings.py:168` - Cannot assign to a type (Literal["gpt-5-mini"])
- `src/config/settings.py:170` - Cannot assign to a type (Literal["claude-sonnet"])
- `src/config/settings.py:172` - Cannot assign to a type (Literal["claude-haiku"])
- `src/agent/unified_agent.py:85` - Missing type annotation
- `src/agent/unified_agent.py:150` - Missing type annotation

### Low Priority - Return Type Mismatches (4 errors)
- `src/agent/agent_executor.py:189` - Incompatible return type (Agent vs AgentRunResult)
- `src/api/endpoints/chat.py:188` - Return type mismatch (EventSourceResponse vs StreamingResponse)
- `src/config/settings.py:231` - Return type mismatch (dict vs BaseSettings)
- `src/constitution_validator/validators/__init__.py:16` - Return type mismatch (module vs ValidationResult)

### Low Priority - Complex Type Issues (6 errors)
- `src/ui/features/streaming_handler.py:170` - AsyncIterator vs Coroutine override issue
- `src/agentic_rag/storage/neo4j_store.py:27,31` - Function as type annotation
- `src/agent/unified_agent.py:343,379` - Pydantic AI model/result callable issues
- `tests/integration/test_unified_agent.py:25,33` - List assignment overload issues

---

## Optional Improvements

### Documentation
- [ ] Add type stubs for remaining untyped libraries
- [ ] Document type annotation patterns for team

### Testing
- [ ] Add type checking to CI/CD pipeline
- [ ] Create type stub tests

### Code Quality
- [ ] Gradually add stricter MyPy settings
- [ ] Address remaining 19 type errors during refactoring

---
