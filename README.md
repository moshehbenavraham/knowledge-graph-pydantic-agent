# Base Agent - Production-Ready AI Assistant with Agentic RAG

Advanced AI agent implementation using Pydantic AI with **Agentic RAG (Retrieval-Augmented Generation)** system that combines PostgreSQL/Supabase for content storage with Neo4j knowledge graphs for intelligent search and reasoning. Features comprehensive tooling for document retrieval, memory management, web search, image analysis, and code execution with support for multiple LLM providers.

## 🚀 Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd base_agent

# Install dependencies
make setup

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run the application
make run-ui
```

Access the web interface at **http://localhost:8501**

## 🎯 Core Features

### Agent Capabilities
- **Agentic RAG System**: Advanced knowledge-graph enhanced retrieval with intelligent query routing
  - Vector search for semantic similarity (PostgreSQL/pgvector)
  - Graph search for relationships and facts (Neo4j/Graphiti)
  - Hybrid search combining both approaches
  - Intent-based search strategy selection
- **Long-term Memory**: Persistent conversation memory via mem0 with PostgreSQL backend
- **Web Search**: Internet search via Brave API or self-hosted SearXNG
- **Image Analysis**: Vision model integration for image content analysis
- **Code Execution**: Sandboxed Python code execution with RestrictedPython
- **SQL Query Execution**: Read-only database queries with security validation

### Technical Stack
- **Framework**: Pydantic AI ≥0.0.10 with async support
- **Vector Database**: Supabase with pgvector extension (content storage)
- **Knowledge Graph**: Neo4j with Graphiti (entity relationships and facts)
- **Memory Store**: mem0ai ≥0.0.10 with PostgreSQL backend
- **Embedding Models**:
  - OpenAI text-embedding-3-small (1536d)
  - Ollama nomic-embed-text (768d)
  - Support for multiple embedding models
- **LLM Support**: OpenAI GPT models, Anthropic Claude, OpenRouter providers, Google Gemini, Ollama local models
- **UI Framework**: Streamlit ≥1.29.0 + FastAPI for API endpoints
- **Security**: Custom sandboxed environment for safe code execution

## 📋 Requirements

- **Python**: 3.11 or higher
- **Database**:
  - Supabase project with pgvector extension enabled (content storage)
  - Neo4j 5.0+ instance (knowledge graph) - local or cloud
- **Memory**: 4GB+ RAM for local LLM deployment (if using Ollama)

## 🛠️ Installation

### Method 1: Standard Installation

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd base_agent
   ```

2. **Install Dependencies**
   ```bash
   make setup
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your service credentials:
   ```bash
   # Required: Supabase credentials
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_KEY=your_service_role_key

   # Required: LLM API key
   LLM_API_KEY=your_openai_api_key

   # Required: Embedding API key
   EMBEDDING_API_KEY=your_openai_api_key
   ```

4. **Database Setup**

   **PostgreSQL/Supabase (Content Storage):**
   - Create a Supabase project at [supabase.com](https://supabase.com)
   - Enable the `pgvector` extension in Database → Extensions
   - Run SQL scripts in order:
     - [`sql/documents.sql`](sql/documents.sql)
     - [`sql/document_metadata.sql`](sql/document_metadata.sql)
     - [`sql/document_rows.sql`](sql/document_rows.sql)
     - [`sql/execute_sql_rpc.sql`](sql/execute_sql_rpc.sql)
     - [`sql/agentic_rag/schema.sql`](sql/agentic_rag/schema.sql) (for Agentic RAG)

   **Neo4j (Knowledge Graph):**
   ```bash
   # Option A: Docker deployment
   docker run -d \
     --name neo4j \
     -p 7474:7474 -p 7687:7687 \
     -e NEO4J_AUTH=neo4j/password \
     neo4j:latest

   # Option B: Neo4j Aura cloud
   # Create instance at https://neo4j.com/cloud/aura/

   # Initialize knowledge graph
   python -m src.agentic_rag.storage.neo4j_store init
   ```

5. **Run Application**
   ```bash
   make run-ui
   ```

### Method 2: Docker Deployment

```bash
# Build and run with Docker Compose
make docker-build
make docker-run

# Access at http://localhost:8501
```

Docker services include:
- **App**: Streamlit UI on port 8501
- **SearXNG**: Web search engine on port 8080

## ⚙️ Configuration

### Agentic RAG Configuration

```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# Agentic RAG Settings
ENABLE_GRAPH=true              # Enable knowledge graph features
ENABLE_CACHING=true            # Enable result caching
PARALLEL_SEARCH=true           # Enable parallel search execution
CHUNK_SIZE=1000               # Document chunk size
CHUNK_OVERLAP=200             # Chunk overlap for context
MAX_ENTITIES_PER_CHUNK=10     # Entity extraction limit
MAX_FACT_LENGTH=500           # Maximum fact description length
```

### LLM Providers

**OpenAI (Default):**
```bash
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-api-key
LLM_CHOICE=gpt-4o-mini
```

**Local Ollama:**
```bash
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_CHOICE=llama3.1

