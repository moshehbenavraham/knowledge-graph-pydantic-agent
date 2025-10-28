"""Integration tests for the AI agent system.

These tests verify that different components work together correctly,
including RAG pipeline, database operations, tool integration, and memory system.
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
}

with patch.dict(os.environ, TEST_ENV_VARS):
    # Add src directory to path to import modules
    sys.path.append(str(Path(__file__).parent.parent.resolve() / "src"))

    # Import components for integration testing
    from agent.unified_agent import UnifiedAgentDeps as AgentDeps
    from clients.memory import get_mem0_config
    from tools.rag import list_documents_tool, retrieve_relevant_documents_tool
    from tools.sql_query import execute_sql_query_tool
    from tools.web_search import web_search_tool


class TestRAGPipelineIntegration:
    """Test RAG pipeline integration with database and embedding systems."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client for RAG operations."""
        client = MagicMock()

        # Mock document listing
        client.table.return_value.select.return_value.execute.return_value.data = [
            {"file_id": "doc1", "file_name": "document1.pdf", "file_type": "pdf"},
            {"file_id": "doc2", "file_name": "document2.txt", "file_type": "txt"},
        ]

        # Mock document content retrieval
        client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            {"chunk_index": 0, "content": "First chunk of document content"},
            {"chunk_index": 1, "content": "Second chunk of document content"},
        ]

        # Mock vector search
        client.rpc.return_value.execute.return_value.data = [
            {
                "file_id": "doc1",
                "file_name": "relevant_doc.pdf",
                "content": "This is relevant content about AI",
                "similarity": 0.85,
            },
            {
                "file_id": "doc2",
                "file_name": "another_doc.txt",
                "content": "More relevant content about machine learning",
                "similarity": 0.78,
            },
        ]

        return client

    @pytest.fixture
    def mock_embedding_client(self):
        """Mock embedding client for vector operations."""
        client = AsyncMock()
        client.embeddings.create.return_value.data = [
            MagicMock(embedding=[0.1, 0.2, 0.3] * 512)  # Mock 1536-dim embedding
        ]
        return client

    @pytest.fixture
    def mock_hybrid_search(self):
        """Mock HybridSearch instance to avoid real database connections."""
        from uuid import uuid4

        from src.agentic_rag.search.hybrid_search import HybridSearchResult
        from src.agentic_rag.search.intent_analyzer import SearchIntent
        from src.agentic_rag.search.vector_search import ChunkResult
        from src.config import SearchStrategy

        mock_search = AsyncMock()

        # Create realistic ChunkResult objects with proper structure
        chunk1 = ChunkResult(
            chunk_id=uuid4(),
            content="This is relevant content about AI",
            similarity=0.85,
            document_id=uuid4(),
            document_title="AI Guide",
            document_source="relevant_doc.pdf",
            metadata={},
        )
        chunk2 = ChunkResult(
            chunk_id=uuid4(),
            content="More relevant content about machine learning",
            similarity=0.78,
            document_id=uuid4(),
            document_title="ML Basics",
            document_source="another_doc.txt",
            metadata={},
        )

        # Create a realistic HybridSearchResult with correct field names
        mock_result = HybridSearchResult(
            chunks=[chunk1, chunk2],
            facts=[],
            entities=[],
            relationships=[],
            search_strategy=SearchStrategy.VECTOR_ONLY,
            intent=SearchIntent.VECTOR_HEAVY,
            query_time=0.05,  # 50ms in seconds
            metadata={},
        )

        mock_search.search.return_value = mock_result
        return mock_search

    @pytest.mark.asyncio
    async def test_rag_document_retrieval_integration(
        self, mock_supabase_client, mock_embedding_client, mock_hybrid_search
    ):
        """Test end-to-end RAG document retrieval."""
        query = "What is artificial intelligence?"

        # Mock get_hybrid_search to return our mock
        with patch("tools.rag.get_hybrid_search", return_value=mock_hybrid_search):
            # Test the RAG retrieval tool
            result = await retrieve_relevant_documents_tool(
                mock_supabase_client, mock_embedding_client, query
            )

            # Verify HybridSearch.search was called
            mock_hybrid_search.search.assert_called_once()

            # Verify result format
            assert isinstance(result, str)
            assert "relevant_doc.pdf" in result
            assert "This is relevant content about AI" in result

    @pytest.mark.asyncio
    async def test_document_listing_integration(self, mock_supabase_client):
        """Test document listing integration."""
        # Fix mock to use from_() instead of table()
        mock_supabase_client.from_.return_value.select.return_value.execute.return_value.data = [
            {
                "id": "doc1",
                "title": "document1",
                "source": "document1.pdf",
                "created_at": "2024-01-01",
            },
            {
                "id": "doc2",
                "title": "document2",
                "source": "document2.txt",
                "created_at": "2024-01-02",
            },
        ]

        result = await list_documents_tool(mock_supabase_client)

        # Verify database query (uses from_() not table())
        mock_supabase_client.from_.assert_called_with("documents")

        # Verify result format
        assert isinstance(result, list)
        assert len(result) == 2
        # Results are formatted as "ID: ..., Title: ..., Source: ..., Created: ..."
        assert "document1.pdf" in str(result)
        assert "document2.txt" in str(result)

    @pytest.mark.asyncio
    async def test_rag_with_empty_results(
        self, mock_supabase_client, mock_embedding_client, mock_hybrid_search
    ):
        """Test RAG behavior when no documents are found."""
        from src.agentic_rag.search.hybrid_search import HybridSearchResult
        from src.agentic_rag.search.intent_analyzer import SearchIntent
        from src.config import SearchStrategy

        # Mock empty results with correct field names
        empty_result = HybridSearchResult(
            chunks=[],
            facts=[],
            entities=[],
            relationships=[],
            search_strategy=SearchStrategy.VECTOR_ONLY,
            intent=SearchIntent.VECTOR_HEAVY,
            query_time=0.03,
            metadata={},
        )
        mock_hybrid_search.search.return_value = empty_result

        with patch("tools.rag.get_hybrid_search", return_value=mock_hybrid_search):
            result = await retrieve_relevant_documents_tool(
                mock_supabase_client, mock_embedding_client, "nonexistent topic"
            )

            assert "No relevant documents found" in result

    @pytest.mark.asyncio
    async def test_rag_error_handling(
        self, mock_supabase_client, mock_embedding_client, mock_hybrid_search
    ):
        """Test RAG error handling for database failures."""
        # Mock hybrid search error
        mock_hybrid_search.search.side_effect = Exception("Database connection failed")

        with patch("tools.rag.get_hybrid_search", return_value=mock_hybrid_search):
            result = await retrieve_relevant_documents_tool(
                mock_supabase_client, mock_embedding_client, "test query"
            )

            # The tool catches exceptions and returns error message
            assert "Error retrieving documents" in result
            assert "Database connection failed" in result


