# Graph Utilities Package

Knowledge graph utilities for temporal parsing, numeric fact extraction, relationship scoring, and type hierarchy management.

## Overview

This package provides specialized utilities for processing and enriching the Neo4j knowledge graph. All modules work together to transform raw episode data into a fully queryable temporal knowledge base.

## Modules

### temporal_parser.py

Parse document filenames to extract fiscal metadata.

```python
from src.agentic_rag.graph import parse_filename, TemporalMetadata

# Parse document filename
metadata = parse_filename("2023 Q3 INTC.pdf")
# Returns: TemporalMetadata(fiscal_year=2023, fiscal_quarter='Q3', company='Intel', ticker='INTC')

# Extract properties for Neo4j
props = extract_temporal_properties("2023 Q3 INTC.pdf")
# Returns: {'fiscal_year': 2023, 'fiscal_quarter': 'Q3', 'company': 'Intel', ...}
```

**Key Features:**
- Regex-based filename parsing (pattern: `YYYY QN TICKER.pdf`)
- Ticker-to-company name resolution (AAPL, MSFT, NVDA, INTC, AMD)
- Frozen dataclass for immutable metadata

### numeric_parser.py

Extract structured numeric facts from episode text.

```python
from src.agentic_rag.graph import parse_numeric_facts, NumericFact

# Parse financial text
facts = parse_numeric_facts("Revenue was $40,665 million, up 12% year-over-year.")
# Returns: [
#   NumericFact(value=40665000000, unit='USD', original_text='$40,665 million'),
#   NumericFact(value=0.12, unit='percent', original_text='12%')
# ]
```

**Supported Patterns:**
- Currency amounts: `$1.5 billion`, `EUR 500 million`
- Percentages: `12%`, `up 5.5%`
- Magnitudes: thousands, millions, billions, trillions

**Currency Support:** USD, EUR, GBP, JPY, CNY, CAD, AUD, CHF

### relationship_scoring.py

Calculate dynamic relationship strength based on evidence.

```python
from src.agentic_rag.graph import calculate_relationship_strength, ScoringConfig

# Calculate strength score
strength = calculate_relationship_strength(
    relationship_type="acquired",
    chunk_count=5,
    source_importance=0.8,
    target_importance=0.7
)
# Returns: 0.85 (high-confidence acquisition relationship)
```

**Scoring Formula:**
```
strength = (0.4 * chunk_factor) + (0.3 * type_factor) + (0.3 * importance_factor)
```

**Type Priorities (1.0 = highest):**
- acquired, owns: 1.0
- founded, invested_in: 0.9
- partners_with, works_at: 0.5
- related_to, mentioned_in: 0.25

### type_hierarchy.py

Semantic entity type grouping for hierarchical queries.

```python
from src.agentic_rag.graph import get_type_hierarchy, TypeHierarchy

hierarchy = get_type_hierarchy()

# Get subtypes for a parent type
subtypes = hierarchy.get_subtypes("organization")
# Returns: ['company', 'department', 'subsidiary', 'division', ...]

# Build Cypher WHERE clause
clause, params = hierarchy.build_type_match_cypher("organization")
# clause: "e.entity_type IN $type_filter"
# params: {'type_filter': ['organization', 'company', ...]}
```

**Type Categories:**

| Parent Type | Subtypes |
|-------------|----------|
| organization | company, department, subsidiary, division, corporation, enterprise, firm, agency, institution |
| financial_metric | revenue, profit, margin, growth_rate, eps, ebitda, income, expense, cost, earnings, cash_flow |
| product | hardware, software, service, platform, solution, application, device, system |
| person | executive, analyst, employee, ceo, cfo, cto, director, manager, founder, chairman |

## Integration Points

### Neo4j Store

All modules integrate with `neo4j_store.py`:
- `add_episodes()` uses `temporal_parser` for fiscal metadata
- `add_relationships()` uses `relationship_scoring` for strength calculation

### Hybrid Search

`hybrid_search.py` uses relationship strength for result boosting:
- Strong relationships (>0.5) boost chunks containing both entities
- Boost formula: `1.0 + (strength - 0.5) * 0.5` (1.0x - 1.25x range)

### Graph Search

`graph_search.py` uses type hierarchy for entity queries:
- `search_entities_by_type("organization")` matches company, department, etc.
- Hierarchical expansion enables semantic type grouping

## Backfill Scripts

Located in `scripts/`:

| Script | Purpose | Command |
|--------|---------|---------|
| `backfill_temporal_metadata.py` | Add fiscal metadata to episodes | `python scripts/backfill_temporal_metadata.py --dry-run` |
| `backfill_numeric_facts.py` | Extract numeric facts from episodes | `python scripts/backfill_numeric_facts.py --batch-size 500` |
| `backfill_relationship_scores.py` | Calculate relationship strengths | `python scripts/backfill_relationship_scores.py --stats-only` |

**Common Options:**
- `--dry-run`: Preview changes without applying
- `--batch-size N`: Configure batch size
- `--skip N`: Resume from position
- `--verify`: Run verification queries after backfill

## Testing

```bash
# Run all graph module tests
pytest tests/rag_pipeline/test_temporal_metadata.py -v
pytest tests/rag_pipeline/test_numeric_facts.py -v
pytest tests/rag_pipeline/test_relationship_scoring.py -v
pytest tests/rag_pipeline/test_type_hierarchy.py -v

# Run performance benchmarks
pytest tests/rag_pipeline/test_performance_benchmarks.py -v
```

## Dependencies

- structlog: Structured logging
- neo4j: Async driver for database operations
- pydantic: Data validation and models

## Related Documentation

- [CLAUDE.md](../../../CLAUDE.md) - Type hierarchy usage examples
- [Agentic RAG Guide](../../../docs/3-architecture/agentic-rag.md) - System architecture
