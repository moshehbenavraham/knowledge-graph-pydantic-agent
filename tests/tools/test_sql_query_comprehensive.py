"""
Comprehensive tests for SQL query execution tool.

Tests:
- Read-only query validation
- Write operation blocking (INSERT, UPDATE, DELETE, etc)
- Trailing semicolon removal
- Supabase RPC integration
- Error handling
- Result formatting
"""

import json
from unittest.mock import Mock

import pytest

from src.tools.sql_query import execute_sql_query_tool


@pytest.mark.asyncio
class TestSQLQueryValidation:
    """Test SQL query validation."""

    async def test_valid_select_query(self):
        """Test valid SELECT query executes successfully."""
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = [{"id": 1, "name": "test"}]
        mock_supabase.rpc.return_value.execute.return_value = mock_result

        result = await execute_sql_query_tool(
            mock_supabase, "SELECT * FROM document_rows WHERE dataset_id = '123'"
        )

        assert json.loads(result) == [{"id": 1, "name": "test"}]
        mock_supabase.rpc.assert_called_once_with(
            "execute_sql", {"query": "SELECT * FROM document_rows WHERE dataset_id = '123'"}
        )

    async def test_query_with_trailing_semicolon(self):
        """Test trailing semicolon is removed."""
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = []
        mock_supabase.rpc.return_value.execute.return_value = mock_result

        await execute_sql_query_tool(mock_supabase, "SELECT * FROM document_rows;")

        # Verify semicolon was stripped
        call_args = mock_supabase.rpc.call_args
        assert call_args[0][1]["query"] == "SELECT * FROM document_rows"

    async def test_query_with_multiple_trailing_semicolons(self):
        """Test multiple trailing semicolons are removed."""
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = []
        mock_supabase.rpc.return_value.execute.return_value = mock_result

        await execute_sql_query_tool(mock_supabase, "SELECT * FROM document_rows ;;;")

        call_args = mock_supabase.rpc.call_args
        assert call_args[0][1]["query"] == "SELECT * FROM document_rows"

    async def test_blocks_insert_query(self):
        """Test INSERT query is blocked."""
        mock_supabase = Mock()

        result = await execute_sql_query_tool(
            mock_supabase, "INSERT INTO document_rows (id) VALUES (1)"
        )

        assert "Error: Write operation 'INSERT' detected" in result
        mock_supabase.rpc.assert_not_called()

    async def test_blocks_update_query(self):
        """Test UPDATE query is blocked."""
        mock_supabase = Mock()

        result = await execute_sql_query_tool(mock_supabase, "UPDATE document_rows SET value = 1")

        assert "Error: Write operation 'UPDATE' detected" in result

    async def test_blocks_delete_query(self):
        """Test DELETE query is blocked."""
        mock_supabase = Mock()

        result = await execute_sql_query_tool(
            mock_supabase, "DELETE FROM document_rows WHERE id = 1"
        )

        assert "Error: Write operation 'DELETE' detected" in result

    async def test_blocks_drop_query(self):
        """Test DROP query is blocked."""
        mock_supabase = Mock()

        result = await execute_sql_query_tool(mock_supabase, "DROP TABLE document_rows")

        assert "Error: Write operation 'DROP' detected" in result

    async def test_blocks_create_query(self):
        """Test CREATE query is blocked."""
        mock_supabase = Mock()

        result = await execute_sql_query_tool(mock_supabase, "CREATE TABLE test (id INT)")

        assert "Error: Write operation 'CREATE' detected" in result

    async def test_blocks_alter_query(self):
        """Test ALTER query is blocked."""
        mock_supabase = Mock()

        result = await execute_sql_query_tool(
            mock_supabase, "ALTER TABLE document_rows ADD COLUMN test TEXT"
        )

        assert "Error: Write operation 'ALTER' detected" in result

    async def test_blocks_truncate_query(self):
        """Test TRUNCATE query is blocked."""
        mock_supabase = Mock()

        result = await execute_sql_query_tool(mock_supabase, "TRUNCATE TABLE document_rows")

        assert "Error: Write operation 'TRUNCATE' detected" in result

    async def test_blocks_grant_query(self):
        """Test GRANT query is blocked."""
        mock_supabase = Mock()

        result = await execute_sql_query_tool(
            mock_supabase, "GRANT SELECT ON document_rows TO user"
        )

        assert "Error: Write operation 'GRANT' detected" in result

    async def test_blocks_revoke_query(self):
        """Test REVOKE query is blocked."""
        mock_supabase = Mock()

        result = await execute_sql_query_tool(
            mock_supabase, "REVOKE SELECT ON document_rows FROM user"
        )

        assert "Error: Write operation 'REVOKE' detected" in result

    async def test_case_insensitive_validation(self):
        """Test write operation validation is case-insensitive."""
        mock_supabase = Mock()

        # Test lowercase
        result = await execute_sql_query_tool(
            mock_supabase, "insert into document_rows (id) values (1)"
        )
        assert "Error: Write operation 'INSERT' detected" in result

        # Test mixed case
        result = await execute_sql_query_tool(
            mock_supabase, "InSeRt InTo document_rows (id) VALUES (1)"
        )
        assert "Error: Write operation 'INSERT' detected" in result

    async def test_word_boundary_validation(self):
        """Test write operations are detected only as whole words."""
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = []
        mock_supabase.rpc.return_value.execute.return_value = mock_result

        # "inserted" contains "insert" but should not be blocked
        result = await execute_sql_query_tool(
            mock_supabase, "SELECT * FROM document_rows WHERE status = 'inserted'"
        )

        # Should not be blocked (no error message)
        assert "Error: Write operation" not in result


