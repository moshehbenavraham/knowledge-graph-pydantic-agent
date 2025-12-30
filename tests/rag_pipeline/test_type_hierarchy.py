"""
Unit tests for the TypeHierarchy module.

Tests cover:
- TYPE_HIERARCHY constant structure
- TypeHierarchy class initialization
- get_subtypes() method for all parent types
- get_parent_type() method for known and unknown subtypes
- is_subtype_of() relationship validation
- expand_type_filter() for query construction
- build_type_match_cypher() for Cypher generation
- Case-insensitivity testing
- Edge cases: empty strings, None values, unknown types
"""

import pytest

from src.agentic_rag.graph.type_hierarchy import (
    TYPE_HIERARCHY,
    TypeHierarchy,
    get_type_hierarchy,
)


class TestTypeHierarchyConstant:
    """Tests for the TYPE_HIERARCHY constant."""

    def test_type_hierarchy_is_dict(self) -> None:
        """TYPE_HIERARCHY should be a dictionary."""
        assert isinstance(TYPE_HIERARCHY, dict)

    def test_type_hierarchy_has_expected_parent_types(self) -> None:
        """TYPE_HIERARCHY should contain all expected parent types."""
        expected_parents = {"organization", "financial_metric", "product", "person"}
        actual_parents = set(TYPE_HIERARCHY.keys())
        assert expected_parents == actual_parents

    def test_organization_subtypes(self) -> None:
        """Organization should have expected subtypes."""
        subtypes = TYPE_HIERARCHY["organization"]
        assert "company" in subtypes
        assert "department" in subtypes
        assert "subsidiary" in subtypes
        assert "division" in subtypes

    def test_financial_metric_subtypes(self) -> None:
        """Financial_metric should have expected subtypes."""
        subtypes = TYPE_HIERARCHY["financial_metric"]
        assert "revenue" in subtypes
        assert "profit" in subtypes
        assert "margin" in subtypes
        assert "eps" in subtypes
        assert "ebitda" in subtypes

    def test_product_subtypes(self) -> None:
        """Product should have expected subtypes."""
        subtypes = TYPE_HIERARCHY["product"]
        assert "hardware" in subtypes
        assert "software" in subtypes
        assert "service" in subtypes
        assert "platform" in subtypes

    def test_person_subtypes(self) -> None:
        """Person should have expected subtypes."""
        subtypes = TYPE_HIERARCHY["person"]
        assert "executive" in subtypes
        assert "ceo" in subtypes
        assert "cfo" in subtypes
        assert "analyst" in subtypes


class TestTypeHierarchyClass:
    """Tests for the TypeHierarchy class."""

    @pytest.fixture
    def hierarchy(self) -> TypeHierarchy:
        """Create a TypeHierarchy instance for testing."""
        return TypeHierarchy()

    def test_initialization(self, hierarchy: TypeHierarchy) -> None:
        """TypeHierarchy should initialize correctly."""
        assert hierarchy is not None
        assert isinstance(hierarchy.hierarchy, dict)

    def test_custom_hierarchy(self) -> None:
        """TypeHierarchy should accept custom hierarchy."""
        custom = {"animal": ["dog", "cat", "bird"]}
        hierarchy = TypeHierarchy(hierarchy=custom)
        assert hierarchy.get_subtypes("animal") == ["dog", "cat", "bird"]


