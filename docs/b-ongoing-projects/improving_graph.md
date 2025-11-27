# Knowledge Graph Improvement Plan

**Document Version:** 1.0
**Date:** 2025-11-10
**Status:** Planning Phase
**Target:** Enable comprehensive QnA capabilities for quarterly earnings analysis

---

## Executive Summary

This plan addresses 5 critical issues in the current Neo4j knowledge graph implementation and proposes enhancements to support the QnA dataset requirements. The improvements will enable temporal analysis, multi-document queries, and entity-based reasoning across 20 quarterly earnings reports.

**Current State:**
- 5,057 entities extracted
- 18,195 relationships created
- 11,521 episode nodes (isolated)
- 94% chunk coverage

**Target State:**
- Fully connected entity-episode graph
- Dynamic importance scoring
- Document-level entity tracking
- Temporal fact queries
- Canonical entity resolution

---

## Problem Analysis

### QnA Dataset Requirements

**Question Types from qna_data.csv (1,687 questions):**

1. **Multi-Doc RAG (46 questions)** - Cross-document temporal analysis
   - "How has Apple's total net sales changed over time?"
   - "Compare Microsoft's revenue growth vs Intel's revenue decline"
   - "Track AWS segment revenue across quarters"

2. **Single-Doc Single-Chunk RAG (39 questions)** - Specific fact lookups
   - "What was Intel's diluted EPS in Q3 2023?"
   - "What legal proceedings does Apple face?"

3. **Single-Doc Multi-Chunk RAG (7 questions)** - Complex document queries
   - "Summarize all risk factors for Microsoft in Q2 2023"
   - "What are the major factors affecting Apple's gross margin?"

**Query Patterns Requiring Graph:**
- Temporal trend analysis (revenue, expenses over quarters)
- Cross-entity comparisons (AAPL vs MSFT vs INTC)
- Segment tracking (AWS, iPhone, Data Center revenue)
- Event-entity linkage (acquisitions, partnerships, legal proceedings)
- Multi-hop reasoning (Company � acquired � Subsidiary � produces � Product)

---

## Issue 1: Episode Isolation

### Problem

**Current State:**
- 11,521 Episode nodes exist but have no connections to Entity nodes
- Episodes store facts like "Mobileye completed its IPO" but don't link to `Mobileye` entity
- Prevents queries like "Show me all facts about Microsoft" or "Timeline of Intel acquisitions"

**Impact on QnA:**
- Cannot answer "What significant events occurred for Apple in Q3 2023?"
- Cannot trace entity timelines across documents
- Cannot connect facts to entities for context

### Solution: Entity-Episode Bridge

**Schema Changes:**

```cypher
// New relationship type
(Episode)-[:MENTIONS]->(Entity)

// Properties
{
  salience: float,        // How central is entity to this fact (0.0-1.0)
  role: string,           // "subject", "object", "context"
  position: int           // Order of mention in fact
}
```

**Implementation Plan:**

1. **Extraction Enhancement** (`src/agentic_rag/ingestion/graphiti_client.py`)
   - After Graphiti extracts episodes, parse the `fact` text to identify mentioned entities
   - Use existing entity names from graph for matching
   - Create `MENTIONS` relationships for each entity reference

2. **Batch Linking Script** (`scripts/link_episodes_to_entities.py`)
   ```python
   # Pseudocode
   for episode in all_episodes:
       fact_text = episode.fact
       entities = extract_entity_mentions(fact_text)  # NER or LLM
       for entity in entities:
           create_relationship(episode, entity, type="MENTIONS")
   ```

3. **Query Capabilities Enabled:**
   ```cypher
   // Get all facts about Microsoft
   MATCH (e:Entity {name: "Microsoft"})<-[:MENTIONS]-(ep:Episode)
   RETURN ep.fact ORDER BY ep.timestamp

   // Timeline of acquisitions
   MATCH (e:Entity)-[:RELATED_TO {type: "acquired"}]->(target)
   MATCH (ep:Episode)-[:MENTIONS]->(e)
   WHERE ep.fact CONTAINS "acquisition"
   RETURN e.name, target.name, ep.fact, ep.timestamp
   ```

