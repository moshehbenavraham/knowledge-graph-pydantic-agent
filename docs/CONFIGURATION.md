# Configuration Guide

## Overview

The Base Agent uses a **centralized configuration system** built on Pydantic Settings, providing type safety, validation, and a single source of truth for all configuration values.

## Configuration Architecture

### Core Components

```
src/config/
├── settings.py          # Main Settings class with Pydantic BaseSettings
├── __init__.py         # Exports get_settings() singleton
├── api.py              # API-specific configuration facade
├── agent.py            # Agent and search configuration facade  
├── clients.py          # Database and client configurations
└── ui.py               # UI configuration facade
```

### Key Features

- **Type Safety**: Full Pydantic validation with helpful error messages
- **Environment-based**: Loads from environment variables and `.env` files
- **Validation**: Automatic validation with environment-specific rules
- **Singleton Pattern**: Cached settings for performance
- **Module Facades**: Clean interfaces for each subsystem
- **Backward Compatible**: Maintains compatibility with legacy code

## Quick Start

### 1. Basic Setup

```bash
# Copy example configuration
cp .env.example .env

# Edit with your credentials
nano .env
```

### 2. Required Settings

```bash
# Database - Choose one
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_key
# OR
DATABASE_URL=postgresql://user:pass@localhost/db

# LLM Configuration
LLM_PROVIDER=openai              # openai, anthropic, ollama, openrouter
LLM_API_KEY=your_api_key
LLM_MODEL=gpt-4o-mini           # Model to use

# Embedding Configuration  
EMBEDDING_PROVIDER=openai        # openai, nomic, ollama, cohere
EMBEDDING_API_KEY=your_api_key
EMBEDDING_MODEL=text-embedding-3-small
```

### 3. Using in Code

```python
# Import centralized settings
from src.config import get_settings

settings = get_settings()
print(f"Running in {settings.app_env} mode")
print(f"API port: {settings.api_port}")

# Use module-specific facades
from src.config.api import api_config
print(f"CORS origins: {api_config.cors_origins}")

from src.config.agent import agent_config
print(f"LLM model: {agent_config.llm_model}")
```

## Configuration Categories

### Application Environment

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `APP_ENV` | Enum | `development` | Environment: development, testing, production |
| `DEBUG` | Boolean | `false` | Enable debug mode |
| `LOG_LEVEL` | String | `INFO` | Logging level |

### Database Configuration

#### PostgreSQL/Supabase
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DATABASE_URL` | String | - | PostgreSQL connection string |
| `SUPABASE_URL` | String | - | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | String | - | Supabase service role key |

#### Neo4j (Knowledge Graph)
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `NEO4J_URI` | String | `bolt://localhost:7687` | Neo4j connection URI |
| `NEO4J_USER` | String | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | String | - | Neo4j password |
| `NEO4J_DATABASE` | String | `neo4j` | Database name |
| `NEO4J_ENCRYPTED` | Boolean | `true` | Use encrypted connection |

#### Redis (Optional Cache)
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `REDIS_URL` | String | - | Redis connection URL |
| `ENABLE_REDIS_CACHE` | Boolean | `false` | Enable Redis caching |

### LLM Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LLM_PROVIDER` | Enum | `openai` | Provider: openai, anthropic, ollama, openrouter |
| `LLM_BASE_URL` | String | `https://api.openai.com/v1` | API base URL |
| `LLM_API_KEY` | String | - | API key for LLM provider |
| `LLM_MODEL` | String | `gpt-4o-mini` | Model to use |
| `LLM_TEMPERATURE` | Float | `0.7` | Generation temperature (0.0-2.0) |
| `LLM_MAX_TOKENS` | Integer | `2000` | Maximum response tokens |

### Embedding Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `EMBEDDING_PROVIDER` | Enum | `openai` | Provider: openai, nomic, ollama, cohere |
| `EMBEDDING_BASE_URL` | String | `https://api.openai.com/v1` | API base URL |
| `EMBEDDING_API_KEY` | String | - | API key for embeddings |
| `EMBEDDING_MODEL` | String | `text-embedding-3-small` | Embedding model |
| `EMBEDDING_DIMENSION` | Integer | `1536` | Vector dimension |
| `EMBEDDING_BATCH_SIZE` | Integer | `100` | Batch size for processing |

