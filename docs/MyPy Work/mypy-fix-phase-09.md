# MyPy Fix Phase 09: Type Annotations - agentic_rag/search/

**Status**: Not Started
**Estimated Errors**: 25
**Files**: 5
**Prerequisites**: Phase 08 complete

---

## Objective

Add missing type annotations to the `src/agentic_rag/search/` module (search strategies and ranking).

---

## Files to Annotate

| File | Missing Annotations |
|------|---------------------|
| src/agentic_rag/search/ranker.py | 8 |
| src/agentic_rag/search/hybrid_search.py | 5 |
| src/agentic_rag/search/graph_search.py | ~4 |
| src/agentic_rag/search/vector_search.py | ~4 |
| src/agentic_rag/search/intent_analyzer.py | ~4 |

---

## Search-Specific Patterns

### Search Functions
```python
# Before
async def search(query, filters, limit):
    ...

# After
async def search(
    query: str,
    filters: SearchFilters | None = None,
    limit: int = 10
) -> SearchResults:
    ...
```

### Ranker Methods
```python
# Before
def rank_results(results, query, weights):
    ...

# After
def rank_results(
    results: list[SearchResult],
    query: str,
    weights: RankingWeights | None = None
) -> list[RankedResult]:
    ...
```

### Intent Analysis
```python
# Before
def analyze_intent(query):
    ...

# After
from enum import Enum

class SearchIntent(Enum):
    VECTOR_HEAVY = "vector_heavy"
    GRAPH_HEAVY = "graph_heavy"
    HYBRID = "hybrid"
    TEMPORAL = "temporal"
    ENTITY_FOCUSED = "entity_focused"

def analyze_intent(query: str) -> SearchIntent:
    ...
```

### Score Calculation
```python
# Before
def calculate_score(vector_score, graph_score, boost):
    ...

# After
def calculate_score(
    vector_score: float,
    graph_score: float,
    boost: float = 1.0
) -> float:
    ...
```

---

## File-by-File Strategy

### ranker.py (8 annotations)
- Score normalization
- Result merging
- Weight application
- Tie-breaking logic

### hybrid_search.py (5 annotations)
- Parallel search execution
- Result combination
- Strategy selection
- Cache integration

### graph_search.py (~4 annotations)
- Cypher query building
- Entity traversal
- Relationship filtering
- Path scoring

### vector_search.py (~4 annotations)
- Embedding comparison
- Similarity calculation
- Filter application
- Result formatting

### intent_analyzer.py (~4 annotations)
- Query parsing
- Keyword detection
- Intent classification
- Confidence scoring

---

## Type Definitions to Add

```python
from typing import TypedDict
from dataclasses import dataclass
from enum import Enum

class SearchIntent(Enum):
    VECTOR_HEAVY = "vector_heavy"
    GRAPH_HEAVY = "graph_heavy"
    HYBRID = "hybrid"
    TEMPORAL = "temporal"
    ENTITY_FOCUSED = "entity_focused"

@dataclass
class SearchResult:
    id: str
    content: str
    score: float
    source: str
    metadata: dict[str, Any]

@dataclass
class RankedResult(SearchResult):
    rank: int
    normalized_score: float

class RankingWeights(TypedDict, total=False):
    vector_weight: float
    graph_weight: float
    recency_weight: float
    relevance_weight: float
```

---

## Verification

```bash
# Check specific file
mypy src/agentic_rag/search/ranker.py --ignore-missing-imports --disallow-untyped-defs

# Check entire module
mypy src/agentic_rag/search/ --ignore-missing-imports --disallow-untyped-defs
```

---

## Completion Checklist

- [ ] Annotate ranker.py (8 functions)
- [ ] Annotate hybrid_search.py (5 functions)
- [ ] Annotate graph_search.py (~4 functions)
- [ ] Annotate vector_search.py (~4 functions)
- [ ] Annotate intent_analyzer.py (~4 functions)
- [ ] Add shared type definitions
- [ ] Verify with mypy --disallow-untyped-defs
- [ ] Run test suite
- [ ] Commit changes

---

## Notes

- Search results often have optional fields
- Score types should be float, not int
- Consider using Protocols for search strategies
- Intent enum should match existing code
