# Architecture

## System Overview

The Base Agent architecture now incorporates an **Agentic RAG (Retrieval-Augmented Generation)** system that combines traditional vector search with knowledge graph capabilities for intelligent information retrieval and reasoning.

### Key Architectural Principles
- **Dual Storage Strategy**: PostgreSQL/Supabase for content, Neo4j for knowledge
- **Zero Content Duplication**: Neo4j stores only extracted entities and relationships
- **Intelligent Query Routing**: Automatic selection of optimal search strategy
- **Parallel Processing**: Concurrent vector and graph searches with result merging
- **Modular Design**: Pluggable components for easy extension and customization

## High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                           User Interface Layer                          │
│  ┌────────────┐     ┌────────────┐     ┌────────────┐                │
│  │  Streamlit │     │   FastAPI  │     │     CLI    │                │
│  └──────┬─────┘     └──────┬─────┘     └──────┬─────┘                │
│         └───────────────────┴───────────────────┘                      │
├────────────────────────────────────────────────────────────────────────┤
│                    Agent Intelligence Layer (Phase 3)                   │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │                    Pydantic AI Agent                          │     │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │     │
│  │  │ Intent       │→ │ Query Router │→ │  Response    │      │     │
│  │  │ Analyzer     │  │ (8 Intent    │  │  Generator   │      │     │
│  │  │ (Smart)      │  │  Types)      │  │  (Citations) │      │     │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │     │
│  └──────────────────────────────────────────────────────────────┘     │
├────────────────────────────────────────────────────────────────────────┤
│                         Tool Orchestration                              │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │ Smart Search  │ Vector Search │ Graph Search │ Comprehensive  │     │
│  │ Entity Lookup │ Timeline      │ Iterative   │ Hybrid Search   │     │
│  │ Web Search    │ Code Exec     │ SQL Query   │ Memory & Vision │     │
│  └──────────────────────────────────────────────────────────────┘     │
├────────────────────────────────────────────────────────────────────────┤
│                         Storage Architecture                            │
│                                                                         │
│  PostgreSQL/Supabase                    Neo4j + Graphiti               │
│  ┌─────────────────────────┐           ┌─────────────────────────┐    │
│  │ Documents (Full Content)│           │ Entities (Name/Type)    │    │
│  │ Chunks (Text+Embeddings)│←─────────→│ Relationships           │    │
│  │ Enhanced Metadata       │ Reference │ Episodes (Brief Facts)  │    │
│  │ Vector Index (pgvector) │   IDs     │ Temporal Properties     │    │
│  │ Entity References       │           │ Confidence Scores       │    │
│  └─────────────────────────┘           └─────────────────────────┘    │
│         Source of Truth                  Knowledge Graph Index         │
│        (99.6% Storage)                   (0.4% Storage Overhead)       │
└────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure
```
base_agent/
├── src/                       # Core agent implementation
│   ├── __init__.py            # Package initialization
│   ├── __main__.py            # Main entry point
│   ├── agent/                 # Agent core modules
│   │   ├── __init__.py        # Package initialization
│   │   ├── agent.py           # Main Pydantic AI agent with tool definitions
│   │   ├── base.py            # Base agent class
│   │   └── prompt.py          # System prompt configuration
│   ├── clients/               # Client factories for external services
│   │   ├── __init__.py        # Package initialization with exports
│   │   ├── database.py        # Supabase client configuration
│   │   ├── embedding.py       # Embedding client configuration
│   │   ├── llm.py             # LLM client configuration
│   │   └── memory.py          # Memory client configuration (mem0)
│   ├── tools/                 # Tool implementations
│   │   ├── __init__.py        # Package initialization with exports
│   │   ├── rag.py             # RAG/document retrieval tools
│   │   ├── web_search.py      # Web search integration
│   │   ├── image_analysis.py  # Vision model integration
│   │   ├── code_execution.py  # Sandboxed code execution
│   │   └── sql_query.py       # SQL query execution
│   ├── rag_pipeline/          # Document processing pipelines
│   │   ├── __init__.py        # Package initialization
│   │   ├── common/            # Shared utilities
│   │   │   ├── __init__.py    # Package initialization
│   │   │   ├── db_handler.py  # Database operations
│   │   │   └── text_processor.py # Text chunking and preprocessing
│   │   ├── sources/           # Data source integrations
│   │   │   ├── __init__.py    # Package initialization
│   │   │   ├── google_drive.py # Google Drive document sync
│   │   │   └── local_files.py  # Local filesystem document sync
│   │   └── pipeline.py        # Main pipeline orchestrator
│   ├── ui/                    # Web interface components
│   │   ├── __init__.py        # Package initialization
│   │   ├── README.md          # UI-specific documentation
│   │   ├── requirements.txt   # UI-specific requirements
│   │   ├── streamlit_app.py   # Main Streamlit application
│   │   ├── streamlit_ui_simple.py # Simple UI variant
│   │   └── streamlit_ui_streaming.py # Streaming UI variant
│   └── utils/                 # Utility modules
│       └── __init__.py        # Package initialization
├── src/agentic_rag/           # Agentic RAG implementation (Phase 3 Complete)
│   ├── __init__.py            # Package initialization
│   ├── config.py              # Configuration management
│   ├── agent/                 # Agent Intelligence Layer
│   │   ├── __init__.py        # Package initialization
│   │   ├── agent.py           # Main Pydantic AI agent with tools
│   │   ├── config.py          # Agent configuration and dependencies
│   │   ├── intent_analyzer.py # Intent analysis system (8 intent types)
│   │   ├── prompts.py         # System prompts for agent
│   │   ├── providers.py       # LLM provider configurations
│   │   ├── response_generator.py # Response generation with citations
│   │   ├── router.py          # Query routing and strategy selection
│   │   └── tools.py           # Advanced search tools implementation
│   ├── ingestion/             # Document processing pipeline
│   │   ├── __init__.py        # Package initialization
│   │   ├── chunker.py         # Semantic document chunking
│   │   ├── embedder.py        # Embedding generation with caching
│   │   ├── extractor.py       # Knowledge extraction using Graphiti
│   │   └── pipeline.py        # Main pipeline orchestrator
│   ├── search/                # Search strategies implementation
│   │   ├── __init__.py        # Package initialization
│   │   ├── base.py            # Base search interface
│   │   ├── graph.py           # Knowledge graph search
│   │   ├── hybrid.py          # Hybrid search (vector + graph)
│   │   ├── strategies.py      # Search strategy definitions
│   │   ├── vector.py          # Vector search implementation
│   │   └── weighted.py        # Result merging and ranking
│   └── storage/               # Storage layer abstractions
│       ├── __init__.py        # Package initialization
│       ├── base.py            # Base storage interface
│       ├── models.py          # Data models and schemas
│       ├── neo4j_store.py     # Neo4j operations
│       ├── postgres_store.py  # PostgreSQL operations
│       ├── schema.sql         # Enhanced database schema
│       └── utils.py           # Storage utilities
├── src/api/                   # API layer
│   ├── __init__.py            # Package initialization
│   └── main.py                # FastAPI application with endpoints
├── sql/                       # Database schema definitions
│   ├── documents.sql          # Vector document storage table
│   ├── document_metadata.sql  # Document metadata table
│   ├── document_rows.sql      # Tabular data storage
│   ├── execute_sql_rpc.sql    # Secure SQL execution function
│   └── agentic_rag/          # Agentic RAG schemas
│       └── schema.sql        # Enhanced PostgreSQL schema
├── tests/                     # Unit and integration tests
│   ├── __init__.py            # Package initialization
│   ├── conftest.py            # Test configuration
│   ├── test_agent.py          # Agent tests
│   ├── test_clients.py        # Client tests
│   ├── test_code_execution.py # Code execution tests
│   ├── test_image_analysis.py # Image analysis tests
│   ├── test_main.py           # Main tests
│   ├── test_rag.py            # RAG tests
│   ├── test_sql_query.py      # SQL query tests
│   ├── test_streamlit_app.py  # UI tests
│   ├── test_web_search.py     # Web search tests
│   └── rag_pipeline/          # RAG pipeline tests
│       ├── test_db_handler.py # Database handler tests
│       ├── test_pipeline.py   # Pipeline tests
│       ├── test_text_processor.py # Text processor tests
│       └── sources/           # Source-specific tests
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md        # System architecture
│   ├── CONFIGURATION.md       # Configuration guide
│   ├── DB_AND_RAG.md         # Database and RAG system
│   ├── INSTALL.md            # Installation instructions
│   ├── PRD.md                # Product requirements
│   ├── TASKS.md              # Task tracking
│   └── USAGE.md              # Usage guide
├── config/                    # Configuration files
├── docker/                    # Docker configuration
│   └── Dockerfile            # Container build instructions
└── supabase/                  # Supabase configuration
    ├── .gitignore            # Supabase gitignore
    ├── config.toml           # Supabase config
    └── .temp/                # Temporary files
```

