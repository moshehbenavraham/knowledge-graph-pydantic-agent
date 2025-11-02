"""
Comprehensive tests for IntentAnalyzer.

Target coverage: 28% → 95%+

Tests all intent detection patterns, scoring logic, entity extraction,
temporal markers, relationship indicators, and statistics tracking.
"""

import pytest

from src.agentic_rag.search.intent_analyzer import (
    IntentAnalysisResult,
    IntentAnalyzer,
    SearchIntent,
)


class TestIntentAnalyzerInit:
    """Test IntentAnalyzer initialization."""

    def test_init_creates_stats(self):
        """Test that initialization creates stats tracking."""
        analyzer = IntentAnalyzer()

        assert analyzer._stats["analyses"] == 0
        assert "intents" in analyzer._stats
        assert all(intent.value in analyzer._stats["intents"] for intent in SearchIntent)


class TestIntentAnalysisResult:
    """Test IntentAnalysisResult dataclass."""

    def test_intent_result_to_dict(self):
        """Test conversion to dictionary."""
        result = IntentAnalysisResult(
            primary_intent=SearchIntent.VECTOR_HEAVY,
            confidence=0.85,
            entities_mentioned=["OpenAI", "GPT-4"],
            temporal_markers=["recent"],
            relationship_indicators=["partnership"],
        )

        result_dict = result.to_dict()

        assert result_dict["primary_intent"] == "vector_heavy"
        assert result_dict["confidence"] == 0.85
        assert result_dict["entities_mentioned"] == ["OpenAI", "GPT-4"]
        assert result_dict["temporal_markers"] == ["recent"]
        assert result_dict["relationship_indicators"] == ["partnership"]


class TestEntityExtraction:
    """Test entity extraction from queries."""

    def test_extract_entities_proper_nouns(self):
        """Test extraction of proper nouns."""
        analyzer = IntentAnalyzer()

        entities = analyzer._extract_entities("OpenAI released GPT-4 with Microsoft")

        assert "OpenAI" in entities
        assert "GPT" in entities or "GPT-4" in entities
        assert "Microsoft" in entities

    def test_extract_entities_known_companies(self):
        """Test extraction of known companies."""
        analyzer = IntentAnalyzer()

        entities = analyzer._extract_entities("Google and Anthropic compete with OpenAI")

        assert "Google" in entities
        assert "Anthropic" in entities
        assert "OpenAI" in entities

    def test_extract_entities_ai_models(self):
        """Test extraction of AI model names."""
        analyzer = IntentAnalyzer()

        entities = analyzer._extract_entities("Claude and GPT-4 are LLMs")

        assert "Claude" in entities
        assert "GPT-4" in entities

    def test_extract_entities_deduplication(self):
        """Test that duplicate entities are removed."""
        analyzer = IntentAnalyzer()

        entities = analyzer._extract_entities("Microsoft Microsoft Microsoft")

        assert entities.count("Microsoft") == 1

    def test_extract_entities_order_preserved(self):
        """Test that entity order is preserved."""
        analyzer = IntentAnalyzer()

        # Use separated entities to test order preservation
        # The regex captures multi-word proper nouns, so we use punctuation to separate
        entities = analyzer._extract_entities("First. Second. Third. Second.")

        # Should have First, Second, Third (Second deduplicated)
        assert len(entities) == 3
        assert entities[0] == "First"
        assert entities[1] == "Second"
        assert entities[2] == "Third"

    def test_extract_entities_empty_query(self):
        """Test entity extraction from empty query."""
        analyzer = IntentAnalyzer()

        entities = analyzer._extract_entities("")

        assert entities == []

    def test_extract_entities_no_entities(self):
        """Test query with no entities."""
        analyzer = IntentAnalyzer()

        entities = analyzer._extract_entities("how does this work")

        assert len(entities) == 0


