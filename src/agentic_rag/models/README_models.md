# Models Package

Pydantic models for knowledge graph data structures.

## Overview

This package provides Pydantic models for structured data used throughout the Agentic RAG system. Models include validation, serialization, and helper methods for Neo4j integration.

## Modules

### document_reference.py

Model for tracking entity-to-document relationships.

```python
from src.agentic_rag.models import DocumentReference

# Create document reference
ref = DocumentReference(
    filename="2023 Q3 INTC.pdf",
    company="Intel",
    quarter="Q3",
    year=2023,
    mention_count=5
)

# Serialize for Neo4j storage
ref_dict = ref.to_dict()
# Returns: {'filename': '2023 Q3 INTC.pdf', 'company': 'Intel', ...}

# Extract from chunk metadata
ref = DocumentReference.from_chunk_metadata({
    'source': 'documents/2023 Q3 INTC.pdf',
    'company': 'Intel',
    'fiscal_quarter': 'Q3',
    'fiscal_year': 2023
})
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| filename | str | Source document filename |
| company | str | Company name (resolved from ticker) |
| quarter | str | Fiscal quarter (Q1-Q4) |
| year | int | Fiscal year |
| mention_count | int | Number of mentions in document |

**Validation:**
- Quarter must be Q1, Q2, Q3, or Q4
- Year must be >= 1900 and <= 2100
- Filename must be non-empty

**Helper Methods:**
- `to_dict()`: Convert to dictionary for Neo4j storage
- `from_chunk_metadata()`: Extract from ingestion metadata
- `sanitize_filename()`: Clean filename for storage

## Usage in Neo4j

Document references are stored as a list property on Entity nodes:

```cypher
// Entity with document references
(e:Entity {
  name: 'Intel',
  entity_type: 'company',
  document_refs: [
    {filename: '2023 Q3 INTC.pdf', company: 'Intel', quarter: 'Q3', year: 2023, mention_count: 5},
    {filename: '2023 Q4 INTC.pdf', company: 'Intel', quarter: 'Q4', year: 2023, mention_count: 8}
  ]
})
```

### Cross-Document Queries

```cypher
// Entities mentioned in multiple documents
MATCH (e:Entity)
WHERE size(e.document_refs) > 1
RETURN e.name, e.entity_type, size(e.document_refs) as doc_count
ORDER BY doc_count DESC
LIMIT 20

// Entities from a specific company
MATCH (e:Entity)
WHERE ANY(d IN e.document_refs WHERE d.company = 'Intel')
RETURN e.name, e.entity_type, e.mention_count

// Entities from Q4 2024 filings
MATCH (e:Entity)
WHERE ANY(d IN e.document_refs WHERE d.quarter = 'Q4' AND d.year = 2024)
RETURN e.name, e.entity_type
```

## Integration Points

### Neo4j Store

`neo4j_store.py` uses DocumentReference for entity storage:
- `add_entities()` accepts `document_metadata` parameter
- References appended on entity MATCH, initialized on CREATE
- Mention counts incremented for existing references

### Ingestion Pipeline

`pipeline.py` extracts document metadata during ingestion:
- Filename parsed for fiscal metadata
- DocumentReference created per chunk
- Passed to `add_entities()` for storage

## Backfill Script

Located at `scripts/backfill_document_refs.py`:

```bash
# Dry run - preview changes
python scripts/backfill_document_refs.py --dry-run

# Backfill with custom batch size
python scripts/backfill_document_refs.py --batch-size 100

# Resume from position
python scripts/backfill_document_refs.py --skip 500
```

**Backfill Features:**
- Idempotent (safe to run multiple times)
- Skips entities with existing document_refs
- Batch processing with progress tracking
- Retry logic with exponential backoff

## Testing

```bash
# Run document reference tests
pytest tests/rag_pipeline/test_document_refs.py -v
```

**Test Coverage:** 36 tests covering validation, serialization, and integration

## Dependencies

- pydantic>=2.0.0: Data validation and serialization
- structlog: Structured logging

## Related Documentation

- [CLAUDE.md](../../../CLAUDE.md) - Cross-document query patterns
- [Agentic RAG Guide](../../../docs/3-architecture/agentic-rag.md) - System architecture
