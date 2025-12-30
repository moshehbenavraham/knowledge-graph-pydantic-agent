"""
Performance benchmark tests for Phase 01 Knowledge Graph components.

Performance targets:
- Type hierarchy expansion: < 10ms
- Relationship strength calculation: < 5ms
- Temporal metadata parsing: < 5ms
- Numeric fact extraction: < 50ms for typical content

These tests verify that core operations complete within acceptable time bounds.
Note: Actual database query performance (Neo4j, Supabase) is tested separately
as it depends on network latency and database load.
"""

import time
from typing import Any

import pytest

from src.agentic_rag.graph import (
    ScoringConfig,
    TypeHierarchy,
    calculate_relationship_strength,
    calculate_relationship_strength_from_dict,
    extract_numeric_facts_json,
    get_type_hierarchy,
    parse_filename,
    parse_numeric_facts,
)


class TestTypeHierarchyPerformance:
    """Performance tests for TypeHierarchy operations."""

    @pytest.fixture
    def hierarchy(self) -> TypeHierarchy:
        """Create a TypeHierarchy instance for testing."""
        return TypeHierarchy()

    def test_get_subtypes_performance(self, hierarchy: TypeHierarchy) -> None:
        """get_subtypes should complete in < 1ms."""
        start = time.perf_counter()
        for _ in range(1000):
            hierarchy.get_subtypes("organization")
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms

        # 1000 iterations in < 100ms means < 0.1ms per call
        assert elapsed < 100, f"get_subtypes too slow: {elapsed:.2f}ms for 1000 calls"

    def test_get_parent_type_performance(self, hierarchy: TypeHierarchy) -> None:
        """get_parent_type should complete in < 1ms."""
        start = time.perf_counter()
        for _ in range(1000):
            hierarchy.get_parent_type("company")
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 100, f"get_parent_type too slow: {elapsed:.2f}ms for 1000 calls"

    def test_is_subtype_of_performance(self, hierarchy: TypeHierarchy) -> None:
        """is_subtype_of should complete in < 1ms."""
        start = time.perf_counter()
        for _ in range(1000):
            hierarchy.is_subtype_of("company", "organization")
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 100, f"is_subtype_of too slow: {elapsed:.2f}ms for 1000 calls"

    def test_expand_type_filter_performance(self, hierarchy: TypeHierarchy) -> None:
        """expand_type_filter should complete in < 10ms."""
        start = time.perf_counter()
        for _ in range(1000):
            hierarchy.expand_type_filter("organization")
        elapsed = (time.perf_counter() - start) * 1000

        # 1000 iterations should complete in < 500ms (< 0.5ms per call)
        assert elapsed < 500, f"expand_type_filter too slow: {elapsed:.2f}ms for 1000 calls"

    def test_build_type_match_cypher_performance(self, hierarchy: TypeHierarchy) -> None:
        """build_type_match_cypher should complete in < 10ms."""
        start = time.perf_counter()
        for _ in range(1000):
            hierarchy.build_type_match_cypher("organization")
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 500, f"build_type_match_cypher too slow: {elapsed:.2f}ms for 1000 calls"

    def test_singleton_access_performance(self) -> None:
        """get_type_hierarchy singleton should have near-zero overhead."""
        start = time.perf_counter()
        for _ in range(10000):
            get_type_hierarchy()
        elapsed = (time.perf_counter() - start) * 1000

        # 10000 accesses should be < 50ms (< 0.005ms per access)
        assert elapsed < 50, f"Singleton access too slow: {elapsed:.2f}ms for 10000 accesses"


class TestRelationshipScoringPerformance:
    """Performance tests for relationship scoring calculations."""

    def test_calculate_relationship_strength_performance(self) -> None:
        """calculate_relationship_strength should complete in < 5ms."""
        start = time.perf_counter()
        for _ in range(1000):
            calculate_relationship_strength(
                chunk_count=5,
                relationship_type="acquired",
                entity1_importance=0.8,
                entity2_importance=0.7,
            )
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 200, f"Scoring too slow: {elapsed:.2f}ms for 1000 calculations"

    def test_calculate_relationship_strength_with_config_performance(self) -> None:
        """Scoring with custom config should not add significant overhead."""
        config = ScoringConfig(w1=0.5, w2=0.3, w3=0.2)

        start = time.perf_counter()
        for _ in range(1000):
            calculate_relationship_strength(
                chunk_count=3,
                relationship_type="works_at",
                entity1_importance=0.6,
                entity2_importance=0.5,
                config=config,
            )
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 200, f"Scoring with config too slow: {elapsed:.2f}ms for 1000 calcs"

    def test_calculate_relationship_strength_from_dict_performance(self) -> None:
        """Dict-based scoring should be efficient."""
        relationship: dict[str, Any] = {
            "type": "partners_with",
            "source_chunks": ["c1", "c2", "c3", "c4", "c5"],
        }
        entity1: dict[str, Any] = {"importance_score": 0.7}
        entity2: dict[str, Any] = {"importance_score": 0.6}

        start = time.perf_counter()
        for _ in range(1000):
            calculate_relationship_strength_from_dict(relationship, entity1, entity2)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 300, f"Dict scoring too slow: {elapsed:.2f}ms for 1000 calculations"

    def test_batch_scoring_performance(self) -> None:
        """Batch scoring many relationships should scale linearly."""
        relationships = [{"chunk_count": i, "type": "related_to"} for i in range(1, 101)]

        start = time.perf_counter()
        for rel in relationships:
            calculate_relationship_strength(
                chunk_count=rel["chunk_count"],
                relationship_type=rel["type"],
            )
        elapsed = (time.perf_counter() - start) * 1000

        # 100 calculations should complete in < 50ms
        assert elapsed < 50, f"Batch scoring too slow: {elapsed:.2f}ms for 100 relationships"