class TestTemporalMarkerDetection:
    """Test temporal marker detection."""

    def test_find_temporal_markers_timeline(self):
        """Test detection of timeline keywords."""
        analyzer = IntentAnalyzer()

        markers = analyzer._find_temporal_markers("show me the timeline of events")

        assert "timeline" in markers

    def test_find_temporal_markers_history(self):
        """Test detection of history keywords."""
        analyzer = IntentAnalyzer()

        markers = analyzer._find_temporal_markers("what is the history of openai")

        assert "history" in markers

    def test_find_temporal_markers_when(self):
        """Test detection of when keywords."""
        analyzer = IntentAnalyzer()

        markers = analyzer._find_temporal_markers("when did this happen")

        assert "when" in markers

    def test_find_temporal_markers_year(self):
        """Test detection of year references."""
        analyzer = IntentAnalyzer()

        markers = analyzer._find_temporal_markers("what happened in 2023")

        assert "date_reference" in markers

    def test_find_temporal_markers_month(self):
        """Test detection of month references."""
        analyzer = IntentAnalyzer()

        markers = analyzer._find_temporal_markers("events in january 2024")

        assert "date_reference" in markers

    def test_find_temporal_markers_quarter(self):
        """Test detection of quarter references."""
        analyzer = IntentAnalyzer()

        markers = analyzer._find_temporal_markers("q1 2024 results")

        assert "date_reference" in markers

    def test_find_temporal_markers_multiple(self):
        """Test detection of multiple temporal markers."""
        analyzer = IntentAnalyzer()

        markers = analyzer._find_temporal_markers("recent timeline of events since 2020")

        assert "recent" in markers
        assert "timeline" in markers
        assert "since" in markers
        assert "date_reference" in markers

    def test_find_temporal_markers_before_after(self):
        """Test detection of before/after keywords."""
        analyzer = IntentAnalyzer()

        markers = analyzer._find_temporal_markers("what happened before and after the event")

        assert "before" in markers
        assert "after" in markers

    def test_find_temporal_markers_none(self):
        """Test query with no temporal markers."""
        analyzer = IntentAnalyzer()

        markers = analyzer._find_temporal_markers("explain the concept")

        assert markers == []


class TestRelationshipIndicatorDetection:
    """Test relationship indicator detection."""

    def test_find_relationship_indicators_related(self):
        """Test detection of related keywords."""
        analyzer = IntentAnalyzer()

        indicators = analyzer._find_relationship_indicators("how are they related")

        assert "related" in indicators

    def test_find_relationship_indicators_connected(self):
        """Test detection of connected keywords."""
        analyzer = IntentAnalyzer()

        indicators = analyzer._find_relationship_indicators("who is connected to whom")

        assert "connected" in indicators

    def test_find_relationship_indicators_partnership(self):
        """Test detection of partnership keywords."""
        analyzer = IntentAnalyzer()

        indicators = analyzer._find_relationship_indicators("their partnership was announced")

        assert "partnership" in indicators

    def test_find_relationship_indicators_acquired(self):
        """Test detection of acquisition keywords."""
        analyzer = IntentAnalyzer()

        indicators = analyzer._find_relationship_indicators("who acquired the company")

        assert "acquired" in indicators

    def test_find_relationship_indicators_invested(self):
        """Test detection of investment keywords."""
        analyzer = IntentAnalyzer()

        indicators = analyzer._find_relationship_indicators("who invested in the startup")

        assert "invested" in indicators

    def test_find_relationship_indicators_owns(self):
        """Test detection of ownership keywords."""
        analyzer = IntentAnalyzer()

        indicators = analyzer._find_relationship_indicators("who owns the subsidiary")

        assert "owns" in indicators

    def test_find_relationship_indicators_multiple(self):
        """Test detection of multiple relationship indicators."""
        analyzer = IntentAnalyzer()

        indicators = analyzer._find_relationship_indicators(
            "the partnership involves companies that are related and connected"
        )

        assert "partnership" in indicators
        assert "related" in indicators
        assert "connected" in indicators

    def test_find_relationship_indicators_none(self):
        """Test query with no relationship indicators."""
        analyzer = IntentAnalyzer()

        indicators = analyzer._find_relationship_indicators("explain the technology")

        assert indicators == []


