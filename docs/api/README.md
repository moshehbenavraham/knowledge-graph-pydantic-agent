# Agentic RAG API Documentation

This directory contains the API reference for the Agentic GraphRAG System.

---

## Overview

The Agentic RAG API is a production-ready FastAPI application providing:
- **Chat Interface**: Synchronous, SSE streaming, and WebSocket conversations
- **Search Engine**: Vector, graph, hybrid, and adaptive search strategies
- **Document Management**: Ingestion, CRUD operations, and reindexing
- **Analytics**: Search metrics, usage tracking, and system monitoring
- **Health Monitoring**: Kubernetes-compatible probes and component health

**Base URL**: `http://localhost:8058`
**API Version**: `0.8.0`
**OpenAPI**: `/api/v1/openapi.json`

---

## Quick Start

### Start the API Server

```bash
# Using Makefile
make run-api

# Direct command
uvicorn src.api.main:app --host 0.0.0.0 --port 8058

# With auto-reload (development)
uvicorn src.api.main:app --host 0.0.0.0 --port 8058 --reload
```

### Interactive Documentation

- **Swagger UI**: http://localhost:8058/docs
- **ReDoc**: http://localhost:8058/redoc

### Basic Health Check

```bash
curl http://localhost:8058/health
```

---

## Documentation Index

| Document | Description |
|----------|-------------|
| [endpoints.md](endpoints.md) | Complete endpoint reference with examples |

### Interactive API Documentation

When the API server is running (`make run-api`), interactive documentation is available:

- **Swagger UI**: `http://localhost:8058/docs` - Interactive API explorer
- **ReDoc**: `http://localhost:8058/redoc` - Alternative documentation format

---

## Authentication

The API currently supports the following authentication methods:

- **Rate Limiting**: Per-user request limits (60 requests/minute default)
- **Tier-Based Access**: `free`, `premium`, `enterprise` tiers
- **API Keys**: Configure via environment variables (future)

Set user tier:
```bash
curl -X POST "http://localhost:8058/health/rate-limits/user123/tier?tier=premium"
```

---

## API Endpoints Summary

### Root Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/api/v1/status` | System status |
| GET | `/metrics` | Prometheus metrics |
| DELETE | `/api/v1/cache` | Clear cache |

### Chat Endpoints (`/api/v1/chat`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat` | Synchronous chat |
| POST | `/api/v1/chat/stream` | SSE streaming chat |
| WS | `/api/v1/chat/ws` | WebSocket chat |
| POST | `/api/v1/chat/feedback` | Submit feedback |
| GET | `/api/v1/chat/sessions/{id}/history` | Session history |

### Search Endpoints (`/api/v1/search`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/search` | Unified search |
| GET | `/api/v1/search/suggest` | Query suggestions |
| GET | `/api/v1/search/entities/{name}` | Entity lookup |
| GET | `/api/v1/search/relationships` | Relationship search |

### Document Endpoints (`/api/v1/documents`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/documents` | Ingest document |
| GET | `/api/v1/documents` | List documents |
| GET | `/api/v1/documents/{id}` | Get document |
| DELETE | `/api/v1/documents/{id}` | Delete document |
| PATCH | `/api/v1/documents/{id}` | Update metadata |
| POST | `/api/v1/documents/{id}/reindex` | Reindex document |
| GET | `/api/v1/documents/{id}/stats` | Document statistics |

### Health Endpoints (`/health`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health |
| GET | `/health/detailed` | Detailed status |
| GET | `/health/metrics` | System metrics |
| GET | `/health/components/{name}` | Component health |
| GET | `/health/readiness` | Kubernetes readiness |
| GET | `/health/liveness` | Kubernetes liveness |
| GET | `/health/startup` | Kubernetes startup |
| GET | `/health/rate-limits/{user_id}` | Rate limit status |
| POST | `/health/rate-limits/{user_id}/tier` | Set user tier |

---

## Search Types

The API supports multiple search strategies:

| Type | Description | Best For |
|------|-------------|----------|
| `vector` | Semantic similarity search | General queries |
| `hybrid` | Vector + graph combined | Entity-related queries |
| `adaptive` | Intent-based strategy selection | Mixed workloads |

---

## Response Formats

All responses follow a consistent JSON format:

**Success Response**:
```json
{
  "data": { ... },
  "status": "success"
}
```

**Error Response**:
```json
{
  "error": {
    "code": "error_code",
    "message": "Human-readable description"
  }
}
```

---

## Rate Limiting

Default limits:
- **Free tier**: 60 requests/minute
- **Premium tier**: 300 requests/minute
- **Enterprise tier**: 1000 requests/minute

Rate limit headers:
- `X-RateLimit-Limit`: Maximum requests
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset timestamp

---

## Middleware Stack

The API includes the following middleware (applied in order):

1. **CORS**: Cross-origin resource sharing
2. **Security Headers**: X-Frame-Options, X-Content-Type-Options, etc.
3. **Compression**: Gzip for responses > 1KB
4. **Rate Limiting**: Per-user request throttling
5. **Correlation ID**: Request tracing (`X-Correlation-ID`)
6. **Timing**: Response time tracking (`X-Response-Time`)
7. **Error Handling**: Consistent error responses
8. **Request Logging**: Structured request/response logging

---

## Configuration

API configuration via environment variables:

```bash
# Server
API_HOST=0.0.0.0
API_PORT=8058
APP_ENV=development

# Features
ENABLE_METRICS=true
ENABLE_TRACING=false

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=60

# Caching
ENABLE_CACHE=true
CACHE_TTL=600
```

---

## Related Documentation

- [CONVENTIONS.md](../../.spec_system/CONVENTIONS.md) - Project coding conventions
- [Developer Setup](../developer/setup_guide.md) - Development environment
- [Troubleshooting](../troubleshooting/README.md) - Common issues

---

**Last Updated**: 2025-12-30