class TestTemporalParsingPerformance:
    """Performance tests for temporal metadata parsing."""

    def test_parse_filename_performance(self) -> None:
        """parse_filename should complete in < 5ms."""
        filenames = [
            "INTC_2024_Q4_earnings.pdf",
            "AAPL_2023_Q3_report.txt",
            "MSFT_2024_Q1_financial.doc",
            "GOOGL_2023_Q2_statement.pdf",
        ]

        start = time.perf_counter()
        for _ in range(250):  # 1000 total parses
            for filename in filenames:
                parse_filename(filename)
        elapsed = (time.perf_counter() - start) * 1000

        # 1000 parses should complete in < 200ms
        assert elapsed < 200, f"Filename parsing too slow: {elapsed:.2f}ms for 1000 parses"

    def test_parse_filename_invalid_performance(self) -> None:
        """Invalid filename parsing should fail fast."""
        invalid_names = [
            "random_file.pdf",
            "no_pattern_here.txt",
            "invalid.doc",
            "",
        ]

        start = time.perf_counter()
        for _ in range(250):
            for name in invalid_names:
                parse_filename(name)
        elapsed = (time.perf_counter() - start) * 1000

        # Invalid parsing should be fast (no complex extraction)
        assert elapsed < 100, f"Invalid parsing too slow: {elapsed:.2f}ms for 1000 parses"


class TestNumericExtractionPerformance:
    """Performance tests for numeric fact extraction."""

    def test_parse_numeric_facts_short_text_performance(self) -> None:
        """Short text numeric parsing should complete in < 20ms."""
        text = "Revenue was $5.2 billion with 15% growth."

        start = time.perf_counter()
        for _ in range(100):
            parse_numeric_facts(text)
        elapsed = (time.perf_counter() - start) * 1000

        # 100 parses of short text should be < 500ms
        assert elapsed < 500, f"Short text parsing too slow: {elapsed:.2f}ms for 100 parses"

    def test_parse_numeric_facts_long_text_performance(self) -> None:
        """Long text numeric parsing should complete in < 100ms per text."""
        # Simulate a paragraph with multiple numeric values
        text = """
        The company reported strong Q4 results with total revenue of $14.2 billion,
        representing a 12.5% increase year-over-year. Operating income reached
        $4.8 billion with margins improving to 33.8%. EPS came in at $1.45,
        beating analyst estimates of $1.38. The company also announced a
        $10 billion stock buyback program and a quarterly dividend of $0.36
        per share, reflecting a 3.4% yield. Cash and investments totaled
        $25.7 billion at quarter end.
        """

        start = time.perf_counter()
        for _ in range(10):
            parse_numeric_facts(text)
        elapsed = (time.perf_counter() - start) * 1000

        # 10 parses of long text should be < 1000ms (< 100ms each)
        assert elapsed < 1000, f"Long text parsing too slow: {elapsed:.2f}ms for 10 parses"

    def test_extract_numeric_facts_json_performance(self) -> None:
        """JSON output should not add significant overhead."""
        text = "Margin improved to 42.5% while revenue hit $8.9B."

        start = time.perf_counter()
        for _ in range(100):
            extract_numeric_facts_json(text)
        elapsed = (time.perf_counter() - start) * 1000

        # JSON serialization should add minimal overhead
        assert elapsed < 600, f"JSON extraction too slow: {elapsed:.2f}ms for 100 extractions"


