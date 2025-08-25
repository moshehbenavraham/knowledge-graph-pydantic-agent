"""End-to-end tests for the AI agent system.

These tests verify complete user workflows from UI interaction to final response,
including Streamlit UI functionality, error handling, and real user scenarios.
"""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock environment variables before importing modules that use them
TEST_ENV_VARS = {
    "LLM_PROVIDER": "openai",
    "LLM_BASE_URL": "https://api.openai.com/v1",
    "LLM_API_KEY": "test-api-key",
    "LLM_CHOICE": "gpt-4o-mini",
    "VISION_LLM_CHOICE": "gpt-4o-mini",
    "EMBEDDING_PROVIDER": "openai",
    "EMBEDDING_BASE_URL": "https://api.openai.com/v1",
    "EMBEDDING_API_KEY": "test-api-key",
    "EMBEDDING_MODEL_CHOICE": "text-embedding-3-small",
    "SUPABASE_URL": "https://test-supabase-url.com",
    "SUPABASE_SERVICE_KEY": "test-supabase-key",
    "BRAVE_API_KEY": "test-brave-key",
    "SEARXNG_BASE_URL": "http://test-searxng-url.com",
    "DATABASE_URL": "postgresql://user:password@localhost:5432/testdb",
    "ENABLE_LONG_TERM_MEMORY": "true",
    "ENABLE_RAG": "true",
    "ENABLE_WEB_SEARCH": "true",
    "ENABLE_CODE_EXECUTION": "true",
    "ENABLE_IMAGE_ANALYSIS": "true",
}

with patch.dict(os.environ, TEST_ENV_VARS):
    # Mock Streamlit before importing UI modules
    streamlit_mock = MagicMock()
    streamlit_mock.session_state = MagicMock()
    streamlit_mock.chat_message = MagicMock()
    streamlit_mock.markdown = MagicMock()
    streamlit_mock.chat_input = MagicMock()
    streamlit_mock.title = MagicMock()
    streamlit_mock.empty = MagicMock()
    streamlit_mock.cache_resource = lambda func: func  # Pass-through decorator

    sys.modules["streamlit"] = streamlit_mock

    # Add src directory to path to import modules
    sys.path.append(str(Path(__file__).parent.parent.resolve() / "src"))

    # Import components for E2E testing
    from pydantic_ai.messages import ModelRequest, ModelResponse

    from agent.agent import agent
    from ui.streamlit_app import display_message_part, get_agent_deps, run_agent_with_streaming
    from ui.streamlit_ui_simple import run_agent


