import pytest
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock, call
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerHTTP
from dataclasses import dataclass
from typing import List, Optional

# Mock environment variables before importing modules that use them
TEST_ENV_VARS = {
    'LLM_PROVIDER': 'openai',
    'LLM_BASE_URL': 'https://api.openai.com/v1',
    'LLM_API_KEY': 'test-api-key',
    'LLM_CHOICE': 'gpt-4o-mini',
    'VISION_LLM_CHOICE': 'gpt-4o-mini',
    'EMBEDDING_PROVIDER': 'openai',
    'EMBEDDING_BASE_URL': 'https://api.openai.com/v1',
    'EMBEDDING_API_KEY': 'test-api-key',
    'EMBEDDING_MODEL_CHOICE': 'text-embedding-3-small',
    'SUPABASE_URL': 'https://test-supabase-url.com',
    'SUPABASE_SERVICE_KEY': 'test-supabase-key',
    'BRAVE_API_KEY': 'test-brave-key',
    'SEARXNG_BASE_URL': 'http://test-searxng-url.com'
}

with patch.dict(os.environ, TEST_ENV_VARS):
    # Add src directory to path to import the agent module
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
    from agent.agent import agent, AgentDeps, get_model, add_memories, web_search, retrieve_relevant_documents, list_documents, get_document_content, execute_sql_query, image_analysis, execute_code
    from agent.prompt import AGENT_SYSTEM_PROMPT
    import tools.web_search
    import tools.rag
    import tools.sql_query
    import tools.image_analysis
    import tools.code_execution


# Test fixtures
@pytest.fixture
def mock_agent_deps():
    """Create a mock AgentDeps instance for testing."""
    deps = MagicMock(spec=AgentDeps)
    deps.supabase = MagicMock()
    deps.embedding_client = AsyncMock()
    deps.http_client = AsyncMock()
    deps.brave_api_key = "test-brave-key"
    deps.searxng_base_url = "http://test-searxng-url.com"
    deps.memories = "Test memory 1\nTest memory 2"
    return deps

@pytest.fixture
def mock_run_context(mock_agent_deps):
    """Create a mock RunContext with AgentDeps."""
    ctx = MagicMock(spec=RunContext)
    ctx.deps = mock_agent_deps
    return ctx


class TestAgentInitialization:
    """Test agent initialization and configuration."""

    def test_get_model_default_configuration(self):
        """Test get_model with default environment variables."""
        model = get_model()
        assert model.model_name == 'gpt-4o-mini'
        assert model.provider.base_url == 'https://api.openai.com/v1'
        assert model.provider.api_key == 'test-api-key'

    @patch.dict(os.environ, {'LLM_CHOICE': 'gpt-4', 'LLM_BASE_URL': 'https://custom-api.com/v1', 'LLM_API_KEY': 'custom-key'})
    def test_get_model_custom_configuration(self):
        """Test get_model with custom environment variables."""
        model = get_model()
        assert model.model_name == 'gpt-4'
        assert model.provider.base_url == 'https://custom-api.com/v1'
        assert model.provider.api_key == 'custom-key'

    @patch.dict(os.environ, {}, clear=True)
    def test_get_model_fallback_values(self):
        """Test get_model with missing environment variables uses fallbacks."""
        model = get_model()
        assert model.model_name == 'gpt-4o-mini'  # Default fallback
        assert model.provider.base_url == 'https://api.openai.com/v1'  # Default fallback
        assert model.provider.api_key == 'ollama'  # Default fallback

    def test_agent_creation_properties(self):
        """Test basic agent creation and properties."""
        assert isinstance(agent, Agent)
        assert agent.system_prompt == AGENT_SYSTEM_PROMPT
        assert agent.deps_type == AgentDeps
        assert agent.retries == 2

    def test_agent_deps_dataclass_structure(self):
        """Test AgentDeps dataclass has correct fields."""
        import inspect
        fields = [field.name for field in AgentDeps.__dataclass_fields__.values()]
        expected_fields = ['supabase', 'embedding_client', 'http_client', 'brave_api_key', 'searxng_base_url', 'memories']
        for field in expected_fields:
            assert field in fields, f"Missing field: {field}"

    def test_agent_has_required_tools(self):
        """Test that agent has all expected tools registered."""
        tool_names = [tool.name for tool in agent.tools]
        expected_tools = ['web_search', 'retrieve_relevant_documents', 'list_documents',
                         'get_document_content', 'execute_sql_query', 'image_analysis', 'execute_code']
        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Missing tool: {tool_name}"

