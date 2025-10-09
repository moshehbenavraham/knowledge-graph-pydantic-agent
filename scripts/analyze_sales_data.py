#!/usr/bin/env python3
"""Analyze the uploaded sales data."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.clients.database import get_supabase_client


def run_query(client, title, query):
    """Run a query and display results."""
    print(f"\n{'='*70}")
    print(f"{title}")
    print(f"{'='*70}")
    result = client.rpc("execute_sql", {"query": query}).execute()

    if result.data and isinstance(result.data, list):
        for row in result.data:
            print(row)
    else:
        print(result.data)
    return result.data


def main():
    client = get_supabase_client()

    print("\n📊 SALES DATA ANALYSIS")

    # 1. Top-selling products (by revenue)
    query1 = """
    SELECT
        row_data->>'product' as product_name,
        ROUND(SUM((row_data->>'sales')::float)::numeric, 2) AS total_revenue,
        SUM((row_data->>'quantity')::int) AS total_units_sold
    FROM document_rows
    GROUP BY row_data->>'product'
    ORDER BY total_revenue DESC
    LIMIT 10
    """
    run_query(client, "🏆 TOP 10 PRODUCTS BY REVENUE", query1)

    # 2. Sales by region
    query2 = """
    SELECT
        row_data->>'region' as region,
        ROUND(SUM((row_data->>'sales')::float)::numeric, 2) AS region_revenue,
        SUM((row_data->>'quantity')::int) AS region_units_sold,
        COUNT(*) AS transaction_count
    FROM document_rows
    GROUP BY row_data->>'region'
    ORDER BY region_revenue DESC
    """
    run_query(client, "🌍 SALES BY REGION", query2)

    # 3. Category with highest average transaction value
    query3 = """
    SELECT
        row_data->>'category' as category,
        ROUND(AVG((row_data->>'sales')::float)::numeric, 2) AS avg_transaction_value,
        COUNT(*) AS transaction_count,
        ROUND(SUM((row_data->>'sales')::float)::numeric, 2) AS total_revenue
    FROM document_rows
    GROUP BY row_data->>'category'
    ORDER BY avg_transaction_value DESC
    """
    run_query(client, "📊 CATEGORY PERFORMANCE (by avg transaction)", query3)

    # 4. Customer type analysis
    query4 = """
    SELECT
        row_data->>'customer_type' as customer_type,
        COUNT(*) AS transactions,
        ROUND(SUM((row_data->>'sales')::float)::numeric, 2) AS total_revenue,
        ROUND(AVG((row_data->>'sales')::float)::numeric, 2) AS avg_transaction,
        SUM((row_data->>'quantity')::int) AS total_units
    FROM document_rows
    GROUP BY row_data->>'customer_type'
    ORDER BY total_revenue DESC
    """
    run_query(client, "👥 CUSTOMER TYPE ANALYSIS", query4)

    # 5. Profit margins (sales - cost)
    query5 = """
    SELECT
        row_data->>'product' as product,
        row_data->>'category' as category,
        ROUND(SUM((row_data->>'sales')::float)::numeric, 2) AS revenue,
        ROUND(SUM((row_data->>'cost')::float)::numeric, 2) AS cost,
        ROUND((SUM((row_data->>'sales')::float) - SUM((row_data->>'cost')::float))::numeric, 2) AS profit,
        ROUND(((SUM((row_data->>'sales')::float) - SUM((row_data->>'cost')::float)) / SUM((row_data->>'sales')::float) * 100)::numeric, 2) AS profit_margin_pct
    FROM document_rows
    GROUP BY row_data->>'product', row_data->>'category'
    ORDER BY profit DESC
    LIMIT 10
    """
    run_query(client, "💰 TOP 10 PRODUCTS BY PROFIT MARGIN", query5)

    print("\n" + "=" * 70)
    print("✅ Analysis complete!")


if __name__ == "__main__":
    main()