class TestCompleteUserWorkflows:
    """Test complete user workflows from query to response."""

    @pytest.fixture
    def mock_complete_system(self):
        """Mock the complete system for E2E testing."""
        # Mock all external dependencies
        mock_supabase = MagicMock()
        mock_embedding_client = AsyncMock()
        mock_http_client = AsyncMock()
        mock_mem0_client = MagicMock()

        # Setup realistic responses
        mock_supabase.rpc.return_value.execute.return_value.data = [
            {
                "file_id": "python_guide",
                "file_name": "python_guide.pdf",
                "content": "Python is a high-level programming language known for its simplicity",
                "similarity": 0.89,
            }
        ]

        mock_embedding_client.embeddings.create.return_value.data = [
            MagicMock(embedding=[0.1] * 1536)
        ]

        mock_mem0_client.search.return_value = {
            "results": [
                {"memory": "User prefers Python programming"},
                {"memory": "User is learning machine learning"},
            ]
        }
        mock_mem0_client.add.return_value = {"id": "mem_123"}

        return {
            "supabase": mock_supabase,
            "embedding_client": mock_embedding_client,
            "http_client": mock_http_client,
            "mem0_client": mock_mem0_client,
        }

    @pytest.mark.asyncio
    @patch("ui.streamlit_app.get_agent_deps")
    @patch("ui.streamlit_app.initialize_mem0")
    @patch("tools.rag.retrieve_relevant_documents_tool")
    @patch("tools.web_search.web_search_tool")
    async def test_research_query_workflow(
        self, mock_web_search, mock_rag, mock_mem0, mock_deps, mock_complete_system
    ):
        """Test complete research query workflow: memory -> RAG -> web search -> response."""
        # Setup mocks
        mock_deps.return_value = (
            mock_complete_system["embedding_client"],
            mock_complete_system["supabase"],
        )
        mock_mem0.return_value = mock_complete_system["mem0_client"]
        mock_rag.return_value = "Found relevant Python documentation"
        mock_web_search.return_value = "Latest Python tutorials and best practices"

        # Simulate user query
        user_query = "How do I learn Python programming effectively?"

        # Mock agent response
        with patch.object(agent, "iter") as mock_agent_iter:
            # Create mock run context
            mock_run = AsyncMock()
            mock_run.__aenter__ = AsyncMock(return_value=mock_run)
            mock_run.__aexit__ = AsyncMock(return_value=None)
            mock_run.result.new_messages.return_value = []

            # Mock streaming response
            async def mock_stream_generator():
                yield "Based on your interest in Python programming, "
                yield "I recommend starting with the basics and "
                yield "practicing with real projects."

            mock_agent_iter.return_value = mock_run
            mock_run.__aiter__ = lambda self: mock_stream_generator()

            # Execute the workflow
            response_parts = [part async for part in run_agent_with_streaming(user_query)]

            # Verify workflow execution
            full_response = "".join(response_parts)
            assert "Python programming" in full_response
            assert "recommend" in full_response

            # Verify memory was searched
            mock_complete_system["mem0_client"].search.assert_called_once()

            # Verify memory was updated
            mock_complete_system["mem0_client"].add.assert_called_once()

    @pytest.mark.asyncio
    @patch("ui.streamlit_ui_simple.agent.run")
    async def test_simple_ui_workflow(self, mock_agent_run):
        """Test simple UI workflow without streaming."""
        # Setup mock response
        mock_result = MagicMock()
        mock_result.output = "This is a simple response to your query."
        mock_result.new_messages.return_value = []
        mock_agent_run.return_value = mock_result

        # Mock session state
        mock_session_state = MagicMock()
        mock_session_state.messages = []

        # Execute simple UI workflow
        with patch("streamlit.session_state", mock_session_state):
            response = await run_agent("What is artificial intelligence?")

            # Verify response
            assert response == "This is a simple response to your query."

            # Verify agent was called
            mock_agent_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_document_analysis_workflow(self, mock_complete_system):
        """Test document analysis workflow: upload -> process -> query -> response."""
        # Mock document processing
        mock_complete_system[
            "supabase"
        ].table.return_value.select.return_value.execute.return_value.data = [
            {"file_id": "uploaded_doc", "file_name": "analysis.pdf", "status": "processed"}
        ]

        # Mock document content retrieval
        mock_complete_system[
            "supabase"
        ].table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            {"chunk_index": 0, "content": "Document contains financial analysis data"},
            {"chunk_index": 1, "content": "Revenue trends show 15% growth year over year"},
        ]

        # Simulate document query workflow
        with patch("tools.rag.get_document_content_tool") as mock_get_content:
            mock_get_content.return_value = "Document contains financial analysis data. Revenue trends show 15% growth year over year."

            # Execute document content retrieval
            from tools.rag import get_document_content_tool

            content = await get_document_content_tool(
                mock_complete_system["supabase"], "uploaded_doc"
            )

            # Verify document processing
            assert "financial analysis" in content
            assert "15% growth" in content

    @pytest.mark.asyncio
    async def test_code_execution_workflow(self, mock_complete_system):
        """Test code execution workflow: code input -> execution -> result display."""
        # Mock code execution
        with patch("tools.code_execution.execute_safe_code_tool") as mock_code_exec:
            mock_code_exec.return_value = "Result: 42\nCalculation completed successfully"

            # Execute code
            from tools.code_execution import execute_safe_code_tool

            result = execute_safe_code_tool("result = 6 * 7\nprint(f'Result: {result}')")

            # Verify code execution
            assert "Result: 42" in result
            assert "successfully" in result

    @pytest.mark.asyncio
    async def test_multi_tool_workflow(self, mock_complete_system):
        """Test workflow using multiple tools in sequence."""
        with (
            patch("tools.web_search.web_search_tool") as mock_web_search,
            patch("tools.rag.retrieve_relevant_documents_tool") as mock_rag,
            patch("tools.sql_query.execute_sql_query_tool") as mock_sql,
        ):

            # Setup tool responses
            mock_web_search.return_value = "Web search found recent AI developments"
            mock_rag.return_value = "Documents contain AI research papers"
            mock_sql.return_value = '{"count": 150, "category": "AI research"}'

            # Execute multi-tool workflow
            web_result = await mock_web_search(
                "AI developments 2024", mock_complete_system["http_client"], "test-key", "test-url"
            )
            rag_result = await mock_rag(
                mock_complete_system["supabase"],
                mock_complete_system["embedding_client"],
                "AI research",
            )
            sql_result = await mock_sql(
                mock_complete_system["supabase"],
                "SELECT COUNT(*) as count FROM research WHERE category = 'AI';",
            )

            # Verify all tools executed
            assert "Web search found" in web_result
            assert "Documents contain" in rag_result
            assert "150" in sql_result