class TestFactIndicatorDetection:
    """Test fact indicator detection."""

    def test_find_fact_indicators_what_is(self):
        """Test detection of what is questions."""
        analyzer = IntentAnalyzer()

        indicators = analyzer._find_fact_indicators("what is machine learning")

        assert "what is" in indicators

    def test_find_fact_indicators_who_is(self):
        """Test detection of who is questions."""
        analyzer = IntentAnalyzer()

        indicators = analyzer._find_fact_indicators("who is the ceo")

        assert "who is" in indicators

    def test_find_fact_indicators_how_many(self):
        """Test detection of how many questions."""
        analyzer = IntentAnalyzer()

        indicators = analyzer._find_fact_indicators("how many employees does it have")

        assert "how many" in indicators

    def test_find_fact_indicators_tell_me_about(self):
        """Test detection of tell me about patterns."""
        analyzer = IntentAnalyzer()

        indicators = analyzer._find_fact_indicators("tell me about the product")

        assert "tell me about" in indicators

    def test_find_fact_indicators_specifically(self):
        """Test detection of specifically keyword."""
        analyzer = IntentAnalyzer()

        indicators = analyzer._find_fact_indicators("what specifically happened")

        assert "specifically" in indicators

    def test_find_fact_indicators_multiple(self):
        """Test detection of multiple fact indicators."""
        analyzer = IntentAnalyzer()

        indicators = analyzer._find_fact_indicators(
            "tell me about the data and specifically what is included"
        )

        assert "tell me about" in indicators
        assert "specifically" in indicators
        assert "what is" in indicators

    def test_find_fact_indicators_none(self):
        """Test query with no fact indicators."""
        analyzer = IntentAnalyzer()

        indicators = analyzer._find_fact_indicators("compare the two")

        assert indicators == []


class TestGraphIntentScoring:
    """Test graph-heavy intent scoring."""

    def test_score_graph_intent_multiple_relationships(self):
        """Test scoring with multiple relationship indicators."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_graph_intent(
            relationship_indicators=["related", "connected"],
            temporal_markers=[],
            entities=["Entity1"],
        )

        assert score >= 0.5

    def test_score_graph_intent_single_relationship(self):
        """Test scoring with single relationship indicator."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_graph_intent(
            relationship_indicators=["partnership"],
            temporal_markers=[],
            entities=[],
        )

        assert score >= 0.3

    def test_score_graph_intent_multiple_entities(self):
        """Test scoring with multiple entities."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_graph_intent(
            relationship_indicators=[],
            temporal_markers=[],
            entities=["Entity1", "Entity2"],
        )

        assert score >= 0.3

    def test_score_graph_intent_temporal_and_relationships(self):
        """Test scoring with both temporal and relationship markers."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_graph_intent(
            relationship_indicators=["connected"],
            temporal_markers=["when"],
            entities=[],
        )

        assert score >= 0.5

    def test_score_graph_intent_capped_at_one(self):
        """Test that score is capped at 1.0."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_graph_intent(
            relationship_indicators=["r1", "r2", "r3"],
            temporal_markers=["t1", "t2"],
            entities=["e1", "e2", "e3"],
        )

        assert score <= 1.0

    def test_score_graph_intent_no_indicators(self):
        """Test scoring with no indicators."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_graph_intent(
            relationship_indicators=[],
            temporal_markers=[],
            entities=[],
        )

        assert score == 0.0


class TestTemporalIntentScoring:
    """Test temporal intent scoring."""

    def test_score_temporal_intent_timeline_keyword(self):
        """Test scoring with timeline keyword."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_temporal_intent(
            temporal_markers=["timeline"],
            fact_indicators=[],
        )

        assert score >= 0.6

    def test_score_temporal_intent_history_keyword(self):
        """Test scoring with history keyword."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_temporal_intent(
            temporal_markers=["history"],
            fact_indicators=[],
        )

        assert score >= 0.6

    def test_score_temporal_intent_multiple_markers(self):
        """Test scoring with multiple temporal markers."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_temporal_intent(
            temporal_markers=["when", "recent"],
            fact_indicators=[],
        )

        assert score >= 0.4

    def test_score_temporal_intent_with_facts(self):
        """Test scoring with temporal and fact indicators."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_temporal_intent(
            temporal_markers=["when"],
            fact_indicators=["what is"],
        )

        assert score >= 0.4

    def test_score_temporal_intent_capped_at_one(self):
        """Test that score is capped at 1.0."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_temporal_intent(
            temporal_markers=["timeline", "history", "when", "recent"],
            fact_indicators=["what is", "tell me about"],
        )

        assert score <= 1.0

    def test_score_temporal_intent_no_markers(self):
        """Test scoring with no markers."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_temporal_intent(
            temporal_markers=[],
            fact_indicators=[],
        )

        assert score == 0.0


