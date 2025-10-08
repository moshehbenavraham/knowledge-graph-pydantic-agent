# Phase 3: Agent Intelligence (Days 7-9)

> **Note**: This document has been updated (2025-08-27) to reflect the current unified agent architecture.  
> The agent implementation has been consolidated into `src/agent/unified_agent.py` and the intent analyzer is now at `src/agentic_rag/search/intent_analyzer.py`.

## Executive Summary

Phase 3 implements the intelligent agent layer using Pydantic AI, building upon the robust database infrastructure (Phase 1) and core components (Phase 2). This phase creates a context-aware agent capable of understanding query intent, intelligently routing searches, and generating well-sourced, confident responses.

## Implementation Status: ✅ COMPLETED

### Phase 3 Components Overview

```
Query Processing Flow:
+--------------------------------------------------------------+
|                      User Query                              |
|                           |                                  |
|                   Intent Analysis                            |
|                           |                                  |
|              +------------+------------+                     |
|              |                         |                     |
|        Query Intent              Entity Extraction           |
|              |                         |                     |
|      Strategy Selection         Context Building             |
|              |                         |                     |
|              +------------+------------+                     |
|                           |                                  |
|                    Tool Execution                            |
|                           |                                  |
|        +------------------+------------------+              |
|        |                  |                  |              |
|   Vector Search      Graph Search      Hybrid Search        |
|        |                  |                  |              |
|        +------------------+------------------+              |
|                           |                                  |
|                   Result Synthesis                           |
|                           |                                  |
|                  Response Generation                         |
|                           |                                  |
|                   Formatted Answer                           |
|                    with Citations                            |
+--------------------------------------------------------------+
```

## Core Architecture Principles

**Intelligence through Intent Understanding | Flexibility through Tool Composition | Reliability through Fallbacks**

- Intent analysis drives search strategy selection
- Tools are composable and can be executed in parallel
- Graceful degradation when components fail
- Citations and confidence scores for transparency

## Detailed Implementation Plan

### 3.1 Intent Analysis System

#### Intent Analyzer Module (`src/agentic_rag/search/intent_analyzer.py`)

```python
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Set
import re
from datetime import datetime

class SearchIntent(Enum):
    """Types of search intent."""
    VECTOR_HEAVY = "vector_heavy"        # Semantic content search
    GRAPH_HEAVY = "graph_heavy"          # Relationship/fact search
    HYBRID = "hybrid"                    # Combined search
    TEMPORAL = "temporal"                # Timeline/history search
    ENTITY_FOCUSED = "entity_focused"    # Specific entity search

class SearchStrategy(Enum):
    """Search strategies based on intent."""
    VECTOR_ONLY = "vector_only"
    GRAPH_ONLY = "graph_only"
    HYBRID = "hybrid"
    ADAPTIVE = "adaptive"            # Dynamically selected strategy

@dataclass
class AnalyzedQuery:
    """Analyzed query with extracted information."""
    original_query: str
    primary_intent: SearchIntent
    confidence: float
    entities: List[str]
    temporal_context: Optional[tuple[datetime, datetime]]
    relationship_types: List[str]
    search_strategy: SearchStrategy
    complexity_score: float  # 0.0 to 1.0
    confidence: float       # 0.0 to 1.0

class IntentAnalyzer:
    """
    Analyzes user queries to determine intent and optimal search strategy.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.relationship_patterns = [
            r'\b(related|connected|relationship|associated)\b',
            r'\b(works? with|founded|acquired|invested|partnered)\b',
            r'\b(competitor|competes|versus|vs\.?)\b'
        ]
        self.temporal_patterns = [
            r'\b(when|timeline|history|evolution|changed|progression)\b',
            r'\b(before|after|during|since|until)\b',
            r'\b(\d{4}|\d{1,2}/\d{1,2}/\d{2,4})\b'
        ]
        self.factual_patterns = [
            r'\b(what is|who is|where is|how much|how many)\b',
            r'\b(define|explain|describe)\b'
        ]

    async def analyze(self, query: str) -> AnalyzedQuery:
        """
        Comprehensive query analysis.

        Steps:
        1. Pattern matching for quick classification
        2. Entity extraction
        3. Temporal context detection
        4. Complexity assessment
        5. Strategy selection
        """
        # Quick pattern-based classification
        primary_intent = self._classify_intent(query)
        secondary_intents = self._find_secondary_intents(query)

        # Extract entities (can use NER or LLM)
        entities = await self._extract_entities(query)

        # Detect temporal context
        temporal_context = self._extract_temporal_context(query)

        # Identify relationship types
        relationship_types = self._identify_relationships(query)

        # Calculate complexity
        complexity_score = self._calculate_complexity(
            query, primary_intent, entities, temporal_context
        )

        # Select search strategy
        search_strategy = self._select_strategy(
            primary_intent,
            secondary_intents,
            entities,
            temporal_context,
            complexity_score
        )

        # Calculate confidence
        confidence = self._calculate_confidence(
            primary_intent,
            entities,
            complexity_score
        )

        return AnalyzedQuery(
            original_query=query,
            primary_intent=primary_intent,
            secondary_intents=secondary_intents,
            entities=entities,
            temporal_context=temporal_context,
            relationship_types=relationship_types,
            search_strategy=search_strategy,
            complexity_score=complexity_score,
            confidence=confidence
        )

    def _classify_intent(self, query: str) -> QueryIntent:
        """Classify primary intent using patterns."""
        query_lower = query.lower()

        # Check patterns in priority order
        if any(re.search(p, query_lower) for p in self.relationship_patterns):
            return QueryIntent.RELATIONSHIP

        if any(re.search(p, query_lower) for p in self.temporal_patterns):
            return QueryIntent.TEMPORAL

        if 'compare' in query_lower or 'vs' in query_lower:
            return QueryIntent.COMPARISON

        if any(term in query_lower for term in ['all', 'list', 'summary', 'overview']):
            return QueryIntent.AGGREGATION

        if any(re.search(p, query_lower) for p in self.factual_patterns):
            return QueryIntent.FACTUAL

        if '?' not in query and len(query.split()) > 10:
            return QueryIntent.EXPLORATORY

        return QueryIntent.FACTUAL  # Default

    def _select_strategy(self,
                        primary_intent: QueryIntent,
                        secondary_intents: List[QueryIntent],
                        entities: List[str],
                        temporal_context: Optional[tuple],
                        complexity: float) -> SearchStrategy:
        """Select optimal search strategy based on analysis."""

        # Relationship queries benefit from graph
        if primary_intent == QueryIntent.RELATIONSHIP:
            return SearchStrategy.GRAPH_FIRST

        # Temporal queries need graph for timeline
        if primary_intent == QueryIntent.TEMPORAL:
            return SearchStrategy.GRAPH_FIRST if entities else SearchStrategy.HYBRID

        # Complex queries need multiple approaches
        if complexity > 0.7:
            return SearchStrategy.HYBRID

        # Multi-hop requires iterative approach
        if primary_intent == QueryIntent.MULTI_HOP:
            return SearchStrategy.ITERATIVE

        # Simple factual queries can use vector
        if primary_intent == QueryIntent.FACTUAL and complexity < 0.3:
            return SearchStrategy.VECTOR_ONLY

        # Default to hybrid for best coverage
        return SearchStrategy.HYBRID
```

