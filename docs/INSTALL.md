# Installation

## System Requirements
- Python 3.11 or higher
- Supabase project with pgvector extension enabled
- 4GB+ RAM for local LLM deployment (if using Ollama)

## Quick Start

1. **Clone and Setup Environment**
   ```bash
   git clone <repository-url>
   cd base_agent

   # Install dependencies with development tools
   make setup

   # This runs: python -m pip install -e .[dev] && pre-commit install
   ```

2. **Configure Environment Variables**
   ```bash
   # Copy example configuration
   cp .env.example .env

   # Edit .env with your service credentials
   # Required: SUPABASE_URL, SUPABASE_SERVICE_KEY, LLM_API_KEY, EMBEDDING_API_KEY
   ```

3. **Database Setup**
   ```bash
   # Using Makefile helper (informational only)
   make db-setup
   ```

   **Manual Supabase Setup:**
   - Go to [Supabase](https://supabase.com/) and create a new project
   - Enable the `pgvector` extension in Database → Extensions
   - Get your project URL and service role key from Project Settings → API
   - Update `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in your `.env` file
   - Run the SQL scripts in order:
     1. [`sql/documents.sql`](../sql/documents.sql)
     2. [`sql/document_metadata.sql`](../sql/document_metadata.sql)
     3. [`sql/document_rows.sql`](../sql/document_rows.sql)
     4. [`sql/execute_sql_rpc.sql`](../sql/execute_sql_rpc.sql)

4. **Run the Application**
   ```bash
   # Start Streamlit UI
   make run-ui

   # Or run in development mode with auto-reload
   make dev
   ```

## Deployment Options

### Cloud Deployment
**Required Services:**
- Supabase project with pgvector enabled
- OpenAI API key or OpenRouter account
- Brave Search API key (optional: uses SearXNG fallback)

### Local Deployment with Ollama
**Required Software:**
- [Ollama](https://ollama.ai/) for local LLM
- [SearXNG](https://github.com/searxng/searxng) for web search
- Supabase project (cloud database)

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

### Optional: MCP Code Execution Server

For enhanced code execution capabilities:

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

3. **Enable in Agent:**
   Uncomment the MCP configuration lines in [`src/agent/agent.py`](../src/agent/agent.py:56)

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Reinstall in development mode
make clean
make setup
```

**Database Connection Issues:**
- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in `.env`
- Ensure pgvector extension is enabled in Supabase
- Check that all SQL scripts have been executed

**Docker Issues:**
```bash
# Reset Docker environment
make docker-stop
docker system prune -f
make docker-build
make docker-run
```

**Pre-commit Issues:**
```bash
# Reinstall pre-commit hooks
pre-commit uninstall
pre-commit install
```
