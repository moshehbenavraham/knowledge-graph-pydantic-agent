#!/usr/bin/env python3
"""
Test Neo4j connection to diagnose authentication issues.

This script tests:
1. Basic driver creation
2. Connection establishment
3. Simple query execution
4. Authentication validity
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

# Load environment variables
load_dotenv()


async def test_neo4j_connection():
    """Test Neo4j connection with detailed error reporting."""

    # Read configuration from environment
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")

    print("=" * 70)
    print("Neo4j Connection Test")
    print("=" * 70)
    print("\n📋 Configuration:")
    print(f"   URI:      {neo4j_uri}")
    print(f"   User:     {neo4j_user}")
    print(f"   Password: {'*' * len(neo4j_password) if neo4j_password else 'NOT SET'}")
    print(f"   Database: {neo4j_database}")
    print()

    # Validate configuration
    if not all([neo4j_uri, neo4j_user, neo4j_password]):
        print("❌ ERROR: Missing Neo4j configuration in .env file")
        print("   Required: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")
        return False

    # Test connection
    driver = None
    try:
        print("🔄 Step 1: Creating Neo4j driver...")

        # Build driver config
        driver_config = {
            "max_connection_pool_size": 10,
            "connection_acquisition_timeout": 30,
            "max_transaction_retry_time": 30,
            "database": neo4j_database,
            "connection_timeout": 30.0,
            "keep_alive": True,
        }

        driver = AsyncGraphDatabase.driver(
            neo4j_uri, auth=(neo4j_user, neo4j_password), **driver_config
        )
        print("✅ Driver created successfully")

        print("\n🔄 Step 2: Verifying driver...")
        await driver.verify_connectivity()
        print("✅ Driver connectivity verified")

        print("\n🔄 Step 3: Opening session...")
        async with driver.session(database=neo4j_database) as session:
            print("✅ Session opened")

            print("\n🔄 Step 4: Running test query...")
            result = await session.run("RETURN 1 as test, 'Connection successful!' as message")
            record = await result.single()
            print(f"✅ Query successful: {record['message']}")

            print("\n🔄 Step 5: Checking database info...")
            result = await session.run(
                """
                CALL dbms.components() YIELD name, versions, edition
                RETURN name, versions[0] as version, edition
            """
            )
            record = await result.single()
            print(f"✅ Neo4j {record['edition']}")
            print(f"   Version: {record['version']}")

            print("\n🔄 Step 6: Checking node count...")
            result = await session.run("MATCH (n) RETURN count(n) as count")
            record = await result.single()
            node_count = record["count"]
            print(f"✅ Total nodes in database: {node_count}")

            print("\n🔄 Step 7: Checking relationship count...")
            result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
            record = await result.single()
            rel_count = record["count"]
            print(f"✅ Total relationships in database: {rel_count}")

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED - Neo4j connection is working perfectly!")
        print("=" * 70)
        return True

    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)

        print(f"\n❌ ERROR: {error_type}")
        print(f"   Message: {error_message}")
        print()

        # Provide specific troubleshooting advice
        if "Unauthorized" in error_message or "authentication" in error_message.lower():
            print("🔍 DIAGNOSIS: Authentication Failed")
            print()
            print("   Possible causes:")
            print("   1. Neo4j Aura instance is paused (free tier auto-pauses after 3 days)")
            print("   2. Password has been reset or is incorrect")
            print("   3. User doesn't have access to this database")
            print()
            print("   Solutions:")
            print("   1. Go to https://console.neo4j.io/")
            print("   2. Check if your instance is paused and resume it")
            print("   3. Reset your password if needed")
            print("   4. Update NEO4J_PASSWORD in your .env file")

        elif "ServiceUnavailable" in error_type or "connection" in error_message.lower():
            print("🔍 DIAGNOSIS: Connection Failed")
            print()
            print("   Possible causes:")
            print("   1. Network connectivity issue")
            print("   2. Neo4j Aura instance is stopped")
            print("   3. URI is incorrect")
            print()
            print("   Solutions:")
            print("   1. Check your internet connection")
            print("   2. Verify the URI in your .env matches your Aura console")
            print("   3. Try accessing https://console.neo4j.io/ in your browser")

        elif "timeout" in error_message.lower():
            print("🔍 DIAGNOSIS: Connection Timeout")
            print()
            print("   Possible causes:")
            print("   1. Instance is starting up (can take 30-60 seconds)")
            print("   2. Firewall blocking connection")
            print()
            print("   Solutions:")
            print("   1. Wait a minute and try again")
            print("   2. Check firewall settings")

        print("\n" + "=" * 70)
        return False

    finally:
        if driver:
            print("\n🔄 Closing driver...")
            await driver.close()
            print("✅ Driver closed")


async def main():
    """Main entry point."""
    success = await test_neo4j_connection()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