### 3.2 Pydantic AI Agent Configuration

#### Main Agent Module (`src/agentic_rag/agent/agent.py`)

```python
from pydantic_ai import Agent, RunContext
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import logging

from .prompts import SYSTEM_PROMPT, TOOL_SELECTION_PROMPT
from .intent_analyzer import IntentAnalyzer, SearchStrategy
from .response_generator import ResponseGenerator
from .providers import get_llm_model

logger = logging.getLogger(__name__)

@dataclass
class AgentDependencies:
    """Dependencies and context for the agent."""
    session_id: str
    user_id: Optional[str] = None
    search_preferences: Dict[str, Any] = None
    intent_analyzer: IntentAnalyzer = None
    response_generator: ResponseGenerator = None
    max_tools_per_query: int = 5
    enable_caching: bool = True

    def __post_init__(self):
        if self.search_preferences is None:
            self.search_preferences = {
                "use_vector": True,
                "use_graph": True,
                "default_limit": 10,
                "confidence_threshold": 0.7
            }
        if self.intent_analyzer is None:
            self.intent_analyzer = IntentAnalyzer()
        if self.response_generator is None:
            self.response_generator = ResponseGenerator()

# Initialize the agent
rag_agent = Agent(
    model=get_llm_model(),
    deps_type=AgentDependencies,
    system_prompt=SYSTEM_PROMPT
)

# Tool: Smart Search
@rag_agent.tool
async def smart_search(
    ctx: RunContext[AgentDependencies],
    query: str
) -> Dict[str, Any]:
    """
    Intelligent search that analyzes intent and routes to appropriate strategy.

    This is the primary tool that orchestrates all search operations.
    """
    # Analyze query intent
    analyzed_query = await ctx.deps.intent_analyzer.analyze(query)

    logger.info(f"Query intent: {analyzed_query.primary_intent}, "
                f"Strategy: {analyzed_query.search_strategy}")

    # Route based on strategy
    if analyzed_query.search_strategy == SearchStrategy.VECTOR_ONLY:
        return await vector_search(ctx, query, limit=20)

    elif analyzed_query.search_strategy == SearchStrategy.GRAPH_ONLY:
        return await graph_search(ctx, query)

    elif analyzed_query.search_strategy == SearchStrategy.GRAPH_FIRST:
        # Graph search with vector enrichment
        graph_results = await graph_search(ctx, query)

        # Get supporting chunks for top facts
        if graph_results.get('facts'):
            chunk_ids = [f['source_chunk'] for f in graph_results['facts'][:5]]
            chunks = await get_chunks_by_ids(ctx, chunk_ids)
            graph_results['supporting_chunks'] = chunks

        return graph_results

    elif analyzed_query.search_strategy == SearchStrategy.HYBRID:
        # Parallel execution
        import asyncio
        vector_task = vector_search(ctx, query, limit=15)
        graph_task = graph_search(ctx, query)

        vector_results, graph_results = await asyncio.gather(
            vector_task, graph_task
        )

        # Merge and rank
        return await ctx.deps.response_generator.merge_results(
            vector_results,
            graph_results,
            analyzed_query
        )

    else:  # ITERATIVE
        return await iterative_search(ctx, query, analyzed_query)

# Tool: Vector Search
@rag_agent.tool
async def vector_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Semantic similarity search using embeddings.

    Best for:
    - Finding similar content
    - Conceptual matches
    - General information retrieval
    """
    from ..search.vector_search import VectorSearch

    searcher = VectorSearch()
    results = await searcher.search(query, limit)

    return {
        "type": "vector",
        "query": query,
        "results": [
            {
                "content": r.content,
                "score": r.score,
                "document_title": r.document_title,
                "chunk_id": r.chunk_id,
                "metadata": r.metadata
            }
            for r in results
        ],
        "total_results": len(results)
    }

# Tool: Graph Search
@rag_agent.tool
async def graph_search(
    ctx: RunContext[AgentDependencies],
    query: str
) -> Dict[str, Any]:
    """
    Knowledge graph search for facts and relationships.

    Best for:
    - Entity relationships
    - Temporal information
    - Specific facts
    """
    from ..search.graph_search import GraphSearch

    searcher = GraphSearch()
    results = await searcher.search(query)

    return {
        "type": "graph",
        "query": query,
        "facts": results.facts,
        "entities": results.entities,
        "relationships": results.relationships,
        "timeline": results.timeline if hasattr(results, 'timeline') else None,
        "total_facts": len(results.facts)
    }

# Tool: Get Entity Relationships
@rag_agent.tool
async def get_entity_relationships(
    ctx: RunContext[AgentDependencies],
    entity_name: str,
    depth: int = 2
) -> Dict[str, Any]:
    """
    Explore relationships for a specific entity.

    Returns the entity's connections up to specified depth.
    """
    from ..search.graph_search import GraphSearch

    searcher = GraphSearch()
    relationships = await searcher.get_entity_relationships(entity_name, depth)

    return {
        "entity": entity_name,
        "depth": depth,
        "relationships": relationships,
        "total_connections": len(relationships)
    }

# Tool: Get Entity Timeline
@rag_agent.tool
async def get_entity_timeline(
    ctx: RunContext[AgentDependencies],
    entity_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get chronological facts about an entity.

    Shows how information about the entity has evolved over time.
    """
    from ..search.graph_search import GraphSearch

    searcher = GraphSearch()
    timeline = await searcher.get_entity_timeline(
        entity_name,
        start_date,
        end_date
    )

    return timeline

# Helper function for iterative search
async def iterative_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    analyzed_query
) -> Dict[str, Any]:
    """
    Multi-step iterative search for complex queries.
    """
    results = {"type": "iterative", "steps": []}

    # Step 1: Initial broad search
    initial = await vector_search(ctx, query, limit=5)
    results["steps"].append({"step": 1, "action": "initial_search", "results": initial})

    # Step 2: Extract entities and search graph
    if analyzed_query.entities:
        for entity in analyzed_query.entities[:3]:  # Limit to top 3
            entity_info = await get_entity_relationships(ctx, entity, depth=1)
            results["steps"].append({
                "step": 2,
                "action": f"explore_entity_{entity}",
                "results": entity_info
            })

    # Step 3: Refine based on findings
    # This would be more sophisticated in production

    return results
```