**Estimated Effort:** 2-3 days (1 day implementation, 1-2 days batch linking)

---

## Issue 2: Static Importance Scores

### Problem

**Current State:**
- All entities have `importance_score = 0.5` (hardcoded default)
- No differentiation between critical entities (Microsoft, Intel) and minor ones (dates, forms)

**Impact on QnA:**
- Cannot prioritize search results by entity importance
- Cannot weight relationships by entity significance
- Cannot filter "noise" entities for cleaner results

### Solution: Dynamic Importance Calculation

**Scoring Algorithm:**

```python
def calculate_importance(entity):
    """
    Multi-factor importance scoring:
    - Mention frequency: 30% weight
    - Relationship count: 25% weight
    - Document coverage: 25% weight
    - Entity type priority: 20% weight
    """
    mention_score = min(entity.mention_count / 100, 1.0) * 0.30
    relationship_score = min(entity.relationship_count / 50, 1.0) * 0.25
    document_score = len(entity.document_refs) / 20 * 0.25

    type_weights = {
        "company": 1.0,
        "person": 0.9,
        "product": 0.8,
        "organization": 0.7,
        "technology": 0.6,
        "location": 0.4,
        "event": 0.3
    }
    type_score = type_weights.get(entity.type, 0.5) * 0.20

    return mention_score + relationship_score + document_score + type_score
```

**Implementation Plan:**

1. **Batch Scoring Script** (`scripts/compute_importance_scores.py`)
   - Query all entities
   - Calculate importance using algorithm above
   - Update `importance_score` property

2. **Incremental Updates** (in ingestion pipeline)
   - Recalculate score when entity is updated
   - Store score in entity metadata

3. **Usage in Search:**
   ```cypher
   // Prioritize high-importance entities
   MATCH (e:Entity)
   WHERE e.name CONTAINS $search_term
   RETURN e ORDER BY e.importance_score DESC LIMIT 10
   ```

**Estimated Effort:** 1 day

---

## Issue 3: Unused Document References

### Problem

**Current State:**
- `entity.document_refs` is always empty (never populated)
- Only `chunk_refs` are tracked
- Cannot answer "Which documents mention Microsoft?"

**Impact on QnA:**
- Cannot trace entity presence across documents
- Cannot answer multi-document queries efficiently
- Cannot identify cross-document entity relationships

### Solution: Document-Level Entity Tracking

**Schema Update:**

```python
# In Entity node
document_refs: [
    "6d9b16be-20ad-42e8-9762-795efe14dd58",  # 2023 Q3 INTC doc UUID
    "a3f2c891-5678-4def-9abc-123456789def"   # 2023 Q2 INTC doc UUID
]

document_metadata: {
    "6d9b16be-20ad-42e8-9762-795efe14dd58": {
        "file_name": "2023 Q3 INTC.pdf",
        "company": "Intel",
        "quarter": "Q3",
        "year": "2023",
        "mention_count": 15
    }
}
```

**Implementation Plan:**

1. **Update Ingestion Pipeline** (`src/agentic_rag/storage/neo4j_store.py:add_entities()`)
   ```python
   # When adding/updating entity
   ON CREATE SET
       e.document_refs = [$document_id]
   ON MATCH SET
       e.document_refs = CASE
           WHEN $document_id IN e.document_refs THEN e.document_refs
           ELSE e.document_refs + $document_id
       END
   ```

2. **Batch Backfill Script** (`scripts/backfill_document_refs.py`)
   ```python
   # For each entity
   for entity in entities:
       chunk_ids = entity.chunk_refs
       # Query PostgreSQL to get document_ids for these chunks
       doc_ids = get_document_ids_for_chunks(chunk_ids)
       # Update entity
       entity.document_refs = doc_ids
   ```

3. **Query Capabilities:**
   ```cypher
   // Entities mentioned in multiple documents
   MATCH (e:Entity)
   WHERE size(e.document_refs) > 5
   RETURN e.name, size(e.document_refs) as doc_count
   ORDER BY doc_count DESC

   // Cross-document entity analysis
   MATCH (e:Entity)
   WHERE "2023 Q3 INTC.pdf" IN e.document_metadata.*.file_name
   AND "2023 Q2 INTC.pdf" IN e.document_metadata.*.file_name
   RETURN e.name, e.type
   ```

