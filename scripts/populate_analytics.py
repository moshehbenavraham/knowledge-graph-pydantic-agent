#!/usr/bin/env python3
"""
Script to populate analytics tables with sample data for dashboard testing.

This script:
1. Performs various RAG searches to populate search_analytics
2. Waits for analytics to flush (batched every 5 seconds)
3. Refreshes materialized views
4. Prints summary statistics
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def main() -> None:
    print("🚀 Analytics Population Script")
    print("=" * 60)

    # Import after path setup
    from src.agentic_rag.analytics import get_analytics_logger
    from src.agentic_rag.storage.connection_manager import get_connection_manager
    from src.tools.rag import get_hybrid_search

    # Initialize connection manager (this also initializes analytics logger)
    print("\n📡 Initializing connection manager...")
    conn_manager = await get_connection_manager()
    print("✅ Connection manager ready")

    # Get analytics logger
    try:
        analytics_logger = get_analytics_logger()
        print("✅ Analytics logger ready")
    except RuntimeError as e:
        print(f"❌ Analytics logger not initialized: {e}")
        return

    # Get hybrid search
    print("\n🔍 Initializing hybrid search...")
    hybrid_search = await get_hybrid_search()
    print("✅ Hybrid search ready")

    # Sample queries covering different intents
    queries = [
        # Vector-heavy (semantic)
        ("What is OpenAI's funding history?", "vector-heavy"),
        ("Explain transformer architecture", "vector-heavy"),
        ("Benefits of RAG systems", "vector-heavy"),
        # Graph-heavy (relationships)
        ("Who invested in Anthropic?", "graph-heavy"),
        ("Companies connected to Microsoft", "graph-heavy"),
        ("Relationships between AI companies", "graph-heavy"),
        # Temporal
        ("When did AI funding boom start?", "temporal"),
        ("Recent AI developments in 2023", "temporal"),
        ("Timeline of AI acquisitions", "temporal"),
        # Entity-focused
        ("Tell me about Sam Altman", "entity-focused"),
        ("Microsoft's role in AI", "entity-focused"),
        ("Google AI strategy", "entity-focused"),
        # Hybrid
        ("How did funding change after ChatGPT?", "hybrid"),
        ("Compare OpenAI and Anthropic safety", "hybrid"),
        ("Differences between cloud AI platforms", "hybrid"),
    ]

    print(f"\n📊 Running {len(queries)} sample queries...")
    print("-" * 60)

    successful_queries = 0
    failed_queries = 0

    for i, (query, intent_type) in enumerate(queries, 1):
        try:
            print(f"\n[{i}/{len(queries)}] {intent_type.upper()}")
            print(f"Query: {query}")

            # Perform search (this automatically logs to analytics)
            result = await hybrid_search.search(query, limit=5)

            print(
                f"✅ Result: {len(result.chunks)} chunks, "
                f"{len(result.entities)} entities, "
                f"latency: {result.query_time:.2f}s"
            )

            successful_queries += 1

            # Small delay to ensure different timestamps
            await asyncio.sleep(0.5)

        except Exception as e:
            print(f"❌ Failed: {e}")
            failed_queries += 1

    print("\n" + "=" * 60)
    print(f"✅ Completed: {successful_queries} successful, {failed_queries} failed")

    # Check analytics logger stats
    print("\n📈 Analytics Logger Stats:")
    stats = analytics_logger.get_stats()
    print(f"  Events logged: {stats['events_logged']}")
    print(f"  Events failed: {stats['events_failed']}")
    print(f"  Queue sizes: {stats['queue_sizes']}")
    print(f"  Last flush: {stats['last_flush']}")
    print(f"  Running: {stats['running']}")

    # Force flush analytics
    print("\n⏳ Waiting for analytics flush (5 seconds)...")
    await asyncio.sleep(6)  # Wait for batch flush

    # Check again
    stats = analytics_logger.get_stats()
    print(
        f"✅ After flush - Events logged: {stats['events_logged']}, "
        f"Queue sizes: {stats['queue_sizes']}"
    )

    # Refresh materialized views
    print("\n🔄 Refreshing materialized views...")
    try:
        async with conn_manager.get_pg_connection() as conn:
            await conn.execute("SELECT refresh_analytics_views();")
        print("✅ Materialized views refreshed")
    except Exception as e:
        print(f"⚠️  Warning: Could not refresh views: {e}")

    # Query analytics tables
    print("\n📊 Analytics Table Summary:")
    print("-" * 60)

    try:
        async with conn_manager.get_pg_connection() as conn:
            # Search analytics count
            row = await conn.fetchrow("SELECT COUNT(*) as count FROM search_analytics;")
            print(f"  search_analytics: {row['count']} records")

            # Intent distribution
            rows = await conn.fetch(
                """
                SELECT detected_intent, COUNT(*) as count
                FROM search_analytics
                GROUP BY detected_intent
                ORDER BY count DESC;
            """
            )
            print("\n  Intent Distribution:")
            for r in rows:
                print(f"    {r['detected_intent']}: {r['count']}")

            # Average latency
            row = await conn.fetchrow(
                """
                SELECT
                    AVG(total_latency_ms) as avg_latency,
                    MIN(total_latency_ms) as min_latency,
                    MAX(total_latency_ms) as max_latency
                FROM search_analytics;
            """
            )
            if row and row["avg_latency"]:
                print("\n  Latency Stats:")
                print(f"    Average: {row['avg_latency']:.2f}ms")
                print(f"    Min: {row['min_latency']:.2f}ms")
                print(f"    Max: {row['max_latency']:.2f}ms")

            # Graph boost stats
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) FILTER (WHERE graph_boost_applied) as with_boost,
                    COUNT(*) as total
                FROM search_analytics;
            """
            )
            if row and row["total"] > 0:
                boost_pct = (row["with_boost"] / row["total"]) * 100
                print(f"\n  Graph Boosts: {row['with_boost']}/{row['total']} ({boost_pct:.1f}%)")

            # Materialized view data
            row = await conn.fetchrow("SELECT COUNT(*) as count FROM intent_distribution_7d;")
            print(f"\n  intent_distribution_7d: {row['count']} records")

            row = await conn.fetchrow("SELECT COUNT(*) as count FROM daily_search_summary;")
            print(f"  daily_search_summary: {row['count']} records")

    except Exception as e:
        print(f"❌ Error querying analytics: {e}")

    print("\n" + "=" * 60)
    print("✅ Analytics population complete!")
    print("\nNext steps:")
    print("  1. Start the UI: make run-ui")
    print("  2. Navigate to the Dashboard tab")
    print("  3. View populated analytics charts")
    print("\nTo add more data:")
    print("  - Run this script again")
    print("  - Use the chat UI to ask questions")
    print("  - Ingest documents: make ingest")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
