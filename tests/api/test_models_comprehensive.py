"""
Comprehensive tests for src/api/models.py.

Tests all Pydantic models, validation, serialization, and edge cases.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError


class TestEnums:
    """Test enum types."""

    def test_search_type_values(self):
        """Test SearchType enum values."""
        from src.api.models import SearchType

        assert SearchType.VECTOR == "vector"
        assert SearchType.GRAPH == "graph"
        assert SearchType.HYBRID == "hybrid"
        assert SearchType.ADAPTIVE == "adaptive"

    def test_message_role_values(self):
        """Test MessageRole enum values."""
        from src.api.models import MessageRole

        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.SYSTEM == "system"


class TestChatMessage:
    """Test ChatMessage model."""

    def test_chat_message_basic(self):
        """Test basic chat message creation."""
        from src.api.models import ChatMessage, MessageRole

        msg = ChatMessage(role=MessageRole.USER, content="Hello")

        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.timestamp is None

    def test_chat_message_with_timestamp(self):
        """Test chat message with timestamp."""
        from src.api.models import ChatMessage, MessageRole

        now = datetime.now(UTC)
        msg = ChatMessage(role=MessageRole.ASSISTANT, content="Hi", timestamp=now)

        assert msg.timestamp == now

    def test_chat_message_json_serialization(self):
        """Test chat message JSON serialization."""
        from src.api.models import ChatMessage, MessageRole

        msg = ChatMessage(role=MessageRole.USER, content="Test")
        json_data = msg.model_dump()

        assert json_data["role"] == "user"
        assert json_data["content"] == "Test"


class TestChatRequest:
    """Test ChatRequest model."""

    def test_chat_request_minimal(self):
        """Test chat request with minimal fields."""
        from src.api.models import ChatRequest

        req = ChatRequest(message="Hello")

        assert req.message == "Hello"
        assert req.session_id is None
        assert req.stream is False
        assert req.include_sources is True

    def test_chat_request_full(self):
        """Test chat request with all fields."""
        from src.api.models import ChatMessage, ChatRequest, MessageRole, SearchType

        history = [ChatMessage(role=MessageRole.USER, content="Previous")]

        req = ChatRequest(
            message="Hello",
            session_id="session-123",
            stream=True,
            include_sources=False,
            search_strategy=SearchType.HYBRID,
            max_tokens=1000,
            temperature=0.7,
            history=history,
        )

        assert req.message == "Hello"
        assert req.session_id == "session-123"
        assert req.stream is True
        assert req.search_strategy == SearchType.HYBRID
        assert req.max_tokens == 1000
        assert req.temperature == 0.7
        assert len(req.history) == 1

    def test_chat_request_empty_message_validation(self):
        """Test empty message validation."""
        from src.api.models import ChatRequest

        with pytest.raises(ValidationError):
            ChatRequest(message="")

    def test_chat_request_max_tokens_validation(self):
        """Test max tokens validation."""
        from src.api.models import ChatRequest

        # Should raise for negative tokens
        with pytest.raises(ValidationError):
            ChatRequest(message="Test", max_tokens=0)

        # Should raise for too many tokens
        with pytest.raises(ValidationError):
            ChatRequest(message="Test", max_tokens=20000)

    def test_chat_request_temperature_validation(self):
        """Test temperature validation."""
        from src.api.models import ChatRequest

        # Valid temperatures
        req1 = ChatRequest(message="Test", temperature=0.0)
        assert req1.temperature == 0.0

        req2 = ChatRequest(message="Test", temperature=2.0)
        assert req2.temperature == 2.0

        # Invalid temperatures
        with pytest.raises(ValidationError):
            ChatRequest(message="Test", temperature=-0.1)

        with pytest.raises(ValidationError):
            ChatRequest(message="Test", temperature=2.1)


class TestSourceDocument:
    """Test SourceDocument model."""

    def test_source_document_basic(self):
        """Test source document creation."""
        from src.api.models import SourceDocument

        doc = SourceDocument(
            document_id="doc-123",
            content="Document content here",
            similarity_score=0.95,
        )

        assert doc.document_id == "doc-123"
        assert doc.content == "Document content here"
        assert doc.similarity_score == 0.95
        assert doc.metadata is None
        assert doc.chunk_index is None

    def test_source_document_with_metadata(self):
        """Test source document with metadata."""
        from src.api.models import SourceDocument

        metadata = {"title": "Test Doc", "author": "Test Author"}

        doc = SourceDocument(
            document_id="doc-123",
            content="Content",
            similarity_score=0.8,
            metadata=metadata,
            chunk_index=5,
        )

        assert doc.metadata == metadata
        assert doc.chunk_index == 5

    def test_source_document_similarity_validation(self):
        """Test similarity score validation."""
        from src.api.models import SourceDocument

        # Valid scores
        doc1 = SourceDocument(document_id="1", content="test", similarity_score=0.0)
        assert doc1.similarity_score == 0.0

        doc2 = SourceDocument(document_id="2", content="test", similarity_score=1.0)
        assert doc2.similarity_score == 1.0

        # Invalid scores
        with pytest.raises(ValidationError):
            SourceDocument(document_id="3", content="test", similarity_score=-0.1)

        with pytest.raises(ValidationError):
            SourceDocument(document_id="4", content="test", similarity_score=1.1)


class TestChatMetrics:
    """Test ChatMetrics model."""

    def test_chat_metrics_basic(self):
        """Test chat metrics creation."""
        from src.api.models import ChatMetrics

        metrics = ChatMetrics(response_time_ms=150.5)

        assert metrics.response_time_ms == 150.5
        assert metrics.tokens_used == 0
        assert metrics.cache_hit is False

    def test_chat_metrics_full(self):
        """Test chat metrics with all fields."""
        from src.api.models import ChatMetrics

        metrics = ChatMetrics(
            response_time_ms=250.3,
            search_time_ms=50.2,
            llm_time_ms=200.1,
            tokens_used=150,
            tokens_prompt=100,
            tokens_completion=50,
            cache_hit=True,
        )

        assert metrics.response_time_ms == 250.3
        assert metrics.search_time_ms == 50.2
        assert metrics.llm_time_ms == 200.1
        assert metrics.tokens_used == 150
        assert metrics.tokens_prompt == 100
        assert metrics.tokens_completion == 50
        assert metrics.cache_hit is True


class TestChatResponse:
    """Test ChatResponse model."""

    def test_chat_response_minimal(self):
        """Test chat response with minimal fields."""
        from src.api.models import ChatResponse

        resp = ChatResponse(
            response="AI response here",
            confidence=0.9,
            session_id="session-123",
        )

        assert resp.response == "AI response here"
        assert resp.confidence == 0.9
        assert resp.session_id == "session-123"
        assert resp.sources is None

    def test_chat_response_with_sources(self):
        """Test chat response with sources."""
        from src.api.models import ChatResponse, SourceDocument

        sources = [
            SourceDocument(document_id="1", content="Source 1", similarity_score=0.9),
            SourceDocument(document_id="2", content="Source 2", similarity_score=0.8),
        ]

        resp = ChatResponse(
            response="Response",
            confidence=0.85,
            session_id="session-123",
            sources=sources,
        )

        assert len(resp.sources) == 2
        assert resp.sources[0].document_id == "1"

    def test_chat_response_confidence_validation(self):
        """Test confidence score validation."""
        from src.api.models import ChatResponse

        # Valid confidence
        resp1 = ChatResponse(response="Test", confidence=0.0, session_id="123")
        assert resp1.confidence == 0.0

        resp2 = ChatResponse(response="Test", confidence=1.0, session_id="123")
        assert resp2.confidence == 1.0

        # Invalid confidence
        with pytest.raises(ValidationError):
            ChatResponse(response="Test", confidence=-0.1, session_id="123")

        with pytest.raises(ValidationError):
            ChatResponse(response="Test", confidence=1.1, session_id="123")


class TestSearchRequest:
    """Test SearchRequest model."""

    def test_search_request_defaults(self):
        """Test search request with defaults."""
        from src.api.models import SearchRequest, SearchType

        req = SearchRequest(query="test query")

        assert req.query == "test query"
        assert req.search_type == SearchType.HYBRID
        assert req.limit == 10
        assert req.threshold == 0.7
        assert req.include_metadata is True

    def test_search_request_custom_values(self):
        """Test search request with custom values."""
        from src.api.models import SearchRequest, SearchType

        req = SearchRequest(
            query="custom query",
            search_type=SearchType.VECTOR,
            limit=50,
            threshold=0.8,
            include_metadata=False,
            filters={"category": "science"},
        )

        assert req.search_type == SearchType.VECTOR
        assert req.limit == 50
        assert req.threshold == 0.8
        assert req.include_metadata is False
        assert req.filters == {"category": "science"}

    def test_search_request_limit_validation(self):
        """Test limit validation."""
        from src.api.models import SearchRequest

        # Valid limits
        req1 = SearchRequest(query="test", limit=1)
        assert req1.limit == 1

        req2 = SearchRequest(query="test", limit=100)
        assert req2.limit == 100

        # Invalid limits
        with pytest.raises(ValidationError):
            SearchRequest(query="test", limit=0)

        with pytest.raises(ValidationError):
            SearchRequest(query="test", limit=101)

    def test_search_request_threshold_validation(self):
        """Test threshold validation."""
        from src.api.models import SearchRequest

        # Valid thresholds
        req1 = SearchRequest(query="test", threshold=0.0)
        assert req1.threshold == 0.0

        req2 = SearchRequest(query="test", threshold=1.0)
        assert req2.threshold == 1.0

        # Invalid thresholds
        with pytest.raises(ValidationError):
            SearchRequest(query="test", threshold=-0.1)

        with pytest.raises(ValidationError):
            SearchRequest(query="test", threshold=1.1)


class TestSearchResult:
    """Test SearchResult model."""

    def test_search_result_basic(self):
        """Test search result creation."""
        from src.api.models import SearchResult

        result = SearchResult(
            id="result-1",
            content="Result content",
            score=0.95,
            document_id="doc-1",
        )

        assert result.id == "result-1"
        assert result.content == "Result content"
        assert result.score == 0.95
        assert result.document_id == "doc-1"
        assert result.metadata is None

    def test_search_result_with_metadata(self):
        """Test search result with metadata."""
        from src.api.models import SearchResult

        metadata = {"source": "test.pdf", "page": 5}

        result = SearchResult(
            id="result-1",
            content="Content",
            score=0.8,
            document_id="doc-1",
            metadata=metadata,
        )

        assert result.metadata == metadata

    def test_search_result_score_validation(self):
        """Test score validation."""
        from src.api.models import SearchResult

        # Valid scores
        r1 = SearchResult(id="1", content="test", score=0.0, document_id="doc")
        assert r1.score == 0.0

        r2 = SearchResult(id="2", content="test", score=1.0, document_id="doc")
        assert r2.score == 1.0

        # Invalid scores
        with pytest.raises(ValidationError):
            SearchResult(id="3", content="test", score=-0.1, document_id="doc")

        with pytest.raises(ValidationError):
            SearchResult(id="4", content="test", score=1.1, document_id="doc")


class TestGraphModels:
    """Test graph entity and relationship models."""

    def test_graph_entity_basic(self):
        """Test graph entity creation."""
        from src.api.models import GraphEntity

        entity = GraphEntity(
            id="entity-1",
            name="John Doe",
            type="person",
        )

        assert entity.id == "entity-1"
        assert entity.name == "John Doe"
        assert entity.type == "person"
        assert entity.properties is None

    def test_graph_entity_with_properties(self):
        """Test graph entity with properties."""
        from src.api.models import GraphEntity

        props = {"age": 30, "occupation": "Engineer"}

        entity = GraphEntity(
            id="entity-1",
            name="John Doe",
            type="person",
            properties=props,
        )

        assert entity.properties == props

    def test_graph_relationship_basic(self):
        """Test graph relationship creation."""
        from src.api.models import GraphRelationship

        rel = GraphRelationship(
            source="entity-1",
            target="entity-2",
            type="knows",
        )

        assert rel.source == "entity-1"
        assert rel.target == "entity-2"
        assert rel.type == "knows"
        assert rel.properties is None

    def test_graph_relationship_with_properties(self):
        """Test graph relationship with properties."""
        from src.api.models import GraphRelationship

        props = {"since": "2020", "strength": "strong"}

        rel = GraphRelationship(
            source="entity-1",
            target="entity-2",
            type="works_with",
            properties=props,
        )

        assert rel.properties == props


class TestSearchResponse:
    """Test SearchResponse model."""

    def test_search_response_basic(self):
        """Test search response creation."""
        from src.api.models import SearchResponse, SearchResult

        results = [
            SearchResult(id="1", content="Result 1", score=0.9, document_id="doc-1"),
            SearchResult(id="2", content="Result 2", score=0.8, document_id="doc-2"),
        ]

        resp = SearchResponse(
            results=results,
            total_results=2,
            search_time_ms=150.5,
            strategy_used="hybrid",
        )

        assert len(resp.results) == 2
        assert resp.total_results == 2
        assert resp.search_time_ms == 150.5
        assert resp.strategy_used == "hybrid"
        assert resp.entities is None
        assert resp.relationships is None

    def test_search_response_with_graph_data(self):
        """Test search response with graph entities and relationships."""
        from src.api.models import GraphEntity, GraphRelationship, SearchResponse

        entities = [GraphEntity(id="e1", name="Entity 1", type="person")]
        relationships = [GraphRelationship(source="e1", target="e2", type="knows")]

        resp = SearchResponse(
            results=[],
            total_results=0,
            search_time_ms=100.0,
            strategy_used="graph",
            entities=entities,
            relationships=relationships,
        )

        assert len(resp.entities) == 1
        assert len(resp.relationships) == 1


class TestDocumentModels:
    """Test document management models."""

    def test_ingest_request_minimal(self):
        """Test ingest request with minimal fields."""
        from src.api.models import IngestRequest

        req = IngestRequest(
            content="Document content",
            title="Test Document",
            source="test.pdf",
        )

        assert req.content == "Document content"
        assert req.title == "Test Document"
        assert req.source == "test.pdf"
        assert req.chunk_strategy == "semantic"
        assert req.extract_knowledge is True

    def test_ingest_request_full(self):
        """Test ingest request with all fields."""
        from src.api.models import IngestRequest

        metadata = {"author": "Test Author", "date": "2024-01-01"}

        req = IngestRequest(
            content="Content",
            title="Title",
            source="source.pdf",
            metadata=metadata,
            chunk_strategy="fixed",
            extract_knowledge=False,
        )

        assert req.metadata == metadata
        assert req.chunk_strategy == "fixed"
        assert req.extract_knowledge is False

    def test_ingest_response(self):
        """Test ingest response."""
        from src.api.models import IngestResponse

        resp = IngestResponse(
            document_id="doc-123",
            chunks_created=25,
            entities_extracted=10,
            relationships_extracted=5,
            processing_time_ms=5000.0,
            status="completed",
        )

        assert resp.document_id == "doc-123"
        assert resp.chunks_created == 25
        assert resp.entities_extracted == 10
        assert resp.relationships_extracted == 5
        assert resp.processing_time_ms == 5000.0
        assert resp.status == "completed"

    def test_document_metadata(self):
        """Test document metadata model."""
        from src.api.models import DocumentMetadata

        now = datetime.now(UTC)

        meta = DocumentMetadata(
            id="doc-1",
            title="Test Doc",
            source="test.pdf",
            created_at=now,
            chunk_count=10,
        )

        assert meta.id == "doc-1"
        assert meta.title == "Test Doc"
        assert meta.source == "test.pdf"
        assert meta.created_at == now
        assert meta.chunk_count == 10

    def test_document_list_response(self):
        """Test document list response."""
        from src.api.models import DocumentListResponse, DocumentMetadata

        now = datetime.now(UTC)

        docs = [
            DocumentMetadata(id="1", title="Doc 1", source="1.pdf", created_at=now, chunk_count=5),
            DocumentMetadata(id="2", title="Doc 2", source="2.pdf", created_at=now, chunk_count=3),
        ]

        resp = DocumentListResponse(
            documents=docs,
            total=100,
            page=1,
            page_size=10,
            has_more=True,
        )

        assert len(resp.documents) == 2
        assert resp.total == 100
        assert resp.page == 1
        assert resp.page_size == 10
        assert resp.has_more is True

    def test_document_content(self):
        """Test document content model."""
        from src.api.models import DocumentContent, DocumentMetadata

        now = datetime.now(UTC)

        metadata = DocumentMetadata(
            id="doc-1",
            title="Test",
            source="test.pdf",
            created_at=now,
            chunk_count=3,
        )

        chunks = ["Chunk 1", "Chunk 2", "Chunk 3"]

        content = DocumentContent(
            metadata=metadata,
            content="Full document content",
            chunks=chunks,
        )

        assert content.metadata.id == "doc-1"
        assert content.content == "Full document content"
        assert len(content.chunks) == 3


class TestStreamingModels:
    """Test streaming models."""

    def test_stream_event(self):
        """Test stream event model."""
        from src.api.models import StreamEvent

        event = StreamEvent(
            event="message",
            data={"content": "Hello"},
            id="event-1",
            retry=3000,
        )

        assert event.event == "message"
        assert event.data == {"content": "Hello"}
        assert event.id == "event-1"
        assert event.retry == 3000

    def test_stream_chunk(self):
        """Test stream chunk model."""
        from src.api.models import StreamChunk

        chunk = StreamChunk(
            content="Chunk content",
            done=False,
            metadata={"index": 0},
        )

        assert chunk.content == "Chunk content"
        assert chunk.done is False
        assert chunk.metadata == {"index": 0}

    def test_stream_chunk_final(self):
        """Test final stream chunk."""
        from src.api.models import StreamChunk

        chunk = StreamChunk(content="", done=True)

        assert chunk.content == ""
        assert chunk.done is True


class TestErrorModels:
    """Test error models."""

    def test_error_detail(self):
        """Test error detail model."""
        from src.api.models import ErrorDetail

        error = ErrorDetail(
            code="validation_error",
            message="Invalid input",
            details={"field": "email", "reason": "invalid format"},
        )

        assert error.code == "validation_error"
        assert error.message == "Invalid input"
        assert error.details == {"field": "email", "reason": "invalid format"}
        assert isinstance(error.timestamp, datetime)

    def test_error_response(self):
        """Test error response model."""
        from src.api.models import ErrorDetail, ErrorResponse

        error_detail = ErrorDetail(code="not_found", message="Resource not found")

        resp = ErrorResponse(
            error=error_detail,
            request_id="req-123",
        )

        assert resp.error.code == "not_found"
        assert resp.request_id == "req-123"


class TestStatusModels:
    """Test status and health models."""

    def test_cache_status(self):
        """Test cache status model."""
        from src.api.models import CacheStatus

        status = CacheStatus(
            enabled=True,
            healthy=True,
            type="redis",
            hit_rate=0.85,
        )

        assert status.enabled is True
        assert status.healthy is True
        assert status.type == "redis"
        assert status.hit_rate == 0.85

    def test_component_status(self):
        """Test component status model."""
        from src.api.models import ComponentStatus

        status = ComponentStatus(
            name="PostgreSQL",
            healthy=True,
            details={"response_time": 0.05},
        )

        assert status.name == "PostgreSQL"
        assert status.healthy is True
        assert status.details == {"response_time": 0.05}

    def test_status_response(self):
        """Test status response model."""
        from src.api.models import CacheStatus, ComponentStatus, StatusResponse

        cache = CacheStatus(enabled=True, healthy=True, type="redis")
        components = [
            ComponentStatus(name="Database", healthy=True),
            ComponentStatus(name="LLM", healthy=True),
        ]

        resp = StatusResponse(
            status="operational",
            version="1.0.0",
            cache=cache,
            components=components,
            metrics={"uptime": 3600},
        )

        assert resp.status == "operational"
        assert resp.version == "1.0.0"
        assert resp.cache.enabled is True
        assert len(resp.components) == 2
        assert resp.metrics == {"uptime": 3600}


class TestFeedbackModels:
    """Test feedback models."""

    def test_feedback_request_minimal(self):
        """Test feedback request with minimal fields."""
        from src.api.models import FeedbackRequest

        req = FeedbackRequest(
            message_id="msg-123",
            rating=5,
        )

        assert req.message_id == "msg-123"
        assert req.rating == 5
        assert req.feedback_text is None
        assert req.issues is None

    def test_feedback_request_full(self):
        """Test feedback request with all fields."""
        from src.api.models import FeedbackRequest

        req = FeedbackRequest(
            message_id="msg-123",
            rating=2,
            feedback_text="Response was inaccurate",
            issues=["incorrect", "slow"],
        )

        assert req.rating == 2
        assert req.feedback_text == "Response was inaccurate"
        assert req.issues == ["incorrect", "slow"]

    def test_feedback_request_rating_validation(self):
        """Test rating validation."""
        from src.api.models import FeedbackRequest

        # Valid ratings
        for rating in [1, 2, 3, 4, 5]:
            req = FeedbackRequest(message_id="msg", rating=rating)
            assert req.rating == rating

        # Invalid ratings
        with pytest.raises(ValidationError):
            FeedbackRequest(message_id="msg", rating=0)

        with pytest.raises(ValidationError):
            FeedbackRequest(message_id="msg", rating=6)

    def test_feedback_response(self):
        """Test feedback response model."""
        from src.api.models import FeedbackResponse

        resp = FeedbackResponse(
            success=True,
            feedback_id="feedback-123",
        )

        assert resp.success is True
        assert resp.feedback_id == "feedback-123"


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_chat_request_to_dict(self):
        """Test converting chat request to dict."""
        from src.api.models import ChatRequest

        req = ChatRequest(message="Test", max_tokens=1000)
        data = req.model_dump()

        assert isinstance(data, dict)
        assert data["message"] == "Test"
        assert data["max_tokens"] == 1000

    def test_search_response_to_json(self):
        """Test converting search response to JSON."""
        from src.api.models import SearchResponse

        resp = SearchResponse(
            results=[],
            total_results=0,
            search_time_ms=100.0,
            strategy_used="hybrid",
        )

        json_str = resp.model_dump_json()

        assert isinstance(json_str, str)
        assert "hybrid" in json_str

    def test_model_from_dict(self):
        """Test creating model from dict."""
        from src.api.models import ChatRequest

        data = {
            "message": "Test message",
            "session_id": "session-123",
            "stream": True,
        }

        req = ChatRequest(**data)

        assert req.message == "Test message"
        assert req.session_id == "session-123"
        assert req.stream is True


class TestModelDefaults:
    """Test model default values."""

    def test_chat_request_defaults(self):
        """Test chat request defaults."""
        from src.api.models import ChatRequest

        req = ChatRequest(message="Test")

        assert req.stream is False
        assert req.include_sources is True
        assert req.max_tokens == 2000

    def test_search_request_defaults(self):
        """Test search request defaults."""
        from src.api.models import SearchRequest, SearchType

        req = SearchRequest(query="test")

        assert req.search_type == SearchType.HYBRID
        assert req.limit == 10
        assert req.threshold == 0.7

    def test_ingest_request_defaults(self):
        """Test ingest request defaults."""
        from src.api.models import IngestRequest

        req = IngestRequest(
            content="Content",
            title="Title",
            source="source.pdf",
        )

        assert req.chunk_strategy == "semantic"
        assert req.extract_knowledge is True