**Estimated Effort:** 1-2 days

---

## Issue 4: Temporal Metadata

### Problem

**Current State:**
- Episode timestamps reflect ingestion time (2025-11-09), not document date (Q3 2023)
- Cannot query "What happened in Q3 2023?"
- No temporal ordering of facts

**Impact on QnA:**
- Cannot answer temporal queries ("Show me Apple's revenue trend")
- Cannot filter by quarter/year
- Cannot build timeline visualizations

### Solution: Document-Aware Temporal Metadata

**Schema Enhancement:**

```python
# Episode properties
{
    "timestamp": "2025-11-09T22:21:35Z",           # Ingestion time (keep)
    "document_date": "2023-09-30",                 # Document quarter end
    "fiscal_quarter": "Q3",                        # Extracted quarter
    "fiscal_year": 2023,                           # Extracted year
    "company": "Intel",                            # Source company
    "temporal_relevance": "point",                 # point | range
    "start_date": "2023-07-01",                    # For range facts
    "end_date": "2023-09-30"                       # For range facts
}

# Entity properties (add)
{
    "first_document_date": "2022-09-30",           # Earliest mention
    "last_document_date": "2023-09-30",            # Most recent mention
    "temporal_span_quarters": 4                    # Quarters spanned
}
```

**Implementation Plan:**

1. **Document Metadata Enrichment**
   - Parse document filename to extract quarter/year
   - Store in document metadata during ingestion
   - Format: `2023 Q3 AAPL.pdf` � `{quarter: "Q3", year: 2023, company: "AAPL"}`

2. **Episode Enhancement** (`src/agentic_rag/ingestion/pipeline.py`)
   ```python
   async def create_episode(fact, chunk_id, document_id):
       # Get document metadata
       doc_meta = await get_document_metadata(document_id)

       episode = {
           "fact": fact,
           "timestamp": datetime.now(),              # Ingestion time
           "document_date": doc_meta["quarter_end"], # Q3 2023 end
           "fiscal_quarter": doc_meta["quarter"],    # "Q3"
           "fiscal_year": doc_meta["year"],          # 2023
           "company": doc_meta["company"]            # "AAPL"
       }
   ```

3. **Entity Temporal Tracking**
   ```cypher
   // Update entity temporal span when adding document
   MATCH (e:Entity)
   SET e.first_document_date = CASE
       WHEN e.first_document_date IS NULL OR $doc_date < e.first_document_date
       THEN $doc_date
       ELSE e.first_document_date
   END,
   e.last_document_date = CASE
       WHEN e.last_document_date IS NULL OR $doc_date > e.last_document_date
       THEN $doc_date
       ELSE e.last_document_date
   END
   ```

4. **Query Capabilities:**
   ```cypher
   // Facts from Q3 2023
   MATCH (ep:Episode)
   WHERE ep.fiscal_quarter = "Q3" AND ep.fiscal_year = 2023
   RETURN ep.fact, ep.company

   // Entity timeline
   MATCH (e:Entity {name: "Microsoft"})<-[:MENTIONS]-(ep:Episode)
   RETURN ep.fiscal_quarter, ep.fiscal_year, ep.fact
   ORDER BY ep.fiscal_year, ep.fiscal_quarter

   // Cross-quarter trends
   MATCH (e:Entity {name: "iPhone"})<-[:MENTIONS]-(ep:Episode)
   WHERE ep.fact CONTAINS "revenue"
   RETURN ep.fiscal_year, ep.fiscal_quarter, ep.fact
   ORDER BY ep.fiscal_year, ep.fiscal_quarter
   ```

**Estimated Effort:** 2-3 days

---

## Issue 5: Entity Deduplication

### Problem

**Current State:**
- "Company" appears 266 times (generic references)
- "Apple" vs "Apple Inc." are separate entities (127 vs 106 mentions)
- "Microsoft" vs "Microsoft Corporation" fragmentation

**Impact on QnA:**
- Diluted entity relationships
- Incomplete entity histories
- Inaccurate importance scores

### Solution: Canonical Entity Resolution