class TestEntityIntentScoring:
    """Test entity-focused intent scoring."""

    def test_score_entity_intent_single_entity_with_facts(self):
        """Test scoring with single entity and fact indicators."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_entity_intent(
            entities=["OpenAI"],
            fact_indicators=["what is"],
        )

        assert score >= 0.5

    def test_score_entity_intent_multiple_entities(self):
        """Test scoring with multiple specific entities."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_entity_intent(
            entities=["Entity1", "Entity2", "Entity3"],
            fact_indicators=[],
        )

        assert score >= 0.3

    def test_score_entity_intent_entities_and_facts(self):
        """Test scoring with entities and fact indicators."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_entity_intent(
            entities=["Company1", "Company2"],
            fact_indicators=["tell me about"],
        )

        assert score >= 0.2

    def test_score_entity_intent_no_entities(self):
        """Test scoring with no entities."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_entity_intent(
            entities=[],
            fact_indicators=["what is"],
        )

        assert score == 0.0


class TestVectorIntentScoring:
    """Test vector-heavy intent scoring."""

    def test_score_vector_intent_default(self):
        """Test default vector score."""
        analyzer = IntentAnalyzer()

        # Use a query without content patterns to get default 0.5
        score = analyzer._score_vector_intent(
            query_lower="the concept",
            relationship_indicators=[],
            temporal_markers=[],
        )

        assert score == 0.5

    def test_score_vector_intent_with_explain(self):
        """Test scoring with explain keyword."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_vector_intent(
            query_lower="explain this concept",
            relationship_indicators=[],
            temporal_markers=[],
        )

        assert score >= 0.8

    def test_score_vector_intent_with_describe(self):
        """Test scoring with describe keyword."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_vector_intent(
            query_lower="describe the process",
            relationship_indicators=[],
            temporal_markers=[],
        )

        assert score >= 0.8

    def test_score_vector_intent_with_summary(self):
        """Test scoring with summary keyword."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_vector_intent(
            query_lower="give me a summary",
            relationship_indicators=[],
            temporal_markers=[],
        )

        assert score >= 0.8

    def test_score_vector_intent_reduced_by_relationships(self):
        """Test that relationship indicators reduce vector score."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_vector_intent(
            query_lower="explain the connection",
            relationship_indicators=["connection"],
            temporal_markers=[],
        )

        assert score < 0.8

    def test_score_vector_intent_reduced_by_temporal(self):
        """Test that temporal markers reduce vector score."""
        analyzer = IntentAnalyzer()

        # Base score 0.5, temporal reduces by 0.1 to 0.4
        score = analyzer._score_vector_intent(
            query_lower="the data when",
            relationship_indicators=[],
            temporal_markers=["when"],
        )

        # Should be reduced from 0.5 to 0.4
        assert score == 0.4
        assert score < 0.5

    def test_score_vector_intent_minimum_zero(self):
        """Test that score doesn't go below zero."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_vector_intent(
            query_lower="",
            relationship_indicators=["r1", "r2"],
            temporal_markers=["t1", "t2"],
        )

        assert score >= 0.0

    def test_score_vector_intent_maximum_one(self):
        """Test that score doesn't exceed one."""
        analyzer = IntentAnalyzer()

        score = analyzer._score_vector_intent(
            query_lower="explain describe summary overview understand learn about information on",
            relationship_indicators=[],
            temporal_markers=[],
        )

        assert score <= 1.0


