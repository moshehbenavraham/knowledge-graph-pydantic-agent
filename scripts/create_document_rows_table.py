#!/usr/bin/env python3
"""Create document_rows table in Supabase for CSV/tabular data uploads."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.clients.database import get_supabase_client
from src.config import get_settings


def main():
    """Create document_rows table."""
    settings = get_settings()
    client = get_supabase_client()

    # Read SQL schema
    sql_file = project_root / "src/agentic_rag/storage/migrations/sql/002_document_rows_table.sql"

    with open(sql_file) as f:
        sql = f.read()

    print("Creating document_rows table...")
    print(f"Database: {settings.supabase_url}")

    try:
        # Execute SQL via Supabase RPC (if available) or direct query
        # Note: Supabase client doesn't directly support DDL, so we'll use the PostgREST approach
        # We need to execute this via the Supabase SQL editor or use psycopg2

        # Try using raw SQL execution
        result = client.rpc("execute_sql", {"query": sql}).execute()
        print("✅ Table created successfully!")
        print(f"Result: {result}")

    except Exception as e:
        error_msg = str(e)
        if "Could not find the function" in error_msg:
            print("\n⚠️  ERROR: execute_sql RPC function not found.")
            print("\nYou need to execute this SQL manually in Supabase SQL Editor:")
            print("\n" + "=" * 60)
            print(sql)
            print("=" * 60)
            print("\nSteps:")
            print("1. Go to your Supabase dashboard")
            print("2. Click 'SQL Editor' in the left sidebar")
            print("3. Click 'New Query'")
            print("4. Paste the SQL above")
            print("5. Click 'Run' or press Cmd/Ctrl + Enter")
        else:
            print(f"❌ Error: {e}")
            print("\nFalling back to manual instructions:")
            print("\nExecute this SQL in Supabase SQL Editor:")
            print("\n" + "=" * 60)
            print(sql)
            print("=" * 60)


if __name__ == "__main__":
    main()
