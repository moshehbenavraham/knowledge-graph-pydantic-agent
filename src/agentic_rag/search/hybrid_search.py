"""
Hybrid search orchestrator combining vector and graph search.

Intelligently combines results from multiple search strategies for
optimal retrieval performance.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from src.agentic_rag.config import get_config
from src.agentic_rag.storage.connection_manager import ConnectionManager
from src.config import SearchStrategy

from .graph_search import GraphSearch, GraphSearchResult
from .intent_analyzer import IntentAnalyzer, SearchIntent
from .ranker import ResultRanker
from .vector_search import ChunkResult, VectorSearch

logger = logging.getLogger(__name__)


@dataclass
class HybridSearchResult:
    """Combined search result."""

    chunks: list[ChunkResult] = field(default_factory=list)
    facts: list[Any] = field(default_factory=list)
    entities: list[Any] = field(default_factory=list)
    relationships: list[Any] = field(default_factory=list)
    search_strategy: SearchStrategy = SearchStrategy.HYBRID
    intent: SearchIntent | None = None
    query_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chunks": [c.to_dict() for c in self.chunks],
            "facts": [f.to_dict() if hasattr(f, "to_dict") else f for f in self.facts],
            "entities": [e.to_dict() if hasattr(e, "to_dict") else e for e in self.entities],
            "relationships": [
                r.to_dict() if hasattr(r, "to_dict") else r for r in self.relationships
            ],
            "search_strategy": self.search_strategy.value,
            "intent": self.intent.value if self.intent else None,
            "query_time": self.query_time,
            "metadata": self.metadata,
        }


class HybridSearch:
    """
    Intelligent combination of vector and graph search.

    Analyzes query intent, selects appropriate search strategy,
    and merges results for optimal relevance.
    """

    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize hybrid search.

        Args:
            connection_manager: Initialized database connection manager (required)

        Raises:
            ValueError: If connection_manager is None
        """
        if connection_manager is None:
            raise ValueError(
                "HybridSearch requires an initialized ConnectionManager. "
                "Use get_connection_manager() to get a properly initialized instance."
            )

        self.config = get_config()
        self.connection_manager = connection_manager

        # Initialize components
        self.vector_search = VectorSearch(self.connection_manager)
        self.graph_search = GraphSearch(self.connection_manager)
        self.intent_analyzer = IntentAnalyzer()
        self.ranker = ResultRanker()

        self._stats = {
            "searches": 0,
            "strategies": {s.value: 0 for s in SearchStrategy},
            "total_latency": 0,
            "graph_boosts": 0,
            "entity_boosts": 0,
        }

    async def search(
        self, query: str, limit: int = 10, strategy: SearchStrategy | None = None
    ) -> HybridSearchResult:
        """
        Perform hybrid search with intelligent strategy selection.

        Workflow:
        1. Analyze query intent
        2. Determine search strategy
        3. Execute parallel searches
        4. Merge and rank results

        Args:
            query: Search query
            limit: Maximum number of results
            strategy: Force specific strategy (optional)

        Returns:
            Hybrid search result
        """
        start_time = datetime.now()
        self._stats["searches"] += 1

        # Analyze intent if strategy not specified
        if strategy is None:
            intent_result = self.intent_analyzer.analyze(query)
            strategy = self._select_strategy(intent_result)
            intent = intent_result.primary_intent
        else:
            intent = None
            intent_result = None

        self._stats["strategies"][strategy.value] += 1

        logger.info(
            f"\n{'=' * 80}\n"
            f"HYBRID SEARCH STARTING\n"
            f"Query: {query[:100]}{'...' if len(query) > 100 else ''}\n"
            f"Strategy: {strategy.value}\n"
            f"Intent: {intent.value if intent else 'Not analyzed'}\n"
            f"Graph Enabled: {self.config.performance.enable_graph}\n"
            f"Parallel Enabled: {self.config.performance.enable_parallel_search}\n"
            f"Limit: {limit}\n"
            f"{'=' * 80}"
        )

        # Execute search based on strategy
        if strategy == SearchStrategy.VECTOR_ONLY:
            result = await self._vector_only_search(query, limit)

        elif strategy == SearchStrategy.GRAPH_ONLY:
            result = await self._graph_only_search(query, limit, intent_result)

        elif strategy == SearchStrategy.HYBRID:
            result = await self._hybrid_search(query, limit, intent_result)

        else:  # ADAPTIVE
            result = await self._adaptive_search(query, limit, intent_result)

        # Set metadata
        result.search_strategy = strategy
        result.intent = intent
        result.query_time = (datetime.now() - start_time).total_seconds()

        # Update statistics
        self._stats["total_latency"] += result.query_time

        logger.info(
            f"Hybrid search completed in {result.query_time:.3f}s: "
            f"{len(result.chunks)} chunks, {len(result.facts)} facts"
        )

        # Log analytics event (async, non-blocking)
        await self._log_search_analytics(
            query, strategy, intent, result, start_time, datetime.now()
        )

        return result

    def _select_strategy(self, intent_result) -> SearchStrategy:
        """
        Select search strategy based on intent.

        Args:
            intent_result: Intent analysis result

        Returns:
            Selected search strategy
        """
        intent = intent_result.primary_intent

        # Map intent to strategy
        if intent == SearchIntent.VECTOR_HEAVY:
            selected = SearchStrategy.VECTOR_ONLY
            reason = "Intent is VECTOR_HEAVY - semantic content search optimal"
        elif intent == SearchIntent.GRAPH_HEAVY:
            # Use graph if enabled
            if self.config.performance.enable_graph:
                selected = SearchStrategy.GRAPH_ONLY
                reason = "Intent is GRAPH_HEAVY and graph is enabled - using graph-only search"
            else:
                selected = SearchStrategy.VECTOR_ONLY
                reason = (
                    "Intent is GRAPH_HEAVY but graph is DISABLED - falling back to vector search"
                )
        elif intent in [SearchIntent.TEMPORAL, SearchIntent.ENTITY_FOCUSED]:
            # These benefit from hybrid approach
            if self.config.performance.enable_graph:
                selected = SearchStrategy.HYBRID
                reason = f"Intent is {intent.value} - benefits from hybrid approach (graph enabled)"
            else:
                selected = SearchStrategy.VECTOR_ONLY
                reason = f"Intent is {intent.value} but graph is DISABLED - using vector search"
        elif self.config.performance.enable_graph:
            selected = SearchStrategy.ADAPTIVE
            reason = "Intent is HYBRID - using adaptive strategy (graph enabled)"
        else:
            selected = SearchStrategy.VECTOR_ONLY
            reason = "Intent is HYBRID but graph is DISABLED - using vector search"

        logger.info(
            f"STRATEGY SELECTION: {selected.value}\n"
            f"  Reason: {reason}\n"
            f"  Intent: {intent.value} (confidence: {intent_result.confidence:.2f})\n"
            f"  Entities mentioned: {len(intent_result.entities_mentioned)}\n"
            f"  Relationship indicators: {len(intent_result.relationship_indicators)}\n"
            f"  Temporal markers: {len(intent_result.temporal_markers)}"
        )

        return selected

    async def _vector_only_search(self, query: str, limit: int) -> HybridSearchResult:
        """
        Perform vector-only search.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            Search result
        """
        logger.info("▶ Executing VECTOR_ONLY search strategy")
        start = datetime.now()

        chunks = await self.vector_search.search(query, limit)
        if chunks is None:
            chunks = []

        elapsed = (datetime.now() - start).total_seconds()
        logger.info(f"✓ VECTOR_ONLY search completed: {len(chunks)} chunks in {elapsed:.3f}s")

        return HybridSearchResult(chunks=chunks, metadata={"search_type": "vector_only"})

    async def _graph_only_search(self, query: str, limit: int, intent_result) -> HybridSearchResult:
        """
        Perform graph-only search with optional chunk retrieval.

        Args:
            query: Search query
            limit: Maximum results
            intent_result: Intent analysis result

        Returns:
            Search result
        """
        logger.info("▶ Executing GRAPH_ONLY search strategy")
        start = datetime.now()

        # Perform graph search
        graph_results = await self.graph_search.search(query, limit)

        # Optionally fetch content for source chunks
        chunks = []
        if graph_results and graph_results.chunk_refs:
            # Convert string refs to UUIDs
            chunk_uuids = []
            for ref in graph_results.chunk_refs[:limit]:
                try:
                    chunk_uuids.append(UUID(ref))
                except ValueError:
                    continue

            if chunk_uuids:
                chunks = await self.vector_search.get_chunks_by_ids(chunk_uuids)

        elapsed = (datetime.now() - start).total_seconds()

        if graph_results:
            logger.info(
                f"✓ GRAPH_ONLY search completed in {elapsed:.3f}s: "
                f"{len(chunks)} chunks, {len(graph_results.facts)} facts, "
                f"{len(graph_results.entities)} entities, {len(graph_results.relationships)} relationships"
            )
            return HybridSearchResult(
                chunks=chunks,
                facts=graph_results.facts,
                entities=graph_results.entities,
                relationships=graph_results.relationships,
                metadata={"search_type": "graph_only", "chunk_refs": graph_results.chunk_refs},
            )
        logger.info(
            f"✓ GRAPH_ONLY search completed in {elapsed:.3f}s: {len(chunks)} chunks, 0 facts"
        )
        return HybridSearchResult(
            chunks=chunks,
            facts=[],
            entities=[],
            relationships=[],
            metadata={"search_type": "graph_only", "chunk_refs": []},
        )

    async def _hybrid_search(self, query: str, limit: int, intent_result) -> HybridSearchResult:
        """
        Perform combined vector and graph search.

        Args:
            query: Search query
            limit: Maximum results
            intent_result: Intent analysis result

        Returns:
            Search result
        """
        logger.info("▶ Executing HYBRID search strategy (vector + graph in parallel)")
        start = datetime.now()

        # Execute searches in parallel
        if self.config.performance.enable_parallel_search:
            logger.info("  → Launching parallel vector and graph searches...")
            vector_task = asyncio.create_task(self.vector_search.search(query, limit * 2))
            graph_task = asyncio.create_task(self.graph_search.search(query, limit))

            vector_results, graph_results = await asyncio.gather(vector_task, graph_task)
            logger.info("  ✓ Parallel searches completed")
        else:
            # Sequential execution
            logger.info("  → Sequential execution (parallel disabled)")
            vector_results = await self.vector_search.search(query, limit * 2)
            graph_results = await self.graph_search.search(query, limit)

        # Boost vector results based on graph context
        boosted_chunks = await self._boost_with_graph_context(
            vector_results, graph_results, intent_result
        )

        # Rank and limit results
        logger.info("  → Ranking and merging results...")
        ranked_chunks = self.ranker.rank_chunks(boosted_chunks, limit)

        elapsed = (datetime.now() - start).total_seconds()
        logger.info(
            f"✓ HYBRID search completed in {elapsed:.3f}s:\n"
            f"  Vector results: {len(vector_results)}\n"
            f"  Graph results: {len(graph_results.facts)} facts, {len(graph_results.entities)} entities\n"
            f"  Final ranked chunks: {len(ranked_chunks)}\n"
            f"  Boosts applied: {self._stats['graph_boosts']} graph, {self._stats['entity_boosts']} entity"
        )

        return HybridSearchResult(
            chunks=ranked_chunks,
            facts=graph_results.facts[:10],  # Limit facts
            entities=graph_results.entities[:10],
            relationships=graph_results.relationships[:10],
            metadata={
                "search_type": "hybrid",
                "vector_count": len(vector_results),
                "graph_facts": len(graph_results.facts),
                "boosts_applied": self._stats["graph_boosts"],
            },
        )

    async def _adaptive_search(self, query: str, limit: int, intent_result) -> HybridSearchResult:
        """
        Adaptive search that adjusts strategy based on initial results.

        Args:
            query: Search query
            limit: Maximum results
            intent_result: Intent analysis result

        Returns:
            Search result
        """
        logger.info("▶ Executing ADAPTIVE search strategy")
        start = datetime.now()

        # Start with fast vector search
        logger.info("  → Phase 1: Initial vector search (5 results)")
        initial_chunks = await self.vector_search.search(query, 5)

        # Check if we need graph search
        need_graph = False
        reasons = []

        # Low similarity scores suggest need for graph
        if not initial_chunks or all(c.similarity < 0.7 for c in initial_chunks):
            need_graph = True
            reasons.append("low similarity scores")

        # Multiple entities mentioned suggests graph search
        if intent_result and len(intent_result.entities_mentioned) >= 2:
            need_graph = True
            reasons.append(f"{len(intent_result.entities_mentioned)} entities mentioned")

        if need_graph and self.config.performance.enable_graph:
            logger.info(f"  → Phase 2: Switching to HYBRID search (reasons: {', '.join(reasons)})")
            # Perform full hybrid search
            return await self._hybrid_search(query, limit, intent_result)

        # Continue with vector-only
        logger.info("  → Phase 2: Continuing with vector-only search")
        more_chunks = await self.vector_search.search(query, limit)

        elapsed = (datetime.now() - start).total_seconds()
        logger.info(
            f"✓ ADAPTIVE search completed in {elapsed:.3f}s: {len(more_chunks)} chunks (vector-only)"
        )

        return HybridSearchResult(chunks=more_chunks, metadata={"search_type": "adaptive_vector"})

    async def _boost_with_graph_context(
        self, vector_results: list[ChunkResult], graph_results: GraphSearchResult, intent_result
    ) -> list[ChunkResult]:
        """
        Boost vector results using graph context.

        Args:
            vector_results: Vector search results
            graph_results: Graph search results
            intent_result: Intent analysis result

        Returns:
            Boosted chunk results
        """
        # Extract relevant context from graph
        relevant_chunk_ids = set(graph_results.chunk_refs)
        relevant_entities = {e.name.lower() for e in graph_results.entities}

        # Apply boosts
        for chunk in vector_results:
            boost = 1.0

            # Boost if chunk is referenced in graph results
            if str(chunk.chunk_id) in relevant_chunk_ids:
                boost *= 1.3
                self._stats["graph_boosts"] += 1

            # Boost if chunk contains relevant entities
            chunk_entities_lower = {e.lower() for e in chunk.entities}
            if chunk_entities_lower & relevant_entities:
                boost *= 1.2
                self._stats["entity_boosts"] += 1

            # Boost based on intent match
            if intent_result:
                # Temporal queries boost recent chunks
                if intent_result.primary_intent == SearchIntent.TEMPORAL:
                    # Check chunk metadata for recency
                    if "created_at" in chunk.metadata:
                        # Simple recency boost (would need proper implementation)
                        boost *= 1.1

                # Entity queries boost chunks with mentioned entities
                if intent_result.primary_intent == SearchIntent.ENTITY_FOCUSED:
                    mentioned_lower = {e.lower() for e in intent_result.entities_mentioned}
                    if chunk_entities_lower & mentioned_lower:
                        boost *= 1.3

            # Apply boost to similarity score
            chunk.similarity = min(1.0, chunk.similarity * boost)

        # Re-sort by boosted scores
        vector_results.sort(key=lambda x: x.similarity, reverse=True)

        return vector_results

    async def search_similar(self, chunk_id: UUID, limit: int = 5) -> HybridSearchResult:
        """
        Find similar content using both vector and graph context.

        Args:
            chunk_id: Reference chunk ID
            limit: Maximum results

        Returns:
            Similar content
        """
        # Get similar chunks by vector
        similar_chunks = await self.vector_search.search_similar_chunks(chunk_id, limit)

        # Get chunk's entities for graph search
        if similar_chunks and self.config.performance.enable_graph:
            reference_chunk = similar_chunks[0]
            if reference_chunk.entities:
                # Search graph for related entities
                entity_query = " ".join(reference_chunk.entities[:3])
                graph_results = await self.graph_search.search(entity_query, 10)

                # Boost similar chunks with related entities
                similar_chunks = await self._boost_with_graph_context(
                    similar_chunks, graph_results, None
                )

                return HybridSearchResult(
                    chunks=similar_chunks,
                    facts=graph_results.facts[:5],
                    entities=graph_results.entities[:5],
                    search_strategy=SearchStrategy.HYBRID,
                    metadata={"reference_chunk": str(chunk_id)},
                )

        return HybridSearchResult(
            chunks=similar_chunks,
            search_strategy=SearchStrategy.VECTOR_ONLY,
            metadata={"reference_chunk": str(chunk_id)},
        )

    def get_stats(self) -> dict[str, Any]:
        """
        Get search statistics.

        Returns:
            Statistics dictionary
        """
        stats = self._stats.copy()

        # Add component stats
        stats["vector_stats"] = self.vector_search.get_stats()
        stats["graph_stats"] = self.graph_search.get_stats()
        stats["intent_stats"] = self.intent_analyzer.get_stats()

        # Calculate averages
        if stats["searches"] > 0:
            stats["avg_latency"] = stats["total_latency"] / stats["searches"]
            stats["strategy_distribution"] = {
                strategy: count / stats["searches"]
                for strategy, count in stats["strategies"].items()
            }
            stats["avg_graph_boosts"] = stats["graph_boosts"] / stats["searches"]
            stats["avg_entity_boosts"] = stats["entity_boosts"] / stats["searches"]

        return stats

    async def _log_search_analytics(
        self,
        query: str,
        strategy: SearchStrategy,
        intent: SearchIntent | None,
        result: HybridSearchResult,
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        """
        Log search analytics event (async, non-blocking).

        Args:
            query: Search query
            strategy: Search strategy used
            intent: Detected intent
            result: Search result
            start_time: Search start time
            end_time: Search end time
        """
        try:
            from src.agentic_rag.analytics import SearchAnalyticsEvent, get_analytics_logger

            # Calculate latency
            total_latency_ms = (end_time - start_time).total_seconds() * 1000

            # Map strategy to analytics format
            strategy_map = {
                SearchStrategy.VECTOR_ONLY: "VECTOR_HEAVY",
                SearchStrategy.GRAPH_ONLY: "GRAPH_HEAVY",
                SearchStrategy.HYBRID: "HYBRID",
                SearchStrategy.ADAPTIVE: "HYBRID",
            }

            intent_map = {
                SearchIntent.VECTOR_HEAVY: "VECTOR_HEAVY",
                SearchIntent.GRAPH_HEAVY: "GRAPH_HEAVY",
                SearchIntent.HYBRID: "HYBRID",
                SearchIntent.TEMPORAL: "TEMPORAL",
                SearchIntent.ENTITY_FOCUSED: "ENTITY_FOCUSED",
            }

            # Get latencies from metadata if available
            metadata = result.metadata or {}
            vector_latency = metadata.get("vector_latency_ms", 0)
            graph_latency = metadata.get("graph_latency_ms", 0)
            intent_latency = metadata.get("intent_analysis_latency_ms", 0)
            ranking_latency = metadata.get("ranking_latency_ms", 0)

            # Create analytics event
            event = SearchAnalyticsEvent(
                query_text=query,
                detected_intent=intent_map.get(intent, "HYBRID") if intent else "HYBRID",
                strategy_used=strategy_map.get(strategy, "HYBRID"),
                total_latency_ms=total_latency_ms,
                vector_latency_ms=vector_latency,
                graph_latency_ms=graph_latency,
                intent_analysis_latency_ms=intent_latency,
                ranking_latency_ms=ranking_latency,
                chunks_returned=len(result.chunks),
                cache_hit=metadata.get("cache_hit", False),
                entities_found=len(result.entities),
                relationships_found=len(result.relationships),
                facts_found=len(result.facts),
                graph_boost_applied=bool(result.entities or result.facts),
                entity_boost_applied=bool(result.entities),
                source="api",  # Will be overridden by caller if needed
                metadata={
                    "search_type": metadata.get("search_type", "hybrid"),
                    "limit": metadata.get("limit", 10),
                },
            )

            # Log event (non-blocking)
            analytics_logger = get_analytics_logger()
            await analytics_logger.log_search(event)

        except Exception as e:
            # Never let analytics errors break search
            logger.warning(f"Failed to log search analytics: {e}")
