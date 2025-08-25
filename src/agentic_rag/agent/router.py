"""
Query routing for optimal search strategy selection.
"""

import logging
from dataclasses import dataclass
from typing import Any

from .intent_analyzer import QueryIntent, SearchStrategy

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """Represents a routing decision for a query."""

    primary_strategy: SearchStrategy
    fallback_strategies: list[SearchStrategy]
    confidence: float
    reasoning: str
    recommended_tools: list[str]


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
            QueryIntent.MULTI_HOP: SearchStrategy.ITERATIVE,
        }

        # Fallback strategies for each primary
        self.fallback_map = {
            SearchStrategy.VECTOR_ONLY: [SearchStrategy.HYBRID],
            SearchStrategy.GRAPH_ONLY: [SearchStrategy.HYBRID],
            SearchStrategy.VECTOR_FIRST: [SearchStrategy.HYBRID, SearchStrategy.GRAPH_ONLY],
            SearchStrategy.GRAPH_FIRST: [SearchStrategy.HYBRID, SearchStrategy.VECTOR_ONLY],
            SearchStrategy.HYBRID: [SearchStrategy.VECTOR_FIRST, SearchStrategy.GRAPH_FIRST],
            SearchStrategy.ITERATIVE: [SearchStrategy.HYBRID],
        }

        # Tool recommendations
        self.strategy_tools_map = {
            SearchStrategy.VECTOR_ONLY: ["vector_search"],
            SearchStrategy.GRAPH_ONLY: ["graph_search", "get_entity_relationships"],
            SearchStrategy.VECTOR_FIRST: ["vector_search", "graph_search"],
            SearchStrategy.GRAPH_FIRST: ["graph_search", "vector_search"],
            SearchStrategy.HYBRID: ["smart_search", "comprehensive_search"],
            SearchStrategy.ITERATIVE: [
                "smart_search",
                "get_entity_relationships",
                "get_entity_timeline",
            ],
        }

    def route(self, analyzed_query) -> RoutingDecision:
        """
        Make routing decision based on analyzed query.
        """
        # Get primary strategy
        primary_strategy = self.intent_strategy_map.get(
            analyzed_query.primary_intent, SearchStrategy.HYBRID
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
        reasoning = self._generate_reasoning(analyzed_query, primary_strategy)

        # Calculate routing confidence
        confidence = self._calculate_routing_confidence(analyzed_query, primary_strategy)

        return RoutingDecision(
            primary_strategy=primary_strategy,
            fallback_strategies=fallbacks,
            confidence=confidence,
            reasoning=reasoning,
            recommended_tools=tools,
        )

    def _generate_reasoning(self, analyzed_query, strategy: SearchStrategy) -> str:
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
            SearchStrategy.ITERATIVE: "Using iterative search for complex query",
        }

        reasons.append(strategy_reason.get(strategy, "Using default strategy"))

        return ". ".join(reasons)

    def _calculate_routing_confidence(self, analyzed_query, strategy: SearchStrategy) -> float:
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

    def should_use_graph(self, analyzed_query) -> bool:
        """Determine if graph search should be used."""
        # Check if strategy involves graph
        graph_strategies = [
            SearchStrategy.GRAPH_ONLY,
            SearchStrategy.GRAPH_FIRST,
            SearchStrategy.HYBRID,
            SearchStrategy.ITERATIVE,
        ]

        decision = self.route(analyzed_query)
        return decision.primary_strategy in graph_strategies

    def should_use_vector(self, analyzed_query) -> bool:
        """Determine if vector search should be used."""
        # Check if strategy involves vector
        vector_strategies = [
            SearchStrategy.VECTOR_ONLY,
            SearchStrategy.VECTOR_FIRST,
            SearchStrategy.HYBRID,
            SearchStrategy.ITERATIVE,
        ]

        decision = self.route(analyzed_query)
        return decision.primary_strategy in vector_strategies

    def get_search_params(
        self, analyzed_query, strategy: SearchStrategy | None = None
    ) -> dict[str, Any]:
        """Get recommended search parameters for a strategy."""
        if strategy is None:
            decision = self.route(analyzed_query)
            strategy = decision.primary_strategy

        params = {"limit": 10, "use_vector": True, "use_graph": True, "confidence_threshold": 0.7}

        # Adjust parameters based on strategy
        if strategy == SearchStrategy.VECTOR_ONLY:
            params["use_graph"] = False
            params["limit"] = 20

        elif strategy == SearchStrategy.GRAPH_ONLY:
            params["use_vector"] = False
            params["max_facts"] = 30

        elif strategy == SearchStrategy.VECTOR_FIRST:
            params["vector_limit"] = 15
            params["graph_limit"] = 10
            params["vector_weight"] = 0.7

        elif strategy == SearchStrategy.GRAPH_FIRST:
            params["vector_limit"] = 10
            params["graph_limit"] = 20
            params["vector_weight"] = 0.3

        elif strategy == SearchStrategy.HYBRID:
            params["vector_limit"] = 15
            params["graph_limit"] = 15
            params["vector_weight"] = 0.5

        elif strategy == SearchStrategy.ITERATIVE:
            params["max_iterations"] = 3
            params["refine_queries"] = True

        # Adjust based on query complexity
        if analyzed_query.complexity_score > 0.7:
            params["limit"] = int(params.get("limit", 10) * 1.5)

        return params

    def select_fallback(
        self, primary_strategy: SearchStrategy, error_type: str | None = None
    ) -> SearchStrategy:
        """Select appropriate fallback strategy based on error."""
        fallbacks = self.fallback_map.get(primary_strategy, [SearchStrategy.HYBRID])

        if not fallbacks:
            return SearchStrategy.HYBRID

        # Select based on error type if provided
        if error_type == "graph_unavailable":
            # Prefer vector-based fallbacks
            for fallback in fallbacks:
                if fallback in [SearchStrategy.VECTOR_ONLY, SearchStrategy.VECTOR_FIRST]:
                    return fallback

        elif error_type == "vector_unavailable":
            # Prefer graph-based fallbacks
            for fallback in fallbacks:
                if fallback in [SearchStrategy.GRAPH_ONLY, SearchStrategy.GRAPH_FIRST]:
                    return fallback

        # Return first fallback as default
        return fallbacks[0]


