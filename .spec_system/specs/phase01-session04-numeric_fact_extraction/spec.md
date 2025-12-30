# Session Specification

**Session ID**: `phase01-session04-numeric_fact_extraction`
**Phase**: 01 - Knowledge Graph Improvements
**Status**: Not Started
**Created**: 2025-12-30

---

## 1. Session Overview

This session implements numeric fact extraction from episode text in the Neo4j knowledge graph. The goal is to transform unstructured financial statements like "revenue was $40,665 million" into queryable structured data that enables range-based queries such as "Find all revenue facts > $50B" and entity-specific queries like "What was Apple's Q3 2023 revenue?"

Numeric fact extraction is the fourth session in Phase 01 (Knowledge Graph Improvements) and builds directly on the foundation established by the previous three sessions. Sessions 01-03 established document references (which documents contain entities), temporal metadata (when facts occurred), and entity deduplication (clean entity graph). Session 04 adds the "what" dimension - extracting the actual numeric values from facts.

This capability is essential for financial analysts who need to query specific metrics rather than relying on semantic text search alone. By storing normalized numeric values alongside the original text, the system enables both precise numeric filtering and context preservation for human interpretation.

---

## 2. Objectives

1. Parse numeric values from episode text using regex patterns, extracting value, unit, and preserving original text
2. Add structured `numeric_facts` property to Neo4j Episode nodes with normalized values
3. Create a backfill script to process all existing episodes and populate numeric facts
4. Enable Cypher queries for numeric range filtering across the knowledge graph

---

## 3. Prerequisites

### Required Sessions
- [x] `phase01-session01-document_reference_population` - Document references for source tracking
- [x] `phase01-session02-temporal_metadata_extraction` - Temporal metadata for fact dating
- [x] `phase01-session03-entity_deduplication` - Clean, deduplicated entity graph

### Required Tools/Knowledge
- Python regex (`re` module) for pattern matching
- Neo4j Cypher for graph queries and property updates
- Financial notation formats (millions, billions, currency symbols)

