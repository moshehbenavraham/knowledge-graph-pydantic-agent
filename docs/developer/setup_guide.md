# Developer Setup Guide

Complete guide for setting up the Agentic GraphRAG development environment.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [Development Workflow](#development-workflow)
- [IDE Configuration](#ide-configuration)
- [Common Issues](#common-issues)

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.11+ | Runtime |
| Git | 2.30+ | Version control |
| Make | 4.0+ | Task automation |
| PostgreSQL Client | 14+ | Database tools (optional) |

### Recommended Tools

- **uv**: Fast Python package manager
- **pyenv**: Python version management
- **Docker**: For local services (optional)
- **shellcheck**: Script validation (for Phase 03 scripts)

### System Requirements

- **RAM**: 8GB minimum (16GB recommended for full RAG)
- **Disk**: 6GB for dependencies (includes PyTorch)
- **Network**: Access to Supabase and Neo4j Aura

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/your-org/base_agent.git
cd base_agent
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

**Full RAG Installation** (recommended):
```bash
pip install uv
uv pip install -e .[dev,rag]
```

This installs:
- Core dependencies (streamlit, pydantic-ai, supabase)
- Development tools (pytest, ruff, black, mypy)
- RAG dependencies (neo4j, graphiti, torch)

**Minimal Installation** (for UI-only development):
```bash
pip install -e .[dev]
```

### 4. Install Pre-commit Hooks

```bash
pre-commit install
```

This enforces code quality on every commit.

---

## Configuration

### 1. Create Environment File

```bash
cp .env.example .env
```

### 2. Required Environment Variables

Edit `.env` with your credentials:

```bash
# LLM Configuration
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-openai-key
LLM_MODEL=gpt-4o-mini

# Embedding Configuration
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=sk-your-openai-key

# Supabase (PostgreSQL + Vector)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres

# Neo4j (Knowledge Graph)
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password
NEO4J_DATABASE=neo4j

# Optional Features
ENABLE_METRICS=true
LOG_LEVEL=INFO
UI_MODE=advanced
```

### 3. Validate Configuration

```bash
# Test configuration loading
python -c "from src.config import get_settings; print(get_settings().llm_provider)"
```

---

## Database Setup

### Supabase (PostgreSQL)

1. Create a Supabase project at https://supabase.com
2. Enable pgvector extension:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Run migration scripts:
   ```bash
   # In Supabase SQL Editor, run these files in order:
   # - src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql
   # - src/agentic_rag/storage/migrations/sql/004_analytics_schema.sql
   # - src/agentic_rag/storage/migrations/sql/005_auth_tables.sql
   ```

### Neo4j Aura

1. Create a free Neo4j Aura instance at https://neo4j.com/cloud/aura-free
2. Note the connection URI and password
3. Initialize the graph:
   ```bash
   make neo4j-init
   ```

### Test Connections

```bash
# Test PostgreSQL
python -c "
from src.clients.database import get_supabase_client
client = get_supabase_client()
print('Supabase connected!')
"

# Test Neo4j
python scripts/test_neo4j_connection.py
```

---

## Running the Application

### Streamlit UI

```bash
# Default (advanced mode)
make run-ui

# Simple mode (no persistence)
make run-ui-simple

# Standard mode (streaming)
make run-ui-standard
```

Access at: http://localhost:8502

### FastAPI Server

```bash
make run-api
```

Access at: http://localhost:8058
Docs at: http://localhost:8058/docs

### RAG Pipeline

```bash
# Ingest documents
make ingest

# Clean ingest (reset data)
make ingest-clean
```

---

## Development Workflow

### Code Quality Commands

```bash
# Format code
make format

# Run linter
make lint

# Run security checks
make security

# Run all checks
make check
```

### Testing

```bash
# Run test suite
make test

# Run with coverage
make test-coverage

# Run specific tests
pytest tests/test_unified_agent.py -v
pytest -k "test_search" -v
```

### Branch Workflow

1. Create feature branch:
   ```bash
   git checkout -b feature/your-feature
   ```

2. Make changes and commit:
   ```bash
   git add .
   git commit -m "Add your feature"
   ```

3. Pre-commit hooks run automatically

4. Push and create PR:
   ```bash
   git push origin feature/your-feature
   ```

---

## IDE Configuration

### VS Code

Recommended extensions:
- Python (ms-python)
- Pylance
- Black Formatter
- Ruff
- GitLens

Settings (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true,
  "editor.rulers": [100]
}
```

### PyCharm

1. Set Project Interpreter to `.venv`
2. Enable Black as formatter
3. Configure Ruff as external tool
4. Set line length to 100

---

## Common Issues

### Import Errors

```bash
# Reinstall in development mode
pip install -e .

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Database Connection Issues

See [Troubleshooting Guide](../troubleshooting/README.md) for detailed solutions.

### Pre-commit Hook Failures

```bash
# Run formatters manually
make format

# Skip hooks temporarily (not recommended)
git commit --no-verify
```

### Memory Issues

```bash
# Reduce batch sizes in .env
EMBEDDING_BATCH_SIZE=5
INGESTION_BATCH_SIZE=3
```

---

## Next Steps

- Read [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines
- Review [CONVENTIONS.md](../../.spec_system/CONVENTIONS.md) for architecture details
- Check [API Documentation](../api/README.md) for endpoint reference

---

**Last Updated**: 2025-12-30