class TestAgentSystemPrompts:
    """Test system prompt functionality and memory integration."""

    def test_add_memories_system_prompt(self, mock_run_context):
        """Test add_memories function with basic memories."""
        mock_run_context.deps.memories = "Memory 1\nMemory 2"

        prompt = add_memories(mock_run_context)
        assert prompt == "\nUser Memories:\nMemory 1\nMemory 2"

    def test_add_memories_empty_memories(self, mock_run_context):
        """Test add_memories function with empty memories."""
        mock_run_context.deps.memories = ""

        prompt = add_memories(mock_run_context)
        assert prompt == "\nUser Memories:\n"

    def test_add_memories_multiline_memories(self, mock_run_context):
        """Test add_memories function with complex multiline memories."""
        complex_memories = "User prefers Python\nLikes AI/ML topics\nWorks in tech industry\nTimezone: UTC-8"
        mock_run_context.deps.memories = complex_memories

        prompt = add_memories(mock_run_context)
        expected = f"\nUser Memories:\n{complex_memories}"
        assert prompt == expected

    def test_system_prompt_content(self):
        """Test that system prompt contains expected content."""
        assert "intelligent AI assistant" in AGENT_SYSTEM_PROMPT.lower()
        assert "tool" in AGENT_SYSTEM_PROMPT.lower()
        assert "memory" in AGENT_SYSTEM_PROMPT.lower()
        assert "document" in AGENT_SYSTEM_PROMPT.lower()

    def test_system_prompt_structure(self):
        """Test system prompt has proper structure and sections."""
        prompt_lower = AGENT_SYSTEM_PROMPT.lower()
        expected_sections = ["goal:", "tool instructions:", "output format:", "misc instructions:"]
        for section in expected_sections:
            assert section in prompt_lower, f"Missing section: {section}"

