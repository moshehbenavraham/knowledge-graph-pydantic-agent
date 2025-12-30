"""
Unit tests for ResultMerger.

Tests the normalization of different result types into unified SearchResultItem format.
"""

from unittest.mock import MagicMock

import pytest

from src.agentic_rag.search.result_merger import (
    ResultMerger,
    ResultType,
    SearchResultItem,
)


@pytest.fixture
def merger() -> ResultMerger:
    """Create ResultMerger instance."""
    return ResultMerger()


class TestSearchResultItem:
    """Tests for SearchResultItem dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic SearchResultItem creation."""
        item = SearchResultItem(
            result_type=ResultType.VECTOR_CHUNK,
            title="Test Document",
            content="Test content here",
            relevance_score=0.85,
        )
        assert item.result_type == ResultType.VECTOR_CHUNK
        assert item.title == "Test Document"
        assert item.content == "Test content here"
        assert item.relevance_score == 0.85

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        item = SearchResultItem(
            result_type=ResultType.ENTITY,
            title="Test",
            content="Content",
        )
        assert item.relevance_score == 0.0
        assert item.relationship_strength is None
        assert item.temporal_recency is None
        assert item.entities == []
        assert item.source_documents == []
        assert item.metadata == {}

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        item = SearchResultItem(
            result_type=ResultType.GRAPH_PATH,
            title="Path",
            content="A -> B -> C",
            relevance_score=0.9,
            relationship_strength=0.85,
            entities=["A", "B", "C"],
        )
        result = item.to_dict()
        assert result["result_type"] == "graph_path"
        assert result["title"] == "Path"
        assert result["relevance_score"] == 0.9
        assert result["relationship_strength"] == 0.85
        assert result["entities"] == ["A", "B", "C"]

    def test_combined_score_relevance_only(self) -> None:
        """Test combined score with only relevance."""
        item = SearchResultItem(
            result_type=ResultType.VECTOR_CHUNK,
            title="Test",
            content="Content",
            relevance_score=0.8,
        )
        assert item.combined_score == 0.8

    def test_combined_score_with_relationship(self) -> None:
        """Test combined score with relationship strength."""
        item = SearchResultItem(
            result_type=ResultType.GRAPH_PATH,
            title="Test",
            content="Content",
            relevance_score=0.8,
            relationship_strength=0.6,
        )
        # Weighted average: (0.8*1.0 + 0.6*0.8) / (1.0 + 0.8)
        expected = (0.8 * 1.0 + 0.6 * 0.8) / 1.8
        assert abs(item.combined_score - expected) < 0.01

    def test_combined_score_all_signals(self) -> None:
        """Test combined score with all signals."""
        item = SearchResultItem(
            result_type=ResultType.TEMPORAL_TREND,
            title="Test",
            content="Content",
            relevance_score=0.9,
            relationship_strength=0.8,
            temporal_recency=0.7,
        )
        # All signals contribute to combined score
        assert item.combined_score > 0
        assert item.combined_score <= 1.0