**Strategy: Multi-Pass Deduplication**

**Pass 1: Exact Match Normalization**
```python
canonical_mappings = {
    "Apple Inc.": "Apple",
    "Microsoft Corporation": "Microsoft",
    "Intel Corporation": "Intel",
    "Amazon.com, Inc.": "Amazon",
    "NVIDIA Corporation": "NVIDIA"
}
```

**Pass 2: Fuzzy Matching**
```python
from fuzzywuzzy import fuzz

def find_duplicates(entities):
    """
    Group entities by similarity:
    - Same type
    - >90% string similarity
    - Co-occur in same chunks
    """
    groups = []
    for e1 in entities:
        for e2 in entities:
            if e1.type == e2.type and fuzz.ratio(e1.name, e2.name) > 90:
                groups.append((e1, e2))
    return groups
```

**Pass 3: Context-Based Disambiguation**
```python
def resolve_ambiguous(entity_name):
    """
    For generic terms like "Company":
    - Check co-occurring entities in same chunks
    - Resolve to most frequent co-occurrence
    - Or mark as ambiguous and preserve
    """
    if entity_name in ["Company", "the Company"]:
        # Check chunk context
        chunks = get_chunks_for_entity(entity_name)
        companies = extract_company_names_from_chunks(chunks)
        return most_common(companies)
```

**Implementation Plan:**

1. **Canonical Name Registry** (`src/agentic_rag/entity_resolution/canonical_names.py`)
   ```python
   CANONICAL_NAMES = {
       "company": {
           "Apple Inc.": "Apple",
           "AAPL": "Apple",
           "Microsoft Corporation": "Microsoft",
           "MSFT": "Microsoft",
           # ... more mappings
       },
       "product": {
           "Form 10-Q": "10-Q Filing",
           "Quarterly Report": "10-Q Filing"
       }
   }
   ```

2. **Entity Merger Script** (`scripts/merge_duplicate_entities.py`)
   ```cypher
   // Merge two entities
   MATCH (e1:Entity {name: "Apple Inc."}), (e2:Entity {name: "Apple"})

   // Merge relationships
   MATCH (e1)-[r1:RELATED_TO]->(target)
   MERGE (e2)-[r2:RELATED_TO]->(target)
   ON CREATE SET r2 = r1
   ON MATCH SET r2.strength = r2.strength + r1.strength

   // Merge properties
   SET e2.mention_count = e1.mention_count + e2.mention_count,
       e2.chunk_refs = e1.chunk_refs + e2.chunk_refs,
       e2.relationship_count = e1.relationship_count + e2.relationship_count

   // Delete duplicate
   DETACH DELETE e1
   ```

3. **Ingestion-Time Resolution**
   - Apply canonical mapping before entity creation
   - Use `canonical_name` property for matching
   - Preserve original name in `aliases` array

**Estimated Effort:** 3-4 days

---

## Additional Enhancements

### Enhancement 1: Numeric Fact Extraction

**Problem:** Episodes contain text like "revenue was $52 million" but can't be queried numerically

**Solution:**
```python
# Episode properties
{
    "fact": "iPhone revenue was $40,665 million in Q3 2022",
    "numeric_facts": {
        "revenue": {
            "value": 40665,
            "unit": "million USD",
            "metric": "revenue",
            "entity": "iPhone"
        }
    }
}
```

**Use Case:**
```cypher
// Find all revenue facts > $50B
MATCH (ep:Episode)
WHERE ep.numeric_facts.revenue.value > 50000
RETURN ep.fact
```

**Effort:** 2 days

### Enhancement 2: Relationship Strength Scoring

**Problem:** All relationships have `strength = 0.5` (static)

**Solution:**
```python
def calculate_relationship_strength(rel):
    """
    Factors:
    - Number of supporting chunks (more chunks = stronger)
    - Co-occurrence frequency
    - Relationship type priority
    - Entity importance product
    """
    chunk_score = min(len(rel.source_chunks) / 10, 1.0) * 0.4

    type_weights = {
        "acquired": 1.0,
        "owns": 0.9,
        "partners_with": 0.8,
        "works_at": 0.6,
        "mentioned_with": 0.3
    }
    type_score = type_weights.get(rel.type, 0.5) * 0.3

    importance_product = sqrt(source.importance_score * target.importance_score) * 0.3

    return chunk_score + type_score + importance_product
```

