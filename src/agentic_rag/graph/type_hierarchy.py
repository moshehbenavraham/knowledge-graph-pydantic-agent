"""
Entity type hierarchy for semantic type grouping in knowledge graph queries.

This module provides hierarchical type categorization enabling queries like
"all organizations" to match companies, departments, and subsidiaries automatically.
The hierarchy is static (domain-invariant) for performance and simplicity.

Key components:
- TYPE_HIERARCHY: Static mapping of parent types to subtypes
- TypeHierarchy: Class with methods for type lookup and query construction
- Cypher query builder for hierarchical type matching
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# Static type hierarchy mapping: parent_type -> list of subtypes
# All types are lowercase for case-insensitive matching
TYPE_HIERARCHY: dict[str, list[str]] = {
    "organization": [
        "company",
        "department",
        "subsidiary",
        "division",
        "corporation",
        "enterprise",
        "firm",
        "agency",
        "institution",
    ],
    "financial_metric": [
        "revenue",
        "profit",
        "margin",
        "growth_rate",
        "eps",
        "ebitda",
        "income",
        "expense",
        "cost",
        "earnings",
        "cash_flow",
    ],
    "product": [
        "hardware",
        "software",
        "service",
        "platform",
        "solution",
        "application",
        "device",
        "system",
    ],
    "person": [
        "executive",
        "analyst",
        "employee",
        "ceo",
        "cfo",
        "cto",
        "director",
        "manager",
        "founder",
        "chairman",
    ],
}

# Build reverse lookup for efficient parent type resolution
_SUBTYPE_TO_PARENT: dict[str, str] = {}
for parent, subtypes in TYPE_HIERARCHY.items():
    for subtype in subtypes:
        _SUBTYPE_TO_PARENT[subtype.lower()] = parent.lower()
    # Parent type maps to itself
    _SUBTYPE_TO_PARENT[parent.lower()] = parent.lower()


@dataclass
class TypeHierarchy:
    """
    Entity type hierarchy manager for semantic type grouping.

    Provides methods to navigate the type hierarchy and build Cypher queries
    that match entities by parent type (e.g., "organization" matches "company").

    The hierarchy is immutable and case-insensitive for consistent behavior.

    Attributes:
        hierarchy: Mapping of parent types to their subtypes

    Example:
        >>> th = TypeHierarchy()
        >>> th.get_subtypes("organization")
        ['company', 'department', 'subsidiary', 'division', ...]
        >>> th.get_parent_type("company")
        'organization'
        >>> th.is_subtype_of("company", "organization")
        True
    """

    hierarchy: dict[str, list[str]] = field(default_factory=lambda: TYPE_HIERARCHY.copy())

    def __post_init__(self) -> None:
        """Initialize reverse lookup and validate hierarchy."""
        # Build instance-level reverse lookup
        self._subtype_to_parent: dict[str, str] = {}
        for parent, subtypes in self.hierarchy.items():
            parent_lower = parent.lower()
            for subtype in subtypes:
                self._subtype_to_parent[subtype.lower()] = parent_lower
            # Parent type maps to itself
            self._subtype_to_parent[parent_lower] = parent_lower

        logger.debug(
            "TypeHierarchy initialized",
            parent_types=list(self.hierarchy.keys()),
            total_subtypes=sum(len(st) for st in self.hierarchy.values()),
        )

    def get_subtypes(self, parent_type: str) -> list[str]:
        """
        Get all subtypes for a given parent type.

        Args:
            parent_type: The parent type category (e.g., "organization")

        Returns:
            List of subtype strings, empty list if parent_type not found

        Example:
            >>> th = TypeHierarchy()
            >>> th.get_subtypes("organization")
            ['company', 'department', 'subsidiary', 'division', ...]
            >>> th.get_subtypes("unknown")
            []
        """
        if not parent_type:
            logger.debug("get_subtypes called with empty parent_type")
            return []

        normalized = parent_type.lower().strip()
        subtypes = self.hierarchy.get(normalized, [])

        logger.debug(
            "get_subtypes",
            parent_type=normalized,
            subtypes_count=len(subtypes),
        )

        return subtypes.copy()

    def get_parent_type(self, subtype: str) -> str | None:
        """
        Get the parent type for a given subtype.

        Args:
            subtype: The subtype to look up (e.g., "company")

        Returns:
            Parent type string, or None if subtype not found in hierarchy

        Example:
            >>> th = TypeHierarchy()
            >>> th.get_parent_type("company")
            'organization'
            >>> th.get_parent_type("revenue")
            'financial_metric'
            >>> th.get_parent_type("unknown")
            None
        """
        if not subtype:
            logger.debug("get_parent_type called with empty subtype")
            return None

        normalized = subtype.lower().strip()
        parent = self._subtype_to_parent.get(normalized)

        logger.debug(
            "get_parent_type",
            subtype=normalized,
            parent_type=parent,
        )

        return parent

    def is_subtype_of(self, subtype: str, parent_type: str) -> bool:
        """
        Check if a type is a subtype of a given parent type.

        This is true if:
        - subtype is in the parent_type's subtype list, OR
        - subtype equals parent_type (a type is its own subtype)

        Args:
            subtype: The potential subtype (e.g., "company")
            parent_type: The parent type to check against (e.g., "organization")

        Returns:
            True if subtype belongs to parent_type category, False otherwise

        Example:
            >>> th = TypeHierarchy()
            >>> th.is_subtype_of("company", "organization")
            True
            >>> th.is_subtype_of("organization", "organization")
            True
            >>> th.is_subtype_of("revenue", "organization")
            False
        """
        if not subtype or not parent_type:
            logger.debug(
                "is_subtype_of called with empty values",
                subtype=subtype,
                parent_type=parent_type,
            )
            return False

        subtype_normalized = subtype.lower().strip()
        parent_normalized = parent_type.lower().strip()

        # Check if subtype's parent matches the given parent_type
        actual_parent = self._subtype_to_parent.get(subtype_normalized)
        result = actual_parent == parent_normalized

        logger.debug(
            "is_subtype_of",
            subtype=subtype_normalized,
            parent_type=parent_normalized,
            actual_parent=actual_parent,
            result=result,
        )

        return result

    def get_all_parent_types(self) -> list[str]:
        """
        Get all parent type names in the hierarchy.

        Returns:
            List of parent type strings

        Example:
            >>> th = TypeHierarchy()
            >>> th.get_all_parent_types()
            ['organization', 'financial_metric', 'product', 'person']
        """
        return list(self.hierarchy.keys())

    def expand_type_filter(self, entity_type: str) -> list[str]:
        """
        Expand a type filter to include all matching types.

        If entity_type is a parent type, returns all its subtypes plus itself.
        If entity_type is a subtype or unknown, returns just that type.

        Args:
            entity_type: Type to expand (parent or subtype)

        Returns:
            List of all types that should match the filter

        Example:
            >>> th = TypeHierarchy()
            >>> th.expand_type_filter("organization")
            ['organization', 'company', 'department', 'subsidiary', ...]
            >>> th.expand_type_filter("company")
            ['company']
        """
        if not entity_type:
            logger.debug("expand_type_filter called with empty entity_type")
            return []

        normalized = entity_type.lower().strip()

        # Check if this is a parent type
        if normalized in self.hierarchy:
            expanded = [normalized] + self.hierarchy[normalized]
            logger.debug(
                "expand_type_filter expanded parent type",
                entity_type=normalized,
                expanded_count=len(expanded),
            )
            return expanded

        # Not a parent type, return as-is
        logger.debug(
            "expand_type_filter returning single type",
            entity_type=normalized,
        )
        return [normalized]

    def build_type_match_cypher(
        self,
        entity_type: str,
        node_variable: str = "e",
        type_property: str = "entity_type",
    ) -> tuple[str, dict[str, Any]]:
        """
        Build Cypher WHERE clause for type matching with hierarchy expansion.

        Generates parameterized Cypher that matches entities whose type
        is in the expanded type list (for parent types) or exact match
        (for specific types).

        Args:
            entity_type: Type to match (can be parent or specific type)
            node_variable: Cypher node variable name (default: "e")
            type_property: Property name holding entity type (default: "entity_type")

        Returns:
            Tuple of (WHERE clause string, parameters dict)

        Example:
            >>> th = TypeHierarchy()
            >>> clause, params = th.build_type_match_cypher("organization")
            >>> print(clause)
            e.entity_type IN $type_filter
            >>> print(params)
            {'type_filter': ['organization', 'company', 'department', ...]}
        """
        if not entity_type:
            logger.warning("build_type_match_cypher called with empty entity_type")
            return "", {}

        expanded_types = self.expand_type_filter(entity_type)

        # Build parameterized query
        clause = f"{node_variable}.{type_property} IN $type_filter"
        params: dict[str, Any] = {"type_filter": expanded_types}

        logger.debug(
            "build_type_match_cypher",
            entity_type=entity_type,
            expanded_types_count=len(expanded_types),
            clause=clause,
        )

        return clause, params


# Module-level singleton for convenience
_default_hierarchy: TypeHierarchy | None = None


def get_type_hierarchy() -> TypeHierarchy:
    """
    Get the default TypeHierarchy singleton.

    Returns:
        TypeHierarchy instance with default configuration

    Example:
        >>> hierarchy = get_type_hierarchy()
        >>> hierarchy.get_subtypes("person")
        ['executive', 'analyst', 'employee', 'ceo', ...]
    """
    global _default_hierarchy
    if _default_hierarchy is None:
        _default_hierarchy = TypeHierarchy()
    return _default_hierarchy
