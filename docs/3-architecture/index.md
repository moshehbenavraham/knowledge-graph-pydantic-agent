# Architecture Overview

Comprehensive view of Knowledge Graph Pydantic Agent's technical architecture, design principles, and system components.

## System Overview

Built on **unified agent architecture** consolidating multiple AI capabilities into a single intelligent system. Emphasizes modularity, scalability, and production readiness.

## Core Architecture Principles

### 🧠 Unified Intelligence
- **Single Agent Pattern**: One `unified_agent.py` handles all capabilities
- **Intent-Aware Routing**: Intelligent tool selection based on query analysis
- **Parallel Processing**: Concurrent execution of multiple strategies
- **Context Preservation**: Memory and knowledge graph integration

### 🔧 Modular Design
- **Separation of Concerns**: Clear boundaries between components
- **Dependency Injection**: Configurable service implementations
- **Plugin Architecture**: Extensible tool and provider systems
- **Type Safety**: Full Pydantic validation throughout

### 🚀 Production Excellence
- **Async Architecture**: Non-blocking operations throughout
- **Circuit Breakers**: Automatic failure detection and recovery
- **Comprehensive Monitoring**: Metrics, tracing, and structured logging
- **Security First**: Input validation, sandboxing, and access controls

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          User Interfaces                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐ │
│  │  Streamlit  │  │   FastAPI   │  │     CLI     │  │   Monitoring   │ │
│  │     UI      │  │   Server    │  │   Tools     │  │     Stack      │ │
│  └─────┬───────┘  └─────┬───────┘  └─────┬───────┘  └──────┬─────────┘ │
│        │                 │                 │                  │          │
└────────┼─────────────────┼─────────────────┼──────────────────┼──────────┘
         │                 │                 │                  │
┌────────▼─────────────────┼─────────────────┼──────────────────┼──────────┐
│     🧠 Unified Agent      │                 │                  │          │
│  ┌─────────────────────┐  │  ┌─────────────┐ │  ┌─────────────┐ │          │
│  │   Intent Analysis   │◄─┼──┤   Smart     │◄┼──┤   Tool      │◄┼──────────┘
│  │   & Routing         │  │  │  Search     │ │  │Orchestration│ │
│  └─────────────────────┘  │  └─────────────┘ │  └─────────────┘ │
└───────────────────────────┼─────────────────┼──────────────────┼──────────┘
                            │                 │                  │
┌───────────────────────────▼─────────────────┼──────────────────▼──────────┐
│              🔍 Search & Retrieval           │         🛠️ External Tools     │
│  ┌─────────────────┐  ┌─────────────────┐  │  ┌─────────────────┐  ┌─────┐ │
│  │   Vector RAG    │  │  Graph RAG      │  │  │   Web Search    │  │ SQL │ │
│  │   (Supabase)    │  │   (Neo4j)       │  │  │   (Multi-Prov)  │  │Query│ │
│  └─────────────────┘  └─────────────────┘  │  └─────────────────┘  └─────┘ │
└────────────────────────────────────────────┼────────────────────────────────┘
                                             │