**Effort:** 1-2 days

### Enhancement 3: Entity Type Hierarchy

**Problem:** Flat entity types, no semantic relationships

**Solution:**
```python
TYPE_HIERARCHY = {
    "organization": ["company", "department", "subsidiary"],
    "financial_instrument": ["stock", "bond", "derivative"],
    "metric": ["revenue", "profit", "expense"],
    "time_period": ["quarter", "year", "fiscal_period"]
}
```

**Use Case:**
```cypher
// Find all organization entities
MATCH (e:Entity)
WHERE e.type IN ["company", "department", "subsidiary"]
RETURN e.name
```

**Effort:** 1 day

---

## Implementation Roadmap

### Phase 1: Critical Fixes (Week 1)
**Goal:** Address blocking issues for basic QnA

- [x] **Day 1-2:** Issue 3 - Document References
  - Update ingestion pipeline
  - Backfill existing entities

- [x] **Day 3-4:** Issue 4 - Temporal Metadata
  - Enhance document parsing
  - Update episode creation

- [x] **Day 5:** Issue 2 - Importance Scoring
  - Implement scoring algorithm
  - Batch compute scores

**Deliverable:** Entities have document tracking, temporal context, and dynamic importance

### Phase 2: Graph Connectivity (Week 2)
**Goal:** Enable entity-fact queries

- [x] **Day 1-3:** Issue 1 - Episode-Entity Linking
  - Implement entity mention extraction
  - Create MENTIONS relationships
  - Batch link existing episodes

- [x] **Day 4-5:** Enhancement 1 - Numeric Facts
  - Extract numeric values from episodes
  - Structure as queryable properties

**Deliverable:** Fully connected graph with queryable facts

### Phase 3: Quality Improvements (Week 3)
**Goal:** Clean and optimize graph

- [x] **Day 1-4:** Issue 5 - Entity Deduplication
  - Build canonical name registry
  - Merge duplicate entities
  - Update ingestion pipeline

- [x] **Day 5:** Enhancement 2 - Relationship Scoring
  - Compute dynamic relationship strengths

**Deliverable:** High-quality, deduplicated graph

### Phase 4: Advanced Features (Week 4)
**Goal:** Enable sophisticated queries

- [x] **Day 1-2:** Enhancement 3 - Type Hierarchy
  - Implement hierarchical types
  - Update entity creation

- [x] **Day 3-5:** Testing & Validation
  - Test QnA queries
  - Benchmark performance
  - Documentation

**Deliverable:** Production-ready knowledge graph

---

## Success Metrics

### Before Improvements
- Episode-Entity connections: 0
- Entity deduplication: 0% (multiple versions exist)
- Temporal queries: Not possible
- Document tracking: 0 entities with document_refs
- Importance variance: 0 (all 0.5)

### After Improvements
- Episode-Entity connections: >90% episodes linked
- Entity deduplication: >95% reduction in duplicates
- Temporal queries: All 46 multi-doc temporal questions answerable
- Document tracking: 100% entities with document_refs
- Importance variance: Top 10% entities clearly distinguished

### QnA Performance Targets
- **Multi-Doc RAG queries:** <2 seconds response time
- **Temporal trend queries:** <1 second
- **Entity lookup:** <500ms
- **Cross-document entity queries:** <3 seconds

---

## Testing Strategy

### Unit Tests
```python
def test_entity_episode_linking():
    """Ensure episodes link to mentioned entities"""
    episode = create_episode("Microsoft acquired LinkedIn")
    entities = get_linked_entities(episode)
    assert "Microsoft" in entities
    assert "LinkedIn" in entities

def test_importance_scoring():
    """Validate importance calculation"""
    microsoft = get_entity("Microsoft")
    generic_company = get_entity("Company")
    assert microsoft.importance_score > generic_company.importance_score

def test_canonical_resolution():
    """Ensure duplicates are merged"""
    before = count_entities(name_like="Apple%")
    merge_duplicates()
    after = count_entities(name_like="Apple%")
    assert after < before
```

