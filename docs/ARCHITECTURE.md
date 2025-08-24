# Architecture

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
├── sql/                       # Database schema definitions
│   ├── documents.sql          # Vector document storage table
│   ├── document_metadata.sql  # Document metadata table
│   ├── document_rows.sql      # Tabular data storage
│   └── execute_sql_rpc.sql    # Secure SQL execution function
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

## Database Schema
- **documents**: Vector embeddings with pgvector (1536 or 768 dimensions)
- **document_metadata**: File metadata, schemas, and source URLs
- **document_rows**: Structured data from CSV/Excel files as JSONB
- **mem0_memories**: Long-term conversation memory storage

## Technical Components

### Client Architecture
- **Database Client**: Supabase client for PostgreSQL operations
- **Embedding Client**: OpenAI-compatible embedding generation
- **LLM Client**: Multi-provider language model support (OpenAI, OpenRouter, Ollama)
- **Memory Client**: Mem0 integration for persistent memory

### Tool System
All tools are implemented as async functions and integrated via Pydantic AI's tool system:
- **RAG Tools**: Document retrieval, listing, and content access
- **Web Search**: Brave API primary, SearXNG fallback
- **Image Analysis**: Vision model integration via subagent
- **Code Execution**: RestrictedPython sandbox
- **SQL Query**: Secure read-only database queries

### Agent Implementation
- **Framework**: Pydantic AI with OpenAI-compatible providers
- **Context Management**: Dataclass-based dependency injection
- **Memory Integration**: Automatic memory retrieval and storage
- **Error Handling**: Built-in retry mechanisms and graceful degradation