class TestAgentTools:
    """Test agent tool integration and functionality."""

    @pytest.mark.asyncio
    @patch('tools.web_search.web_search_tool')
    async def test_web_search_tool_success(self, mock_web_search_tool, mock_run_context):
        """Test successful web search tool execution."""
        mock_web_search_tool.return_value = "Web search result for test query"

        result = await web_search(mock_run_context, "test query")

        mock_web_search_tool.assert_called_once_with(
            "test query",
            mock_run_context.deps.http_client,
            "test-brave-key",
            "http://test-searxng-url.com"
        )
        assert result == "Web search result for test query"

    @pytest.mark.asyncio
    @patch('tools.web_search.web_search_tool')
    async def test_web_search_tool_with_none_brave_key(self, mock_web_search_tool, mock_run_context):
        """Test web search tool when Brave API key is None."""
        mock_run_context.deps.brave_api_key = None
        mock_web_search_tool.return_value = "SearXNG search result"

        result = await web_search(mock_run_context, "test query")

        mock_web_search_tool.assert_called_once_with(
            "test query",
            mock_run_context.deps.http_client,
            None,
            "http://test-searxng-url.com"
        )
        assert result == "SearXNG search result"

    @pytest.mark.asyncio
    @patch('tools.web_search.web_search_tool')
    async def test_web_search_tool_exception_handling(self, mock_web_search_tool, mock_run_context):
        """Test web search tool handles exceptions properly."""
        mock_web_search_tool.side_effect = Exception("Network error")

        with pytest.raises(Exception, match="Network error"):
            await web_search(mock_run_context, "test query")

    @pytest.mark.asyncio
    @patch('tools.rag.retrieve_relevant_documents_tool')
    async def test_retrieve_relevant_documents_success(self, mock_retrieve_relevant_documents_tool, mock_run_context):
        """Test successful document retrieval."""
        expected_result = "Document 1: Content about AI\nDocument 2: Content about ML"
        mock_retrieve_relevant_documents_tool.return_value = expected_result

        result = await retrieve_relevant_documents(mock_run_context, "AI and machine learning")

        mock_retrieve_relevant_documents_tool.assert_called_once_with(
            mock_run_context.deps.supabase,
            mock_run_context.deps.embedding_client,
            "AI and machine learning"
        )
        assert result == expected_result

    @pytest.mark.asyncio
    @patch('tools.rag.retrieve_relevant_documents_tool')
    async def test_retrieve_relevant_documents_empty_query(self, mock_retrieve_relevant_documents_tool, mock_run_context):
        """Test document retrieval with empty query."""
        mock_retrieve_relevant_documents_tool.return_value = "No relevant documents found"

        result = await retrieve_relevant_documents(mock_run_context, "")

        mock_retrieve_relevant_documents_tool.assert_called_once_with(
            mock_run_context.deps.supabase,
            mock_run_context.deps.embedding_client,
            ""
        )
        assert result == "No relevant documents found"

    @pytest.mark.asyncio
    @patch('tools.rag.list_documents_tool')
    async def test_list_documents_success(self, mock_list_documents_tool, mock_run_context):
        """Test successful document listing."""
        expected_docs = ["document1.pdf", "document2.txt", "image1.jpg"]
        mock_list_documents_tool.return_value = expected_docs

        result = await list_documents(mock_run_context)

        mock_list_documents_tool.assert_called_once_with(mock_run_context.deps.supabase)
        assert result == expected_docs

    @pytest.mark.asyncio
    @patch('tools.rag.list_documents_tool')
    async def test_list_documents_empty_result(self, mock_list_documents_tool, mock_run_context):
        """Test document listing when no documents exist."""
        mock_list_documents_tool.return_value = []

        result = await list_documents(mock_run_context)

        mock_list_documents_tool.assert_called_once_with(mock_run_context.deps.supabase)
        assert result == []

    @pytest.mark.asyncio
    @patch('tools.rag.get_document_content_tool')
    async def test_get_document_content_success(self, mock_get_document_content_tool, mock_run_context):
        """Test successful document content retrieval."""
        expected_content = "This is the full content of the document with multiple paragraphs..."
        mock_get_document_content_tool.return_value = expected_content

        result = await get_document_content(mock_run_context, "doc123")

        mock_get_document_content_tool.assert_called_once_with(mock_run_context.deps.supabase, "doc123")
        assert result == expected_content

    @pytest.mark.asyncio
    @patch('tools.rag.get_document_content_tool')
    async def test_get_document_content_not_found(self, mock_get_document_content_tool, mock_run_context):
        """Test document content retrieval for non-existent document."""
        mock_get_document_content_tool.return_value = "Document not found"

        result = await get_document_content(mock_run_context, "nonexistent_doc")

        mock_get_document_content_tool.assert_called_once_with(mock_run_context.deps.supabase, "nonexistent_doc")
        assert result == "Document not found"

    @pytest.mark.asyncio
    @patch('tools.sql_query.execute_sql_query_tool')
    async def test_execute_sql_query_success(self, mock_execute_sql_query_tool, mock_run_context):
        """Test successful SQL query execution."""
        expected_result = '{"rows": [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]}'
        mock_execute_sql_query_tool.return_value = expected_result

        result = await execute_sql_query(mock_run_context, "SELECT id, name FROM users LIMIT 2;")

        mock_execute_sql_query_tool.assert_called_once_with(mock_run_context.deps.supabase, "SELECT id, name FROM users LIMIT 2;")
        assert result == expected_result

    @pytest.mark.asyncio
    @patch('tools.sql_query.execute_sql_query_tool')
    async def test_execute_sql_query_complex(self, mock_execute_sql_query_tool, mock_run_context):
        """Test complex SQL query with JSON operations."""
        complex_query = "SELECT AVG((row_data->>'revenue')::numeric) FROM document_rows WHERE dataset_id = '123';"
        expected_result = '{"average_revenue": 50000.0}'
        mock_execute_sql_query_tool.return_value = expected_result

        result = await execute_sql_query(mock_run_context, complex_query)

        mock_execute_sql_query_tool.assert_called_once_with(mock_run_context.deps.supabase, complex_query)
        assert result == expected_result

    @pytest.mark.asyncio
    @patch('tools.image_analysis.image_analysis_tool')
    async def test_image_analysis_success(self, mock_image_analysis_tool, mock_run_context):
        """Test successful image analysis."""
        expected_analysis = "The image shows a cat sitting on a windowsill with sunlight streaming in."
        mock_image_analysis_tool.return_value = expected_analysis

        result = await image_analysis(mock_run_context, "cat_image.jpg", "describe what you see")

        mock_image_analysis_tool.assert_called_once_with(mock_run_context.deps.supabase, "cat_image.jpg", "describe what you see")
        assert result == expected_analysis

    @pytest.mark.asyncio
    @patch('tools.code_execution.execute_safe_code_tool')
    async def test_execute_code_success(self, mock_execute_safe_code_tool, mock_run_context):
        """Test successful code execution."""
        code = "result = 2 + 2\nprint(f'Result: {result}')"
        expected_output = "Result: 4"
        mock_execute_safe_code_tool.return_value = expected_output

        result = await execute_code(mock_run_context, code)

        mock_execute_safe_code_tool.assert_called_once_with(code)
        assert result == expected_output

    @pytest.mark.asyncio
    @patch('tools.code_execution.execute_safe_code_tool')
    async def test_execute_code_with_error(self, mock_execute_safe_code_tool, mock_run_context):
        """Test code execution with syntax error."""
        invalid_code = "print('hello'"  # Missing closing parenthesis
        error_message = "SyntaxError: unexpected EOF while parsing"
        mock_execute_safe_code_tool.return_value = error_message

        result = await execute_code(mock_run_context, invalid_code)

        mock_execute_safe_code_tool.assert_called_once_with(invalid_code)
        assert result == error_message


