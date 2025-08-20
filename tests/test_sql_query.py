import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import os
import sys
import json

# Mock environment variables before importing modules that use them
with patch.dict(os.environ, {
    'SUPABASE_URL': 'https://test-supabase-url.com',
    'SUPABASE_SERVICE_KEY': 'test-supabase-key',
}):
    # Add src directory to path to import the tools module
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
    from tools.sql_query import execute_sql_query_tool


class TestSqlQueryTool:
    @pytest.mark.asyncio
    async def test_execute_sql_query_tool_success(self):
        # Mock Supabase client and response
        mock_supabase = MagicMock()
        mock_rpc = MagicMock()
        mock_supabase.rpc.return_value = mock_rpc
        mock_execute = MagicMock()
        mock_rpc.execute.return_value = mock_execute
        
        # Setup mock data
        mock_execute.data = [{'column1': 'value1', 'column2': 123}]
        
        # Test the function with a valid read-only query
        query = "SELECT * FROM test_table WHERE id = '123';"
        result = await execute_sql_query_tool(mock_supabase, query)
        
        # Verify Supabase RPC was called correctly
        mock_supabase.rpc.assert_called_once_with(
            'execute_custom_sql',
            {'sql_query': query}
        )
        
        # Verify the result is correctly formatted JSON
        assert json.loads(result) == [{'column1': 'value1', 'column2': 123}]

    @pytest.mark.asyncio
    async def test_execute_sql_query_tool_write_operation_detected(self):
        # Mock Supabase client (should not be called)
        mock_supabase = MagicMock()
        
        # Test the function with a write operation
        query = "INSERT INTO test_table (id) VALUES ('123');"
        result = await execute_sql_query_tool(mock_supabase, query)
        
        # Verify an error message is returned for write operations
        assert "Error: Write operation 'INSERT' detected. Only read-only queries are allowed." in result
        # Verify Supabase RPC was NOT called
        mock_supabase.rpc.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_sql_query_tool_error_from_supabase(self):
        # Mock Supabase client and response with an error
        mock_supabase = MagicMock()
        mock_rpc = MagicMock()
        mock_supabase.rpc.return_value = mock_rpc
        mock_execute = MagicMock()
        mock_rpc.execute.return_value = mock_execute
        
        # Setup mock error data
        mock_execute.data = {'error': 'Database error message'}
        
        # Test the function
        query = "SELECT * FROM non_existent_table;"
        result = await execute_sql_query_tool(mock_supabase, query)
        
        # Verify an error message is returned
        assert "SQL Error: Database error message" in result

    @pytest.mark.asyncio
    async def test_execute_sql_query_tool_general_exception(self):
        # Mock Supabase client that raises a general exception
        mock_supabase = MagicMock()
        mock_supabase.rpc.side_effect = Exception("General test exception")
        
        # Test the function
        query = "SELECT * FROM test_table;"
        result = await execute_sql_query_tool(mock_supabase, query)
        
        # Verify the exception was handled
        assert "Error executing SQL query: General test exception" in result