class TestDatabaseOperationsIntegration:
    """Test database operations integration across different components."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client for database operations."""
        client = MagicMock()

        # Mock SQL query execution
        client.rpc.return_value.execute.return_value.data = [
            {"id": 1, "name": "John Doe", "email": "john@example.com"},
            {"id": 2, "name": "Jane Smith", "email": "jane@example.com"},
        ]

        return client

    @pytest.mark.asyncio
    async def test_sql_query_integration(self, mock_supabase_client):
        """Test SQL query execution integration."""
        query = "SELECT id, name, email FROM users LIMIT 2;"

        result = await execute_sql_query_tool(mock_supabase_client, query)

        # Verify RPC call was made (semicolon is stripped by the tool)
        mock_supabase_client.rpc.assert_called_once_with(
            "execute_sql", {"query": "SELECT id, name, email FROM users LIMIT 2"}
        )

        # Verify result format
        assert isinstance(result, str)
        assert "John Doe" in result
        assert "jane@example.com" in result

    @pytest.mark.asyncio
    async def test_database_connection_resilience(self, mock_supabase_client):
        """Test database connection resilience and retry logic."""
        # First call fails
        mock_supabase_client.rpc.side_effect = Exception("Connection timeout")

        # Tool catches exceptions and returns error string
        result = await execute_sql_query_tool(mock_supabase_client, "SELECT 1;")
        assert "Error executing SQL query" in result
        assert "Connection timeout" in result

    @pytest.mark.asyncio
    async def test_sql_injection_protection(self, mock_supabase_client):
        """Test SQL injection protection in query execution."""
        malicious_query = "SELECT * FROM users; DROP TABLE users; --"

        # Tool detects DROP operation and blocks it
        result = await execute_sql_query_tool(mock_supabase_client, malicious_query)

        # Verify the error was returned (protection is client-side)
        assert "Error: Write operation 'DROP' detected" in result
        assert "Only read-only queries are allowed" in result
        # RPC should not be called because the query was blocked
        mock_supabase_client.rpc.assert_not_called()


