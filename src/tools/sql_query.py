from supabase import Client
import json
import re

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
    FROM dataset_rows
    WHERE dataset_id = '123'
    GROUP BY row_data->>'category';
    
    Args:
        supabase: The Supabase client
        sql_query: The SQL query to execute (must be read-only)
        
    Returns:
        str: The results of the SQL query in JSON format
    """
    try:
        # Validate that the query is read-only by checking for write operations
        sql_query = sql_query.strip()
        write_operations = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'GRANT', 'REVOKE']
        
        # Convert query to uppercase for case-insensitive comparison
        upper_query = sql_query.upper()
        
        # Check if any write operations are in the query
        for op in write_operations:
            pattern = r'\b' + op + r'\b'
            if re.search(pattern, upper_query):
                return f"Error: Write operation '{op}' detected. Only read-only queries are allowed."
        
        # Execute the query using the RPC function
        result = supabase.rpc(
            'execute_custom_sql',
            {"sql_query": sql_query}
        ).execute()
        
        # Check for errors in the response
        if result.data and 'error' in result.data:
            return f"SQL Error: {result.data['error']}"
        
        # Format the results nicely
        return json.dumps(result.data, indent=2)
        
    except Exception as e:
        return f"Error executing SQL query: {str(e)}"