class TestGetSubtypes:
    """Tests for the get_subtypes method."""

    @pytest.fixture
    def hierarchy(self) -> TypeHierarchy:
        """Create a TypeHierarchy instance for testing."""
        return TypeHierarchy()

    def test_get_subtypes_organization(self, hierarchy: TypeHierarchy) -> None:
        """get_subtypes should return organization subtypes."""
        subtypes = hierarchy.get_subtypes("organization")
        assert "company" in subtypes
        assert "department" in subtypes
        assert len(subtypes) > 0

    def test_get_subtypes_financial_metric(self, hierarchy: TypeHierarchy) -> None:
        """get_subtypes should return financial_metric subtypes."""
        subtypes = hierarchy.get_subtypes("financial_metric")
        assert "revenue" in subtypes
        assert "profit" in subtypes

    def test_get_subtypes_product(self, hierarchy: TypeHierarchy) -> None:
        """get_subtypes should return product subtypes."""
        subtypes = hierarchy.get_subtypes("product")
        assert "hardware" in subtypes
        assert "software" in subtypes

    def test_get_subtypes_person(self, hierarchy: TypeHierarchy) -> None:
        """get_subtypes should return person subtypes."""
        subtypes = hierarchy.get_subtypes("person")
        assert "executive" in subtypes
        assert "ceo" in subtypes

    def test_get_subtypes_unknown_returns_empty(self, hierarchy: TypeHierarchy) -> None:
        """get_subtypes should return empty list for unknown parent type."""
        subtypes = hierarchy.get_subtypes("unknown_type")
        assert subtypes == []

    def test_get_subtypes_empty_string_returns_empty(self, hierarchy: TypeHierarchy) -> None:
        """get_subtypes should return empty list for empty string."""
        subtypes = hierarchy.get_subtypes("")
        assert subtypes == []

    def test_get_subtypes_case_insensitive(self, hierarchy: TypeHierarchy) -> None:
        """get_subtypes should be case insensitive."""
        lower = hierarchy.get_subtypes("organization")
        upper = hierarchy.get_subtypes("ORGANIZATION")
        mixed = hierarchy.get_subtypes("Organization")
        assert lower == upper == mixed

    def test_get_subtypes_returns_copy(self, hierarchy: TypeHierarchy) -> None:
        """get_subtypes should return a copy, not the original list."""
        subtypes1 = hierarchy.get_subtypes("organization")
        subtypes2 = hierarchy.get_subtypes("organization")
        assert subtypes1 is not subtypes2
        assert subtypes1 == subtypes2


class TestGetParentType:
    """Tests for the get_parent_type method."""

    @pytest.fixture
    def hierarchy(self) -> TypeHierarchy:
        """Create a TypeHierarchy instance for testing."""
        return TypeHierarchy()

    def test_get_parent_type_company(self, hierarchy: TypeHierarchy) -> None:
        """get_parent_type should return organization for company."""
        parent = hierarchy.get_parent_type("company")
        assert parent == "organization"

    def test_get_parent_type_revenue(self, hierarchy: TypeHierarchy) -> None:
        """get_parent_type should return financial_metric for revenue."""
        parent = hierarchy.get_parent_type("revenue")
        assert parent == "financial_metric"

    def test_get_parent_type_hardware(self, hierarchy: TypeHierarchy) -> None:
        """get_parent_type should return product for hardware."""
        parent = hierarchy.get_parent_type("hardware")
        assert parent == "product"

    def test_get_parent_type_ceo(self, hierarchy: TypeHierarchy) -> None:
        """get_parent_type should return person for ceo."""
        parent = hierarchy.get_parent_type("ceo")
        assert parent == "person"

    def test_get_parent_type_parent_returns_itself(self, hierarchy: TypeHierarchy) -> None:
        """get_parent_type should return parent type for parent type itself."""
        assert hierarchy.get_parent_type("organization") == "organization"
        assert hierarchy.get_parent_type("financial_metric") == "financial_metric"

    def test_get_parent_type_unknown_returns_none(self, hierarchy: TypeHierarchy) -> None:
        """get_parent_type should return None for unknown subtype."""
        parent = hierarchy.get_parent_type("unknown_type")
        assert parent is None

    def test_get_parent_type_empty_string_returns_none(self, hierarchy: TypeHierarchy) -> None:
        """get_parent_type should return None for empty string."""
        parent = hierarchy.get_parent_type("")
        assert parent is None

    def test_get_parent_type_case_insensitive(self, hierarchy: TypeHierarchy) -> None:
        """get_parent_type should be case insensitive."""
        assert hierarchy.get_parent_type("COMPANY") == "organization"
        assert hierarchy.get_parent_type("Company") == "organization"
        assert hierarchy.get_parent_type("company") == "organization"


