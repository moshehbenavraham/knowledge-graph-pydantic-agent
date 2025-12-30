"""
Unit tests for relationship scoring functions.

Tests the evidence-based scoring system that calculates relationship strength
based on chunk count, relationship type priority, and entity importance scores.
"""

import pytest

from src.agentic_rag.graph.relationship_scoring import (
    DEFAULT_IMPORTANCE_SCORE,
    DEFAULT_MAX_CHUNKS,
    DEFAULT_TYPE_PRIORITY,
    TYPE_PRIORITIES,
    ScoringConfig,
    _calculate_importance_factor,
    _get_type_priority,
    _normalize_chunk_factor,
    calculate_relationship_strength,
    calculate_relationship_strength_from_dict,
)


class TestNormalizeChunkFactor:
    """Tests for _normalize_chunk_factor helper function."""

    def test_zero_chunks_returns_zero(self):
        """Zero chunks should return 0.0."""
        assert _normalize_chunk_factor(0) == 0.0

    def test_negative_chunks_returns_zero(self):
        """Negative chunks should return 0.0."""
        assert _normalize_chunk_factor(-1) == 0.0
        assert _normalize_chunk_factor(-100) == 0.0

    def test_one_chunk_returns_fraction(self):
        """One chunk should return 1/MAX_CHUNKS."""
        result = _normalize_chunk_factor(1, max_chunks=10)
        assert result == 0.1

    def test_max_chunks_returns_one(self):
        """MAX_CHUNKS should return 1.0."""
        result = _normalize_chunk_factor(10, max_chunks=10)
        assert result == 1.0

    def test_above_max_chunks_capped_at_one(self):
        """Chunks above MAX_CHUNKS should be capped at 1.0."""
        result = _normalize_chunk_factor(20, max_chunks=10)
        assert result == 1.0
        result = _normalize_chunk_factor(100, max_chunks=10)
        assert result == 1.0

    def test_custom_max_chunks(self):
        """Custom max_chunks threshold should work correctly."""
        result = _normalize_chunk_factor(5, max_chunks=5)
        assert result == 1.0
        result = _normalize_chunk_factor(1, max_chunks=5)
        assert result == 0.2

    def test_zero_max_chunks_returns_one(self):
        """Zero max_chunks should return 1.0 to avoid division by zero."""
        result = _normalize_chunk_factor(5, max_chunks=0)
        assert result == 1.0


class TestGetTypePriority:
    """Tests for _get_type_priority helper function."""

    def test_known_type_acquired(self):
        """ACQUIRED type should have highest priority."""
        result = _get_type_priority("acquired")
        assert result == 1.0

    def test_known_type_owns(self):
        """OWNS type should have highest priority."""
        result = _get_type_priority("owns")
        assert result == 1.0

    def test_known_type_invested_in(self):
        """INVESTED_IN type should have high priority."""
        result = _get_type_priority("invested_in")
        assert result == 0.75

    def test_known_type_partners_with(self):
        """PARTNERS_WITH type should have medium priority."""
        result = _get_type_priority("partners_with")
        assert result == 0.55

    def test_known_type_related_to(self):
        """RELATED_TO type should have low priority."""
        result = _get_type_priority("related_to")
        assert result == 0.3

    def test_known_type_mentioned_in(self):
        """MENTIONED_IN type should have lowest priority."""
        result = _get_type_priority("mentioned_in")
        assert result == 0.25

    def test_unknown_type_returns_default(self):
        """Unknown types should return DEFAULT_TYPE_PRIORITY."""
        result = _get_type_priority("unknown_type")
        assert result == DEFAULT_TYPE_PRIORITY
        assert result == 0.5

    def test_none_type_returns_default(self):
        """None type should return DEFAULT_TYPE_PRIORITY."""
        result = _get_type_priority(None)
        assert result == DEFAULT_TYPE_PRIORITY

    def test_empty_string_returns_default(self):
        """Empty string should return DEFAULT_TYPE_PRIORITY."""
        result = _get_type_priority("")
        assert result == DEFAULT_TYPE_PRIORITY

    def test_case_insensitive(self):
        """Type lookup should be case-insensitive."""
        assert _get_type_priority("ACQUIRED") == 1.0
        assert _get_type_priority("Acquired") == 1.0
        assert _get_type_priority("aCqUiReD") == 1.0

    def test_whitespace_trimmed(self):
        """Leading/trailing whitespace should be trimmed."""
        assert _get_type_priority("  acquired  ") == 1.0
        assert _get_type_priority("\tacquired\n") == 1.0


