# MyPy Fix Phase 13: Type Annotations - clients/ + config/

**Status**: Not Started
**Estimated Errors**: 15
**Files**: 5
**Prerequisites**: Phase 12 complete

---

## Objective

Add missing type annotations to `src/clients/` and `src/config/` modules.

---

## Files to Annotate

| File | Missing Annotations |
|------|---------------------|
| src/clients/memory.py | 3 |
| src/clients/llm.py | ~2 |
| src/clients/database.py | ~2 |
| src/config/__init__.py | ~3 |
| src/config/settings.py | ~5 |

---

## Client-Specific Patterns

### LLM Client
```python
# Before
def get_llm_client(provider, model):
    ...

# After
from pydantic_ai import Agent
from typing import Literal

LLMProvider = Literal["openai", "anthropic", "ollama"]

def get_llm_client(
    provider: LLMProvider,
    model: str
) -> Agent[Any]:
    ...
```

### Memory Client (Mem0)
```python
# Before
async def store_memory(user_id, content, metadata):
    ...

# After
async def store_memory(
    user_id: str,
    content: str,
    metadata: dict[str, Any] | None = None
) -> MemoryRecord:
    ...
```

### Database Client
```python
# Before
def get_database_client(connection_string):
    ...

# After
from supabase import Client

def get_database_client(
    connection_string: str
) -> Client:
    ...
```

---

## Config-Specific Patterns

### Settings Class
```python
# Before
class Settings:
    def __init__(self):
        self.llm_provider = os.getenv("LLM_PROVIDER")

# After (Pydantic)
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    llm_provider: str = "openai"
    model_name: str = "gpt-4"
    api_key: str | None = None
```

### Config Loading
```python
# Before
def get_settings():
    return Settings()

# After
from functools import lru_cache

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### Environment Parsing
```python
# Before
def parse_bool_env(key, default):
    ...

# After
def parse_bool_env(key: str, default: bool = False) -> bool:
    ...
```

---

## File-by-File Strategy

### clients/memory.py (3 annotations)
- Mem0 initialization
- Memory CRUD operations
- Search functionality

### clients/llm.py (~2 annotations)
- Provider factory
- Model configuration

### clients/database.py (~2 annotations)
- Connection factory
- Client initialization

### config/__init__.py (~3 annotations)
- Module exports
- Factory functions
- Singleton management

### config/settings.py (~5 annotations)
- Settings class (should already be typed via Pydantic)
- Custom validators
- Computed properties

---

## Type Definitions to Add

```python
from typing import TypedDict, Literal
from dataclasses import dataclass

LLMProvider = Literal["openai", "anthropic", "ollama", "google"]
DatabaseProvider = Literal["supabase", "postgres"]

@dataclass
class MemoryRecord:
    id: str
    user_id: str
    content: str
    metadata: dict[str, Any]
    created_at: datetime

class ClientConfig(TypedDict, total=False):
    timeout: int
    retries: int
    api_key: str
    base_url: str
```

---

## Verification

```bash
# Check clients
mypy src/clients/ --ignore-missing-imports --disallow-untyped-defs

# Check config
mypy src/config/ --ignore-missing-imports --disallow-untyped-defs
```

---

## Completion Checklist

- [ ] Annotate clients/memory.py (3 functions)
- [ ] Annotate clients/llm.py (~2 functions)
- [ ] Annotate clients/database.py (~2 functions)
- [ ] Annotate config/__init__.py (~3 functions)
- [ ] Review config/settings.py (Pydantic should handle most)
- [ ] Add Literal types for providers
- [ ] Verify with mypy --disallow-untyped-defs
- [ ] Run test suite
- [ ] Commit changes

---

## Notes

- Pydantic Settings classes are mostly self-typing
- Use Literal for finite choice parameters
- lru_cache decorated functions need explicit return types
- Client factory functions return typed clients