### UI Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `UI_MODE` | Enum | `standard` | UI mode: simple, standard, advanced |

**UI Modes Explained:**
- **Simple**: Fast, lightweight, no persistence
- **Standard**: Streaming, tools visibility, conversation history
- **Advanced**: All features including metrics, memory, MCP support

### Web Search Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `WEB_SEARCH_PROVIDER` | Enum | - | Force specific provider: jina, brave, searxng |
| `JINA_API_KEY` | String | - | Jina.ai API key |
| `BRAVE_API_KEY` | String | - | Brave Search API key |
| `SEARXNG_BASE_URL` | String | - | SearXNG instance URL |

### Performance Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_GRAPH` | Boolean | `true` | Enable graph database features |
| `ENABLE_CACHING` | Boolean | `true` | Enable caching |
| `ENABLE_PARALLEL_SEARCH` | Boolean | `true` | Enable parallel search execution |
| `VECTOR_SEARCH_TIMEOUT` | Float | `2.0` | Vector search timeout (seconds) |
| `GRAPH_SEARCH_TIMEOUT` | Float | `3.0` | Graph search timeout (seconds) |

### Ingestion & Chunking

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CHUNK_SIZE` | Integer | `1000` | Document chunk size |
| `CHUNK_OVERLAP` | Integer | `200` | Overlap between chunks |
| `USE_SEMANTIC_CHUNKING` | Boolean | `true` | Use semantic chunking |
| `MAX_ENTITIES_PER_CHUNK` | Integer | `10` | Max entities to extract |
| `MAX_FACT_LENGTH` | Integer | `500` | Maximum fact length |
| `GRAPH_BATCH_SIZE` | Integer | `10` | Batch size for graph operations |

### Connection Pools

#### PostgreSQL Pool
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PG_POOL_MIN` | Integer | `5` | Minimum pool size |
| `PG_POOL_MAX` | Integer | `20` | Maximum pool size |
| `PG_COMMAND_TIMEOUT` | Integer | `60` | Command timeout (seconds) |
| `PG_MAX_QUERIES` | Integer | `50000` | Max queries before connection reset |
| `PG_MAX_INACTIVE_LIFETIME` | Integer | `300` | Max inactive connection lifetime |

#### Neo4j Pool
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `NEO4J_POOL_SIZE` | Integer | `50` | Connection pool size |
| `NEO4J_CONNECTION_TIMEOUT` | Float | `30.0` | Connection timeout (seconds) |
| `NEO4J_MAX_RETRY_TIME` | Integer | `30` | Maximum retry time |

#### Redis Pool
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `REDIS_POOL_SIZE` | Integer | `10` | Redis connection pool size |
| `REDIS_SOCKET_TIMEOUT` | Integer | `5` | Socket timeout (seconds) |

### API Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `API_HOST` | String | `0.0.0.0` | API server host |
| `API_PORT` | Integer | `8058` | API server port |
| `CORS_ORIGINS` | String | `http://localhost:3000` | Comma-separated CORS origins |
| `HOT_RELOAD` | Boolean | `false` | Enable hot reload |

### Circuit Breaker

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | Integer | `5` | Failures before circuit opens |
| `CIRCUIT_BREAKER_RECOVERY_TIMEOUT` | Integer | `60` | Recovery timeout (seconds) |
| `CIRCUIT_BREAKER_HALF_OPEN_REQUESTS` | Integer | `3` | Requests in half-open state |

### Caching Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `EMBEDDING_CACHE_SIZE` | Integer | `1000` | Embedding cache size |
| `EMBEDDING_CACHE_TTL` | Integer | `3600` | Embedding cache TTL (seconds) |
| `GRAPH_CACHE_SIZE` | Integer | `500` | Graph cache size |
| `GRAPH_CACHE_TTL` | Integer | `1800` | Graph cache TTL (seconds) |

