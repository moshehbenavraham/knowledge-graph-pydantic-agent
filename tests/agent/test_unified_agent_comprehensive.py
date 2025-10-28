"""
Comprehensive tests for unified agent module.

Tests:
- UnifiedAgentDeps initialization
- Memory system prompt
- Smart search tool
- Graph query tool
- RAG retrieval tools
- Web search tool
- SQL query tools
- Image analysis tool
- Code execution tool
- Advanced search tools
- Main agent execution
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic_ai import RunContext

from src.agent.unified_agent import (
    UnifiedAgentDeps,
    add_memories,
    analyze_image,
    comprehensive_search,
    execute_python_code,
    execute_sql,
    get_full_document,
    iterative_search,
    list_all_documents,
    query_knowledge_graph,
    query_tabular_data,
    retrieve_documents,
    run_unified_agent,
    search_web,
    smart_search,
    super_agent,
)


@pytest.fixture
def mock_supabase():
    """Create mock Supabase client."""
    return Mock()


@pytest.fixture
def mock_embedding_client():
    """Create mock embedding client."""
    return AsyncMock()


@pytest.fixture
def mock_http_client():
    """Create mock HTTP client."""
    return AsyncMock()


@pytest.fixture
def unified_deps(mock_supabase, mock_embedding_client, mock_http_client):
    """Create UnifiedAgentDeps instance."""
    return UnifiedAgentDeps(
        supabase=mock_supabase,
        embedding_client=mock_embedding_client,
        http_client=mock_http_client,
        brave_api_key="test-brave-key",
        searxng_base_url="http://searxng:8080",
        jina_api_key="test-jina-key",
        web_search_provider="jina",
        memories="User prefers technical explanations",
        session_id="test-session",
        user_id="test-user",
    )


@pytest.fixture
def mock_run_context(unified_deps):
    """Create mock RunContext."""
    ctx = Mock(spec=RunContext)
    ctx.deps = unified_deps
    return ctx


class TestUnifiedAgentDeps:
    """Test UnifiedAgentDeps initialization."""

    def test_init_with_all_params(self, mock_supabase, mock_embedding_client, mock_http_client):
        """Test initialization with all parameters."""
        deps = UnifiedAgentDeps(
            supabase=mock_supabase,
            embedding_client=mock_embedding_client,
            http_client=mock_http_client,
            brave_api_key="brave-key",
            searxng_base_url="http://searxng:8080",
            jina_api_key="jina-key",
            web_search_provider="jina",
            memories="Test memories",
            session_id="session-123",
            user_id="user-456",
        )

        assert deps.supabase == mock_supabase
        assert deps.embedding_client == mock_embedding_client
        assert deps.http_client == mock_http_client
        assert deps.brave_api_key == "brave-key"
        assert deps.searxng_base_url == "http://searxng:8080"
        assert deps.jina_api_key == "jina-key"
        assert deps.web_search_provider == "jina"
        assert deps.memories == "Test memories"
        assert deps.session_id == "session-123"
        assert deps.user_id == "user-456"

    def test_init_with_minimal_params(self, mock_supabase, mock_embedding_client, mock_http_client):
        """Test initialization with minimal parameters."""
        deps = UnifiedAgentDeps(
            supabase=mock_supabase,
            embedding_client=mock_embedding_client,
            http_client=mock_http_client,
        )

        assert deps.supabase == mock_supabase
        assert deps.embedding_client == mock_embedding_client
        assert deps.http_client == mock_http_client
        assert deps.brave_api_key is None
        assert deps.searxng_base_url is None
        assert deps.jina_api_key is None
        assert deps.web_search_provider is None
        assert deps.memories == ""
        assert deps.session_id == "default"
        assert deps.user_id is None

    def test_search_config_default(self, mock_supabase, mock_embedding_client, mock_http_client):
        """Test default search_config is set."""
        deps = UnifiedAgentDeps(
            supabase=mock_supabase,
            embedding_client=mock_embedding_client,
            http_client=mock_http_client,
        )

        assert deps.search_config is not None
        assert deps.search_config["use_vector"] is True
        assert deps.search_config["use_graph"] is True
        assert deps.search_config["use_hybrid"] is True
        assert deps.search_config["confidence_threshold"] == 0.7
        assert deps.search_config["max_results"] == 20

    def test_search_config_custom(self, mock_supabase, mock_embedding_client, mock_http_client):
        """Test custom search_config is preserved."""
        custom_config = {
            "use_vector": False,
            "use_graph": True,
            "custom_param": "value",
        }

        deps = UnifiedAgentDeps(
            supabase=mock_supabase,
            embedding_client=mock_embedding_client,
            http_client=mock_http_client,
            search_config=custom_config,
        )

        assert deps.search_config == custom_config
        assert deps.search_config["use_vector"] is False
        assert deps.search_config["custom_param"] == "value"


class TestMemorySystemPrompt:
    """Test memory system prompt."""

    def test_add_memories_with_content(self, mock_run_context):
        """Test adding memories when memories exist."""
        mock_run_context.deps.memories = "User is a Python developer"

        result = add_memories(mock_run_context)

        assert result == "\nUser Memories:\nUser is a Python developer"

    def test_add_memories_empty(self, mock_run_context):
        """Test adding memories when no memories exist."""
        mock_run_context.deps.memories = ""

        result = add_memories(mock_run_context)

        assert result == ""

    def test_add_memories_whitespace(self, mock_run_context):
        """Test adding memories with whitespace."""
        mock_run_context.deps.memories = "   "

        result = add_memories(mock_run_context)

        # Whitespace is truthy, so it returns the formatted string
        assert result == "\nUser Memories:\n   "


@pytest.mark.asyncio
class TestSmartSearch:
    """Test smart search tool."""

    async def test_smart_search_success(self, mock_run_context):
        """Test successful smart search."""
        with patch("src.agent.unified_agent.smart_search_tool") as mock_tool:
            mock_tool.return_value = {
                "query": "test query",
                "intent": "VECTOR_HEAVY",
                "chunks": [{"content": "result"}],
                "entities": [],
                "facts": [],
            }

            result = await smart_search(mock_run_context, "test query", limit=5)

            assert result["query"] == "test query"
            assert result["intent"] == "VECTOR_HEAVY"
            assert len(result["chunks"]) == 1
            mock_tool.assert_called_once_with(user_query="test query", analyze_intent=True, limit=5)

    async def test_smart_search_default_limit(self, mock_run_context):
        """Test smart search with default limit."""
        with patch("src.agent.unified_agent.smart_search_tool") as mock_tool:
            mock_tool.return_value = {"query": "test", "chunks": []}

            await smart_search(mock_run_context, "test")

            # Should use default limit of 10
            mock_tool.assert_called_once_with(user_query="test", analyze_intent=True, limit=10)

    async def test_smart_search_error_handling(self, mock_run_context):
        """Test smart search error handling."""
        with patch("src.agent.unified_agent.smart_search_tool") as mock_tool:
            mock_tool.side_effect = Exception("API error")

            result = await smart_search(mock_run_context, "test query")

            assert result["query"] == "test query"
            assert "error" in result
            assert "API error" in result["error"]
            assert result["chunks"] == []
            assert result["entities"] == []
            assert result["facts"] == []


@pytest.mark.asyncio
class TestGraphQuery:
    """Test graph query tool."""

    async def test_query_knowledge_graph_success(self, mock_run_context):
        """Test successful graph query."""
        with patch("src.agent.unified_agent.graph_query_tool") as mock_tool:
            mock_tool.return_value = {
                "entity": "OpenAI",
                "facts": [{"description": "Founded in 2015"}],
                "relationships": [],
            }

            result = await query_knowledge_graph(
                mock_run_context, "OpenAI", query_type="entity_facts", limit=5
            )

            assert result["entity"] == "OpenAI"
            assert len(result["facts"]) == 1
            mock_tool.assert_called_once_with(
                entity_name="OpenAI", query_type="entity_facts", limit=5
            )

    async def test_query_knowledge_graph_default_params(self, mock_run_context):
        """Test graph query with default parameters."""
        with patch("src.agent.unified_agent.graph_query_tool") as mock_tool:
            mock_tool.return_value = {"entity": "TestEntity"}

            await query_knowledge_graph(mock_run_context, "TestEntity")

            mock_tool.assert_called_once_with(
                entity_name="TestEntity", query_type="entity_facts", limit=10
            )

    async def test_query_knowledge_graph_error_handling(self, mock_run_context):
        """Test graph query error handling."""
        with patch("src.agent.unified_agent.graph_query_tool") as mock_tool:
            mock_tool.side_effect = Exception("Graph database error")

            result = await query_knowledge_graph(mock_run_context, "TestEntity")

            assert result["entity"] == "TestEntity"
            assert result["query_type"] == "entity_facts"
            assert "error" in result
            assert "Graph database error" in result["error"]


@pytest.mark.asyncio
class TestRAGTools:
    """Test RAG retrieval tools."""

    async def test_retrieve_documents_success(self, mock_run_context):
        """Test successful document retrieval."""
        with patch("src.agent.unified_agent.retrieve_relevant_documents_tool") as mock_tool:
            mock_tool.return_value = "Relevant document content"

            result = await retrieve_documents(mock_run_context, "test query", limit=5)

            assert result == "Relevant document content"
            mock_tool.assert_called_once_with(
                mock_run_context.deps.supabase,
                mock_run_context.deps.embedding_client,
                "test query",
                limit=5,
            )

    async def test_retrieve_documents_error(self, mock_run_context):
        """Test document retrieval error handling."""
        with patch("src.agent.unified_agent.retrieve_relevant_documents_tool") as mock_tool:
            mock_tool.side_effect = Exception("Database error")

            result = await retrieve_documents(mock_run_context, "test query")

            assert "Error:" in result
            assert "Database error" in result

    async def test_list_all_documents(self, mock_run_context):
        """Test listing all documents."""
        with patch("src.agent.unified_agent.list_documents_tool") as mock_tool:
            mock_tool.return_value = ["doc1.pdf", "doc2.txt"]

            result = await list_all_documents(mock_run_context)

            assert result == ["doc1.pdf", "doc2.txt"]
            mock_tool.assert_called_once_with(mock_run_context.deps.supabase)

    async def test_get_full_document(self, mock_run_context):
        """Test getting full document."""
        with patch("src.agent.unified_agent.get_document_content_tool") as mock_tool:
            mock_tool.return_value = "Full document content"

            result = await get_full_document(mock_run_context, "doc-123")

            assert result == "Full document content"
            mock_tool.assert_called_once_with(mock_run_context.deps.supabase, "doc-123")


@pytest.mark.asyncio
class TestWebSearch:
    """Test web search tool."""

    async def test_search_web_success(self, mock_run_context):
        """Test successful web search."""
        with patch("src.agent.unified_agent.web_search_tool") as mock_tool:
            mock_tool.return_value = "Web search results"

            result = await search_web(mock_run_context, "test query")

            assert result == "Web search results"
            mock_tool.assert_called_once_with(
                query="test query",
                http_client=mock_run_context.deps.http_client,
                brave_api_key=mock_run_context.deps.brave_api_key,
                searxng_base_url=mock_run_context.deps.searxng_base_url,
                jina_api_key=mock_run_context.deps.jina_api_key,
                search_provider=mock_run_context.deps.web_search_provider,
            )


@pytest.mark.asyncio
class TestSQLTools:
    """Test SQL query tools."""

    async def test_execute_sql_success(self, mock_run_context):
        """Test successful SQL execution."""
        with patch("src.agent.unified_agent.execute_sql_query_tool") as mock_tool:
            mock_tool.return_value = '[{"count": 42}]'

            result = await execute_sql(mock_run_context, "SELECT COUNT(*) FROM documents")

            assert result == '[{"count": 42}]'
            mock_tool.assert_called_once_with(
                mock_run_context.deps.supabase, "SELECT COUNT(*) FROM documents"
            )

    async def test_query_tabular_data_success(self, mock_run_context):
        """Test successful tabular data query."""
        with patch("src.agent.unified_agent.execute_sql_query_tool") as mock_tool:
            mock_tool.return_value = '[{"sales": 1000}]'

            result = await query_tabular_data(
                mock_run_context,
                "SELECT SUM(row_data->>'sales') FROM document_rows WHERE dataset_id = 'test-id'",
            )

            assert result == '[{"sales": 1000}]'
            mock_tool.assert_called_once()


@pytest.mark.asyncio
class TestImageAnalysis:
    """Test image analysis tool."""

    async def test_analyze_image_success(self, mock_run_context):
        """Test successful image analysis."""
        with patch("src.agent.unified_agent.image_analysis_tool") as mock_tool:
            mock_tool.return_value = "The image contains a cat"

            result = await analyze_image(mock_run_context, "image-123", "What is in this image?")

            assert result == "The image contains a cat"
            mock_tool.assert_called_once_with(
                mock_run_context.deps.supabase, "image-123", "What is in this image?"
            )


@pytest.mark.asyncio
class TestCodeExecution:
    """Test code execution tool."""

    async def test_execute_python_code_success(self, mock_run_context):
        """Test successful code execution."""
        with patch("src.agent.unified_agent.execute_safe_code_tool") as mock_tool:
            mock_tool.return_value = "42\n"

            result = await execute_python_code(mock_run_context, "print(6 * 7)")

            assert result == "42\n"
            mock_tool.assert_called_once_with("print(6 * 7)")


@pytest.mark.asyncio
class TestAdvancedSearch:
    """Test advanced search tools."""

    async def test_comprehensive_search_vector_only(self, mock_run_context):
        """Test comprehensive search with vector only."""
        with patch("src.agent.unified_agent.retrieve_relevant_documents_tool") as mock_tool:
            mock_tool.return_value = "Vector results"

            result = await comprehensive_search(
                mock_run_context, "test query", use_vector=True, use_graph=False
            )

            assert result["query"] == "test query"
            assert result["search_config"]["use_vector"] is True
            assert result["search_config"]["use_graph"] is False
            assert result["vector_results"] == "Vector results"

    async def test_comprehensive_search_error_handling(self, mock_run_context):
        """Test comprehensive search error handling."""
        with patch("src.agent.unified_agent.retrieve_relevant_documents_tool") as mock_tool:
            mock_tool.side_effect = Exception("Search failed")

            result = await comprehensive_search(mock_run_context, "test query")

            assert result["query"] == "test query"
            assert "vector_error" in result
            assert "Search failed" in result["vector_error"]

    async def test_iterative_search(self, mock_run_context):
        """Test iterative search."""
        with patch("src.agent.unified_agent.retrieve_relevant_documents_tool") as mock_tool:
            mock_tool.return_value = "Initial results"

            result = await iterative_search(mock_run_context, "complex query")

            assert result["query"] == "complex query"
            assert len(result["iterations"]) == 1
            assert result["iterations"][0]["step"] == 1
            assert result["iterations"][0]["action"] == "initial_search"
            assert result["final_answer"] == "Initial results"


@pytest.mark.asyncio
class TestMainExecution:
    """Test main agent execution."""

    async def test_run_unified_agent_success(
        self, mock_supabase, mock_embedding_client, mock_http_client
    ):
        """Test successful agent execution."""
        with patch.object(super_agent, "run") as mock_run:
            mock_result = Mock()
            mock_result.output = "Agent response"
            mock_result.model_used = "gpt-4"
            mock_result.tools_used = ["smart_search"]
            mock_run.return_value = mock_result

            result = await run_unified_agent(
                query="test query",
                session_id="test-session",
                user_id="test-user",
                supabase_client=mock_supabase,
                embedding_client=mock_embedding_client,
                http_client=mock_http_client,
                memories="User memories",
            )

            assert result["status"] == "success"
            assert result["query"] == "test query"
            assert result["response"] == "Agent response"
            assert result["metadata"]["session_id"] == "test-session"
            assert result["metadata"]["user_id"] == "test-user"
            assert result["metadata"]["model_used"] == "gpt-4"
            assert result["metadata"]["tools_used"] == ["smart_search"]

    async def test_run_unified_agent_with_search_config(
        self, mock_supabase, mock_embedding_client, mock_http_client
    ):
        """Test agent execution with custom search config."""
        custom_config = {"use_vector": False, "use_graph": True}

        with patch.object(super_agent, "run") as mock_run:
            mock_result = Mock()
            mock_result.output = "Agent response"
            mock_run.return_value = mock_result

            result = await run_unified_agent(
                query="test query",
                supabase_client=mock_supabase,
                embedding_client=mock_embedding_client,
                http_client=mock_http_client,
                search_config=custom_config,
            )

            assert result["status"] == "success"
            # Verify search_config was passed to deps
            call_args = mock_run.call_args
            assert call_args[1]["deps"].search_config == custom_config

    async def test_run_unified_agent_minimal_params(
        self, mock_supabase, mock_embedding_client, mock_http_client
    ):
        """Test agent execution with minimal parameters."""
        with patch.object(super_agent, "run") as mock_run:
            mock_result = Mock()
            mock_result.output = "Response"
            mock_run.return_value = mock_result

            result = await run_unified_agent(
                query="test",
                supabase_client=mock_supabase,
                embedding_client=mock_embedding_client,
                http_client=mock_http_client,
            )

            assert result["status"] == "success"
            assert result["metadata"]["session_id"] == "default"
            assert result["metadata"]["user_id"] is None

    async def test_run_unified_agent_error(
        self, mock_supabase, mock_embedding_client, mock_http_client
    ):
        """Test agent execution error handling."""
        with patch.object(super_agent, "run") as mock_run:
            mock_run.side_effect = Exception("Agent execution failed")

            result = await run_unified_agent(
                query="test query",
                session_id="test-session",
                user_id="test-user",
                supabase_client=mock_supabase,
                embedding_client=mock_embedding_client,
                http_client=mock_http_client,
            )

            assert result["status"] == "error"
            assert result["query"] == "test query"
            assert "Agent execution failed" in result["error"]
            assert result["metadata"]["session_id"] == "test-session"
            assert result["metadata"]["user_id"] == "test-user"

    async def test_run_unified_agent_fallback_http_client(
        self, mock_supabase, mock_embedding_client
    ):
        """Test agent creates fallback HTTP client when none provided."""
        with patch.object(super_agent, "run") as mock_run:
            mock_result = Mock()
            mock_result.output = "Response"
            mock_run.return_value = mock_result

            # Don't provide http_client
            result = await run_unified_agent(
                query="test",
                supabase_client=mock_supabase,
                embedding_client=mock_embedding_client,
                http_client=None,
            )

            assert result["status"] == "success"
            # Should have created a fallback AsyncClient
            call_args = mock_run.call_args
            assert call_args[1]["deps"].http_client is not None


class TestAgentConfiguration:
    """Test agent configuration."""

    def test_super_agent_exists(self):
        """Test super_agent is properly initialized."""
        assert super_agent is not None
        assert super_agent.system_prompt is not None

    def test_super_agent_deps_type(self):
        """Test super_agent dependencies type."""
        assert super_agent.deps_type == UnifiedAgentDeps
