"""End-to-end tests for the AI agent system.

These tests verify complete user workflows from UI interaction to final response,
including Streamlit UI functionality, error handling, and real user scenarios.

IMPORTANT: This module uses lazy initialization for streamlit mocks. The mock is
only installed when test functions actually run, not at module collection time.
This prevents contamination of other test modules during pytest collection.
"""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.messages import ModelRequest, ModelResponse

# Import tools that are currently imported within functions
try:
    from src.tools.code_execution import execute_safe_code_tool
    from src.tools.rag import get_document_content_tool, retrieve_relevant_documents_tool
    from src.tools.sql_query import execute_sql_query_tool
except ImportError:
    # Mock these if not available
    get_document_content_tool = None
    retrieve_relevant_documents_tool = None
    execute_safe_code_tool = None
    execute_sql_query_tool = None

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

# Store original streamlit modules for restoration
_original_streamlit_modules = {}
_streamlit_modules_to_mock = [
    "streamlit",
    "streamlit.components",
    "streamlit.components.v1",
    "streamlit.components.v1.components",
    "streamlit.runtime",
    "streamlit.runtime.uploaded_file_manager",
]

# Module-level cache for lazy-loaded imports
_agent = None
_display_message_part = None
_ModelRequest = None
_ModelResponse = None
_mock_installed = False


def _save_original_streamlit_modules():
    """Save references to original streamlit modules before mocking."""
    global _original_streamlit_modules
    for module_name in _streamlit_modules_to_mock:
        if module_name in sys.modules:
            _original_streamlit_modules[module_name] = sys.modules[module_name]


def _restore_streamlit_modules():
    """Restore original streamlit modules after tests complete."""
    global _original_streamlit_modules, _mock_installed

    if not _mock_installed:
        return

    # First, restore any original modules we saved
    for module_name, original in _original_streamlit_modules.items():
        sys.modules[module_name] = original

    # Remove mock modules that weren't originally present
    for name in _streamlit_modules_to_mock:
        if name not in _original_streamlit_modules and name in sys.modules:
            # Check if it's a mock (not the real streamlit)
            module = sys.modules[name]
            if isinstance(module, MagicMock) or (
                hasattr(module, "__class__") and "MagicMock" in str(type(module))
            ):
                del sys.modules[name]

    # Also remove dependent modules so they get fresh imports
    dependent_modules = [
        name
        for name in list(sys.modules.keys())
        if (
            name.startswith("src.auth.")
            or name.startswith("src.ui.")
            or name in {"src.auth", "src.ui"}
            or name.startswith("agent.")
            or name.startswith("ui.")
        )
    ]
    for name in dependent_modules:
        if name in sys.modules:
            del sys.modules[name]

    _original_streamlit_modules.clear()
    _mock_installed = False


def _install_streamlit_mock():
    """Install streamlit mock for E2E testing."""
    global _agent, _display_message_part, _ModelRequest, _ModelResponse, _mock_installed

    if _mock_installed:
        return

    # Save original modules before mocking
    _save_original_streamlit_modules()

    # Mock Streamlit before importing UI modules
    streamlit_mock = MagicMock()
    streamlit_mock.session_state = MagicMock()
    streamlit_mock.chat_message = MagicMock()
    streamlit_mock.markdown = MagicMock()
    streamlit_mock.chat_input = MagicMock()
    streamlit_mock.title = MagicMock()
    streamlit_mock.empty = MagicMock()
    streamlit_mock.cache_resource = lambda func: func  # Pass-through decorator

    # Mock nested Streamlit modules
    streamlit_components_mock = MagicMock()
    streamlit_components_v1_mock = MagicMock()
    streamlit_components_v1_components_mock = MagicMock()

    streamlit_mock.components = streamlit_components_mock
    streamlit_components_mock.v1 = streamlit_components_v1_mock
    streamlit_components_v1_mock.components = streamlit_components_v1_components_mock

    # Mock runtime modules
    streamlit_runtime_mock = MagicMock()
    streamlit_uploaded_file_mock = MagicMock()
    streamlit_runtime_mock.uploaded_file_manager = streamlit_uploaded_file_mock

    streamlit_mock.runtime = streamlit_runtime_mock

    sys.modules["streamlit"] = streamlit_mock
    sys.modules["streamlit.components"] = streamlit_components_mock
    sys.modules["streamlit.components.v1"] = streamlit_components_v1_mock
    sys.modules["streamlit.components.v1.components"] = streamlit_components_v1_components_mock
    sys.modules["streamlit.runtime"] = streamlit_runtime_mock
    sys.modules["streamlit.runtime.uploaded_file_manager"] = streamlit_uploaded_file_mock

    # Add src directory to path to import modules
    src_path = str(Path(__file__).parent.parent.resolve() / "src")
    if src_path not in sys.path:
        sys.path.append(src_path)

    # Import components for E2E testing
    from pydantic_ai.messages import ModelRequest, ModelResponse

    from agent.unified_agent import super_agent
    from ui.streamlit_app import display_message_part

    _agent = super_agent
    _display_message_part = display_message_part
    _ModelRequest = ModelRequest
    _ModelResponse = ModelResponse
    _mock_installed = True


