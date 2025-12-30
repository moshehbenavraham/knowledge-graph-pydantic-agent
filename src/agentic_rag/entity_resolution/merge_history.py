"""Merge history logging and rollback support for entity deduplication.

This module provides:
- Pydantic models for merge operations
- Logging of merge operations to Neo4j
- Retrieval and rollback capabilities

All merge operations are logged to enable auditing and potential rollback.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog
from neo4j import AsyncDriver
from pydantic import BaseModel, ConfigDict, Field, field_serializer

logger = structlog.get_logger(__name__)


class MergeStatus(str, Enum):
    """Status of a merge operation."""

    PENDING = "pending"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class MergeMatchType(str, Enum):
    """Type of match that triggered the merge."""

    EXACT = "exact"
    FUZZY = "fuzzy"
    CONTEXT = "context"
    TICKER = "ticker"
    MANUAL = "manual"


class MergedEntity(BaseModel):
    """Information about an entity that was merged into another."""

    entity_id: str = Field(..., description="UUID of the merged entity")
    name: str = Field(..., description="Original name of the entity")
    entity_type: str = Field(default="", description="Entity type (e.g., COMPANY)")
    mention_count: int = Field(default=0, description="Mention count before merge")
    document_refs: list[dict[str, Any]] = Field(
        default_factory=list, description="Document references before merge"
    )
    relationship_count: int = Field(default=0, description="Number of relationships transferred")


class MergeOperation(BaseModel):
    """Record of a single entity merge operation.

    Captures all information needed to audit or rollback a merge.
    """

    merge_id: str = Field(..., description="Unique identifier for this merge")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the merge was performed",
    )
    status: MergeStatus = Field(
        default=MergeStatus.PENDING, description="Current status of the merge"
    )
    match_type: MergeMatchType = Field(..., description="How the duplicate was identified")
    similarity_score: float = Field(
        default=1.0, description="Similarity score (1.0 for exact matches)"
    )

    # Canonical (target) entity
    canonical_id: str = Field(..., description="UUID of the canonical entity")
    canonical_name: str = Field(..., description="Name of the canonical entity")

    # Merged (source) entities
    merged_entities: list[MergedEntity] = Field(
        default_factory=list, description="Entities merged into the canonical"
    )

    # Metadata
    user: str = Field(default="system", description="User who initiated the merge")
    notes: str = Field(default="", description="Optional notes about the merge")

    model_config = ConfigDict(ser_json_timedelta="iso8601")

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        """Serialize datetime to ISO format string."""
        return value.isoformat()


class MergeHistory:
    """Manages merge operation history in Neo4j.

    Provides logging, retrieval, and rollback capabilities for entity merges.
    Merge history is stored as MergeOperation nodes in Neo4j.
    """

    def __init__(self, driver: AsyncDriver) -> None:
        """Initialize MergeHistory with Neo4j driver.

        Args:
            driver: Async Neo4j driver instance
        """
        self._driver = driver

    async def log_merge(self, operation: MergeOperation) -> str:
        """Log a merge operation to Neo4j.

        Creates a MergeOperation node with all merge details for auditing
        and potential rollback.

        Args:
            operation: The merge operation to log

        Returns:
            The merge_id of the logged operation

        Raises:
            Exception: If logging fails
        """
        logger.info(
            "Logging merge operation",
            merge_id=operation.merge_id,
            canonical=operation.canonical_name,
            merged_count=len(operation.merged_entities),
        )

        query = """
        CREATE (m:MergeOperation {
            merge_id: $merge_id,
            timestamp: $timestamp,
            status: $status,
            match_type: $match_type,
            similarity_score: $similarity_score,
            canonical_id: $canonical_id,
            canonical_name: $canonical_name,
            merged_entities: $merged_entities,
            user_initiated: $user,
            notes: $notes
        })
        RETURN m.merge_id AS merge_id
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                merge_id=operation.merge_id,
                timestamp=operation.timestamp.isoformat(),
                status=operation.status.value,
                match_type=operation.match_type.value,
                similarity_score=operation.similarity_score,
                canonical_id=operation.canonical_id,
                canonical_name=operation.canonical_name,
                merged_entities=[e.model_dump() for e in operation.merged_entities],
                user=operation.user,
                notes=operation.notes,
            )
            record = await result.single()

            if record:
                logger.info("Merge operation logged", merge_id=record["merge_id"])
                return str(record["merge_id"])

            raise RuntimeError("Failed to log merge operation")

    async def update_status(self, merge_id: str, status: MergeStatus, notes: str = "") -> bool:
        """Update the status of a merge operation.

        Args:
            merge_id: The merge operation ID
            status: New status to set
            notes: Optional notes about the status change

        Returns:
            True if update succeeded, False otherwise
        """
        logger.info("Updating merge status", merge_id=merge_id, status=status.value)

        query = """
        MATCH (m:MergeOperation {merge_id: $merge_id})
        SET m.status = $status,
            m.updated_at = $updated_at,
            m.notes = m.notes + $notes_append
        RETURN m.merge_id AS merge_id
        """

        notes_append = f"\n[{datetime.now(UTC).isoformat()}] {notes}" if notes else ""

        async with self._driver.session() as session:
            result = await session.run(
                query,
                merge_id=merge_id,
                status=status.value,
                updated_at=datetime.now(UTC).isoformat(),
                notes_append=notes_append,
            )
            record = await result.single()
            return record is not None

    async def get_merge(self, merge_id: str) -> MergeOperation | None:
        """Retrieve a specific merge operation by ID.

        Args:
            merge_id: The merge operation ID

        Returns:
            MergeOperation if found, None otherwise
        """
        query = """
        MATCH (m:MergeOperation {merge_id: $merge_id})
        RETURN m
        """

        async with self._driver.session() as session:
            result = await session.run(query, merge_id=merge_id)
            record = await result.single()

            if not record:
                return None

            node = record["m"]
            return self._node_to_operation(dict(node))

    async def get_merges_by_canonical(
        self, canonical_id: str, limit: int = 100
    ) -> list[MergeOperation]:
        """Get all merge operations for a canonical entity.

        Args:
            canonical_id: UUID of the canonical entity
            limit: Maximum number of operations to return

        Returns:
            List of merge operations for the entity
        """
        query = """
        MATCH (m:MergeOperation {canonical_id: $canonical_id})
        RETURN m
        ORDER BY m.timestamp DESC
        LIMIT $limit
        """

        operations: list[MergeOperation] = []
        async with self._driver.session() as session:
            result = await session.run(query, canonical_id=canonical_id, limit=limit)
            async for record in result:
                node = record["m"]
                op = self._node_to_operation(dict(node))
                if op:
                    operations.append(op)

        return operations

    async def get_recent_merges(
        self,
        limit: int = 50,
        status: MergeStatus | None = None,
    ) -> list[MergeOperation]:
        """Get recent merge operations.

        Args:
            limit: Maximum number of operations to return
            status: Optional filter by status

        Returns:
            List of recent merge operations
        """
        if status:
            query = """
            MATCH (m:MergeOperation {status: $status})
            RETURN m
            ORDER BY m.timestamp DESC
            LIMIT $limit
            """
            params = {"status": status.value, "limit": limit}
        else:
            query = """
            MATCH (m:MergeOperation)
            RETURN m
            ORDER BY m.timestamp DESC
            LIMIT $limit
            """
            params = {"limit": limit}

        operations: list[MergeOperation] = []
        async with self._driver.session() as session:
            result = await session.run(query, dict(params))
            async for record in result:
                node = record["m"]
                op = self._node_to_operation(dict(node))
                if op:
                    operations.append(op)

        return operations

    async def get_merge_stats(self) -> dict[str, Any]:
        """Get aggregate statistics about merge operations.

        Returns:
            Dictionary with merge statistics
        """
        query = """
        MATCH (m:MergeOperation)
        RETURN
            count(m) AS total_merges,
            count(CASE WHEN m.status = 'completed' THEN 1 END) AS completed,
            count(CASE WHEN m.status = 'rolled_back' THEN 1 END) AS rolled_back,
            count(CASE WHEN m.status = 'failed' THEN 1 END) AS failed,
            count(CASE WHEN m.match_type = 'exact' THEN 1 END) AS exact_matches,
            count(CASE WHEN m.match_type = 'fuzzy' THEN 1 END) AS fuzzy_matches,
            count(CASE WHEN m.match_type = 'context' THEN 1 END) AS context_matches,
            count(CASE WHEN m.match_type = 'ticker' THEN 1 END) AS ticker_matches
        """

        async with self._driver.session() as session:
            result = await session.run(query)
            record = await result.single()

            if record:
                return dict(record)

            return {
                "total_merges": 0,
                "completed": 0,
                "rolled_back": 0,
                "failed": 0,
                "exact_matches": 0,
                "fuzzy_matches": 0,
                "context_matches": 0,
                "ticker_matches": 0,
            }

    def _node_to_operation(self, node_data: dict[str, Any]) -> MergeOperation | None:
        """Convert a Neo4j node to a MergeOperation.

        Args:
            node_data: Dictionary of node properties

        Returns:
            MergeOperation instance or None if conversion fails
        """
        try:
            # Parse merged entities from stored JSON
            merged_entities_raw = node_data.get("merged_entities", [])
            merged_entities = [
                MergedEntity(**e) if isinstance(e, dict) else e for e in merged_entities_raw
            ]

            return MergeOperation(
                merge_id=node_data["merge_id"],
                timestamp=datetime.fromisoformat(node_data["timestamp"]),
                status=MergeStatus(node_data["status"]),
                match_type=MergeMatchType(node_data["match_type"]),
                similarity_score=float(node_data.get("similarity_score", 1.0)),
                canonical_id=node_data["canonical_id"],
                canonical_name=node_data["canonical_name"],
                merged_entities=merged_entities,
                user=node_data.get("user_initiated", "system"),
                notes=node_data.get("notes", ""),
            )
        except Exception as e:
            logger.warning(
                "Failed to parse merge operation",
                error=str(e),
                merge_id=node_data.get("merge_id"),
            )
            return None