# For Ollama embeddings, update SQL scripts:
# Change vector(1536) to vector(768) in sql/*.sql files
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL_CHOICE=nomic-embed-text
```

**OpenRouter:**
```bash
LLM_PROVIDER=openrouter
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your-openrouter-key
LLM_CHOICE=anthropic/claude-3-sonnet
```

### Feature Flags

```bash
ENABLE_CODE_EXECUTION=false      # Enable/disable code execution tool
ENABLE_WEB_SEARCH=true          # Enable/disable web search
ENABLE_IMAGE_ANALYSIS=true      # Enable/disable image analysis
ENABLE_LONG_TERM_MEMORY=true    # Enable/disable persistent memory
ENABLE_RAG=true                 # Enable/disable RAG functionality
```

### Search Providers

```bash
# Primary: Brave Search (recommended)
BRAVE_API_KEY=your_brave_api_key

# Fallback: Self-hosted SearXNG
SEARXNG_BASE_URL=http://localhost:8080
```

## 🤖 Agentic RAG System

The Agentic RAG system enhances traditional RAG with intelligent search routing and knowledge graph capabilities:

### Architecture Overview
- **PostgreSQL/Supabase**: Stores full document content and embeddings
- **Neo4j/Graphiti**: Stores extracted entities, relationships, and temporal facts
- **Zero Duplication**: Neo4j only stores knowledge references, not content
- **Intelligent Routing**: Automatically selects optimal search strategy based on query intent

### Search Strategies

1. **Vector Search**: For semantic similarity and content discovery
   - Uses pgvector for embedding-based search
   - Returns actual document chunks
   - Best for: General questions, content retrieval

2. **Graph Search**: For relationships and fact-finding
   - Queries Neo4j knowledge graph
   - Returns entities, relationships, and facts
   - Best for: Relationship queries, temporal questions

3. **Hybrid Search**: Combines both approaches
   - Parallel execution with intelligent merging
   - Graph context boosts relevant vector results
   - Best for: Complex queries requiring both content and relationships

### Running Agentic RAG

```bash
# Start the API server
python -m src.api.main

# Or use the CLI
python -m src.agentic_rag.agent.agent chat "Your question here"

# Ingest documents
python -m src.agentic_rag.ingestion.pipeline ingest path/to/documents
```

### API Endpoints

- `POST /ingest` - Ingest documents with knowledge extraction
- `POST /chat` - Chat with the agent
- `GET /search/{mode}` - Direct search (vector/graph/hybrid)
- `POST /chat/stream` - Streaming chat responses

## 🔧 Usage

### Web Interface

1. **Start the agent:**
   ```bash
   make run-ui
   # or
   streamlit run src/ui/streamlit_app.py
   ```

2. **Access:** http://localhost:8501

3. **Features:**
   - Real-time chat interface
   - File upload for document processing
   - Conversation history with persistent memory
   - Tool execution visibility and feedback

### Document Processing

**Supported Formats:**
- **Text**: `.txt`, `.md`, `.py`, `.js`, `.html`, `.css`
- **Documents**: `.pdf`, `.docx`
- **Spreadsheets**: `.csv`, `.xlsx` (structured data extraction)
- **Images**: `.jpg`, `.png`, `.gif` (vision analysis)

**Run RAG Pipeline:**
```bash
make run-rag
# or
python -m src.rag_pipeline.pipeline
```

### Available Tools

- **`retrieve_relevant_documents`**: Vector similarity search
- **`list_documents`**: Enumerate available documents
- **`get_document_content`**: Retrieve full document content
- **`execute_sql_query`**: Query structured data
- **`web_search`**: Internet search via Brave/SearXNG
- **`image_analysis`**: Vision model image analysis
- **`execute_code`**: Sandboxed Python execution

## 🧰 Development

### Available Commands

```bash
# Setup and dependencies
make setup              # Install dependencies and pre-commit hooks
make clean              # Clean Python cache files

# Code quality
make format             # Format code with Black and Ruff
make lint               # Run linting checks
make test               # Run test suite
make test-coverage      # Run tests with coverage
make security           # Run security scans
make check              # Run all checks (lint, test, security)

# Running services
make run-ui             # Start Streamlit UI
make run-rag            # Run document processing pipeline
make dev                # Development mode with auto-reload

# Docker
make docker-build       # Build Docker images
make docker-run         # Start Docker services
make docker-stop        # Stop Docker services

