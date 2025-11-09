#!/usr/bin/env python3
"""
Database connectivity test script for Base Agent project.
Tests connections to Supabase/PostgreSQL and Neo4j.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog

logger = structlog.get_logger()


async def test_supabase_connection() -> dict[str, Any]:
    """Test Supabase/PostgreSQL connection."""
    try:
        from src.config import get_settings
        from supabase import Client, create_client

        settings = get_settings()

        if not settings.supabase_url or not settings.supabase_service_key:
            return {
                "status": "error",
                "message": "Missing Supabase credentials (SUPABASE_URL or SUPABASE_SERVICE_KEY)",
            }

        logger.info("Testing Supabase connection...", url=settings.supabase_url[:50] + "...")

        # Create Supabase client
        supabase: Client = create_client(settings.supabase_url, settings.supabase_service_key)

        # Test basic query
        _ = supabase.table("documents").select("id").limit(1).execute()

        # Test analytics tables
        _ = supabase.table("search_analytics").select("id").limit(1).execute()

        # Test auth tables if using database auth
        auth_result = None
        if settings.use_database_auth:
            auth_result = supabase.table("auth_users").select("id").limit(1).execute()

        return {
            "status": "success",
            "message": "Supabase connection successful",
            "details": {
                "url": settings.supabase_url[:50] + "...",
                "documents_table": "accessible",
                "analytics_table": "accessible",
                "auth_table": (
                    "accessible" if auth_result else "not tested (USE_DATABASE_AUTH=false)"
                ),
            },
        }
    except ImportError as e:
        return {
            "status": "error",
            "message": f"Missing dependencies: {e!s}",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Supabase connection failed: {e!s}",
        }


async def test_neo4j_connection() -> dict[str, Any]:
    """Test Neo4j connection."""
    try:
        from neo4j import GraphDatabase

        from src.config import get_settings

        settings = get_settings()

        if not settings.neo4j_uri or not settings.neo4j_user or not settings.neo4j_password:
            return {
                "status": "error",
                "message": "Missing Neo4j credentials (NEO4J_URI, NEO4J_USER, or NEO4J_PASSWORD)",
            }

        logger.info("Testing Neo4j connection...", uri=settings.neo4j_uri)

        # Create Neo4j driver
        driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )

        # Verify connectivity
        driver.verify_connectivity()

        # Test basic query
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as node_count LIMIT 1")
            record = result.single()
            node_count = record["node_count"] if record else 0

        driver.close()

        return {
            "status": "success",
            "message": "Neo4j connection successful",
            "details": {
                "uri": settings.neo4j_uri,
                "node_count": node_count,
            },
        }
    except ImportError as e:
        return {
            "status": "error",
            "message": f"Missing dependencies: {e!s}",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Neo4j connection failed: {e!s}",
        }


async def test_postgresql_direct() -> dict[str, Any]:
    """Test direct PostgreSQL connection (for mem0 DATABASE_URL)."""
    try:
        import asyncpg

        from src.config import get_settings

        settings = get_settings()

        if not settings.database_url:
            return {
                "status": "warning",
                "message": "DATABASE_URL not set (required for mem0 memory feature)",
            }

        logger.info("Testing direct PostgreSQL connection...")

        # Test connection
        conn = await asyncpg.connect(settings.database_url)

        # Test basic query
        version = await conn.fetchval("SELECT version()")

        await conn.close()

        return {
            "status": "success",
            "message": "PostgreSQL direct connection successful",
            "details": {
                "version": version[:100] + "..." if len(version) > 100 else version,
            },
        }
    except ImportError as e:
        return {
            "status": "error",
            "message": f"Missing dependencies (asyncpg): {e!s}",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"PostgreSQL direct connection failed: {e!s}",
        }


def print_result(name: str, result: dict[str, Any]) -> None:
    """Print formatted test result."""
    status = result["status"]
    message = result["message"]
    details = result.get("details", {})

    # Status symbols
    symbols = {
        "success": "\u2713",  # checkmark
        "error": "\u2717",  # X
        "warning": "\u26a0",  # warning
    }

    # Colors (ANSI)
    colors = {
        "success": "\033[92m",  # Green
        "error": "\033[91m",  # Red
        "warning": "\033[93m",  # Yellow
        "reset": "\033[0m",
    }

    symbol = symbols.get(status, "?")
    color = colors.get(status, "")
    reset = colors["reset"]

    print(f"\n{color}{symbol} {name}{reset}")
    print(f"  Status: {status.upper()}")
    print(f"  Message: {message}")

    if details:
        print("  Details:")
        for key, value in details.items():
            print(f"    - {key}: {value}")


async def main():
    """Run all database connectivity tests."""
    print("=" * 80)
    print("DATABASE CONNECTIVITY TEST")
    print("=" * 80)

    # Run all tests
    supabase_result = await test_supabase_connection()
    neo4j_result = await test_neo4j_connection()
    postgres_result = await test_postgresql_direct()

    # Print results
    print_result("Supabase/PostgreSQL (Supabase Client)", supabase_result)
    print_result("Neo4j Knowledge Graph", neo4j_result)
    print_result("PostgreSQL Direct (mem0)", postgres_result)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    all_results = [supabase_result, neo4j_result, postgres_result]
    success_count = sum(1 for r in all_results if r["status"] == "success")
    error_count = sum(1 for r in all_results if r["status"] == "error")
    warning_count = sum(1 for r in all_results if r["status"] == "warning")

    print(f"Total tests: {len(all_results)}")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Warnings: {warning_count}")

    if error_count > 0:
        print("\n\u26a0 Some database connections failed. Check .env configuration.")
        sys.exit(1)
    elif warning_count > 0:
        print(
            "\n\u26a0 All critical connections successful, but some optional features unavailable."
        )
        sys.exit(0)
    else:
        print("\n\u2713 All database connections successful!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