class TestIsSubtypeOf:
    """Tests for the is_subtype_of method."""

    @pytest.fixture
    def hierarchy(self) -> TypeHierarchy:
        """Create a TypeHierarchy instance for testing."""
        return TypeHierarchy()

    def test_is_subtype_of_company_organization(self, hierarchy: TypeHierarchy) -> None:
        """company is a subtype of organization."""
        assert hierarchy.is_subtype_of("company", "organization") is True

    def test_is_subtype_of_revenue_financial_metric(self, hierarchy: TypeHierarchy) -> None:
        """revenue is a subtype of financial_metric."""
        assert hierarchy.is_subtype_of("revenue", "financial_metric") is True

    def test_is_subtype_of_hardware_product(self, hierarchy: TypeHierarchy) -> None:
        """hardware is a subtype of product."""
        assert hierarchy.is_subtype_of("hardware", "product") is True

    def test_is_subtype_of_ceo_person(self, hierarchy: TypeHierarchy) -> None:
        """ceo is a subtype of person."""
        assert hierarchy.is_subtype_of("ceo", "person") is True

    def test_is_subtype_of_parent_is_its_own_subtype(self, hierarchy: TypeHierarchy) -> None:
        """A parent type is its own subtype."""
        assert hierarchy.is_subtype_of("organization", "organization") is True
        assert hierarchy.is_subtype_of("person", "person") is True

    def test_is_subtype_of_cross_category_false(self, hierarchy: TypeHierarchy) -> None:
        """Subtypes from different categories should return False."""
        assert hierarchy.is_subtype_of("company", "person") is False
        assert hierarchy.is_subtype_of("revenue", "product") is False
        assert hierarchy.is_subtype_of("ceo", "organization") is False

    def test_is_subtype_of_unknown_subtype_false(self, hierarchy: TypeHierarchy) -> None:
        """Unknown subtype should return False."""
        assert hierarchy.is_subtype_of("unknown", "organization") is False

    def test_is_subtype_of_unknown_parent_false(self, hierarchy: TypeHierarchy) -> None:
        """Unknown parent should return False."""
        assert hierarchy.is_subtype_of("company", "unknown") is False

    def test_is_subtype_of_empty_strings_false(self, hierarchy: TypeHierarchy) -> None:
        """Empty strings should return False."""
        assert hierarchy.is_subtype_of("", "organization") is False
        assert hierarchy.is_subtype_of("company", "") is False
        assert hierarchy.is_subtype_of("", "") is False

    def test_is_subtype_of_case_insensitive(self, hierarchy: TypeHierarchy) -> None:
        """is_subtype_of should be case insensitive."""
        assert hierarchy.is_subtype_of("COMPANY", "organization") is True
        assert hierarchy.is_subtype_of("company", "ORGANIZATION") is True
        assert hierarchy.is_subtype_of("Company", "Organization") is True


class TestGetAllParentTypes:
    """Tests for the get_all_parent_types method."""

    @pytest.fixture
    def hierarchy(self) -> TypeHierarchy:
        """Create a TypeHierarchy instance for testing."""
        return TypeHierarchy()

    def test_get_all_parent_types(self, hierarchy: TypeHierarchy) -> None:
        """get_all_parent_types should return all parent types."""
        parents = hierarchy.get_all_parent_types()
        assert "organization" in parents
        assert "financial_metric" in parents
        assert "product" in parents
        assert "person" in parents
        assert len(parents) == 4


class TestExpandTypeFilter:
    """Tests for the expand_type_filter method."""

    @pytest.fixture
    def hierarchy(self) -> TypeHierarchy:
        """Create a TypeHierarchy instance for testing."""
        return TypeHierarchy()

    def test_expand_type_filter_parent_type(self, hierarchy: TypeHierarchy) -> None:
        """expand_type_filter should expand parent type to include all subtypes."""
        expanded = hierarchy.expand_type_filter("organization")
        assert "organization" in expanded
        assert "company" in expanded
        assert "department" in expanded
        assert len(expanded) > 1

    def test_expand_type_filter_subtype(self, hierarchy: TypeHierarchy) -> None:
        """expand_type_filter should return single type for subtype."""
        expanded = hierarchy.expand_type_filter("company")
        assert expanded == ["company"]

    def test_expand_type_filter_unknown_type(self, hierarchy: TypeHierarchy) -> None:
        """expand_type_filter should return single type for unknown type."""
        expanded = hierarchy.expand_type_filter("unknown_type")
        assert expanded == ["unknown_type"]

    def test_expand_type_filter_empty_string(self, hierarchy: TypeHierarchy) -> None:
        """expand_type_filter should return empty list for empty string."""
        expanded = hierarchy.expand_type_filter("")
        assert expanded == []

    def test_expand_type_filter_case_insensitive(self, hierarchy: TypeHierarchy) -> None:
        """expand_type_filter should be case insensitive."""
        lower = hierarchy.expand_type_filter("organization")
        upper = hierarchy.expand_type_filter("ORGANIZATION")
        assert lower == upper


