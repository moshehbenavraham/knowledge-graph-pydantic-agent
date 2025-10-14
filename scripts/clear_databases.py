#!/usr/bin/env python3
"""Clear both PostgreSQL and Neo4j databases."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def clear_postgres():
    """Clear PostgreSQL tables."""
    print("=" * 60)
    print("Clearing PostgreSQL")
    print("=" * 60)

    try:
        from src.agentic_rag.storage.connection_manager import ConnectionManager

        conn_mgr = ConnectionManager()
        await conn_mgr.initialize()

        try:
            async with conn_mgr.get_pg_connection() as conn:
                # Get counts before clearing
                doc_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
                chunk_count = await conn.fetchval("SELECT COUNT(*) FROM chunks")
                print(f"Before: {doc_count} documents, {chunk_count} chunks")

                # Delete all data (cascades to chunks due to foreign keys)
                await conn.execute("DELETE FROM chunks")
                await conn.execute("DELETE FROM documents")

                # Verify
                doc_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
                chunk_count = await conn.fetchval("SELECT COUNT(*) FROM chunks")
                print(f"After: {doc_count} documents, {chunk_count} chunks")
                print("✅ PostgreSQL cleared")

        finally:
            await conn_mgr.close()

        return True

    except Exception as e:
        print(f"❌ PostgreSQL clear failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def clear_neo4j():
    """Clear Neo4j database."""
    print("\n" + "=" * 60)
    print("Clearing Neo4j")
    print("=" * 60)

    try:
        from src.agentic_rag.storage.connection_manager import ConnectionManager

        conn_mgr = ConnectionManager()
        await conn_mgr.initialize()

        try:
            async with conn_mgr.get_neo4j_session() as session:
                # Get counts before clearing
                result = await session.run("MATCH (n) RETURN count(n) as count")
                node_count = (await result.single())["count"]

                result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
                rel_count = (await result.single())["count"]

                print(f"Before: {node_count} nodes, {rel_count} relationships")

                # Delete everything
                await session.run("MATCH (n) DETACH DELETE n")

                # Verify
                result = await session.run("MATCH (n) RETURN count(n) as count")
                node_count = (await result.single())["count"]

                result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
                rel_count = (await result.single())["count"]

                print(f"After: {node_count} nodes, {rel_count} relationships")
                print("✅ Neo4j cleared")

        finally:
            await conn_mgr.close()

        return True

    except Exception as e:
        print(f"❌ Neo4j clear failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all clears."""
    print("\n🗑️  Clearing All Databases\n")

    pg_success = await clear_postgres()
    neo4j_success = await clear_neo4j()

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"PostgreSQL: {'✅ CLEARED' if pg_success else '❌ FAIL'}")
    print(f"Neo4j:      {'✅ CLEARED' if neo4j_success else '❌ FAIL'}")

    if pg_success and neo4j_success:
        print("\n✅ All databases cleared - ready for clean ingestion")
        return 0
    print("\n⚠️  Some clears failed")
    return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