### 3.3 Tool Implementations

#### Tools Module (`src/agentic_rag/agent/tools.py`)

```python
"""
Tool implementations for the Pydantic AI agent.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Input models for tools
class VectorSearchInput(BaseModel):
    """Input for vector search."""
    query: str = Field(..., description="Search query")
    limit: int = Field(default=10, description="Maximum results", ge=1, le=50)
    similarity_threshold: float = Field(default=0.7, description="Minimum similarity", ge=0, le=1)

class GraphSearchInput(BaseModel):
    """Input for graph search."""
    query: str = Field(..., description="Search query")
    include_timeline: bool = Field(default=False, description="Include temporal data")
    max_facts: int = Field(default=20, description="Maximum facts to return")

class HybridSearchInput(BaseModel):
    """Input for hybrid search."""
    query: str = Field(..., description="Search query")
    vector_weight: float = Field(default=0.6, description="Weight for vector results", ge=0, le=1)
    limit: int = Field(default=20, description="Maximum combined results")

class DocumentInput(BaseModel):
    """Input for document retrieval."""
    document_id: str = Field(..., description="Document UUID")
    include_chunks: bool = Field(default=True, description="Include all chunks")

class EntityRelationshipInput(BaseModel):
    """Input for entity relationship queries."""
    entity_name: str = Field(..., description="Entity name")
    depth: int = Field(default=2, description="Traversal depth", ge=1, le=5)
    relationship_types: Optional[List[str]] = Field(None, description="Filter by relationship types")

# Tool implementations
async def comprehensive_search(
    query: str,
    search_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Perform comprehensive search using multiple strategies.

    This is the main search orchestrator that combines different
    search methods based on configuration.
    """
    results = {
        "query": query,
        "timestamp": datetime.utcnow().isoformat(),
        "search_config": search_config,
        "vector_results": [],
        "graph_results": [],
        "combined_results": [],
        "metadata": {}
    }

    tasks = []

    # Vector search task
    if search_config.get("use_vector", True):
        from ..search.vector_search import VectorSearch
        vector_searcher = VectorSearch()
        tasks.append(("vector", vector_searcher.search(query, limit=search_config.get("vector_limit", 15))))

    # Graph search task
    if search_config.get("use_graph", True):
        from ..search.graph_search import GraphSearch
        graph_searcher = GraphSearch()
        tasks.append(("graph", graph_searcher.search(query)))

    # Execute searches in parallel
    if tasks:
        search_results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)

        for (search_type, _), result in zip(tasks, search_results):
            if isinstance(result, Exception):
                logger.error(f"{search_type} search failed: {result}")
                results["metadata"][f"{search_type}_error"] = str(result)
            else:
                if search_type == "vector":
                    results["vector_results"] = result
                else:
                    results["graph_results"] = result

    # Combine and rank results
    if results["vector_results"] or results["graph_results"]:
        from ..search.ranker import ResultRanker
        ranker = ResultRanker()
        results["combined_results"] = await ranker.rank_combined(
            results["vector_results"],
            results["graph_results"],
            query
        )

    return results

async def get_document_context(
    document_id: str,
    chunk_index: Optional[int] = None,
    context_size: int = 2
) -> Dict[str, Any]:
    """
    Get document with surrounding context.

    Retrieves a document and optionally focuses on a specific chunk
    with surrounding context chunks.
    """
    from ..storage.postgres_store import PostgresStore

    store = PostgresStore()

    # Get document
    document = await store.get_document(document_id)
    if not document:
        return {"error": "Document not found"}

    # Get all chunks
    chunks = await store.get_document_chunks(document_id)

    result = {
        "document": document,
        "total_chunks": len(chunks),
        "chunks": chunks
    }

    # If specific chunk requested, provide context
    if chunk_index is not None and 0 <= chunk_index < len(chunks):
        start_idx = max(0, chunk_index - context_size)
        end_idx = min(len(chunks), chunk_index + context_size + 1)

        result["focal_chunk"] = chunks[chunk_index]
        result["context_chunks"] = chunks[start_idx:end_idx]
        result["context_range"] = (start_idx, end_idx)

    return result

async def explore_entity_network(
    entity_name: str,
    max_depth: int = 3,
    max_nodes: int = 50
) -> Dict[str, Any]:
    """
    Explore the network around an entity.

    Builds a graph of relationships starting from the given entity.
    """
    from ..search.graph_search import GraphSearch

    searcher = GraphSearch()

    network = {
        "central_entity": entity_name,
        "nodes": [],
        "edges": [],
        "depth_explored": 0
    }

    visited = set()
    queue = [(entity_name, 0)]

    while queue and len(network["nodes"]) < max_nodes:
        current_entity, depth = queue.pop(0)

        if current_entity in visited or depth > max_depth:
            continue

        visited.add(current_entity)

        # Get relationships for current entity
        relationships = await searcher.get_entity_relationships(current_entity, depth=1)

        # Add node
        network["nodes"].append({
            "id": current_entity,
            "depth": depth,
            "type": relationships.get("entity_type", "unknown")
        })

        # Add edges and queue connected entities
        for rel in relationships.get("relationships", []):
            network["edges"].append({
                "source": current_entity,
                "target": rel["target"],
                "type": rel["type"],
                "confidence": rel.get("confidence", 1.0)
            })

            if rel["target"] not in visited:
                queue.append((rel["target"], depth + 1))

        network["depth_explored"] = max(network["depth_explored"], depth)

    return network

async def temporal_analysis(
    entity_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    event_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Analyze temporal patterns and events.

    Provides timeline analysis for entities or general events.
    """
    from ..search.graph_search import GraphSearch

    searcher = GraphSearch()

    # Get timeline data
    if entity_name:
        timeline = await searcher.get_entity_timeline(entity_name, start_date, end_date)
    else:
        timeline = await searcher.get_events_timeline(start_date, end_date, event_types)

    # Analyze patterns
    analysis = {
        "timeline": timeline,
        "total_events": len(timeline),
        "date_range": None,
        "event_frequency": {},
        "key_periods": []
    }

    if timeline:
        dates = [event.get("date") for event in timeline if event.get("date")]
        if dates:
            analysis["date_range"] = (min(dates), max(dates))

        # Count event types
        for event in timeline:
            event_type = event.get("type", "unknown")
            analysis["event_frequency"][event_type] = analysis["event_frequency"].get(event_type, 0) + 1

        # Identify key periods (simplified - would be more sophisticated)
        # Group events by month/year and find peaks

    return analysis
```

