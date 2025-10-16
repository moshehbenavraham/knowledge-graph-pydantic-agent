# Configuration Reference

This section provides comprehensive documentation for all configuration options in Luminari AI Agent.

## Configuration System Overview

Luminari uses a **centralized Pydantic-based configuration system** that provides:

- **Type Safety**: Full validation with helpful error messages
- **Environment Integration**: Automatic loading from `.env` files
- **Runtime Validation**: Settings validated at application startup
- **Module Facades**: Clean interfaces for different subsystems

## Quick Reference

### Essential Settings (Required)

| Setting | Description | Example |
|---------|-------------|---------|
| `SUPABASE_URL` | Supabase project URL | `https://your-project.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | `your_service_key` |
| `LLM_PROVIDER` | LLM provider (openai/anthropic/ollama) | `openai` |
| `LLM_API_KEY` | API key for LLM provider | `sk-your-key` |
| `LLM_MODEL` | Model name to use | `gpt-4o-mini` |
| `EMBEDDING_PROVIDER` | Embedding provider | `openai` |
| `EMBEDDING_API_KEY` | API key for embeddings | `sk-your-key` |
| `EMBEDDING_MODEL` | Embedding model name | `text-embedding-3-small` |

### Optional but Recommended

| Setting | Description | Example |
|---------|-------------|---------|
| `NEO4J_URI` | Neo4j knowledge graph URL | `neo4j+s://your-instance.neo4j.io` |
| `REDIS_URL` | Redis cache URL | `redis://localhost:6379` |
| `JINA_API_KEY` | Web search API key | `your-jina-key` |
| `UI_MODE` | Interface mode | `standard` |

## Configuration Categories

### [Core Services](./environment.md#core-services)
Database connections, API endpoints, and essential services

### [AI Models](./environment.md#ai-models)
LLM and embedding model configuration

### [Features](./environment.md#feature-flags)
Feature toggles and capability switches

### [Performance](./environment.md#performance)
Caching, timeouts, and resource management

### [Security](./environment.md#security)
Access controls, rate limiting, and hardening

### [Monitoring](./environment.md#monitoring)
Logging, metrics, and observability settings

## Using Configuration

### Loading Settings

```python
from src.config import get_settings

# Get all settings
settings = get_settings()

# Access specific values
llm_model = settings.llm.model
db_url = settings.database.url
```

### Module-Specific Access

```python
from src.config.api import APIConfig
from src.config.agent import AgentConfig

# API configuration
api_config = APIConfig()
port = api_config.port

# Agent configuration
agent_config = AgentConfig()
temperature = agent_config.temperature
```

## Validation and Troubleshooting

### Configuration Validation

The system validates all settings at startup:

```bash
make run-ui  # Will show validation errors if any
```

### Common Issues

- **[Missing Variables](./troubleshooting.md#missing-environment-variables)** - Required settings not found
- **[Invalid Values](./troubleshooting.md#invalid-configuration-values)** - Settings with wrong format
- **[Connection Errors](./troubleshooting.md#database-connection-issues)** - Cannot connect to services

## Environment-Specific Configuration

### Development
```bash
LOG_LEVEL=DEBUG
ENABLE_METRICS=false
UI_MODE=advanced
```

### Production
```bash
LOG_LEVEL=WARNING
ENABLE_METRICS=true
CORS_ORIGINS=https://yourdomain.com
```

## Best Practices

### Security
- Never commit `.env` files to version control
- Use strong, unique API keys for production
- Rotate credentials regularly
- Use least-privilege permissions

### Performance
- Enable Redis caching for production
- Configure appropriate rate limits
- Monitor resource usage and adjust accordingly

### Maintenance
- Keep `.env.example` synchronized with code
- Document any custom configuration additions
- Test configuration changes in staging first

## Getting Help

- **[Environment Variables](./environment.md)** - Complete reference for all settings
- **[Settings System](./settings.md)** - Technical details about Pydantic configuration
- **[Troubleshooting Guide](../9-troubleshooting/)** - Solutions for common configuration issues

---

**Configuration Reference Complete** | Ready to customize your deployment