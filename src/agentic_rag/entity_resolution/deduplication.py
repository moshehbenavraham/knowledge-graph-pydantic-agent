"""Multi-pass entity deduplication engine.

This module implements the core deduplication logic with three passes:
1. Exact match: Normalized string comparison
2. Fuzzy match: RapidFuzz similarity with 90% threshold
3. Context-based match: Document reference disambiguation

The EntityResolver facade combines all passes for unified access.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import structlog
from neo4j import AsyncDriver
from rapidfuzz import fuzz

from src.agentic_rag.entity_resolution.canonical_names import (
    TICKER_TO_CANONICAL,
    get_canonical_name,
    is_excluded_term,
    normalize_entity_name,
)
from src.agentic_rag.entity_resolution.merge_history import MergeMatchType

logger = structlog.get_logger(__name__)

# Configuration
DEFAULT_FUZZY_THRESHOLD = 90.0  # Minimum similarity score for fuzzy matches
MIN_NAME_LENGTH = 2  # Minimum normalized name length to consider


@dataclass
class Entity:
    """Represents an entity from the knowledge graph."""

    entity_id: str
    name: str
    entity_type: str = ""
    mention_count: int = 0
    document_refs: list[dict[str, Any]] = field(default_factory=list)

    @property
    def normalized_name(self) -> str:
        """Get the normalized form of the entity name."""
        return normalize_entity_name(self.name)

    def get_companies(self) -> set[str]:
        """Extract unique company identifiers from document_refs."""
        companies: set[str] = set()
        for ref in self.document_refs:
            if isinstance(ref, dict) and ref.get("company"):
                companies.add(str(ref["company"]).upper())
        return companies


@dataclass
class DuplicateGroup:
    """A group of entities identified as duplicates."""

    canonical: Entity
    duplicates: list[Entity] = field(default_factory=list)
    match_type: MergeMatchType = MergeMatchType.EXACT
    similarity_score: float = 1.0

    @property
    def total_mentions(self) -> int:
        """Total mention count across all entities in group."""
        return self.canonical.mention_count + sum(e.mention_count for e in self.duplicates)

    def all_entities(self) -> list[Entity]:
        """Get all entities in the group including canonical."""
        return [self.canonical, *self.duplicates]


async def fetch_all_entities(driver: AsyncDriver) -> list[Entity]:
    """Fetch all entities from Neo4j knowledge graph.

    Args:
        driver: Neo4j async driver

    Returns:
        List of Entity objects
    """
    logger.info("Fetching all entities from graph")

    query = """
    MATCH (e:Entity)
    RETURN
        e.uuid AS entity_id,
        e.name AS name,
        e.entity_type AS entity_type,
        e.mention_count AS mention_count,
        e.document_refs AS document_refs
    ORDER BY e.mention_count DESC
    """

    entities: list[Entity] = []
    async with driver.session() as session:
        result = await session.run(query)
        async for record in result:
            entity = Entity(
                entity_id=str(record["entity_id"]),
                name=str(record["name"] or ""),
                entity_type=str(record["entity_type"] or ""),
                mention_count=int(record["mention_count"] or 0),
                document_refs=list(record["document_refs"] or []),
            )
            entities.append(entity)

    logger.info("Fetched entities", count=len(entities))
    return entities


def exact_match_pass(entities: list[Entity]) -> list[DuplicateGroup]:
    """Find duplicates via exact normalized string matching (T010).

    Groups entities that have identical normalized names after:
    - Lowercasing
    - Suffix removal (Inc., Corp., etc.)
    - Whitespace normalization

    Args:
        entities: List of entities to process

    Returns:
        List of DuplicateGroup objects for exact matches
    """
    logger.info("Running exact match pass", entity_count=len(entities))

    # Group by normalized name
    name_groups: dict[str, list[Entity]] = defaultdict(list)
    for entity in entities:
        normalized = entity.normalized_name
        if len(normalized) >= MIN_NAME_LENGTH and not is_excluded_term(entity.name):
            name_groups[normalized].append(entity)

    # Convert groups with multiple entities to DuplicateGroups
    groups: list[DuplicateGroup] = []
    for entity_list in name_groups.values():
        if len(entity_list) > 1:
            # Sort by mention count descending, pick highest as canonical
            sorted_entities = sorted(entity_list, key=lambda e: e.mention_count, reverse=True)
            groups.append(
                DuplicateGroup(
                    canonical=sorted_entities[0],
                    duplicates=sorted_entities[1:],
                    match_type=MergeMatchType.EXACT,
                    similarity_score=1.0,
                )
            )

    logger.info(
        "Exact match pass complete",
        groups_found=len(groups),
        entities_to_merge=sum(len(g.duplicates) for g in groups),
    )
    return groups


def fuzzy_match_pass(
    entities: list[Entity],
    already_matched: set[str],
    threshold: float = DEFAULT_FUZZY_THRESHOLD,
) -> list[DuplicateGroup]:
    """Find duplicates via fuzzy string matching (T011).

    Uses RapidFuzz for efficient similarity computation with configurable
    threshold. Excludes entities already matched in exact pass.

    Args:
        entities: List of entities to process
        already_matched: Set of entity IDs already matched
        threshold: Minimum similarity score (0-100)

    Returns:
        List of DuplicateGroup objects for fuzzy matches
    """
    logger.info(
        "Running fuzzy match pass",
        entity_count=len(entities),
        already_matched=len(already_matched),
        threshold=threshold,
    )

    # Filter to unmatched, valid entities
    candidates = [
        e
        for e in entities
        if e.entity_id not in already_matched
        and len(e.normalized_name) >= MIN_NAME_LENGTH
        and not is_excluded_term(e.name)
    ]

    if len(candidates) < 2:
        return []

    # Build groups using greedy matching
    groups: list[DuplicateGroup] = []
    matched_ids: set[str] = set()

    # Sort by mention count so higher-count entities become canonicals
    candidates_sorted = sorted(candidates, key=lambda e: e.mention_count, reverse=True)

    for i, entity in enumerate(candidates_sorted):
        if entity.entity_id in matched_ids:
            continue

        # Find similar entities
        similar: list[tuple[Entity, float]] = []
        for other in candidates_sorted[i + 1 :]:
            if other.entity_id in matched_ids:
                continue

            score = fuzz.ratio(entity.normalized_name, other.normalized_name)
            if score >= threshold:
                similar.append((other, score))

        if similar:
            # Create group with this entity as canonical
            duplicates = [e for e, _ in similar]
            min_score = min(s for _, s in similar)
            matched_ids.add(entity.entity_id)
            matched_ids.update(e.entity_id for e in duplicates)

            groups.append(
                DuplicateGroup(
                    canonical=entity,
                    duplicates=duplicates,
                    match_type=MergeMatchType.FUZZY,
                    similarity_score=min_score / 100.0,
                )
            )

    logger.info(
        "Fuzzy match pass complete",
        groups_found=len(groups),
        entities_to_merge=sum(len(g.duplicates) for g in groups),
    )
    return groups


def context_match_pass(
    entities: list[Entity],
    already_matched: set[str],
) -> list[DuplicateGroup]:
    """Find duplicates via document reference context (T012).

    Uses the document_refs.company field to identify entities that:
    - Have different names but same company context
    - Are likely the same entity mentioned differently across documents

    Args:
        entities: List of entities to process
        already_matched: Set of entity IDs already matched

    Returns:
        List of DuplicateGroup objects for context matches
    """
    logger.info(
        "Running context match pass",
        entity_count=len(entities),
        already_matched=len(already_matched),
    )

    # Filter to unmatched entities with document_refs
    candidates = [
        e
        for e in entities
        if e.entity_id not in already_matched and e.document_refs and not is_excluded_term(e.name)
    ]

    if len(candidates) < 2:
        return []

    # Group by company identifier from document_refs
    company_groups: dict[str, list[Entity]] = defaultdict(list)
    for entity in candidates:
        for company in entity.get_companies():
            # Only consider if entity name relates to company
            # (e.g., ticker symbol, partial name match)
            normalized = entity.normalized_name
            if (
                company.lower() in normalized
                or normalized in company.lower()
                or get_canonical_name(entity.name.upper())
            ):
                company_groups[company].append(entity)

    # Convert groups to DuplicateGroups
    groups: list[DuplicateGroup] = []
    matched_ids: set[str] = set()

    for company, entity_list in company_groups.items():
        # Filter out already matched in this pass
        entity_list = [e for e in entity_list if e.entity_id not in matched_ids]

        if len(entity_list) > 1:
            # Sort by mention count
            sorted_entities = sorted(entity_list, key=lambda e: e.mention_count, reverse=True)

            # Check if ticker maps to canonical
            canonical = sorted_entities[0]
            ticker_canonical = get_canonical_name(company)
            if ticker_canonical:
                # Use ticker-derived canonical name as reference
                for e in sorted_entities:
                    if e.name == ticker_canonical:
                        canonical = e
                        break

            duplicates = [e for e in sorted_entities if e.entity_id != canonical.entity_id]

            if duplicates:
                matched_ids.add(canonical.entity_id)
                matched_ids.update(e.entity_id for e in duplicates)

                groups.append(
                    DuplicateGroup(
                        canonical=canonical,
                        duplicates=duplicates,
                        match_type=MergeMatchType.CONTEXT,
                        similarity_score=0.85,  # Context matches have lower confidence
                    )
                )

    logger.info(
        "Context match pass complete",
        groups_found=len(groups),
        entities_to_merge=sum(len(g.duplicates) for g in groups),
    )
    return groups


def ticker_resolution_pass(entities: list[Entity]) -> list[DuplicateGroup]:
    """Find entities that should resolve to ticker-based canonical names.

    Uses the TICKER_TO_CANONICAL mapping to identify entities that
    are ticker symbols and should merge with their full company names.

    Args:
        entities: List of entities to process

    Returns:
        List of DuplicateGroup objects for ticker resolutions
    """
    logger.info("Running ticker resolution pass", entity_count=len(entities))

    # Build lookup by normalized name
    name_to_entities: dict[str, list[Entity]] = defaultdict(list)
    for entity in entities:
        name_to_entities[entity.normalized_name].append(entity)

    groups: list[DuplicateGroup] = []

    # Check each known ticker
    for ticker, canonical_name in TICKER_TO_CANONICAL.items():
        ticker_lower = ticker.lower()
        canonical_normalized = normalize_entity_name(canonical_name)

        # Find entities matching ticker or canonical
        ticker_entities = name_to_entities.get(ticker_lower, [])
        canonical_entities = name_to_entities.get(canonical_normalized, [])

        all_entities = ticker_entities + canonical_entities
        if len(all_entities) > 1:
            # Prefer the full canonical name as the canonical entity
            sorted_entities = sorted(
                all_entities,
                key=lambda e: (
                    e.normalized_name == canonical_normalized,
                    e.mention_count,
                ),
                reverse=True,
            )

            groups.append(
                DuplicateGroup(
                    canonical=sorted_entities[0],
                    duplicates=sorted_entities[1:],
                    match_type=MergeMatchType.TICKER,
                    similarity_score=1.0,
                )
            )

    logger.info(
        "Ticker resolution pass complete",
        groups_found=len(groups),
        entities_to_merge=sum(len(g.duplicates) for g in groups),
    )
    return groups


async def find_duplicates(
    driver: AsyncDriver,
    fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
) -> list[DuplicateGroup]:
    """Find all duplicate entities using multi-pass approach.

    Executes passes in order of confidence:
    1. Ticker resolution (known mappings)
    2. Exact match (normalized strings)
    3. Fuzzy match (similarity threshold)
    4. Context match (document references)

    Args:
        driver: Neo4j async driver
        fuzzy_threshold: Minimum similarity for fuzzy matches (0-100)

    Returns:
        List of all DuplicateGroup objects found
    """
    logger.info("Starting duplicate detection", fuzzy_threshold=fuzzy_threshold)

    # Fetch all entities
    entities = await fetch_all_entities(driver)
    if len(entities) < 2:
        logger.info("Insufficient entities for deduplication", count=len(entities))
        return []

    all_groups: list[DuplicateGroup] = []
    matched_ids: set[str] = set()

    # Pass 1: Ticker resolution
    ticker_groups = ticker_resolution_pass(entities)
    all_groups.extend(ticker_groups)
    for group in ticker_groups:
        matched_ids.add(group.canonical.entity_id)
        matched_ids.update(e.entity_id for e in group.duplicates)

    # Pass 2: Exact match
    exact_groups = exact_match_pass([e for e in entities if e.entity_id not in matched_ids])
    all_groups.extend(exact_groups)
    for group in exact_groups:
        matched_ids.add(group.canonical.entity_id)
        matched_ids.update(e.entity_id for e in group.duplicates)

    # Pass 3: Fuzzy match
    fuzzy_groups = fuzzy_match_pass(entities, matched_ids, fuzzy_threshold)
    all_groups.extend(fuzzy_groups)
    for group in fuzzy_groups:
        matched_ids.add(group.canonical.entity_id)
        matched_ids.update(e.entity_id for e in group.duplicates)

    # Pass 4: Context match
    context_groups = context_match_pass(entities, matched_ids)
    all_groups.extend(context_groups)

    logger.info(
        "Duplicate detection complete",
        total_groups=len(all_groups),
        total_entities_to_merge=sum(len(g.duplicates) for g in all_groups),
        ticker_groups=len(ticker_groups),
        exact_groups=len(exact_groups),
        fuzzy_groups=len(fuzzy_groups),
        context_groups=len(context_groups),
    )

    return all_groups


class EntityResolver:
    """Facade for entity resolution operations (T013).

    Provides a unified interface for:
    - Finding duplicate entities
    - Resolving entity names to canonical forms
    - Executing merge operations

    Example:
        resolver = EntityResolver(driver)
        duplicates = await resolver.find_all_duplicates()
        for group in duplicates:
            print(f"Merge {len(group.duplicates)} into {group.canonical.name}")
    """

    def __init__(
        self,
        driver: AsyncDriver,
        fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
    ) -> None:
        """Initialize EntityResolver.

        Args:
            driver: Neo4j async driver
            fuzzy_threshold: Minimum similarity for fuzzy matches (0-100)
        """
        self._driver = driver
        self._fuzzy_threshold = fuzzy_threshold

    async def find_all_duplicates(self) -> list[DuplicateGroup]:
        """Find all duplicate entities using multi-pass approach.

        Returns:
            List of DuplicateGroup objects representing detected duplicates
        """
        return await find_duplicates(self._driver, self._fuzzy_threshold)

    async def find_duplicates_for_entity(self, entity_name: str) -> list[Entity]:
        """Find potential duplicates for a specific entity name.

        Args:
            entity_name: Name to find duplicates for

        Returns:
            List of entities that may be duplicates
        """
        normalized = normalize_entity_name(entity_name)
        if len(normalized) < MIN_NAME_LENGTH:
            return []

        entities = await fetch_all_entities(self._driver)
        duplicates: list[Entity] = []

        for entity in entities:
            if (
                entity.normalized_name == normalized
                or fuzz.ratio(normalized, entity.normalized_name) >= self._fuzzy_threshold
            ):
                duplicates.append(entity)

        return duplicates

    def resolve_name(self, name: str) -> str:
        """Resolve an entity name to its canonical form.

        Applies normalization and ticker lookup to get the best
        canonical representation.

        Args:
            name: Entity name to resolve

        Returns:
            Canonical form of the name
        """
        # Check for ticker symbol first
        canonical = get_canonical_name(name)
        if canonical:
            return canonical

        # Otherwise normalize
        return normalize_entity_name(name)

    async def get_entity_count(self) -> int:
        """Get the total number of entities in the graph.

        Returns:
            Count of Entity nodes
        """
        query = "MATCH (e:Entity) RETURN count(e) AS count"
        async with self._driver.session() as session:
            result = await session.run(query)
            record = await result.single()
            return int(record["count"]) if record else 0

    async def get_duplicate_stats(self) -> dict[str, Any]:
        """Get statistics about potential duplicates.

        Returns:
            Dictionary with duplicate detection statistics
        """
        groups = await self.find_all_duplicates()

        by_type: dict[str, int] = defaultdict(int)
        for group in groups:
            by_type[group.match_type.value] += 1

        return {
            "total_groups": len(groups),
            "total_entities_to_merge": sum(len(g.duplicates) for g in groups),
            "by_match_type": dict(by_type),
            "potential_reduction": sum(len(g.duplicates) for g in groups),
        }