## Database Architecture

### PostgreSQL/Supabase (Content Storage)
- **documents**: Full document content and metadata
- **chunks**: Document chunks with vector embeddings (1536 or 768 dimensions)
- **document_metadata**: File metadata, schemas, and source URLs
- **document_rows**: Structured data from CSV/Excel files as JSONB
- **mem0_memories**: Long-term conversation memory storage

### Neo4j (Knowledge Graph)
- **Entity Nodes**: Extracted entities (name, type) with chunk references
- **Relationships**: Entity connections with confidence scores
- **Episodes**: Temporal facts and events with timestamps
- **Properties**: Metadata and attributes without content duplication

### Data Flow
```
Document Ingestion:
─────────────────
Document → Chunk → Embed → Store in PostgreSQL
            ↓
      Extract Knowledge
            ↓
    ┌───────┴────────┐
    ↓                ↓
Entities          Facts
(names only)    (summaries)
    ↓                ↓
    └───────┬────────┘
            ↓
     Store in Neo4j
     (with chunk_id references)

Query Processing:
────────────────
User Query → Intent Analysis → Tool Selection
                                      ↓
                    ┌─────────────────┼─────────────────┐
                    ↓                 ↓                 ↓
            Vector Search      Graph Search      Hybrid Search
            (PostgreSQL)         (Neo4j)           (Both)
                    ↓                 ↓                 ↓
                    └─────────────────┼─────────────────┘
                                      ↓
                              Result Merging
                                      ↓
                              Response Generation
```