# Database (Informational)
make db-setup           # Show Supabase setup instructions
```

### Code Quality Tools

- **Linting**: Ruff with comprehensive rule set
- **Formatting**: Black with 100-character line length
- **Type Checking**: MyPy for static analysis
- **Security**: Bandit, Safety, pip-audit
- **Testing**: Pytest with async support and coverage
- **Pre-commit**: Automated code quality checks

## 📁 Project Structure

```
base_agent/
├── src/                        # Core application code
│   ├── __init__.py            # Package initialization
│   ├── __main__.py            # Main entry point
│   ├── agent/                  # Agent implementation
│   │   ├── __init__.py        # Package initialization
│   │   ├── agent.py            # Main Pydantic AI agent
│   │   ├── base.py             # Base agent class
│   │   └── prompt.py           # System prompts
│   ├── clients/                # External service clients
│   │   ├── __init__.py        # Package initialization with exports
│   │   ├── database.py         # Supabase client
│   │   ├── embedding.py        # Embedding client factory
│   │   ├── llm.py              # LLM client factory
│   │   └── memory.py           # Memory client (mem0)
│   ├── tools/                  # Agent tools
│   │   ├── __init__.py        # Package initialization with exports
│   │   ├── rag.py              # Document retrieval tools
│   │   ├── web_search.py       # Web search integration
│   │   ├── image_analysis.py   # Image analysis tools
│   │   ├── code_execution.py   # Code execution tools
│   │   └── sql_query.py        # SQL query tools
│   ├── rag_pipeline/           # Document processing
│   │   ├── __init__.py        # Package initialization
│   │   ├── common/             # Shared utilities
│   │   │   ├── __init__.py    # Package initialization
│   │   │   ├── db_handler.py   # Database operations
│   │   │   └── text_processor.py # Text preprocessing
│   │   ├── sources/            # Data source integrations
│   │   │   ├── __init__.py    # Package initialization
│   │   │   ├── google_drive.py # Google Drive integration
│   │   │   └── local_files.py  # Local file processing
│   │   └── pipeline.py         # Main orchestrator
│   ├── ui/                     # Web interfaces
│   │   ├── __init__.py        # Package initialization
│   │   ├── README.md          # UI documentation
│   │   ├── requirements.txt   # UI-specific requirements
│   │   ├── streamlit_app.py    # Main Streamlit UI
│   │   ├── streamlit_ui_simple.py     # Simple variant
│   │   └── streamlit_ui_streaming.py  # Streaming variant
│   └── utils/                  # Utility modules
│       └── __init__.py        # Package initialization
├── src/agentic_rag/               # Agentic RAG implementation
│   ├── __init__.py            # Package initialization
│   ├── config.py              # Configuration management
│   ├── agent/                 # Agent Intelligence Layer
│   │   ├── __init__.py        # Package initialization
│   │   ├── agent.py           # Pydantic AI agent with tools
│   │   ├── config.py          # Agent configuration
│   │   ├── intent_analyzer.py # Intent analysis system
│   │   ├── prompts.py         # System prompts
│   │   ├── providers.py       # LLM providers
│   │   ├── response_generator.py # Response generation
│   │   ├── router.py          # Query routing
│   │   └── tools.py           # Search tools
│   ├── ingestion/             # Document ingestion pipeline
│   │   ├── __init__.py        # Package initialization
│   │   ├── chunker.py         # Semantic chunking
│   │   ├── embedder.py        # Embedding generation
│   │   ├── extractor.py       # Knowledge extraction
│   │   └── pipeline.py        # Pipeline orchestrator
│   ├── search/                # Search implementations
│   │   ├── __init__.py        # Package initialization
│   │   ├── base.py            # Base search interface
│   │   ├── graph.py           # Graph search
│   │   ├── hybrid.py          # Hybrid search
│   │   ├── strategies.py      # Search strategies
│   │   ├── vector.py          # Vector search
│   │   └── weighted.py        # Weighted result merging
│   └── storage/               # Storage implementations
│       ├── __init__.py        # Package initialization
│       ├── base.py            # Base storage interface
│       ├── models.py          # Data models
│       ├── neo4j_store.py     # Neo4j operations
│       ├── postgres_store.py  # PostgreSQL operations
│       ├── schema.sql         # Enhanced database schema
│       └── utils.py           # Storage utilities
├── sql/                        # Database schemas
│   ├── documents.sql          # Vector document storage
│   ├── document_metadata.sql  # Document metadata table
│   ├── document_rows.sql      # Tabular data storage
│   ├── execute_sql_rpc.sql    # Secure SQL execution function
│   └── agentic_rag/           # Agentic RAG schemas
│       └── schema.sql         # Enhanced PostgreSQL schema
├── tests/                      # Test suite
│   ├── __init__.py            # Package initialization
│   ├── conftest.py            # Test configuration
│   ├── test_*.py              # Individual test modules
│   └── rag_pipeline/          # RAG pipeline tests
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md        # System architecture
│   ├── CONFIGURATION.md       # Configuration guide
│   ├── DB_AND_RAG.md         # Database and RAG details
│   ├── INSTALL.md            # Installation guide
│   ├── USAGE.md              # Usage instructions
│   └── projects_ongoing/      # Project tracking
│       ├── AGENTIC_RAG_HIGH_LEVEL.md  # High-level design
│       └── AGENTIC_RAG_PHASE_*.md     # Implementation phases
├── config/                     # Configuration files
├── docker/                     # Container configuration
│   └── Dockerfile            # Container build instructions
└── supabase/                   # Supabase configuration
    ├── .gitignore            # Supabase gitignore
    ├── config.toml           # Supabase config
    └── .temp/                # Temporary files
