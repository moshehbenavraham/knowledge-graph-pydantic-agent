# API Endpoint Reference

Complete reference for all Agentic RAG API endpoints with examples.

---

## Table of Contents

- [Root Endpoints](#root-endpoints)
- [Chat Endpoints](#chat-endpoints)
- [Search Endpoints](#search-endpoints)
- [Document Endpoints](#document-endpoints)
- [Health Endpoints](#health-endpoints)
- [Analytics Endpoints](#analytics-endpoints)

---

## Root Endpoints

### GET /

Get API information and available endpoints.

**Response**:
```json
{
  "name": "Agentic RAG API",
  "version": "0.8.0",
  "status": "operational",
  "documentation": {
    "swagger": "/docs",
    "redoc": "/redoc",
    "openapi": "/api/v1/openapi.json"
  },
  "endpoints": {
    "health": "/health",
    "metrics": "/metrics",
    "status": "/api/v1/status",
    "chat": "/api/v1/chat",
    "search": "/api/v1/search",
    "documents": "/api/v1/documents",
    "analytics": "/api/v1/analytics"
  }
}
```

### GET /api/v1/status

Get comprehensive system status.

**Response**:
```json
{
  "status": "operational",
  "version": "0.8.0",
  "components": [
    {
      "name": "PostgreSQL",
      "healthy": true,
      "details": {}
    },
    {
      "name": "Neo4j",
      "healthy": true,
      "details": {}
    },
    {
      "name": "Cache",
      "healthy": true,
      "details": {}
    }
  ],
  "metrics": {
    "environment": "development",
    "features": {}
  }
}
```

### GET /metrics

Get Prometheus metrics in exposition format.

**Response**: Prometheus text format

### DELETE /api/v1/cache

Clear cache entries.

**Query Parameters**:
- `pattern` (string, default: "*"): Cache key pattern to clear

**Example**:
```bash
curl -X DELETE "http://localhost:8058/api/v1/cache?pattern=search:*"
```

**Response**:
```json
{
  "message": "All cache entries cleared"
}
```

---

## Chat Endpoints

### POST /api/v1/chat

Synchronous chat request.

**Request Body**:
```json
{
  "message": "What is machine learning?",
  "session_id": "session-123",
  "search_strategy": "adaptive",
  "include_sources": true,
  "max_tokens": 1000,
  "temperature": 0.7,
  "stream": false
}
```

**Fields**:
- `message` (string, required): User message
- `session_id` (string, optional): Session identifier for context
- `search_strategy` (string, default: "adaptive"): Search strategy
- `include_sources` (boolean, default: false): Include source documents
- `max_tokens` (integer, optional): Maximum response tokens
- `temperature` (float, optional): LLM temperature (0.0-1.0)
- `stream` (boolean, default: false): Enable streaming (use /stream endpoint)

**Response**:
```json
{
  "response": "Machine learning is a subset of artificial intelligence...",
  "sources": [
    {
      "document_id": "doc-123",
      "content": "Machine learning algorithms...",
      "similarity_score": 0.89,
      "metadata": {"source": "ai_guide.pdf"},
      "chunk_index": 5
    }
  ],
  "confidence": 0.85,
  "search_strategy_used": "adaptive",
  "session_id": "session-123",
  "message_id": "msg-456",
  "metrics": {
    "response_time_ms": 1250.5,
    "search_time_ms": 150.2,
    "llm_time_ms": 980.3,
    "tokens_used": 512,
    "tokens_prompt": 256,
    "tokens_completion": 256,
    "cache_hit": false
  }
}
```

**Example**:
```bash
curl -X POST "http://localhost:8058/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is machine learning?",
    "include_sources": true
  }'
```

### POST /api/v1/chat/stream

SSE streaming chat response.

**Request Body**: Same as POST /api/v1/chat

**Response**: Server-Sent Events stream

**Event Types**:
- `text`: Text chunk
- `tool_call`: Tool execution started
- `tool_return`: Tool execution completed
- `done`: Stream completed
- `error`: Error occurred

**Example**:
```bash
curl -N -X POST "http://localhost:8058/api/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain AI"}'
```

**Stream Output**:
```
event: text
data: {"content": "Artificial "}

event: text
data: {"content": "intelligence "}

event: tool_call
data: {"tool_name": "smart_search", "tool_id": "call_123"}

event: tool_return
data: {"tool_id": "call_123", "result": {...}}

event: done
data: {"message_id": "msg-789"}
```

### WebSocket /api/v1/chat/ws

Bidirectional WebSocket chat.

**Connect**:
```javascript
const ws = new WebSocket('ws://localhost:8058/api/v1/chat/ws');
```

**Send Message**:
```json
{
  "type": "chat",
  "message": "Hello, how are you?"
}
```

**Receive Response**:
```json
{
  "type": "text",
  "content": "I'm doing well!"
}
```

**Ping/Pong**:
```json
{"type": "ping"}
// Response: {"type": "pong"}
```

### POST /api/v1/chat/feedback

Submit feedback on chat response.

**Request Body**:
```json
{
  "message_id": "msg-456",
  "rating": 5,
  "issues": ["missing_context"],
  "comment": "Could have been more detailed"
}
```

**Fields**:
- `message_id` (string, required): Message to rate
- `rating` (integer, 1-5): Quality rating
- `issues` (array, optional): Issue categories
- `comment` (string, optional): Free-text feedback

**Response**:
```json
{
  "success": true,
  "feedback_id": "feedback-789"
}
```

### GET /api/v1/chat/sessions/{session_id}/history

Get chat history for session.

**Path Parameters**:
- `session_id` (string): Session identifier

**Query Parameters**:
- `limit` (integer, default: 50): Maximum messages

**Response**:
```json
{
  "session_id": "session-123",
  "messages": [],
  "total_messages": 0
}
```

---

## Search Endpoints

### POST /api/v1/search

Unified search endpoint.

**Request Body**:
```json
{
  "query": "machine learning applications",
  "search_type": "hybrid",
  "limit": 10,
  "threshold": 0.5,
  "filters": {
    "source": "research_papers"
  }
}
```

**Fields**:
- `query` (string, required): Search query
- `search_type` (string, default: "adaptive"): "vector", "hybrid", or "adaptive"
- `limit` (integer, default: 10): Maximum results
- `threshold` (float, default: 0.5): Minimum similarity score
- `filters` (object, optional): Metadata filters

**Response**:
```json
{
  "results": [
    {
      "id": "chunk-123",
      "content": "Machine learning has many applications...",
      "score": 0.92,
      "document_id": "doc-456",
      "metadata": {"source": "ml_guide.pdf"}
    }
  ],
  "total_results": 1,
  "search_time_ms": 125.5,
  "strategy_used": "hybrid",
  "entities": [
    {
      "id": "entity-789",
      "name": "Machine Learning",
      "type": "concept",
      "properties": {}
    }
  ],
  "relationships": [
    {
      "source": "Machine Learning",
      "target": "Artificial Intelligence",
      "type": "SUBSET_OF",
      "properties": {}
    }
  ]
}
```

**Example**:
```bash
curl -X POST "http://localhost:8058/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning",
    "search_type": "hybrid",
    "limit": 5
  }'
```

### GET /api/v1/search/suggest

Get query suggestions.

**Query Parameters**:
- `query` (string, required, min: 2): Query prefix
- `limit` (integer, default: 5, max: 20): Maximum suggestions

**Response**:
```json
{
  "query": "mach",
  "suggestions": [
    "machine learning",
    "machine learning applications",
    "machine translation"
  ]
}
```

### GET /api/v1/search/entities/{entity_name}

Get entity information from knowledge graph.

**Path Parameters**:
- `entity_name` (string): Entity name to lookup

**Response**:
```json
{
  "name": "OpenAI",
  "type": "organization",
  "properties": {
    "founded": "2015",
    "headquarters": "San Francisco"
  },
  "relationships": [
    {
      "target": "Microsoft",
      "type": "PARTNERED_WITH",
      "properties": {}
    }
  ]
}
```

### GET /api/v1/search/relationships

Find relationships between entities.

**Query Parameters**:
- `entity1` (string, required): First entity name
- `entity2` (string, required): Second entity name
- `max_depth` (integer, default: 3, max: 5): Maximum path depth

**Response**:
```json
{
  "entity1": "OpenAI",
  "entity2": "Microsoft",
  "relationships": [
    {
      "path": ["OpenAI", "PARTNERED_WITH", "Microsoft"],
      "strength": 0.95
    }
  ],
  "shortest_path_length": 1
}
```

---

## Document Endpoints

### POST /api/v1/documents

Ingest a new document.

**Request Body**:
```json
{
  "content": "Document content here...",
  "title": "Machine Learning Guide",
  "source": "ml_guide.pdf",
  "metadata": {
    "author": "John Doe",
    "category": "AI"
  }
}
```

**Response** (201 Created):
```json
{
  "document_id": "doc-123",
  "chunks_created": 15,
  "entities_extracted": 8,
  "relationships_extracted": 12,
  "processing_time_ms": 5250.5,
  "status": "completed"
}
```

**Example**:
```bash
curl -X POST "http://localhost:8058/api/v1/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "This is a test document about AI.",
    "title": "AI Overview",
    "source": "manual_input"
  }'
```

### GET /api/v1/documents

List documents with pagination.

**Query Parameters**:
- `page` (integer, default: 1): Page number
- `page_size` (integer, default: 20, max: 100): Items per page
- `source_filter` (string, optional): Filter by source

**Response**:
```json
{
  "documents": [
    {
      "id": "doc-123",
      "title": "Machine Learning Guide",
      "source": "ml_guide.pdf",
      "created_at": "2025-12-30T10:00:00Z",
      "updated_at": null,
      "chunk_count": 15,
      "metadata": {"author": "John Doe"}
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "has_more": false
}
```

### GET /api/v1/documents/{document_id}

Get document content.

**Path Parameters**:
- `document_id` (string): Document UUID

**Query Parameters**:
- `include_chunks` (boolean, default: false): Include chunk breakdown

**Response**:
```json
{
  "metadata": {
    "id": "doc-123",
    "title": "Machine Learning Guide",
    "source": "ml_guide.pdf",
    "created_at": "2025-12-30T10:00:00Z",
    "chunk_count": 15
  },
  "content": "Full document content...",
  "chunks": ["Chunk 1 content...", "Chunk 2 content..."]
}
```

### DELETE /api/v1/documents/{document_id}

Delete document and associated data.

**Response**:
```json
{
  "status": "deleted",
  "document_id": "doc-123"
}
```

### PATCH /api/v1/documents/{document_id}

Update document metadata.

**Query Parameters**:
- `title` (string, optional): New title
- `metadata` (object, optional): Updated metadata

**Response**:
```json
{
  "status": "updated",
  "document_id": "doc-123",
  "updates": {
    "title": "Updated Title"
  }
}
```

### POST /api/v1/documents/{document_id}/reindex

Regenerate embeddings and knowledge extraction.

**Response**:
```json
{
  "status": "reindexed",
  "document_id": "doc-123"
}
```

### GET /api/v1/documents/{document_id}/stats

Get document statistics.

**Response**:
```json
{
  "document_id": "doc-123",
  "chunk_count": 15,
  "entity_count": 8,
  "relationship_count": 12,
  "created_at": "2025-12-30T10:00:00Z",
  "last_accessed": null
}
```

---

## Health Endpoints

### GET /health

Basic health check.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-30T12:00:00Z",
  "service": "luminari-ai-agent",
  "version": "1.8.0"
}
```

### GET /health/detailed

Comprehensive health status.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-30T12:00:00Z",
  "uptime": 3600,
  "version": "1.8.0",
  "checks": {
    "database": {"status": "healthy", "response_time": 15.2},
    "llm": {"status": "healthy", "response_time": 250.5},
    "embedding": {"status": "healthy", "response_time": 50.1}
  }
}
```

### GET /health/metrics

Get system metrics.

**Response**:
```json
{
  "timestamp": "2025-12-30T12:00:00Z",
  "system": {
    "cpu_percent": 25.5,
    "memory_percent": 45.2,
    "uptime": 3600
  },
  "prometheus_endpoint": "http://localhost:9090/metrics"
}
```

### GET /health/components/{component}

Get health status for specific component.

**Components**: `database`, `llm`, `embedding`, `memory`, `web_search`

**Response**:
```json
{
  "name": "database",
  "status": "healthy",
  "response_time": 15.2,
  "error": null,
  "last_check": "2025-12-30T12:00:00Z",
  "details": {}
}
```

### GET /health/readiness

Kubernetes readiness probe.

**Response** (200 OK):
```json
{
  "ready": true,
  "timestamp": "2025-12-30T12:00:00Z"
}
```

**Response** (503 Service Unavailable):
```json
{
  "ready": false,
  "timestamp": "2025-12-30T12:00:00Z",
  "critical_failures": ["database"]
}
```

### GET /health/liveness

Kubernetes liveness probe.

**Response**:
```json
{
  "alive": true,
  "timestamp": "2025-12-30T12:00:00Z",
  "uptime": 3600
}
```

### GET /health/startup

Kubernetes startup probe.

**Response**:
```json
{
  "started": true,
  "timestamp": "2025-12-30T12:00:00Z",
  "uptime": 60
}
```

### GET /health/rate-limits/{user_id}

Get rate limit status for user.

**Response**:
```json
{
  "user_id": "user-123",
  "tier": "free",
  "requests_used": 45,
  "requests_limit": 60,
  "reset_at": "2025-12-30T12:01:00Z"
}
```

### POST /health/rate-limits/{user_id}/tier

Set user rate limit tier.

**Query Parameters**:
- `tier` (string, required): "free", "premium", or "enterprise"

**Response**:
```json
{
  "user_id": "user-123",
  "tier": "premium",
  "updated_at": "2025-12-30T12:00:00Z"
}
```

---

## Error Responses

All endpoints return consistent error responses:

**400 Bad Request**:
```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid request parameters",
    "details": {"field": "query", "issue": "required"}
  }
}
```

**404 Not Found**:
```json
{
  "error": {
    "code": "not_found",
    "message": "The requested resource was not found"
  }
}
```

**429 Too Many Requests**:
```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Rate limit exceeded. Try again in 60 seconds."
  }
}
```

**500 Internal Server Error**:
```json
{
  "error": {
    "code": "internal_server_error",
    "message": "An internal error occurred"
  }
}
```

---

**Last Updated**: 2025-12-30
