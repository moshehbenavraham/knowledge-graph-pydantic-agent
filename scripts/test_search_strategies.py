#!/usr/bin/env python3
"""Test search strategies with real ingested data."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_vector_search() -> bool:
    """Test vector search with semantic query."""
    print("=" * 60)
    print("Test 1: Vector Search (Semantic Query)")
    print("=" * 60)
    print("Query: 'What is OpenAI's latest funding round?'\n")

    try:
        from src.agentic_rag.search.vector_search import VectorSearch
        from src.agentic_rag.storage.connection_manager import ConnectionManager

        conn_mgr = ConnectionManager()
        await conn_mgr.initialize()

        try:
            vector_search = VectorSearch(conn_mgr)
            results = await vector_search.search(
                query="What is OpenAI's latest funding round?", limit=5
            )

            print(f"✅ Found {len(results)} results\n")

            for i, result in enumerate(results, 1):
                print(f"Result {i}:")
                print(f"  Document: {result.document_title}")
                print(f"  Source: {result.document_source}")
                print(f"  Score: {result.similarity:.4f}")
                print(f"  Content: {result.content[:200]}...")
                print()

            return True

        finally:
            await conn_mgr.close()

    except Exception as e:
        print(f"❌ Vector search failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_graph_search() -> bool:
    """Test graph search with entity/relationship query."""
    print("\n" + "=" * 60)
    print("Test 2: Graph Search (Entity Relationships)")
    print("=" * 60)
    print("Query: 'How is Microsoft related to OpenAI?'\n")

    try:
        from src.agentic_rag.search.graph_search import GraphSearch
        from src.agentic_rag.storage.connection_manager import ConnectionManager

        conn_mgr = ConnectionManager()
        await conn_mgr.initialize()

        try:
            graph_search = GraphSearch(conn_mgr)

            # Search for entity relationships
            results = await graph_search.search(query="Microsoft OpenAI relationship", limit=10)

            print(f"✅ Found {len(results.entities)} entities\n")

            # Show entities
            if results.entities:
                print("Entities found:")
                for i, entity in enumerate(results.entities[:5], 1):
                    print(f"  {i}. {entity.name} ({entity.type})")
                    if hasattr(entity, "relevance_score"):
                        print(f"     Relevance: {entity.relevance_score:.4f}")
                print()

            # Show relationships
            if results.relationships:
                print(f"Relationships found ({len(results.relationships)}):")
                for i, rel in enumerate(results.relationships[:10], 1):
                    print(f"  {i}. {rel.source} → {rel.target}")
                    if hasattr(rel, "relationship_type"):
                        print(f"     Type: {rel.relationship_type}")
                print()

            # Query Neo4j directly for Microsoft-OpenAI relationships
            async with conn_mgr.get_neo4j_session() as session:
                result = await session.run(
                    """
                    MATCH (e1:Entity)-[r:RELATED_TO]->(e2:Entity)
                    WHERE e1.name =~ '(?i).*microsoft.*' AND e2.name =~ '(?i).*openai.*'
                       OR e1.name =~ '(?i).*openai.*' AND e2.name =~ '(?i).*microsoft.*'
                    RETURN e1.name as entity1, e2.name as entity2, r.type as rel_type
                    LIMIT 5
                    """
                )

                records = [record async for record in result]
                if records:
                    print("Direct relationships (Microsoft ↔ OpenAI):")
                    for record in records:
                        print(f"  - {record['entity1']} → {record['entity2']}")
                        if record["rel_type"]:
                            print(f"    Type: {record['rel_type']}")
                else:
                    print("[INFO] No direct relationships found (entities may not be connected)")

            return True

        finally:
            await conn_mgr.close()

    except Exception as e:
        print(f"❌ Graph search failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_hybrid_search() -> bool:
    """Test hybrid search with complex query."""
    print("\n" + "=" * 60)
    print("Test 3: Hybrid Search (Complex Query)")
    print("=" * 60)
    print("Query: 'Tell me about recent AI company acquisitions and partnerships'\n")

    try:
        from src.agentic_rag.search.hybrid_search import HybridSearch
        from src.agentic_rag.storage.connection_manager import ConnectionManager

        conn_mgr = ConnectionManager()
        await conn_mgr.initialize()

        try:
            hybrid_search = HybridSearch(conn_mgr)

            # This should trigger intent analysis and use hybrid strategy
            results = await hybrid_search.search(
                query="Tell me about recent AI company acquisitions and partnerships", limit=5
            )

            print(f"Strategy used: {results.search_strategy}")
            print(f"Intent detected: {results.intent}\n")

            # Show chunks
            if results.chunks:
                print(f"✅ Found {len(results.chunks)} chunks\n")
                for i, chunk in enumerate(results.chunks[:3], 1):
                    print(f"Chunk {i}:")
                    print(f"  Document: {chunk.document_title}")
                    print(f"  Score: {chunk.similarity:.4f}")
                    print(f"  Content: {chunk.content[:200]}...")
                    print()

            # Show entities
            if results.entities:
                print(f"✅ Found {len(results.entities)} entities\n")
                print("Top entities:")
                for i, entity in enumerate(results.entities[:5], 1):
                    print(f"  {i}. {entity.name} ({entity.type})")

            # Show relationships
            if results.relationships:
                print(f"\n✅ Found {len(results.relationships)} relationships\n")
                print("Sample relationships:")
                for i, rel in enumerate(results.relationships[:5], 1):
                    print(f"  {i}. {rel.source} → {rel.target}")

            print(f"\nQuery time: {results.query_time:.3f}s")

            return True

        finally:
            await conn_mgr.close()

    except Exception as e:
        print(f"❌ Hybrid search failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_intent_analysis() -> bool:
    """Test intent analyzer with different query types."""
    print("\n" + "=" * 60)
    print("Test 4: Intent Analysis")
    print("=" * 60)

    try:
        from src.agentic_rag.search.intent_analyzer import IntentAnalyzer

        analyzer = IntentAnalyzer()

        test_queries = [
            "What is OpenAI's latest funding round?",  # VECTOR_HEAVY
            "How is Microsoft related to OpenAI?",  # GRAPH_HEAVY
            "Tell me about AI acquisitions in 2024",  # TEMPORAL
            "Show me all companies that invested in Anthropic",  # ENTITY_FOCUSED
            "Explain the AI market landscape and key players",  # HYBRID
        ]

        print("Testing query classification:\n")
        for query in test_queries:
            intent_result = analyzer.analyze(query)
            print(f"Query: {query[:60]}")
            print(f"  Intent: {intent_result.primary_intent.value}")
            print(f"  Confidence: {intent_result.confidence:.2f}")
            print()

        return True

    except Exception as e:
        print(f"❌ Intent analysis failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main() -> int:
    """Run all search strategy tests."""
    print("\n🔍 Testing Search Strategies with Real Data\n")

    results = {
        "Vector Search": await test_vector_search(),
        "Graph Search": await test_graph_search(),
        "Hybrid Search": await test_hybrid_search(),
        "Intent Analysis": await test_intent_analysis(),
    }

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<20} {status}")

    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All search strategy tests passed!")
        return 0
    print("\n⚠️  Some tests failed")
    return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