@pytest.mark.asyncio
class TestSQLQueryExecution:
    """Test SQL query execution."""

    async def test_complex_select_with_aggregation(self):
        """Test complex SELECT with aggregation."""
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = [{"category": "A", "total": 100}, {"category": "B", "total": 200}]
        mock_supabase.rpc.return_value.execute.return_value = mock_result

        query = """
        SELECT
            row_data->>'category' as category,
            SUM((row_data->>'sales')::numeric) as total
        FROM document_rows
        WHERE dataset_id = '123'
        GROUP BY row_data->>'category'
        """

        result = await execute_sql_query_tool(mock_supabase, query)

        data = json.loads(result)
        assert len(data) == 2
        assert data[0]["category"] == "A"
        assert data[1]["total"] == 200

    async def test_jsonb_field_extraction(self):
        """Test JSONB field extraction query."""
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = [{"avg_revenue": 50000.50}]
        mock_supabase.rpc.return_value.execute.return_value = mock_result

        query = """
        SELECT AVG((row_data->>'revenue')::numeric) as avg_revenue
        FROM document_rows
        WHERE dataset_id = '123'
        """

        result = await execute_sql_query_tool(mock_supabase, query)

        data = json.loads(result)
        assert data[0]["avg_revenue"] == 50000.50

    async def test_empty_result_set(self):
        """Test query returning no results."""
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = []
        mock_supabase.rpc.return_value.execute.return_value = mock_result

        result = await execute_sql_query_tool(
            mock_supabase, "SELECT * FROM document_rows WHERE id = 999999"
        )

        assert json.loads(result) == []

    async def test_query_with_multiple_conditions(self):
        """Test query with multiple WHERE conditions."""
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = [{"id": 1, "value": 100}]
        mock_supabase.rpc.return_value.execute.return_value = mock_result

        query = """
        SELECT * FROM document_rows
        WHERE dataset_id = '123'
        AND (row_data->>'status')::text = 'active'
        AND (row_data->>'value')::numeric > 50
        """

        result = await execute_sql_query_tool(mock_supabase, query)

        data = json.loads(result)
        assert len(data) == 1


@pytest.mark.asyncio
class TestSQLQueryErrors:
    """Test SQL query error handling."""

    async def test_sql_error_in_response(self):
        """Test handling SQL error from Supabase."""
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = {"error": "column 'invalid' does not exist"}
        mock_supabase.rpc.return_value.execute.return_value = mock_result

        result = await execute_sql_query_tool(mock_supabase, "SELECT invalid FROM document_rows")

        assert "SQL Error:" in result
        assert "column 'invalid' does not exist" in result

    async def test_exception_during_execution(self):
        """Test handling exception during query execution."""
        mock_supabase = Mock()
        mock_supabase.rpc.side_effect = Exception("Connection timeout")

        result = await execute_sql_query_tool(mock_supabase, "SELECT * FROM document_rows")

        assert "Error executing SQL query:" in result
        assert "Connection timeout" in result

    async def test_malformed_rpc_response(self):
        """Test handling malformed RPC response."""
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = None
        mock_supabase.rpc.return_value.execute.return_value = mock_result

        result = await execute_sql_query_tool(mock_supabase, "SELECT * FROM document_rows")

        # Should return "null" as JSON
        assert result == "null"


@pytest.mark.asyncio
class TestSQLQueryFormatting:
    """Test SQL query result formatting."""

    async def test_result_json_formatting(self):
        """Test results are formatted as pretty JSON."""
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = [{"id": 1, "name": "test"}]
        mock_supabase.rpc.return_value.execute.return_value = mock_result

        result = await execute_sql_query_tool(mock_supabase, "SELECT * FROM document_rows")

        # Verify it's valid JSON
        data = json.loads(result)
        assert isinstance(data, list)

        # Verify it's formatted with indentation
        assert "\n" in result  # Pretty-printed JSON has newlines

    async def test_unicode_in_results(self):
        """Test handling Unicode characters in results."""
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = [{"name": "Test 测试 🎉"}]
        mock_supabase.rpc.return_value.execute.return_value = mock_result

        result = await execute_sql_query_tool(mock_supabase, "SELECT * FROM document_rows")

        data = json.loads(result)
        assert data[0]["name"] == "Test 测试 🎉"

    async def test_null_values_in_results(self):
        """Test handling NULL values in results."""
        mock_supabase = Mock()
        mock_result = Mock()
        mock_result.data = [{"id": 1, "value": None}]
        mock_supabase.rpc.return_value.execute.return_value = mock_result

        result = await execute_sql_query_tool(mock_supabase, "SELECT * FROM document_rows")

        data = json.loads(result)
        assert data[0]["value"] is None
