# Installation

## ⚠️ Choose Your Deployment Path

**Before installing, decide which features you need:**

### 🌐 Option A: Lightweight Cloud-Only (Recommended for Getting Started)

**Install:** `pip install -e .[dev]` (253 packages, ~500MB, 5 minutes)

**Resources Required:**
- 500MB disk space
- 2GB RAM
- Python 3.11+

**What You Get:**
- ✅ Full AI assistant with streaming chat
- ✅ Vector search (Supabase pgvector)
- ✅ OpenAI embeddings (via API)
- ✅ Web search, image analysis, SQL queries, code execution
- ✅ Conversation memory (mem0)
- ❌ No knowledge graph
- ❌ No local embeddings

**Best for:** Quick setup, testing, production deployment, cost-sensitive projects

---

### 🧠 Option B: Full Agentic RAG (Advanced Features)

**Install:** `pip install -e .[dev,rag]` (303 packages, ~5.5GB, 15 minutes)

**Resources Required:**
- **5.5GB disk space** (includes 3.7GB of PyTorch + CUDA)
- **8GB+ RAM** (PyTorch memory overhead)
- Python 3.11+

**What You Get:**
- ✅ Everything from Option A, plus:
- ✅ Knowledge graph (Neo4j + Graphiti)
- ✅ Entity extraction & relationship discovery
- ✅ Temporal reasoning (facts with timestamps)
- ✅ Local embeddings (sentence-transformers)
- ✅ Document parsing (PDFs, DOCX via unstructured)

**Best for:** Research, advanced RAG features, offline embeddings, entity-centric queries

**⚠️ Note:** Downloads 3.7GB of CUDA libraries (PyTorch includes GPU support by default)
- **With NVIDIA GPU:** Utilized for 10-50x faster embeddings (run `nvidia-smi` to check)
- **CPU-only:** Unused bloat, but harmless

---

## System Requirements

### Hardware Requirements (Option A - Lightweight)
- **Python**: 3.11 or higher
- **Memory**: 2GB+ RAM (4GB recommended)
- **Storage**: 500MB+ free space
- **Network**: Internet connection for LLM providers and web search
- **OS**: Windows, macOS, or Linux

### Hardware Requirements (Option B - Full RAG)
- **Python**: 3.11 or higher
- **Memory**: 8GB+ RAM (for PyTorch + transformers)
- **Storage**: 6GB+ free space (5.5GB for packages)
- **Network**: Internet connection for cloud services
- **OS**: Windows, macOS, or Linux

### Database Requirements
- **PostgreSQL/Supabase**: Primary storage with pgvector extension (**required for both options**)
- **Neo4j 5.0+**: Knowledge graph (**optional** - only needed for Option B)
- **Vector Dimensions**: 1536 (OpenAI) or 768 (Ollama) embeddings support

**Note:** Neo4j setup is optional. The system works fully without it (Option A), you just won't have knowledge graph features.

## Quick Start