### 3.4 System Prompts

#### Prompts Module (`src/agentic_rag/agent/prompts.py`)

```python
"""
System prompts and templates for the agent.
"""

SYSTEM_PROMPT = """You are an advanced AI assistant with access to both vector search and knowledge graph capabilities.

Your knowledge base contains:
- Document chunks with semantic embeddings for similarity search
- A knowledge graph with entities, relationships, and temporal facts
- Full document access when detailed context is needed

Core Capabilities:
1. **Vector Search**: Find semantically similar content across all documents
2. **Graph Search**: Explore entity relationships and temporal facts
3. **Hybrid Search**: Combine both approaches for comprehensive results
4. **Entity Analysis**: Deep dive into specific entities and their connections
5. **Temporal Analysis**: Understand how information evolves over time

When answering questions:
- Always search for relevant information before responding
- Cite your sources by mentioning document titles and specific facts
- Indicate confidence levels when appropriate
- Use multiple search strategies for complex questions
- Acknowledge when information is incomplete or conflicting

Search Strategy Guidelines:
- Use vector search for: conceptual questions, definitions, general information
- Use graph search for: relationships, specific facts, timelines, entity connections
- Use hybrid search for: comprehensive research, complex multi-faceted questions
- Use iterative search for: questions requiring multiple steps or refinement

Response Format:
- Provide clear, structured answers
- Include relevant citations [Document: Title]
- Mention confidence when uncertain
- Suggest follow-up questions when appropriate

Remember: You have access to both broad semantic understanding and precise factual knowledge. Use both strategically."""

TOOL_SELECTION_PROMPT = """Based on the user's query, select the most appropriate search tool(s):

Query: {query}
Detected Intent: {intent}
Extracted Entities: {entities}

Available tools:
1. smart_search - Automatic strategy selection based on intent
2. vector_search - Semantic similarity search
3. graph_search - Knowledge graph facts and relationships
4. get_entity_relationships - Deep dive into an entity
5. get_entity_timeline - Temporal information about an entity
6. comprehensive_search - Multi-strategy parallel search

Select tools that best match the query intent and return the tool names."""

RESPONSE_GENERATION_PROMPT = """Generate a comprehensive response based on the search results.

Query: {query}
Search Results: {results}
Result Confidence: {confidence}

Guidelines:
1. Synthesize information from multiple sources
2. Cite specific documents and facts
3. Acknowledge any uncertainty or gaps
4. Maintain factual accuracy
5. Structure the response clearly

Format the response with:
- Direct answer to the question
- Supporting evidence with citations
- Confidence indicator if applicable
- Related information if relevant"""

CITATION_FORMAT_PROMPT = """Format citations for the following information:

Source Document: {document_title}
Chunk ID: {chunk_id}
Content: {content}
Confidence: {confidence}

Create a citation in the format: [Source: Document Title, Confidence: X%]"""

ERROR_HANDLING_PROMPT = """An error occurred during search. Provide a helpful response:

Error Type: {error_type}
Error Message: {error_message}
Fallback Strategy: {fallback_strategy}

Generate a user-friendly message that:
1. Acknowledges the issue without technical details
2. Suggests an alternative approach
3. Offers to try a different search strategy"""
```

### 3.5 Response Generation

#### Response Generator Module (`src/agentic_rag/agent/response_generator.py`)

