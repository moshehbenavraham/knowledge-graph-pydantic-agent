"""
Analytics logger service - core infrastructure component.

This is NOT optional. All analytics logging flows through this service.
Provides async, non-blocking, batched logging with comprehensive validation.
"""

import asyncio
import contextlib
import hashlib
import json
import logging
from collections import deque
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class SearchAnalyticsEvent(BaseModel):
    """Search analytics event model with validation."""

    session_id: UUID | None = None
    query_text: str = Field(..., min_length=1)
    query_hash: str = ""
    detected_intent: str = Field(
        ..., pattern="^(VECTOR_HEAVY|GRAPH_HEAVY|HYBRID|TEMPORAL|ENTITY_FOCUSED)$"
    )
    strategy_used: str = Field(
        ..., pattern="^(VECTOR_HEAVY|GRAPH_HEAVY|HYBRID|TEMPORAL|ENTITY_FOCUSED)$"
    )
    total_latency_ms: float = Field(..., ge=0)
    vector_latency_ms: float = Field(default=0, ge=0)
    graph_latency_ms: float = Field(default=0, ge=0)
    intent_analysis_latency_ms: float = Field(default=0, ge=0)
    ranking_latency_ms: float = Field(default=0, ge=0)
    chunks_returned: int = Field(default=0, ge=0)
    cache_hit: bool = False
    entities_found: int = Field(default=0, ge=0)
    relationships_found: int = Field(default=0, ge=0)
    facts_found: int = Field(default=0, ge=0)
    graph_boost_applied: bool = False
    entity_boost_applied: bool = False
    user_id: str | None = None
    source: str = Field(default="ui", pattern="^(ui|api|cli)$")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("query_hash", mode="before")
    @classmethod
    def generate_query_hash(cls, v: str, info) -> str:
        """Auto-generate query hash from query_text if not provided."""
        if not v and info.data.get("query_text"):
            return hashlib.md5(info.data["query_text"].encode(), usedforsecurity=False).hexdigest()
        return v


class ToolUsageEvent(BaseModel):
    """Tool usage event model with validation."""

    session_id: UUID | None = None
    tool_name: str = Field(..., min_length=1)
    execution_time_ms: float = Field(..., ge=0)
    success: bool
    error_type: str | None = None
    error_message: str | None = None
    input_params: dict[str, Any] | None = None
    result_summary: dict[str, Any] | None = None
    triggered_by: str = Field(
        default="agent", pattern="^(user_query|agent_decision|fallback|system)$"
    )
    user_id: str | None = None
    source: str = Field(default="ui", pattern="^(ui|api|cli)$")


class AgentInteractionEvent(BaseModel):
    """Agent interaction event model with validation."""

    session_id: UUID
    interaction_type: str = Field(..., pattern="^(query|feedback|correction|clarification|error)$")
    user_message: str = Field(..., min_length=1)
    agent_response: str = Field(..., min_length=1)
    response_time_ms: float = Field(..., ge=0)
    tokens_used: int | None = Field(default=None, ge=0)
    model_used: str = Field(..., min_length=1)
    tools_called: list[str] = Field(default_factory=list)
    memory_used: bool = False
    rag_used: bool = False
    user_feedback: str | None = Field(default=None, pattern="^(thumbs_up|thumbs_down)$")
    feedback_comment: str | None = None
    feedback_at: datetime | None = None
    user_id: str | None = None
    source: str = Field(default="ui", pattern="^(ui|api|cli)$")
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestionAnalyticsEvent(BaseModel):
    """Ingestion analytics event model with validation."""

    document_id: UUID
    total_processing_time_ms: float = Field(..., ge=0)
    chunking_time_ms: float = Field(default=0, ge=0)
    embedding_time_ms: float = Field(default=0, ge=0)
    graph_extraction_time_ms: float = Field(default=0, ge=0)
    chunks_created: int = Field(default=0, ge=0)
    entities_extracted: int = Field(default=0, ge=0)
    relationships_extracted: int = Field(default=0, ge=0)
    facts_extracted: int = Field(default=0, ge=0)
    success: bool
    error_message: str | None = None
    file_size_bytes: int = Field(..., ge=0)
    file_type: str = Field(..., min_length=1)
    processing_mode: str = Field(..., pattern="^(full|incremental|reindex|update)$")