class TestAgentErrorHandling:
    """Test agent error handling and edge cases."""

    @pytest.mark.asyncio
    @patch('tools.web_search.web_search_tool')
    async def test_tool_timeout_handling(self, mock_web_search_tool, mock_run_context):
        """Test handling of tool timeouts."""
        import asyncio
        mock_web_search_tool.side_effect = asyncio.TimeoutError("Request timed out")

        with pytest.raises(asyncio.TimeoutError):
            await web_search(mock_run_context, "test query")

    @pytest.mark.asyncio
    @patch('tools.rag.retrieve_relevant_documents_tool')
    async def test_database_connection_error(self, mock_retrieve_relevant_documents_tool, mock_run_context):
        """Test handling of database connection errors."""
        mock_retrieve_relevant_documents_tool.side_effect = ConnectionError("Database connection failed")

        with pytest.raises(ConnectionError):
            await retrieve_relevant_documents(mock_run_context, "test query")

    @pytest.mark.asyncio
    async def test_invalid_agent_deps(self):
        """Test agent behavior with invalid dependencies."""
        invalid_ctx = MagicMock(spec=RunContext)
        invalid_ctx.deps = None

        with pytest.raises(AttributeError):
            await web_search(invalid_ctx, "test query")

    def test_agent_deps_validation(self):
        """Test AgentDeps field validation."""
        # Test that AgentDeps can be created with proper types
        from httpx import AsyncClient
        from supabase import Client
        from openai import AsyncOpenAI

        # Mock the required types
        mock_supabase = MagicMock(spec=Client)
        mock_embedding_client = MagicMock(spec=AsyncOpenAI)
        mock_http_client = MagicMock(spec=AsyncClient)

        deps = AgentDeps(
            supabase=mock_supabase,
            embedding_client=mock_embedding_client,
            http_client=mock_http_client,
            brave_api_key="test-key",
            searxng_base_url="http://test.com",
            memories="test memories"
        )

        assert deps.supabase == mock_supabase
        assert deps.embedding_client == mock_embedding_client
        assert deps.http_client == mock_http_client
        assert deps.brave_api_key == "test-key"
        assert deps.searxng_base_url == "http://test.com"
        assert deps.memories == "test memories"


