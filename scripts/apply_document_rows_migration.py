#!/usr/bin/env python3
"""Apply document_rows table migration using direct Postgres connection."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_settings


def main():
    """Create document_rows table via direct Postgres connection."""
    settings = get_settings()

    # Read SQL schema
    sql_file = project_root / "src/agentic_rag/storage/migrations/sql/002_document_rows_table.sql"

    with open(sql_file) as f:
        sql = f.read()

    print("Creating document_rows table...")
    print(f"Database: {settings.database_url.split('@')[1] if settings.database_url else 'N/A'}")

    try:
        import psycopg2

        # Connect to database
        conn = psycopg2.connect(
            settings.database_url
        )  # noqa: CONST-III-001 - Standalone migration script using centralized config
        cursor = conn.cursor()

        # Execute SQL
        cursor.execute(sql)
        conn.commit()

        print("✅ Table created successfully!")

        # Verify table exists
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'document_rows';
        """
        )

        result = cursor.fetchone()
        if result:
            print(f"✅ Verified: {result[0]} table exists")

            # Check columns
            cursor.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'document_rows'
                ORDER BY ordinal_position;
            """
            )

            columns = cursor.fetchall()
            print("\nTable schema:")
            for col_name, col_type in columns:
                print(f"  - {col_name}: {col_type}")

        cursor.close()
        conn.close()

    except ImportError:
        print("\n❌ psycopg2 not installed.")
        print("\nInstall it with: pip install psycopg2-binary")
        print("\nOr execute this SQL manually in Supabase SQL Editor:")
        print("\n" + "=" * 60)
        print(sql)
        print("=" * 60)
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
