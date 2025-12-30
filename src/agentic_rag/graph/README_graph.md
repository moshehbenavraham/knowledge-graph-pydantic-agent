# Graph Utilities Package

Knowledge graph utilities for temporal parsing, numeric fact extraction, relationship scoring, type hierarchy management, and advanced query engines.

## Overview

This package provides specialized utilities for processing and enriching the Neo4j knowledge graph. All modules work together to transform raw episode data into a fully queryable temporal knowledge base.

**Phase 02 Additions:** Multi-hop query engine, temporal trend queries, and cross-entity comparison capabilities.

## Phase 02 Query Engines

### multi_hop.py

Multi-hop path traversal for discovering indirect connections between entities.

```python
from src.agentic_rag.graph import (
    execute_multi_hop,
    MultiHopQuery,
    find_paths_between,
    explore_entity_neighborhood,
)

# Build multi-hop query
query = MultiHopQuery(
    start_entity="Intel",
    end_entity="Mobileye",  # Optional
    min_hops=1,
    max_hops=3,
    min_strength=0.5,
    entity_type_filter="organization",
    limit=20,
)

# Execute traversal
results = await execute_multi_hop(connection_manager, query)

for path in results:
    print(path.get_path_summary())
    # Output: "Intel --[acquired]--> Mobileye"
    print(f"Strength: {path.cumulative_strength}")

# Convenience functions
paths = await find_paths_between(connection_manager, "Intel", "AMD", max_hops=3)
paths = await explore_entity_neighborhood(connection_manager, "Intel", hops=2)
```

**Key Features:**
- Variable-depth Cypher generation (1-3 hops)
- Relationship type and strength filtering
- Entity type filtering with TypeHierarchy expansion
- Cumulative path strength calculation (product of edge strengths)

**Agent Tool:** `graph_traverse`

### temporal_queries.py

Temporal trend analysis using fiscal quarter/year metadata.

```python
from src.agentic_rag.graph import (
    execute_temporal_query,
    TemporalQuery,
    get_entity_trend,
    compare_quarters,
    compare_years,
    TrendResult,
    ComparisonResult,
)

# Build temporal query
query = TemporalQuery(
    entity_name="Intel",
    metric_type="revenue",
    start_quarter="Q1",
    start_year=2023,
    end_quarter="Q4",
    end_year=2023,
)

# Execute query
trend = await execute_temporal_query(connection_manager, query)
print(f"Direction: {trend.trend_direction}")
print(f"Data points: {len(trend.data_points)}")

# Convenience functions
trend = await get_entity_trend(connection_manager, "Intel", "revenue", 4)
qoq = await compare_quarters(connection_manager, "Intel", "revenue", "Q3", "Q4", 2023)
yoy = await compare_years(connection_manager, "Intel", "revenue", "Q3", 2022, 2023)
```

**Key Features:**
- Time-series data retrieval from knowledge graph
- Quarter-over-quarter (QoQ) comparison
- Year-over-year (YoY) comparison
- Trend direction detection (UP, DOWN, STABLE)
- Percent change calculation with negative baseline handling

**Agent Tool:** `temporal_trend`

### entity_comparison.py

Cross-entity comparison across documents and time periods.

```python
from src.agentic_rag.graph import (
    execute_comparison,
    ComparisonQuery,
    EntityComparisonResult,
    EntityMetrics,
)

# Build comparison query
query = ComparisonQuery(
    entities=["Intel", "AMD", "NVIDIA"],
    metric_type="revenue",
    fiscal_quarter="Q3",
    fiscal_year=2023,
    rank_by="value",
    rank_ascending=False,
)

# Execute comparison
result = await execute_comparison(connection_manager, query)

for entity, metrics in result.entity_metrics.items():
    print(f"{entity}: {metrics.value} {metrics.unit}")

# Ranking
print(f"Rankings: {result.rankings}")
# Output: ['NVIDIA', 'Intel', 'AMD']
```

**Key Features:**
- Side-by-side entity metric comparison
- Type hierarchy validation (prevents invalid comparisons)
- Ranking functionality (ascending/descending)
- Growth rate calculation (QoQ/YoY)

**Agent Tool:** `compare_entities`

## Phase 01 Modules

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
# Phase 02 query engine tests
pytest tests/agentic_rag/graph/test_multi_hop.py -v          # 53 tests
pytest tests/agentic_rag/graph/test_temporal_queries.py -v   # 62 tests
pytest tests/agentic_rag/graph/test_entity_comparison.py -v  # 84 tests

# Phase 01 module tests
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
