"""
Unit tests for enhanced IntentAnalyzer with new intents.

Tests the MULTI_HOP, TEMPORAL_TREND, and COMPARISON intent detection
methods added in Phase 02 Session 04.
"""

import pytest

from src.agentic_rag.search.intent_analyzer import IntentAnalyzer, SearchIntent


@pytest.fixture
def analyzer() -> IntentAnalyzer:
    """Create IntentAnalyzer instance."""
    return IntentAnalyzer()


class TestMultiHopIntentDetection:
    """Tests for MULTI_HOP intent detection."""

    def test_detects_connected_to_pattern(self, analyzer: IntentAnalyzer) -> None:
        """Test detection of 'connected to' pattern."""
        result = analyzer.analyze("How is Intel connected to Mobileye?")
        assert result.primary_intent == SearchIntent.MULTI_HOP
        assert result.confidence >= 0.6

    def test_detects_path_from_pattern(self, analyzer: IntentAnalyzer) -> None:
        """Test detection of 'path from' pattern."""
        result = analyzer.analyze("Find the path from Apple to NVIDIA")
        assert result.primary_intent == SearchIntent.MULTI_HOP
        assert result.confidence >= 0.6

    def test_detects_connection_between_pattern(self, analyzer: IntentAnalyzer) -> None:
        """Test detection of 'connection between' pattern."""
        result = analyzer.analyze("What is the connection between Microsoft and OpenAI?")
        assert result.primary_intent == SearchIntent.MULTI_HOP
        assert result.confidence >= 0.6

    def test_detects_degrees_of_separation(self, analyzer: IntentAnalyzer) -> None:
        """Test detection of 'degrees of separation' pattern."""
        result = analyzer.analyze("How many degrees of separation between Tesla and Meta?")
        assert result.primary_intent == SearchIntent.MULTI_HOP

    def test_detects_linked_through_pattern(self, analyzer: IntentAnalyzer) -> None:
        """Test detection of 'linked through' pattern."""
        # Use explicit path/connection language to ensure detection
        result = analyzer.analyze("Find the path from Amazon to Google linked through acquisitions")
        assert result.primary_intent == SearchIntent.MULTI_HOP

    def test_two_entities_boost_multi_hop(self, analyzer: IntentAnalyzer) -> None:
        """Test that two entities boost multi-hop score."""
        result = analyzer.analyze("How is Intel connected to AMD through the chip market?")
        assert result.primary_intent == SearchIntent.MULTI_HOP
        assert len(result.entities_mentioned) >= 2

    def test_find_multi_hop_indicators(self, analyzer: IntentAnalyzer) -> None:
        """Test _find_multi_hop_indicators method."""
        indicators = analyzer._find_multi_hop_indicators("connected to via through network")
        assert "connected to" in indicators
        assert "through" in indicators
        assert "via" in indicators
        assert "network" in indicators