class SystemMetricsEvent(BaseModel):
    """System metrics snapshot event model."""

    pg_active_connections: int = Field(default=0, ge=0)
    pg_idle_connections: int = Field(default=0, ge=0)
    pg_total_queries: int = Field(default=0, ge=0)
    pg_failed_queries: int = Field(default=0, ge=0)
    pg_avg_query_time_ms: float = Field(default=0, ge=0)
    neo4j_active_connections: int = Field(default=0, ge=0)
    neo4j_idle_connections: int = Field(default=0, ge=0)
    neo4j_total_queries: int = Field(default=0, ge=0)
    neo4j_failed_queries: int = Field(default=0, ge=0)
    neo4j_avg_query_time_ms: float = Field(default=0, ge=0)
    cache_hit_rate: float = Field(default=0, ge=0, le=1)
    cache_size_mb: float = Field(default=0, ge=0)
    active_sessions: int = Field(default=0, ge=0)
    requests_per_minute: float = Field(default=0, ge=0)
    avg_response_time_ms: float = Field(default=0, ge=0)
    error_rate: float = Field(default=0, ge=0, le=1)


class AnalyticsLogger:
    """
    Centralized analytics logging service with async batching.

    This is core infrastructure - NOT optional.
    Uses async batching for performance with <5ms overhead.
    """

    def __init__(
        self,
        connection_manager,
        batch_size: int = 100,
        batch_interval_seconds: float = 5.0,
    ):
        """
        Initialize analytics logger.

        Args:
            connection_manager: Database connection manager (ConnectionManager instance)
            batch_size: Number of events to batch before flushing
            batch_interval_seconds: Maximum time to wait before flushing
        """
        self.connection_manager = connection_manager
        self.batch_size = batch_size
        self.batch_interval_seconds = batch_interval_seconds

        # Event queues
        self._search_queue: deque[SearchAnalyticsEvent] = deque()
        self._tool_queue: deque[ToolUsageEvent] = deque()
        self._interaction_queue: deque[AgentInteractionEvent] = deque()
        self._ingestion_queue: deque[IngestionAnalyticsEvent] = deque()
        self._system_queue: deque[SystemMetricsEvent] = deque()

        # Background task
        self._flush_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._running = False
        self._background_tasks: set[asyncio.Task] = set()  # Track background tasks

        # Metrics
        self.events_logged = 0
        self.events_failed = 0
        self.last_flush = datetime.now()

    async def start(self) -> None:
        """Start background flush task."""
        if self._running:
            return

        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("Analytics logger started")

    async def stop(self) -> None:
        """Stop background flush task and flush remaining events."""
        if not self._running:
            return

        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._flush_task

        # Final flush
        await self._flush_all()
        logger.info("Analytics logger stopped")

    async def _flush_loop(self) -> None:
        """Background loop to flush events periodically."""
        while self._running:
            try:
                await asyncio.sleep(self.batch_interval_seconds)
                await self._flush_all()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in analytics flush loop")

    async def _flush_all(self) -> None:
        """Flush all event queues to database."""
        async with self._lock:
            try:
                # Flush each queue
                if self._search_queue:
                    await self._flush_search_events()
                if self._tool_queue:
                    await self._flush_tool_events()
                if self._interaction_queue:
                    await self._flush_interaction_events()
                if self._ingestion_queue:
                    await self._flush_ingestion_events()
                if self._system_queue:
                    await self._flush_system_events()

                self.last_flush = datetime.now()
            except Exception:
                logger.exception("Error flushing analytics events")
                self.events_failed += 1

    async def _flush_search_events(self) -> None:
        """Flush search analytics events to database."""
        if not self._search_queue:
            return

        # Extract batch
        batch = []
        while self._search_queue and len(batch) < self.batch_size:
            batch.append(self._search_queue.popleft())

        if not batch:
            return

        try:
            async with self.connection_manager.get_pg_connection() as conn:
                # Batch insert
                await conn.executemany(
                    """
                    INSERT INTO search_analytics (
                        session_id, query_text, query_hash, detected_intent, strategy_used,
                        total_latency_ms, vector_latency_ms, graph_latency_ms,
                        intent_analysis_latency_ms, ranking_latency_ms,
                        chunks_returned, cache_hit, entities_found, relationships_found,
                        facts_found, graph_boost_applied, entity_boost_applied,
                        user_id, source, metadata
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                        $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
                    )
                    """,
                    [
                        (
                            event.session_id,
                            event.query_text,
                            event.query_hash,
                            event.detected_intent,
                            event.strategy_used,
                            event.total_latency_ms,
                            event.vector_latency_ms,
                            event.graph_latency_ms,
                            event.intent_analysis_latency_ms,
                            event.ranking_latency_ms,
                            event.chunks_returned,
                            event.cache_hit,
                            event.entities_found,
                            event.relationships_found,
                            event.facts_found,
                            event.graph_boost_applied,
                            event.entity_boost_applied,
                            event.user_id,
                            event.source,
                            json.dumps(event.metadata),
                        )
                        for event in batch
                    ],
                )

            self.events_logged += len(batch)
            logger.debug(f"Flushed {len(batch)} search analytics events")

        except Exception:
            logger.exception("Error flushing search events")
            # Put events back in queue for retry
            for event in reversed(batch):
                self._search_queue.appendleft(event)
            self.events_failed += len(batch)
            raise

    async def _flush_tool_events(self) -> None:
        """Flush tool usage events to database."""
        if not self._tool_queue:
            return

        batch = []
        while self._tool_queue and len(batch) < self.batch_size:
            batch.append(self._tool_queue.popleft())

        if not batch:
            return

        try:
            async with self.connection_manager.get_pg_connection() as conn:
                await conn.executemany(
                    """
                    INSERT INTO tool_usage_analytics (
                        session_id, tool_name, execution_time_ms, success,
                        error_type, error_message, input_params, result_summary,
                        triggered_by, user_id, source
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
                    )
                    """,
                    [
                        (
                            event.session_id,
                            event.tool_name,
                            event.execution_time_ms,
                            event.success,
                            event.error_type,
                            event.error_message,
                            json.dumps(event.input_params) if event.input_params else None,
                            json.dumps(event.result_summary) if event.result_summary else None,
                            event.triggered_by,
                            event.user_id,
                            event.source,
                        )
                        for event in batch
                    ],
                )

            self.events_logged += len(batch)
            logger.debug(f"Flushed {len(batch)} tool usage events")

        except Exception:
            logger.exception("Error flushing tool events")
            for event in reversed(batch):
                self._tool_queue.appendleft(event)
            self.events_failed += len(batch)
            raise

    async def _flush_interaction_events(self) -> None:
        """Flush agent interaction events to database."""
        if not self._interaction_queue:
            return

        batch = []
        while self._interaction_queue and len(batch) < self.batch_size:
            batch.append(self._interaction_queue.popleft())

        if not batch:
            return

        try:
            async with self.connection_manager.get_pg_connection() as conn:
                await conn.executemany(
                    """
                    INSERT INTO agent_interactions (
                        session_id, interaction_type, user_message, agent_response,
                        response_time_ms, tokens_used, model_used, tools_called,
                        memory_used, rag_used, user_feedback, feedback_comment,
                        feedback_at, user_id, source, metadata
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
                    )
                    """,
                    [
                        (
                            event.session_id,
                            event.interaction_type,
                            event.user_message,
                            event.agent_response,
                            event.response_time_ms,
                            event.tokens_used,
                            event.model_used,
                            event.tools_called,
                            event.memory_used,
                            event.rag_used,
                            event.user_feedback,
                            event.feedback_comment,
                            event.feedback_at,
                            event.user_id,
                            event.source,
                            json.dumps(event.metadata),
                        )
                        for event in batch
                    ],
                )

            self.events_logged += len(batch)
            logger.debug(f"Flushed {len(batch)} interaction events")

        except Exception:
            logger.exception("Error flushing interaction events")
            for event in reversed(batch):
                self._interaction_queue.appendleft(event)
            self.events_failed += len(batch)
            raise

    async def _flush_ingestion_events(self) -> None:
        """Flush ingestion events to database."""
        if not self._ingestion_queue:
            return

        batch = []
        while self._ingestion_queue and len(batch) < self.batch_size:
            batch.append(self._ingestion_queue.popleft())

        if not batch:
            return

        try:
            async with self.connection_manager.get_pg_connection() as conn:
                await conn.executemany(
                    """
                    INSERT INTO ingestion_analytics (
                        document_id, total_processing_time_ms, chunking_time_ms,
                        embedding_time_ms, graph_extraction_time_ms, chunks_created,
                        entities_extracted, relationships_extracted, facts_extracted,
                        success, error_message, file_size_bytes, file_type, processing_mode
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
                    )
                    """,
                    [
                        (
                            event.document_id,
                            event.total_processing_time_ms,
                            event.chunking_time_ms,
                            event.embedding_time_ms,
                            event.graph_extraction_time_ms,
                            event.chunks_created,
                            event.entities_extracted,
                            event.relationships_extracted,
                            event.facts_extracted,
                            event.success,
                            event.error_message,
                            event.file_size_bytes,
                            event.file_type,
                            event.processing_mode,
                        )
                        for event in batch
                    ],
                )

            self.events_logged += len(batch)
            logger.debug(f"Flushed {len(batch)} ingestion events")

        except Exception:
            logger.exception("Error flushing ingestion events")
            for event in reversed(batch):
                self._ingestion_queue.appendleft(event)
            self.events_failed += len(batch)
            raise

    async def _flush_system_events(self) -> None:
        """Flush system metrics events to database."""
        if not self._system_queue:
            return

        batch = []
        while self._system_queue and len(batch) < self.batch_size:
            batch.append(self._system_queue.popleft())

        if not batch:
            return

        try:
            async with self.connection_manager.get_pg_connection() as conn:
                await conn.executemany(
                    """
                    INSERT INTO system_metrics (
                        pg_active_connections, pg_idle_connections, pg_total_queries,
                        pg_failed_queries, pg_avg_query_time_ms,
                        neo4j_active_connections, neo4j_idle_connections, neo4j_total_queries,
                        neo4j_failed_queries, neo4j_avg_query_time_ms,
                        cache_hit_rate, cache_size_mb, active_sessions,
                        requests_per_minute, avg_response_time_ms, error_rate
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
                    )
                    """,
                    [
                        (
                            event.pg_active_connections,
                            event.pg_idle_connections,
                            event.pg_total_queries,
                            event.pg_failed_queries,
                            event.pg_avg_query_time_ms,
                            event.neo4j_active_connections,
                            event.neo4j_idle_connections,
                            event.neo4j_total_queries,
                            event.neo4j_failed_queries,
                            event.neo4j_avg_query_time_ms,
                            event.cache_hit_rate,
                            event.cache_size_mb,
                            event.active_sessions,
                            event.requests_per_minute,
                            event.avg_response_time_ms,
                            event.error_rate,
                        )
                        for event in batch
                    ],
                )

            self.events_logged += len(batch)
            logger.debug(f"Flushed {len(batch)} system metrics events")

        except Exception:
            logger.exception("Error flushing system events")
            for event in reversed(batch):
                self._system_queue.appendleft(event)
            self.events_failed += len(batch)
            raise

    async def log_search(self, event: SearchAnalyticsEvent) -> None:
        """
        Log a search analytics event (async, non-blocking).

        Args:
            event: Validated search analytics event
        """
        async with self._lock:
            self._search_queue.append(event)

            # Force flush if batch is full
            if len(self._search_queue) >= self.batch_size:
                task = asyncio.create_task(self._flush_search_events())
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

    async def log_tool_usage(self, event: ToolUsageEvent) -> None:
        """Log a tool usage event (async, non-blocking)."""
        async with self._lock:
            self._tool_queue.append(event)

            if len(self._tool_queue) >= self.batch_size:
                task = asyncio.create_task(self._flush_tool_events())
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

    async def log_interaction(self, event: AgentInteractionEvent) -> None:
        """Log an agent interaction event (async, non-blocking)."""
        async with self._lock:
            self._interaction_queue.append(event)

            if len(self._interaction_queue) >= self.batch_size:
                task = asyncio.create_task(self._flush_interaction_events())
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

    async def log_ingestion(self, event: IngestionAnalyticsEvent) -> None:
        """Log an ingestion analytics event (async, non-blocking)."""
        async with self._lock:
            self._ingestion_queue.append(event)

            if len(self._ingestion_queue) >= self.batch_size:
                task = asyncio.create_task(self._flush_ingestion_events())
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

    async def log_system_metrics(self, event: SystemMetricsEvent) -> None:
        """Log a system metrics snapshot (async, non-blocking)."""
        async with self._lock:
            self._system_queue.append(event)

            if len(self._system_queue) >= self.batch_size:
                task = asyncio.create_task(self._flush_system_events())
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

    def get_stats(self) -> dict[str, Any]:
        """Get analytics logger statistics."""
        return {
            "events_logged": self.events_logged,
            "events_failed": self.events_failed,
            "queue_sizes": {
                "search": len(self._search_queue),
                "tool": len(self._tool_queue),
                "interaction": len(self._interaction_queue),
                "ingestion": len(self._ingestion_queue),
                "system": len(self._system_queue),
            },
            "last_flush": self.last_flush.isoformat(),
            "running": self._running,
        }