### Environment Requirements
- Neo4j Aura connection configured (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`)
- Python 3.11+ with development dependencies installed
- Access to episode text via existing Cypher queries

---

## 4. Scope

### In Scope (MVP)
- Parse numeric values from episode text with pattern matching
- Support financial formats: millions (M, million), billions (B, billion), thousands (K, thousand)
- Handle currency symbols: USD ($), EUR, GBP
- Parse percentages: 50% -> 0.5 normalized, 50 raw
- Create structured output: `{value: float, unit: str, original: str, type: str}`
- Add `numeric_facts` JSON property to Episode nodes
- Backfill script for existing episodes
- Cypher query examples for range filtering

### Out of Scope (Deferred)
- LLM-based extraction - *Reason: Regex sufficient for MVP financial patterns*
- Non-financial numerics (dates, counts, IDs) - *Reason: Different parsing rules needed*
- Currency conversion - *Reason: Requires exchange rate data and temporal context*
- Cross-entity comparison queries - *Reason: Query layer feature, not extraction*
- Negative value handling - *Reason: Rare in financial filings, add if needed later*

---

## 5. Technical Approach

### Architecture

The numeric parser is implemented as a standalone utility module that processes episode text and returns structured numeric facts. It operates independently of the agent system (following the unified agent principle) and is called by the backfill script and future ingestion pipeline hooks.

```
Episode.text --> NumericParser --> numeric_facts JSON --> Episode.numeric_facts property
```

The parser uses a pipeline of regex patterns, each specialized for a specific format:
1. Currency with magnitude: `$40.6B`, `$40,665 million`
2. Plain magnitude: `40 billion`, `40.6B`
3. Percentages: `50%`, `50 percent`

### Design Patterns
- **Strategy Pattern**: Different regex handlers for different numeric formats
- **Builder Pattern**: Construct NumericFact objects from matched components
- **Utility Module**: Stateless functions, no class instances needed for parsing

### Technology Stack
- Python 3.11+ (regex, json, typing)
- Neo4j Python driver (existing in codebase)
- Pydantic models for NumericFact structure
- structlog for logging

---

## 6. Deliverables

### Files to Create
| File | Purpose | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/graph/numeric_parser.py` | Core numeric extraction logic with regex patterns | ~200 |
| `scripts/backfill_numeric_facts.py` | CLI script to process existing episodes | ~150 |
| `tests/rag_pipeline/test_numeric_facts.py` | Unit tests for parser and backfill | ~250 |

### Files to Modify
| File | Changes | Est. Lines |
|------|---------|------------|
| `src/agentic_rag/graph/__init__.py` | Export NumericParser | ~5 |
| `docs/graph_queries.md` | Add numeric range query examples (if exists) | ~30 |

---

## 7. Success Criteria

### Functional Requirements
- [ ] Parser extracts numeric values from financial text patterns
- [ ] Values normalized correctly (40,665 million -> 40665000000)
- [ ] Currency symbols mapped to ISO codes ($ -> USD)
- [ ] Percentages stored as both raw (50) and normalized (0.5)
- [ ] Original text preserved in output structure
- [ ] Backfill script processes all episodes without errors

### Testing Requirements
- [ ] Unit tests cover all supported formats (15+ test cases)
- [ ] Edge cases tested (no numbers, malformed input, multiple numbers)
- [ ] Backfill script tested with mock Neo4j connection
- [ ] All existing tests still pass (no regressions)

### Quality Gates
- [ ] All files ASCII-encoded (no unicode characters)
- [ ] Unix LF line endings
- [ ] Code follows project conventions (CONVENTIONS.md)
- [ ] Type hints on all functions (MyPy strict)
- [ ] Docstrings on all public functions (Google style)
- [ ] Structured logging with context parameters
- [ ] 75%+ test coverage on new code

---

## 8. Implementation Notes

### Key Considerations
- Regex patterns must handle comma-separated thousands: `40,665`
- Decimal points in both positions: `$40.6B` and `40.665 million`
- Case insensitivity: `Million`, `MILLION`, `million`
- Multiple numeric facts per episode (extract all, not just first)

### Potential Challenges
- **Pattern overlap**: "40.6 billion dollars" vs "$40.6B" need distinct patterns
  - *Mitigation*: Process patterns in order of specificity, most specific first
- **Ambiguous units**: "50" could be percentage or count
  - *Mitigation*: Only extract when unit/context is explicit
- **Performance**: Large episode corpus may slow backfill
  - *Mitigation*: Batch processing with progress logging, transaction batching

### Relevant Considerations
- **[P00] Dual-database architecture**: Numeric facts stored in Neo4j episodes, not PostgreSQL - this is graph metadata enhancement
- **[P00] Unified agent principle**: Parser is a utility function, not a new agent or tool
- **[P00] Centralized config**: Use `get_settings()` if any configuration values needed (e.g., batch size)
- **[Lesson] Structured logging**: Use structlog with context parameters for all log statements

### ASCII Reminder
All output files must use ASCII-only characters (0-127). No unicode symbols, emojis, or special characters.

---

## 9. Testing Strategy

### Unit Tests
- Test each regex pattern independently with known inputs
- Test normalization: millions, billions, thousands conversions
- Test currency mapping: $, EUR, GBP to ISO codes
- Test percentage handling: raw vs normalized values
- Test edge cases: empty string, no numbers, only text

### Integration Tests
- Test parser with real episode text samples from corpus
- Test backfill script with mock Neo4j connection
- Test Cypher queries return expected results after backfill

### Manual Testing
- Run backfill on development Neo4j instance
- Execute sample range queries via Neo4j Browser
- Verify original text preservation in results

### Edge Cases
- Episode with no numeric content (should return empty list)
- Episode with malformed numbers ("$40.6.5B")
- Episode with multiple currencies ("$40B and EUR 35B")
- Very large numbers (trillions)
- Very small numbers (0.001%)

---

## 10. Dependencies

### External Libraries
- `neo4j`: 5.x (existing in project)
- `pydantic`: 2.x (existing in project)
- `structlog`: 24.x (existing in project)
- `re`: stdlib (no external dependency)

### Other Sessions
- **Depends on**: `phase01-session03-entity_deduplication` (clean entity graph)
- **Depended by**: `phase01-session05-relationship_scoring` (uses numeric facts for evidence scoring)

---

## Data Structures

### NumericFact Model
```python
from pydantic import BaseModel
from typing import Literal

class NumericFact(BaseModel):
    """Extracted numeric fact from episode text."""
    value: float  # Normalized value (e.g., 40665000000)
    raw_value: float  # Value before magnitude normalization (e.g., 40665)
    unit: str  # ISO currency code or "percent" or "number"
    magnitude: str | None  # "million", "billion", "thousand", or None
    original_text: str  # Original matched text (e.g., "$40,665 million")
    fact_type: Literal["currency", "percentage", "number"]
```

### Episode Property Structure
```json
{
  "numeric_facts": [
    {
      "value": 40665000000,
      "raw_value": 40665,
      "unit": "USD",
      "magnitude": "million",
      "original_text": "$40,665 million",
      "fact_type": "currency"
    }
  ]
}
```

---

## Cypher Query Examples

### Range Filtering
```cypher
// Find all revenue facts > $50B
MATCH (e:Episode)
WHERE ANY(fact IN e.numeric_facts WHERE fact.value > 50000000000 AND fact.unit = 'USD')
RETURN e.name, e.content, e.numeric_facts

// Find percentage facts between 10% and 50%
MATCH (e:Episode)
WHERE ANY(fact IN e.numeric_facts WHERE fact.fact_type = 'percentage' AND fact.value >= 0.1 AND fact.value <= 0.5)
RETURN e.name, e.content
```

### Entity-Specific Queries
```cypher
// Find numeric facts for a specific entity
MATCH (entity:Entity {name: 'Apple Inc'})-[:MENTIONED_IN]->(e:Episode)
WHERE e.numeric_facts IS NOT NULL
RETURN entity.name, e.content, e.numeric_facts
```

---

## Next Steps

Run `/tasks` to generate the implementation task checklist.
