#!/usr/bin/env python3
"""Apply execute_sql RPC function to Supabase."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_settings


def main():
    """Create execute_sql RPC function via direct Postgres connection."""
    settings = get_settings()

    # Read SQL schema
    sql_file = project_root / "src/agentic_rag/storage/migrations/sql/003_execute_sql_rpc.sql"

    with open(sql_file) as f:
        sql = f.read()

    print("Creating execute_sql RPC function...")
    print(f"Database: {settings.database_url.split('@')[1] if settings.database_url else 'N/A'}")

    try:
        import psycopg2

        # Connect to database
        conn = psycopg2.connect(settings.database_url)  # noqa: CONST-III-001 - Standalone migration script using centralized config
        cursor = conn.cursor()

        # Execute SQL
        cursor.execute(sql)
        conn.commit()

        print("✅ RPC function created successfully!")

        # Test the function
        print("\nTesting execute_sql function...")
        cursor.execute(
            """
            SELECT execute_sql('SELECT COUNT(*) as count FROM document_rows');
        """
        )

        result = cursor.fetchone()
        print(f"✅ Test query result: {result[0]}")

        cursor.close()
        conn.close()

    except ImportError:
        print("\n❌ psycopg2 not installed.")
        print("\nInstall it with: pip install psycopg2-binary")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nSQL that failed:")
        print("\n" + "=" * 60)
        print(sql)
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
