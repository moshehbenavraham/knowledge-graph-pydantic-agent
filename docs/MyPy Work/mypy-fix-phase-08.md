# MyPy Fix Phase 08: Type Annotations - agentic_rag/storage/

**Status**: Not Started
**Estimated Errors**: 35
**Files**: 6
**Prerequisites**: Phase 07 complete

---

## Objective

Add missing type annotations to the `src/agentic_rag/storage/` module (database clients and storage backends).

---

## Files to Annotate

| File | Missing Annotations |
|------|---------------------|
| src/agentic_rag/storage/connection_manager.py | 14 |
| src/agentic_rag/storage/postgres_store.py | 7 |
| src/agentic_rag/storage/migrations/neo4j_init.py | 7 |
| src/agentic_rag/storage/migrations/postgres_migrations.py | 5 |
| src/agentic_rag/storage/neo4j_store.py | ~2 |
| src/agentic_rag/storage/graphiti_client.py | ~2 |

---

## Storage-Specific Patterns

### Connection Manager
```python
# Before
class ConnectionManager:
    def __init__(self):
        self._postgres = None
        self._neo4j = None

    async def get_postgres(self):
        ...

# After
from typing import Optional
from asyncpg import Pool
from neo4j import AsyncDriver

class ConnectionManager:
    def __init__(self) -> None:
        self._postgres: Optional[Pool] = None
        self._neo4j: Optional[AsyncDriver] = None

    async def get_postgres(self) -> Pool:
        ...
```

### Database Operations
```python
# Before
async def execute_query(query, params):
    ...

# After
async def execute_query(
    query: str,
    params: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    ...
```

### Vector Store Methods
```python
# Before
async def similarity_search(embedding, k):
    ...

# After
async def similarity_search(
    embedding: list[float],
    k: int = 10
) -> list[DocumentChunk]:
    ...
```

### Graph Store Methods
```python
# Before
async def get_related_entities(entity_id):
    ...

# After
async def get_related_entities(
    entity_id: str
) -> list[Entity]:
    ...
```

---

## File-by-File Strategy

### connection_manager.py (14 annotations)
- Connection pooling
- Lazy initialization
- Health checks
- Cleanup methods

### postgres_store.py (7 annotations)
- CRUD operations
- Vector similarity search
- Embedding storage
- Query execution

### migrations/neo4j_init.py (7 annotations)
- Schema creation
- Index setup
- Constraint definitions
- Migration runners

### migrations/postgres_migrations.py (5 annotations)
- Table creation
- Index management
- Migration tracking

### neo4j_store.py (~2 annotations)
- Graph queries
- Node/relationship creation

### graphiti_client.py (~2 annotations)
- Graphiti API wrapper
- Entity extraction

---

## Type Definitions to Add

Consider adding these to a types.py file:
```python
from typing import TypedDict

class DocumentChunk(TypedDict):
    id: str
    content: str
    embedding: list[float]
    metadata: dict[str, Any]

class Entity(TypedDict):
    id: str
    name: str
    type: str
    properties: dict[str, Any]

class Relationship(TypedDict):
    source_id: str
    target_id: str
    type: str
    properties: dict[str, Any]
```

---

## Verification

```bash
# Check specific file
mypy src/agentic_rag/storage/connection_manager.py --ignore-missing-imports --disallow-untyped-defs

# Check entire module
mypy src/agentic_rag/storage/ --ignore-missing-imports --disallow-untyped-defs
```

---

## Completion Checklist

- [ ] Annotate connection_manager.py (14 functions)
- [ ] Annotate postgres_store.py (7 functions)
- [ ] Annotate migrations/neo4j_init.py (7 functions)
- [ ] Annotate migrations/postgres_migrations.py (5 functions)
- [ ] Annotate neo4j_store.py
- [ ] Annotate graphiti_client.py
- [ ] Add TypedDict definitions if needed
- [ ] Verify with mypy --disallow-untyped-defs
- [ ] Run test suite
- [ ] Commit changes

---

## Notes

- Database drivers may have incomplete type stubs
- Use Any for untyped third-party return values
- Consider Protocol for database client interfaces
- Connection pool types vary by driver
