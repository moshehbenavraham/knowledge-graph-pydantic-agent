#!/usr/bin/env python3
"""Test SQL query functionality on uploaded CSV data."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.clients.database import get_supabase_client


def main():
    """Test SQL queries on document_rows table."""
    client = get_supabase_client()

    print("Testing SQL Query Tool on Uploaded CSV Data")
    print("=" * 70)

    # Test 1: Simple count
    print("\n1. Simple COUNT query:")
    query1 = "SELECT COUNT(*) as total_rows FROM document_rows"
    result1 = client.rpc("execute_sql", {"query": query1}).execute()
    print(f"   Result: {result1.data}")

    # Test 2: Category breakdown
    print("\n2. Sales by Category:")
    query2 = """
    SELECT
        row_data->>'category' as category,
        COUNT(*) as transaction_count,
        ROUND(SUM((row_data->>'sales')::float)::numeric, 2) as total_sales,
        ROUND(AVG((row_data->>'sales')::float)::numeric, 2) as avg_sales
    FROM document_rows
    GROUP BY row_data->>'category'
    ORDER BY total_sales DESC
    """
    result2 = client.rpc("execute_sql", {"query": query2}).execute()

    if result2.data and isinstance(result2.data, list):
        for row in result2.data:
            category = row.get("category", "Unknown")
            count = row.get("transaction_count", 0)
            total = row.get("total_sales", 0)
            avg = row.get("avg_sales", 0)
            print(f"   {category}: {count} transactions, ${total} total, ${avg} avg")

    # Test 3: Top products
    print("\n3. Top 5 Products by Sales:")
    query3 = """
    SELECT
        row_data->>'product' as product,
        SUM((row_data->>'sales')::float) as total_sales,
        SUM((row_data->>'quantity')::int) as total_quantity
    FROM document_rows
    GROUP BY row_data->>'product'
    ORDER BY total_sales DESC
    LIMIT 5
    """
    result3 = client.rpc("execute_sql", {"query": query3}).execute()

    if result3.data and isinstance(result3.data, list):
        for idx, row in enumerate(result3.data, 1):
            product = row.get("product", "Unknown")
            sales = row.get("total_sales", 0)
            qty = row.get("total_quantity", 0)
            print(f"   {idx}. {product}: ${sales:.2f} ({qty} units)")

    # Test 4: Regional analysis
    print("\n4. Sales by Region:")
    query4 = """
    SELECT
        row_data->>'region' as region,
        COUNT(*) as transactions,
        ROUND(SUM((row_data->>'sales')::float)::numeric, 2) as total_sales
    FROM document_rows
    GROUP BY row_data->>'region'
    ORDER BY total_sales DESC
    """
    result4 = client.rpc("execute_sql", {"query": query4}).execute()

    if result4.data and isinstance(result4.data, list):
        for row in result4.data:
            region = row.get("region", "Unknown")
            transactions = row.get("transactions", 0)
            total = row.get("total_sales", 0)
            print(f"   {region}: {transactions} transactions, ${total} total")

    print("\n" + "=" * 70)
    print("✅ All SQL queries executed successfully!")
    print("The agent SQL tool is ready to use with uploaded CSV data.")


if __name__ == "__main__":
    main()