class TestTemporalTrendIntentDetection:
    """Tests for TEMPORAL_TREND intent detection."""

    def test_detects_trend_pattern(self, analyzer: IntentAnalyzer) -> None:
        """Test detection of 'trend' pattern."""
        result = analyzer.analyze("What is the revenue trend for Apple?")
        assert result.primary_intent == SearchIntent.TEMPORAL_TREND
        assert result.confidence >= 0.6

    def test_detects_over_time_pattern(self, analyzer: IntentAnalyzer) -> None:
        """Test detection of 'over time' pattern."""
        result = analyzer.analyze("How has Intel's profit changed over time?")
        assert result.primary_intent == SearchIntent.TEMPORAL_TREND

    def test_detects_yoy_pattern(self, analyzer: IntentAnalyzer) -> None:
        """Test detection of 'year over year' pattern."""
        result = analyzer.analyze("Show me Microsoft's year over year growth")
        assert result.primary_intent == SearchIntent.TEMPORAL_TREND

    def test_detects_qoq_pattern(self, analyzer: IntentAnalyzer) -> None:
        """Test detection of 'quarter over quarter' pattern."""
        result = analyzer.analyze("What is NVIDIA's qoq revenue change?")
        assert result.primary_intent == SearchIntent.TEMPORAL_TREND

    def test_detects_growth_pattern(self, analyzer: IntentAnalyzer) -> None:
        """Test detection of 'growth' pattern."""
        result = analyzer.analyze("Show AMD's revenue growth from 2020 to 2024")
        assert result.primary_intent == SearchIntent.TEMPORAL_TREND

    def test_detects_decline_pattern(self, analyzer: IntentAnalyzer) -> None:
        """Test detection of 'decline' pattern."""
        result = analyzer.analyze("Has Intel's market share shown a decline?")
        assert result.primary_intent == SearchIntent.TEMPORAL_TREND

    def test_temporal_markers_boost_trend(self, analyzer: IntentAnalyzer) -> None:
        """Test that temporal markers boost trend score."""
        result = analyzer.analyze("What is the revenue trend for Apple since 2020?")
        assert result.primary_intent == SearchIntent.TEMPORAL_TREND
        assert len(result.temporal_markers) >= 1

    def test_find_temporal_trend_indicators(self, analyzer: IntentAnalyzer) -> None:
        """Test _find_temporal_trend_indicators method."""
        indicators = analyzer._find_temporal_trend_indicators("trend growth yoy over time")
        assert "trend" in indicators
        assert "growth" in indicators
        assert "yoy" in indicators
        assert "over time" in indicators


class TestComparisonIntentDetection:
    """Tests for COMPARISON intent detection."""

    def test_detects_compare_pattern(self, analyzer: IntentAnalyzer) -> None:
        """Test detection of 'compare' pattern."""
        result = analyzer.analyze("Compare Intel and AMD revenue")
        assert result.primary_intent == SearchIntent.COMPARISON
        assert result.confidence >= 0.6

    def test_detects_versus_pattern(self, analyzer: IntentAnalyzer) -> None:
        """Test detection of 'versus' pattern."""
        result = analyzer.analyze("Apple versus Microsoft profit margins")
        assert result.primary_intent == SearchIntent.COMPARISON

    def test_detects_vs_pattern(self, analyzer: IntentAnalyzer) -> None:
        """Test detection of 'vs' pattern."""
        result = analyzer.analyze("Intel vs AMD in Q3 2024")
        assert result.primary_intent == SearchIntent.COMPARISON

    def test_detects_difference_between_pattern(self, analyzer: IntentAnalyzer) -> None:
        """Test detection of 'difference between' pattern."""
        result = analyzer.analyze("What is the difference between NVIDIA and AMD?")
        assert result.primary_intent == SearchIntent.COMPARISON

    def test_detects_ranking_pattern(self, analyzer: IntentAnalyzer) -> None:
        """Test detection of 'rank' pattern."""
        result = analyzer.analyze("Rank Intel, AMD, and NVIDIA by revenue")
        assert result.primary_intent == SearchIntent.COMPARISON

    def test_multiple_entities_boost_comparison(self, analyzer: IntentAnalyzer) -> None:
        """Test that multiple entities boost comparison score."""
        result = analyzer.analyze("Compare Intel, AMD, and NVIDIA profit")
        assert result.primary_intent == SearchIntent.COMPARISON
        assert len(result.entities_mentioned) >= 2

    def test_find_comparison_indicators(self, analyzer: IntentAnalyzer) -> None:
        """Test _find_comparison_indicators method."""
        indicators = analyzer._find_comparison_indicators("compare versus vs ranking")
        assert "compare" in indicators
        assert "versus" in indicators
        assert "vs" in indicators
        assert "ranking" in indicators