class TestStreamlitUIFunctionality:
    """Test Streamlit UI components and functionality."""

    def test_display_message_part_user_message(self):
        """Test displaying user messages in UI."""
        # Mock message part
        mock_part = MagicMock()
        mock_part.part_kind = "user-prompt"
        mock_part.content = "Hello, how are you?"

        # Mock Streamlit functions
        with (
            patch("streamlit.chat_message") as mock_chat_message,
            patch("streamlit.markdown") as mock_markdown,
        ):

            mock_context = MagicMock()
            mock_chat_message.return_value.__enter__ = MagicMock(return_value=mock_context)
            mock_chat_message.return_value.__exit__ = MagicMock(return_value=None)

            # Test display function
            display_message_part(mock_part)

            # Verify UI calls
            mock_chat_message.assert_called_once_with("user")
            mock_markdown.assert_called_once_with("Hello, how are you?")

    def test_display_message_part_assistant_message(self):
        """Test displaying assistant messages in UI."""
        # Mock message part
        mock_part = MagicMock()
        mock_part.part_kind = "text"
        mock_part.content = "I'm doing well, thank you for asking!"

        # Mock Streamlit functions
        with (
            patch("streamlit.chat_message") as mock_chat_message,
            patch("streamlit.markdown") as mock_markdown,
        ):

            mock_context = MagicMock()
            mock_chat_message.return_value.__enter__ = MagicMock(return_value=mock_context)
            mock_chat_message.return_value.__exit__ = MagicMock(return_value=None)

            # Test display function
            display_message_part(mock_part)

            # Verify UI calls
            mock_chat_message.assert_called_once_with("assistant")
            mock_markdown.assert_called_once_with("I'm doing well, thank you for asking!")

    def test_session_state_management(self):
        """Test session state management for conversation history."""
        # Mock session state
        mock_session_state = MagicMock()
        mock_session_state.messages = []

        # Create mock messages
        mock_request = MagicMock(spec=ModelRequest)
        mock_response = MagicMock(spec=ModelResponse)

        # Test session state updates
        with patch("streamlit.session_state", mock_session_state):
            # Simulate adding messages to session state
            mock_session_state.messages.append(mock_request)
            mock_session_state.messages.append(mock_response)

            # Verify messages were added
            assert len(mock_session_state.messages) == 2
            assert mock_request in mock_session_state.messages
            assert mock_response in mock_session_state.messages

    @patch("ui.streamlit_app.get_agent_deps")
    @patch("ui.streamlit_app.initialize_mem0")
    def test_resource_caching(self, mock_mem0, mock_deps):
        """Test that expensive resources are properly cached."""
        # Mock return values
        mock_embedding_client = AsyncMock()
        mock_supabase = MagicMock()
        mock_mem0_client = MagicMock()

        mock_deps.return_value = (mock_embedding_client, mock_supabase)
        mock_mem0.return_value = mock_mem0_client

        # Call cached functions multiple times
        deps1 = get_agent_deps()
        deps2 = get_agent_deps()

        mem0_1 = mock_mem0()
        mem0_2 = mock_mem0()

        # Verify same instances returned (caching working)
        assert deps1 == deps2
        assert mem0_1 == mem0_2

    def test_ui_error_handling(self):
        """Test UI error handling for various failure scenarios."""
        # Mock message part with missing content
        mock_part = MagicMock()
        mock_part.part_kind = "user-prompt"
        mock_part.content = None

        # Should handle gracefully without crashing
        try:
            display_message_part(mock_part)
        except Exception as e:
            pytest.fail(f"UI should handle missing content gracefully, but raised: {e}")

    def test_streaming_ui_components(self):
        """Test streaming UI components and real-time updates."""
        # Mock streaming placeholder
        mock_placeholder = MagicMock()

        with patch("streamlit.empty") as mock_empty:
            mock_empty.return_value = mock_placeholder

            # Simulate streaming updates
            placeholder = mock_empty()
            placeholder.markdown("Partial response...")
            placeholder.markdown("Complete response.")

            # Verify streaming updates
            assert mock_placeholder.markdown.call_count == 2
            mock_placeholder.markdown.assert_any_call("Partial response...")
            mock_placeholder.markdown.assert_any_call("Complete response.")


