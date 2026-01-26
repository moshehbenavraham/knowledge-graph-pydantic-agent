# Complete Installation Guide

Detailed setup instructions for Knowledge Graph Pydantic Agent with all features enabled.

## System Requirements

### Hardware
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 2GB base + 5GB for full RAG features
- **Network**: Internet connection for API services

### Software
- **Python 3.11+** (3.12 recommended)
- **Git** for version control
- **Make** for build automation
- **Docker** (optional, for containerized deployment)

## Installation Methods

### Option 1: Full Installation (Recommended)

```bash
git clone <repository-url>
cd knowledge-graph-pydantic-agent
pip install -e .[dev,rag]  # Or: make setup
```

**Includes:** Runtime dependencies, development tools, RAG components, documentation tools

### Option 2: Lightweight Installation

For testing without knowledge graph features:

```bash
pip install -e .[dev]
```

**Note:** Excludes local embeddings and knowledge graph features. Upgrade later if needed.

## Environment Configuration

### 1. Copy Configuration Template

```bash
cp .env.example .env
```

### 2. Configure Core Services

Edit `.env` with your credentials:

#### Database (Choose One)

**Supabase (Recommended):**
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
```

**Direct PostgreSQL:**
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/kgpa
```

#### LLM Provider (Choose One)

**OpenAI (Recommended):**
```bash
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-openai-api-key
LLM_MODEL=gpt-4o-mini
```

**Anthropic Claude:**
```bash
LLM_PROVIDER=anthropic
LLM_API_KEY=your-anthropic-api-key
LLM_MODEL=claude-3-5-sonnet-20241022
```

**Ollama (Local):**
```bash
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama2:7b  # your installed model
```

#### Embedding Provider
```bash
EMBEDDING_PROVIDER=openai  # or ollama for local
EMBEDDING_API_KEY=your-openai-api-key
EMBEDDING_MODEL=text-embedding-3-small
```

### 3. Optional Enhancements

#### Knowledge Graph (Neo4j)

```bash
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password
```

#### Performance Caching (Redis)

```bash
REDIS_URL=redis://localhost:6379
ENABLE_REDIS_CACHE=true
```

#### Web Search Integration

```bash
# Choose one or more providers
JINA_API_KEY=your-jina-api-key
BRAVE_API_KEY=your-brave-api-key
SEARXNG_BASE_URL=http://localhost:8080
```

## Database Initialization

### PostgreSQL/Supabase Setup

Run the database migration to create all required tables:

```bash
# Option 1: Using the migration runner
python -c "
import asyncio
from src.agentic_rag.storage.migrations.sql_runner import run_migration

async def init():
    await run_migration('src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql')

asyncio.run(init())
"

# Option 2: Manual SQL execution
# Copy and run the SQL file in your Supabase SQL Editor:
# src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql
```

**What gets created:**
- Document storage tables with vector indexes
- User session management
- Tool execution logs
- Analytics and metrics tables

### Neo4j Knowledge Graph (Optional)

```bash
# Initialize Neo4j database
make neo4j-init

# Or manually:
python -m src.agentic_rag.storage.migrations.neo4j_init
```

## Verification Steps

### 1. Test Database Connections

```bash
# Test Supabase connection
python -c "
from src.clients.database import DatabaseClient
client = DatabaseClient()
print('✅ Supabase connection successful')
"

# Test Neo4j connection (if configured)
python scripts/test_neo4j_connection.py
```

### 2. Test LLM Integration

```bash
# Test LLM provider
python -c "
from src.clients.llm import LLMClient
client = LLMClient()
response = client.complete('Hello, world!')
print(f'✅ LLM response: {response[:100]}...')
"
```

### 3. Test Embedding Generation

```bash
# Test embedding provider
python -c "
from src.clients.embedding import EmbeddingClient
client = EmbeddingClient()
embedding = client.embed('Test document content')
print(f'✅ Embedding generated: {len(embedding)} dimensions')
"
```

## Application Startup

### Web Interface

```bash
# Start Streamlit UI
make run-ui

# Available modes:
make run-ui-simple     # Lightweight mode
make run-ui            # Standard mode (default)
make run-ui-advanced   # Full features with memory and MCP
```

Access at: `http://localhost:8501`

### API Server

```bash
# Start FastAPI server
make run-api
```

API available at: `http://localhost:8058`
- Interactive docs: `http://localhost:8058/docs`
- Health check: `http://localhost:8058/health`

### Development Mode

```bash
# Auto-reload for development
make dev
```

## Post-Installation Tasks

### 1. Upload Sample Data (Optional)

```bash
# Ingest sample documents for testing
python -m src.agentic_rag.ingestion ingest --sample-data
```

### 2. Configure Monitoring (Optional)

```bash
# Start monitoring stack
make monitoring-up

# Access Grafana: http://localhost:3000
# Access Prometheus: http://localhost:9090
# Access Jaeger: http://localhost:16686
```

### 3. Set Up SSL/HTTPS (Production)

For production deployments, configure SSL certificates and update:

```bash
# In .env
API_HOST=0.0.0.0
API_PORT=8058
CORS_ORIGINS=https://yourdomain.com
```

## Docker Deployment

### Using Docker Compose

```bash
# Build and run with Docker
make docker-build
make docker-run
```

**What's included:**
- Knowledge Graph Pydantic Agent application container
- PostgreSQL database
- Redis cache
- Neo4j knowledge graph
- Monitoring stack (Prometheus, Grafana, Jaeger)

### Production Docker

```bash
# Production build
docker build -f docker/Dockerfile.production -t kgpa-ai-agent:prod .

# Run with docker-compose
docker-compose -f docker/docker-compose.prod.yml up -d
```

## Troubleshooting Installation

### Common Issues

**Import Errors:**
```bash
# Clear Python cache
make clean
pip install -e .[dev,rag] --force-reinstall
```

**Database Connection Issues:**
- Verify Supabase credentials and network access
- Check if pgvector extension is enabled in Supabase
- Ensure PostgreSQL port (5432) is accessible

**LLM API Errors:**
- Confirm API keys are valid and have credits
- Check rate limits and usage quotas
- Verify model names are correct

**Memory Issues:**
- Ensure sufficient RAM (8GB+ recommended)
- For large document processing, consider increasing swap space

### Getting Help

- **[Troubleshooting Guide](../10-troubleshooting/)** - Detailed solutions for common issues
- **[Configuration Reference](../4-configuration/)** - All settings explained

## Next Steps

1. **[First Run Guide](./first-run.md)** - Start using the system
2. **[Configuration Guide](./configuration.md)** - Customize for your needs
3. **[User Guides](../5-guides/)** - Learn specific features

---

**Installation Complete!** 🎉

You now have a fully functional Knowledge Graph Pydantic Agent with all features enabled.
