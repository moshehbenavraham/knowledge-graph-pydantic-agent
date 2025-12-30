import json
import re

import structlog
from supabase.client import Client

logger = structlog.get_logger(__name__)


async def execute_sql_query_tool(supabase: Client, sql_query: str) -> str:
    """
    Run a SQL query - use this to query from the document_rows table once you know the file ID you are querying.
    dataset_id is the file_id and you are always using the row_data for filtering, which is a jsonb field that has
    all the keys from the file schema given in the document_metadata table.

    Example query:

    SELECT AVG((row_data->>'revenue')::numeric)
    FROM document_rows
    WHERE dataset_id = '123';

    Example query 2:

    SELECT
        row_data->>'category' as category,
        SUM((row_data->>'sales')::numeric) as total_sales
    FROM document_rows
    WHERE dataset_id = '123'
    GROUP BY row_data->>'category';

    Args:
        supabase: The Supabase client
        sql_query: The SQL query to execute (must be read-only)

    Returns:
        str: The results of the SQL query in JSON format
    """
    logger.info("execute_sql_query_tool called", query_length=len(sql_query))

    try:
        # Validate that the query is read-only by checking for write operations
        sql_query = sql_query.strip()

        # Remove trailing semicolons (Supabase RPC doesn't accept them)
        sql_query = sql_query.rstrip(";").strip()

        write_operations = [
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "CREATE",
            "ALTER",
            "TRUNCATE",
            "GRANT",
            "REVOKE",
        ]

        # Convert query to uppercase for case-insensitive comparison
        upper_query = sql_query.upper()

        # Check if any write operations are in the query
        for op in write_operations:
            pattern = r"\b" + op + r"\b"
            if re.search(pattern, upper_query):
                logger.warning("Write operation detected in SQL query", operation=op)
                return (
                    f"Error: Write operation '{op}' detected. Only read-only queries are allowed."
                )

        # Execute the query using the RPC function
        logger.debug("Executing SQL query via Supabase RPC")
        result = supabase.rpc("execute_sql", {"query": sql_query}).execute()

        # Check for errors in the response
        if result.data and "error" in result.data:
            logger.error("SQL query returned error", error=result.data["error"])
            return f"SQL Error: {result.data['error']}"

        # Format the results nicely
        result_json = json.dumps(result.data, indent=2)
        result_count = len(result.data) if isinstance(result.data, list) else 1
        logger.info("SQL query executed successfully", result_count=result_count)
        return result_json

    except Exception as e:
        logger.exception("Error executing SQL query", error=str(e))
        return f"Error executing SQL query: {e!s}"