┌────────────────────────────────────────────▼────────────────────────────────────┐
│                                 📊 Data Storage                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐ │
│  │   PostgreSQL    │  │     Neo4j       │  │     Redis       │  │     mem0   │ │
│  │   (Vectors)     │  │   (Knowledge    │  │   (Cache)       │  │  (Memory)  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └────────────┘ │
└────────────────────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Agent Layer (`src/agent/`)
**Purpose**: Central intelligence and tool orchestration

- **`unified_agent.py`**: Main agent implementation with all capabilities
- **`base.py`**: Base classes and type definitions
- **`intent_analyzer.py`**: Query intent classification and routing logic

**Key Features:**
- 5-strategy intent routing (VECTOR_HEAVY, GRAPH_HEAVY, HYBRID, TEMPORAL, ENTITY_FOCUSED)
- Parallel tool execution with result aggregation
- Context management and memory integration

### 2. Storage Layer (`src/agentic_rag/storage/`)
**Purpose**: Data persistence and retrieval systems

**PostgreSQL/Supabase:**
- Document content and metadata storage
- Vector embeddings (1536d OpenAI, 768d local)
- Full-text search capabilities
- Session and analytics data

**Neo4j + Graphiti:**
- Entity extraction and relationship mapping
- Temporal fact storage (episodes)
- Knowledge graph traversal and querying
- Entity resolution and deduplication

**Redis:**
- Query result caching
- Session state management
- Performance optimization

### 3. Interface Layer
**Purpose**: Multiple access patterns for different use cases

**Streamlit UI (`src/ui/`):**
- Interactive web interface with runtime modes
- Analytics dashboard with knowledge graph visualization
- File upload and export capabilities

**FastAPI Server (`src/api/`):**
- REST API with OpenAPI documentation
- WebSocket streaming support
- Circuit breaker and rate limiting
- Health checks and metrics endpoints

### 4. Tool Layer (`src/tools/`)
**Purpose**: Specialized capabilities and integrations

- **RAG Tools**: Document retrieval and similarity search
- **SQL Tools**: Database querying with validation
- **Web Search**: Multi-provider search integration
- **Code Execution**: Sandboxed Python execution
- **Image Analysis**: Vision model integration

## Data Flow Architecture

### Query Processing Flow

```
User Query → Intent Analysis → Tool Selection → Parallel Execution → Response Aggregation
     ↓              ↓              ↓              ↓              ↓
1. Query received → 2. Classify intent → 3. Route to tools → 4. Execute in parallel → 5. Combine results
   from UI/API       (5 strategies)     (vector/graph/hybrid)   (with caching)        (with context)
```

### Document Ingestion Flow

```
Documents → Preprocessing → Chunking → Embedding → Storage → Knowledge Extraction
    ↓           ↓           ↓         ↓         ↓          ↓
1. Upload → 2. Clean & → 3. Split → 4. Generate → 5. Store → 6. Extract entities
   files     normalize    into      vectors     in both    & relationships
                        chunks                 DBs
```

### Knowledge Graph Flow

```
Entity Extraction → Relationship Discovery → Fact Timeline → Graph Storage → Query Interface
       ↓                   ↓                    ↓             ↓              ↓
1. Identify entities → 2. Find connections → 3. Temporal → 4. Neo4j → 5. Graph traversal
   from text chunks      between entities     ordering     storage     & search
```

## Security Architecture

### Defense in Depth
- **Input Validation**: All user inputs validated at multiple layers
- **Sandboxed Execution**: Code execution in RestrictedPython environment
- **Access Controls**: Configurable permissions and rate limiting
- **Audit Logging**: Comprehensive security event tracking

### Data Protection
- **Encryption**: TLS for all external communications
- **Secrets Management**: Secure API key handling
- **Data Sanitization**: PII detection and redaction
- **Backup Security**: Encrypted backups with access controls

## Performance Architecture

### Scalability Design
- **Horizontal Scaling**: Stateless design supports multiple instances
- **Connection Pooling**: Efficient database connection management
- **Caching Strategy**: Multi-level caching (Redis + in-memory)
- **Async Processing**: Non-blocking operations throughout

### Resource Management
- **Memory Optimization**: Streaming for large document processing
- **CPU Efficiency**: Parallel processing and connection reuse
- **Network Optimization**: Connection pooling and request batching
- **Storage Efficiency**: Compressed vectors and optimized indexes

## Deployment Architecture

### Container Strategy
- **Multi-stage Builds**: Optimized production images
- **Health Checks**: Comprehensive container health monitoring
- **Service Discovery**: Automatic service registration and discovery
- **Configuration Management**: Environment-based configuration injection

### Monitoring Integration
- **Metrics Collection**: Prometheus metrics from all components
- **Distributed Tracing**: OpenTelemetry integration for request tracing
- **Log Aggregation**: Structured logging with correlation IDs
- **Alert Management**: Configurable alerting and notification system

## Architecture Documentation

- **[Full Architecture Reference](reference.md)** - Complete technical architecture documentation
- **[Agentic RAG System](agentic-rag.md)** - RAG architecture and search strategies
- **[Database & RAG Integration](database-and-rag.md)** - Database schemas and RAG workflows
- **[Architecture Diagrams](diagrams.md)** - Visual system diagrams and flows

## Next Steps

Explore detailed architecture documentation:
1. Start with [Agentic RAG](agentic-rag.md) for search architecture
2. Review [Database Integration](database-and-rag.md) for storage details
3. See [Diagrams](diagrams.md) for visual representations
4. Check [Full Reference](reference.md) for comprehensive details

## Quick Links

- [Back to Documentation Home](../README.md)
- [Configuration](../4-configuration/index.md)
- [Deployment](../6-deployment/index.md)

---

**Architecture Overview Complete** | Ready for detailed technical exploration