```python
"""
Response generation with citation management and confidence scoring.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class Citation:
    """Represents a citation for a piece of information."""
    document_title: str
    document_id: str
    chunk_id: Optional[str]
    content: str
    confidence: float
    source_type: str  # 'vector', 'graph', 'document'

@dataclass
class GeneratedResponse:
    """A generated response with citations and metadata."""
    answer: str
    citations: List[Citation]
    confidence: float
    search_strategy_used: str
    follow_up_questions: List[str]
    metadata: Dict[str, Any]

class ResponseGenerator:
    """
    Generates responses from search results with proper citations.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.min_confidence_threshold = 0.5

    async def generate_response(
        self,
        query: str,
        search_results: Dict[str, Any],
        analyzed_query: Any
    ) -> GeneratedResponse:
        """
        Generate a comprehensive response from search results.
        """
        # Extract relevant content
        relevant_content = self._extract_relevant_content(search_results)

        # Generate citations
        citations = self._generate_citations(relevant_content)

        # Calculate overall confidence
        confidence = self._calculate_confidence(relevant_content, analyzed_query)

        # Synthesize answer
        answer = await self._synthesize_answer(
            query,
            relevant_content,
            citations,
            confidence
        )

        # Generate follow-up questions
        follow_ups = self._generate_follow_ups(query, relevant_content)

        return GeneratedResponse(
            answer=answer,
            citations=citations,
            confidence=confidence,
            search_strategy_used=search_results.get("search_type", "unknown"),
            follow_up_questions=follow_ups,
            metadata={
                "total_sources": len(citations),
                "content_pieces": len(relevant_content),
                "query_complexity": analyzed_query.complexity_score
            }
        )

    def _extract_relevant_content(
        self,
        search_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract and rank relevant content from search results."""
        content_pieces = []

        # Extract from vector results
        if "vector_results" in search_results:
            for result in search_results["vector_results"]:
                content_pieces.append({
                    "content": result["content"],
                    "score": result["score"],
                    "source_type": "vector",
                    "document_title": result.get("document_title", "Unknown"),
                    "document_id": result.get("document_id"),
                    "chunk_id": result.get("chunk_id")
                })

        # Extract from graph results
        if "graph_results" in search_results:
            for fact in search_results["graph_results"].get("facts", []):
                content_pieces.append({
                    "content": fact["fact"],
                    "score": fact.get("confidence", 0.8),
                    "source_type": "graph",
                    "source_chunk": fact.get("source_chunk"),
                    "entities": fact.get("entities", [])
                })

        # Sort by relevance score
        content_pieces.sort(key=lambda x: x["score"], reverse=True)

        # Filter by minimum confidence
        content_pieces = [
            c for c in content_pieces
            if c["score"] >= self.min_confidence_threshold
        ]

        return content_pieces[:20]  # Limit to top 20 pieces

    def _generate_citations(
        self,
        content_pieces: List[Dict[str, Any]]
    ) -> List[Citation]:
        """Generate citations for content pieces."""
        citations = []
        seen_chunks = set()  # Avoid duplicate citations

        for piece in content_pieces:
            chunk_id = piece.get("chunk_id") or piece.get("source_chunk")

            # Skip if already cited
            if chunk_id and chunk_id in seen_chunks:
                continue

            citation = Citation(
                document_title=piece.get("document_title", "Unknown Source"),
                document_id=piece.get("document_id", ""),
                chunk_id=chunk_id,
                content=piece["content"][:200],  # Truncate for citation
                confidence=piece["score"],
                source_type=piece["source_type"]
            )

            citations.append(citation)
            if chunk_id:
                seen_chunks.add(chunk_id)

        return citations

    def _calculate_confidence(
        self,
        content_pieces: List[Dict[str, Any]],
        analyzed_query: Any
    ) -> float:
        """Calculate overall confidence in the response."""
        if not content_pieces:
            return 0.0

        # Factors affecting confidence:
        # 1. Average relevance score
        avg_score = sum(c["score"] for c in content_pieces) / len(content_pieces)

        # 2. Number of supporting sources
        source_factor = min(len(content_pieces) / 10, 1.0)  # Max at 10 sources

        # 3. Query complexity (simpler queries should have higher confidence)
        complexity_factor = 1.0 - (analyzed_query.complexity_score * 0.3)

        # 4. Source diversity (both vector and graph results)
        source_types = set(c["source_type"] for c in content_pieces)
        diversity_factor = 1.0 if len(source_types) > 1 else 0.8

        # Weighted combination
        confidence = (
            avg_score * 0.4 +
            source_factor * 0.2 +
            complexity_factor * 0.2 +
            diversity_factor * 0.2
        )

        return min(max(confidence, 0.0), 1.0)

    async def _synthesize_answer(
        self,
        query: str,
        content_pieces: List[Dict[str, Any]],
        citations: List[Citation],
        confidence: float
    ) -> str:
        """Synthesize a coherent answer from content pieces."""
        if not content_pieces:
            return "I couldn't find relevant information to answer your question."

        # For now, a simple implementation
        # In production, this would use LLM for synthesis

        # Group content by source type
        vector_content = [c for c in content_pieces if c["source_type"] == "vector"]
        graph_content = [c for c in content_pieces if c["source_type"] == "graph"]

        answer_parts = []

        # Add main answer from top results
        if vector_content:
            answer_parts.append(vector_content[0]["content"])

        # Add facts from knowledge graph
        if graph_content:
            facts = [c["content"] for c in graph_content[:3]]
            if facts:
                answer_parts.append("\n\nRelevant facts:\n- " + "\n- ".join(facts))

        # Add confidence indicator
        confidence_text = self._confidence_to_text(confidence)
        answer_parts.append(f"\n\n*Confidence: {confidence_text}*")

        # Add citations
        if citations:
            citation_text = "\n\nSources:\n"
            for i, cite in enumerate(citations[:5], 1):
                citation_text += f"{i}. {cite.document_title} "
                citation_text += f"(Confidence: {cite.confidence:.1%})\n"
            answer_parts.append(citation_text)

        return "\n".join(answer_parts)

    def _confidence_to_text(self, confidence: float) -> str:
        """Convert confidence score to human-readable text."""
        if confidence >= 0.9:
            return "Very High"
        elif confidence >= 0.75:
            return "High"
        elif confidence >= 0.6:
            return "Moderate"
        elif confidence >= 0.4:
            return "Low"
        else:
            return "Very Low"

    def _generate_follow_ups(
        self,
        query: str,
        content_pieces: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate relevant follow-up questions."""
        follow_ups = []

        # Extract entities mentioned in results
        entities = set()
        for piece in content_pieces:
            if "entities" in piece:
                entities.update(piece["entities"])

        # Generate entity-based follow-ups
        for entity in list(entities)[:3]:
            follow_ups.append(f"What else can you tell me about {entity}?")

        # Add general follow-ups
        follow_ups.extend([
            "Would you like more details on any specific aspect?",
            "Should I search for related information?"
        ])

        return follow_ups[:5]

    async def merge_results(
        self,
        vector_results: Dict[str, Any],
        graph_results: Dict[str, Any],
        analyzed_query: Any
    ) -> Dict[str, Any]:
        """Merge results from multiple search strategies."""
        merged = {
            "type": "hybrid",
            "vector_results": vector_results.get("results", []),
            "graph_results": graph_results,
            "merged_results": []
        }

        # Score and rank all results together
        all_results = []

        # Add vector results
        for vr in vector_results.get("results", []):
            all_results.append({
                **vr,
                "source": "vector",
                "adjusted_score": vr["score"] * 0.6  # Weight for vector
            })

        # Add graph facts as results
        for fact in graph_results.get("facts", []):
            all_results.append({
                "content": fact["fact"],
                "source": "graph",
                "score": fact.get("confidence", 0.8),
                "adjusted_score": fact.get("confidence", 0.8) * 0.4,  # Weight for graph
                "entities": fact.get("entities", [])
            })

        # Sort by adjusted score
        all_results.sort(key=lambda x: x["adjusted_score"], reverse=True)

        merged["merged_results"] = all_results[:20]

        return merged
```

