"""
Comprehensive tests for rag.py module.

Tests all RAG tools including hybrid search, intent analysis, graph queries,
document retrieval, and result formatting.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.agentic_rag.search.hybrid_search import HybridSearchResult
from src.config import SearchStrategy
from src.tools.rag import (
    _format_search_results,
    cleanup_rag_tools,
    get_document_content_tool,
    get_hybrid_search,
    get_intent_analyzer,
    graph_query_tool,
    list_documents_tool,
    retrieve_relevant_documents_tool,
    smart_search_tool,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    client = MagicMock()
    client.from_ = MagicMock()
    return client


@pytest.fixture
def mock_search_result():
    """Create a mock HybridSearchResult."""

    class MockChunk:
        def __init__(self, chunk_id, content, doc_id, title, source, similarity, entities):
            self.chunk_id = chunk_id
            self.content = content
            self.document_id = doc_id
            self.document_title = title
            self.document_source = source
            self.similarity = similarity
            self.entities = entities

    class MockEntity:
        def __init__(self, name, entity_type):
            self.name = name
            self.type = entity_type

    class MockFact:
        def __init__(self, description, created_at=None):
            self.description = description
            self.created_at = created_at

    result = MagicMock(spec=HybridSearchResult)
    result.chunks = [
        MockChunk(
            chunk_id=uuid4(),
            content="This is test content for chunk 1",
            doc_id=uuid4(),
            title="Test Document 1",
            source="test_source_1.txt",
            similarity=0.95,
            entities=["Entity1", "Entity2"],
        ),
        MockChunk(
            chunk_id=uuid4(),
            content="This is test content for chunk 2",
            doc_id=uuid4(),
            title="Test Document 2",
            source="test_source_2.txt",
            similarity=0.88,
            entities=[],
        ),
    ]
    result.entities = [
        MockEntity("Entity1", "person"),
        MockEntity("Entity2", "organization"),
    ]
    result.facts = [MockFact("Test fact 1"), MockFact("Test fact 2")]
    result.relationships = []
    result.search_strategy = SearchStrategy.COMPREHENSIVE
    result.query_time = 0.125
    return result


@pytest.fixture
def mock_connection_manager():
    """Mock ConnectionManager."""
    manager = AsyncMock()
    manager.close = AsyncMock()
    return manager


@pytest.fixture
def mock_hybrid_search():
    """Mock HybridSearch instance."""
    search = AsyncMock()
    search.search = AsyncMock()
    return search


# ============================================================================
# get_hybrid_search Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.tools.rag.get_connection_manager")
@patch("src.tools.rag.HybridSearch")
async def test_get_hybrid_search_first_call(mock_hs_class, mock_get_cm):
    """Test first call to get_hybrid_search initializes everything."""
    mock_cm = AsyncMock()
    mock_get_cm.return_value = mock_cm
    mock_hs = AsyncMock()
    mock_hs_class.return_value = mock_hs

    # Reset module state
    import src.tools.rag as rag_module

    rag_module._connection_manager = None
    rag_module._hybrid_search = None

    result = await get_hybrid_search()

    assert result == mock_hs
    mock_get_cm.assert_called_once()
    mock_hs_class.assert_called_once_with(mock_cm)


@pytest.mark.asyncio
@patch("src.tools.rag.get_connection_manager")
@patch("src.tools.rag.HybridSearch")
async def test_get_hybrid_search_cached(mock_hs_class, mock_get_cm):
    """Test subsequent calls return cached instance."""
    mock_cm = AsyncMock()
    mock_get_cm.return_value = mock_cm
    mock_hs = AsyncMock()
    mock_hs_class.return_value = mock_hs

    # Reset and get first time
    import src.tools.rag as rag_module

    rag_module._connection_manager = None
    rag_module._hybrid_search = None
    rag_module._current_loop = asyncio.get_running_loop()

    result1 = await get_hybrid_search()
    result2 = await get_hybrid_search()

    assert result1 == result2
    # Should only initialize once
    assert mock_get_cm.call_count == 1
    assert mock_hs_class.call_count == 1


@pytest.mark.asyncio
@patch("src.tools.rag.get_connection_manager")
@patch("src.tools.rag.HybridSearch")
async def test_get_hybrid_search_event_loop_change(mock_hs_class, mock_get_cm):
    """Test that changing event loop resets instances."""
    mock_cm = AsyncMock()
    mock_get_cm.return_value = mock_cm
    mock_hs = AsyncMock()
    mock_hs_class.return_value = mock_hs

    import src.tools.rag as rag_module

    rag_module._connection_manager = None
    rag_module._hybrid_search = None

    # Set a different loop ID to simulate loop change
    rag_module._current_loop = None

    await get_hybrid_search()

    # Verify reset happened
    assert mock_get_cm.call_count == 1


# ============================================================================
# get_intent_analyzer Tests
# ============================================================================


@patch("src.tools.rag.IntentAnalyzer")
def test_get_intent_analyzer_first_call(mock_ia_class):
    """Test first call to get_intent_analyzer initializes."""
    mock_ia = MagicMock()
    mock_ia_class.return_value = mock_ia

    # Reset state
    import src.tools.rag as rag_module

    rag_module._intent_analyzer = None

    result = get_intent_analyzer()

    assert result == mock_ia
    mock_ia_class.assert_called_once()


@patch("src.tools.rag.IntentAnalyzer")
def test_get_intent_analyzer_cached(mock_ia_class):
    """Test subsequent calls return cached instance."""
    mock_ia = MagicMock()
    mock_ia_class.return_value = mock_ia

    import src.tools.rag as rag_module

    rag_module._intent_analyzer = None

    result1 = get_intent_analyzer()
    result2 = get_intent_analyzer()

    assert result1 == result2
    # Should only initialize once
    mock_ia_class.assert_called_once()


# ============================================================================
# retrieve_relevant_documents_tool Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.tools.rag.get_hybrid_search")
async def test_retrieve_documents_success(mock_get_hs, mock_search_result):
    """Test successful document retrieval."""
    mock_hs = AsyncMock()
    mock_hs.search.return_value = mock_search_result
    mock_get_hs.return_value = mock_hs

    result = await retrieve_relevant_documents_tool(
        supabase=None, embedding_client=None, user_query="test query", limit=10
    )

    assert "Test Document 1" in result
    assert "Test Document 2" in result
    assert "test_source_1.txt" in result
    assert "COMPREHENSIVE" in result  # search strategy
    mock_hs.search.assert_called_once_with(query="test query", limit=10, strategy=None)


@pytest.mark.asyncio
@patch("src.tools.rag.get_hybrid_search")
async def test_retrieve_documents_with_strategy(mock_get_hs, mock_search_result):
    """Test document retrieval with explicit strategy."""
    mock_hs = AsyncMock()
    mock_hs.search.return_value = mock_search_result
    mock_get_hs.return_value = mock_hs

    await retrieve_relevant_documents_tool(
        supabase=None,
        embedding_client=None,
        user_query="test query",
        strategy=SearchStrategy.VECTOR_HEAVY,
        limit=5,
    )

    mock_hs.search.assert_called_once_with(
        query="test query", limit=5, strategy=SearchStrategy.VECTOR_HEAVY
    )


@pytest.mark.asyncio
@patch("src.tools.rag.get_hybrid_search")
async def test_retrieve_documents_no_results(mock_get_hs):
    """Test document retrieval with no results."""
    empty_result = MagicMock()
    empty_result.chunks = []
    empty_result.entities = []
    empty_result.facts = []
    empty_result.search_strategy = SearchStrategy.VECTOR_HEAVY
    empty_result.query_time = 0.05

    mock_hs = AsyncMock()
    mock_hs.search.return_value = empty_result
    mock_get_hs.return_value = mock_hs

    result = await retrieve_relevant_documents_tool(
        supabase=None, embedding_client=None, user_query="nonexistent query"
    )

    assert result == "No relevant documents found."


@pytest.mark.asyncio
@patch("src.tools.rag.get_hybrid_search")
async def test_retrieve_documents_error_handling(mock_get_hs):
    """Test error handling in document retrieval."""
    mock_hs = AsyncMock()
    mock_hs.search.side_effect = Exception("Database connection failed")
    mock_get_hs.return_value = mock_hs

    result = await retrieve_relevant_documents_tool(
        supabase=None, embedding_client=None, user_query="test query"
    )

    assert "Error retrieving documents" in result
    assert "Database connection failed" in result


# ============================================================================
# smart_search_tool Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.tools.rag.get_hybrid_search")
@patch("src.tools.rag.get_intent_analyzer")
async def test_smart_search_with_intent_analysis(mock_get_ia, mock_get_hs, mock_search_result):
    """Test smart search with intent analysis enabled."""
    # Mock intent analyzer
    mock_ia = MagicMock()
    mock_intent_result = MagicMock()
    mock_intent_result.primary_intent = SearchStrategy.COMPREHENSIVE
    mock_ia.analyze.return_value = mock_intent_result
    mock_get_ia.return_value = mock_ia

    # Mock hybrid search
    mock_hs = AsyncMock()
    mock_hs.search.return_value = mock_search_result
    mock_get_hs.return_value = mock_hs

    result = await smart_search_tool("test query", analyze_intent=True, limit=10)

    assert result["query"] == "test query"
    assert result["intent"] == "COMPREHENSIVE"
    assert result["strategy_used"] == "COMPREHENSIVE"
    assert len(result["chunks"]) == 2
    assert len(result["entities"]) == 2
    assert len(result["facts"]) == 2
    assert result["total_results"] == 2
    assert result["query_time_ms"] > 0

    # Verify intent analysis was called
    mock_ia.analyze.assert_called_once_with("test query")


@pytest.mark.asyncio
@patch("src.tools.rag.get_hybrid_search")
async def test_smart_search_without_intent_analysis(mock_get_hs, mock_search_result):
    """Test smart search with intent analysis disabled."""
    mock_hs = AsyncMock()
    mock_hs.search.return_value = mock_search_result
    mock_get_hs.return_value = mock_hs

    result = await smart_search_tool("test query", analyze_intent=False, limit=10)

    assert result["query"] == "test query"
    assert result["intent"] is None  # No intent analysis
    assert len(result["chunks"]) == 2


@pytest.mark.asyncio
@patch("src.tools.rag.get_hybrid_search")
async def test_smart_search_chunks_limit(mock_get_hs, mock_search_result):
    """Test that smart search respects limit parameter."""
    # Create result with many chunks
    mock_chunks = []
    for i in range(20):

        class MockChunk:
            def __init__(self, i):
                self.chunk_id = uuid4()
                self.content = f"Content {i}"
                self.document_id = uuid4()
                self.document_title = f"Doc {i}"
                self.document_source = f"source_{i}.txt"
                self.similarity = 0.9 - (i * 0.01)
                self.entities = []

        mock_chunks.append(MockChunk(i))

    mock_search_result.chunks = mock_chunks

    mock_hs = AsyncMock()
    mock_hs.search.return_value = mock_search_result
    mock_get_hs.return_value = mock_hs

    result = await smart_search_tool("test query", analyze_intent=False, limit=5)

    # Should only return 5 chunks even though result has 20
    assert len(result["chunks"]) == 5


@pytest.mark.asyncio
@patch("src.tools.rag.get_hybrid_search")
async def test_smart_search_entities_limit(mock_get_hs, mock_search_result):
    """Test that entities are limited to 10."""

    class MockEntity:
        def __init__(self, i):
            self.name = f"Entity{i}"
            self.type = "test"

    # Create 20 entities
    mock_search_result.entities = [MockEntity(i) for i in range(20)]

    mock_hs = AsyncMock()
    mock_hs.search.return_value = mock_search_result
    mock_get_hs.return_value = mock_hs

    result = await smart_search_tool("test query", analyze_intent=False)

    # Should only return 10 entities
    assert len(result["entities"]) == 10


@pytest.mark.asyncio
@patch("src.tools.rag.get_hybrid_search")
async def test_smart_search_facts_limit(mock_get_hs, mock_search_result):
    """Test that facts are limited to 10."""

    class MockFact:
        def __init__(self, i):
            self.description = f"Fact {i}"

    # Create 20 facts
    mock_search_result.facts = [MockFact(i) for i in range(20)]

    mock_hs = AsyncMock()
    mock_hs.search.return_value = mock_search_result
    mock_get_hs.return_value = mock_hs

    result = await smart_search_tool("test query", analyze_intent=False)

    # Should only return 10 facts
    assert len(result["facts"]) == 10


@pytest.mark.asyncio
@patch("src.tools.rag.get_hybrid_search")
async def test_smart_search_error_handling(mock_get_hs):
    """Test error handling in smart search."""
    mock_hs = AsyncMock()
    mock_hs.search.side_effect = Exception("Search failed")
    mock_get_hs.return_value = mock_hs

    result = await smart_search_tool("test query")

    assert result["query"] == "test query"
    assert "error" in result
    assert "Search failed" in result["error"]
    assert result["chunks"] == []
    assert result["entities"] == []
    assert result["facts"] == []


@pytest.mark.asyncio
@patch("src.tools.rag.get_hybrid_search")
async def test_smart_search_no_entities_or_facts(mock_get_hs):
    """Test smart search when result has no entities or facts."""
    mock_result = MagicMock()

    class MockChunk:
        chunk_id = uuid4()
        content = "Content"
        document_id = uuid4()
        document_title = "Title"
        document_source = "source.txt"
        similarity = 0.9
        entities = []

    mock_result.chunks = [MockChunk()]
    mock_result.entities = None  # No entities
    mock_result.facts = None  # No facts
    mock_result.relationships = None
    mock_result.search_strategy = SearchStrategy.VECTOR_HEAVY
    mock_result.query_time = 0.1

    mock_hs = AsyncMock()
    mock_hs.search.return_value = mock_result
    mock_get_hs.return_value = mock_hs

    result = await smart_search_tool("test query", analyze_intent=False)

    assert result["entities"] == []
    assert result["facts"] == []


# ============================================================================
# graph_query_tool Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.tools.rag.get_config")
@patch("src.tools.rag.get_hybrid_search")
async def test_graph_query_success(mock_get_hs, mock_get_config, mock_search_result):
    """Test successful graph query."""
    # Mock config with graph enabled
    mock_config = MagicMock()
    mock_config.performance.enable_graph = True
    mock_get_config.return_value = mock_config

    mock_hs = AsyncMock()
    mock_hs.search.return_value = mock_search_result
    mock_get_hs.return_value = mock_hs

    result = await graph_query_tool(entity_name="TestEntity", query_type="entity_facts")

    assert result["query_type"] == "entity_facts"
    assert result["entity"] == "TestEntity"
    assert len(result["facts"]) == 2
    assert len(result["entities"]) == 2
    assert "relationships" in result

    # Verify GRAPH_ONLY strategy was used
    mock_hs.search.assert_called_once_with(
        query="TestEntity", limit=10, strategy=SearchStrategy.GRAPH_ONLY
    )


@pytest.mark.asyncio
@patch("src.tools.rag.get_config")
async def test_graph_query_disabled(mock_get_config):
    """Test graph query when graph is disabled."""
    mock_config = MagicMock()
    mock_config.performance.enable_graph = False
    mock_get_config.return_value = mock_config

    result = await graph_query_tool(entity_name="TestEntity")

    assert "error" in result
    assert "not enabled" in result["error"]
    assert "ENABLE_GRAPH=true" in result["error"]


@pytest.mark.asyncio
@patch("src.tools.rag.get_config")
@patch("src.tools.rag.get_hybrid_search")
async def test_graph_query_no_entity_name(mock_get_hs, mock_get_config, mock_search_result):
    """Test graph query with no entity name (empty query)."""
    mock_config = MagicMock()
    mock_config.performance.enable_graph = True
    mock_get_config.return_value = mock_config

    mock_hs = AsyncMock()
    mock_hs.search.return_value = mock_search_result
    mock_get_hs.return_value = mock_hs

    result = await graph_query_tool(entity_name=None, query_type="temporal_facts")

    assert result["entity"] is None
    # Should search with empty string
    mock_hs.search.assert_called_once_with(query="", limit=10, strategy=SearchStrategy.GRAPH_ONLY)


@pytest.mark.asyncio
@patch("src.tools.rag.get_config")
@patch("src.tools.rag.get_hybrid_search")
async def test_graph_query_with_relationships(mock_get_hs, mock_get_config):
    """Test graph query that returns relationships."""
    mock_config = MagicMock()
    mock_config.performance.enable_graph = True
    mock_get_config.return_value = mock_config

    class MockRelationship:
        def __init__(self, source, target, rel_type):
            self.source = source
            self.target = target
            self.type = rel_type

    mock_result = MagicMock()
    mock_result.facts = []
    mock_result.entities = []
    mock_result.relationships = [
        MockRelationship("Entity1", "Entity2", "related_to"),
        MockRelationship("Entity2", "Entity3", "connected_to"),
    ]

    mock_hs = AsyncMock()
    mock_hs.search.return_value = mock_result
    mock_get_hs.return_value = mock_hs

    result = await graph_query_tool(entity_name="TestEntity", query_type="entity_relationships")

    assert len(result["relationships"]) == 2
    assert result["relationships"][0]["source"] == "Entity1"
    assert result["relationships"][0]["target"] == "Entity2"
    assert result["relationships"][0]["type"] == "related_to"


@pytest.mark.asyncio
@patch("src.tools.rag.get_config")
@patch("src.tools.rag.get_hybrid_search")
async def test_graph_query_error_handling(mock_get_hs, mock_get_config):
    """Test error handling in graph query."""
    mock_config = MagicMock()
    mock_config.performance.enable_graph = True
    mock_get_config.return_value = mock_config

    mock_hs = AsyncMock()
    mock_hs.search.side_effect = Exception("Graph connection failed")
    mock_get_hs.return_value = mock_hs

    result = await graph_query_tool(entity_name="TestEntity")

    assert "error" in result
    assert "Graph connection failed" in result["error"]
    assert result["entity"] == "TestEntity"


# ============================================================================
# list_documents_tool Tests
# ============================================================================


@pytest.mark.asyncio
async def test_list_documents_success(mock_supabase):
    """Test successful document listing."""
    mock_result = MagicMock()
    mock_result.data = [
        {
            "id": str(uuid4()),
            "title": "Document 1",
            "source": "doc1.txt",
            "created_at": "2025-01-01",
        },
        {
            "id": str(uuid4()),
            "title": "Document 2",
            "source": "doc2.pdf",
            "created_at": "2025-01-02",
        },
    ]

    mock_chain = MagicMock()
    mock_chain.select.return_value.execute.return_value = mock_result
    mock_supabase.from_.return_value = mock_chain

    result = await list_documents_tool(mock_supabase)

    assert len(result) == 2
    assert "Document 1" in result[0]
    assert "doc1.txt" in result[0]
    assert "Document 2" in result[1]
    assert "doc2.pdf" in result[1]


@pytest.mark.asyncio
async def test_list_documents_empty(mock_supabase):
    """Test listing when no documents exist."""
    mock_result = MagicMock()
    mock_result.data = []

    mock_chain = MagicMock()
    mock_chain.select.return_value.execute.return_value = mock_result
    mock_supabase.from_.return_value = mock_chain

    result = await list_documents_tool(mock_supabase)

    assert result == []


@pytest.mark.asyncio
async def test_list_documents_missing_fields(mock_supabase):
    """Test listing with documents missing optional fields."""
    mock_result = MagicMock()
    mock_result.data = [
        {
            "id": str(uuid4()),
            # Missing title, source, created_at
        }
    ]

    mock_chain = MagicMock()
    mock_chain.select.return_value.execute.return_value = mock_result
    mock_supabase.from_.return_value = mock_chain

    result = await list_documents_tool(mock_supabase)

    assert len(result) == 1
    assert "Untitled" in result[0]
    assert "N/A" in result[0]


@pytest.mark.asyncio
async def test_list_documents_error_handling(mock_supabase):
    """Test error handling in document listing."""
    mock_supabase.from_.side_effect = Exception("Database error")

    result = await list_documents_tool(mock_supabase)

    assert result == []


# ============================================================================
# get_document_content_tool Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_document_by_uuid(mock_supabase):
    """Test retrieving document by UUID."""
    doc_id = uuid4()
    mock_result = MagicMock()
    mock_result.data = [
        {
            "id": str(doc_id),
            "title": "Test Document",
            "content": "This is test content.",
            "source": "test.txt",
        }
    ]

    mock_chain = MagicMock()
    mock_chain.select.return_value.eq.return_value.execute.return_value = mock_result
    mock_supabase.from_.return_value = mock_chain

    result = await get_document_content_tool(mock_supabase, str(doc_id))

    assert "Test Document" in result
    assert "This is test content." in result
    assert "test.txt" in result
    assert str(doc_id) in result


@pytest.mark.asyncio
async def test_get_document_by_title_search(mock_supabase):
    """Test retrieving document by title search (non-UUID)."""
    mock_result = MagicMock()
    mock_result.data = [
        {
            "id": str(uuid4()),
            "title": "Matching Document",
            "content": "Content here",
            "source": "match.txt",
        }
    ]

    mock_chain = MagicMock()
    mock_chain.select.return_value.or_.return_value.limit.return_value.execute.return_value = (
        mock_result
    )
    mock_supabase.from_.return_value = mock_chain

    result = await get_document_content_tool(mock_supabase, "matching")

    assert "Matching Document" in result
    assert "Content here" in result


@pytest.mark.asyncio
async def test_get_document_not_found(mock_supabase):
    """Test retrieving non-existent document."""
    mock_result = MagicMock()
    mock_result.data = []

    mock_chain = MagicMock()
    mock_chain.select.return_value.eq.return_value.execute.return_value = mock_result
    mock_supabase.from_.return_value = mock_chain

    result = await get_document_content_tool(mock_supabase, str(uuid4()))

    assert "No document found" in result


@pytest.mark.asyncio
async def test_get_document_content_truncation(mock_supabase):
    """Test that content is truncated to 20000 characters."""
    long_content = "x" * 25000
    mock_result = MagicMock()
    mock_result.data = [
        {
            "id": str(uuid4()),
            "title": "Long Document",
            "content": long_content,
            "source": "long.txt",
        }
    ]

    mock_chain = MagicMock()
    mock_chain.select.return_value.eq.return_value.execute.return_value = mock_result
    mock_supabase.from_.return_value = mock_chain

    result = await get_document_content_tool(mock_supabase, str(uuid4()))

    # Content should be truncated
    assert len(result) < len(long_content) + 500  # +500 for formatting


@pytest.mark.asyncio
async def test_get_document_missing_fields(mock_supabase):
    """Test retrieving document with missing optional fields."""
    mock_result = MagicMock()
    mock_result.data = [
        {
            "id": str(uuid4()),
            # Missing title, content, source
        }
    ]

    mock_chain = MagicMock()
    mock_chain.select.return_value.eq.return_value.execute.return_value = mock_result
    mock_supabase.from_.return_value = mock_chain

    result = await get_document_content_tool(mock_supabase, str(uuid4()))

    assert "Untitled" in result
    assert "N/A" in result
    assert "No content available" in result


@pytest.mark.asyncio
async def test_get_document_error_handling(mock_supabase):
    """Test error handling in document retrieval."""
    mock_supabase.from_.side_effect = Exception("Connection timeout")

    result = await get_document_content_tool(mock_supabase, str(uuid4()))

    assert "Error retrieving document" in result
    assert "Connection timeout" in result


# ============================================================================
# _format_search_results Tests
# ============================================================================


def test_format_search_results_with_chunks(mock_search_result):
    """Test formatting results with chunks."""
    result = _format_search_results(mock_search_result)

    assert "Test Document 1" in result
    assert "Test Document 2" in result
    assert "test_source_1.txt" in result
    assert "0.95" in result  # similarity score
    assert "Entity1, Entity2" in result
    assert "COMPREHENSIVE" in result


def test_format_search_results_no_chunks():
    """Test formatting with no results."""
    empty_result = MagicMock()
    empty_result.chunks = []

    result = _format_search_results(empty_result)

    assert result == "No relevant documents found."


def test_format_search_results_with_entities(mock_search_result):
    """Test that entities are included in formatted output."""
    result = _format_search_results(mock_search_result)

    assert "Related Entities:" in result
    assert "Entity1" in result
    assert "Entity2" in result


def test_format_search_results_no_entities():
    """Test formatting when result has no entities."""
    result = MagicMock()

    class MockChunk:
        chunk_id = uuid4()
        content = "Content"
        document_id = uuid4()
        document_title = "Title"
        document_source = "source.txt"
        similarity = 0.9
        entities = []

    result.chunks = [MockChunk()]
    result.entities = []
    result.search_strategy = SearchStrategy.VECTOR_HEAVY
    result.query_time = 0.1

    formatted = _format_search_results(result)

    assert "Related Entities:" not in formatted
    assert "Title" in formatted


def test_format_search_results_metadata_footer(mock_search_result):
    """Test that metadata footer is included."""
    result = _format_search_results(mock_search_result)

    assert "Search Strategy:" in result
    assert "Query Time:" in result
    assert "Total Results:" in result
    assert "125ms" in result  # 0.125 * 1000


# ============================================================================
# cleanup_rag_tools Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.tools.rag._connection_manager")
async def test_cleanup_rag_tools(mock_cm):
    """Test cleanup function closes connections."""
    mock_cm_instance = AsyncMock()
    mock_cm_instance.close = AsyncMock()

    # Set module state
    import src.tools.rag as rag_module

    rag_module._connection_manager = mock_cm_instance
    rag_module._hybrid_search = MagicMock()
    rag_module._intent_analyzer = MagicMock()

    await cleanup_rag_tools()

    # Verify cleanup happened
    mock_cm_instance.close.assert_called_once()
    assert rag_module._connection_manager is None
    assert rag_module._hybrid_search is None
    assert rag_module._intent_analyzer is None


@pytest.mark.asyncio
async def test_cleanup_rag_tools_no_manager():
    """Test cleanup when no connection manager exists."""
    import src.tools.rag as rag_module

    rag_module._connection_manager = None

    # Should not raise error
    await cleanup_rag_tools()


# ============================================================================
# Edge Cases and Integration Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.tools.rag.get_hybrid_search")
async def test_retrieve_documents_empty_query(mock_get_hs, mock_search_result):
    """Test retrieving documents with empty query."""
    mock_hs = AsyncMock()
    mock_hs.search.return_value = mock_search_result
    mock_get_hs.return_value = mock_hs

    result = await retrieve_relevant_documents_tool(
        supabase=None, embedding_client=None, user_query=""
    )

    # Should handle gracefully
    assert isinstance(result, str)
    mock_hs.search.assert_called_once()


@pytest.mark.asyncio
@patch("src.tools.rag.get_hybrid_search")
async def test_smart_search_unicode_query(mock_get_hs, mock_search_result):
    """Test smart search with Unicode characters."""
    mock_hs = AsyncMock()
    mock_hs.search.return_value = mock_search_result
    mock_get_hs.return_value = mock_hs

    result = await smart_search_tool("こんにちは 世界 🌍", analyze_intent=False)

    assert result["query"] == "こんにちは 世界 🌍"
    assert len(result["chunks"]) > 0


@pytest.mark.asyncio
async def test_list_documents_concurrent_calls(mock_supabase):
    """Test concurrent document listing calls."""
    mock_result = MagicMock()
    mock_result.data = [
        {"id": str(uuid4()), "title": "Doc", "source": "src", "created_at": "2025-01-01"}
    ]

    mock_chain = MagicMock()
    mock_chain.select.return_value.execute.return_value = mock_result
    mock_supabase.from_.return_value = mock_chain

    # Run multiple concurrent calls
    results = await asyncio.gather(
        list_documents_tool(mock_supabase),
        list_documents_tool(mock_supabase),
        list_documents_tool(mock_supabase),
    )

    assert len(results) == 3
    assert all(len(r) == 1 for r in results)


@pytest.mark.asyncio
@patch("src.tools.rag.get_hybrid_search")
async def test_large_result_set_handling(mock_get_hs):
    """Test handling of very large result sets."""

    # Create 1000 chunks
    class MockChunk:
        def __init__(self, i):
            self.chunk_id = uuid4()
            self.content = f"Content {i}" * 100
            self.document_id = uuid4()
            self.document_title = f"Doc {i}"
            self.document_source = f"src{i}.txt"
            self.similarity = 0.99 - (i * 0.0001)
            self.entities = [f"Entity{i}"]

    large_result = MagicMock()
    large_result.chunks = [MockChunk(i) for i in range(1000)]
    large_result.entities = []
    large_result.facts = []
    large_result.search_strategy = SearchStrategy.VECTOR_HEAVY
    large_result.query_time = 2.5

    mock_hs = AsyncMock()
    mock_hs.search.return_value = large_result
    mock_get_hs.return_value = mock_hs

    # Request limited results
    result = await smart_search_tool("test", analyze_intent=False, limit=10)

    # Should only return requested limit
    assert len(result["chunks"]) == 10
    assert result["total_results"] == 1000  # But report total