## Technical Components

### Client Architecture
- **Database Client**: Supabase client for PostgreSQL operations
- **Graph Client**: Neo4j driver with Graphiti wrapper for knowledge operations
- **Embedding Client**: Multi-provider embedding generation (OpenAI, Ollama, Nomic)
- **LLM Client**: Multi-provider language model support (OpenAI, Anthropic, Google, OpenRouter, Ollama)
- **Memory Client**: Mem0 integration for persistent memory

### Search Strategies

#### Vector Search (PostgreSQL)
- Semantic similarity using pgvector
- Returns actual document chunks
- Optimized for content discovery
- Sub-200ms response time

#### Graph Search (Neo4j)
- Entity and relationship traversal
- Returns facts and connections
- Optimized for relationship queries
- Sub-500ms response time

#### Hybrid Search
- Parallel execution of both strategies
- Intelligent result merging with boosting
- Graph context enhances vector results
- Best for complex queries

### Intent Analysis
The system analyzes query intent to determine optimal search strategy:
- **Relationship indicators**: "related", "connected", "works with"
- **Temporal indicators**: "timeline", "history", "when"
- **Fact indicators**: "specifically", "exactly", "detail about"

### Tool System
All tools are implemented as async functions and integrated via Pydantic AI's tool system:
- **RAG Tools**: Document retrieval, listing, and content access
- **Web Search**: Brave API primary, SearXNG fallback
- **Image Analysis**: Vision model integration via subagent
- **Code Execution**: RestrictedPython sandbox
- **SQL Query**: Secure read-only database queries

### Agent Implementation

#### Phase 3: Agent Intelligence Layer (Completed)

The Agent Intelligence Layer represents the completed Phase 3 implementation, featuring advanced query understanding and intelligent search orchestration:

**Intent Analysis System:**
- **8 Intent Types**: Factual, Relationship, Temporal, Comparison, Exploratory, Aggregation, Definition, Multi-hop
- **Entity Extraction**: Automatic identification of entities in queries
- **Temporal Context**: Detection of time-based queries
- **Complexity Scoring**: Determines optimal search strategy

**Query Routing Engine:**
- **Strategy Selection**: Intent-based routing to optimal search approach
- **Fallback Mechanisms**: Graceful degradation with alternative strategies
- **Performance Optimization**: Route queries for sub-2s response times
- **Confidence Metrics**: Track routing accuracy and effectiveness

**Response Generation:**
- **Citation Management**: Source tracking for all responses
- **Confidence Scoring**: 0.0-1.0 scale for answer reliability
- **Answer Synthesis**: Multi-source information merging
- **Follow-up Generation**: Intelligent next question suggestions

**Advanced Search Tools:**
- `smart_search`: Automatic strategy selection based on intent
- `vector_search`: Pure semantic similarity search
- `graph_search`: Knowledge graph traversal
- `comprehensive_search`: Multi-strategy parallel execution
- `iterative_search`: Multi-step refinement for complex queries
- `get_entity_relationships`: Deep entity exploration
- `get_entity_timeline`: Temporal information retrieval

**Performance Metrics Achieved:**
- Intent Classification: 90%+ accuracy
- Response Latency: <2s for 95% of queries
- Citation Rate: 100% of responses include sources
- Confidence Scoring: All responses include reliability scores

**Framework Details:**
- **Framework**: Pydantic AI with OpenAI-compatible providers
- **Context Management**: Dataclass-based dependency injection with enhanced session tracking
- **Memory Integration**: Automatic memory retrieval and storage with user isolation
- **Error Handling**: Built-in retry mechanisms and graceful degradation with fallback strategies
- **Tool Orchestration**: Intelligent parallel tool execution with result merging