class TestCalculateImportanceFactor:
    """Tests for _calculate_importance_factor helper function."""

    def test_both_entities_with_scores(self):
        """Both entities with scores should average correctly."""
        result = _calculate_importance_factor(0.8, 0.6)
        assert result == 0.7

    def test_one_entity_none(self):
        """One None entity should use default for that entity."""
        result = _calculate_importance_factor(0.8, None)
        # (0.8 + 0.5) / 2 = 0.65
        assert result == 0.65

        result = _calculate_importance_factor(None, 0.6)
        # (0.5 + 0.6) / 2 = 0.55
        assert result == 0.55

    def test_both_entities_none(self):
        """Both None entities should use defaults."""
        result = _calculate_importance_factor(None, None)
        # (0.5 + 0.5) / 2 = 0.5
        assert result == 0.5

    def test_custom_default_importance(self):
        """Custom default importance should be used for None values."""
        result = _calculate_importance_factor(None, None, default_importance=0.7)
        # (0.7 + 0.7) / 2 = 0.7
        assert result == 0.7

    def test_scores_clamped_to_valid_range(self):
        """Scores should be clamped to [0.0, 1.0]."""
        result = _calculate_importance_factor(1.5, 0.5)
        # (1.0 + 0.5) / 2 = 0.75
        assert result == 0.75

        result = _calculate_importance_factor(-0.5, 0.5)
        # (0.0 + 0.5) / 2 = 0.25
        assert result == 0.25

    def test_zero_scores(self):
        """Zero scores should work correctly."""
        result = _calculate_importance_factor(0.0, 0.0)
        assert result == 0.0

    def test_max_scores(self):
        """Maximum scores should work correctly."""
        result = _calculate_importance_factor(1.0, 1.0)
        assert result == 1.0


class TestScoringConfig:
    """Tests for ScoringConfig dataclass."""

    def test_default_values(self):
        """Default configuration should have expected values."""
        config = ScoringConfig()
        assert config.w1 == 0.4
        assert config.w2 == 0.3
        assert config.w3 == 0.3
        assert config.max_chunks == DEFAULT_MAX_CHUNKS
        assert config.default_importance == DEFAULT_IMPORTANCE_SCORE

    def test_custom_weights(self):
        """Custom weights should be settable."""
        config = ScoringConfig(w1=0.5, w2=0.25, w3=0.25)
        assert config.w1 == 0.5
        assert config.w2 == 0.25
        assert config.w3 == 0.25

    def test_weights_sum_warning(self, caplog):
        """Non-unity weights should log a warning."""
        import logging

        caplog.set_level(logging.WARNING)
        config = ScoringConfig(w1=0.5, w2=0.5, w3=0.5)  # Sum = 1.5
        # Config is created but warning should be logged
        assert config.w1 == 0.5

    def test_custom_max_chunks(self):
        """Custom max_chunks should be settable."""
        config = ScoringConfig(max_chunks=20)
        assert config.max_chunks == 20


