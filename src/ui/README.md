# Luminari AI Agent - Streamlit UI

This directory contains the Streamlit-based user interface for the Luminari AI Agent, providing an interactive chat experience with advanced AI capabilities including RAG, memory, web search, and multi-tool functionality.

## Available UI Components

- `streamlit_app.py` - Unified configurable Streamlit application with three modes
- `features/` - Modular feature handlers for different UI capabilities
  - `base_handler.py` - Core chat functionality
  - `streaming_handler.py` - Real-time token streaming
  - `memory_handler.py` - Mem0 integration for persistent memory
  - `mcp_handler.py` - Model Context Protocol support
  - `upload_handler.py` - File upload processing for documents, images, and tabular data

## Features

- **Interactive Chat Interface** - Clean, modern chat experience
- **Multi-LLM Support** - Works with OpenAI, Anthropic, Ollama, and other providers
- **File Upload** - Direct upload of documents, images, and tabular data via sidebar
  - **Documents**: PDF, TXT, MD files with automatic chunking and embedding
  - **Images**: PNG, JPG, JPEG, GIF, WEBP with base64 storage
  - **Tabular**: CSV, XLSX, XLS with schema detection and row storage
- **Agentic RAG Integration** - Advanced document search with knowledge graph and vector search
- **Knowledge Graph** - Entity relationships and temporal facts via Neo4j
- **Long-term Memory** - Persistent conversation memory using Mem0
- **Web Search** - Integration with Brave Search API and SearXNG
- **Code Execution** - Safe code execution in sandboxed environments
- **Image Analysis** - Vision capabilities with gpt-5-mini (OCR, object detection, scene analysis)
- **Real-time Streaming** - Token-by-token response streaming
- **MCP Support** - Model Context Protocol for extended capabilities

## Prerequisites

- Python 3.11+
- Supabase account and project
- LLM API access (OpenAI, Anthropic, etc.)
- Neo4j database (for Agentic RAG features)
- Optional: Brave Search API key

## Quick Start

### 1. Install the Project

```bash
# From the project root directory
cd /path/to/luminari-ai-agent

# Install with development dependencies
make setup

# Or manually:
pip install -e .[dev]
```

### 2. Environment Configuration

Copy and configure the environment variables:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# ===== SUPABASE (Primary Database) =====
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_supabase_service_role_key

# ===== NEO4J (Knowledge Graph) =====
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# ===== LLM CONFIGURATION =====
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_api_key_here
LLM_CHOICE=gpt-4o-mini

# ===== EMBEDDING CONFIGURATION =====
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=your_api_key_here
EMBEDDING_MODEL_CHOICE=text-embedding-3-small

# ===== WEB SEARCH (Optional) =====
BRAVE_API_KEY=your_brave_api_key
SEARXNG_BASE_URL=http://localhost:8080

# ===== FEATURE FLAGS =====
ENABLE_WEB_SEARCH=true
ENABLE_IMAGE_ANALYSIS=true
ENABLE_LONG_TERM_MEMORY=true
ENABLE_RAG=true
ENABLE_AGENTIC_RAG=true
ENABLE_GRAPH_SEARCH=true
```

### 3. Database Setup

The application uses Supabase as the primary database. Make sure to:

1. Create a Supabase project
2. Set up the required tables (see `sql/` directory)
3. Configure your environment variables

### 4. Running the UI

```bash
# Standard mode (default - streaming with tools)
make run-ui

# Simple mode (fast, no persistence)
make run-ui-simple

# Advanced mode (all features enabled)
make run-ui-advanced

# With custom mode via environment variable
make run-ui MODE=simple

# Or directly with Streamlit
UI_MODE=advanced streamlit run src/ui/streamlit_app.py

# For development with auto-reload
make dev MODE=standard
```

The application will be available at http://localhost:8501

### UI Modes

- **Simple Mode** 🟢 - Basic chat interface with no streaming or advanced features. Fast and lightweight.
- **Standard Mode** 🔵 - Real-time streaming with tool visibility. Recommended for most users.
- **Advanced Mode** 🟣 - Full feature set including memory persistence, MCP servers, and metrics.

## Development

### Local Development Setup

```bash
# Install development dependencies
make setup

# Run with hot reload
make dev

# Run tests
make test

# Run linting and formatting
make check
make format
```

### Docker Development

```bash
# Build and run with Docker Compose
make docker-build
make docker-run

# Stop services
make docker-stop
```

## UI Architecture

### Main Components

- **Chat Interface** - Streamlit-based conversational UI
- **Agent Integration** - Connects to the core 'AI with Apex Advanced RAG Agent'
- **Memory Management** - Handles conversation persistence
- **Tool Integration** - Access to web search, RAG, code execution
- **Streaming Support** - Real-time response rendering

### File Structure

```
src/ui/
├── streamlit_app.py          # Unified configurable UI
├── features/                 # Modular feature handlers
│   ├── __init__.py
│   ├── base_handler.py      # Core functionality
│   ├── streaming_handler.py # Streaming support
│   ├── memory_handler.py    # Memory persistence
│   └── mcp_handler.py       # MCP server integration
└── README.md                # This file
```

## Configuration Options

The UI respects all agent configuration from the main `.env` file:

- **LLM Provider Settings** - Choose your preferred AI provider
- **Memory Configuration** - Enable/disable long-term memory
- **Tool Availability** - Control which tools are accessible
- **Search Configuration** - Web search provider settings
- **Vision Settings** - Image analysis capabilities

## Troubleshooting

### Common Issues

1. **Import Errors** - Ensure you've installed the package: `pip install -e .`
2. **Database Connection** - Verify Supabase credentials and network access
3. **LLM API Issues** - Check API keys and rate limits
4. **Missing Tools** - Verify feature flags in `.env`

### Debug Mode

Enable debug logging by setting:

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

## Production Deployment

For production deployment, consider:

1. **Environment Variables** - Use proper secrets management
2. **Database** - Ensure Supabase is properly configured for production
3. **Scaling** - Consider using Docker and container orchestration
4. **Monitoring** - Enable metrics and health checks
5. **Security** - Review and configure authentication if needed

See the main project documentation for detailed deployment instructions.
