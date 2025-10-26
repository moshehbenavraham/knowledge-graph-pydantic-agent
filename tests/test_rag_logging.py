#!/usr/bin/env python3
"""
Test script to verify enhanced RAG logging.

This script runs a few test queries to demonstrate all the new logging features.
"""

import asyncio
import logging
import sys

# Configure logging to INFO level to see all the new logs
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
    stream=sys.stdout,
)

# Suppress noisy third-party logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("neo4j").setLevel(logging.WARNING)


async def main():
    """Run test queries to verify logging."""
    from src.agentic_rag.search.hybrid_search import HybridSearch
    from src.agentic_rag.storage.connection_manager import get_connection_manager

    print("\n" + "=" * 100)
    print("RAG LOGGING TEST - Enhanced Debugging Demo")
    print("=" * 100 + "\n")

    # Initialize connection manager and hybrid search
    print("Initializing RAG system...")
    connection_manager = await get_connection_manager()
    hybrid_search = HybridSearch(connection_manager)

    # Test queries demonstrating different intents
    test_queries = [
        ("What funding rounds are mentioned?", "VECTOR_HEAVY expected"),
        ("Tell me about OpenAI", "ENTITY_FOCUSED expected"),
        ("How are Microsoft and OpenAI connected?", "GRAPH_HEAVY expected"),
        (
            "Explain Microsoft's AI strategy and relationships",
            "HYBRID expected",
        ),
    ]

    for i, (query, description) in enumerate(test_queries, 1):
        print(f"\n\n{'#' * 100}")
        print(f"# TEST QUERY {i}/4: {description}")
        print(f"# Query: {query}")
        print(f"{'#' * 100}\n")

        try:
            # Execute search (this will trigger all the logging)
            result = await hybrid_search.search(query, limit=5)

            # Print summary
            print(f"\n{'─' * 100}")
            print(f"SUMMARY FOR QUERY {i}:")
            print(f"  Strategy Used: {result.search_strategy.value}")
            print(f"  Intent Detected: {result.intent.value if result.intent else 'N/A'}")
            print(f"  Query Time: {result.query_time:.3f}s")
            print(
                f"  Results: {len(result.chunks)} chunks, {len(result.facts)} facts, "
                f"{len(result.entities)} entities"
            )
            print(f"{'─' * 100}\n")

        except Exception as e:
            print(f"\n❌ ERROR in query {i}: {e}")
            import traceback

            traceback.print_exc()

    # Print final statistics
    print(f"\n\n{'=' * 100}")
    print("FINAL STATISTICS")
    print("=" * 100)
    stats = hybrid_search.get_stats()
    print(f"\nTotal searches: {stats['searches']}")
    print("Strategy distribution:")
    for strategy, pct in stats.get("strategy_distribution", {}).items():
        print(f"  - {strategy}: {pct * 100:.1f}%")
    print("\nVector search stats:")
    print(f"  - Cache hit rate: {stats['vector_stats'].get('cache_hit_rate', 0) * 100:.1f}%")
    print(f"  - Avg latency: {stats['vector_stats'].get('avg_latency', 0):.3f}s")
    print("\nGraph search stats:")
    print(f"  - Avg facts: {stats['graph_stats'].get('avg_facts_per_search', 0):.1f}")
    print(f"  - Avg entities: {stats['graph_stats'].get('avg_entities_per_search', 0):.1f}")
    print(
        f"  - Avg relationships: {stats['graph_stats'].get('avg_relationships_per_search', 0):.1f}"
    )
    print("\nIntent analysis stats:")
    for intent, count in stats["intent_stats"]["intents"].items():
        print(f"  - {intent}: {count} queries")

    print("\n" + "=" * 100)
    print("TEST COMPLETE - Check logs above for detailed debugging information!")
    print("=" * 100 + "\n")

    # Cleanup
    await connection_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