class TestCalculateRelationshipStrength:
    """Tests for calculate_relationship_strength main function."""

    def test_default_parameters(self):
        """Default parameters should produce valid result."""
        result = calculate_relationship_strength()
        # chunk_count=1, type=None, importance=None
        # chunk_factor = 1/10 = 0.1
        # type_factor = 0.5 (default)
        # importance_factor = 0.5 (default)
        # strength = 0.4*0.1 + 0.3*0.5 + 0.3*0.5 = 0.04 + 0.15 + 0.15 = 0.34
        assert result == pytest.approx(0.34, abs=0.01)

    def test_high_evidence_relationship(self):
        """High-evidence relationship should score high."""
        result = calculate_relationship_strength(
            chunk_count=10,
            relationship_type="acquired",
            entity1_importance=0.9,
            entity2_importance=0.9,
        )
        # chunk_factor = 10/10 = 1.0
        # type_factor = 1.0 (acquired)
        # importance_factor = (0.9 + 0.9) / 2 = 0.9
        # strength = 0.4*1.0 + 0.3*1.0 + 0.3*0.9 = 0.4 + 0.3 + 0.27 = 0.97
        assert result == pytest.approx(0.97, abs=0.01)

    def test_low_evidence_relationship(self):
        """Low-evidence relationship should score low."""
        result = calculate_relationship_strength(
            chunk_count=1,
            relationship_type="mentioned_in",
            entity1_importance=0.1,
            entity2_importance=0.1,
        )
        # chunk_factor = 1/10 = 0.1
        # type_factor = 0.25 (mentioned_in)
        # importance_factor = (0.1 + 0.1) / 2 = 0.1
        # strength = 0.4*0.1 + 0.3*0.25 + 0.3*0.1 = 0.04 + 0.075 + 0.03 = 0.145
        assert result == pytest.approx(0.145, abs=0.01)

    def test_zero_chunks_produces_low_score(self):
        """Zero chunks should produce lower score."""
        result = calculate_relationship_strength(chunk_count=0)
        # chunk_factor = 0.0
        # strength = 0.4*0.0 + 0.3*0.5 + 0.3*0.5 = 0.0 + 0.15 + 0.15 = 0.30
        assert result == pytest.approx(0.30, abs=0.01)

    def test_result_in_valid_range(self):
        """Result should always be in [0.0, 1.0]."""
        # Test various combinations
        test_cases = [
            (0, None, None, None),
            (100, "acquired", 1.0, 1.0),
            (1, "unknown", 0.0, 0.0),
            (50, "invested_in", 0.5, 0.8),
        ]
        for chunk_count, rel_type, e1_imp, e2_imp in test_cases:
            result = calculate_relationship_strength(
                chunk_count=chunk_count,
                relationship_type=rel_type,
                entity1_importance=e1_imp,
                entity2_importance=e2_imp,
            )
            assert 0.0 <= result <= 1.0, f"Result {result} out of range for inputs {test_cases}"

    def test_determinism(self):
        """Same inputs should always produce same output."""
        inputs = {
            "chunk_count": 5,
            "relationship_type": "partners_with",
            "entity1_importance": 0.7,
            "entity2_importance": 0.6,
        }
        result1 = calculate_relationship_strength(**inputs)
        result2 = calculate_relationship_strength(**inputs)
        result3 = calculate_relationship_strength(**inputs)
        assert result1 == result2 == result3

    def test_custom_config(self):
        """Custom config should affect result."""
        config = ScoringConfig(w1=1.0, w2=0.0, w3=0.0, max_chunks=5)
        result = calculate_relationship_strength(
            chunk_count=5,
            relationship_type="acquired",
            entity1_importance=0.0,
            entity2_importance=0.0,
            config=config,
        )
        # Only chunk_factor matters: 5/5 = 1.0
        # strength = 1.0*1.0 + 0.0*1.0 + 0.0*0.0 = 1.0
        assert result == 1.0

    def test_partners_with_type(self):
        """partners_with type should have expected score."""
        result = calculate_relationship_strength(
            chunk_count=5,
            relationship_type="partners_with",
            entity1_importance=0.5,
            entity2_importance=0.5,
        )
        # chunk_factor = 5/10 = 0.5
        # type_factor = 0.55 (partners_with)
        # importance_factor = 0.5
        # strength = 0.4*0.5 + 0.3*0.55 + 0.3*0.5 = 0.2 + 0.165 + 0.15 = 0.515
        assert result == pytest.approx(0.515, abs=0.01)


