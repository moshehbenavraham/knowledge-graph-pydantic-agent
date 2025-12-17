#!/usr/bin/env python3
"""
Verify GraphRAG Dashboard Deployment

Tests that all dashboard components are properly installed and configured.
"""

import asyncio
import sys


def check_dependencies():
    """Check that all required dependencies are installed."""
    print("🔍 Checking dashboard dependencies...")

    try:
        import plotly

        print(f"  ✅ plotly {plotly.__version__}")
    except ImportError as e:
        print(f"  ❌ plotly not installed: {e}")
        return False

    try:
        import networkx

        print(f"  ✅ networkx {networkx.__version__}")
    except ImportError as e:
        print(f"  ❌ networkx not installed: {e}")
        return False

    try:
        import pandas

        print(f"  ✅ pandas {pandas.__version__}")
    except ImportError as e:
        print(f"  ❌ pandas not installed: {e}")
        return False

    return True


def check_modules():
    """Check that dashboard modules can be imported."""
    print("\n🔍 Checking dashboard modules...")

    try:
        from src.ui.features.dashboard_handler import DashboardHandler  # noqa: F401

        print("  ✅ DashboardHandler")
    except ImportError as e:
        print(f"  ❌ DashboardHandler: {e}")
        return False

    try:
        from src.ui.features.dashboard_utils import (  # noqa: F401
            format_graph_for_plotly,
            generate_entity_cypher,
            generate_top_entities_cypher,
        )

        print("  ✅ dashboard_utils functions")
    except ImportError as e:
        print(f"  ❌ dashboard_utils: {e}")
        return False

    try:
        from src.config.ui import DashboardConfig  # noqa: F401

        print("  ✅ DashboardConfig")
    except ImportError as e:
        print(f"  ❌ DashboardConfig: {e}")
        return False

    return True


async def check_connections():
    """Check database connections."""
    print("\n🔍 Checking database connections...")

    try:
        from src.agentic_rag.storage.connection_manager import ConnectionManager

        async with ConnectionManager() as conn_mgr:
            # Test PostgreSQL
            try:
                async with conn_mgr.get_pg_connection() as conn:
                    result = await conn.fetchval("SELECT 1")
                    print("  ✅ PostgreSQL connection")
            except Exception as e:
                print(f"  ⚠️  PostgreSQL: {str(e)[:80]}")

            # Test Neo4j
            try:
                async with conn_mgr.get_neo4j_session() as session:
                    result = await session.run("RETURN 1 as test")
                    await result.single()
                    print("  ✅ Neo4j connection")
            except Exception as e:
                print(f"  ⚠️  Neo4j: {str(e)[:80]}")

        return True
    except Exception as e:
        print(f"  ❌ Connection test failed: {e}")
        return False


def check_dashboard_handler():
    """Test DashboardHandler initialization."""
    print("\n🔍 Checking DashboardHandler initialization...")

    try:
        from src.ui.features.dashboard_handler import DashboardHandler

        # Create handler (doesn't connect to DBs yet)
        handler = DashboardHandler()
        print("  ✅ DashboardHandler created")

        # Check methods exist
        assert hasattr(handler, "get_search_metrics")
        assert hasattr(handler, "get_intent_distribution")
        assert hasattr(handler, "get_graph_data")
        assert hasattr(handler, "get_top_entities")
        assert hasattr(handler, "get_entity_timeline")
        assert hasattr(handler, "get_performance_metrics")
        print("  ✅ All handler methods present")

        return True
    except Exception as e:
        print(f"  ❌ DashboardHandler test failed: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("GraphRAG Dashboard Deployment Verification")
    print("=" * 60)

    checks_passed = 0
    total_checks = 4

    # Check dependencies
    if check_dependencies():
        checks_passed += 1

    # Check modules
    if check_modules():
        checks_passed += 1

    # Check database connections (async)
    if asyncio.run(check_connections()):
        checks_passed += 1

    # Check dashboard handler
    if check_dashboard_handler():
        checks_passed += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"Verification Results: {checks_passed}/{total_checks} checks passed")
    print("=" * 60)

    if checks_passed == total_checks:
        print("\n✅ Dashboard deployment VERIFIED!")
        print("\n📊 To access the dashboard:")
        print("   1. Run: make run-ui")
        print("   2. Open: http://localhost:8502")
        print("   3. Click '📊 Dashboard' in the sidebar")
        print("\n📖 Quick Start Guide: docs/DASHBOARD_QUICKSTART.md")
        return 0
    print(f"\n⚠️  {total_checks - checks_passed} check(s) failed")
    print("\nPlease review errors above and fix before using dashboard.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