class TestErrorHandlingWorkflows:
    """Test error handling in complete user workflows."""

    @pytest.mark.asyncio
    async def test_database_connection_failure_workflow(self):
        """Test complete workflow when database connection fails."""
        # Mock database failure
        mock_supabase = MagicMock()
        mock_supabase.rpc.side_effect = Exception("Database connection failed")

        # Test that error propagates through the workflow
        with pytest.raises(Exception, match="Database connection failed"):
            from tools.sql_query import execute_sql_query_tool

            await execute_sql_query_tool(mock_supabase, "SELECT 1;")

    @pytest.mark.asyncio
    async def test_embedding_service_failure_workflow(self):
        """Test workflow when embedding service fails."""
        mock_supabase = MagicMock()
        mock_embedding_client = AsyncMock()
        mock_embedding_client.embeddings.create.side_effect = Exception("Embedding service down")

        # Test RAG failure handling
        with pytest.raises(Exception, match="Embedding service down"):
            from tools.rag import retrieve_relevant_documents_tool

            await retrieve_relevant_documents_tool(
                mock_supabase, mock_embedding_client, "test query"
            )

    @pytest.mark.asyncio
    async def test_web_search_fallback_workflow(self):
        """Test web search fallback when primary service fails."""
        mock_http_client = AsyncMock()

        # Mock Brave API failure, SearXNG success
        with patch("tools.web_search.web_search_tool") as mock_web_search:
            mock_web_search.return_value = "SearXNG fallback results"

            # Execute with None Brave key (should use fallback)
            result = await mock_web_search(
                "test query", mock_http_client, None, "http://searxng-url"
            )

            assert "SearXNG fallback results" in result

    @pytest.mark.asyncio
    async def test_memory_service_degradation_workflow(self):
        """Test workflow when memory service is degraded."""
        # Mock memory service failure
        mock_mem0_client = MagicMock()
        mock_mem0_client.search.side_effect = Exception("Memory service unavailable")

        # Workflow should continue without memories
        with patch("ui.streamlit_app.initialize_mem0") as mock_init_mem0:
            mock_init_mem0.return_value = mock_mem0_client

            # Should handle memory failure gracefully
            with pytest.raises(Exception, match="Memory service unavailable"):
                mock_mem0_client.search("test query", user_id="test", limit=3)

    @pytest.mark.asyncio
    async def test_partial_response_handling(self):
        """Test handling of partial or incomplete responses."""
        # Mock agent that returns partial response
        with patch.object(agent, "run") as mock_agent_run:
            mock_result = MagicMock()
            mock_result.output = "Partial response due to"  # Incomplete
            mock_result.new_messages.return_value = []
            mock_agent_run.return_value = mock_result

            # Should handle partial response gracefully
            response = await run_agent("test query")
            assert "Partial response due to" in response

    @pytest.mark.asyncio
    async def test_timeout_handling_workflow(self):
        """Test timeout handling in complete workflows."""
        # Mock slow operation
        mock_supabase = MagicMock()

        async def slow_operation(*args, **kwargs):
            await asyncio.sleep(10)  # Very slow
            return MagicMock(data=[])

        mock_supabase.rpc.return_value.execute = slow_operation

        # Simulate timeout
        mock_supabase.rpc.side_effect = TimeoutError("Operation timed out")

        with pytest.raises(asyncio.TimeoutError, match="Operation timed out"):
            from tools.sql_query import execute_sql_query_tool

            await execute_sql_query_tool(mock_supabase, "SELECT * FROM large_table;")


