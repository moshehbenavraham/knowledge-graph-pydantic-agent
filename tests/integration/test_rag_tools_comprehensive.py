"""
Comprehensive integration tests for tools/rag.py.

Tests RAG tool functions including hybrid search, intent analysis, and document retrieval.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


@pytest.fixture
def mock_hybrid_search():
    """Mock HybridSearch instance."""
    search = MagicMock()
    search.search = AsyncMock()
    return search


@pytest.fixture
def mock_intent_analyzer():
    """Mock IntentAnalyzer instance."""
    analyzer = MagicMock()
    analyzer.analyze = MagicMock()
    return analyzer


@pytest.fixture
def mock_search_result():
    """Mock HybridSearchResult."""
    from src.config import SearchStrategy

    chunk = MagicMock()
    chunk.chunk_id = uuid4()
    chunk.content = "Test content"
    chunk.document_id = uuid4()
    chunk.document_title = "Test Document"
    chunk.document_source = "test.pdf"
    chunk.similarity = 0.95
    chunk.entities = ["Entity1", "Entity2"]

    # Create entities with proper name attributes
    entity1 = MagicMock()
    entity1.name = "Entity1"
    entity2 = MagicMock()
    entity2.name = "Entity2"

    result = MagicMock()
    result.chunks = [chunk]
    result.entities = [entity1, entity2]
    result.facts = []
    result.relationships = []
    result.search_strategy = SearchStrategy.VECTOR_ONLY
    result.query_time = 0.15
    return result


class TestGetHybridSearch:
    """Test get_hybrid_search function."""

    @patch("src.agentic_rag.storage.connection_manager.get_connection_manager")
    async def test_get_hybrid_search_creates_instance(self, mock_conn_mgr):
        """Test hybrid search instance creation."""
        from src.tools.rag import get_hybrid_search

        mock_conn_mgr.return_value = MagicMock()

        search = await get_hybrid_search()

        assert search is not None
        assert mock_conn_mgr.called

    @patch("src.tools.rag._hybrid_search", new=None)
    @patch("src.agentic_rag.storage.connection_manager.get_connection_manager")
    async def test_get_hybrid_search_singleton(self, mock_conn_mgr):
        """Test hybrid search is singleton."""
        from src.tools.rag import get_hybrid_search

        mock_conn_mgr.return_value = MagicMock()

        search1 = await get_hybrid_search()
        search2 = await get_hybrid_search()

        # Should return same instance
        assert search1 is search2

    @patch("src.tools.rag._hybrid_search", new=None)
    @patch("src.tools.rag._connection_manager", new=None)
    @patch("src.tools.rag._current_loop", new=None)
    @patch("src.agentic_rag.storage.connection_manager.get_connection_manager")
    async def test_get_hybrid_search_event_loop_change(self, mock_conn_mgr):
        """Test handling of event loop changes."""
        from src.tools.rag import get_hybrid_search

        mock_conn_mgr.return_value = MagicMock()

        search = await get_hybrid_search()

        assert search is not None


class TestGetIntentAnalyzer:
    """Test get_intent_analyzer function."""

    def test_get_intent_analyzer_creates_instance(self):
        """Test intent analyzer creation."""
        from src.tools.rag import get_intent_analyzer

        analyzer = get_intent_analyzer()

        assert analyzer is not None

    @patch("src.tools.rag._intent_analyzer", new=None)
    def test_get_intent_analyzer_singleton(self):
        """Test intent analyzer is singleton."""
        from src.tools.rag import get_intent_analyzer

        analyzer1 = get_intent_analyzer()
        analyzer2 = get_intent_analyzer()

        assert analyzer1 is analyzer2


class TestRetrieveRelevantDocumentsTool:
    """Test retrieve_relevant_documents_tool function."""

    @patch("src.tools.rag.get_hybrid_search")
    async def test_retrieve_documents_basic(
        self, mock_get_search, mock_hybrid_search, mock_search_result
    ):
        """Test basic document retrieval."""
        from src.tools.rag import retrieve_relevant_documents_tool

        mock_get_search.return_value = mock_hybrid_search
        mock_hybrid_search.search.return_value = mock_search_result

        result = await retrieve_relevant_documents_tool(
            supabase=None,
            embedding_client=None,
            user_query="test query",
        )

        assert isinstance(result, str)
        assert "Test Document" in result
        assert "Test content" in result

    @patch("src.tools.rag.get_hybrid_search")
    async def test_retrieve_documents_with_strategy(
        self, mock_get_search, mock_hybrid_search, mock_search_result
    ):
        """Test retrieval with specific strategy."""
        from src.config import SearchStrategy
        from src.tools.rag import retrieve_relevant_documents_tool

        mock_get_search.return_value = mock_hybrid_search
        mock_hybrid_search.search.return_value = mock_search_result

        await retrieve_relevant_documents_tool(
            supabase=None,
            embedding_client=None,
            user_query="test query",
            strategy=SearchStrategy.GRAPH_ONLY,
            limit=5,
        )

        # Verify search was called with correct strategy
        call_args = mock_hybrid_search.search.call_args
        assert call_args[1]["strategy"] == SearchStrategy.GRAPH_ONLY
        assert call_args[1]["limit"] == 5

    @patch("src.tools.rag.get_hybrid_search")
    async def test_retrieve_documents_no_results(self, mock_get_search, mock_hybrid_search):
        """Test retrieval with no results."""
        from src.tools.rag import retrieve_relevant_documents_tool

        empty_result = MagicMock()
        empty_result.chunks = []
        empty_result.entities = []

        mock_get_search.return_value = mock_hybrid_search
        mock_hybrid_search.search.return_value = empty_result

        result = await retrieve_relevant_documents_tool(
            supabase=None,
            embedding_client=None,
            user_query="test query",
        )

        assert "No relevant documents found" in result

    @patch("src.tools.rag.get_hybrid_search")
    async def test_retrieve_documents_error(self, mock_get_search, mock_hybrid_search):
        """Test error handling in retrieval."""
        from src.tools.rag import retrieve_relevant_documents_tool

        mock_get_search.return_value = mock_hybrid_search
        mock_hybrid_search.search.side_effect = Exception("Search failed")

        result = await retrieve_relevant_documents_tool(
            supabase=None,
            embedding_client=None,
            user_query="test query",
        )

        assert "Error retrieving documents" in result


class TestSmartSearchTool:
    """Test smart_search_tool function."""

    @patch("src.tools.rag.get_hybrid_search")
    @patch("src.tools.rag.get_intent_analyzer")
    async def test_smart_search_basic(
        self,
        mock_get_analyzer,
        mock_get_search,
        mock_hybrid_search,
        mock_intent_analyzer,
        mock_search_result,
    ):
        """Test basic smart search."""
        from src.config import SearchIntent
        from src.tools.rag import smart_search_tool

        mock_get_search.return_value = mock_hybrid_search
        mock_get_analyzer.return_value = mock_intent_analyzer
        mock_hybrid_search.search.return_value = mock_search_result

        intent_result = MagicMock()
        intent_result.primary_intent = SearchIntent.VECTOR_HEAVY
        mock_intent_analyzer.analyze.return_value = intent_result

        result = await smart_search_tool("test query")

        assert isinstance(result, dict)
        assert "query" in result
        assert "chunks" in result
        assert "entities" in result
        assert "intent" in result

    @patch("src.tools.rag.get_hybrid_search")
    async def test_smart_search_without_intent_analysis(
        self, mock_get_search, mock_hybrid_search, mock_search_result
    ):
        """Test smart search without intent analysis."""
        from src.tools.rag import smart_search_tool

        mock_get_search.return_value = mock_hybrid_search
        mock_hybrid_search.search.return_value = mock_search_result

        result = await smart_search_tool("test query", analyze_intent=False)

        assert result["intent"] is None

    @patch("src.tools.rag.get_hybrid_search")
    @patch("src.tools.rag.get_intent_analyzer")
    async def test_smart_search_with_limit(
        self,
        mock_get_analyzer,
        mock_get_search,
        mock_hybrid_search,
        mock_intent_analyzer,
        mock_search_result,
    ):
        """Test smart search with custom limit."""
        from src.config import SearchIntent
        from src.tools.rag import smart_search_tool

        mock_get_search.return_value = mock_hybrid_search
        mock_get_analyzer.return_value = mock_intent_analyzer
        mock_hybrid_search.search.return_value = mock_search_result

        intent_result = MagicMock()
        intent_result.primary_intent = SearchIntent.VECTOR_HEAVY
        mock_intent_analyzer.analyze.return_value = intent_result

        await smart_search_tool("test query", limit=20)

        call_args = mock_hybrid_search.search.call_args
        assert call_args[1]["limit"] == 20

    @patch("src.tools.rag.get_hybrid_search")
    async def test_smart_search_error(self, mock_get_search, mock_hybrid_search):
        """Test error handling in smart search."""
        from src.tools.rag import smart_search_tool

        mock_get_search.return_value = mock_hybrid_search
        mock_hybrid_search.search.side_effect = Exception("Search failed")

        result = await smart_search_tool("test query")

        assert "error" in result
        assert result["chunks"] == []


class TestGraphQueryTool:
    """Test graph_query_tool function."""

    @patch("src.tools.rag.get_config")
    @patch("src.tools.rag.get_hybrid_search")
    async def test_graph_query_basic(self, mock_get_search, mock_get_config, mock_hybrid_search):
        """Test basic graph query."""
        from src.tools.rag import graph_query_tool

        # Mock config with graph enabled
        config = MagicMock()
        config.performance.enable_graph = True
        mock_get_config.return_value = config

        # Mock search result
        result = MagicMock()
        result.facts = [MagicMock(description="Fact 1", created_at="2024-01-01")]
        result.entities = [MagicMock(name="Entity1", type="person")]
        result.relationships = []

        mock_get_search.return_value = mock_hybrid_search
        mock_hybrid_search.search.return_value = result

        response = await graph_query_tool(entity_name="TestEntity")

        assert isinstance(response, dict)
        assert "facts" in response
        assert "entities" in response

    @patch("src.tools.rag.get_config")
    async def test_graph_query_disabled(self, mock_get_config):
        """Test graph query when graph disabled."""
        from src.tools.rag import graph_query_tool

        config = MagicMock()
        config.performance.enable_graph = False
        mock_get_config.return_value = config

        response = await graph_query_tool(entity_name="TestEntity")

        assert "error" in response
        assert "not enabled" in response["error"]

    @patch("src.tools.rag.get_config")
    @patch("src.tools.rag.get_hybrid_search")
    async def test_graph_query_types(self, mock_get_search, mock_get_config, mock_hybrid_search):
        """Test different graph query types."""
        from src.tools.rag import graph_query_tool

        config = MagicMock()
        config.performance.enable_graph = True
        mock_get_config.return_value = config

        result = MagicMock()
        result.facts = []
        result.entities = []
        result.relationships = []

        mock_get_search.return_value = mock_hybrid_search
        mock_hybrid_search.search.return_value = result

        # Test different query types
        for query_type in ["entity_facts", "entity_relationships", "temporal_facts"]:
            response = await graph_query_tool(entity_name="Test", query_type=query_type)
            assert response["query_type"] == query_type


class TestListDocumentsTool:
    """Test list_documents_tool function."""

    async def test_list_documents_basic(self):
        """Test basic document listing."""
        from src.tools.rag import list_documents_tool

        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {
                "id": str(uuid4()),
                "title": "Doc 1",
                "source": "test1.pdf",
                "created_at": "2024-01-01",
            },
            {
                "id": str(uuid4()),
                "title": "Doc 2",
                "source": "test2.pdf",
                "created_at": "2024-01-02",
            },
        ]

        mock_supabase.from_.return_value.select.return_value.execute.return_value = mock_result

        docs = await list_documents_tool(mock_supabase)

        assert len(docs) == 2
        assert "Doc 1" in docs[0]
        assert "Doc 2" in docs[1]

    async def test_list_documents_empty(self):
        """Test listing with no documents."""
        from src.tools.rag import list_documents_tool

        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []

        mock_supabase.from_.return_value.select.return_value.execute.return_value = mock_result

        docs = await list_documents_tool(mock_supabase)

        assert len(docs) == 0

    async def test_list_documents_error(self):
        """Test error handling in document listing."""
        from src.tools.rag import list_documents_tool

        mock_supabase = MagicMock()
        mock_supabase.from_.side_effect = Exception("Database error")

        docs = await list_documents_tool(mock_supabase)

        assert len(docs) == 0


class TestGetDocumentContentTool:
    """Test get_document_content_tool function."""

    async def test_get_document_by_uuid(self):
        """Test getting document by UUID."""
        from src.tools.rag import get_document_content_tool

        doc_id = str(uuid4())

        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {
                "id": doc_id,
                "title": "Test Doc",
                "content": "Document content here",
                "source": "test.pdf",
            }
        ]

        mock_supabase.from_.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_result
        )

        content = await get_document_content_tool(mock_supabase, doc_id)

        assert "Test Doc" in content
        assert "Document content here" in content

    async def test_get_document_by_title(self):
        """Test getting document by title search."""
        from src.tools.rag import get_document_content_tool

        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {
                "id": str(uuid4()),
                "title": "Matching Title",
                "content": "Content",
                "source": "test.pdf",
            }
        ]

        mock_supabase.from_.return_value.select.return_value.or_.return_value.limit.return_value.execute.return_value = (
            mock_result
        )

        content = await get_document_content_tool(mock_supabase, "not-a-uuid")

        assert "Matching Title" in content

    async def test_get_document_not_found(self):
        """Test getting non-existent document."""
        from src.tools.rag import get_document_content_tool

        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []

        mock_supabase.from_.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_result
        )

        content = await get_document_content_tool(mock_supabase, str(uuid4()))

        assert "No document found" in content

    async def test_get_document_error(self):
        """Test error handling."""
        from src.tools.rag import get_document_content_tool

        mock_supabase = MagicMock()
        mock_supabase.from_.side_effect = Exception("Database error")

        content = await get_document_content_tool(mock_supabase, "test-id")

        assert "Error retrieving document" in content


class TestFormatSearchResults:
    """Test _format_search_results function."""

    def test_format_results_basic(self, mock_search_result):
        """Test basic result formatting."""
        from src.tools.rag import _format_search_results

        formatted = _format_search_results(mock_search_result)

        assert isinstance(formatted, str)
        assert "Test Document" in formatted
        assert "Test content" in formatted
        assert "Search Strategy" in formatted

    def test_format_results_empty(self):
        """Test formatting empty results."""
        from src.tools.rag import _format_search_results

        empty_result = MagicMock()
        empty_result.chunks = []

        formatted = _format_search_results(empty_result)

        assert "No relevant documents found" in formatted

    def test_format_results_with_entities(self, mock_search_result):
        """Test formatting with entities."""
        from src.tools.rag import _format_search_results

        formatted = _format_search_results(mock_search_result)

        assert "Related Entities" in formatted
        assert "Entity1" in formatted or "Entity2" in formatted

    def test_format_results_metadata(self, mock_search_result):
        """Test formatting includes metadata."""
        from src.tools.rag import _format_search_results

        formatted = _format_search_results(mock_search_result)

        assert "Query Time" in formatted
        assert "Total Results" in formatted
        assert "Relevance Score" in formatted


class TestCleanupRagTools:
    """Test cleanup_rag_tools function."""

    @patch("src.tools.rag._connection_manager")
    async def test_cleanup_closes_connections(self, mock_conn_mgr):
        """Test cleanup closes connection manager."""
        from src.tools.rag import cleanup_rag_tools

        mock_conn_mgr.close = AsyncMock()

        await cleanup_rag_tools()

        assert mock_conn_mgr.close.called

    @patch("src.tools.rag._connection_manager", new=None)
    async def test_cleanup_handles_none(self):
        """Test cleanup handles None connection manager."""
        from src.tools.rag import cleanup_rag_tools

        # Should not raise
        await cleanup_rag_tools()


class TestConcurrentOperations:
    """Test concurrent RAG operations."""

    @patch("src.tools.rag.get_hybrid_search")
    async def test_concurrent_searches(
        self, mock_get_search, mock_hybrid_search, mock_search_result
    ):
        """Test multiple concurrent searches."""
        import asyncio

        from src.tools.rag import smart_search_tool

        mock_get_search.return_value = mock_hybrid_search
        mock_hybrid_search.search.return_value = mock_search_result

        # Run 10 concurrent searches
        tasks = [smart_search_tool(f"query {i}", analyze_intent=False) for i in range(10)]

        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        for result in results:
            assert "query" in result
            assert "chunks" in result

    @patch("src.tools.rag.get_hybrid_search")
    async def test_concurrent_different_tools(
        self, mock_get_search, mock_hybrid_search, mock_search_result
    ):
        """Test different tools concurrently."""
        import asyncio

        from src.tools.rag import retrieve_relevant_documents_tool, smart_search_tool

        mock_get_search.return_value = mock_hybrid_search
        mock_hybrid_search.search.return_value = mock_search_result

        tasks = [
            smart_search_tool("query 1", analyze_intent=False),
            retrieve_relevant_documents_tool(None, None, "query 2"),
            smart_search_tool("query 3", analyze_intent=False),
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch("src.tools.rag.get_hybrid_search")
    async def test_empty_query(self, mock_get_search, mock_hybrid_search, mock_search_result):
        """Test handling of empty query."""
        from src.tools.rag import smart_search_tool

        mock_get_search.return_value = mock_hybrid_search
        mock_hybrid_search.search.return_value = mock_search_result

        result = await smart_search_tool("", analyze_intent=False)

        assert isinstance(result, dict)

    @patch("src.tools.rag.get_hybrid_search")
    async def test_very_long_query(self, mock_get_search, mock_hybrid_search, mock_search_result):
        """Test handling of very long query."""
        from src.tools.rag import smart_search_tool

        mock_get_search.return_value = mock_hybrid_search
        mock_hybrid_search.search.return_value = mock_search_result

        long_query = "test " * 1000
        result = await smart_search_tool(long_query, analyze_intent=False)

        assert isinstance(result, dict)

    @patch("src.tools.rag.get_hybrid_search")
    async def test_special_characters_in_query(
        self, mock_get_search, mock_hybrid_search, mock_search_result
    ):
        """Test handling of special characters."""
        from src.tools.rag import smart_search_tool

        mock_get_search.return_value = mock_hybrid_search
        mock_hybrid_search.search.return_value = mock_search_result

        special_query = "test @#$%^&*(){}[]|\\:;\"'<>?/"
        result = await smart_search_tool(special_query, analyze_intent=False)

        assert isinstance(result, dict)

    @patch("src.tools.rag.get_hybrid_search")
    async def test_unicode_query(self, mock_get_search, mock_hybrid_search, mock_search_result):
        """Test handling of Unicode characters."""
        from src.tools.rag import smart_search_tool

        mock_get_search.return_value = mock_hybrid_search
        mock_hybrid_search.search.return_value = mock_search_result

        unicode_query = "test 中文 العربية עברית 日本語"
        result = await smart_search_tool(unicode_query, analyze_intent=False)

        assert isinstance(result, dict)


class TestResultFormatting:
    """Test result formatting edge cases."""

    def test_format_with_very_long_content(self):
        """Test formatting with very long content."""
        from src.config import SearchStrategy
        from src.tools.rag import _format_search_results

        chunk = MagicMock()
        chunk.chunk_id = uuid4()
        chunk.content = "x" * 10000  # Very long content
        chunk.document_id = uuid4()
        chunk.document_title = "Test"
        chunk.document_source = "test.pdf"
        chunk.similarity = 0.95
        chunk.entities = []

        result = MagicMock()
        result.chunks = [chunk]
        result.entities = []
        result.facts = []
        result.search_strategy = SearchStrategy.VECTOR_ONLY
        result.query_time = 0.1

        formatted = _format_search_results(result)

        assert isinstance(formatted, str)
        assert len(formatted) > 0

    def test_format_with_many_chunks(self):
        """Test formatting with many chunks."""
        from src.config import SearchStrategy
        from src.tools.rag import _format_search_results

        chunks = []
        for i in range(100):
            chunk = MagicMock()
            chunk.chunk_id = uuid4()
            chunk.content = f"Content {i}"
            chunk.document_id = uuid4()
            chunk.document_title = f"Doc {i}"
            chunk.document_source = f"doc{i}.pdf"
            chunk.similarity = 0.9 - (i * 0.001)
            chunk.entities = []
            chunks.append(chunk)

        result = MagicMock()
        result.chunks = chunks
        result.entities = []
        result.facts = []
        result.search_strategy = SearchStrategy.VECTOR_ONLY
        result.query_time = 0.5

        formatted = _format_search_results(result)

        assert isinstance(formatted, str)
        assert len(formatted) > 0

    def test_format_with_many_entities(self):
        """Test formatting with many entities."""
        from src.config import SearchStrategy
        from src.tools.rag import _format_search_results

        # Create entities with proper name attributes
        entities = []
        for i in range(100):
            entity = MagicMock()
            entity.name = f"Entity{i}"
            entities.append(entity)

        chunk = MagicMock()
        chunk.chunk_id = uuid4()
        chunk.content = "Test content"
        chunk.document_id = uuid4()
        chunk.document_title = "Test"
        chunk.document_source = "test.pdf"
        chunk.similarity = 0.95
        chunk.entities = []

        result = MagicMock()
        result.chunks = [chunk]
        result.entities = entities
        result.facts = []
        result.search_strategy = SearchStrategy.GRAPH_ONLY
        result.query_time = 0.3

        formatted = _format_search_results(result)

        assert "Related Entities" in formatted
        # Should only show first 5 entities
        assert len([e for e in formatted.split("\n") if "Entity" in e]) <= 10


class TestIntentAnalysisIntegration:
    """Test intent analysis integration."""

    @patch("src.tools.rag.get_hybrid_search")
    @patch("src.tools.rag.get_intent_analyzer")
    async def test_intent_affects_strategy(
        self, mock_get_analyzer, mock_get_search, mock_hybrid_search, mock_intent_analyzer
    ):
        """Test that intent analysis affects search strategy."""
        from src.config import SearchIntent, SearchStrategy
        from src.tools.rag import smart_search_tool

        mock_get_search.return_value = mock_hybrid_search
        mock_get_analyzer.return_value = mock_intent_analyzer

        # Mock result
        result = MagicMock()
        result.chunks = []
        result.entities = []
        result.facts = []
        result.search_strategy = SearchStrategy.GRAPH_ONLY
        result.query_time = 0.1
        mock_hybrid_search.search.return_value = result

        # Test with GRAPH_HEAVY intent
        intent_result = MagicMock()
        intent_result.primary_intent = SearchIntent.GRAPH_HEAVY
        mock_intent_analyzer.analyze.return_value = intent_result

        response = await smart_search_tool("test query with relationships", analyze_intent=True)

        assert response["intent"] == "graph_heavy"  # Enum value, not name

    @patch("src.tools.rag.get_hybrid_search")
    @patch("src.tools.rag.get_intent_analyzer")
    async def test_different_intents(
        self, mock_get_analyzer, mock_get_search, mock_hybrid_search, mock_intent_analyzer
    ):
        """Test different intent types."""
        from src.config import SearchIntent
        from src.tools.rag import smart_search_tool

        mock_get_search.return_value = mock_hybrid_search
        mock_get_analyzer.return_value = mock_intent_analyzer

        result = MagicMock()
        result.chunks = []
        result.entities = []
        result.facts = []
        result.search_strategy = MagicMock(value="VECTOR_ONLY")
        result.query_time = 0.1
        mock_hybrid_search.search.return_value = result

        intents = [
            SearchIntent.VECTOR_HEAVY,
            SearchIntent.GRAPH_HEAVY,
            SearchIntent.HYBRID,
            SearchIntent.TEMPORAL,
            SearchIntent.ENTITY_FOCUSED,
        ]

        for intent in intents:
            intent_result = MagicMock()
            intent_result.primary_intent = intent
            mock_intent_analyzer.analyze.return_value = intent_result

            response = await smart_search_tool("test", analyze_intent=True)

            assert response["intent"] == intent.value


class TestDocumentRetrieval:
    """Test document retrieval scenarios."""

    async def test_get_document_content_truncation(self):
        """Test document content is truncated at 20000 chars."""
        from src.tools.rag import get_document_content_tool

        long_content = "x" * 30000

        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {
                "id": str(uuid4()),
                "title": "Test",
                "content": long_content,
                "source": "test.pdf",
            }
        ]

        mock_supabase.from_.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_result
        )

        content = await get_document_content_tool(mock_supabase, str(uuid4()))

        # Content should be truncated
        assert len(content) < 30000
        assert "Test" in content

    async def test_list_documents_formatting(self):
        """Test document list formatting."""
        from src.tools.rag import list_documents_tool

        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {
                "id": str(uuid4()),
                "title": "Document Title",
                "source": "/path/to/doc.pdf",
                "created_at": "2024-01-15T10:30:00",
            }
        ]

        mock_supabase.from_.return_value.select.return_value.execute.return_value = mock_result

        docs = await list_documents_tool(mock_supabase)

        assert len(docs) == 1
        assert "Document Title" in docs[0]
        assert "/path/to/doc.pdf" in docs[0]
        assert "2024-01-15" in docs[0]


class TestSearchStrategies:
    """Test different search strategies."""

    @patch("src.tools.rag.get_hybrid_search")
    async def test_vector_only_strategy(
        self, mock_get_search, mock_hybrid_search, mock_search_result
    ):
        """Test VECTOR_ONLY strategy."""
        from src.config import SearchStrategy
        from src.tools.rag import retrieve_relevant_documents_tool

        mock_get_search.return_value = mock_hybrid_search
        mock_hybrid_search.search.return_value = mock_search_result

        await retrieve_relevant_documents_tool(
            None, None, "test", strategy=SearchStrategy.VECTOR_ONLY
        )

        call_args = mock_hybrid_search.search.call_args
        assert call_args[1]["strategy"] == SearchStrategy.VECTOR_ONLY

    @patch("src.tools.rag.get_hybrid_search")
    async def test_graph_only_strategy(self, mock_get_search, mock_hybrid_search):
        """Test GRAPH_ONLY strategy."""
        from src.config import SearchStrategy
        from src.tools.rag import retrieve_relevant_documents_tool

        mock_get_search.return_value = mock_hybrid_search

        result = MagicMock()
        result.chunks = []
        result.entities = []
        result.facts = []
        result.search_strategy = SearchStrategy.GRAPH_ONLY
        result.query_time = 0.1
        mock_hybrid_search.search.return_value = result

        await retrieve_relevant_documents_tool(
            None, None, "test", strategy=SearchStrategy.GRAPH_ONLY
        )

        call_args = mock_hybrid_search.search.call_args
        assert call_args[1]["strategy"] == SearchStrategy.GRAPH_ONLY


class TestErrorRecovery:
    """Test error recovery mechanisms."""

    @patch("src.tools.rag.get_hybrid_search")
    async def test_search_timeout_recovery(self, mock_get_search, mock_hybrid_search):
        """Test recovery from search timeout."""

        from src.tools.rag import smart_search_tool

        mock_get_search.return_value = mock_hybrid_search
        mock_hybrid_search.search.side_effect = TimeoutError("Timeout")

        result = await smart_search_tool("test")

        assert "error" in result
        assert result["chunks"] == []

    @patch("src.tools.rag.get_hybrid_search")
    async def test_connection_error_recovery(self, mock_get_search, mock_hybrid_search):
        """Test recovery from connection errors."""
        from src.tools.rag import retrieve_relevant_documents_tool

        mock_get_search.return_value = mock_hybrid_search
        mock_hybrid_search.search.side_effect = ConnectionError("Connection lost")

        result = await retrieve_relevant_documents_tool(None, None, "test")

        assert "Error retrieving documents" in result


class TestPerformanceMetrics:
    """Test performance metrics in results."""

    @patch("src.tools.rag.get_hybrid_search")
    async def test_query_time_recorded(
        self, mock_get_search, mock_hybrid_search, mock_search_result
    ):
        """Test query time is recorded."""
        from src.tools.rag import smart_search_tool

        mock_get_search.return_value = mock_hybrid_search
        mock_search_result.query_time = 0.234
        mock_hybrid_search.search.return_value = mock_search_result

        result = await smart_search_tool("test", analyze_intent=False)

        assert "query_time_ms" in result
        assert result["query_time_ms"] == 234.0

    def test_format_includes_timing(self, mock_search_result):
        """Test formatted results include timing."""
        from src.tools.rag import _format_search_results

        formatted = _format_search_results(mock_search_result)

        assert "Query Time" in formatted
        assert "150ms" in formatted or "0.15" in formatted or "150" in formatted