### Monitoring & Observability

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_TRACING` | Boolean | `false` | Enable OpenTelemetry tracing |
| `JAEGER_HOST` | String | `localhost` | Jaeger agent host |
| `JAEGER_PORT` | Integer | `6831` | Jaeger agent port |

## Advanced Usage

### Environment-Specific Validation

The configuration system automatically validates settings based on the environment:

```python
# Production requires certain settings
APP_ENV=production
# Will validate that API keys are set
# Will warn about debug mode being enabled
# Will require database URLs
```

### Accessing Configuration

#### Direct Access
```python
from src.config import get_settings

settings = get_settings()
# All settings available with auto-completion
print(settings.llm_model)
print(settings.chunk_size)
```

#### Module Facades
```python
# API-specific settings
from src.config.api import api_config
uvicorn_config = api_config.get_uvicorn_config()
cors_config = api_config.get_cors_config()

# Agent settings
from src.config.agent import agent_config
if agent_config.has_web_search_configured():
    search_config = agent_config.get_web_search_config()

# Client settings
from src.config.clients import clients_config
llm_config = clients_config.get_llm_config()
db_config = clients_config.get_postgres_config()

# UI settings
from src.config.ui import ui_config
if ui_config.is_advanced_mode:
    # Enable advanced features
    pass
```

### Testing with Configuration

```python
import os
from unittest.mock import patch
from src.config import reload_settings

def test_with_config():
    with patch.dict(os.environ, {
        "UI_MODE": "advanced",
        "LLM_MODEL": "gpt-4",
        "ENABLE_GRAPH": "false"
    }):
        settings = reload_settings()
        assert settings.ui_mode == "advanced"
        assert settings.llm_model == "gpt-4"
        assert not settings.enable_graph
```

### Configuration Validation

The system provides comprehensive validation:

```python
from src.config import get_settings

settings = get_settings()

# Check for production warnings
if settings.app_env == "production":
    warnings = settings.validate_for_production()
    for warning in warnings:
        print(f"⚠️ {warning}")
```

### Custom Configuration

Extend the configuration for your needs:

```python
from src.config.settings import Settings
from pydantic import Field

class CustomSettings(Settings):
    """Extended settings with custom fields."""
    
    my_custom_field: str = Field(
        default="default_value",
        description="My custom configuration"
    )
```

## Migration from Old System

### Before (Scattered Configuration)
```python
# Old way - scattered across files
import os
api_key = os.getenv("LLM_API_KEY", "default")
model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

# Duplicate configs in multiple files
class EmbeddingConfig:
    dimension = 1536
    model = "text-embedding-3-small"
```

### After (Centralized)
```python
# New way - centralized with validation
from src.config import get_settings
from src.config.clients import clients_config

settings = get_settings()
# Type-safe with auto-completion
api_key = settings.llm_api_key
model = settings.llm_model

# Or use facades
model = clients_config.llm_model
dimension = clients_config.embedding_dimension
```

## Best Practices

1. **Always use the centralized system** - Don't use `os.getenv()` directly
2. **Use facades for module-specific config** - Cleaner and more maintainable
3. **Validate in production** - Use the built-in validation methods
4. **Keep secrets in `.env`** - Never commit credentials
5. **Use type hints** - The system provides full type safety
6. **Test with overrides** - Use `patch.dict(os.environ)` for testing

## Troubleshooting

### Common Issues

**Issue**: "Configuration validation failed"
```bash
# Check required fields are set
cat .env | grep -E "SUPABASE_URL|LLM_API_KEY|EMBEDDING_API_KEY"

# Ensure no typos in environment variable names
```

**Issue**: "Settings not updating"
```python
# Force reload after environment changes
from src.config import reload_settings
settings = reload_settings()
```

**Issue**: "Import errors"
```python
# Ensure you're importing from the right location
from src.config import get_settings  # ✅
from src.agentic_rag.config import get_config  # ⚠️ Legacy (but still works)
```

## Complete Environment Variables Reference

See [.env.example](../.env.example) for a complete list of all available environment variables with descriptions and examples.