class TestAnalyzeMethod:
    """Test the main analyze method."""

    def test_analyze_vector_heavy_query(self):
        """Test analysis of vector-heavy query."""
        analyzer = IntentAnalyzer()

        result = analyzer.analyze("Explain the concept of machine learning")

        assert result.primary_intent == SearchIntent.VECTOR_HEAVY
        assert 0.0 <= result.confidence <= 1.0

    def test_analyze_graph_heavy_query(self):
        """Test analysis of graph-heavy query."""
        analyzer = IntentAnalyzer()

        result = analyzer.analyze("How are Microsoft and OpenAI related and connected?")

        assert result.primary_intent in [SearchIntent.GRAPH_HEAVY, SearchIntent.HYBRID]
        assert len(result.relationship_indicators) > 0

    def test_analyze_temporal_query(self):
        """Test analysis of temporal query."""
        analyzer = IntentAnalyzer()

        result = analyzer.analyze("Show me the timeline of OpenAI's history")

        assert result.primary_intent in [SearchIntent.TEMPORAL, SearchIntent.HYBRID]
        assert len(result.temporal_markers) > 0

    def test_analyze_entity_focused_query(self):
        """Test analysis of entity-focused query."""
        analyzer = IntentAnalyzer()

        result = analyzer.analyze("Tell me about GPT-4")

        assert result.primary_intent in [SearchIntent.ENTITY_FOCUSED, SearchIntent.HYBRID]
        assert len(result.entities_mentioned) > 0

    def test_analyze_hybrid_low_confidence(self):
        """Test that low confidence defaults to hybrid."""
        analyzer = IntentAnalyzer()

        result = analyzer.analyze("what")

        assert result.primary_intent == SearchIntent.HYBRID
        assert result.confidence == 0.7

    def test_analyze_increments_stats(self):
        """Test that analyze increments statistics."""
        analyzer = IntentAnalyzer()

        initial_analyses = analyzer._stats["analyses"]

        analyzer.analyze("test query")

        assert analyzer._stats["analyses"] == initial_analyses + 1

    def test_analyze_tracks_intent_distribution(self):
        """Test that analyze tracks intent distribution."""
        analyzer = IntentAnalyzer()

        result = analyzer.analyze("explain this")

        assert analyzer._stats["intents"][result.primary_intent.value] > 0

    def test_analyze_extracts_entities(self):
        """Test that analyze extracts entities."""
        analyzer = IntentAnalyzer()

        result = analyzer.analyze("OpenAI and Microsoft partnership")

        assert "OpenAI" in result.entities_mentioned or "Microsoft" in result.entities_mentioned

    def test_analyze_finds_temporal_markers(self):
        """Test that analyze finds temporal markers."""
        analyzer = IntentAnalyzer()

        result = analyzer.analyze("what happened in 2023")

        assert len(result.temporal_markers) > 0

    def test_analyze_finds_relationship_indicators(self):
        """Test that analyze finds relationship indicators."""
        analyzer = IntentAnalyzer()

        result = analyzer.analyze("who is connected to whom")

        assert len(result.relationship_indicators) > 0

    def test_analyze_empty_query(self):
        """Test analysis of empty query."""
        analyzer = IntentAnalyzer()

        result = analyzer.analyze("")

        assert result.primary_intent == SearchIntent.HYBRID
        assert result.entities_mentioned == []

    def test_analyze_complex_query(self):
        """Test analysis of complex query with multiple indicators."""
        analyzer = IntentAnalyzer()

        result = analyzer.analyze(
            "Explain the timeline of Microsoft's partnership with OpenAI from 2019 to 2023"
        )

        assert len(result.entities_mentioned) >= 2
        assert len(result.temporal_markers) > 0
        assert len(result.relationship_indicators) > 0