class TestBuildTypeMatchCypher:
    """Tests for the build_type_match_cypher method."""

    @pytest.fixture
    def hierarchy(self) -> TypeHierarchy:
        """Create a TypeHierarchy instance for testing."""
        return TypeHierarchy()

    def test_build_type_match_cypher_parent_type(self, hierarchy: TypeHierarchy) -> None:
        """build_type_match_cypher should create valid clause for parent type."""
        clause, params = hierarchy.build_type_match_cypher("organization")
        assert "e.entity_type IN $type_filter" in clause
        assert "type_filter" in params
        assert "organization" in params["type_filter"]
        assert "company" in params["type_filter"]

    def test_build_type_match_cypher_subtype(self, hierarchy: TypeHierarchy) -> None:
        """build_type_match_cypher should create clause for subtype."""
        clause, params = hierarchy.build_type_match_cypher("company")
        assert clause == "e.entity_type IN $type_filter"
        assert params["type_filter"] == ["company"]

    def test_build_type_match_cypher_custom_node_variable(self, hierarchy: TypeHierarchy) -> None:
        """build_type_match_cypher should use custom node variable."""
        clause, _params = hierarchy.build_type_match_cypher("organization", node_variable="entity")
        assert "entity.entity_type IN $type_filter" in clause

    def test_build_type_match_cypher_custom_type_property(self, hierarchy: TypeHierarchy) -> None:
        """build_type_match_cypher should use custom type property."""
        clause, _params = hierarchy.build_type_match_cypher("organization", type_property="type")
        assert "e.type IN $type_filter" in clause

    def test_build_type_match_cypher_empty_string(self, hierarchy: TypeHierarchy) -> None:
        """build_type_match_cypher should return empty for empty string."""
        clause, params = hierarchy.build_type_match_cypher("")
        assert clause == ""
        assert params == {}


class TestGetTypeHierarchySingleton:
    """Tests for the get_type_hierarchy singleton function."""

    def test_get_type_hierarchy_returns_instance(self) -> None:
        """get_type_hierarchy should return a TypeHierarchy instance."""
        hierarchy = get_type_hierarchy()
        assert isinstance(hierarchy, TypeHierarchy)

    def test_get_type_hierarchy_returns_same_instance(self) -> None:
        """get_type_hierarchy should return the same singleton instance."""
        h1 = get_type_hierarchy()
        h2 = get_type_hierarchy()
        assert h1 is h2

    def test_get_type_hierarchy_is_functional(self) -> None:
        """get_type_hierarchy singleton should be fully functional."""
        hierarchy = get_type_hierarchy()
        assert hierarchy.get_subtypes("organization") is not None
        assert hierarchy.get_parent_type("company") == "organization"
        assert hierarchy.is_subtype_of("ceo", "person") is True


class TestEdgeCases:
    """Tests for edge cases and unusual inputs."""

    @pytest.fixture
    def hierarchy(self) -> TypeHierarchy:
        """Create a TypeHierarchy instance for testing."""
        return TypeHierarchy()

    def test_whitespace_handling(self, hierarchy: TypeHierarchy) -> None:
        """Methods should handle whitespace in input."""
        assert hierarchy.get_subtypes("  organization  ") is not None
        assert hierarchy.get_parent_type("  company  ") == "organization"
        assert hierarchy.is_subtype_of("  company  ", "  organization  ") is True

    def test_long_type_name(self, hierarchy: TypeHierarchy) -> None:
        """Methods should handle very long type names."""
        long_name = "a" * 1000
        assert hierarchy.get_subtypes(long_name) == []
        assert hierarchy.get_parent_type(long_name) is None
        assert hierarchy.is_subtype_of(long_name, "organization") is False

    def test_special_characters_in_type(self, hierarchy: TypeHierarchy) -> None:
        """Methods should handle special characters safely."""
        special = "type-with_special.chars!"
        assert hierarchy.get_subtypes(special) == []
        assert hierarchy.get_parent_type(special) is None
        # Should not raise exceptions
        hierarchy.expand_type_filter(special)
        hierarchy.build_type_match_cypher(special)
