"""
Enhanced tests for unified agent system.

Target coverage: 50% → 75%+
"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from openai import AsyncOpenAI
from pydantic_ai import RunContext
from supabase.client import Client

from src.agent.unified_agent import (
    UnifiedAgentDeps,
    add_memories,
    query_knowledge_graph,
    retrieve_documents,
    smart_search,
    super_agent,
)


class TestUnifiedAgentDeps:
    """Test UnifiedAgentDeps dataclass."""

    def test_init_required_fields(self):
        """Test initialization with required fields."""
        mock_supabase = MagicMock(spec=Client)
        mock_embedding = MagicMock(spec=AsyncOpenAI)
        mock_http = MagicMock(spec=AsyncClient)

        deps = UnifiedAgentDeps(
            supabase=mock_supabase,
            embedding_client=mock_embedding,
            http_client=mock_http,
        )

        assert deps.supabase == mock_supabase
        assert deps.embedding_client == mock_embedding
        assert deps.http_client == mock_http

    def test_init_default_values(self):
        """Test default values for optional fields."""
        deps = UnifiedAgentDeps(
            supabase=MagicMock(),
            embedding_client=MagicMock(),
            http_client=MagicMock(),
        )

        assert deps.brave_api_key is None
        assert deps.searxng_base_url is None
        assert deps.jina_api_key is None
        assert deps.web_search_provider is None
        assert deps.memories == ""
        assert deps.session_id == "default"
        assert deps.user_id is None

    def test_init_custom_optional_values(self):
        """Test initialization with custom optional values."""
        deps = UnifiedAgentDeps(
            supabase=MagicMock(),
            embedding_client=MagicMock(),
            http_client=MagicMock(),
            brave_api_key="brave-key",
            searxng_base_url="http://searxng.local",
            jina_api_key="jina-key",
            web_search_provider="brave",
            memories="User likes Python",
            session_id="session-123",
            user_id="user-456",
        )

        assert deps.brave_api_key == "brave-key"
        assert deps.searxng_base_url == "http://searxng.local"
        assert deps.jina_api_key == "jina-key"
        assert deps.web_search_provider == "brave"
        assert deps.memories == "User likes Python"
        assert deps.session_id == "session-123"
        assert deps.user_id == "user-456"

    def test_search_config_default(self):
        """Test default search configuration."""
        deps = UnifiedAgentDeps(
            supabase=MagicMock(),
            embedding_client=MagicMock(),
            http_client=MagicMock(),
        )

        assert deps.search_config is not None
        assert deps.search_config["use_vector"] is True
        assert deps.search_config["use_graph"] is True
        assert deps.search_config["use_hybrid"] is True
        assert deps.search_config["confidence_threshold"] == 0.7
        assert deps.search_config["max_results"] == 20

    def test_search_config_custom(self):
        """Test custom search configuration."""
        custom_config = {
            "use_vector": False,
            "use_graph": True,
            "confidence_threshold": 0.8,
            "max_results": 50,
        }

        deps = UnifiedAgentDeps(
            supabase=MagicMock(),
            embedding_client=MagicMock(),
            http_client=MagicMock(),
            search_config=custom_config,
        )

        assert deps.search_config == custom_config


class TestAddMemories:
    """Test memory tool."""

    def test_add_memories_with_content(self):
        """Test adding memories when present."""
        deps = UnifiedAgentDeps(
            supabase=MagicMock(),
            embedding_client=MagicMock(),
            http_client=MagicMock(),
            memories="User prefers Python. Lives in SF.",
        )

        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = deps

        result = add_memories(mock_ctx)

        assert "User Memories:" in result
        assert "User prefers Python" in result
        assert "Lives in SF" in result

    def test_add_memories_without_content(self):
        """Test adding memories when empty."""
        deps = UnifiedAgentDeps(
            supabase=MagicMock(),
            embedding_client=MagicMock(),
            http_client=MagicMock(),
            memories="",
        )

        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = deps

        result = add_memories(mock_ctx)

        assert result == ""


class TestSmartSearch:
    """Test smart search tool."""

    @pytest.mark.asyncio
    async def test_smart_search_success(self):
        """Test successful smart search."""
        deps = UnifiedAgentDeps(
            supabase=MagicMock(),
            embedding_client=MagicMock(),
            http_client=MagicMock(),
        )

        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = deps

        expected_result = {
            "query": "test query",
            "intent": "VECTOR_HEAVY",
            "chunks": [{"content": "Result 1"}],
            "entities": [],
            "facts": [],
        }

        with patch("src.agent.unified_agent.smart_search_tool", return_value=expected_result):
            result = await smart_search(mock_ctx, query="test query", limit=10)

        assert result["query"] == "test query"
        assert result["intent"] == "VECTOR_HEAVY"
        assert len(result["chunks"]) == 1

    @pytest.mark.asyncio
    async def test_smart_search_custom_limit(self):
        """Test smart search with custom limit."""
        deps = UnifiedAgentDeps(
            supabase=MagicMock(),
            embedding_client=MagicMock(),
            http_client=MagicMock(),
        )

        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = deps

        expected_result = {
            "query": "test",
            "chunks": [{"content": f"Result {i}"} for i in range(20)],
        }

        with patch(
            "src.agent.unified_agent.smart_search_tool", return_value=expected_result
        ) as mock_tool:
            await smart_search(mock_ctx, query="test", limit=20)

            # Verify limit was passed
            mock_tool.assert_called_once_with(user_query="test", analyze_intent=True, limit=20)

    @pytest.mark.asyncio
    async def test_smart_search_error_handling(self):
        """Test smart search error handling."""
        deps = UnifiedAgentDeps(
            supabase=MagicMock(),
            embedding_client=MagicMock(),
            http_client=MagicMock(),
        )

        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = deps

        with patch(
            "src.agent.unified_agent.smart_search_tool", side_effect=Exception("Search failed")
        ):
            result = await smart_search(mock_ctx, query="test", limit=10)

        assert "error" in result
        assert result["error"] == "Search failed"
        assert result["chunks"] == []


class TestQueryKnowledgeGraph:
    """Test knowledge graph query tool."""

    @pytest.mark.asyncio
    async def test_query_knowledge_graph_entity_facts(self):
        """Test querying entity facts."""
        deps = UnifiedAgentDeps(
            supabase=MagicMock(),
            embedding_client=MagicMock(),
            http_client=MagicMock(),
        )

        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = deps

        expected_result = {
            "entity": "OpenAI",
            "query_type": "entity_facts",
            "facts": ["Fact 1", "Fact 2"],
        }

        with patch("src.agent.unified_agent.graph_query_tool", return_value=expected_result):
            result = await query_knowledge_graph(
                mock_ctx, entity_name="OpenAI", query_type="entity_facts"
            )

        assert result["entity"] == "OpenAI"
        assert result["query_type"] == "entity_facts"
        assert len(result["facts"]) == 2

    @pytest.mark.asyncio
    async def test_query_knowledge_graph_relationships(self):
        """Test querying entity relationships."""
        deps = UnifiedAgentDeps(
            supabase=MagicMock(),
            embedding_client=MagicMock(),
            http_client=MagicMock(),
        )

        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = deps

        expected_result = {
            "entity": "Tesla",
            "query_type": "entity_relationships",
            "relationships": [{"type": "WORKS_WITH", "target": "SpaceX"}],
        }

        with patch("src.agent.unified_agent.graph_query_tool", return_value=expected_result):
            result = await query_knowledge_graph(
                mock_ctx, entity_name="Tesla", query_type="entity_relationships", limit=10
            )

        assert result["query_type"] == "entity_relationships"
        assert len(result["relationships"]) == 1

    @pytest.mark.asyncio
    async def test_query_knowledge_graph_error(self):
        """Test knowledge graph query error handling."""
        deps = UnifiedAgentDeps(
            supabase=MagicMock(),
            embedding_client=MagicMock(),
            http_client=MagicMock(),
        )

        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = deps

        with patch(
            "src.agent.unified_agent.graph_query_tool", side_effect=Exception("Graph error")
        ):
            result = await query_knowledge_graph(mock_ctx, entity_name="Test")

        assert "error" in result
        assert result["error"] == "Graph error"


class TestRetrieveDocuments:
    """Test retrieve documents tool."""

    @pytest.mark.asyncio
    async def test_retrieve_documents_success(self):
        """Test successful document retrieval."""
        deps = UnifiedAgentDeps(
            supabase=MagicMock(),
            embedding_client=MagicMock(),
            http_client=MagicMock(),
        )

        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = deps

        expected_result = """Found 3 relevant documents:

Document 1: Content here
Document 2: More content
Document 3: Final content"""

        with patch(
            "src.agent.unified_agent.retrieve_relevant_documents_tool", return_value=expected_result
        ):
            result = await retrieve_documents(mock_ctx, query="test query", limit=10)

        assert "Found 3 relevant documents" in result
        assert "Document 1" in result

    @pytest.mark.asyncio
    async def test_retrieve_documents_custom_limit(self):
        """Test document retrieval with custom limit."""
        deps = UnifiedAgentDeps(
            supabase=MagicMock(),
            embedding_client=MagicMock(),
            http_client=MagicMock(),
        )

        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = deps

        with patch("src.agent.unified_agent.retrieve_relevant_documents_tool") as mock_tool:
            await retrieve_documents(mock_ctx, query="test", limit=20)

            # Verify limit was passed
            call_args = mock_tool.call_args
            assert "limit" in call_args[1]
            assert call_args[1]["limit"] == 20

    @pytest.mark.asyncio
    async def test_retrieve_documents_error(self):
        """Test document retrieval error handling."""
        deps = UnifiedAgentDeps(
            supabase=MagicMock(),
            embedding_client=MagicMock(),
            http_client=MagicMock(),
        )

        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = deps

        with patch(
            "src.agent.unified_agent.retrieve_relevant_documents_tool",
            side_effect=Exception("Retrieval failed"),
        ):
            result = await retrieve_documents(mock_ctx, query="test")

        assert "error" in result.lower() or "failed" in result.lower()


class TestSuperAgent:
    """Test super agent configuration."""

    def test_super_agent_exists(self):
        """Test that super agent is initialized."""
        assert super_agent is not None

    def test_super_agent_has_system_prompt(self):
        """Test that super agent has system prompt."""
        # Agent should have been initialized with system prompt
        assert hasattr(super_agent, "_system_prompts")

    def test_super_agent_deps_type(self):
        """Test that super agent uses correct deps type."""
        # Verify deps_type is set correctly
        assert super_agent._deps_type == UnifiedAgentDeps

    def test_super_agent_retries(self):
        """Test that super agent has retry configuration."""
        # Agent should have retries configured
        assert hasattr(super_agent, "_max_result_retries")


class TestToolRegistration:
    """Test tool registration on super agent."""

    def test_smart_search_registered(self):
        """Test that smart_search tool is registered."""
        # Get registered tools
        tools = super_agent._function_toolset.tools

        # Check if smart_search is in tools
        tool_names = [tool.name for tool in tools.values()]
        assert "smart_search" in tool_names

    def test_query_knowledge_graph_registered(self):
        """Test that query_knowledge_graph tool is registered."""
        tools = super_agent._function_toolset.tools
        tool_names = [tool.name for tool in tools.values()]
        assert "query_knowledge_graph" in tool_names

    def test_retrieve_documents_registered(self):
        """Test that retrieve_documents tool is registered."""
        tools = super_agent._function_toolset.tools
        tool_names = [tool.name for tool in tools.values()]
        assert "retrieve_documents" in tool_names


class TestIntegration:
    """Integration tests for unified agent."""

    @pytest.mark.asyncio
    async def test_full_deps_initialization(self):
        """Test full deps initialization with all fields."""
        mock_supabase = MagicMock(spec=Client)
        mock_embedding = MagicMock(spec=AsyncOpenAI)
        mock_http = MagicMock(spec=AsyncClient)

        deps = UnifiedAgentDeps(
            supabase=mock_supabase,
            embedding_client=mock_embedding,
            http_client=mock_http,
            brave_api_key="test-key",
            memories="Test memories",
            session_id="test-session",
            user_id="test-user",
            web_search_provider="brave",
        )

        # Verify all fields are properly set
        assert deps.supabase == mock_supabase
        assert deps.brave_api_key == "test-key"
        assert deps.memories == "Test memories"
        assert deps.search_config["use_vector"] is True

    @pytest.mark.asyncio
    async def test_smart_search_with_real_deps(self):
        """Test smart search with realistic dependencies."""
        deps = UnifiedAgentDeps(
            supabase=MagicMock(),
            embedding_client=MagicMock(),
            http_client=MagicMock(),
            search_config={
                "use_vector": True,
                "use_graph": True,
                "confidence_threshold": 0.8,
                "max_results": 15,
            },
        )

        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = deps

        expected = {
            "query": "test",
            "intent": "HYBRID",
            "chunks": [],
            "entities": [],
        }

        with patch("src.agent.unified_agent.smart_search_tool", return_value=expected):
            result = await smart_search(mock_ctx, "test", limit=15)

        assert result["intent"] == "HYBRID"

    @pytest.mark.asyncio
    async def test_memory_context_preserved(self):
        """Test that memory context is preserved through tool calls."""
        deps = UnifiedAgentDeps(
            supabase=MagicMock(),
            embedding_client=MagicMock(),
            http_client=MagicMock(),
            memories="User loves AI research",
            user_id="user-123",
        )

        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.deps = deps

        # Test that memories can be accessed
        memory_prompt = add_memories(mock_ctx)
        assert "User loves AI research" in memory_prompt

        # Simulate a search with memory context
        with patch("src.agent.unified_agent.smart_search_tool", return_value={"query": "AI"}):
            await smart_search(mock_ctx, "AI research papers")

        # Verify deps still has memories
        assert mock_ctx.deps.memories == "User loves AI research"