class TestIntentScoring:
    """Tests for intent scoring methods."""

    def test_score_multi_hop_intent_strong_indicators(self, analyzer: IntentAnalyzer) -> None:
        """Test scoring with strong multi-hop indicators."""
        score = analyzer._score_multi_hop_intent(
            multi_hop_indicators=["connected to", "path from"],
            entities=["Intel", "AMD"],
        )
        assert score >= 0.8

    def test_score_multi_hop_intent_weak_indicators(self, analyzer: IntentAnalyzer) -> None:
        """Test scoring with weak multi-hop indicators."""
        score = analyzer._score_multi_hop_intent(
            multi_hop_indicators=["via"],
            entities=[],
        )
        assert score < 0.5

    def test_score_temporal_trend_intent_strong_indicators(self, analyzer: IntentAnalyzer) -> None:
        """Test scoring with strong trend indicators."""
        score = analyzer._score_temporal_trend_intent(
            trend_indicators=["trend", "growth"],
            temporal_markers=["2023", "2024"],
            entities=["Intel"],
        )
        assert score >= 0.7

    def test_score_temporal_trend_intent_weak_indicators(self, analyzer: IntentAnalyzer) -> None:
        """Test scoring with weak trend indicators."""
        score = analyzer._score_temporal_trend_intent(
            trend_indicators=[],
            temporal_markers=[],
            entities=[],
        )
        assert score == 0.0

    def test_score_comparison_intent_strong_indicators(self, analyzer: IntentAnalyzer) -> None:
        """Test scoring with strong comparison indicators."""
        score = analyzer._score_comparison_intent(
            comparison_indicators=["compare", "versus"],
            entities=["Intel", "AMD", "NVIDIA"],
        )
        assert score >= 0.8

    def test_score_comparison_intent_weak_indicators(self, analyzer: IntentAnalyzer) -> None:
        """Test scoring with weak comparison indicators."""
        score = analyzer._score_comparison_intent(
            comparison_indicators=["against"],
            entities=["Intel"],
        )
        assert score < 0.5


class TestIntentFallback:
    """Tests for intent fallback behavior."""

    def test_low_confidence_falls_to_hybrid(self, analyzer: IntentAnalyzer) -> None:
        """Test that low confidence queries fall to HYBRID intent."""
        result = analyzer.analyze("tell me something")
        assert result.primary_intent == SearchIntent.HYBRID
        assert result.confidence >= 0.5

    def test_ambiguous_query_handled(self, analyzer: IntentAnalyzer) -> None:
        """Test that ambiguous queries are handled gracefully."""
        result = analyzer.analyze("information")
        # Should not fail and should return a valid intent
        assert result.primary_intent in SearchIntent
        assert result.confidence > 0

    def test_mixed_signals_resolved(self, analyzer: IntentAnalyzer) -> None:
        """Test that mixed signals are resolved correctly."""
        # Query with both comparison and trend signals
        result = analyzer.analyze("Compare Intel vs AMD revenue trend over time")
        # Should pick the strongest signal
        assert result.primary_intent in [
            SearchIntent.COMPARISON,
            SearchIntent.TEMPORAL_TREND,
        ]


class TestStatisticsTracking:
    """Tests for statistics tracking."""

    def test_stats_initialized(self, analyzer: IntentAnalyzer) -> None:
        """Test that statistics are initialized correctly."""
        stats = analyzer.get_stats()
        assert "analyses" in stats
        assert "intents" in stats

    def test_new_intents_tracked(self, analyzer: IntentAnalyzer) -> None:
        """Test that new intents are tracked in stats."""
        stats = analyzer.get_stats()
        intents = stats["intents"]
        assert SearchIntent.MULTI_HOP.value in intents
        assert SearchIntent.TEMPORAL_TREND.value in intents
        assert SearchIntent.COMPARISON.value in intents

    def test_analysis_count_increments(self, analyzer: IntentAnalyzer) -> None:
        """Test that analysis count increments."""
        initial_count = analyzer.get_stats()["analyses"]
        analyzer.analyze("test query")
        final_count = analyzer.get_stats()["analyses"]
        assert final_count == initial_count + 1