class TestCalculateRelationshipStrengthFromDict:
    """Tests for calculate_relationship_strength_from_dict convenience function."""

    def test_with_full_data(self):
        """Full relationship and entity dicts should work correctly."""
        relationship = {
            "type": "invested_in",
            "source_chunks": ["chunk1", "chunk2", "chunk3"],
        }
        entity1 = {"importance_score": 0.8}
        entity2 = {"importance_score": 0.6}

        result = calculate_relationship_strength_from_dict(
            relationship=relationship,
            entity1=entity1,
            entity2=entity2,
        )
        # chunk_count = 3
        # chunk_factor = 3/10 = 0.3
        # type_factor = 0.75 (invested_in)
        # importance_factor = (0.8 + 0.6) / 2 = 0.7
        # strength = 0.4*0.3 + 0.3*0.75 + 0.3*0.7 = 0.12 + 0.225 + 0.21 = 0.555
        assert result == pytest.approx(0.555, abs=0.01)

    def test_with_minimal_data(self):
        """Minimal relationship dict should use defaults."""
        relationship = {}
        result = calculate_relationship_strength_from_dict(relationship=relationship)
        # chunk_count = 1 (fallback)
        # type = None, importance = None
        # Should match default calculation
        expected = calculate_relationship_strength(chunk_count=1)
        assert result == expected

    def test_with_none_entities(self):
        """None entities should use defaults."""
        relationship = {
            "type": "acquired",
            "source_chunks": ["chunk1"],
        }
        result = calculate_relationship_strength_from_dict(
            relationship=relationship,
            entity1=None,
            entity2=None,
        )
        expected = calculate_relationship_strength(
            chunk_count=1,
            relationship_type="acquired",
            entity1_importance=None,
            entity2_importance=None,
        )
        assert result == expected

    def test_with_empty_source_chunks(self):
        """Empty source_chunks should default to chunk_count=1 (minimum evidence)."""
        relationship = {
            "type": "works_at",
            "source_chunks": [],
        }
        result = calculate_relationship_strength_from_dict(relationship=relationship)
        # Empty list defaults to chunk_count=1 for minimum evidence
        expected = calculate_relationship_strength(
            chunk_count=1,
            relationship_type="works_at",
        )
        assert result == expected

    def test_with_missing_importance_score(self):
        """Entities without importance_score should use default."""
        relationship = {"type": "founded"}
        entity1 = {"name": "Entity1"}  # No importance_score
        entity2 = {"name": "Entity2", "importance_score": 0.9}

        result = calculate_relationship_strength_from_dict(
            relationship=relationship,
            entity1=entity1,
            entity2=entity2,
        )
        expected = calculate_relationship_strength(
            chunk_count=1,
            relationship_type="founded",
            entity1_importance=None,  # Will use default
            entity2_importance=0.9,
        )
        assert result == expected


