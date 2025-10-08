"""
Query intent analysis for intelligent search routing.

Analyzes user queries to determine the optimal search strategy.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SearchIntent(Enum):
    """Types of search intent."""

    VECTOR_HEAVY = "vector_heavy"  # Semantic content search
    GRAPH_HEAVY = "graph_heavy"  # Relationship/fact search
    HYBRID = "hybrid"  # Combined search
    TEMPORAL = "temporal"  # Timeline/history search
    ENTITY_FOCUSED = "entity_focused"  # Specific entity search


@dataclass
class IntentAnalysisResult:
    """Result of intent analysis."""

    primary_intent: SearchIntent
    confidence: float
    entities_mentioned: list[str]
    temporal_markers: list[str]
    relationship_indicators: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "primary_intent": self.primary_intent.value,
            "confidence": self.confidence,
            "entities_mentioned": self.entities_mentioned,
            "temporal_markers": self.temporal_markers,
            "relationship_indicators": self.relationship_indicators,
        }


class IntentAnalyzer:
    """
    Analyze query intent to determine optimal search strategy.

    Uses pattern matching and keyword analysis to understand
    what type of information the user is seeking.
    """

    # Keyword patterns for different intents
    RELATIONSHIP_KEYWORDS = [
        "related",
        "connected",
        "relationship",
        "relation",
        "works with",
        "works at",
        "employed",
        "founded",
        "created",
        "acquired",
        "bought",
        "invested",
        "partnership",
        "partner",
        "competitor",
        "competes",
        "versus",
        "vs",
        "owns",
        "owned by",
        "subsidiary",
        "parent company",
        "collaborates",
        "collaboration",
        "joint venture",
    ]

    TEMPORAL_KEYWORDS = [
        "timeline",
        "history",
        "evolution",
        "progression",
        "changed",
        "when",
        "date",
        "year",
        "month",
        "before",
        "after",
        "during",
        "since",
        "until",
        "first",
        "last",
        "latest",
        "recent",
        "current",
        "past",
        "present",
        "future",
        "chronological",
    ]

    FACT_KEYWORDS = [
        "fact",
        "facts",
        "specifically",
        "exactly",
        "precise",
        "detail",
        "details",
        "information about",
        "tell me about",
        "what is",
        "what are",
        "who is",
        "who are",
        "how many",
        "how much",
        "statistics",
        "data",
    ]

    ENTITY_PATTERNS = [
        r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b",  # Proper nouns
        r"\b(?:OpenAI|Anthropic|Google|Microsoft|Apple|Meta|Amazon|Tesla|NVIDIA)\b",  # Known companies
        r"\b(?:GPT-\d+|Claude|Gemini|LaMDA|PaLM|DALL-E|Stable Diffusion)\b",  # AI models
    ]

    def __init__(self):
        """Initialize intent analyzer."""
        self._stats = {"analyses": 0, "intents": {intent.value: 0 for intent in SearchIntent}}

    def analyze(self, query: str) -> IntentAnalysisResult:
        """
        Analyze query to determine search intent.

        Args:
            query: User query

        Returns:
            Intent analysis result
        """
        self._stats["analyses"] += 1
        query_lower = query.lower()

        # Extract features
        entities = self._extract_entities(query)
        temporal_markers = self._find_temporal_markers(query_lower)
        relationship_indicators = self._find_relationship_indicators(query_lower)
        fact_indicators = self._find_fact_indicators(query_lower)

        # Score different intents
        scores = {
            SearchIntent.GRAPH_HEAVY: self._score_graph_intent(
                relationship_indicators, temporal_markers, entities
            ),
            SearchIntent.TEMPORAL: self._score_temporal_intent(temporal_markers, fact_indicators),
            SearchIntent.ENTITY_FOCUSED: self._score_entity_intent(entities, fact_indicators),
            SearchIntent.VECTOR_HEAVY: self._score_vector_intent(
                query_lower, relationship_indicators, temporal_markers
            ),
            SearchIntent.HYBRID: 0.5,  # Default moderate score
        }

        # Determine primary intent
        primary_intent = max(scores, key=scores.get)
        confidence = scores[primary_intent]

        # Adjust for ambiguous cases
        if confidence < 0.6:
            primary_intent = SearchIntent.HYBRID
            confidence = 0.7

        # Update statistics
        self._stats["intents"][primary_intent.value] += 1

        logger.debug(
            f"Intent analysis: {primary_intent.value} "
            f"(confidence: {confidence:.2f}) for query: {query[:100]}..."
        )

        return IntentAnalysisResult(
            primary_intent=primary_intent,
            confidence=confidence,
            entities_mentioned=entities,
            temporal_markers=temporal_markers,
            relationship_indicators=relationship_indicators,
        )

    def _extract_entities(self, query: str) -> list[str]:
        """
        Extract potential entity names from query.

        Args:
            query: User query

        Returns:
            List of entity names
        """
        entities = []

        for pattern in self.ENTITY_PATTERNS:
            matches = re.findall(pattern, query)
            entities.extend(matches)

        # Deduplicate while preserving order
        seen = set()
        unique_entities = []
        for entity in entities:
            if entity not in seen:
                seen.add(entity)
                unique_entities.append(entity)

        return unique_entities

    def _find_temporal_markers(self, query_lower: str) -> list[str]:
        """
        Find temporal indicators in query.

        Args:
            query_lower: Lowercase query

        Returns:
            List of temporal markers found
        """
        markers = []

        for keyword in self.TEMPORAL_KEYWORDS:
            if keyword in query_lower:
                markers.append(keyword)

        # Look for date patterns
        date_patterns = [
            r"\b\d{4}\b",  # Years
            r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b",
            r"\b(?:q1|q2|q3|q4)\s+\d{4}\b",  # Quarters
        ]

        for pattern in date_patterns:
            if re.search(pattern, query_lower):
                markers.append("date_reference")
                break

        return markers

    def _find_relationship_indicators(self, query_lower: str) -> list[str]:
        """
        Find relationship indicators in query.

        Args:
            query_lower: Lowercase query

        Returns:
            List of relationship indicators
        """
        indicators = []

        for keyword in self.RELATIONSHIP_KEYWORDS:
            if keyword in query_lower:
                indicators.append(keyword)

        return indicators

    def _find_fact_indicators(self, query_lower: str) -> list[str]:
        """
        Find fact-seeking indicators in query.

        Args:
            query_lower: Lowercase query

        Returns:
            List of fact indicators
        """
        indicators = []

        for keyword in self.FACT_KEYWORDS:
            if keyword in query_lower:
                indicators.append(keyword)

        return indicators

    def _score_graph_intent(
        self, relationship_indicators: list[str], temporal_markers: list[str], entities: list[str]
    ) -> float:
        """
        Score likelihood of graph-heavy search intent.

        Args:
            relationship_indicators: Relationship keywords found
            temporal_markers: Temporal markers found
            entities: Entities mentioned

        Returns:
            Score between 0 and 1
        """
        score = 0.0

        # Strong indicators
        if len(relationship_indicators) >= 2:
            score += 0.5
        elif len(relationship_indicators) == 1:
            score += 0.3

        # Multiple entities suggest relationship search
        if len(entities) >= 2:
            score += 0.3

        # Temporal markers with relationships
        if temporal_markers and relationship_indicators:
            score += 0.2

        return min(score, 1.0)

    def _score_temporal_intent(
        self, temporal_markers: list[str], fact_indicators: list[str]
    ) -> float:
        """
        Score likelihood of temporal search intent.

        Args:
            temporal_markers: Temporal markers found
            fact_indicators: Fact indicators found

        Returns:
            Score between 0 and 1
        """
        score = 0.0

        # Strong temporal indicators
        if any(
            marker in ["timeline", "history", "evolution", "chronological"]
            for marker in temporal_markers
        ):
            score += 0.6
        elif len(temporal_markers) >= 2:
            score += 0.4
        elif len(temporal_markers) == 1:
            score += 0.2

        # Facts with temporal context
        if temporal_markers and fact_indicators:
            score += 0.2

        return min(score, 1.0)

    def _score_entity_intent(self, entities: list[str], fact_indicators: list[str]) -> float:
        """
        Score likelihood of entity-focused search intent.

        Args:
            entities: Entities mentioned
            fact_indicators: Fact indicators found

        Returns:
            Score between 0 and 1
        """
        score = 0.0

        # Single entity with fact-seeking
        if len(entities) == 1 and fact_indicators:
            score += 0.5

        # Multiple specific entities
        if len(entities) >= 3:
            score += 0.3

        # "Tell me about X" pattern
        if fact_indicators and entities:
            score += 0.2

        return min(score, 1.0)

    def _score_vector_intent(
        self, query_lower: str, relationship_indicators: list[str], temporal_markers: list[str]
    ) -> float:
        """
        Score likelihood of vector-heavy search intent.

        Args:
            query_lower: Lowercase query
            relationship_indicators: Relationship keywords found
            temporal_markers: Temporal markers found

        Returns:
            Score between 0 and 1
        """
        # Default score for general queries
        score = 0.5

        # Reduce score if other indicators are present
        if relationship_indicators:
            score -= 0.2
        if temporal_markers:
            score -= 0.1

        # Boost for content-seeking patterns
        content_patterns = [
            "explain",
            "describe",
            "summary",
            "overview",
            "understand",
            "learn about",
            "information on",
        ]

        for pattern in content_patterns:
            if pattern in query_lower:
                score += 0.3
                break

        return max(0.0, min(score, 1.0))

    def get_stats(self) -> dict[str, Any]:
        """
        Get analysis statistics.

        Returns:
            Statistics dictionary
        """
        stats = self._stats.copy()

        if stats["analyses"] > 0:
            stats["intent_distribution"] = {
                intent: count / stats["analyses"] for intent, count in stats["intents"].items()
            }

        return stats