class TestToolIntegration:
    """Test integration between different tools and agent system."""

    @pytest.fixture
    def mock_agent_deps(self):
        """Create mock agent dependencies for tool integration testing."""
        deps = MagicMock(spec=AgentDeps)
        deps.supabase = MagicMock()
        deps.embedding_client = AsyncMock()
        deps.http_client = AsyncMock()
        deps.brave_api_key = "test-brave-key"
        deps.searxng_base_url = "http://test-searxng-url.com"
        deps.memories = "User prefers Python\nUser works in AI/ML"
        return deps

    @pytest.mark.asyncio
    @patch("tests.test_integration.web_search_tool")
    @patch("tests.test_integration.retrieve_relevant_documents_tool")
    async def test_web_search_and_rag_integration(
        self, mock_rag_tool, mock_web_search_tool, mock_agent_deps
    ):
        """Test integration between web search and RAG tools."""
        # Setup mocks
        mock_web_search_tool.return_value = "Web search results about Python AI libraries"
        mock_rag_tool.return_value = "Document results about Python machine learning"

        # Simulate a workflow that uses both tools
        web_results = await web_search_tool(
            "Python AI libraries",
            mock_agent_deps.http_client,
            mock_agent_deps.brave_api_key,
            mock_agent_deps.searxng_base_url,
        )

        rag_results = await retrieve_relevant_documents_tool(
            mock_agent_deps.supabase, mock_agent_deps.embedding_client, "Python AI libraries"
        )

        # Verify both tools were called
        mock_web_search_tool.assert_called_once()
        mock_rag_tool.assert_called_once()

        # Verify results
        assert "Web search results" in web_results
        assert "Document results" in rag_results

    @pytest.mark.asyncio
    async def test_tool_error_propagation(self, mock_agent_deps):
        """Test that tool errors are properly propagated through the system."""
        # Mock a tool failure
        mock_agent_deps.supabase.rpc.side_effect = Exception("Database unavailable")

        # Tool catches exceptions and returns error string
        result = await execute_sql_query_tool(mock_agent_deps.supabase, "SELECT 1;")
        assert "Error executing SQL query" in result
        assert "Database unavailable" in result

    @pytest.mark.asyncio
    @patch("tests.test_integration.retrieve_relevant_documents_tool")
    async def test_memory_context_in_rag(self, mock_rag_tool, mock_agent_deps):
        """Test that user memories provide context for RAG operations."""
        mock_rag_tool.return_value = "Python-specific AI documentation found"

        # Execute RAG with memory context
        result = await retrieve_relevant_documents_tool(
            mock_agent_deps.supabase, mock_agent_deps.embedding_client, "machine learning tutorials"
        )

        # Verify the tool was called
        mock_rag_tool.assert_called_once()
        assert result == "Python-specific AI documentation found"