class TestAgentEdgeCases:
    """Test agent behavior in edge cases and boundary conditions."""

    @pytest.mark.asyncio
    @patch('tools.web_search.web_search_tool')
    async def test_empty_search_query(self, mock_web_search_tool, mock_run_context):
        """Test web search with empty query."""
        mock_web_search_tool.return_value = "Please provide a search query"

        result = await web_search(mock_run_context, "")

        mock_web_search_tool.assert_called_once_with("", mock_run_context.deps.http_client, "test-brave-key", "http://test-searxng-url.com")
        assert result == "Please provide a search query"

    @pytest.mark.asyncio
    @patch('tools.web_search.web_search_tool')
    async def test_very_long_search_query(self, mock_web_search_tool, mock_run_context):
        """Test web search with very long query."""
        long_query = "a" * 1000  # 1000 character query
        mock_web_search_tool.return_value = "Search results for long query"

        result = await web_search(mock_run_context, long_query)

        mock_web_search_tool.assert_called_once()
        assert result == "Search results for long query"

    @pytest.mark.asyncio
    @patch('tools.rag.retrieve_relevant_documents_tool')
    async def test_special_characters_in_query(self, mock_retrieve_relevant_documents_tool, mock_run_context):
        """Test document retrieval with special characters."""
        special_query = "What about C++ & Python? (2024) [updated]"
        mock_retrieve_relevant_documents_tool.return_value = "Documents about programming languages"

        result = await retrieve_relevant_documents(mock_run_context, special_query)

        mock_retrieve_relevant_documents_tool.assert_called_once_with(
            mock_run_context.deps.supabase,
            mock_run_context.deps.embedding_client,
            special_query
        )
        assert result == "Documents about programming languages"

    def test_memory_formatting_edge_cases(self, mock_run_context):
        """Test memory formatting with various edge cases."""
        # Test with None memories
        mock_run_context.deps.memories = None
        prompt = add_memories(mock_run_context)
        assert prompt == "\nUser Memories:\nNone"

        # Test with whitespace-only memories
        mock_run_context.deps.memories = "   \n\t  "
        prompt = add_memories(mock_run_context)
        assert prompt == "\nUser Memories:\n   \n\t  "

        # Test with very long memories
        long_memories = "Memory line " * 100
        mock_run_context.deps.memories = long_memories
        prompt = add_memories(mock_run_context)
        assert long_memories in prompt


