"""
Dashboard handler for GraphRAG analytics and visualization.

Fetches statistics from the persistent analytics database (PostgreSQL),
providing methods for dashboard data retrieval with caching.

All metrics are sourced from analytics tables and materialized views,
not from in-memory counters.
"""

from datetime import datetime, timedelta
from typing import Any, cast

import structlog

from src.agentic_rag.storage.connection_manager import ConnectionManager

from .dashboard_utils import (
    generate_entity_timeline_cypher,
    generate_relationship_cypher,
    generate_top_entities_cypher,
)

logger = structlog.get_logger(__name__)


class DashboardHandler:
    """
    Handler for dashboard data retrieval and analytics.

    Queries the persistent analytics database to provide historical
    metrics and visualizations without runtime dependencies on search components.
    """

    def __init__(self, connection_manager: ConnectionManager | None = None):
        """
        Initialize dashboard handler.

        Args:
            connection_manager: Database connection manager
        """
        self.connection_manager = connection_manager or ConnectionManager()

        # Cache for expensive queries
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._cache_ttl = timedelta(seconds=30)

    def _get_cached(self, key: str) -> Any | None:
        """
        Get cached value if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if expired/missing
        """
        if key in self._cache:
            value, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._cache_ttl:
                return value
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        """
        Set cached value with current timestamp.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = (value, datetime.now())

    async def get_search_metrics(self, window: str = "7d") -> dict[str, Any]:
        """
        Fetch aggregated search statistics from analytics database.

        Args:
            window: Time window (24h, 7d, 30d)

        Returns:
            Dictionary with search metrics including total searches,
            average latency, strategy distribution, and boost rates
        """
        cache_key = f"search_metrics_{window}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cast("dict[str, Any]", cached)

        try:
            # Convert window to interval
            interval_map = {"24h": "24 hours", "7d": "7 days", "30d": "30 days"}
            interval = interval_map.get(window, "7 days")

            async with self.connection_manager.get_pg_connection() as conn:
                # Get overall summary from search_analytics table
                # interval is from whitelist, not user input
                summary = await conn.fetchrow(
                    f"""
                    SELECT
                        COUNT(*) AS total_searches,
                        AVG(total_latency_ms) AS avg_latency_ms,
                        AVG(vector_latency_ms) AS avg_vector_latency_ms,
                        AVG(graph_latency_ms) AS avg_graph_latency_ms,
                        COUNT(*) FILTER (WHERE graph_boost_applied) AS graph_boosts,
                        COUNT(*) FILTER (WHERE entity_boost_applied) AS entity_boosts,
                        COUNT(*) FILTER (WHERE cache_hit) AS cache_hits,
                        AVG(entities_found) AS avg_entities_found,
                        AVG(relationships_found) AS avg_relationships_found
                    FROM search_analytics
                    WHERE created_at >= NOW() - INTERVAL '{interval}'
                    """  # nosec B608
                )

                # Get strategy distribution from materialized view or table
                if window == "7d":
                    # Use materialized view for 7d window
                    strategies = await conn.fetch(
                        """
                        SELECT strategy_used, search_count
                        FROM intent_distribution_7d
                        ORDER BY search_count DESC
                        """
                    )
                else:
                    # Query directly for other windows
                    # interval is from whitelist, not user input
                    strategies = await conn.fetch(
                        f"""
                        SELECT
                            strategy_used,
                            COUNT(*) as search_count
                        FROM search_analytics
                        WHERE created_at >= NOW() - INTERVAL '{interval}'
                        GROUP BY strategy_used
                        ORDER BY search_count DESC
                        """  # nosec B608
                    )

            # Process results
            total_searches = summary["total_searches"] or 0
            strategy_distribution = {
                row["strategy_used"]: row["search_count"] for row in strategies
            }
            most_used_strategy = strategies[0]["strategy_used"] if strategies else "HYBRID"

            # Calculate boost rate
            graph_boosts = summary["graph_boosts"] or 0
            entity_boosts = summary["entity_boosts"] or 0
            boost_rate = (
                (graph_boosts + entity_boosts) / total_searches if total_searches > 0 else 0
            )

            metrics = {
                "total_searches": total_searches,
                "avg_latency_ms": float(summary["avg_latency_ms"] or 0),
                "most_used_strategy": most_used_strategy,
                "boost_rate": boost_rate,
                "strategy_distribution": strategy_distribution,
                "vector_stats": {
                    "avg_latency_ms": float(summary["avg_vector_latency_ms"] or 0),
                    "cache_hits": summary["cache_hits"] or 0,
                },
                "graph_stats": {
                    "avg_latency_ms": float(summary["avg_graph_latency_ms"] or 0),
                    "entities_found": int(summary["avg_entities_found"] or 0),
                    "relationships_found": int(summary["avg_relationships_found"] or 0),
                },
            }

            self._set_cache(cache_key, metrics)
            return metrics

        except Exception as e:
            logger.exception("Error fetching search metrics from analytics database")
            return {
                "total_searches": 0,
                "avg_latency_ms": 0,
                "most_used_strategy": "HYBRID",
                "boost_rate": 0,
                "strategy_distribution": {},
                "error": str(e),
            }

    async def get_intent_distribution(self, window: str = "7d") -> dict[str, float]:
        """
        Get distribution of query intents from analytics database.

        Args:
            window: Time window (24h, 7d, 30d)

        Returns:
            Dictionary mapping intent types to their percentage frequencies
        """
        cache_key = f"intent_distribution_{window}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cast("dict[str, float]", cached)

        try:
            async with self.connection_manager.get_pg_connection() as conn:
                # Use materialized view for 7d, direct query otherwise
                if window == "7d":
                    rows = await conn.fetch(
                        """
                        SELECT
                            detected_intent,
                            search_count,
                            avg_latency_ms,
                            avg_chunks_returned
                        FROM intent_distribution_7d
                        ORDER BY search_count DESC
                        """
                    )
                else:
                    interval_map = {"24h": "24 hours", "30d": "30 days"}
                    interval = interval_map.get(window, "7 days")
                    # interval is from whitelist, not user input
                    rows = await conn.fetch(
                        f"""
                        SELECT
                            detected_intent,
                            COUNT(*) as search_count,
                            AVG(total_latency_ms) as avg_latency_ms,
                            AVG(chunks_returned) as avg_chunks_returned
                        FROM search_analytics
                        WHERE created_at >= NOW() - INTERVAL '{interval}'
                        GROUP BY detected_intent
                        ORDER BY search_count DESC
                        """  # nosec B608
                    )

            # Calculate percentages
            total = sum(row["search_count"] for row in rows) or 1
            distribution = {
                row["detected_intent"]: (row["search_count"] / total * 100) for row in rows
            }

            self._set_cache(cache_key, distribution)
            return distribution

        except Exception:
            logger.exception("Error fetching intent distribution from analytics database")
            return {}

    async def get_graph_data(
        self, limit: int = 50, filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Fetch entity and relationship data for visualization.

        Args:
            limit: Maximum number of entities to return
            filters: Optional filters for entity selection

        Returns:
            Dictionary with entities and relationships
        """
        cache_key = f"graph_data_{limit}_{filters!s}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cast("dict[str, Any]", cached)

        try:
            # Connect to Neo4j and fetch entities
            async with self.connection_manager.get_neo4j_session() as session:
                # Get top entities
                entity_query = generate_top_entities_cypher(limit=limit)
                entity_result = await session.run(entity_query)
                entity_records = await entity_result.data()

                entities = []
                entity_ids = []
                for record in entity_records:
                    entities.append(
                        {
                            "id": record["id"],
                            "name": record["name"],
                            "type": record["type"],
                            "relationship_count": record["relationship_count"],
                        }
                    )
                    entity_ids.append(record["id"])

                # Get relationships for these entities
                if entity_ids:
                    rel_query = generate_relationship_cypher(entity_ids=entity_ids, limit=limit * 2)
                    rel_result = await session.run(rel_query)
                    rel_records = await rel_result.data()

                    relationships = []
                    for record in rel_records:
                        relationships.append(
                            {
                                "source_id": record["source_id"],
                                "target_id": record["target_id"],
                                "relationship_type": record["relationship_type"],
                                "summary": record.get("summary", ""),
                            }
                        )
                else:
                    relationships = []

            graph_data = {"entities": entities, "relationships": relationships}

            self._set_cache(cache_key, graph_data)
            return graph_data

        except Exception as e:
            logger.exception("Error fetching graph data")
            return {"entities": [], "relationships": [], "error": str(e)}

    async def get_top_entities(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        Get most connected entities.

        Args:
            limit: Maximum number of entities to return

        Returns:
            List of entity dictionaries with statistics
        """
        cache_key = f"top_entities_{limit}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cast("list[dict[str, Any]]", cached)

        try:
            async with self.connection_manager.get_neo4j_session() as session:
                query = generate_top_entities_cypher(limit=limit)
                result = await session.run(query)
                records = await result.data()

                entities = []
                for record in records:
                    entities.append(
                        {
                            "id": record["id"],
                            "name": record["name"],
                            "type": record["type"],
                            "relationship_count": record["relationship_count"],
                            "chunk_count": record["chunk_count"],
                            "created_at": record.get("created_at"),
                        }
                    )

            self._set_cache(cache_key, entities)
            return entities

        except Exception:
            logger.exception("Error fetching top entities")
            return []

    async def get_entity_timeline(self, entity_id: str) -> list[dict[str, Any]]:
        """
        Get temporal facts for specific entity.

        Args:
            entity_id: Entity UUID

        Returns:
            List of temporal facts with timestamps
        """
        cache_key = f"entity_timeline_{entity_id}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cast("list[dict[str, Any]]", cached)

        try:
            async with self.connection_manager.get_neo4j_session() as session:
                query = generate_entity_timeline_cypher(entity_id)
                result = await session.run(query)
                records = await result.data()

                timeline = []
                for record in records:
                    timeline.append(
                        {
                            "description": record["description"],
                            "valid_from": record.get("valid_from"),
                            "valid_to": record.get("valid_to"),
                            "created_at": record.get("created_at"),
                        }
                    )

            self._set_cache(cache_key, timeline)
            return timeline

        except Exception:
            logger.exception("Error fetching entity timeline")
            return []

    async def get_performance_metrics(self, window: str = "7d") -> dict[str, Any]:
        """
        Get latency breakdown and cache stats from analytics database.

        Args:
            window: Time window (24h, 7d, 30d)

        Returns:
            Dictionary with performance metrics including percentiles
        """
        cache_key = f"performance_metrics_{window}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cast("dict[str, Any]", cached)

        try:
            # Convert window to interval
            interval_map = {"24h": "24 hours", "7d": "7 days", "30d": "30 days"}
            interval = interval_map.get(window, "7 days")

            async with self.connection_manager.get_pg_connection() as conn:
                # Query performance metrics with percentiles
                # interval is from validated whitelist (24h/7d/30d), not user input
                metrics_row = await conn.fetchrow(
                    f"""
                    SELECT
                        AVG(vector_latency_ms) AS avg_vector_latency_ms,
                        AVG(graph_latency_ms) AS avg_graph_latency_ms,
                        AVG(ranking_latency_ms) AS avg_ranking_latency_ms,
                        AVG(total_latency_ms) AS avg_total_latency_ms,
                        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY total_latency_ms) AS p50_latency_ms,
                        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_latency_ms) AS p95_latency_ms,
                        PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY total_latency_ms) AS p99_latency_ms,
                        COUNT(*) FILTER (WHERE cache_hit) AS cache_hits,
                        COUNT(*) AS total_searches
                    FROM search_analytics
                    WHERE created_at >= NOW() - INTERVAL '{interval}'
                    """  # nosec B608
                )

                # Get latest system metrics if available (inside same connection context)
                system_metrics = await conn.fetchrow(
                    """
                    SELECT
                        pg_active_connections,
                        pg_idle_connections,
                        neo4j_active_connections,
                        cache_hit_rate as system_cache_hit_rate
                    FROM system_metrics
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                )

            # Get connection pool metrics from connection manager
            pg_metrics = self.connection_manager.pg_metrics
            neo4j_metrics = self.connection_manager.neo4j_metrics

            # Calculate cache hit rate
            total_searches = metrics_row["total_searches"] or 1
            cache_hit_rate = (metrics_row["cache_hits"] or 0) / total_searches

            # Prefer system_metrics for DB connections if available, otherwise use pool metrics
            if system_metrics:
                pg_active = system_metrics["pg_active_connections"]
                neo4j_active = system_metrics["neo4j_active_connections"]
                db_connections_active = pg_active + neo4j_active
                db_connections_idle = system_metrics["pg_idle_connections"]
            else:
                # Fallback: show pool size instead of currently-in-use connections
                pg_active = (
                    self.connection_manager.pg_pool.get_size()
                    if self.connection_manager.pg_pool
                    else 0
                )
                neo4j_active = 0
                db_connections_active = pg_active
                db_connections_idle = 0

            metrics = {
                "vector_latency_ms": float(metrics_row["avg_vector_latency_ms"] or 0),
                "graph_latency_ms": float(metrics_row["avg_graph_latency_ms"] or 0),
                "ranking_latency_ms": float(metrics_row["avg_ranking_latency_ms"] or 0),
                "total_latency_ms": float(metrics_row["avg_total_latency_ms"] or 0),
                "p50_latency_ms": float(metrics_row["p50_latency_ms"] or 0),
                "p95_latency_ms": float(metrics_row["p95_latency_ms"] or 0),
                "p99_latency_ms": float(metrics_row["p99_latency_ms"] or 0),
                "cache_hit_rate": cache_hit_rate,
                "cache_hits": metrics_row["cache_hits"] or 0,
                "db_connections_active": db_connections_active,
                "db_connections_idle": db_connections_idle,
                "pg_active_connections": pg_active,
                "neo4j_active_connections": neo4j_active,
                "pg_metrics": {
                    "total_queries": pg_metrics.total_queries,
                    "failed_queries": pg_metrics.failed_queries,
                    "avg_query_time_ms": pg_metrics.avg_query_time_ms,
                },
                "neo4j_metrics": {
                    "total_queries": neo4j_metrics.total_queries,
                    "failed_queries": neo4j_metrics.failed_queries,
                    "avg_query_time_ms": neo4j_metrics.avg_query_time_ms,
                },
            }

            self._set_cache(cache_key, metrics)
            return metrics

        except Exception as e:
            logger.exception("Error fetching performance metrics from analytics database")
            return {
                "vector_latency_ms": 0,
                "graph_latency_ms": 0,
                "ranking_latency_ms": 0,
                "total_latency_ms": 0,
                "p50_latency_ms": 0,
                "p95_latency_ms": 0,
                "p99_latency_ms": 0,
                "cache_hit_rate": 0,
                "cache_hits": 0,
                "db_connections_active": 0,
                "db_connections_idle": 0,
                "error": str(e),
            }

    async def get_time_series_data(
        self, window: str = "7d", metric: str = "searches"
    ) -> list[dict[str, Any]]:
        """
        Get time-series search data for charts from analytics database.

        Args:
            window: Time window (24h, 7d, 30d)
            metric: Metric to retrieve (searches, latency, cache_hits, graph_boosts)

        Returns:
            List of time-stamped search statistics
        """
        cache_key = f"time_series_{window}_{metric}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cast("list[dict[str, Any]]", cached)

        try:
            async with self.connection_manager.get_pg_connection() as conn:
                if window in {"7d", "30d"}:
                    # Try materialized view first, fallback to direct query
                    days = 7 if window == "7d" else 30
                    interval = f"{days} days"

                    try:
                        # Try materialized view first
                        rows = await conn.fetch(
                            """
                            SELECT
                                date AS timestamp,
                                total_searches AS searches,
                                avg_latency_ms AS latency,
                                cache_hits,
                                graph_boosts
                            FROM daily_search_summary
                            WHERE date >= CURRENT_DATE - ($1::int) * INTERVAL '1 day'
                            ORDER BY date ASC
                            """,
                            days,
                        )

                        # If materialized view returns no data, fall back to direct query
                        if not rows:
                            logger.warning(
                                f"Materialized view returned no data for {window}, "
                                f"falling back to direct query"
                            )
                            raise ValueError("No data in materialized view")

                    except Exception as e:
                        logger.warning(
                            f"Materialized view query failed ({e}), using direct query instead"
                        )
                        # Fallback: Query search_analytics directly with daily aggregation
                        # nosec B608
                        rows = await conn.fetch(
                            f"""
                            SELECT
                                DATE(created_at) AS timestamp,
                                COUNT(*) AS searches,
                                AVG(total_latency_ms) AS latency,
                                COUNT(*) FILTER (WHERE cache_hit) AS cache_hits,
                                COUNT(*) FILTER (WHERE graph_boost_applied) AS graph_boosts
                            FROM search_analytics
                            WHERE created_at >= NOW() - INTERVAL '{interval}'
                            GROUP BY DATE(created_at)
                            ORDER BY timestamp ASC
                            """  # nosec B608
                        )
                else:
                    # For 24h window, use hourly aggregation
                    rows = await conn.fetch(
                        """
                        SELECT
                            DATE_TRUNC('hour', created_at) AS timestamp,
                            COUNT(*) AS searches,
                            AVG(total_latency_ms) AS latency,
                            COUNT(*) FILTER (WHERE cache_hit) AS cache_hits,
                            COUNT(*) FILTER (WHERE graph_boost_applied) AS graph_boosts
                        FROM search_analytics
                        WHERE created_at >= NOW() - INTERVAL '24 hours'
                        GROUP BY DATE_TRUNC('hour', created_at)
                        ORDER BY timestamp ASC
                        """
                    )

            # Format results
            result = [
                {"timestamp": row["timestamp"], metric: row[metric]}
                for row in rows
                if metric in row
            ]

            self._set_cache(cache_key, result)
            return result

        except Exception:
            logger.exception("Error fetching time-series data from analytics database")
            return []

    async def get_tool_usage_metrics(self, window: str = "7d") -> dict[str, Any]:
        """
        Get tool usage analytics from database.

        Args:
            window: Time window (24h, 7d, 30d)

        Returns:
            Dictionary with tool usage summary and per-tool statistics
        """
        cache_key = f"tool_usage_{window}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cast("dict[str, Any]", cached)

        try:
            async with self.connection_manager.get_pg_connection() as conn:
                # Use materialized view for 7d window
                if window == "7d":
                    summary = await conn.fetchrow(
                        """
                        SELECT
                            SUM(total_calls) AS total_calls,
                            COUNT(DISTINCT tool_name) AS unique_tools,
                            AVG(success_rate) AS avg_success_rate
                        FROM tool_performance_7d
                        """
                    )

                    tools = await conn.fetch(
                        """
                        SELECT
                            tool_name,
                            total_calls,
                            success_rate,
                            avg_execution_time_ms,
                            p95_execution_time_ms
                        FROM tool_performance_7d
                        ORDER BY total_calls DESC
                        LIMIT 20
                        """
                    )
                else:
                    # Direct query for other windows
                    interval_map = {"24h": "24 hours", "30d": "30 days"}
                    interval = interval_map.get(window, "7 days")

                    # interval is from validated whitelist (24h/30d), not user input
                    summary = await conn.fetchrow(
                        f"""
                        SELECT
                            COUNT(*) AS total_calls,
                            COUNT(DISTINCT tool_name) AS unique_tools,
                            COUNT(*) FILTER (WHERE success = true)::float / NULLIF(COUNT(*), 0) AS avg_success_rate
                        FROM tool_usage_analytics
                        WHERE created_at >= NOW() - INTERVAL '{interval}'
                        """  # nosec B608
                    )

                    # interval is from validated whitelist (24h/30d), not user input
                    tools = await conn.fetch(
                        f"""
                        SELECT
                            tool_name,
                            COUNT(*) as total_calls,
                            COUNT(*) FILTER (WHERE success = true)::float / NULLIF(COUNT(*), 0) as success_rate,
                            AVG(execution_time_ms) as avg_execution_time_ms,
                            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_ms) as p95_execution_time_ms
                        FROM tool_usage_analytics
                        WHERE created_at >= NOW() - INTERVAL '{interval}'
                        GROUP BY tool_name
                        ORDER BY total_calls DESC
                        LIMIT 20
                        """  # nosec B608
                    )

            return {
                "total_calls": int(summary["total_calls"] or 0),
                "unique_tools": int(summary["unique_tools"] or 0),
                "avg_success_rate": float(summary["avg_success_rate"] or 0.0),
                "tools": [dict(row) for row in tools],
            }

        except Exception as e:
            logger.exception("Error fetching tool usage metrics from analytics database")
            return {
                "total_calls": 0,
                "unique_tools": 0,
                "avg_success_rate": 0.0,
                "tools": [],
                "error": str(e),
            }

    async def get_agent_interaction_metrics(self, window: str = "7d") -> dict[str, Any]:
        """
        Get agent interaction analytics from database.

        Args:
            window: Time window (24h, 7d, 30d)

        Returns:
            Dictionary with interaction statistics and user feedback
        """
        cache_key = f"agent_interactions_{window}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cast("dict[str, Any]", cached)

        try:
            # Convert window to interval
            interval_map = {"24h": "24 hours", "7d": "7 days", "30d": "30 days"}
            interval = interval_map.get(window, "7 days")

            async with self.connection_manager.get_pg_connection() as conn:
                # interval is from validated whitelist (24h/7d/30d), not user input
                stats = await conn.fetchrow(
                    f"""
                    SELECT
                        COUNT(*) AS total_interactions,
                        COUNT(DISTINCT session_id) AS unique_sessions,
                        AVG(response_time_ms) AS avg_response_time_ms,
                        COUNT(*) FILTER (WHERE rag_used) / NULLIF(COUNT(*), 0)::float AS rag_usage_rate,
                        COUNT(*) FILTER (WHERE user_feedback = 'thumbs_up') AS thumbs_up,
                        COUNT(*) FILTER (WHERE user_feedback = 'thumbs_down') AS thumbs_down,
                        COUNT(*) FILTER (WHERE user_feedback IS NOT NULL) / NULLIF(COUNT(*), 0)::float AS feedback_rate
                    FROM agent_interactions
                    WHERE created_at >= NOW() - INTERVAL '{interval}'
                    """  # nosec B608
                )

            return {
                "total_interactions": int(stats["total_interactions"] or 0),
                "unique_sessions": int(stats["unique_sessions"] or 0),
                "avg_response_time_ms": float(stats["avg_response_time_ms"] or 0),
                "rag_usage_rate": float(stats["rag_usage_rate"] or 0),
                "thumbs_up": int(stats["thumbs_up"] or 0),
                "thumbs_down": int(stats["thumbs_down"] or 0),
                "feedback_rate": float(stats["feedback_rate"] or 0),
            }

        except Exception as e:
            logger.exception("Error fetching agent interaction metrics from analytics database")
            return {
                "total_interactions": 0,
                "unique_sessions": 0,
                "avg_response_time_ms": 0,
                "rag_usage_rate": 0,
                "thumbs_up": 0,
                "thumbs_down": 0,
                "feedback_rate": 0,
                "error": str(e),
            }

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        logger.info("Dashboard cache cleared")

    async def refresh_materialized_views(self) -> bool:
        """
        Refresh materialized views for analytics dashboards.

        This updates the daily_search_summary, intent_distribution_7d,
        and tool_performance_7d views with the latest data.

        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.connection_manager.get_pg_connection() as conn:
                # Call the refresh function from the analytics schema
                await conn.execute("SELECT refresh_analytics_views();")
                logger.info("Materialized views refreshed successfully")
                # Clear cache after refresh so new data is fetched
                self.clear_cache()
                return True
        except Exception:
            logger.exception("Error refreshing materialized views")
            return False
