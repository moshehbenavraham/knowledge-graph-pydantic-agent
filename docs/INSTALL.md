# Installation

## System Requirements
- **Python**: 3.11 or higher
- **Database**: Supabase project with pgvector extension enabled
- **Memory**: 4GB+ RAM for local LLM deployment (if using Ollama)
- **OS**: Windows, macOS, or Linux

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

   **Supabase Setup (Required):**
   - Go to [Supabase](https://supabase.com/) and create a new project
   - Enable the `pgvector` extension in Database → Extensions
   - Get your project URL and service role key from Project Settings → API
   - Update `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in your `.env` file
   - **Execute SQL scripts in order** in the Supabase SQL Editor:
     1. [`sql/documents.sql`](../sql/documents.sql) - Vector storage with search function
     2. [`sql/document_metadata.sql`](../sql/document_metadata.sql) - Document metadata
     3. [`sql/document_rows.sql`](../sql/document_rows.sql) - Structured data storage
     4. [`sql/execute_sql_rpc.sql`](../sql/execute_sql_rpc.sql) - Secure SQL execution

   ```bash
   # Database setup helper (informational only)
   make db-setup
   ```

4. **Run the Application**
   ```bash
   # Start Streamlit UI
   make run-ui

   # Or run in development mode with auto-reload
   make dev

   # Access the web interface at http://localhost:8501
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
   - Edit [`src/agent/agent.py`](../src/agent/agent.py)
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

### Getting Help

- Check the [Configuration Guide](CONFIGURATION.md) for environment setup
- Review [Usage Documentation](USAGE.md) for feature usage
- See [Architecture Documentation](ARCHITECTURE.md) for system overview
- Check existing [GitHub Issues](https://github.com/your-repo/issues) for known problems