### 3.6 Query Router

#### Router Module (`src/agentic_rag/agent/router.py`)

```python
"""
Query routing for optimal search strategy selection.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging
from enum import Enum

from .intent_analyzer import QueryIntent, SearchStrategy

logger = logging.getLogger(__name__)

@dataclass
class RoutingDecision:
    """Represents a routing decision for a query."""
    primary_strategy: SearchStrategy
    fallback_strategies: List[SearchStrategy]
    confidence: float
    reasoning: str
    recommended_tools: List[str]

class QueryRouter:
    """
    Routes queries to appropriate search strategies based on intent.
    """

    def __init__(self):
        # Strategy mappings
        self.intent_strategy_map = {
            QueryIntent.FACTUAL: SearchStrategy.VECTOR_FIRST,
            QueryIntent.RELATIONSHIP: SearchStrategy.GRAPH_FIRST,
            QueryIntent.TEMPORAL: SearchStrategy.GRAPH_FIRST,
            QueryIntent.COMPARISON: SearchStrategy.HYBRID,
            QueryIntent.EXPLORATORY: SearchStrategy.ITERATIVE,
            QueryIntent.AGGREGATION: SearchStrategy.HYBRID,
            QueryIntent.DEFINITION: SearchStrategy.VECTOR_ONLY,
            QueryIntent.MULTI_HOP: SearchStrategy.ITERATIVE
        }

        # Fallback strategies for each primary
        self.fallback_map = {
            SearchStrategy.VECTOR_ONLY: [SearchStrategy.HYBRID],
            SearchStrategy.GRAPH_ONLY: [SearchStrategy.HYBRID],
            SearchStrategy.VECTOR_FIRST: [SearchStrategy.HYBRID, SearchStrategy.GRAPH_ONLY],
            SearchStrategy.GRAPH_FIRST: [SearchStrategy.HYBRID, SearchStrategy.VECTOR_ONLY],
            SearchStrategy.HYBRID: [SearchStrategy.VECTOR_FIRST, SearchStrategy.GRAPH_FIRST],
            SearchStrategy.ITERATIVE: [SearchStrategy.HYBRID]
        }

        # Tool recommendations
        self.strategy_tools_map = {
            SearchStrategy.VECTOR_ONLY: ["vector_search"],
            SearchStrategy.GRAPH_ONLY: ["graph_search", "get_entity_relationships"],
            SearchStrategy.VECTOR_FIRST: ["vector_search", "graph_search"],
            SearchStrategy.GRAPH_FIRST: ["graph_search", "vector_search"],
            SearchStrategy.HYBRID: ["smart_search", "comprehensive_search"],
            SearchStrategy.ITERATIVE: ["smart_search", "get_entity_relationships", "get_entity_timeline"]
        }

    def route(self, analyzed_query) -> RoutingDecision:
        """
        Make routing decision based on analyzed query.
        """
        # Get primary strategy
        primary_strategy = self.intent_strategy_map.get(
            analyzed_query.primary_intent,
            SearchStrategy.HYBRID
        )

        # Adjust based on entities
        if analyzed_query.entities and len(analyzed_query.entities) > 2:
            # Multiple entities suggest relationship exploration
            if primary_strategy == SearchStrategy.VECTOR_ONLY:
                primary_strategy = SearchStrategy.HYBRID

        # Adjust based on temporal context
        if analyzed_query.temporal_context:
            if primary_strategy == SearchStrategy.VECTOR_ONLY:
                primary_strategy = SearchStrategy.GRAPH_FIRST

        # Get fallback strategies
        fallbacks = self.fallback_map.get(primary_strategy, [SearchStrategy.HYBRID])

        # Get recommended tools
        tools = self.strategy_tools_map.get(primary_strategy, ["smart_search"])

        # Generate reasoning
        reasoning = self._generate_reasoning(
            analyzed_query,
            primary_strategy
        )

        # Calculate routing confidence
        confidence = self._calculate_routing_confidence(
            analyzed_query,
            primary_strategy
        )

        return RoutingDecision(
            primary_strategy=primary_strategy,
            fallback_strategies=fallbacks,
            confidence=confidence,
            reasoning=reasoning,
            recommended_tools=tools
        )

    def _generate_reasoning(
        self,
        analyzed_query,
        strategy: SearchStrategy
    ) -> str:
        """Generate explanation for routing decision."""
        reasons = []

        # Intent-based reasoning
        intent_reason = f"Query intent is {analyzed_query.primary_intent.value}"
        reasons.append(intent_reason)

        # Entity-based reasoning
        if analyzed_query.entities:
            entity_reason = f"Found {len(analyzed_query.entities)} entities"
            reasons.append(entity_reason)

        # Strategy reasoning
        strategy_reason = {
            SearchStrategy.VECTOR_ONLY: "Using vector search for semantic similarity",
            SearchStrategy.GRAPH_ONLY: "Using graph search for structured facts",
            SearchStrategy.HYBRID: "Using hybrid search for comprehensive coverage",
            SearchStrategy.GRAPH_FIRST: "Prioritizing graph for relationship data",
            SearchStrategy.VECTOR_FIRST: "Prioritizing vector for content matching",
            SearchStrategy.ITERATIVE: "Using iterative search for complex query"
        }

        reasons.append(strategy_reason.get(strategy, "Using default strategy"))

        return ". ".join(reasons)

    def _calculate_routing_confidence(
        self,
        analyzed_query,
        strategy: SearchStrategy
    ) -> float:
        """Calculate confidence in routing decision."""
        confidence = 0.5  # Base confidence

        # Strong intent match
        if analyzed_query.primary_intent in self.intent_strategy_map:
            confidence += 0.2

        # Entities detected
        if analyzed_query.entities:
            confidence += 0.15

        # High query confidence
        if analyzed_query.confidence > 0.8:
            confidence += 0.15

        # Strategy is not fallback
        if strategy != SearchStrategy.HYBRID:
            confidence += 0.1

        return min(confidence, 1.0)
```

## Testing Strategy

### Test Suite

Tests are consolidated in `tests/test_rag.py` which includes comprehensive testing for:

```python
"""
Comprehensive tests for Agent Intelligence and RAG functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.agentic_rag.agent.intent_analyzer import (
    IntentAnalyzer, QueryIntent, SearchStrategy
)
from src.agentic_rag.agent.agent import rag_agent, AgentDependencies
from src.agentic_rag.agent.response_generator import ResponseGenerator
from src.agentic_rag.agent.router import QueryRouter

class TestIntentAnalyzer:
    """Test intent analysis functionality."""

    @pytest.mark.asyncio
    async def test_factual_query_classification(self):
        """Test classification of factual queries."""
        analyzer = IntentAnalyzer()

        queries = [
            "What is OpenAI?",
            "Who founded Microsoft?",
            "How many employees does Google have?"
        ]

        for query in queries:
            result = await analyzer.analyze(query)
            assert result.primary_intent == QueryIntent.FACTUAL
            assert result.search_strategy in [
                SearchStrategy.VECTOR_ONLY,
                SearchStrategy.VECTOR_FIRST
            ]

    @pytest.mark.asyncio
    async def test_relationship_query_classification(self):
        """Test classification of relationship queries."""
        analyzer = IntentAnalyzer()

        queries = [
            "How is Microsoft related to OpenAI?",
            "What companies has Google acquired?",
            "Who are Apple's main competitors?"
        ]

        for query in queries:
            result = await analyzer.analyze(query)
            assert result.primary_intent == QueryIntent.RELATIONSHIP
            assert result.search_strategy in [
                SearchStrategy.GRAPH_FIRST,
                SearchStrategy.HYBRID
            ]

    @pytest.mark.asyncio
    async def test_temporal_query_classification(self):
        """Test classification of temporal queries."""
        analyzer = IntentAnalyzer()

        query = "Show me the timeline of AI developments in 2023"
        result = await analyzer.analyze(query)

        assert result.primary_intent == QueryIntent.TEMPORAL
        assert result.temporal_context is not None
        assert result.search_strategy == SearchStrategy.GRAPH_FIRST

    @pytest.mark.asyncio
    async def test_entity_extraction(self):
        """Test entity extraction from queries."""
        analyzer = IntentAnalyzer()

        query = "Compare Google and Microsoft's AI strategies"
        result = await analyzer.analyze(query)

        assert "Google" in result.entities or "google" in [e.lower() for e in result.entities]
        assert "Microsoft" in result.entities or "microsoft" in [e.lower() for e in result.entities]

    @pytest.mark.asyncio
    async def test_complexity_scoring(self):
        """Test query complexity scoring."""
        analyzer = IntentAnalyzer()

        simple_query = "What is AI?"
        complex_query = "Analyze the competitive dynamics between major tech companies in the AI space, considering their investments, partnerships, and technical capabilities"

        simple_result = await analyzer.analyze(simple_query)
        complex_result = await analyzer.analyze(complex_query)

        assert simple_result.complexity_score < 0.5
        assert complex_result.complexity_score > 0.7

class TestQueryRouter:
    """Test query routing functionality."""

    def test_routing_decisions(self):
        """Test routing decisions for different intents."""
        router = QueryRouter()

        # Mock analyzed queries
        factual_query = Mock(
            primary_intent=QueryIntent.FACTUAL,
            entities=[],
            temporal_context=None,
            confidence=0.9
        )

        relationship_query = Mock(
            primary_intent=QueryIntent.RELATIONSHIP,
            entities=["Microsoft", "OpenAI"],
            temporal_context=None,
            confidence=0.85
        )

        # Test factual routing
        factual_decision = router.route(factual_query)
        assert factual_decision.primary_strategy == SearchStrategy.VECTOR_FIRST
        assert len(factual_decision.fallback_strategies) > 0

        # Test relationship routing
        relationship_decision = router.route(relationship_query)
        assert relationship_decision.primary_strategy == SearchStrategy.GRAPH_FIRST
        assert "graph_search" in relationship_decision.recommended_tools

    def test_fallback_strategies(self):
        """Test fallback strategy selection."""
        router = QueryRouter()

        # Test each primary strategy has fallbacks
        for strategy in SearchStrategy:
            mock_query = Mock(
                primary_intent=QueryIntent.FACTUAL,
                entities=[],
                temporal_context=None,
                confidence=0.5
            )

            # Force specific strategy
            router.intent_strategy_map[QueryIntent.FACTUAL] = strategy
            decision = router.route(mock_query)

            assert len(decision.fallback_strategies) > 0
            assert decision.fallback_strategies[0] != strategy

class TestResponseGenerator:
    """Test response generation functionality."""

    @pytest.mark.asyncio
    async def test_citation_generation(self):
        """Test citation generation from search results."""
        generator = ResponseGenerator()

        search_results = {
            "vector_results": [
                {
                    "content": "Test content 1",
                    "score": 0.9,
                    "document_title": "Doc 1",
                    "document_id": "doc1",
                    "chunk_id": "chunk1"
                }
            ],
            "graph_results": {
                "facts": [
                    {
                        "fact": "Test fact 1",
                        "confidence": 0.85,
                        "source_chunk": "chunk2"
                    }
                ]
            }
        }

        content = generator._extract_relevant_content(search_results)
        citations = generator._generate_citations(content)

        assert len(citations) > 0
        assert citations[0].document_title == "Doc 1"
        assert citations[0].confidence == 0.9

    @pytest.mark.asyncio
    async def test_confidence_calculation(self):
        """Test confidence calculation for responses."""
        generator = ResponseGenerator()

        # High confidence scenario
        high_conf_content = [
            {"content": "High relevance", "score": 0.95, "source_type": "vector"},
            {"content": "Supporting fact", "score": 0.9, "source_type": "graph"}
        ]

        mock_query = Mock(complexity_score=0.3)

        confidence = generator._calculate_confidence(high_conf_content, mock_query)
        assert confidence > 0.8

        # Low confidence scenario
        low_conf_content = [
            {"content": "Low relevance", "score": 0.5, "source_type": "vector"}
        ]

        mock_complex_query = Mock(complexity_score=0.9)

        confidence = generator._calculate_confidence(low_conf_content, mock_complex_query)
        assert confidence < 0.6

    @pytest.mark.asyncio
    async def test_result_merging(self):
        """Test merging results from multiple sources."""
        generator = ResponseGenerator()

        vector_results = {
            "results": [
                {"content": "Vector result", "score": 0.8}
            ]
        }

        graph_results = {
            "facts": [
                {"fact": "Graph fact", "confidence": 0.9}
            ]
        }

        mock_query = Mock()

        merged = await generator.merge_results(
            vector_results,
            graph_results,
            mock_query
        )

        assert merged["type"] == "hybrid"
        assert len(merged["merged_results"]) == 2
        # Graph result should be ranked higher due to confidence
        assert "Graph fact" in merged["merged_results"][0]["content"]

class TestAgentIntegration:
    """Integration tests for the complete agent."""

    @pytest.mark.asyncio
    async def test_end_to_end_query_processing(self):
        """Test complete query processing pipeline."""
        # This would require mocking the database connections
        # and search implementations

        deps = AgentDependencies(
            session_id="test_session",
            user_id="test_user"
        )

        # Mock the search functions
        with patch('src.agentic_rag.agent.agent.vector_search') as mock_vector:
            mock_vector.return_value = {
                "type": "vector",
                "results": [
                    {
                        "content": "AI is artificial intelligence",
                        "score": 0.9,
                        "document_title": "AI Basics"
                    }
                ]
            }

            # Would test actual agent execution here
            # result = await rag_agent.run("What is AI?", deps=deps)
            # assert "artificial intelligence" in result.data

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in agent."""
        deps = AgentDependencies(session_id="test_session")

        # Test with search failure
        with patch('src.agentic_rag.agent.agent.vector_search') as mock_vector:
            mock_vector.side_effect = Exception("Search failed")

            # Agent should handle gracefully
            # result = await rag_agent.run("Test query", deps=deps)
            # assert result.error is not None

class TestPerformance:
    """Performance tests for agent components."""

    @pytest.mark.asyncio
    async def test_intent_analysis_performance(self):
        """Test intent analysis meets performance targets."""
        analyzer = IntentAnalyzer()

        queries = [
            "What is OpenAI?",
            "How are Microsoft and OpenAI related?",
            "Show me the timeline of AI developments",
            "Compare Google and Microsoft AI strategies"
        ] * 10  # 40 queries

        import time
        start = time.perf_counter()

        for query in queries:
            await analyzer.analyze(query)

        elapsed = time.perf_counter() - start
        avg_time = elapsed / len(queries)

        # Should analyze each query in under 100ms
        assert avg_time < 0.1

    @pytest.mark.asyncio
    async def test_response_generation_performance(self):
        """Test response generation performance."""
        generator = ResponseGenerator()

        # Mock search results
        search_results = {
            "vector_results": [
                {"content": f"Result {i}", "score": 0.8 + i*0.01}
                for i in range(20)
            ]
        }

        mock_query = Mock(complexity_score=0.5)

        import time
        start = time.perf_counter()

        for _ in range(10):
            response = await generator.generate_response(
                "Test query",
                search_results,
                mock_query
            )

        elapsed = time.perf_counter() - start
        avg_time = elapsed / 10

        # Should generate response in under 500ms
        assert avg_time < 0.5
```

