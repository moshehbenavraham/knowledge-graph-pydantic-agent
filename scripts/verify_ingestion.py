#!/usr/bin/env python3
"""Verify ingestion results in both PostgreSQL and Neo4j."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def verify_postgres():
    """Verify PostgreSQL ingestion."""
    print("=" * 60)
    print("PostgreSQL Verification")
    print("=" * 60)

    try:
        from src.agentic_rag.storage.connection_manager import ConnectionManager

        conn_mgr = ConnectionManager()
        await conn_mgr.initialize()

        try:
            async with conn_mgr.get_pg_connection() as conn:
                # Count documents
                doc_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
                print(f"📄 Total Documents: {doc_count}")

                # Count chunks
                chunk_count = await conn.fetchval("SELECT COUNT(*) FROM chunks")
                print(f"📦 Total Chunks: {chunk_count}")

                # Check embeddings
                sample = await conn.fetchrow(
                    "SELECT embedding_1536, embedding_768 FROM chunks LIMIT 1"
                )
                if sample:
                    has_1536 = sample["embedding_1536"] is not None
                    has_768 = sample["embedding_768"] is not None
                    print(f"✅ Embeddings: 1536d={has_1536}, 768d={has_768}")

                # Recent documents
                recent = await conn.fetch(
                    """
                    SELECT id, title, source, created_at
                    FROM documents
                    ORDER BY created_at DESC
                    LIMIT 10
                    """
                )

                if recent:
                    print(f"\n📋 Recent Documents ({len(recent)}):")
                    for i, doc in enumerate(recent, 1):
                        source_name = doc["source"].split("/")[-1] if doc["source"] else "N/A"
                        print(f"  {i}. {doc['title'][:50]:<50} ({source_name})")

                # Chunks per document
                chunk_stats = await conn.fetch(
                    """
                    SELECT d.title, COUNT(c.id) as chunk_count
                    FROM documents d
                    LEFT JOIN chunks c ON c.document_id = d.id
                    GROUP BY d.id, d.title
                    ORDER BY d.created_at DESC
                    LIMIT 10
                    """
                )

                if chunk_stats:
                    print("\n📊 Chunks per Document:")
                    for stat in chunk_stats:
                        title = stat["title"][:40]
                        print(f"  - {title:<40} → {stat['chunk_count']} chunks")

        finally:
            await conn_mgr.close()

        return True

    except Exception as e:
        print(f"❌ PostgreSQL verification failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def verify_neo4j():
    """Verify Neo4j ingestion."""
    print("\n" + "=" * 60)
    print("Neo4j Verification")
    print("=" * 60)

    try:
        from src.agentic_rag.storage.connection_manager import ConnectionManager

        conn_mgr = ConnectionManager()
        await conn_mgr.initialize()

        try:
            async with conn_mgr.get_neo4j_session() as session:
                # Count entities
                result = await session.run("MATCH (e:Entity) RETURN count(e) as count")
                entity_count = (await result.single())["count"]
                print(f"🔷 Total Entities: {entity_count}")

                # Count episodes (facts)
                result = await session.run("MATCH (ep:Episode) RETURN count(ep) as count")
                episode_count = (await result.single())["count"]
                print(f"📌 Total Episodes (Facts): {episode_count}")

                # Count relationships
                result = await session.run("MATCH ()-[r:RELATED_TO]->() RETURN count(r) as count")
                rel_count = (await result.single())["count"]
                print(f"🔗 Total Relationships: {rel_count}")

                # Top entities by connections
                result = await session.run(
                    """
                    MATCH (e:Entity)
                    OPTIONAL MATCH (e)-[r:RELATED_TO]-()
                    RETURN e.name as name, e.type as type,
                           count(DISTINCT r) as connections
                    ORDER BY connections DESC
                    LIMIT 10
                    """
                )

                records = [record async for record in result]
                if records:
                    print("\n🌟 Top Entities by Connections:")
                    for i, record in enumerate(records, 1):
                        name = record["name"] or "Unknown"
                        entity_type = record["type"] or "Unknown"
                        connections = record["connections"]
                        print(f"  {i}. {name:<30} ({entity_type:<15}) → {connections} connections")

                # Sample entities
                result = await session.run(
                    """
                    MATCH (e:Entity)
                    RETURN e.name as name, e.type as type
                    ORDER BY e.created_at DESC
                    LIMIT 10
                    """
                )

                records = [record async for record in result]
                if records:
                    print(f"\n📋 Recent Entities ({len(records)}):")
                    for i, record in enumerate(records, 1):
                        name = record["name"] or "Unknown"
                        entity_type = record["type"] or "Unknown"
                        print(f"  {i}. {name:<40} ({entity_type})")

        finally:
            await conn_mgr.close()

        return True

    except Exception as e:
        print(f"❌ Neo4j verification failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all verifications."""
    print("\n🔍 Verifying Agentic RAG Ingestion Results\n")

    pg_success = await verify_postgres()
    neo4j_success = await verify_neo4j()

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"PostgreSQL: {'✅ PASS' if pg_success else '❌ FAIL'}")
    print(f"Neo4j:      {'✅ PASS' if neo4j_success else '❌ FAIL'}")

    if pg_success and neo4j_success:
        print("\n🎉 All verification checks passed!")
        return 0
    print("\n⚠️  Some verification checks failed")
    return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
