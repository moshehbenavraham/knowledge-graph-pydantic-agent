"""
API request and response models for Agentic RAG API.

Following 100-character line limit and Pydantic naming conventions.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SearchType(str, Enum):
    """Search strategy types."""

    VECTOR = "vector"
    GRAPH = "graph"
    HYBRID = "hybrid"
    ADAPTIVE = "adaptive"


class MessageRole(str, Enum):
    """Message role types."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# ===== Chat Models =====


class ChatMessage(BaseModel):
    """Individual chat message."""

    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: datetime | None = Field(None, description="Message timestamp")


class ChatRequest(BaseModel):
    """Chat request with configuration options."""

    message: str = Field(..., min_length=1, description="User message")
    session_id: str | None = Field(None, description="Session ID for context")
    stream: bool = Field(False, description="Enable streaming response")
    include_sources: bool = Field(True, description="Include source citations")
    search_strategy: SearchType | None = Field(None, description="Search strategy to use")
    max_tokens: int | None = Field(2000, ge=1, le=16000, description="Maximum response tokens")
    temperature: float | None = Field(None, ge=0.0, le=2.0, description="LLM temperature")
    history: list[ChatMessage] | None = Field(None, description="Previous conversation history")


class SourceDocument(BaseModel):
    """Source document reference with metadata."""

    document_id: str = Field(..., description="Document ID")
    content: str = Field(..., description="Relevant content excerpt")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity")
    metadata: dict[str, Any] | None = Field(None, description="Document metadata")
    chunk_index: int | None = Field(None, description="Chunk index in document")


class ChatMetrics(BaseModel):
    """Performance metrics for chat response."""

    response_time_ms: float = Field(..., description="Total response time")
    search_time_ms: float | None = Field(None, description="Search time")
    llm_time_ms: float | None = Field(None, description="LLM generation time")
    tokens_used: int = Field(0, description="Total tokens used")
    tokens_prompt: int = Field(0, description="Prompt tokens")
    tokens_completion: int = Field(0, description="Completion tokens")
    cache_hit: bool = Field(False, description="Whether response was cached")


class ChatResponse(BaseModel):
    """Chat response with sources and metadata."""

    response: str = Field(..., description="Agent response")
    sources: list[SourceDocument] | None = Field(None, description="Source documents")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Response confidence score")
    search_strategy_used: str | None = Field(None, description="Search strategy used")
    session_id: str = Field(..., description="Session ID")
    message_id: str | None = Field(None, description="Unique message ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Time")
    metrics: ChatMetrics | None = Field(None, description="Performance metrics")


# ===== Search Models =====


class SearchRequest(BaseModel):
    """Search request with filters and options."""

    query: str = Field(..., min_length=1, description="Search query")
    search_type: SearchType = Field(SearchType.HYBRID, description="Search type")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")
    threshold: float = Field(0.7, ge=0.0, le=1.0, description="Similarity threshold")
    include_metadata: bool = Field(True, description="Include document metadata")
    filters: dict[str, Any] | None = Field(None, description="Additional filters")


class SearchResult(BaseModel):
    """Individual search result."""

    id: str = Field(..., description="Result ID")
    content: str = Field(..., description="Content excerpt")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    document_id: str = Field(..., description="Source document ID")
    metadata: dict[str, Any] | None = Field(None, description="Result metadata")


class GraphEntity(BaseModel):
    """Knowledge graph entity."""

    id: str = Field(..., description="Entity ID")
    name: str = Field(..., description="Entity name")
    type: str = Field(..., description="Entity type")
    properties: dict[str, Any] | None = Field(None, description="Properties")


class GraphRelationship(BaseModel):
    """Knowledge graph relationship."""

    source: str = Field(..., description="Source entity ID")
    target: str = Field(..., description="Target entity ID")
    type: str = Field(..., description="Relationship type")
    properties: dict[str, Any] | None = Field(None, description="Properties")


class SearchResponse(BaseModel):
    """Search response with results and metadata."""

    results: list[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., ge=0, description="Total number of results")
    search_time_ms: float = Field(..., description="Search time in milliseconds")
    strategy_used: str = Field(..., description="Search strategy used")
    entities: list[GraphEntity] | None = Field(None, description="Related graph entities")
    relationships: list[GraphRelationship] | None = Field(None, description="Graph relationships")