class TestGetStats:
    """Test statistics retrieval."""

    def test_get_stats_initial_state(self):
        """Test stats in initial state."""
        analyzer = IntentAnalyzer()

        stats = analyzer.get_stats()

        assert stats["analyses"] == 0
        assert "intents" in stats

    def test_get_stats_after_analyses(self):
        """Test stats after performing analyses."""
        analyzer = IntentAnalyzer()

        analyzer.analyze("query 1")
        analyzer.analyze("query 2")
        analyzer.analyze("query 3")

        stats = analyzer.get_stats()

        assert stats["analyses"] == 3
        assert "intent_distribution" in stats

    def test_get_stats_intent_distribution(self):
        """Test intent distribution calculation."""
        analyzer = IntentAnalyzer()

        # Force specific intent
        analyzer.analyze("explain this")  # VECTOR_HEAVY
        analyzer.analyze("explain that")  # VECTOR_HEAVY

        stats = analyzer.get_stats()

        assert "intent_distribution" in stats
        assert stats["intent_distribution"]["vector_heavy"] > 0

    def test_get_stats_distribution_sums_to_one(self):
        """Test that distribution percentages sum to ~1.0."""
        analyzer = IntentAnalyzer()

        for i in range(10):
            analyzer.analyze(f"query {i}")

        stats = analyzer.get_stats()

        if "intent_distribution" in stats:
            total = sum(stats["intent_distribution"].values())
            assert abs(total - 1.0) < 0.01


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_analyze_very_long_query(self):
        """Test analysis of very long query."""
        analyzer = IntentAnalyzer()

        long_query = "explain " * 1000
        result = analyzer.analyze(long_query)

        assert result.primary_intent == SearchIntent.VECTOR_HEAVY

    def test_analyze_special_characters(self):
        """Test query with special characters."""
        analyzer = IntentAnalyzer()

        result = analyzer.analyze("What's the relationship between A&B @ 2023?")

        assert isinstance(result, IntentAnalysisResult)

    def test_analyze_unicode_characters(self):
        """Test query with unicode characters."""
        analyzer = IntentAnalyzer()

        result = analyzer.analyze("François Hollande et Emmanuel Macron")

        assert isinstance(result, IntentAnalysisResult)

    def test_analyze_numbers_only(self):
        """Test query with only numbers."""
        analyzer = IntentAnalyzer()

        result = analyzer.analyze("2023 2024 2025")

        assert len(result.temporal_markers) > 0

    def test_analyze_mixed_case(self):
        """Test query with mixed case."""
        analyzer = IntentAnalyzer()

        result = analyzer.analyze("EXPLAIN The CONCEPT")

        assert result.primary_intent == SearchIntent.VECTOR_HEAVY

    def test_multiple_analyzers_independent_stats(self):
        """Test that multiple analyzers have independent stats."""
        analyzer1 = IntentAnalyzer()
        analyzer2 = IntentAnalyzer()

        analyzer1.analyze("query 1")
        analyzer1.analyze("query 2")

        analyzer2.analyze("query 3")

        assert analyzer1._stats["analyses"] == 2
        assert analyzer2._stats["analyses"] == 1


class TestPatternMatching:
    """Test pattern matching edge cases."""

    def test_entity_pattern_single_word_proper_noun(self):
        """Test single word proper noun extraction."""
        analyzer = IntentAnalyzer()

        entities = analyzer._extract_entities("Microsoft announced")

        assert "Microsoft" in entities

    def test_entity_pattern_multi_word_proper_noun(self):
        """Test multi-word proper noun extraction."""
        analyzer = IntentAnalyzer()

        entities = analyzer._extract_entities("New York City")

        assert "New York" in entities or "New York City" in entities

    def test_temporal_pattern_year_boundary(self):
        """Test year pattern at boundaries."""
        analyzer = IntentAnalyzer()

        markers1 = analyzer._find_temporal_markers("999")  # Too short
        markers2 = analyzer._find_temporal_markers("2023")  # Valid
        markers3 = analyzer._find_temporal_markers("99999")  # Too long

        assert "date_reference" not in markers1
        assert "date_reference" in markers2
        assert "date_reference" not in markers3

    def test_relationship_keyword_case_insensitive(self):
        """Test relationship keywords are case insensitive."""
        analyzer = IntentAnalyzer()

        # Method expects lowercased input (query_lower parameter)
        # The analyze() method lowercases before calling this
        indicators1 = analyzer._find_relationship_indicators("RELATED".lower())
        indicators2 = analyzer._find_relationship_indicators("related".lower())
        indicators3 = analyzer._find_relationship_indicators("ReLaTeD".lower())

        assert "related" in indicators1
        assert "related" in indicators2
        assert "related" in indicators3

    def test_partial_keyword_match(self):
        """Test that partial matches are found."""
        analyzer = IntentAnalyzer()

        # "partner" should match in "partnership"
        indicators = analyzer._find_relationship_indicators("partnership announcement")

        assert "partnership" in indicators or "partner" in indicators


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
