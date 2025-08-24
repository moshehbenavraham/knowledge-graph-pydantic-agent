"""
Pydantic models for data validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MessageRole(str, Enum):
    """Message role enumeration."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class SearchType(str, Enum):
    """Search type enumeration."""

    VECTOR = "vector"
    HYBRID = "hybrid"
    GRAPH = "graph"


# Request Models
class ChatRequest(BaseModel):
    """Chat request model."""

    message: str = Field(..., description="User message")
    session_id: str | None = Field(None, description="Session ID for conversation continuity")
    user_id: str | None = Field(None, description="User identifier")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    search_type: SearchType = Field(
        default=SearchType.HYBRID, description="Type of search to perform"
    )

    model_config = ConfigDict(use_enum_values=True)


class SearchRequest(BaseModel):
    """Search request model."""

    query: str = Field(..., description="Search query")
    search_type: SearchType = Field(default=SearchType.HYBRID, description="Type of search")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results")
    filters: dict[str, Any] = Field(default_factory=dict, description="Search filters")

    model_config = ConfigDict(use_enum_values=True)


# Response Models
class DocumentMetadata(BaseModel):
    """Document metadata model."""

    id: str
    title: str
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    chunk_count: int | None = None


class ChunkResult(BaseModel):
    """Chunk search result model."""

    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)
    document_title: str
    document_source: str

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: float) -> float:
        """Ensure score is between 0 and 1."""
        return max(0.0, min(1.0, v))


class GraphSearchResult(BaseModel):
    """Knowledge graph search result model."""

    fact: str
    uuid: str
    valid_at: str | None = None
    invalid_at: str | None = None
    source_node_uuid: str | None = None


class EntityRelationship(BaseModel):
    """Entity relationship model."""

    from_entity: str
    to_entity: str
    relationship_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Search response model."""

    results: list[ChunkResult] = Field(default_factory=list)
    graph_results: list[GraphSearchResult] = Field(default_factory=list)
    total_results: int = 0
    search_type: SearchType
    query_time_ms: float


class ToolCall(BaseModel):
    """Tool call information model."""

    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    tool_call_id: str | None = None


class ChatResponse(BaseModel):
    """Chat response model."""

    message: str
    session_id: str
    sources: list[DocumentMetadata] = Field(default_factory=list)
    tools_used: list[ToolCall] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StreamDelta(BaseModel):
    """Streaming response delta."""

    content: str
    delta_type: Literal["text", "tool_call", "end"] = "text"
    metadata: dict[str, Any] = Field(default_factory=dict)


# Database Models
class Document(BaseModel):
    """Document model."""

    id: str | None = None
    title: str
    source: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Chunk(BaseModel):
    """Document chunk model."""

    id: str | None = None
    document_id: str
    content: str
    embedding: list[float] | None = None
    chunk_index: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    token_count: int | None = None
    created_at: datetime | None = None

    @field_validator("embedding")
    @classmethod
    def validate_embedding(cls, v: list[float] | None) -> list[float] | None:
        """Validate embedding dimensions."""
        if v is not None and len(v) != 1536:  # OpenAI text-embedding-3-small
            raise ValueError(f"Embedding must have 1536 dimensions, got {len(v)}")
        return v


class Session(BaseModel):
    """Session model."""

    id: str | None = None
    user_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    expires_at: datetime | None = None


class Message(BaseModel):
    """Message model."""

    id: str | None = None
    session_id: str
    role: MessageRole
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None

    model_config = ConfigDict(use_enum_values=True)


# Agent Models
class AgentDependencies(BaseModel):
    """Dependencies for the agent."""

    session_id: str
    database_url: str | None = None
    neo4j_uri: str | None = None
    openai_api_key: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class AgentContext(BaseModel):
    """Agent execution context."""

    session_id: str
    messages: list[Message] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    search_results: list[ChunkResult] = Field(default_factory=list)
    graph_results: list[GraphSearchResult] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# Ingestion Models
class IngestionConfig(BaseModel):
    """Configuration for document ingestion."""

    chunk_size: int = Field(default=1000, ge=100, le=5000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000)
    max_chunk_size: int = Field(default=2000, ge=500, le=10000)
    use_semantic_chunking: bool = True
    extract_entities: bool = True
    # New option for faster ingestion
    skip_graph_building: bool = Field(
        default=False, description="Skip knowledge graph building for faster ingestion"
    )

    @field_validator("chunk_overlap")
    @classmethod
    def validate_overlap(cls, v: int, info) -> int:
        """Ensure overlap is less than chunk size."""
        chunk_size = info.data.get("chunk_size", 1000)
        if v >= chunk_size:
            raise ValueError(f"Chunk overlap ({v}) must be less than chunk size ({chunk_size})")
        return v


class IngestionResult(BaseModel):
    """Result of document ingestion."""

    document_id: str
    title: str
    chunks_created: int
    entities_extracted: int
    relationships_created: int
    processing_time_ms: float
    errors: list[str] = Field(default_factory=list)


# Error Models
class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    error_type: str
    details: dict[str, Any] | None = None
    request_id: str | None = None


# Health Check Models
class HealthStatus(BaseModel):
    """Health check status."""

    status: Literal["healthy", "degraded", "unhealthy"]
    database: bool
    graph_database: bool
    llm_connection: bool
    version: str
    timestamp: datetime