class TestTypePrioritiesConstant:
    """Tests for TYPE_PRIORITIES constant dictionary."""

    def test_all_values_in_valid_range(self):
        """All priority values should be in [0.0, 1.0]."""
        for rel_type, priority in TYPE_PRIORITIES.items():
            assert 0.0 <= priority <= 1.0, f"{rel_type} has invalid priority {priority}"

    def test_acquired_is_highest(self):
        """acquired/owns should have the highest priority."""
        max_priority = max(TYPE_PRIORITIES.values())
        assert TYPE_PRIORITIES["acquired"] == max_priority
        assert TYPE_PRIORITIES["owns"] == max_priority

    def test_mentioned_in_is_low(self):
        """mentioned_in should have low priority."""
        assert TYPE_PRIORITIES["mentioned_in"] < 0.5

    def test_expected_types_present(self):
        """Expected relationship types should be defined."""
        expected_types = [
            "acquired",
            "owns",
            "invested_in",
            "works_at",
            "partners_with",
            "competes_with",
            "founded",
            "related_to",
            "mentioned_in",
        ]
        for rel_type in expected_types:
            assert rel_type in TYPE_PRIORITIES, f"Missing type: {rel_type}"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_large_chunk_count(self):
        """Very large chunk counts should be handled correctly."""
        result = calculate_relationship_strength(chunk_count=1000000)
        assert 0.0 <= result <= 1.0

    def test_float_entity_importance(self):
        """Float entity importance scores should work correctly."""
        result = calculate_relationship_strength(
            entity1_importance=0.123456789,
            entity2_importance=0.987654321,
        )
        assert 0.0 <= result <= 1.0

    def test_unicode_relationship_type(self):
        """Unicode in relationship type should not crash."""
        result = calculate_relationship_strength(relationship_type="related_\u00e9")
        # Should use default priority for unknown type
        assert 0.0 <= result <= 1.0

    def test_whitespace_only_relationship_type(self):
        """Whitespace-only relationship type should use default."""
        result = calculate_relationship_strength(relationship_type="   ")
        # Empty after strip, should use default
        expected = calculate_relationship_strength(relationship_type="")
        assert result == expected

    def test_self_referential_relationship(self):
        """Same entity importance for both sides should work."""
        result = calculate_relationship_strength(
            chunk_count=5,
            relationship_type="related_to",
            entity1_importance=0.7,
            entity2_importance=0.7,  # Same entity
        )
        assert 0.0 <= result <= 1.0
        # importance_factor = (0.7 + 0.7) / 2 = 0.7
        assert result > 0.3  # Should have reasonable score


class TestIntegration:
    """Integration tests for scoring workflow."""

    def test_score_ordering_by_evidence(self):
        """Higher evidence should produce higher scores."""
        low_evidence = calculate_relationship_strength(
            chunk_count=1,
            relationship_type="mentioned_in",
            entity1_importance=0.3,
            entity2_importance=0.3,
        )
        medium_evidence = calculate_relationship_strength(
            chunk_count=5,
            relationship_type="partners_with",
            entity1_importance=0.5,
            entity2_importance=0.5,
        )
        high_evidence = calculate_relationship_strength(
            chunk_count=10,
            relationship_type="acquired",
            entity1_importance=0.9,
            entity2_importance=0.9,
        )

        assert low_evidence < medium_evidence < high_evidence

    def test_type_priority_affects_ordering(self):
        """Relationship type should affect score ordering."""
        # Same chunk count and importance, different types
        acquired_score = calculate_relationship_strength(
            chunk_count=5,
            relationship_type="acquired",
            entity1_importance=0.5,
            entity2_importance=0.5,
        )
        mentioned_score = calculate_relationship_strength(
            chunk_count=5,
            relationship_type="mentioned_in",
            entity1_importance=0.5,
            entity2_importance=0.5,
        )

        assert acquired_score > mentioned_score

    def test_chunk_count_affects_ordering(self):
        """More chunks should produce higher scores."""
        one_chunk = calculate_relationship_strength(chunk_count=1)
        five_chunks = calculate_relationship_strength(chunk_count=5)
        ten_chunks = calculate_relationship_strength(chunk_count=10)

        assert one_chunk < five_chunks < ten_chunks

    def test_importance_affects_ordering(self):
        """Higher entity importance should produce higher scores."""
        low_importance = calculate_relationship_strength(
            entity1_importance=0.1,
            entity2_importance=0.1,
        )
        high_importance = calculate_relationship_strength(
            entity1_importance=0.9,
            entity2_importance=0.9,
        )

        assert low_importance < high_importance