1. **Clone and Setup Environment**
   ```bash
   git clone <repository-url>
   cd base_agent
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Choose Your Installation Path**

   **Option A: Lightweight (Recommended first)**
   ```bash
   # Install with UV (faster) or pip
   pip install uv  # Optional but 30x faster
   uv pip install -e .[dev]
   # OR: pip install -e .[dev]

   # Install pre-commit hooks
   pre-commit install
   ```

   **Option B: Full RAG (5.5GB download)**
   ```bash
   # Install with UV (recommended for large installs)
   pip install uv
   uv pip install -e .[dev,rag]

   # Install pre-commit hooks
   pre-commit install
   ```

2. **Configure Environment Variables**
   ```bash
   # Copy example configuration
   cp .env.example .env

   # Edit .env with your service credentials
   # The system uses a centralized Pydantic configuration with validation

   # Required settings:
   # - SUPABASE_URL and SUPABASE_SERVICE_KEY (or DATABASE_URL)
   # - LLM_API_KEY and LLM_PROVIDER
   # - EMBEDDING_API_KEY and EMBEDDING_PROVIDER

   # The configuration system will validate all settings on startup
   ```

3. **Database Setup**

   **PostgreSQL/Supabase Setup (Required):**
   - Go to [Supabase](https://supabase.com/) and create a new project
   - Enable the `pgvector` extension in Database → Extensions
   - Get your project URL and service role key from Project Settings → API
   - Update `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in your `.env` file
   - **Get PostgreSQL connection string** from Project Settings → Database → Connection string:
     ```env
     # For WSL2 or IPv4-only networks, use Session pooler (recommended):
     # Important: URL-encode special characters in password (? → %3F, $ → %24, @ → %40)
     DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-[REGION].pooler.supabase.com:5432/postgres

     # Example for us-east-2 region:
     DATABASE_URL=postgresql://postgres.hokdgtbedrsenvldxbyx:your%3Fpass%24word@aws-1-us-east-2.pooler.supabase.com:5432/postgres

     # Direct connection (IPv6 only, not compatible with WSL2):
     DATABASE_URL=postgresql://postgres:your%3Fpass%24word@db.your-project.supabase.co:5432/postgres

     # Note: Transaction pooler (port 6543) may timeout on WSL2 - use Session pooler (port 5432)
     ```
   - **Execute single migration file** in the Supabase SQL Editor:
     - Go to SQL Editor → New Query
     - Copy contents of [`src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql`](../../src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql)
     - Paste and run
     - This creates all tables (documents, chunks, sessions, messages, search_cache, graph_sync_queue), indexes, functions, and triggers

   **Neo4j Setup (For Agentic RAG - Optional):**
   ```bash
   # Option A: Local Docker deployment
   docker run -d \
     --name neo4j \
     -p 7474:7474 -p 7687:7687 \
     -e NEO4J_AUTH=neo4j/password \
     neo4j:latest

   # Option B: Neo4j Aura cloud
   # Create instance at https://neo4j.com/cloud/aura/
   # Copy connection details to .env

   # Initialize knowledge graph
   python -m src.agentic_rag.storage.neo4j_store init
   ```

   **Environment Variables for Agentic RAG:**
   ```bash
   # Neo4j configuration
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your-password

   # Agentic RAG settings
   ENABLE_GRAPH=true
   PARALLEL_SEARCH=true
   CHUNK_SIZE=1000
   MAX_ENTITIES_PER_CHUNK=10
   ```

   ```bash
   # Database setup helper (informational only)
   make db-setup
   ```

4. **Run the Application**
   ```bash
   # Start Streamlit UI (includes Phase 3 features)
   make run-ui

   # Or run in development mode with auto-reload
   make dev

   # Access the web interface at http://localhost:8501

   # For Agentic RAG API server (Phase 3)
   python -m src.api.main
   # API available at http://localhost:8058 with intent analysis

   # For Agentic RAG CLI with smart search
   python -m src.agentic_rag.agent.agent chat "Your question"

   # Test Phase 3 features
   python -m src.agentic_rag.agent.agent chat "How is Microsoft related to OpenAI?"
   ```

5. **Ingest Documents (Agentic RAG)**

   **Storage Backend Options:**

   The system supports two storage backends with intelligent fallback:

   - **PostgreSQL (Primary)**: Direct database connection - faster, with connection pooling
   - **REST API (Fallback)**: HTTPS-based - works when PostgreSQL ports blocked

   ```bash
   # Default: Tries PostgreSQL, auto-falls back to REST API if connection fails
   make ingest

   # Or with custom document path:
   python -m src.agentic_rag.ingestion ingest --path /path/to/documents

   # Force REST API mode (skip PostgreSQL attempt):
   python -m src.agentic_rag.ingestion ingest --rest-api

   # With verbose logging:
   python -m src.agentic_rag.ingestion ingest --verbose
   ```

   **Test documents included:**
   ```bash
   # Ingest example documents (21 AI industry articles)
   make ingest
   # Uses: docs/example_big_tech_docs_for_ingestion_testing/
   ```

   **Verify ingestion:**
   ```bash
   # Test PostgreSQL connectivity
   python test_db_connection.py

   # Test REST API connectivity
   python test_supabase_rest.py
   ```

   **When to use each backend:**
   - **Auto (recommended)**: Let system choose based on network availability
   - **PostgreSQL**: Production, local development, Docker (when ports 5432/6543 accessible)
   - **REST API**: Corporate VPNs, restrictive firewalls, WSL2 with IPv6 issues

## Deployment Options

### Cloud Deployment
**Required Services:**
- Supabase project with pgvector enabled
- Neo4j Aura instance (for Agentic RAG)
- OpenAI API key or alternative LLM provider
- Brave Search API key (optional: uses SearXNG fallback)

