"""
Tests for the Unified Super-Agent
==================================

Comprehensive test suite for our new unified agent that combines all capabilities.
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock imports to avoid missing dependencies
with patch.dict(
    "sys.modules",
    {
        "httpx": MagicMock(),
        "openai": MagicMock(),
        "supabase": MagicMock(),
        "supabase.client": MagicMock(),
    },
):
    from httpx import AsyncClient
    from openai import AsyncOpenAI

    # Import the unified agent
    from src.agent import UnifiedAgentDeps, run_unified_agent, super_agent
    from supabase.client import Client


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    client = MagicMock()
    # Mock RPC calls
    client.rpc = MagicMock()
    client.rpc.return_value.execute = MagicMock(
        return_value=MagicMock(data=[{"content": "test content", "similarity": 0.9}])
    )
    # Mock table operations
    client.table = MagicMock()
    client.table.return_value.select = MagicMock()
    client.table.return_value.select.return_value.execute = MagicMock(
        return_value=MagicMock(data=[{"id": "doc1", "file_path": "test.txt"}])
    )
    return client


@pytest.fixture
def mock_embedding_client():
    """Mock OpenAI embedding client."""
    client = MagicMock()
    client.embeddings = MagicMock()
    client.embeddings.create = AsyncMock(
        return_value=MagicMock(data=[MagicMock(embedding=[0.1] * 1536)])
    )
    return client


@pytest.fixture
def mock_http_client():
    """Mock HTTP client."""
    return MagicMock()


@pytest.fixture
def unified_deps(mock_supabase, mock_embedding_client, mock_http_client):
    """Create UnifiedAgentDeps with mocked clients."""
    return UnifiedAgentDeps(
        supabase=mock_supabase,
        embedding_client=mock_embedding_client,
        http_client=mock_http_client,
        brave_api_key="test_brave_key",
        jina_api_key="test_jina_key",
        memories="Test user context",
        session_id="test_session",
        user_id="test_user",
    )


class TestUnifiedAgent:
    """Test suite for the unified super-agent."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self, unified_deps):
        """Test that the agent initializes correctly."""
        assert super_agent is not None
        assert super_agent.model is not None
        assert unified_deps.supabase is not None
        assert unified_deps.embedding_client is not None

    @pytest.mark.asyncio
    async def test_smart_search_tool(self, unified_deps):
        """Test the smart search tool with intent routing."""
        # Mock the tool function
        with patch("src.agent.unified_agent.retrieve_relevant_documents_tool") as mock_retrieve:
            mock_retrieve.return_value = "Found 3 relevant documents about AI"

            # Create a mock context
            ctx = MagicMock()
            ctx.deps = unified_deps

            # Test vector-focused query
            result = await smart_search(ctx, "Find similar documents about machine learning")
            assert "results" in result
            assert result["strategy"] in ["vector_first", "hybrid"]

    @pytest.mark.asyncio
    async def test_retrieve_documents_tool(self, unified_deps):
        """Test the RAG document retrieval tool."""
        with patch("src.agent.unified_agent.retrieve_relevant_documents_tool") as mock_retrieve:
            mock_retrieve.return_value = "Document 1: Machine learning basics..."

            ctx = MagicMock()
            ctx.deps = unified_deps

            result = await retrieve_documents(ctx, "machine learning", limit=5)
            assert result is not None
            mock_retrieve.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_documents_tool(self, unified_deps):
        """Test listing all documents."""
        with patch("src.agent.unified_agent.list_documents_tool") as mock_list:
            mock_list.return_value = ["doc1.txt", "doc2.pdf", "image1.png"]

            ctx = MagicMock()
            ctx.deps = unified_deps

            result = await list_all_documents(ctx)
            assert isinstance(result, list)
            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_web_search_tool(self, unified_deps):
        """Test web search functionality."""
        with patch("src.agent.unified_agent.web_search_tool") as mock_search:
            mock_search.return_value = "Latest AI news: GPT-5 announced..."

            ctx = MagicMock()
            ctx.deps = unified_deps

            result = await search_web(ctx, "latest AI news")
            assert result is not None
            mock_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_sql_query_tool(self, unified_deps):
        """Test SQL query execution."""
        with patch("src.agent.unified_agent.execute_sql_query_tool") as mock_sql:
            mock_sql.return_value = '[{"count": 42}]'

            ctx = MagicMock()
            ctx.deps = unified_deps

            result = await execute_sql(ctx, "SELECT COUNT(*) FROM documents")
            assert "42" in result

    @pytest.mark.asyncio
    async def test_code_execution_tool(self, unified_deps):
        """Test Python code execution."""
        with patch("src.agent.unified_agent.execute_safe_code_tool") as mock_exec:
            mock_exec.return_value = "Result: 120"

            ctx = MagicMock()
            ctx.deps = unified_deps

            code = "import math\nprint(f'Result: {math.factorial(5)}')"
            result = await execute_python_code(ctx, code)
            assert "120" in result

    @pytest.mark.asyncio
    async def test_image_analysis_tool(self, unified_deps):
        """Test image analysis functionality."""
        with patch("src.agent.unified_agent.image_analysis_tool") as mock_analyze:
            mock_analyze.return_value = "The image shows a diagram of neural network architecture"

            ctx = MagicMock()
            ctx.deps = unified_deps

            result = await analyze_image(ctx, "diagram.png", "What does this image show?")
            assert "neural network" in result.lower()

    @pytest.mark.asyncio
    async def test_comprehensive_search(self, unified_deps):
        """Test comprehensive search with multiple strategies."""
        with patch("src.agent.unified_agent.retrieve_relevant_documents_tool") as mock_retrieve:
            mock_retrieve.return_value = "Vector search results..."

            ctx = MagicMock()
            ctx.deps = unified_deps

            result = await comprehensive_search(
                ctx, "artificial intelligence", use_vector=True, use_graph=False, max_results=10
            )

            assert result["query"] == "artificial intelligence"
            assert "search_config" in result
            assert result["search_config"]["max_results"] == 10

    @pytest.mark.asyncio
    async def test_run_unified_agent(self, mock_supabase, mock_embedding_client, mock_http_client):
        """Test the main run function."""
        with patch("src.agent.unified_agent.super_agent.run") as mock_run:
            mock_run.return_value = MagicMock(
                data="The answer is 42",
                model_used="gpt-4",
                tools_used=["smart_search", "retrieve_documents"],
            )

            result = await run_unified_agent(
                query="What is the meaning of life?",
                session_id="test",
                supabase_client=mock_supabase,
                embedding_client=mock_embedding_client,
                http_client=mock_http_client,
            )

            assert result["status"] == "success"
            assert result["response"] == "The answer is 42"
            assert result["metadata"]["session_id"] == "test"

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_supabase, mock_embedding_client, mock_http_client):
        """Test error handling in the agent."""
        with patch("src.agent.unified_agent.super_agent.run") as mock_run:
            mock_run.side_effect = Exception("Test error")

            result = await run_unified_agent(
                query="This will fail",
                session_id="test",
                supabase_client=mock_supabase,
                embedding_client=mock_embedding_client,
                http_client=mock_http_client,
            )

            assert result["status"] == "error"
            assert "Test error" in result["error"]

    @pytest.mark.asyncio
    async def test_memory_integration(self, unified_deps):
        """Test that memories are properly integrated."""
        # The add_memories system prompt should include user context
        ctx = MagicMock()
        ctx.deps = unified_deps
        ctx.deps.memories = "User loves Python programming"

        memory_prompt = add_memories(ctx)
        assert "User loves Python" in memory_prompt

    @pytest.mark.asyncio
    async def test_iterative_search(self, unified_deps):
        """Test iterative search for complex queries."""
        with patch("src.agent.unified_agent.retrieve_relevant_documents_tool") as mock_retrieve:
            mock_retrieve.return_value = "Initial search results..."

            ctx = MagicMock()
            ctx.deps = unified_deps

            result = await iterative_search(ctx, "complex query about AI ethics", max_iterations=2)

            assert result["query"] == "complex query about AI ethics"
            assert "iterations" in result
            assert len(result["iterations"]) >= 1


class TestUnifiedAgentIntegration:
    """Integration tests for the unified agent."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_agent_flow(self, mock_supabase, mock_embedding_client):
        """Test complete agent flow with multiple tools."""
        # This would be a more comprehensive integration test
        # that tests the agent with real tool interactions
        pass

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_agent_with_real_llm(self):
        """Test agent with actual LLM (requires API keys)."""
        # Skip if no API keys available
        if not os.getenv("LLM_API_KEY"):
            pytest.skip("No LLM API key available")

        # This would test with real LLM calls
        pass


# Import tool functions for testing
from src.agent.unified_agent import (
    add_memories,
    analyze_image,
    comprehensive_search,
    execute_python_code,
    execute_sql,
    iterative_search,
    list_all_documents,
    retrieve_documents,
    search_web,
    smart_search,
)

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
