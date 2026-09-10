#!/usr/bin/env python3
"""Test database connection and schema."""

import asyncio
import sys

from dotenv import load_dotenv

# Load .env with override to ignore cached shell variables
load_dotenv(override=True)

from src.agentic_rag.storage.connection_manager import ConnectionManager


async def main():
    """Test database connection."""
    try:
        print("Initializing connection manager...")
        conn_mgr = ConnectionManager()
        await conn_mgr.initialize()

        print("Testing database connection...")
        async with conn_mgr.pg_pool.acquire() as conn:
            docs_exists = await conn.fetchval("""
                SELECT EXISTS (SELECT FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'documents');
            """)

            chunks_exists = await conn.fetchval("""
                SELECT EXISTS (SELECT FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'chunks');
            """)

            if docs_exists and chunks_exists:
                print("\n✅ Database connection successful!")
                print("✅ documents table exists")
                print("✅ chunks table exists")
                print("\n✅ Schema is initialized and ready for ingestion!")

                await conn_mgr.close()
                return 0
            print(f"\n❌ Schema incomplete: documents={docs_exists}, chunks={chunks_exists}")
            print("⚠️  Please run: src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql")

            await conn_mgr.close()
            return 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