```

## 🔍 Advanced Features

### Code Execution Options

**Option 1: Built-in Sandbox (Default)**
- Uses RestrictedPython with whitelisted modules
- No file system or network access
- Core Python libraries included

**Option 2: MCP Code Execution Server**
1. Install Deno: https://deno.land/
2. Run MCP server:
   ```bash
   deno run -N -R=node_modules -W=node_modules --node-modules-dir=auto jsr:@pydantic/mcp-run-python sse
   ```
3. Enable in `src/agent/agent.py` (see comments)

### Google Drive Integration

1. **Setup Google Cloud Project**
   - Enable Drive API
   - Create OAuth 2.0 credentials

2. **Configure Environment**
   ```bash
   GOOGLE_DRIVE_FOLDER_ID=your_folder_id
   GOOGLE_DRIVE_CREDENTIALS_PATH=config/google_credentials.json
   ```

3. **Features**
   - Automatic document monitoring
   - OAuth 2.0 authentication
   - Binary file support

## 🧠 Memory System

The agent uses **mem0** for persistent memory:
- **Session Memory**: Temporary conversation context
- **Long-term Memory**: Persistent across sessions
- **User Isolation**: Separate memory per user
- **Deduplication**: Automatic similar memory removal

## 🛡️ Security

- **Sandboxed Execution**: RestrictedPython for code execution
- **SQL Injection Protection**: Parameterized queries and validation
- **API Key Security**: Environment variable storage
- **Read-only Database**: SQL queries restricted to SELECT operations

## 📊 Monitoring

The agent includes comprehensive logging and error handling:
- **Structured Logging**: JSON format with context
- **Error Tracking**: Detailed error messages and stack traces
- **Performance Metrics**: Response times and resource usage

## 🐛 Troubleshooting

### Common Issues

**Import Errors:**
```bash
make clean
make setup
```

**Database Connection:**
- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`
- Ensure pgvector extension is enabled
- Check SQL scripts execution

**Docker Issues:**
```bash
make docker-stop
docker system prune -f
make docker-build
make docker-run
```

**Memory Issues:**
- Check mem0 configuration
- Verify database connectivity
- Review memory retention settings

## 📚 Documentation

- **[Architecture](docs/ARCHITECTURE.md)**: System design and structure
- **[Installation](docs/INSTALL.md)**: Detailed setup instructions
- **[Configuration](docs/CONFIGURATION.md)**: Environment and settings
- **[Usage](docs/USAGE.md)**: User guides and examples
- **[Database & RAG](docs/DB_AND_RAG.md)**: Database setup and RAG system
- **[PRD](docs/PRD.md)**: Product requirements and specifications
- **[Tasks](docs/TASKS.md)**: Development tasks and progress

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/new-feature`
3. **Install development dependencies**: `make setup`
4. **Make changes and test**: `make check`
5. **Commit changes**: `git commit -m "feat: add new feature"`
6. **Push branch**: `git push origin feature/new-feature`
7. **Create Pull Request**

### Development Workflow

- **Code Style**: Black + Ruff formatting
- **Testing**: Pytest with >75% coverage requirement
- **Security**: Bandit security scanning
- **Pre-commit**: Automated quality checks

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[Pydantic AI](https://github.com/pydantic/pydantic-ai)**: Core agent framework
- **[Supabase](https://supabase.com)**: Database and vector storage
- **[mem0](https://mem0.ai)**: Memory management system
- **[Streamlit](https://streamlit.io)**: Web interface framework

## 📧 Support

For questions, issues, or contributions:
- **Issues**: Create a GitHub issue
- **Discussions**: Use GitHub Discussions
- **Documentation**: Check the `docs/` directory

---

**Version**: 0.7.1
**Last Updated**: December 2024
**Status**: Phase 3 Complete - Agent Intelligence Layer with Intent Analysis
