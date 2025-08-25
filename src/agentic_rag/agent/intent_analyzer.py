"""
Intent analysis system for query classification and search strategy selection.
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """Types of query intents."""
    FACTUAL = "factual"              # Simple fact lookup
    RELATIONSHIP = "relationship"      # Entity relationships
    TEMPORAL = "temporal"             # Time-based queries
    COMPARISON = "comparison"         # Comparing entities
    EXPLORATORY = "exploratory"       # Open-ended exploration
    AGGREGATION = "aggregation"       # Statistical/summary
    DEFINITION = "definition"         # Concept explanation
    MULTI_HOP = "multi_hop"          # Requires multiple steps


class SearchStrategy(Enum):
    """Search strategies based on intent."""
    VECTOR_ONLY = "vector_only"
    GRAPH_ONLY = "graph_only"
    HYBRID = "hybrid"
    VECTOR_FIRST = "vector_first"    # Vector with graph enrichment
    GRAPH_FIRST = "graph_first"      # Graph with vector context
    ITERATIVE = "iterative"          # Multi-step refinement


@dataclass
class AnalyzedQuery:
    """Analyzed query with extracted information."""
    original_query: str
    primary_intent: QueryIntent
    secondary_intents: List[QueryIntent]
    entities: List[str]
    temporal_context: Optional[Tuple[datetime, datetime]]
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

    def _find_secondary_intents(self, query: str) -> List[QueryIntent]:
        """Find secondary intents in the query."""
        secondary_intents = []
        query_lower = query.lower()

        # Check for multiple intent indicators
        if any(re.search(p, query_lower) for p in self.relationship_patterns):
            if QueryIntent.RELATIONSHIP not in secondary_intents:
                secondary_intents.append(QueryIntent.RELATIONSHIP)

        if any(re.search(p, query_lower) for p in self.temporal_patterns):
            if QueryIntent.TEMPORAL not in secondary_intents:
                secondary_intents.append(QueryIntent.TEMPORAL)

        if 'compare' in query_lower or 'difference' in query_lower:
            if QueryIntent.COMPARISON not in secondary_intents:
                secondary_intents.append(QueryIntent.COMPARISON)

        return secondary_intents

    async def _extract_entities(self, query: str) -> List[str]:
        """Extract entities from the query."""
        # Simple pattern-based extraction for now
        # In production, would use NER or LLM
        entities = []
        
        # Look for capitalized words (simple heuristic)
        words = query.split()
        for word in words:
            if word[0].isupper() and len(word) > 1:
                # Filter out common starting words
                if word.lower() not in ['what', 'who', 'where', 'when', 'how', 'why']:
                    entities.append(word.strip('.,!?'))
        
        # Look for quoted terms
        quoted = re.findall(r'"([^"]*)"', query)
        entities.extend(quoted)
        
        return list(set(entities))  # Remove duplicates

    def _extract_temporal_context(self, query: str) -> Optional[Tuple[datetime, datetime]]:
        """Extract temporal context from the query."""
        # Look for year patterns
        years = re.findall(r'\b(19\d{2}|20\d{2})\b', query)
        
        if years:
            # For now, return a simple year range
            min_year = int(min(years))
            max_year = int(max(years))
            
            try:
                start = datetime(min_year, 1, 1)
                end = datetime(max_year, 12, 31)
                return (start, end)
            except ValueError:
                pass
        
        return None

    def _identify_relationships(self, query: str) -> List[str]:
        """Identify relationship types mentioned in the query."""
        relationships = []
        query_lower = query.lower()
        
        relationship_map = {
            'founded': 'FOUNDED',
            'acquired': 'ACQUIRED',
            'partnered': 'PARTNERED',
            'invested': 'INVESTED',
            'competes': 'COMPETES_WITH',
            'works': 'WORKS_AT',
            'owns': 'OWNS',
            'subsidiary': 'SUBSIDIARY_OF'
        }
        
        for keyword, rel_type in relationship_map.items():
            if keyword in query_lower:
                relationships.append(rel_type)
        
        return relationships

    def _calculate_complexity(self,
                            query: str,
                            primary_intent: QueryIntent,
                            entities: List[str],
                            temporal_context: Optional[tuple]) -> float:
        """Calculate query complexity score."""
        complexity = 0.0
        
        # Length factor
        word_count = len(query.split())
        if word_count > 20:
            complexity += 0.3
        elif word_count > 10:
            complexity += 0.2
        else:
            complexity += 0.1
        
        # Entity factor
        if len(entities) > 3:
            complexity += 0.3
        elif len(entities) > 1:
            complexity += 0.2
        elif len(entities) == 1:
            complexity += 0.1
        
        # Intent factor
        if primary_intent in [QueryIntent.MULTI_HOP, QueryIntent.EXPLORATORY]:
            complexity += 0.3
        elif primary_intent in [QueryIntent.RELATIONSHIP, QueryIntent.COMPARISON]:
            complexity += 0.2
        else:
            complexity += 0.1
        
        # Temporal factor
        if temporal_context:
            complexity += 0.1
        
        return min(complexity, 1.0)

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

    def _calculate_confidence(self,
                             primary_intent: QueryIntent,
                             entities: List[str],
                             complexity_score: float) -> float:
        """Calculate confidence in the analysis."""
        confidence = 0.5  # Base confidence
        
        # Clear intent boosts confidence
        if primary_intent in [QueryIntent.FACTUAL, QueryIntent.RELATIONSHIP]:
            confidence += 0.2
        
        # Having entities boosts confidence
        if entities:
            confidence += 0.15
        
        # Lower complexity boosts confidence
        if complexity_score < 0.5:
            confidence += 0.15
        
        return min(confidence, 1.0)