# MyPy Fix Phase 10: Type Annotations - agentic_rag/ingestion/

**Status**: Not Started
**Estimated Errors**: 30
**Files**: 4
**Prerequisites**: Phase 09 complete

---

## Objective

Add missing type annotations to the `src/agentic_rag/ingestion/` module (document processing pipeline).

---

## Files to Annotate

| File | Missing Annotations |
|------|---------------------|
| src/agentic_rag/ingestion/pipeline.py | 8 |
| src/agentic_rag/ingestion/embedder.py | 9 |
| src/agentic_rag/ingestion/chunker.py | 4 |
| src/agentic_rag/ingestion/knowledge_extractor.py | 4 |
| src/agentic_rag/config.py | 9 |

---

## Ingestion-Specific Patterns

### Pipeline Methods
```python
# Before
async def process_document(document, options):
    ...

# After
async def process_document(
    document: Document,
    options: ProcessingOptions | None = None
) -> ProcessedDocument:
    ...
```

### Chunking Functions
```python
# Before
def chunk_text(text, chunk_size, overlap):
    ...

# After
def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 50
) -> list[TextChunk]:
    ...
```

### Embedding Generation
```python
# Before
async def generate_embeddings(texts, batch_size):
    ...

# After
async def generate_embeddings(
    texts: list[str],
    batch_size: int = 32
) -> list[list[float]]:
    ...
```

### Knowledge Extraction
```python
# Before
async def extract_entities(text):
    ...

# After
async def extract_entities(
    text: str
) -> list[ExtractedEntity]:
    ...
```

---

## File-by-File Strategy

### pipeline.py (8 annotations)
- Document loading
- Processing orchestration
- Batch processing
- Error handling

### embedder.py (9 annotations)
- Embedding model initialization
- Batch embedding generation
- Dimension handling
- Provider switching

### chunker.py (4 annotations)
- Text splitting strategies
- Overlap handling
- Semantic chunking
- Metadata preservation

### knowledge_extractor.py (4 annotations)
- Entity extraction
- Relationship detection
- Fact extraction
- Temporal parsing

### config.py (9 annotations)
- Configuration loading
- Default values
- Validation
- Environment parsing

---

## Type Definitions to Add

```python
from typing import TypedDict
from dataclasses import dataclass

@dataclass
class Document:
    id: str
    content: str
    metadata: dict[str, Any]
    source: str

@dataclass
class TextChunk:
    id: str
    content: str
    start_idx: int
    end_idx: int
    metadata: dict[str, Any]

@dataclass
class ProcessedDocument:
    document: Document
    chunks: list[TextChunk]
    embeddings: list[list[float]]
    entities: list[ExtractedEntity]

@dataclass
class ExtractedEntity:
    name: str
    type: str
    confidence: float
    span: tuple[int, int]

class ProcessingOptions(TypedDict, total=False):
    chunk_size: int
    overlap: int
    extract_entities: bool
    generate_embeddings: bool
```

---

## Verification

```bash
# Check specific file
mypy src/agentic_rag/ingestion/pipeline.py --ignore-missing-imports --disallow-untyped-defs

# Check entire module
mypy src/agentic_rag/ingestion/ --ignore-missing-imports --disallow-untyped-defs
```

---

## Completion Checklist

- [ ] Annotate pipeline.py (8 functions)
- [ ] Annotate embedder.py (9 functions)
- [ ] Annotate chunker.py (4 functions)
- [ ] Annotate knowledge_extractor.py (4 functions)
- [ ] Annotate config.py (9 functions)
- [ ] Add shared type definitions
- [ ] Verify with mypy --disallow-untyped-defs
- [ ] Run test suite
- [ ] Commit changes

---

## Notes

- Embedding dimensions vary by model (768 for Ollama, 1536 for OpenAI)
- Document metadata is often dynamic - use dict[str, Any]
- Consider Protocol for embedding providers
- Chunk IDs should be deterministic