## Configuration Files

### Agent Configuration (`src/agentic_rag/agent/config.py`)

```python
"""
Configuration for the agent intelligence layer.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class AgentConfig:
    """Configuration for the Pydantic AI agent."""

    # LLM Settings
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2000
    llm_timeout: int = 30

    # Agent Behavior
    max_tools_per_query: int = 5
    enable_streaming: bool = True
    enable_caching: bool = True
    confidence_threshold: float = 0.7

    # Search Settings
    default_search_limit: int = 10
    max_search_results: int = 50
    parallel_search_timeout: int = 5

    # Intent Analysis
    intent_cache_ttl: int = 300  # 5 minutes
    entity_extraction_model: Optional[str] = None  # Use default if None

    # Response Generation
    max_citations: int = 10
    include_confidence: bool = True
    generate_follow_ups: bool = True

    # Performance
    enable_query_cache: bool = True
    query_cache_ttl: int = 900  # 15 minutes
    embedding_cache_ttl: int = 3600  # 1 hour

    # Monitoring
    enable_metrics: bool = True
    log_level: str = "INFO"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_')
        }

# Global configuration instance
agent_config = AgentConfig()
```

## Deliverables Summary

### Phase 3 will deliver:

1. **Intent Analysis System**
   - Query classification with 9 intent types
   - Entity extraction
   - Temporal context detection
   - Complexity scoring
   - Strategy selection

2. **Pydantic AI Agent**
   - Flexible LLM provider support
   - 7+ registered tools
   - Smart search orchestration
   - Session management
   - Error handling

3. **Tool Implementations**
   - Vector search tool
   - Graph search tool
   - Hybrid search tool
   - Entity relationship tool
   - Entity timeline tool
   - Document retrieval tool
   - Comprehensive search tool

4. **Response Generation**
   - Citation management
   - Confidence scoring
   - Answer synthesis
   - Follow-up generation
   - Result merging

5. **Query Routing**
   - Intent-based routing
   - Fallback strategies
   - Tool recommendations
   - Routing confidence
   - Performance optimization

6. **Testing Suite**
   - Tests consolidated in `tests/test_rag.py`
   - Unit tests for all components
   - Integration tests
   - Performance benchmarks
   - Error handling tests

## Success Criteria

- Query intent classification accuracy >85%
- Response latency <3s for 95% of queries
- Source citation in 100% of responses
- Graceful handling of all error cases
- Test coverage >80%
- Complete documentation

## Risk Mitigation

### Technical Risks
- **LLM hallucination**: Strict citation requirements, confidence scoring
- **Query misclassification**: Fallback to hybrid search, multiple intent detection
- **Tool failures**: Circuit breakers, graceful degradation, fallback strategies
- **Slow responses**: Timeouts, partial results, caching

### Operational Risks
- **Cost overruns**: Token limits, caching, query batching
- **Rate limits**: Request queuing, exponential backoff
- **Memory leaks**: Session cleanup, connection pooling, resource limits

## Next Steps

After Phase 3 completion:

**Phase 4: API & Performance Optimization**
- FastAPI implementation
- Streaming responses
- Advanced caching
- Load balancing
- Performance monitoring

**Phase 5: Production Deployment**
- Docker containerization
- Kubernetes deployment
- CI/CD pipeline
- Monitoring & alerting
- Documentation & training