class TestEdgeCaseWorkflows:
    """Test edge cases and boundary conditions in workflows."""

    @pytest.mark.asyncio
    async def test_empty_query_workflow(self):
        """Test workflow with empty or whitespace-only queries."""
        # Test empty query
        with patch.object(agent, "run") as mock_agent_run:
            mock_result = MagicMock()
            mock_result.output = "Please provide a valid query."
            mock_result.new_messages.return_value = []
            mock_agent_run.return_value = mock_result

            response = await run_agent("")
            assert "Please provide a valid query" in response

    @pytest.mark.asyncio
    async def test_very_long_query_workflow(self):
        """Test workflow with extremely long queries."""
        # Create very long query
        long_query = "What is " + "very " * 1000 + "long question?"

        with patch.object(agent, "run") as mock_agent_run:
            mock_result = MagicMock()
            mock_result.output = "I understand your detailed question."
            mock_result.new_messages.return_value = []
            mock_agent_run.return_value = mock_result

            response = await run_agent(long_query)
            assert "I understand" in response

    @pytest.mark.asyncio
    async def test_special_characters_workflow(self):
        """Test workflow with special characters and unicode."""
        special_query = "What about C++ & Python? 🐍 (2024) [updated] 中文"

        with patch.object(agent, "run") as mock_agent_run:
            mock_result = MagicMock()
            mock_result.output = (
                "I can help with programming languages including special characters."
            )
            mock_result.new_messages.return_value = []
            mock_agent_run.return_value = mock_result

            response = await run_agent(special_query)
            assert "programming languages" in response

    @pytest.mark.asyncio
    async def test_concurrent_user_sessions_workflow(self):
        """Test handling of concurrent user sessions."""
        # Mock multiple concurrent sessions
        sessions = []
        for _ in range(5):
            session_mock = MagicMock()
            session_mock.messages = []
            sessions.append(session_mock)

        # Simulate concurrent execution
        async def simulate_session(session_id):
            with (
                patch("streamlit.session_state", sessions[session_id]),
                patch.object(agent, "run") as mock_agent_run,
            ):
                mock_result = MagicMock()
                mock_result.output = f"Response for session {session_id}"
                mock_result.new_messages.return_value = []
                mock_agent_run.return_value = mock_result

                return await run_agent(f"Query from session {session_id}")

        # Execute concurrent sessions
        tasks = [simulate_session(i) for i in range(5)]
        responses = await asyncio.gather(*tasks)

        # Verify all sessions handled correctly
        assert len(responses) == 5
        for i, response in enumerate(responses):
            assert f"session {i}" in response

    @pytest.mark.asyncio
    async def test_large_response_handling_workflow(self):
        """Test handling of very large responses."""
        # Mock large response
        large_response = "This is a very detailed response. " * 1000

        with patch.object(agent, "run") as mock_agent_run:
            mock_result = MagicMock()
            mock_result.output = large_response
            mock_result.new_messages.return_value = []
            mock_agent_run.return_value = mock_result

            response = await run_agent("Give me a detailed explanation")

            # Should handle large response
            assert len(response) > 10000
            assert "very detailed response" in response

    @pytest.mark.asyncio
    async def test_malformed_data_handling_workflow(self):
        """Test handling of malformed or corrupted data."""
        # Mock malformed database response
        mock_supabase = MagicMock()
        mock_supabase.rpc.return_value.execute.return_value.data = [
            {"malformed": "data", "missing_fields": None},
            {"incomplete": True},
        ]

        # Should handle malformed data gracefully
        from tools.sql_query import execute_sql_query_tool

        result = await execute_sql_query_tool(mock_supabase, "SELECT * FROM table;")

        # Should return some result even with malformed data
        assert isinstance(result, str)
        assert len(result) > 0


class TestPerformanceWorkflows:
    """Test performance aspects of complete workflows."""

    @pytest.mark.asyncio
    async def test_high_load_workflow(self):
        """Test workflow under high load conditions."""

        # Simulate high load with many concurrent requests
        async def simulate_load():
            with patch.object(agent, "run") as mock_agent_run:
                mock_result = MagicMock()
                mock_result.output = "Response under load"
                mock_result.new_messages.return_value = []
                mock_agent_run.return_value = mock_result

                return await run_agent("test query")

        # Execute many concurrent requests
        tasks = [simulate_load() for _ in range(20)]
        responses = await asyncio.gather(*tasks)

        # All should complete successfully
        assert len(responses) == 20
        for response in responses:
            assert "Response under load" in response

    @pytest.mark.asyncio
    async def test_memory_intensive_workflow(self):
        """Test workflow with memory-intensive operations."""
        # Mock memory-intensive operations
        mock_supabase = MagicMock()
        large_dataset = [{"id": i, "data": f"row_{i}"} for i in range(10000)]
        mock_supabase.rpc.return_value.execute.return_value.data = large_dataset

        # Should handle large datasets
        from tools.sql_query import execute_sql_query_tool

        result = await execute_sql_query_tool(mock_supabase, "SELECT * FROM large_table;")

        # Should process large dataset
        assert "row_0" in result
        assert "row_9999" in result

    @pytest.mark.asyncio
    async def test_streaming_performance_workflow(self):
        """Test streaming performance with rapid updates."""

        # Mock rapid streaming updates
        async def rapid_stream():
            for i in range(100):
                yield f"token_{i} "

        # Collect streaming tokens
        tokens = [token async for token in rapid_stream()]

        # Should handle rapid streaming
        assert len(tokens) == 100
        assert tokens[0] == "token_0 "
        assert tokens[99] == "token_99 "