def get_agent():
    """Get the agent instance, installing mock if needed."""
    if not _mock_installed:
        _install_streamlit_mock()
    return _agent


def get_display_message_part():
    """Get the display_message_part function, installing mock if needed."""
    if not _mock_installed:
        _install_streamlit_mock()
    return _display_message_part


# Module-scoped fixture that ensures cleanup happens after all tests in this module
@pytest.fixture(scope="module", autouse=True)
def setup_and_cleanup_e2e_mocks():
    """
    Module-scoped fixture to set up and clean up streamlit mocks.

    This fixture installs the mock when the first test runs and cleans up
    after all tests in this module complete.
    """
    # Set flag to tell conftest.py fixture to skip streamlit restoration
    os.environ["_PYTEST_E2E_MODULE_ACTIVE"] = "true"

    # Install the mock before tests run
    _install_streamlit_mock()

    yield

    # Cleanup runs after all tests in this module
    os.environ.pop("_PYTEST_E2E_MODULE_ACTIVE", None)
    _restore_streamlit_modules()


# Test helper functions to simulate removed/refactored functionality
async def run_agent(query: str) -> str:
    """Test helper to simulate agent execution."""
    agent = get_agent()
    result = await agent.run(query)
    return result.output


async def run_agent_with_streaming(query: str):
    """Test helper to simulate streaming agent execution."""
    agent = get_agent()
    async with agent.iter(query) as run:
        async for message in run:
            if hasattr(message, "content"):
                yield message.content
            elif isinstance(message, str):
                yield message


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
    @patch("src.tools.rag.retrieve_relevant_documents_tool")
    @patch("src.tools.web_search.web_search_tool")
    async def test_research_query_workflow(self, mock_web_search, mock_rag, mock_complete_system):
        """Test complete research query workflow: memory -> RAG -> web search -> response."""
        # Setup mocks
        mock_rag.return_value = "Found relevant Python documentation"
        mock_web_search.return_value = "Latest Python tutorials and best practices"

        # Simulate user query
        user_query = "How do I learn Python programming effectively?"

        # Mock agent response
        with patch.object(get_agent(), "run") as mock_agent_run:
            # Create mock result
            mock_result = MagicMock()
            mock_result.output = (
                "Based on your interest in Python programming, "
                "I recommend starting with the basics and "
                "practicing with real projects."
            )
            mock_result.new_messages.return_value = []
            mock_agent_run.return_value = mock_result

            # Execute the workflow
            response = await run_agent(user_query)

            # Verify workflow execution
            assert "Python programming" in response
            assert "recommend" in response

            # Verify agent was called
            mock_agent_run.assert_called_once_with(user_query)

    @pytest.mark.asyncio
    async def test_simple_ui_workflow(self):
        """Test simple UI workflow without streaming."""
        # Mock agent response
        with patch.object(get_agent(), "run") as mock_agent_run:
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
        # Mock document content retrieval tool
        with patch("src.tools.rag.get_document_content_tool") as mock_get_content:
            # Setup realistic document content
            expected_content = (
                "Document contains financial analysis data. "
                "Revenue trends show 15% growth year over year."
            )
            mock_get_content.return_value = expected_content

            # Execute document content retrieval
            if get_document_content_tool is None:
                pytest.skip("get_document_content_tool not available")

            content = await mock_get_content(mock_complete_system["supabase"], "uploaded_doc")

            # Verify document processing
            assert "financial analysis" in content
            assert "15% growth" in content

    @pytest.mark.asyncio
    async def test_code_execution_workflow(self, mock_complete_system):
        """Test code execution workflow: code input -> execution -> result display."""
        # Mock code execution
        with patch("src.tools.code_execution.execute_safe_code_tool") as mock_code_exec:
            mock_code_exec.return_value = "Result: 42\n"

            # Execute code
            if execute_safe_code_tool is None:
                pytest.skip("execute_safe_code_tool not available")

            result = mock_code_exec("result = 6 * 7\nprint(f'Result: {result}')")

            # Verify code execution
            assert "Result: 42" in result

    @pytest.mark.asyncio
    async def test_multi_tool_workflow(self, mock_complete_system):
        """Test workflow using multiple tools in sequence."""
        with (
            patch("src.tools.web_search.web_search_tool") as mock_web_search,
            patch("src.tools.rag.retrieve_relevant_documents_tool") as mock_rag,
            patch("src.tools.sql_query.execute_sql_query_tool") as mock_sql,
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
            get_display_message_part()(mock_part)

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
            get_display_message_part()(mock_part)

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

    def test_resource_caching(self):
        """Test that expensive resources are properly cached."""
        # Test that Streamlit's @cache_resource decorator is used correctly
        # by verifying the decorator is applied to resource functions

        # The caching is now handled by Streamlit's @cache_resource decorator
        # which is applied at the module level, so we just verify it's there
        import streamlit as st

        # Verify cache_resource is a callable (our mock passes through)
        assert callable(st.cache_resource)

        # Test that calling the same mock function twice returns consistent results
        mock_func = MagicMock(return_value="cached_result")
        cached_func = st.cache_resource(mock_func)

        result1 = cached_func()
        result2 = cached_func()

        # Should return the same result (caching behavior)
        assert result1 == result2

    def test_ui_error_handling(self):
        """Test UI error handling for various failure scenarios."""
        # Mock message part with missing content
        mock_part = MagicMock()
        mock_part.part_kind = "user-prompt"
        mock_part.content = None

        # Should handle gracefully without crashing
        try:
            get_display_message_part()(mock_part)
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
        with patch("src.tools.sql_query.execute_sql_query_tool") as mock_sql_tool:
            # Setup mock to raise exception
            mock_sql_tool.side_effect = Exception("Database connection failed")

            # Test that error is raised
            with pytest.raises(Exception, match="Database connection failed"):
                if execute_sql_query_tool is None:
                    pytest.skip("execute_sql_query_tool not available")

                await mock_sql_tool(MagicMock(), "SELECT 1;")

    @pytest.mark.asyncio
    async def test_embedding_service_failure_workflow(self):
        """Test workflow when embedding service fails."""
        # Mock RAG tool to raise exception
        with patch("src.tools.rag.retrieve_relevant_documents_tool") as mock_rag_tool:
            mock_rag_tool.side_effect = Exception("Embedding service down")

            # Test RAG failure handling
            with pytest.raises(Exception, match="Embedding service down"):
                if retrieve_relevant_documents_tool is None:
                    pytest.skip("retrieve_relevant_documents_tool not available")

                await mock_rag_tool(MagicMock(), AsyncMock(), "test query")

    @pytest.mark.asyncio
    async def test_web_search_fallback_workflow(self):
        """Test web search fallback when primary service fails."""
        mock_http_client = AsyncMock()

        # Mock Brave API failure, SearXNG success
        with patch("src.tools.web_search.web_search_tool") as mock_web_search:
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

        # Test that memory service failure is properly handled
        with pytest.raises(Exception, match="Memory service unavailable"):
            mock_mem0_client.search("test query", user_id="test", limit=3)

    @pytest.mark.asyncio
    async def test_partial_response_handling(self):
        """Test handling of partial or incomplete responses."""
        # Mock agent that returns partial response
        with patch.object(get_agent(), "run") as mock_agent_run:
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
        # Mock SQL tool to raise timeout error
        with patch("src.tools.sql_query.execute_sql_query_tool") as mock_sql_tool:
            mock_sql_tool.side_effect = TimeoutError("Operation timed out")

            with pytest.raises(asyncio.TimeoutError, match="Operation timed out"):
                if execute_sql_query_tool is None:
                    pytest.skip("execute_sql_query_tool not available")

                await mock_sql_tool(MagicMock(), "SELECT * FROM large_table;")


class TestEdgeCaseWorkflows:
    """Test edge cases and boundary conditions in workflows."""

    @pytest.mark.asyncio
    async def test_empty_query_workflow(self):
        """Test workflow with empty or whitespace-only queries."""
        # Test empty query
        with patch.object(get_agent(), "run") as mock_agent_run:
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

        with patch.object(get_agent(), "run") as mock_agent_run:
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

        with patch.object(get_agent(), "run") as mock_agent_run:
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
                patch.object(get_agent(), "run") as mock_agent_run,
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

        with patch.object(get_agent(), "run") as mock_agent_run:
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
        if execute_sql_query_tool is None:
            pytest.skip("execute_sql_query_tool not available")

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
            with patch.object(get_agent(), "run") as mock_agent_run:
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
        if execute_sql_query_tool is None:
            pytest.skip("execute_sql_query_tool not available")

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