class TestResultMerger:
    """Tests for ResultMerger class."""

    def test_initialization(self, merger: ResultMerger) -> None:
        """Test merger initialization."""
        assert merger is not None
        stats = merger.get_stats()
        assert stats["merges"] == 0

    def test_merge_all_empty(self, merger: ResultMerger) -> None:
        """Test merge_all with no inputs."""
        result = merger.merge_all()
        assert result == []

    def test_normalize_chunks(self, merger: ResultMerger) -> None:
        """Test normalizing vector chunks."""
        mock_chunk = MagicMock()
        mock_chunk.document_title = "Test Doc"
        mock_chunk.content = "Test content"
        mock_chunk.similarity = 0.85
        mock_chunk.entities = ["Intel", "AMD"]
        mock_chunk.document_source = "test.pdf"
        mock_chunk.chunk_id = "chunk-123"
        mock_chunk.document_id = "doc-456"

        items = merger.normalize_chunks([mock_chunk])
        assert len(items) == 1
        assert items[0].result_type == ResultType.VECTOR_CHUNK
        assert items[0].title == "Test Doc"
        assert items[0].relevance_score == 0.85
        assert items[0].entities == ["Intel", "AMD"]

    def test_normalize_paths(self, merger: ResultMerger) -> None:
        """Test normalizing path results."""
        mock_node1 = MagicMock()
        mock_node1.name = "Intel"
        mock_node2 = MagicMock()
        mock_node2.name = "Mobileye"

        mock_path = MagicMock()
        mock_path.nodes = [mock_node1, mock_node2]
        mock_path.cumulative_strength = 0.75
        mock_path.hop_count = 1
        mock_path.source_documents = ["doc1.pdf"]
        mock_path.get_path_summary.return_value = "Intel -> Mobileye"

        items = merger.normalize_paths([mock_path])
        assert len(items) == 1
        assert items[0].result_type == ResultType.GRAPH_PATH
        assert items[0].title == "Intel -> Mobileye"
        assert items[0].relationship_strength == 0.75
        assert "Intel" in items[0].entities
        assert "Mobileye" in items[0].entities

    def test_normalize_trends(self, merger: ResultMerger) -> None:
        """Test normalizing trend results."""
        mock_dp = MagicMock()
        mock_dp.year = 2024

        mock_direction = MagicMock()
        mock_direction.value = "increasing"

        mock_trend = MagicMock()
        mock_trend.entity = "Intel"
        mock_trend.metric = "revenue"
        mock_trend.direction = mock_direction
        mock_trend.percent_change = 15.5
        mock_trend.time_span = "2020-2024"
        mock_trend.data_points = [mock_dp]
        mock_trend.get_summary.return_value = "Intel revenue increased 15.5%"

        items = merger.normalize_trends([mock_trend])
        assert len(items) == 1
        assert items[0].result_type == ResultType.TEMPORAL_TREND
        assert "Intel" in items[0].title
        assert "revenue" in items[0].title
        assert items[0].temporal_recency is not None

    def test_normalize_comparisons(self, merger: ResultMerger) -> None:
        """Test normalizing comparison results."""
        mock_entity1 = MagicMock()
        mock_entity1.entity_name = "Intel"
        mock_entity2 = MagicMock()
        mock_entity2.entity_name = "AMD"

        mock_comparison = MagicMock()
        mock_comparison.entities = [mock_entity1, mock_entity2]
        mock_comparison.metric = "revenue"
        mock_comparison.comparison_valid = True
        mock_comparison.ranking = ["AMD", "Intel"]
        mock_comparison.get_summary.return_value = "AMD leads Intel in revenue"

        items = merger.normalize_comparisons([mock_comparison])
        assert len(items) == 1
        assert items[0].result_type == ResultType.ENTITY_COMPARISON
        assert "Intel" in items[0].entities
        assert "AMD" in items[0].entities
        assert items[0].relevance_score == 0.8  # Valid comparison

    def test_merge_all_multiple_types(self, merger: ResultMerger) -> None:
        """Test merging multiple result types."""
        mock_chunk = MagicMock()
        mock_chunk.document_title = "Test"
        mock_chunk.content = "Content"
        mock_chunk.similarity = 0.9
        mock_chunk.entities = []
        mock_chunk.document_source = ""
        mock_chunk.chunk_id = "1"
        mock_chunk.document_id = "1"

        mock_node = MagicMock()
        mock_node.name = "Intel"

        mock_path = MagicMock()
        mock_path.nodes = [mock_node]
        mock_path.cumulative_strength = 0.8
        mock_path.hop_count = 1
        mock_path.source_documents = []
        mock_path.get_path_summary.return_value = "Intel"

        items = merger.merge_all(chunks=[mock_chunk], paths=[mock_path])
        assert len(items) == 2
        types = {item.result_type for item in items}
        assert ResultType.VECTOR_CHUNK in types
        assert ResultType.GRAPH_PATH in types

    def test_deduplication(self, merger: ResultMerger) -> None:
        """Test that duplicate items are removed."""
        item1 = SearchResultItem(
            result_type=ResultType.VECTOR_CHUNK,
            title="Same Title",
            content="Content 1",
            relevance_score=0.9,
            entities=["Intel"],
        )
        item2 = SearchResultItem(
            result_type=ResultType.VECTOR_CHUNK,
            title="Same Title",
            content="Content 2",
            relevance_score=0.8,
            entities=["Intel"],
        )

        # Test internal deduplication
        unique = merger._deduplicate([item1, item2])
        assert len(unique) == 1

    def test_stats_tracking(self, merger: ResultMerger) -> None:
        """Test statistics tracking."""
        mock_chunk = MagicMock()
        mock_chunk.document_title = "Test"
        mock_chunk.content = "Content"
        mock_chunk.similarity = 0.9
        mock_chunk.entities = []
        mock_chunk.document_source = ""
        mock_chunk.chunk_id = "1"
        mock_chunk.document_id = "1"

        merger.merge_all(chunks=[mock_chunk])
        stats = merger.get_stats()
        assert stats["merges"] == 1
        assert stats["chunks_merged"] == 1

    def test_error_handling(self, merger: ResultMerger) -> None:
        """Test graceful error handling."""

        # Pass an object that will cause an error during normalization
        class BadObject:
            @property
            def document_title(self) -> str:
                raise ValueError("Test error")

        items = merger.normalize_chunks([BadObject()])
        # Should not raise, just skip invalid items
        assert len(items) == 0


class TestResultType:
    """Tests for ResultType enum."""

    def test_all_types_exist(self) -> None:
        """Test that all expected result types exist."""
        assert ResultType.VECTOR_CHUNK
        assert ResultType.GRAPH_PATH
        assert ResultType.TEMPORAL_TREND
        assert ResultType.ENTITY_COMPARISON
        assert ResultType.ENTITY
        assert ResultType.FACT

    def test_string_values(self) -> None:
        """Test result type string values."""
        assert ResultType.VECTOR_CHUNK.value == "vector_chunk"
        assert ResultType.GRAPH_PATH.value == "graph_path"
        assert ResultType.TEMPORAL_TREND.value == "temporal_trend"
        assert ResultType.ENTITY_COMPARISON.value == "entity_comparison"