class AdaptiveRouter(QueryRouter):
    """
    Adaptive router that learns from feedback and adjusts routing decisions.
    """

    def __init__(self):
        super().__init__()
        self.routing_history = []
        self.success_rates = {}

    def record_outcome(
        self,
        query_intent: QueryIntent,
        strategy_used: SearchStrategy,
        success: bool,
        response_quality: float,
    ):
        """Record the outcome of a routing decision."""
        self.routing_history.append(
            {
                "intent": query_intent,
                "strategy": strategy_used,
                "success": success,
                "quality": response_quality,
            }
        )

        # Update success rates
        key = (query_intent, strategy_used)
        if key not in self.success_rates:
            self.success_rates[key] = {"successes": 0, "total": 0}

        self.success_rates[key]["total"] += 1
        if success:
            self.success_rates[key]["successes"] += 1

    def get_best_strategy_for_intent(
        self, intent: QueryIntent, min_samples: int = 5
    ) -> SearchStrategy | None:
        """Get the best performing strategy for an intent based on history."""
        best_strategy = None
        best_rate = 0.0

        for (hist_intent, strategy), stats in self.success_rates.items():
            if hist_intent != intent:
                continue

            if stats["total"] < min_samples:
                continue

            success_rate = stats["successes"] / stats["total"]

            if success_rate > best_rate:
                best_rate = success_rate
                best_strategy = strategy

        return best_strategy

    def route(self, analyzed_query) -> RoutingDecision:
        """Route with adaptive learning."""
        # Check if we have historical data for this intent
        historical_best = self.get_best_strategy_for_intent(analyzed_query.primary_intent)

        if historical_best:
            # Use historical best with high confidence
            decision = super().route(analyzed_query)
            decision.primary_strategy = historical_best
            decision.confidence = min(decision.confidence + 0.1, 1.0)
            decision.reasoning += " (Based on historical performance)"
            return decision

        # Fall back to standard routing
        return super().route(analyzed_query)
