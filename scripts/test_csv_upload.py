#!/usr/bin/env python3
"""Test CSV upload functionality."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd

from src.clients.database import get_supabase_client


async def test_csv_upload():
    """Test uploading the sample sales CSV."""
    # Load the CSV file
    csv_path = project_root / "docs/example_docs/sample_sales_data.csv"

    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        return False

    print(f"Testing CSV upload: {csv_path.name}")

    # Read CSV
    df = pd.read_csv(csv_path)
    print(f"✅ Loaded CSV: {len(df)} rows, {len(df.columns)} columns")
    print(f"   Columns: {', '.join(df.columns)}")

    # Get Supabase client
    supabase = get_supabase_client()

    # Create document metadata
    doc = {
        "title": csv_path.name,
        "source": csv_path.name,
        "content": f"[Dataset: {csv_path.name}]",
        "metadata": {
            "source": csv_path.name,
            "file_type": "text/csv",
            "upload_source": "test_script",
            "is_tabular": True,
            "columns": list(df.columns),
            "row_count": len(df),
            "schema": df.dtypes.astype(str).to_dict(),
        },
    }

    try:
        # Insert document
        print("\nInserting document metadata...")
        result = supabase.table("documents").insert(doc).execute()
        dataset_id = result.data[0]["id"] if result.data else None

        if not dataset_id:
            print("❌ Failed to get dataset_id")
            return False

        print(f"✅ Document created with ID: {dataset_id}")

        # Prepare rows
        print(f"\nPreparing {len(df)} rows for insertion...")
        rows_data = []
        for idx, row in df.iterrows():
            row_doc = {
                "dataset_id": dataset_id,
                "row_data": row.to_dict(),
                "row_index": int(idx),
            }
            rows_data.append(row_doc)

        # Insert rows in batches (Supabase has limits)
        batch_size = 100
        total_rows = len(rows_data)

        print(f"Inserting {total_rows} rows in batches of {batch_size}...")

        for i in range(0, total_rows, batch_size):
            batch = rows_data[i : i + batch_size]
            supabase.table("document_rows").insert(batch).execute()
            print(f"  Inserted batch {i // batch_size + 1} ({len(batch)} rows)")

        print(f"✅ Successfully inserted all {total_rows} rows")

        # Verify insertion
        print("\nVerifying data...")
        verify_result = (
            supabase.table("document_rows")
            .select("id, row_index, row_data")
            .eq("dataset_id", dataset_id)
            .limit(3)
            .execute()
        )

        if verify_result.data:
            print(f"✅ Verified: {len(verify_result.data)} sample rows retrieved")
            print("\nSample row data:")
            for row in verify_result.data[:2]:
                print(f"  Row {row['row_index']}: {row['row_data']}")

        # Count total rows
        count_result = (
            supabase.table("document_rows")
            .select("id", count="exact")
            .eq("dataset_id", dataset_id)
            .execute()
        )

        print(f"\n✅ Total rows in database: {count_result.count}")

        return True

    except Exception as e:
        print(f"❌ Upload failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_csv_upload())
    sys.exit(0 if success else 1)
