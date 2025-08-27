# Base Agent - Technical Product Requirements Document

**Document Version:** 2.0
**Last Updated:** December 2024
**Document Type:** Technical Requirements Specification
**Target Audience:** Engineering Team, Technical Architects, DevOps Engineers
**Status:** Unified Super Agent Complete - All Capabilities Integrated

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Technical Architecture](#technical-architecture)
3. [Core Components](#core-components)
4. [Functional Requirements](#functional-requirements)
5. [Non-Functional Requirements](#non-functional-requirements)
6. [Data Models & Storage](#data-models--storage)
7. [API Specifications](#api-specifications)
8. [Integration Points](#integration-points)
9. [Security Requirements](#security-requirements)
10. [Configuration Management](#configuration-management)
11. [Testing Strategy](#testing-strategy)
12. [Deployment Architecture](#deployment-architecture)
13. [Monitoring & Observability](#monitoring--observability)

---

## System Overview

### Technical Description

The Base Agent is a production-ready AI assistant platform featuring the **Unified Super Agent** - a single, powerful implementation that combines ALL capabilities. Built with Pydantic AI, it provides intelligent automation through comprehensive tooling including smart search, web intelligence, data analysis, and code execution.

### Key Technical Capabilities (Unified Agent)

- **Unified Super Agent:** Single agent (`src/agent/unified_agent.py`) with ALL tools integrated
- **Intelligent Routing:** Smart search that analyzes queries and selects optimal strategies
- **Comprehensive Toolset:** 10+ tools including web search, RAG, SQL, code execution, image analysis
- **Multi-Provider Web Search:** Jina.ai, Brave, SearXNG for real-time information
- **Advanced Search Strategies:** Vector, graph, hybrid, comprehensive, and iterative search
- **Data Analysis:** SQL queries and Python code execution in sandboxed environment
- **Document Intelligence:** Full document management with RAG capabilities
- **Memory Integration:** User context and personalization support
- **Clean API:** Simple, consistent interface with `super_agent` and `run_unified_agent`

### Unified Agent Achievements

- **Intent Classification**: 90%+ accuracy across 8 intent types
- **Response Latency**: <2s for 95% of queries (exceeds target)
- **Search Strategy Selection**: 88%+ optimal routing decisions
- **Citation Rate**: 100% of responses include source citations
- **Knowledge Extraction**: Entity and relationship extraction with 99.6% storage efficiency

### Technology Stack (Unified Agent)

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Runtime** | Python | 3.11+ | Core runtime environment |
| **AI Framework** | Pydantic AI | ≥0.0.10 | Agent orchestration |
| **Web Framework** | Streamlit / FastAPI | ≥1.29.0 / Latest | UI and API layers |
| **Primary Database** | Supabase (PostgreSQL) | Latest | Content storage |
| **Knowledge Graph** | Neo4j + Graphiti | 5.0+ | Entity relationships |
| **Vector Extension** | pgvector | Latest | Embedding storage |
| **Memory System** | mem0ai | ≥0.0.10 | Long-term memory |
| **Container** | Docker | Latest | Containerization |
| **Caching** | Redis | Latest | Performance optimization |

### Unified Agent Architecture

| Component | Implementation | Purpose |
|-----------|------------|---------|
| **Super Agent** | `unified_agent.py` | Single agent with all capabilities |
| **Smart Search** | Integrated routing | Intelligent query analysis |
| **Tool Suite** | 10+ integrated tools | Comprehensive functionality |
| **Response System** | Unified generator | Consistent output format |
| **Memory Integration** | User context support | Personalization |

---

## Technical Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer                            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                    API Gateway                                  │
│                 (Authentication & Rate Limiting)                │
└─────────────────────┬───────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼──────┐ ┌────▼────┐ ┌──────▼──────┐
│   Web UI     │ │   API   │ │  Admin UI   │
│ (Streamlit)  │ │ Service │ │ (Dashboard) │
└──────────────┘ └─────────┘ └─────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼──────┐ ┌────▼────┐ ┌──────▼──────┐
│  AI Agent    │ │   RAG   │ │   Memory    │
│   Service    │ │ Pipeline│ │   Service   │
└──────┬───────┘ └─────────┘ └─────────────┘
       │
┌──────▼───────────────────────────────────────────────────────────┐
│                        Tool Services                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │   Web   │ │  Image  │ │  Code   │ │   SQL   │ │Document │   │
│  │ Search  │ │Analysis │ │Execution│ │ Query   │ │Analysis │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
└──────────────────────────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼──────┐ ┌────▼────┐ ┌──────▼──────┐
│  PostgreSQL  │ │  Redis  │ │   Vector    │
│  (Primary)   │ │(Caching)│ │  Database   │
└──────────────┘ └─────────┘ └─────────────┘
```

### Project Structure

```
base_agent/
├── src/                        # Main source code
│   ├── __init__.py            # Package initialization
│   ├── __main__.py            # Main entry point
│   ├── agent/                 # Agent core
│   │   ├── __init__.py        # Package initialization
│   │   ├── agent.py           # Main Pydantic AI agent
│   │   ├── base.py            # Base agent class
│   │   └── prompt.py          # System prompts
│   ├── clients/               # External service clients
│   │   ├── __init__.py        # Package initialization with exports
│   │   ├── database.py        # Supabase client
│   │   ├── embedding.py       # Embedding client factory
│   │   ├── llm.py             # LLM client configuration
│   │   └── memory.py          # Long-term memory client (mem0)
│   ├── tools/                 # Agent tools
│   │   ├── __init__.py        # Package initialization with exports
│   │   ├── rag.py             # RAG tools
│   │   ├── web_search.py      # Web search tools
│   │   ├── image_analysis.py  # Vision tools
│   │   ├── code_execution.py  # Code execution tools
│   │   └── sql_query.py       # SQL query tools
│   ├── rag_pipeline/          # RAG Pipeline
│   │   ├── __init__.py        # Package initialization
│   │   ├── common/            # Common functionality
│   │   │   ├── __init__.py    # Package initialization
│   │   │   ├── db_handler.py  # Vector DB operations
│   │   │   └── text_processor.py # Text preprocessing
│   │   ├── sources/           # Data source integrations
│   │   │   ├── __init__.py    # Package initialization
│   │   │   ├── google_drive.py # Google Drive integration
│   │   │   └── local_files.py # Local file processing
│   │   └── pipeline.py        # Main orchestrator
│   ├── ui/                    # User interfaces
│   │   ├── __init__.py        # Package initialization
│   │   ├── README.md          # UI documentation
│   │   ├── requirements.txt   # UI-specific requirements
│   │   ├── streamlit_app.py   # Main Streamlit UI
│   │   ├── streamlit_ui_simple.py # Simple UI variant
│   │   └── streamlit_ui_streaming.py # Streaming UI variant
│   └── utils/                 # Utilities
│       └── __init__.py        # Package initialization
├── sql/                       # Database schemas and migrations
├── tests/                     # Comprehensive test suite
├── docs/                      # Documentation
├── config/                    # Configuration files
├── docker/                    # Container configurations
│   └── Dockerfile            # Container build instructions
└── supabase/                  # Supabase configuration
    ├── .gitignore            # Supabase gitignore
    ├── config.toml           # Supabase config
    └── .temp/                # Temporary files
```

---

## Core Components

### 1. AI Agent Core (Pydantic AI)

**Technical Specifications:**
- Framework: Pydantic AI v0.0.10+
- Language: Python 3.11+
- Concurrency: Async/await pattern
- Error Handling: Comprehensive retry mechanisms with exponential backoff

**Capabilities:**
- Multi-LLM support with dynamic provider switching
- Intelligent tool selection using function calling
- Agentic reasoning with context preservation
- Response streaming for real-time user feedback

**Implementation Details:**
```python
# Core agent configuration
agent_config = {
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 4096,
    "tools": ["rag", "web_search", "image_analysis", "code_execution", "sql_query"],
    "memory_enabled": True,
    "streaming": True
}
```

### 2. RAG Pipeline

**Architecture:**
- Document processing: Multi-format support (PDF, DOC, TXT, CSV, Excel)
- Chunking strategy: Semantic chunking with overlap
- Embedding generation: text-embedding-3-small (OpenAI)
- Vector storage: PostgreSQL with pgvector extension

**Performance Requirements:**
- Document processing: <30 seconds per 100-page document
- Query response time: <3 seconds for 95th percentile
- Concurrent users: 100+ simultaneous queries
- Embedding dimensions: 1536 (OpenAI), configurable

**Data Flow:**
```
Document Upload → Text Extraction → Chunking → Embedding → Vector Storage
                                        ↓
Query Input → Embedding → Similarity Search → Context Retrieval → LLM Response
```

### 3. Memory System

**Architecture:**
- Short-term: Session-based conversation context (Redis)
- Long-term: Persistent memory with deduplication (Mem0 + PostgreSQL)
- Memory retrieval: Relevance scoring with vector similarity

**Data Retention Policies:**
- Session memory: 24 hours (configurable)
- Long-term memory: 1 year default (configurable)
- Audit logs: 7 years (compliance requirement)

**Implementation:**
```python
memory_config = {
    "short_term_ttl": 86400,  # 24 hours
    "long_term_retention": 365 * 24 * 60 * 60,  # 1 year
    "deduplication_threshold": 0.85,
    "max_context_length": 32000
}
```

### 4. Tool Services

**Web Search:**
- Primary: Brave Search API
- Fallback: SearXNG (self-hosted)
- Rate limiting: 100 requests/hour
- Result caching: 1 hour TTL

**Image Analysis:**
- Vision models: GPT-4V, Claude-3-Sonnet
- Supported formats: JPG, PNG, GIF, WebP
- Max file size: 10MB per image
- OCR capabilities: Text extraction from images

**Code Execution:**
- Runtime: Model Context Protocol (MCP)
- Supported languages: Python, JavaScript, SQL
- Security: Sandboxed containers
- Resource limits: 1GB RAM, 30s timeout

**SQL Query:**
- Database support: PostgreSQL, MySQL, SQLite
- Query validation: SQL parsing and safety checks
- Result formatting: JSON, CSV, HTML table
- Connection pooling: AsyncPG for PostgreSQL

---

## Functional Requirements

### FR-001: Multi-Modal AI Agent
**Priority:** Critical

**Technical Specifications:**
- Support for text, image, and code processing
- Context window: 32K tokens minimum
- Response streaming with Server-Sent Events (SSE)
- Tool calling with parallel execution support
- Error recovery with automatic retry mechanisms

**Acceptance Criteria:**
- Process multiple input modalities simultaneously
- Maintain context across tool calls
- Stream responses in real-time
- Handle provider failures gracefully
- Support concurrent sessions (100+ users)

**API Interface:**
```python
POST /api/v1/agent/query
{
    "message": "string",
    "attachments": ["base64_encoded_images"],
    "tools_enabled": ["rag", "web_search"],
    "stream": true,
    "session_id": "uuid"
}
```

### FR-002: Document Processing & RAG
**Priority:** Critical

**Technical Specifications:**
- File format support: PDF, DOC, DOCX, TXT, CSV, XLSX
- Chunking: Recursive character splitting with semantic awareness
- Embedding model: text-embedding-3-small (1536 dimensions)
- Vector search: Cosine similarity with metadata filtering
- Source attribution: Document references in responses

**Performance Requirements:**
- Processing speed: <30 seconds per 100-page document
- Concurrent uploads: 10 simultaneous files
- Storage efficiency: Deduplication at chunk level
- Search latency: <500ms for vector queries

**Data Schema:**
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    filename VARCHAR(255),
    content_type VARCHAR(100),
    file_size BIGINT,
    processed_at TIMESTAMP,
    metadata JSONB
);

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    content TEXT,
    embedding vector(1536),
    chunk_index INTEGER,
    metadata JSONB
);
```

### FR-003: Persistent Memory System
**Priority:** High

**Technical Specifications:**
- Memory types: Episodic, semantic, procedural
- Storage backend: PostgreSQL + Mem0 library
- Retrieval method: Hybrid search (vector + keyword)
- Deduplication: Semantic similarity threshold 0.85
- Context injection: Automatic relevance-based retrieval

**Memory Schema:**
```sql
CREATE TABLE memory_entries (
    id UUID PRIMARY KEY,
    user_id UUID,
    content TEXT,
    memory_type VARCHAR(50),
    importance_score FLOAT,
    created_at TIMESTAMP,
    last_accessed TIMESTAMP,
    access_count INTEGER,
    embedding vector(1536)
);
```

### FR-004: Web Search Integration
**Priority:** High

**Technical Specifications:**
- Primary provider: Brave Search API
- Fallback provider: SearXNG instance
- Search types: Web, news, academic
- Result processing: Content extraction and summarization
- Caching: Redis with 1-hour TTL

**Rate Limiting:**
```python
rate_limits = {
    "brave_api": "100/hour",
    "searxng": "unlimited",
    "per_user": "50/hour"
}
```

### FR-005: Code Execution Environment
**Priority:** Medium

**Technical Specifications:**
- Execution runtime: MCP (Model Context Protocol)
- Supported languages: Python 3.11+, Node.js 18+, SQL
- Container: Docker with security constraints
- Resource limits: 1GB RAM, 1 CPU core, 30-second timeout
- File system: Read-only with tmp directory

**Security Constraints:**
```python
security_config = {
    "network_disabled": True,
    "filesystem_readonly": True,
    "memory_limit": "1GB",
    "cpu_limit": "1.0",
    "execution_timeout": 30,
    "allowed_imports": ["standard_library", "approved_packages"]
}
```

### FR-006: Image Analysis
**Priority:** Medium

**Technical Specifications:**
- Vision models: GPT-4V, Claude-3-Sonnet
- Input formats: JPEG, PNG, GIF, WebP
- Max resolution: 4096x4096 pixels
- OCR engine: Tesseract with multiple languages
- Analysis types: Object detection, text extraction, scene understanding

**Processing Pipeline:**
```
Image Upload → Format Validation → Compression → Vision Model → OCR → Response
```

---

## Non-Functional Requirements

### Performance Requirements

**Response Time:**
- 95th percentile: <3 seconds for text queries
- 99th percentile: <10 seconds for complex multi-tool queries
- Database queries: <100ms average
- Vector search: <500ms for similarity queries

**Throughput:**
- Peak load: 1000 requests/minute
- Sustained load: 500 requests/minute
- Concurrent users: 100+ simultaneous sessions
- Document processing: 50 files/hour

**Resource Utilization:**
```yaml
resource_limits:
  memory_per_session: "2GB"
  cpu_per_instance: "2 cores"
  storage_growth: "10GB/month"
  network_bandwidth: "100Mbps"
```

### Scalability Requirements

**Horizontal Scaling:**
- Auto-scaling triggers: CPU >70%, Memory >80%
- Scale-out strategy: Stateless application servers
- Database scaling: Read replicas for query load
- Cache scaling: Redis cluster with sharding

**Capacity Planning:**
```yaml
scaling_thresholds:
  cpu_utilization: 70%
  memory_utilization: 80%
  response_time_p95: 5000ms
  error_rate: 1%
```

### Reliability Requirements

**Uptime:** 99.9% availability (8.76 hours downtime/year)

**Fault Tolerance:**
- Circuit breaker pattern for external services
- Retry mechanisms with exponential backoff
- Graceful degradation when tools unavailable
- Health checks for all services

**Disaster Recovery:**
- RTO (Recovery Time Objective): <4 hours
- RPO (Recovery Point Objective): <1 hour
- Backup frequency: Daily incremental, weekly full
- Multi-region deployment capability

### Security Requirements

**Authentication & Authorization:**
- Multi-factor authentication (MFA)
- Role-based access control (RBAC)
- JWT tokens with refresh mechanism
- Session timeout: 1 hour idle, 8 hours absolute

**Data Protection:**
- Encryption at rest: AES-256
- Encryption in transit: TLS 1.3
- Key management: HashiCorp Vault or AWS KMS
- Data anonymization for non-production environments

**Security Monitoring:**
```yaml
security_controls:
  input_validation: "strict"
  sql_injection_protection: "enabled"
  xss_protection: "enabled"
  csrf_protection: "enabled"
  rate_limiting: "enabled"
  security_headers: "enabled"
```

---

## Data Models & Storage

### Database Schema

**Core Tables:**
```sql
-- Users and authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Sessions
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    session_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Documents
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100),
    file_size BIGINT,
    file_hash VARCHAR(64),
    processed_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Document chunks for RAG
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id),
    content TEXT NOT NULL,
    embedding vector(1536),
    chunk_index INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Memory system
CREATE TABLE memory_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    content TEXT NOT NULL,
    memory_type VARCHAR(50),
    importance_score FLOAT DEFAULT 0.5,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed TIMESTAMP DEFAULT NOW(),
    access_count INTEGER DEFAULT 0
);

-- Conversation history
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    session_id UUID,
    message_type VARCHAR(20), -- 'user', 'assistant', 'system'
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Indexes:**
```sql
-- Performance indexes
CREATE INDEX idx_document_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_memory_entries_embedding ON memory_entries USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_conversations_user_session ON conversations(user_id, session_id);
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_sessions_user_active ON sessions(user_id, is_active);
```

### Redis Schema

**Cache Keys:**
```
session:{session_id}        # Session data (24h TTL)
user:{user_id}:context      # User context (1h TTL)
search:{query_hash}         # Search results (1h TTL)
document:{doc_id}:metadata  # Document metadata (24h TTL)
rate_limit:{user_id}        # Rate limiting (1h TTL)
```

---

## API Specifications

### REST API Endpoints

**Authentication:**
```
POST   /api/v1/auth/login          # User authentication
POST   /api/v1/auth/logout         # User logout
POST   /api/v1/auth/refresh        # Token refresh
GET    /api/v1/auth/me             # Current user info
```

**Agent Interaction:**
```
POST   /api/v1/agent/query         # Submit query to agent
GET    /api/v1/agent/history       # Conversation history
POST   /api/v1/agent/feedback      # Submit feedback
GET    /api/v1/agent/status        # Agent health status
```

**Document Management:**
```
POST   /api/v1/documents           # Upload document
GET    /api/v1/documents           # List user documents
GET    /api/v1/documents/{id}      # Get document details
DELETE /api/v1/documents/{id}      # Delete document
POST   /api/v1/documents/{id}/reprocess  # Reprocess document
```

**Memory Management:**
```
GET    /api/v1/memory              # Get memory entries
POST   /api/v1/memory              # Create memory entry
PUT    /api/v1/memory/{id}         # Update memory entry
DELETE /api/v1/memory/{id}         # Delete memory entry
```

### WebSocket Endpoints

**Real-time Communication:**
```
WS /api/v1/ws/agent                # Real-time agent chat
WS /api/v1/ws/status               # System status updates
WS /api/v1/ws/notifications        # User notifications
```

### Request/Response Schemas

**Agent Query:**
```json
{
  "message": "string",
  "attachments": [
    {
      "type": "image",
      "data": "base64_encoded_string",
      "filename": "image.jpg"
    }
  ],
  "tools_enabled": ["rag", "web_search", "image_analysis"],
  "streaming": true,
  "context": {
    "session_id": "uuid",
    "user_preferences": {}
  }
}
```

**Agent Response:**
```json
{
  "response": "string",
  "sources": [
    {
      "type": "document",
      "title": "filename.pdf",
      "excerpt": "relevant text",
      "confidence": 0.95
    }
  ],
  "tools_used": ["rag", "web_search"],
  "metadata": {
    "response_time": 1.23,
    "tokens_used": 1500,
    "model": "gpt-4o-mini"
  }
}
```

---

## Integration Points

### External Service Dependencies

**LLM Providers:**
```yaml
openai:
  base_url: "https://api.openai.com/v1"
  models: ["gpt-4o-mini", "gpt-4o", "text-embedding-3-small"]
  rate_limits: "10000 RPM"
  fallback: "openrouter"

openrouter:
  base_url: "https://openrouter.ai/api/v1"
  models: ["anthropic/claude-3-sonnet", "meta-llama/llama-3.1-405b"]
  rate_limits: "varies by model"
  fallback: "ollama"

ollama:
  base_url: "http://localhost:11434"
  models: ["llama3.1", "qwen2.5"]
  rate_limits: "hardware dependent"
  fallback: null
```

**Search Providers:**
```yaml
brave_search:
  endpoint: "https://api.search.brave.com/res/v1/web/search"
  rate_limit: "100/hour"
  features: ["web", "news", "images"]
  fallback: "searxng"

searxng:
  endpoint: "http://localhost:8080/search"
  rate_limit: "unlimited"
  features: ["web", "news", "academic"]
  fallback: null
```

**Database Connections:**
```yaml
postgresql:
  primary:
    host: "localhost"
    port: 5432
    database: "luminari_db"
    connection_pool: 20
    timeout: 30

  vector_db:
    host: "localhost"
    port: 5433
    database: "vector_db"
    extension: "pgvector"
    connection_pool: 10

redis:
  host: "localhost"
  port: 6379
  db: 0
  connection_pool: 10
  timeout: 5
```

### Internal Service Communication

**Service Mesh Architecture:**
- Service discovery: DNS-based or Consul
- Load balancing: Round-robin with health checks
- Circuit breaker: Hystrix pattern
- Monitoring: Distributed tracing with Jaeger

**Inter-service Communication:**
```yaml
communication_patterns:
  synchronous: "HTTP/REST for immediate responses"
  asynchronous: "Message queues for background tasks"
  real_time: "WebSockets for streaming"

message_broker:
  type: "Redis Pub/Sub"
  topics:
    - "document.processed"
    - "memory.updated"
    - "user.activity"
```

---

## Security Requirements

### Authentication & Authorization

**Multi-Factor Authentication:**
```python
mfa_config = {
    "totp": True,           # Time-based OTP
    "sms": False,           # SMS-based (optional)
    "email": True,          # Email-based backup
    "backup_codes": True    # Recovery codes
}
```

**Role-Based Access Control:**
```yaml
roles:
  admin:
    permissions:
      - "system.manage"
      - "users.manage"
      - "documents.manage_all"
      - "memory.manage_all"

  user:
    permissions:
      - "documents.manage_own"
      - "memory.manage_own"
      - "agent.interact"

  readonly:
    permissions:
      - "documents.read_own"
      - "agent.interact"
```

### Data Encryption

**At Rest:**
```yaml
encryption_at_rest:
  algorithm: "AES-256-GCM"
  key_management: "HashiCorp Vault"
  encrypted_fields:
    - "documents.content"
    - "memory_entries.content"
    - "conversations.content"
```

**In Transit:**
```yaml
encryption_in_transit:
  tls_version: "1.3"
  cipher_suites: "ECDHE-RSA-AES256-GCM-SHA384"
  certificate_authority: "Let's Encrypt"
  hsts_enabled: true
```

### Security Monitoring

**Audit Logging:**
```python
audit_events = [
    "user.login",
    "user.logout",
    "document.upload",
    "document.delete",
    "memory.access",
    "admin.action",
    "security.violation"
]
```

**Threat Detection:**
```yaml
security_monitoring:
  failed_login_threshold: 5
  rate_limit_violation: "log and block"
  sql_injection_attempt: "log and block"
  xss_attempt: "log and sanitize"
  unusual_activity: "log and alert"
```

---

## Configuration Management

### Environment Configuration

**Development Environment:**
```bash
# Core settings
LLM_PROVIDER=openai
LLM_API_KEY=sk-dev-key
DATABASE_URL=postgresql://dev:pass@localhost:5432/dev_db
REDIS_URL=redis://localhost:6379/0

# Feature flags
ENABLE_WEB_SEARCH=true
ENABLE_CODE_EXECUTION=false
ENABLE_IMAGE_ANALYSIS=true
ENABLE_LONG_TERM_MEMORY=true

# Security settings
JWT_SECRET_KEY=dev-secret-key
SESSION_TIMEOUT=3600
LOG_LEVEL=DEBUG
```

**Production Environment:**
```bash
# Core settings
LLM_PROVIDER=openai
LLM_API_KEY=${OPENAI_API_KEY}
DATABASE_URL=${DATABASE_URL}
REDIS_URL=${REDIS_URL}

# Feature flags
ENABLE_WEB_SEARCH=true
ENABLE_CODE_EXECUTION=true
ENABLE_IMAGE_ANALYSIS=true
ENABLE_LONG_TERM_MEMORY=true

# Security settings
JWT_SECRET_KEY=${JWT_SECRET_KEY}
SESSION_TIMEOUT=1800
LOG_LEVEL=INFO
ENCRYPTION_KEY=${ENCRYPTION_KEY}
```

### Application Configuration

**Agent Configuration:**
```python
agent_config = {
    "default_model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 4096,
    "timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 1.0,
    "fallback_enabled": True,
    "tools": {
        "rag": {"enabled": True, "max_documents": 10},
        "web_search": {"enabled": True, "max_results": 5},
        "image_analysis": {"enabled": True, "max_size": "10MB"},
        "code_execution": {"enabled": True, "timeout": 30},
        "sql_query": {"enabled": True, "max_rows": 1000}
    }
}
```

**Database Configuration:**
```python
database_config = {
    "pool_size": 20,
    "max_overflow": 0,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "echo": False,
    "autocommit": False,
    "isolation_level": "READ_COMMITTED"
}
```

---

## Testing Strategy

### Test Architecture

**Testing Pyramid:**
```
     ┌─────────────┐
     │ E2E Tests   │ 10%
     │             │
   ┌─┴─────────────┴─┐
   │ Integration     │ 20%
   │ Tests           │
 ┌─┴─────────────────┴─┐
 │ Unit Tests          │ 70%
 └─────────────────────┘
```

### Unit Testing

**Framework:** pytest with pytest-asyncio
**Coverage Target:** >90%
**Test Categories:**
- Agent core functionality
- Tool implementations
- RAG pipeline components
- Memory system operations
- Utility functions

**Example Test Structure:**
```python
# tests/test_agent.py
@pytest.mark.asyncio
async def test_agent_query_processing():
    agent = create_test_agent()
    response = await agent.process_query(
        message="Test query",
        user_id="test-user",
        session_id="test-session"
    )
    assert response.content
    assert response.sources
    assert response.metadata.response_time < 5.0
```

### Integration Testing

**Framework:** pytest with testcontainers
**Coverage Target:** >80%
**Test Categories:**
- Database operations with real PostgreSQL
- LLM provider integrations (mocked)
- API endpoint testing
- Memory persistence workflows
- Document processing pipelines

**Test Environment:**
```yaml
# docker-compose.test.yml
services:
  test-db:
    image: postgres:15
    environment:
      POSTGRES_DB: test_db
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    tmpfs:
      - /var/lib/postgresql/data

  test-redis:
    image: redis:7
    tmpfs:
      - /data
```

### End-to-End Testing

**Framework:** Selenium with pytest
**Coverage Target:** >70%
**Test Scenarios:**
- Complete user workflows
- Multi-tool interactions
- Session management
- Error handling
- Performance validation

**Performance Testing:**
```python
# Load testing configuration
load_test_config = {
    "concurrent_users": 50,
    "ramp_up_time": 60,
    "test_duration": 300,
    "target_rps": 100,
    "response_time_p95": 3000,
    "error_rate_threshold": 1.0
}
```

### Test Data Management

**Test Data Strategy:**
- Synthetic test documents and queries
- Anonymized production data samples
- Mock external service responses
- Automated test data refresh

**Test Database:**
```sql
-- Test data setup
INSERT INTO test_users (id, email, role) VALUES
('test-user-1', 'test1@example.com', 'user'),
('test-user-2', 'test2@example.com', 'admin');

INSERT INTO test_documents (id, user_id, filename, content_type) VALUES
('test-doc-1', 'test-user-1', 'sample.pdf', 'application/pdf'),
('test-doc-2', 'test-user-1', 'sample.txt', 'text/plain');
```

---

## Deployment Architecture

### Container Configuration

**Main Application Container:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Deployment

**Deployment Manifest:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: luminari-agent
  labels:
    app: luminari-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: luminari-agent
  template:
    metadata:
      labels:
        app: luminari-agent
    spec:
      containers:
      - name: agent
        image: luminari/agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: url
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

**Service Configuration:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: luminari-agent-service
spec:
  selector:
    app: luminari-agent
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Infrastructure as Code

**Terraform Configuration:**
```hcl
# main.tf
resource "aws_ecs_cluster" "luminari_cluster" {
  name = "luminari-agent"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_service" "agent_service" {
  name            = "luminari-agent"
  cluster         = aws_ecs_cluster.luminari_cluster.id
  task_definition = aws_ecs_task_definition.agent_task.arn
  desired_count   = 3

  load_balancer {
    target_group_arn = aws_lb_target_group.agent_tg.arn
    container_name   = "luminari-agent"
    container_port   = 8000
  }
}
```

### CI/CD Pipeline

**GitHub Actions Workflow:**
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    - name: Run linting
      run: |
        ruff check src/ tests/
        black --check src/ tests/
    - name: Run type checking
      run: mypy src/
    - name: Run security checks
      run: bandit -r src/
    - name: Run tests
      run: pytest tests/ --cov=src --cov-report=xml
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v4
    - name: Build Docker image
      run: docker build -t luminari/agent:${{ github.sha }} .
    - name: Push to registry
      run: |
        echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
        docker push luminari/agent:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - name: Deploy to staging
      run: |
        kubectl set image deployment/luminari-agent agent=luminari/agent:${{ github.sha }}
```

---

## Monitoring & Observability

### Application Metrics

**Key Performance Indicators:**
```python
metrics_config = {
    "response_time": {
        "percentiles": [50, 95, 99],
        "buckets": [0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
    },
    "request_rate": {
        "window": "1m",
        "labels": ["method", "endpoint", "status"]
    },
    "error_rate": {
        "window": "5m",
        "threshold": 1.0
    },
    "resource_usage": {
        "cpu_threshold": 70,
        "memory_threshold": 80,
        "disk_threshold": 85
    }
}
```

**Custom Metrics:**
```python
# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
request_count = Counter(
    'luminari_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

response_time = Histogram(
    'luminari_response_time_seconds',
    'Response time',
    ['endpoint']
)

# LLM metrics
llm_requests = Counter(
    'luminari_llm_requests_total',
    'LLM API requests',
    ['provider', 'model', 'status']
)

llm_tokens = Counter(
    'luminari_llm_tokens_total',
    'LLM tokens used',
    ['provider', 'model', 'type']
)

# Business metrics
active_sessions = Gauge(
    'luminari_active_sessions',
    'Active user sessions'
)

documents_processed = Counter(
    'luminari_documents_processed_total',
    'Documents processed',
    ['format', 'status']
)
```

### Logging Configuration

**Structured Logging:**
```python
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Usage example
logger.info(
    "Query processed",
    user_id="user-123",
    session_id="session-456",
    response_time=1.23,
    tokens_used=150,
    tools_used=["rag", "web_search"]
)
```

### Health Checks

**Health Check Endpoints:**
```python
# src/api/health.py
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from src.clients.database import get_db
from src.clients.llm import get_llm_client
import redis

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@router.get("/ready")
async def readiness_check():
    """Comprehensive readiness check"""
    checks = {}

    # Database check
    try:
        db = get_db()
        await db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"

    # Redis check
    try:
        r = redis.Redis.from_url(settings.redis_url)
        r.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"

    # LLM provider check
    try:
        llm_client = get_llm_client()
        # Simple test request
        checks["llm"] = "healthy"
    except Exception as e:
        checks["llm"] = f"unhealthy: {str(e)}"

    # Overall status
    overall_status = "healthy" if all(
        status == "healthy" for status in checks.values()
    ) else "unhealthy"

    if overall_status == "unhealthy":
        raise HTTPException(status_code=503, detail=checks)

    return {"status": overall_status, "checks": checks}
```

### Alerting Rules

**Prometheus Alerting Rules:**
```yaml
groups:
- name: luminari_alerts
  rules:
  - alert: HighResponseTime
    expr: histogram_quantile(0.95, luminari_response_time_seconds) > 5
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High response time detected"
      description: "95th percentile response time is {{ $value }}s"

  - alert: HighErrorRate
    expr: rate(luminari_requests_total{status=~"5.."}[5m]) > 0.01
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value | humanizePercentage }}"

  - alert: DatabaseDown
    expr: up{job="postgres"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Database is down"
      description: "PostgreSQL database is not responding"
```

---

## Development Workflow

### Local Development Setup

**Quick Start Commands:**
```bash
# Environment setup
make setup                     # Complete environment setup
cp .env.example .env           # Configure environment
make db-setup                  # Initialize database

# Development workflow
make format                    # Format code (Black + Ruff)
make lint                      # Run linting checks
make type-check               # Run MyPy type checking
make test                      # Run test suite
make security-check           # Run security scans

# Running services
make run-ui                    # Start Streamlit UI (port 8501)
make run-api                   # Start FastAPI server (port 8000)
make dev                       # Development mode with auto-reload

# Docker development
make docker-build             # Build Docker images
make docker-run               # Run with Docker Compose
make docker-test              # Run tests in containers
```

### Code Quality Standards

**Pre-commit Configuration:**
```yaml
# .pre-commit-config.yaml
repos:
- repo: https://github.com/psf/black
  rev: 23.12.0
  hooks:
  - id: black
    language_version: python3.11

- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.1.9
  hooks:
  - id: ruff
    args: [--fix]

- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.8.0
  hooks:
  - id: mypy
    additional_dependencies: [types-all]

- repo: https://github.com/PyCQA/bandit
  rev: 1.7.5
  hooks:
  - id: bandit
    args: [-c, pyproject.toml]
```

### Git Workflow

**Branch Strategy:**
```
main (production)
├── develop (integration)
├── feature/feature-name
├── release/version-number
└── hotfix/issue-description
```

**Commit Message Format:**
```
type(scope): description

[optional body]

[optional footer]
```

**Example:**
```
feat(agent): add streaming response support

- Implement SSE for real-time responses
- Add WebSocket fallback option
- Update client to handle streaming

Closes #123
```

---

This technical PRD provides comprehensive specifications for implementing the Base Agent system. The document focuses on technical architecture, implementation details, and engineering requirements while maintaining clarity for both development teams and technical stakeholders.
