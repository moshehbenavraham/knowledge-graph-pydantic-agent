"""
Unit tests for graph filter components.

Tests filter rendering, state management, and value conversion.
"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import patch

from src.ui.components.graph_filters import (
    DEFAULT_ENTITY_TYPES,
    DEFAULT_RELATIONSHIP_TYPES,
    GraphFilterState,
    convert_to_datetime,
)


class TestGraphFilterState:
    """Tests for GraphFilterState dataclass."""

    def test_default_initialization(self) -> None:
        """Test GraphFilterState default values."""
        state = GraphFilterState()

        assert state.search_term == ""
        assert state.entity_types == []
        assert state.relationship_types == []
        assert state.min_strength == 0.3
        assert state.start_date is None
        assert state.end_date is None
        assert state.max_nodes == 100
        assert state.max_depth == 1

    def test_custom_initialization(self) -> None:
        """Test GraphFilterState with custom values."""
        state = GraphFilterState(
            search_term="test",
            entity_types=["company"],
            relationship_types=["acquired"],
            min_strength=0.5,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            max_nodes=50,
            max_depth=2,
        )

        assert state.search_term == "test"
        assert state.entity_types == ["company"]
        assert state.relationship_types == ["acquired"]
        assert state.min_strength == 0.5
        assert state.start_date == date(2024, 1, 1)
        assert state.end_date == date(2024, 12, 31)
        assert state.max_nodes == 50
        assert state.max_depth == 2

    def test_to_dict(self) -> None:
        """Test GraphFilterState.to_dict() method."""
        state = GraphFilterState(
            search_term="test",
            entity_types=["company"],
            min_strength=0.7,
        )

        as_dict = state.to_dict()

        assert as_dict["search_term"] == "test"
        assert as_dict["entity_types"] == ["company"]
        assert as_dict["min_strength"] == 0.7
        assert "start_date" in as_dict
        assert "end_date" in as_dict

    def test_to_dict_with_dates(self) -> None:
        """Test GraphFilterState.to_dict() with date values."""
        state = GraphFilterState(
            start_date=date(2024, 6, 15),
            end_date=date(2024, 12, 31),
        )

        as_dict = state.to_dict()

        assert as_dict["start_date"] == "2024-06-15"
        assert as_dict["end_date"] == "2024-12-31"

    def test_to_dict_without_dates(self) -> None:
        """Test GraphFilterState.to_dict() without dates."""
        state = GraphFilterState()

        as_dict = state.to_dict()

        assert as_dict["start_date"] is None
        assert as_dict["end_date"] is None


class TestGraphFilterStateFromSessionState:
    """Tests for GraphFilterState.from_session_state method."""

    def test_from_session_state_defaults(self) -> None:
        """Test from_session_state with empty session state."""
        mock_session_state = {}

        with patch("streamlit.session_state", mock_session_state):
            state = GraphFilterState.from_session_state()

            assert state.search_term == ""
            assert state.entity_types == []
            assert state.min_strength == 0.3

    def test_from_session_state_with_values(self) -> None:
        """Test from_session_state with populated session state."""
        mock_session_state = {
            "graph_filter_search_term": "Intel",
            "graph_filter_entity_types": ["company"],
            "graph_filter_min_strength": 0.8,
            "graph_filter_max_nodes": 75,
        }

        with patch("streamlit.session_state", mock_session_state):
            state = GraphFilterState.from_session_state()

            assert state.search_term == "Intel"
            assert state.entity_types == ["company"]
            assert state.min_strength == 0.8
            assert state.max_nodes == 75

    def test_from_session_state_with_custom_prefix(self) -> None:
        """Test from_session_state with custom prefix."""
        mock_session_state = {
            "custom_search_term": "AMD",
            "custom_entity_types": ["organization"],
        }

        with patch("streamlit.session_state", mock_session_state):
            state = GraphFilterState.from_session_state(prefix="custom")

            assert state.search_term == "AMD"
            assert state.entity_types == ["organization"]


class TestConvertToDatetime:
    """Tests for convert_to_datetime helper function."""

    def test_convert_none(self) -> None:
        """Test converting None returns None."""
        result = convert_to_datetime(None)
        assert result is None

    def test_convert_date(self) -> None:
        """Test converting date to datetime."""
        d = date(2024, 6, 15)
        result = convert_to_datetime(d)

        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15
        assert result.hour == 0
        assert result.minute == 0

    def test_convert_date_start_of_day(self) -> None:
        """Test that converted datetime is at start of day."""
        d = date(2024, 1, 1)
        result = convert_to_datetime(d)

        assert result is not None
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0


class TestDefaultEntityTypes:
    """Tests for DEFAULT_ENTITY_TYPES constant."""

    def test_contains_common_types(self) -> None:
        """Test DEFAULT_ENTITY_TYPES contains common entity types."""
        common_types = ["company", "person", "organization", "product", "technology"]

        for entity_type in common_types:
            assert entity_type in DEFAULT_ENTITY_TYPES

    def test_all_lowercase(self) -> None:
        """Test all entity types are lowercase."""
        for entity_type in DEFAULT_ENTITY_TYPES:
            assert entity_type == entity_type.lower()

    def test_no_duplicates(self) -> None:
        """Test no duplicate entity types."""
        assert len(DEFAULT_ENTITY_TYPES) == len(set(DEFAULT_ENTITY_TYPES))


class TestDefaultRelationshipTypes:
    """Tests for DEFAULT_RELATIONSHIP_TYPES constant."""

    def test_contains_common_types(self) -> None:
        """Test DEFAULT_RELATIONSHIP_TYPES contains common relationship types."""
        common_types = ["acquired", "employs", "partnered_with", "related_to"]

        for rel_type in common_types:
            assert rel_type in DEFAULT_RELATIONSHIP_TYPES

    def test_all_lowercase(self) -> None:
        """Test all relationship types are lowercase."""
        for rel_type in DEFAULT_RELATIONSHIP_TYPES:
            assert rel_type == rel_type.lower()

    def test_no_duplicates(self) -> None:
        """Test no duplicate relationship types."""
        assert len(DEFAULT_RELATIONSHIP_TYPES) == len(set(DEFAULT_RELATIONSHIP_TYPES))


class TestFilterStateValidation:
    """Tests for GraphFilterState validation scenarios."""

    def test_strength_bounds(self) -> None:
        """Test min_strength value bounds."""
        # Valid range
        state = GraphFilterState(min_strength=0.0)
        assert state.min_strength == 0.0

        state = GraphFilterState(min_strength=1.0)
        assert state.min_strength == 1.0

        state = GraphFilterState(min_strength=0.5)
        assert state.min_strength == 0.5

    def test_max_depth_values(self) -> None:
        """Test max_depth valid values."""
        for depth in [1, 2, 3]:
            state = GraphFilterState(max_depth=depth)
            assert state.max_depth == depth

    def test_max_nodes_values(self) -> None:
        """Test max_nodes valid values."""
        for nodes in [10, 50, 100, 200]:
            state = GraphFilterState(max_nodes=nodes)
            assert state.max_nodes == nodes

    def test_empty_lists_are_valid(self) -> None:
        """Test that empty lists are valid for filters."""
        state = GraphFilterState(
            entity_types=[],
            relationship_types=[],
        )

        assert state.entity_types == []
        assert state.relationship_types == []


class TestFilterStateEquality:
    """Tests for GraphFilterState equality."""

    def test_equal_states(self) -> None:
        """Test two equal states."""
        state1 = GraphFilterState(
            search_term="test",
            entity_types=["company"],
            min_strength=0.5,
        )
        state2 = GraphFilterState(
            search_term="test",
            entity_types=["company"],
            min_strength=0.5,
        )

        assert state1.to_dict() == state2.to_dict()

    def test_different_states(self) -> None:
        """Test two different states."""
        state1 = GraphFilterState(search_term="test1")
        state2 = GraphFilterState(search_term="test2")

        assert state1.to_dict() != state2.to_dict()


class TestFilterStateSerialization:
    """Tests for GraphFilterState serialization."""

    def test_round_trip_serialization(self) -> None:
        """Test that state can be serialized and deserialized."""
        original = GraphFilterState(
            search_term="Intel",
            entity_types=["company", "person"],
            relationship_types=["acquired"],
            min_strength=0.7,
            max_nodes=50,
            max_depth=2,
        )

        as_dict = original.to_dict()

        # Verify all fields are in dict
        assert as_dict["search_term"] == "Intel"
        assert as_dict["entity_types"] == ["company", "person"]
        assert as_dict["relationship_types"] == ["acquired"]
        assert as_dict["min_strength"] == 0.7
        assert as_dict["max_nodes"] == 50
        assert as_dict["max_depth"] == 2

    def test_json_serializable(self) -> None:
        """Test that to_dict output is JSON serializable."""
        import json

        state = GraphFilterState(
            search_term="test",
            start_date=date(2024, 1, 1),
        )

        as_dict = state.to_dict()

        # Should not raise
        json_str = json.dumps(as_dict)
        assert isinstance(json_str, str)

        # Should round-trip
        parsed = json.loads(json_str)
        assert parsed["search_term"] == "test"
        assert parsed["start_date"] == "2024-01-01"