# ===== Document Management Models =====


class IngestRequest(BaseModel):
    """Document ingestion request."""

    content: str = Field(..., min_length=1, description="Document content")
    title: str = Field(..., min_length=1, description="Document title")
    source: str = Field(..., description="Document source/origin")
    metadata: dict[str, Any] | None = Field(None, description="Custom metadata")
    chunk_strategy: str | None = Field("semantic", description="Chunking strategy")
    extract_knowledge: bool = Field(True, description="Extract entities and relationships")


class IngestResponse(BaseModel):
    """Document ingestion response."""

    document_id: str = Field(..., description="Created document ID")
    chunks_created: int = Field(..., ge=0, description="Number of chunks")
    entities_extracted: int = Field(0, ge=0, description="Number of entities")
    relationships_extracted: int = Field(0, ge=0, description="Number of relations")
    processing_time_ms: float = Field(..., description="Processing time")
    status: str = Field(..., description="Processing status")


class DocumentMetadata(BaseModel):
    """Document metadata summary."""

    id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    source: str = Field(..., description="Document source")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Update timestamp")
    chunk_count: int = Field(0, ge=0, description="Number of chunks")
    metadata: dict[str, Any] | None = Field(None, description="Custom metadata")


class DocumentListResponse(BaseModel):
    """List of documents with pagination."""

    documents: list[DocumentMetadata] = Field(..., description="Documents")
    total: int = Field(..., ge=0, description="Total document count")
    page: int = Field(..., ge=1, description="Current page")
    page_size: int = Field(..., ge=1, description="Page size")
    has_more: bool = Field(..., description="More pages available")


class DocumentContent(BaseModel):
    """Full document content with chunks."""

    metadata: DocumentMetadata = Field(..., description="Document metadata")
    content: str = Field(..., description="Full document content")
    chunks: list[str] | None = Field(None, description="Individual chunks")


# ===== Streaming Models =====


class StreamEvent(BaseModel):
    """Server-sent event for streaming."""

    event: str = Field(..., description="Event type")
    data: dict[str, Any] = Field(..., description="Event data")
    id: str | None = Field(None, description="Event ID")
    retry: int | None = Field(None, description="Retry timeout in ms")


class StreamChunk(BaseModel):
    """Streaming response chunk."""

    content: str = Field(..., description="Content chunk")
    done: bool = Field(False, description="Stream completed")
    metadata: dict[str, Any] | None = Field(None, description="Chunk metadata")


# ===== Error Models =====


class ErrorDetail(BaseModel):
    """Detailed error information."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: dict[str, Any] | None = Field(None, description="Additional details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Time")


class ErrorResponse(BaseModel):
    """Standardized error response."""

    error: ErrorDetail = Field(..., description="Error details")
    request_id: str | None = Field(None, description="Request correlation ID")


# ===== Status and Health Models =====


class CacheStatus(BaseModel):
    """Cache status information."""

    enabled: bool = Field(..., description="Cache enabled")
    healthy: bool = Field(..., description="Cache health")
    type: str = Field(..., description="Cache type (redis/memory)")
    hit_rate: float | None = Field(None, description="Cache hit rate")


class ComponentStatus(BaseModel):
    """Individual component status."""

    name: str = Field(..., description="Component name")
    healthy: bool = Field(..., description="Health status")
    details: dict[str, Any] | None = Field(None, description="Status details")


class StatusResponse(BaseModel):
    """API status and health information."""

    status: str = Field(..., description="Overall status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Time")
    cache: CacheStatus | None = Field(None, description="Cache status")
    components: list[ComponentStatus] = Field(
        default_factory=list, description="Component statuses"
    )
    metrics: dict[str, Any] | None = Field(None, description="Runtime metrics")


# ===== Feedback Models =====


class FeedbackRequest(BaseModel):
    """User feedback on response."""

    message_id: str = Field(..., description="Message ID being rated")
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    feedback_text: str | None = Field(None, description="Optional feedback text")
    issues: list[str] | None = Field(None, description="Issue categories")


class FeedbackResponse(BaseModel):
    """Feedback submission response."""

    success: bool = Field(..., description="Submission success")
    feedback_id: str = Field(..., description="Feedback record ID")
