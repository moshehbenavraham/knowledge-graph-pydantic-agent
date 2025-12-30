# Entity Resolution Package

Multi-pass entity deduplication with canonical name resolution, fuzzy matching, and merge history tracking.

## Overview

This package reduces entity fragmentation in the knowledge graph by identifying and merging duplicate entities. It uses a four-pass deduplication algorithm with configurable thresholds and full merge history for potential rollback.

## Modules

### canonical_names.py

Canonical name normalization and ticker resolution.

```python
from src.agentic_rag.entity_resolution import (
    normalize_entity_name,
    get_canonical_name,
    is_excluded_term
)

# Normalize entity names
normalize_entity_name("Apple Inc.")  # Returns: "apple"
normalize_entity_name("Microsoft Corporation")  # Returns: "microsoft"

# Get canonical name from ticker
get_canonical_name("AAPL")  # Returns: "Apple"
get_canonical_name("MSFT")  # Returns: "Microsoft"

# Check excluded terms
is_excluded_term("the company")  # Returns: True
is_excluded_term("Intel")  # Returns: False
```

**Company Suffixes Stripped:**
- Inc., Corp., Corporation, LLC, Ltd., Limited
- Company, Co., Group, Holdings, International
- 24+ suffix patterns with multi-pass stripping

**Ticker Mappings:**
50+ major company mappings including AAPL, MSFT, NVDA, INTC, AMD, GOOGL, META, AMZN, etc.

### deduplication.py

Four-pass deduplication engine with configurable thresholds.

```python
from src.agentic_rag.entity_resolution import EntityResolver, Entity

# Create resolver
resolver = EntityResolver(fuzzy_threshold=90)

# Find duplicates
entities = [
    Entity(id="1", name="Apple Inc.", entity_type="company"),
    Entity(id="2", name="AAPL", entity_type="company"),
    Entity(id="3", name="Apple", entity_type="company"),
]
groups = resolver.find_duplicates(entities)
# Returns: [DuplicateGroup(canonical="Apple", entities=[...])]
```

**Deduplication Passes:**

| Pass | Method | Confidence | Description |
|------|--------|------------|-------------|
| 1 | Ticker Resolution | 0.95 | Known ticker-to-company mappings |
| 2 | Exact Match | 0.90 | Normalized string comparison |
| 3 | Fuzzy Match | 0.75 | RapidFuzz with 90% threshold |
| 4 | Context Match | 0.60 | Document reference overlap |

### merge_history.py

Neo4j-based merge history logging and retrieval.

```python
from src.agentic_rag.entity_resolution import MergeHistory, MergeOperation

# Log merge operation
history = MergeHistory(neo4j_driver)
await history.log_merge(MergeOperation(
    canonical_id="1",
    merged_ids=["2", "3"],
    match_type=MergeMatchType.EXACT,
    confidence=0.90,
    merged_by="backfill_script"
))

# Query merge history
merges = await history.get_merges_for_entity("1")
```

**Merge History Features:**
- Complete audit trail of all merges
- Rollback support via stored merge operations
- Query by entity, timestamp, or match type

## Integration Points

### Knowledge Extractor

`knowledge_extractor.py` uses normalization during entity extraction:
- All extracted entities pass through `normalize_entity_name()`
- Excluded generic terms filtered before storage
- Canonical names applied for known tickers

### Ingestion Pipeline

`pipeline.py` applies normalization before Neo4j storage:
- Entities normalized and deduplicated
- Document references preserved across merges
- Importance scores recalculated after merge

## Merge Script

Located at `scripts/merge_duplicate_entities.py`:

```bash
# Dry run - preview merges
python scripts/merge_duplicate_entities.py --dry-run

# Interactive mode - confirm each merge
python scripts/merge_duplicate_entities.py --interactive

# Batch mode - apply all merges
python scripts/merge_duplicate_entities.py --batch

# With custom fuzzy threshold
python scripts/merge_duplicate_entities.py --fuzzy-threshold 85
```

**Merge Process:**
1. Fetch all entities from Neo4j
2. Run four-pass deduplication
3. For each duplicate group:
   - Select canonical entity (highest importance)
   - Transfer relationships to canonical
   - Log merge history
   - Delete merged entities

## Testing

```bash
# Run entity resolution tests
pytest tests/rag_pipeline/test_entity_deduplication.py -v

# Run specific test classes
pytest tests/rag_pipeline/test_entity_deduplication.py::TestNormalizeEntityName -v
pytest tests/rag_pipeline/test_entity_deduplication.py::TestFuzzyMatchPass -v
```

**Test Coverage:** 66 tests covering all modules and edge cases

## Dependencies

- rapidfuzz>=3.0.0: Fast fuzzy string matching
- neo4j: Async driver for database operations
- pydantic: Data validation and models
- structlog: Structured logging

## Configuration

No additional configuration required. Settings are derived from main application config:
- Neo4j connection: Uses existing `NEO4J_*` environment variables
- Fuzzy threshold: 90% default, configurable per-call

## Related Documentation

- [CLAUDE.md](../../../CLAUDE.md) - Entity deduplication overview
- [Agentic RAG Guide](../../../docs/3-architecture/agentic-rag.md) - System architecture