class TestAgentConfiguration:
    """Test agent configuration and environment variable handling."""

    @patch.dict(os.environ, {'LLM_CHOICE': 'gpt-3.5-turbo'})
    def test_model_configuration_override(self):
        """Test that environment variables properly override model configuration."""
        model = get_model()
        assert model.model_name == 'gpt-3.5-turbo'

    @patch.dict(os.environ, {'LLM_BASE_URL': 'https://custom-endpoint.com/v1'})
    def test_base_url_configuration_override(self):
        """Test that base URL can be overridden via environment variables."""
        model = get_model()
        assert model.provider.base_url == 'https://custom-endpoint.com/v1'

    @patch.dict(os.environ, {'LLM_API_KEY': 'custom-api-key-12345'})
    def test_api_key_configuration_override(self):
        """Test that API key can be overridden via environment variables."""
        model = get_model()
        assert model.provider.api_key == 'custom-api-key-12345'

    def test_agent_system_prompt_immutability(self):
        """Test that system prompt is properly set and immutable."""
        original_prompt = agent.system_prompt
        assert original_prompt == AGENT_SYSTEM_PROMPT

        # Verify the prompt contains key sections
        assert "intelligent AI assistant" in original_prompt.lower()
        assert "tool instructions" in original_prompt.lower()

    def test_agent_retry_configuration(self):
        """Test that agent retry configuration is properly set."""
        assert agent.retries == 2
        assert isinstance(agent.retries, int)

    def test_agent_deps_type_configuration(self):
        """Test that agent dependencies type is properly configured."""
        assert agent.deps_type == AgentDeps

        # Verify AgentDeps has all required fields
        import dataclasses
        assert dataclasses.is_dataclass(AgentDeps)

        field_names = [field.name for field in dataclasses.fields(AgentDeps)]
        required_fields = ['supabase', 'embedding_client', 'http_client', 'brave_api_key', 'searxng_base_url', 'memories']

        for field in required_fields:
            assert field in field_names, f"Missing required field: {field}"


class TestAgentIntegration:
    """Test agent integration scenarios and workflows."""

    @pytest.mark.asyncio
    @patch('tools.rag.list_documents_tool')
    @patch('tools.rag.get_document_content_tool')
    async def test_document_workflow(self, mock_get_content, mock_list_docs, mock_run_context):
        """Test a typical document workflow: list then retrieve content."""
        # Setup mocks
        mock_list_docs.return_value = ["doc1.pdf", "doc2.txt"]
        mock_get_content.return_value = "Content of doc1.pdf"

        # Execute workflow
        docs = await list_documents(mock_run_context)
        content = await get_document_content(mock_run_context, "doc1.pdf")

        # Verify calls and results
        mock_list_docs.assert_called_once_with(mock_run_context.deps.supabase)
        mock_get_content.assert_called_once_with(mock_run_context.deps.supabase, "doc1.pdf")

        assert docs == ["doc1.pdf", "doc2.txt"]
        assert content == "Content of doc1.pdf"

    @pytest.mark.asyncio
    @patch('tools.web_search.web_search_tool')
    @patch('tools.rag.retrieve_relevant_documents_tool')
    async def test_search_and_rag_workflow(self, mock_rag, mock_web_search, mock_run_context):
        """Test combining web search with RAG retrieval."""
        # Setup mocks
        mock_web_search.return_value = "Web results about AI"
        mock_rag.return_value = "Document results about AI"

        # Execute workflow
        web_results = await web_search(mock_run_context, "artificial intelligence")
        doc_results = await retrieve_relevant_documents(mock_run_context, "artificial intelligence")

        # Verify results
        assert web_results == "Web results about AI"
        assert doc_results == "Document results about AI"

        # Verify both tools were called with the same query
        mock_web_search.assert_called_once()
        mock_rag.assert_called_once()

    def test_agent_tool_registration_completeness(self):
        """Test that all expected tools are properly registered with the agent."""
        tool_names = [tool.name for tool in agent.tools]

        expected_tools = [
            'web_search',
            'retrieve_relevant_documents',
            'list_documents',
            'get_document_content',
            'execute_sql_query',
            'image_analysis',
            'execute_code'
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Tool '{expected_tool}' not found in registered tools"

        # Verify we have the expected number of tools
        assert len(tool_names) >= len(expected_tools), "Missing some expected tools"