### Integration Tests
```python
def test_temporal_query():
    """Test quarter-based fact retrieval"""
    facts = query_facts(quarter="Q3", year=2023, company="Apple")
    assert len(facts) > 0
    assert all(f.fiscal_quarter == "Q3" for f in facts)

def test_multi_document_entity():
    """Test entity presence across documents"""
    entity = get_entity("Microsoft")
    docs = entity.document_refs
    assert len(docs) >= 4  # Should appear in all 4 Microsoft docs
```

### QnA Validation Tests
```python
def test_qna_dataset():
    """Run sample questions from qna_data.csv"""
    questions = load_qna_dataset()

    # Multi-doc temporal query
    q1 = "How has Apple's total net sales changed over time?"
    answer1 = query_graph(q1)
    assert "82,959 million" in answer1  # Q3 2022
    assert "117,154 million" in answer1  # Q1 2023

    # Entity relationship query
    q2 = "What companies did Intel acquire?"
    answer2 = query_graph(q2)
    assert "Mobileye" in answer2 or "Tower Semiconductor" in answer2
```

---

## Risks & Mitigation

### Risk 1: Performance Degradation
**Issue:** Adding episode-entity links could slow queries

**Mitigation:**
- Create indexes on temporal properties
- Use relationship property indexes
- Implement query result caching

```cypher
CREATE INDEX entity_name_idx FOR (e:Entity) ON (e.name);
CREATE INDEX episode_temporal_idx FOR (ep:Episode) ON (ep.fiscal_year, ep.fiscal_quarter);
CREATE INDEX entity_importance_idx FOR (e:Entity) ON (e.importance_score);
```

### Risk 2: Entity Merger Errors
**Issue:** Incorrectly merging distinct entities

**Mitigation:**
- Manual review of high-importance mergers
- Preserve merge history for rollback
- Confidence scoring for automatic mergers

### Risk 3: Temporal Parsing Failures
**Issue:** Filename parsing doesn't cover all edge cases

**Mitigation:**
- Fallback to document content parsing
- Manual validation of parsed dates
- Error logging and monitoring

---

## Maintenance Plan

### Ongoing Tasks

**Weekly:**
- Review entity deduplication candidates
- Validate importance scores for new entities
- Monitor query performance metrics

**Monthly:**
- Recompute importance scores (as corpus grows)
- Audit entity-episode links for accuracy
- Review and update canonical name registry

**Quarterly:**
- Full graph quality assessment
- Performance optimization tuning
- Schema evolution planning

---

## Documentation Updates Required

1. **Architecture Docs** (`docs/3-architecture/database-and-rag.md`)
   - Update entity schema documentation
   - Add episode-entity relationship diagrams
   - Document temporal query patterns

2. **Development Guide** (`docs/8-development/`)
   - Entity resolution guidelines
   - Temporal metadata standards
   - Graph query cookbook

3. **API Documentation**
   - New graph query endpoints
   - Temporal filter parameters
   - Entity resolution API

---

## Cost Estimation

### Development Time
- Phase 1: 5 days
- Phase 2: 5 days
- Phase 3: 5 days
- Phase 4: 5 days
- **Total: 20 days (~4 weeks)**

### Infrastructure
- No additional Neo4j resources needed (existing tier sufficient)
- Minimal PostgreSQL impact (some metadata columns)
- One-time batch processing compute: ~4 hours

### Ongoing Costs
- Recompute importance scores: ~30 minutes/month
- Entity deduplication review: ~2 hours/month
- Monitoring and maintenance: ~4 hours/month

---

## Conclusion

These improvements will transform the knowledge graph from a disconnected entity index into a fully queryable temporal knowledge base capable of answering complex multi-document questions. The phased approach ensures incremental value delivery while maintaining system stability.

**Priority Order:**
1. Document references (unlocks cross-doc queries)
2. Temporal metadata (enables trend analysis)
3. Episode-entity linking (connects facts to entities)
4. Entity deduplication (improves quality)
5. Importance scoring (optimizes search)

By completing Phase 1-2 (2 weeks), the system will support 80% of QnA dataset requirements. Full implementation (4 weeks) will enable 95%+ coverage with high-quality responses.