class TestCombinedOperationsPerformance:
    """Performance tests for combined operations."""

    def test_type_hierarchy_and_scoring_combined(self) -> None:
        """Combined hierarchy lookup and scoring should be efficient."""
        hierarchy = get_type_hierarchy()

        start = time.perf_counter()
        for _ in range(100):
            # Simulate a typical search flow
            _ = hierarchy.expand_type_filter("organization")
            _ = hierarchy.is_subtype_of("company", "organization")
            _ = calculate_relationship_strength(
                chunk_count=5,
                relationship_type="acquired",
                entity1_importance=0.8,
                entity2_importance=0.7,
            )
            _ = hierarchy.build_type_match_cypher("organization")
        elapsed = (time.perf_counter() - start) * 1000

        # 100 combined operations should be < 100ms
        assert elapsed < 100, f"Combined operations too slow: {elapsed:.2f}ms for 100 iterations"

    def test_temporal_and_numeric_combined(self) -> None:
        """Combined temporal and numeric extraction should be efficient."""
        filename = "INTC_2024_Q4_earnings.pdf"
        content = "Intel reported $14.2B revenue with 12% growth rate."

        start = time.perf_counter()
        for _ in range(100):
            _ = parse_filename(filename)
            _ = parse_numeric_facts(content)
        elapsed = (time.perf_counter() - start) * 1000

        # 100 combined extractions should be < 500ms
        assert elapsed < 500, f"Combined extractions too slow: {elapsed:.2f}ms for 100 iterations"

    def test_full_pipeline_simulation_performance(self) -> None:
        """Simulated full pipeline should complete in reasonable time."""
        hierarchy = get_type_hierarchy()
        filename = "AAPL_2024_Q3_report.pdf"
        content = "Apple revenue reached $85.8B with margins at 45.2%."

        start = time.perf_counter()
        for _ in range(50):
            # 1. Parse temporal metadata
            _ = parse_filename(filename)

            # 2. Extract numeric facts
            _ = parse_numeric_facts(content)

            # 3. Expand entity types
            _ = hierarchy.expand_type_filter("organization")
            _ = hierarchy.expand_type_filter("financial_metric")

            # 4. Build Cypher query
            _ = hierarchy.build_type_match_cypher("organization")

            # 5. Score relationships
            _ = calculate_relationship_strength(
                chunk_count=10,
                relationship_type="reported",
                entity1_importance=0.9,
                entity2_importance=0.7,
            )
        elapsed = (time.perf_counter() - start) * 1000

        # 50 full pipeline runs should be < 500ms (< 10ms each)
        assert elapsed < 500, f"Full pipeline too slow: {elapsed:.2f}ms for 50 iterations"


class TestScalabilityPerformance:
    """Tests for scalability with larger datasets."""

    def test_type_hierarchy_all_types_lookup(self) -> None:
        """Looking up all types should scale well."""
        hierarchy = get_type_hierarchy()
        all_parents = hierarchy.get_all_parent_types()

        start = time.perf_counter()
        for _ in range(100):
            for parent in all_parents:
                _ = hierarchy.get_subtypes(parent)
                subtypes = hierarchy.get_subtypes(parent)
                for subtype in subtypes:
                    _ = hierarchy.get_parent_type(subtype)
        elapsed = (time.perf_counter() - start) * 1000

        # Full traversal 100 times should be < 200ms
        assert elapsed < 200, f"Full traversal too slow: {elapsed:.2f}ms"

    def test_batch_relationship_scoring(self) -> None:
        """Scoring many relationships should scale linearly."""
        # Create 1000 relationship scenarios
        scenarios = [
            {
                "chunk_count": (i % 10) + 1,
                "type": ["acquired", "works_at", "related_to", "partners_with"][i % 4],
                "e1_imp": 0.5 + (i % 5) * 0.1,
                "e2_imp": 0.4 + (i % 6) * 0.1,
            }
            for i in range(1000)
        ]

        start = time.perf_counter()
        for scenario in scenarios:
            calculate_relationship_strength(
                chunk_count=scenario["chunk_count"],
                relationship_type=scenario["type"],
                entity1_importance=scenario["e1_imp"],
                entity2_importance=scenario["e2_imp"],
            )
        elapsed = (time.perf_counter() - start) * 1000

        # 1000 scorings should complete in < 500ms
        assert elapsed < 500, f"Batch scoring too slow: {elapsed:.2f}ms for 1000 relationships"

    def test_concurrent_access_simulation(self) -> None:
        """Simulated concurrent access should not degrade performance."""
        hierarchy = get_type_hierarchy()

        # Simulate multiple "users" accessing different operations
        operations = [
            lambda: hierarchy.get_subtypes("organization"),
            lambda: hierarchy.get_parent_type("company"),
            lambda: hierarchy.is_subtype_of("ceo", "person"),
            lambda: hierarchy.expand_type_filter("financial_metric"),
            lambda: calculate_relationship_strength(chunk_count=5, relationship_type="acquired"),
        ]

        start = time.perf_counter()
        for _ in range(200):
            for op in operations:
                op()
        elapsed = (time.perf_counter() - start) * 1000

        # 1000 operations should complete in < 100ms
        assert elapsed < 100, f"Concurrent simulation too slow: {elapsed:.2f}ms"