### Local Deployment with Ollama
**Required Software:**
- [Ollama](https://ollama.ai/) for local LLM
- [SearXNG](https://github.com/searxng/searxng) for web search
- Supabase project (cloud database)
- Neo4j Docker container (for Agentic RAG)

**Ollama Setup for Agentic RAG (Phase 3):**
```bash
# Install required models
ollama pull llama3.1
ollama pull nomic-embed-text

# Update .env for Phase 3
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_CHOICE=llama3.1
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL_CHOICE=nomic-embed-text

# Phase 3 specific settings
ENABLE_INTENT_ANALYSIS=true
ENABLE_SMART_ROUTING=true
EXTRACTION_MODEL=llama3.1

# Important: Change vector dimensions in SQL from 1536 to 768
# This affects: documents.sql, chunks table, and hybrid search functions
```

### Docker Deployment

**Prerequisites:**
- Docker and Docker Compose installed

**Build and Run:**
```bash
# Build the Docker images
make docker-build

# Start all services (app + SearXNG)
make docker-run

# Stop services
make docker-stop
```

**Docker Services:**
- **App**: Streamlit UI on port 8501
- **SearXNG**: Web search engine on port 8080

## Development Setup

### Available Make Commands

**Core Development:**
```bash
make setup          # Install dependencies and pre-commit hooks
make format          # Format code with Black and Ruff
make lint           # Check code style and types
make test           # Run test suite
make test-coverage  # Run tests with coverage report
make security       # Run security scans (Bandit, Safety, pip-audit)
make check          # Run all checks (lint, type, test)
```

**Running Services:**
```bash
make run-ui         # Start Streamlit UI
make run-rag        # Run RAG pipeline
make dev            # Development mode with auto-reload
```

**Docker Commands:**
```bash
make docker-build   # Build Docker images
make docker-run     # Start Docker services
make docker-stop    # Stop Docker services
```

### Optional: Enhanced Code Execution with MCP

For enhanced code execution capabilities beyond the built-in sandbox:

1. **Install Deno:**
   ```bash
   # macOS/Linux
   curl -fsSL https://deno.land/x/install/install.sh | sh

   # Windows
   iwr https://deno.land/x/install/install.ps1 -useb | iex
   ```

2. **Start MCP Server:**
   ```bash
   deno run -N -R=node_modules -W=node_modules --node-modules-dir=auto jsr:@pydantic/mcp-run-python sse
   ```

3. **Configure Agent:**
   - Edit [`src/agent/unified_agent.py`](../../src/agent/unified_agent.py)
   - Add MCP server configuration (see comments in the file)
   - Comment out the built-in `execute_code` tool (lines 187-201)

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Clean and reinstall dependencies
make clean
make setup

# If issues persist, reinstall in development mode
python -m pip install -e .[dev]
```

**Database Connection Issues:**
- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in `.env`
- Ensure pgvector extension is enabled: `CREATE EXTENSION IF NOT EXISTS vector;`
- Check that all 4 SQL scripts have been executed in order
- Verify service role key permissions in Supabase dashboard

**Environment Variable Issues:**
```bash
# Verify environment file exists
ls -la .env

# Check required variables are set
grep -E "SUPABASE_URL|LLM_API_KEY|EMBEDDING_API_KEY" .env
```

**Docker Issues:**
```bash
# Reset Docker environment
make docker-stop
docker system prune -f
make docker-build
make docker-run
```

**Dependency Issues:**
```bash
# Update pip and reinstall
python -m pip install --upgrade pip
make clean
make setup
```

**Pre-commit Issues:**
```bash
# Reinstall pre-commit hooks
pre-commit uninstall
pre-commit install

# Or skip pre-commit for testing
git commit --no-verify
```

### Verifying Phase 3 Installation

After installation, verify that all Phase 3 features are working:

```bash
# Test intent analysis and smart search
python -c "
from EXAMPLE_agentic_rag_knowledge_graph.agent import AgenticRAGAgent
import asyncio

async def test():
    agent = AgenticRAGAgent()
    response = await agent.chat('How are companies using AI?')
    print(f'Intent: {response.intent}')
    print(f'Strategy: {response.search_strategy}')
    print(f'Confidence: {response.confidence}')

asyncio.run(test())
"

# Expected output should show:
# Intent: EXPLORATORY or FACTUAL
# Strategy: COMPREHENSIVE or HYBRID
# Confidence: 0.7-0.9
```

**Phase 3 Feature Checklist:**
- ✅ Intent analysis working (8 intent types)
- ✅ Smart search routing operational
- ✅ Confidence scoring enabled
- ✅ Citation management active
- ✅ Response generation with follow-ups
- ✅ Entity and relationship extraction
- ✅ Temporal fact processing

### Getting Help

- Check the [Configuration Guide](../4-configuration/environment.md) for environment setup
- Review [Usage Documentation](../5-guides/usage.md) for feature usage
- See [Architecture Documentation](../3-architecture/index.md) for system overview
- View [Examples](../5-guides/examples.md) for Phase 3 usage patterns
- Check existing [GitHub Issues](https://github.com/your-repo/issues) for known problems