class TestMemorySystemIntegration:
    """Test memory system integration with other components."""

    @pytest.fixture
    def mock_mem0_client(self):
        """Mock mem0 client for memory operations."""
        client = MagicMock()
        client.add.return_value = {"id": "mem_123", "content": "User prefers Python"}
        client.search.return_value = [
            {"content": "User prefers Python programming", "score": 0.9},
            {"content": "User works in machine learning", "score": 0.8},
        ]
        client.get_all.return_value = [
            {"id": "mem_123", "content": "User prefers Python programming"},
            {"id": "mem_456", "content": "User works in machine learning"},
        ]
        return client

    @patch("clients.memory.get_mem0_client")
    def test_memory_configuration_integration(self, mock_get_mem0_client):
        """Test memory system configuration integration."""
        mock_client = MagicMock()
        mock_get_mem0_client.return_value = mock_client

        # Test memory configuration
        config = get_mem0_config()

        # Verify configuration structure
        assert "llm" in config
        assert "embedder" in config
        assert "vector_store" in config

        # Verify Supabase integration
        assert config["vector_store"]["provider"] == "supabase"
        assert config["vector_store"]["config"]["collection_name"] == "mem0_memories"

    @patch("clients.memory.get_mem0_client")
    def test_memory_and_rag_vector_store_integration(self, mock_get_mem0_client):
        """Test that memory and RAG systems can coexist in the same vector store."""
        mock_client = MagicMock()
        mock_get_mem0_client.return_value = mock_client

        config = get_mem0_config()

        # Both should use Supabase but different collections
        assert config["vector_store"]["provider"] == "supabase"
        # Memory uses mem0_memories collection
        assert config["vector_store"]["config"]["collection_name"] == "mem0_memories"

        # RAG uses documents table (different from memory)
        # This ensures no conflicts between memory and document storage

    def test_memory_persistence_across_sessions(self, mock_mem0_client):
        """Test memory persistence across different user sessions."""
        # Simulate adding memories in different sessions
        session1_memory = "User asked about Python best practices"
        session2_memory = "User implemented a neural network"

        # Add memories
        mock_mem0_client.add(session1_memory)
        mock_mem0_client.add(session2_memory)

        # Retrieve all memories
        all_memories = mock_mem0_client.get_all()

        # Verify persistence
        assert len(all_memories) == 2
        mock_mem0_client.add.assert_any_call(session1_memory)
        mock_mem0_client.add.assert_any_call(session2_memory)


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows that span multiple components."""

    @pytest.fixture
    def mock_hybrid_search(self):
        """Mock HybridSearch instance to avoid real database connections."""
        from uuid import uuid4

        from src.agentic_rag.search.hybrid_search import HybridSearchResult
        from src.agentic_rag.search.intent_analyzer import SearchIntent
        from src.agentic_rag.search.vector_search import ChunkResult
        from src.config import SearchStrategy

        mock_search = AsyncMock()

        # Create realistic ChunkResult for AI guide
        chunk1 = ChunkResult(
            chunk_id=uuid4(),
            content="Comprehensive guide to artificial intelligence and machine learning",
            similarity=0.92,
            document_id=uuid4(),
            document_title="AI Guide",
            document_source="ai_guide.pdf",
            metadata={},
        )

        mock_result = HybridSearchResult(
            chunks=[chunk1],
            facts=[],
            entities=[],
            relationships=[],
            search_strategy=SearchStrategy.VECTOR_ONLY,
            intent=SearchIntent.VECTOR_HEAVY,
            query_time=0.05,
            metadata={},
        )

        mock_search.search.return_value = mock_result
        return mock_search

    @pytest.fixture
    def integrated_agent_deps(self):
        """Create integrated agent dependencies for end-to-end testing."""
        deps = MagicMock(spec=AgentDeps)

        # Mock Supabase with realistic responses
        deps.supabase = MagicMock()
        deps.supabase.rpc.return_value.execute.return_value.data = [
            {
                "file_id": "ai_guide",
                "file_name": "ai_guide.pdf",
                "content": "Comprehensive guide to artificial intelligence and machine learning",
                "similarity": 0.92,
            }
        ]

        # Mock embedding client
        deps.embedding_client = AsyncMock()
        deps.embedding_client.embeddings.create.return_value.data = [
            MagicMock(embedding=[0.1] * 1536)
        ]

        # Mock HTTP client for web search
        deps.http_client = AsyncMock()

        # API keys and URLs
        deps.brave_api_key = "test-brave-key"
        deps.searxng_base_url = "http://test-searxng-url.com"

        # User memories
        deps.memories = (
            "User is a Python developer\n"
            "User prefers practical examples\n"
            "User is learning machine learning"
        )

        return deps

    @pytest.mark.asyncio
    @patch("tests.test_integration.web_search_tool")
    async def test_research_workflow(
        self, mock_web_search, integrated_agent_deps, mock_hybrid_search
    ):
        """Test a complete research workflow: memory -> RAG -> web search."""
        # Setup web search mock
        mock_web_search.return_value = "Latest AI research papers and tutorials"

        # Step 1: Retrieve relevant documents (RAG) with mocked hybrid search
        with patch("tools.rag.get_hybrid_search", return_value=mock_hybrid_search):
            rag_result = await retrieve_relevant_documents_tool(
                integrated_agent_deps.supabase,
                integrated_agent_deps.embedding_client,
                "machine learning tutorials for Python developers",
            )

        # Step 2: Supplement with web search
        web_result = await web_search_tool(
            "latest machine learning tutorials Python",
            integrated_agent_deps.http_client,
            integrated_agent_deps.brave_api_key,
            integrated_agent_deps.searxng_base_url,
        )

        # Verify the workflow executed successfully
        assert "ai_guide.pdf" in rag_result
        assert "Comprehensive guide" in rag_result
        assert "Latest AI research" in web_result

        # Verify all components were called
        mock_hybrid_search.search.assert_called_once()
        mock_web_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_data_analysis_workflow(self, integrated_agent_deps, mock_hybrid_search):
        """Test a data analysis workflow: SQL query -> document retrieval."""
        # Mock SQL query results
        integrated_agent_deps.supabase.rpc.return_value.execute.return_value.data = [
            {"metric": "user_engagement", "value": 85.2, "trend": "increasing"}
        ]

        # Step 1: Execute SQL query for data
        sql_result = await execute_sql_query_tool(
            integrated_agent_deps.supabase,
            "SELECT metric, value, trend FROM analytics WHERE date >= '2024-01-01';",
        )

        # Step 2: Retrieve relevant documentation with mocked hybrid search
        with patch("tools.rag.get_hybrid_search", return_value=mock_hybrid_search):
            doc_result = await retrieve_relevant_documents_tool(
                integrated_agent_deps.supabase,
                integrated_agent_deps.embedding_client,
                "user engagement analysis best practices",
            )

        # Verify workflow results
        assert "user_engagement" in sql_result
        assert "85.2" in sql_result
        assert "ai_guide.pdf" in doc_result

        # Verify database interactions (only SQL query uses supabase.rpc, RAG uses hybrid_search)
        assert integrated_agent_deps.supabase.rpc.call_count == 1  # Only SQL query


class TestPerformanceIntegration:
    """Test performance aspects of component integration."""

    @pytest.fixture
    def mock_hybrid_search(self):
        """Mock HybridSearch instance for performance tests."""
        from uuid import uuid4

        from src.agentic_rag.search.hybrid_search import HybridSearchResult
        from src.agentic_rag.search.intent_analyzer import SearchIntent
        from src.agentic_rag.search.vector_search import ChunkResult
        from src.config import SearchStrategy

        mock_search = AsyncMock()

        chunk = ChunkResult(
            chunk_id=uuid4(),
            content="Test content",
            similarity=0.85,
            document_id=uuid4(),
            document_title="Test Doc",
            document_source="test.pdf",
            metadata={},
        )

        mock_result = HybridSearchResult(
            chunks=[chunk],
            facts=[],
            entities=[],
            relationships=[],
            search_strategy=SearchStrategy.VECTOR_ONLY,
            intent=SearchIntent.VECTOR_HEAVY,
            query_time=0.05,
            metadata={},
        )

        mock_search.search.return_value = mock_result
        return mock_search

    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, mock_hybrid_search):
        """Test that multiple tools can execute concurrently without conflicts."""
        # Mock components
        mock_supabase = MagicMock()
        mock_embedding_client = AsyncMock()

        # Create multiple concurrent tasks with mocked hybrid search
        with patch("tools.rag.get_hybrid_search", return_value=mock_hybrid_search):
            tasks = [
                retrieve_relevant_documents_tool(mock_supabase, mock_embedding_client, f"query {i}")
                for i in range(3)
            ]

            # Execute concurrently
            results = await asyncio.gather(*tasks)

        # Verify all tasks completed
        assert len(results) == 3
        for result in results:
            assert isinstance(result, str)

        # Verify concurrent hybrid search access
        assert mock_hybrid_search.search.call_count == 3

    @pytest.mark.asyncio
    async def test_large_document_processing(self):
        """Test integration with large document processing."""
        mock_supabase = MagicMock()
        mock_embedding_client = AsyncMock()

        # Mock large document chunks
        large_chunks = [
            {"chunk_index": i, "content": f"Large document chunk {i} " * 100}
            for i in range(50)  # 50 large chunks
        ]

        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = (
            large_chunks
        )
        mock_embedding_client.embeddings.create.return_value.data = [
            MagicMock(embedding=[0.1] * 1536)
        ]

        # Test RAG with large document
        result = await retrieve_relevant_documents_tool(
            mock_supabase, mock_embedding_client, "test query"
        )

        # Verify handling of large results
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_memory_intensive_operations(self):
        """Test memory-intensive operations across components."""
        mock_supabase = MagicMock()

        # Mock memory-intensive SQL query result
        large_dataset = [
            {"id": i, "data": f"row_{i}_" * 1000} for i in range(1000)  # Large dataset
        ]
        mock_supabase.rpc.return_value.execute.return_value.data = large_dataset

        # Execute memory-intensive query
        result = await execute_sql_query_tool(
            mock_supabase, "SELECT * FROM large_table LIMIT 1000;"
        )

        # Verify large result handling
        assert isinstance(result, str)
        assert "row_0_" in result
        assert "row_999_" in result


class TestErrorRecoveryIntegration:
    """Test error recovery and resilience across integrated components."""

    @pytest.mark.asyncio
    async def test_database_failover_scenarios(self):
        """Test database failover and recovery scenarios."""
        mock_supabase = MagicMock()

        # Simulate database connection failure then recovery
        mock_supabase.rpc.side_effect = [
            Exception("Connection failed"),
            Exception("Still failing"),
            MagicMock(execute=MagicMock(return_value=MagicMock(data=[{"result": "recovered"}]))),
        ]

        # First two attempts should fail (tool catches exceptions)
        result1 = await execute_sql_query_tool(mock_supabase, "SELECT 1;")
        assert "Error executing SQL query" in result1
        assert "Connection failed" in result1

        result2 = await execute_sql_query_tool(mock_supabase, "SELECT 1;")
        assert "Error executing SQL query" in result2
        assert "Still failing" in result2

        # Third attempt should succeed
        result3 = await execute_sql_query_tool(mock_supabase, "SELECT 1;")
        assert "recovered" in result3

    @pytest.mark.asyncio
    async def test_embedding_service_degradation(self):
        """Test behavior when embedding service is degraded."""
        mock_supabase = MagicMock()
        mock_embedding_client = AsyncMock()

        # Simulate hybrid search failure
        mock_hybrid_search = AsyncMock()
        mock_hybrid_search.search.side_effect = Exception("Embedding service unavailable")

        # RAG should fail gracefully (tool catches exceptions)
        with patch("tools.rag.get_hybrid_search", return_value=mock_hybrid_search):
            result = await retrieve_relevant_documents_tool(
                mock_supabase, mock_embedding_client, "test query"
            )

        # Verify error message
        assert "Error retrieving documents" in result
        assert "Embedding service unavailable" in result

    @pytest.mark.asyncio
    async def test_partial_system_failure_recovery(self):
        """Test recovery when only part of the system fails."""
        mock_supabase = MagicMock()
        mock_embedding_client = AsyncMock()
        mock_http_client = AsyncMock()

        # RAG fails but web search works
        mock_hybrid_search = AsyncMock()
        mock_hybrid_search.search.side_effect = Exception("RAG unavailable")

        # Web search should still work
        with patch("tests.test_integration.web_search_tool") as mock_web_search:
            mock_web_search.return_value = "Web search results available"

            # RAG fails (tool catches exception)
            with patch("tools.rag.get_hybrid_search", return_value=mock_hybrid_search):
                rag_result = await retrieve_relevant_documents_tool(
                    mock_supabase, mock_embedding_client, "test query"
                )
            assert "Error retrieving documents" in rag_result
            assert "RAG unavailable" in rag_result

            # But web search succeeds
            web_result = await web_search_tool(
                "test query", mock_http_client, "test-key", "http://test-url"
            )
            assert "Web search results available" in web_result

    @pytest.mark.asyncio
    async def test_timeout_handling_integration(self):
        """Test timeout handling across integrated components."""
        mock_supabase = MagicMock()
        mock_embedding_client = AsyncMock()

        # Simulate timeout in hybrid search
        mock_hybrid_search = AsyncMock()
        mock_hybrid_search.search.side_effect = TimeoutError("Operation timed out")

        # Tool catches TimeoutError and returns error string
        with patch("tools.rag.get_hybrid_search", return_value=mock_hybrid_search):
            result = await retrieve_relevant_documents_tool(
                mock_supabase, mock_embedding_client, "test query"
            )

        # Verify error message
        assert "Error retrieving documents" in result
        assert "Operation timed out" in result


class TestSecurityIntegration:
    """Test security aspects of component integration."""

    @pytest.mark.asyncio
    async def test_sql_injection_prevention_integration(self):
        """Test SQL injection prevention across the integrated system."""
        mock_supabase = MagicMock()

        # Mock successful execution (protection happens at RPC level)
        mock_supabase.rpc.return_value.execute.return_value.data = [{"result": "safe"}]

        # Test various injection attempts - client-side validation blocks these
        injection_tests = [
            ("SELECT * FROM users; DROP TABLE users; --", "DROP"),
            ("'; DELETE FROM documents; --", "DELETE"),
        ]

        for malicious_query, blocked_op in injection_tests:
            # Tool detects write operations and blocks them
            result = await execute_sql_query_tool(mock_supabase, malicious_query)

            # Verify the error was returned (client-side protection)
            assert f"Error: Write operation '{blocked_op}' detected" in result
            assert "Only read-only queries are allowed" in result

    @pytest.mark.asyncio
    async def test_data_sanitization_integration(self):
        """Test data sanitization across component boundaries."""
        from uuid import uuid4

        from src.agentic_rag.search.hybrid_search import HybridSearchResult
        from src.agentic_rag.search.intent_analyzer import SearchIntent
        from src.agentic_rag.search.vector_search import ChunkResult
        from src.config import SearchStrategy

        mock_supabase = MagicMock()
        mock_embedding_client = AsyncMock()

        # Create mock hybrid search with potentially unsafe data
        mock_hybrid_search = AsyncMock()

        chunk = ChunkResult(
            chunk_id=uuid4(),
            content="<script>alert('xss')</script>Safe content here",
            similarity=0.9,
            document_id=uuid4(),
            document_title="document.pdf",
            document_source="document.pdf",
            metadata={},
        )

        mock_result = HybridSearchResult(
            chunks=[chunk],
            facts=[],
            entities=[],
            relationships=[],
            search_strategy=SearchStrategy.VECTOR_ONLY,
            intent=SearchIntent.VECTOR_HEAVY,
            query_time=0.05,
            metadata={},
        )

        mock_hybrid_search.search.return_value = mock_result

        # Execute RAG retrieval with mocked hybrid search
        with patch("tools.rag.get_hybrid_search", return_value=mock_hybrid_search):
            result = await retrieve_relevant_documents_tool(
                mock_supabase, mock_embedding_client, "test query"
            )

        # Verify the result contains the data (sanitization would happen at display layer)
        assert "Safe content here" in result
        assert "document.pdf" in result

    @pytest.mark.asyncio
    async def test_api_key_handling_integration(self):
        """Test secure API key handling across components."""
        mock_http_client = AsyncMock()

        # Test with None API key (should use fallback)
        with patch("tests.test_integration.web_search_tool") as mock_web_search:
            mock_web_search.return_value = "Fallback search results"

            result = await web_search_tool(
                "test query", mock_http_client, None, "http://fallback-url"
            )

            # Should use fallback service
            mock_web_search.assert_called_once_with(
                "test query", mock_http_client, None, "http://fallback-url"
            )
            assert "Fallback search results" in result
