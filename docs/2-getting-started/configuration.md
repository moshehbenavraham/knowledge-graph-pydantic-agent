# Configuration Guide

This guide explains how to configure Luminari AI Agent for your specific requirements using the centralized Pydantic settings system.

## Configuration Architecture

Luminari uses a **centralized configuration system** with these key benefits:

- **Type Safety**: Full Pydantic validation with helpful error messages
- **Environment-based**: Loads from `.env` files and environment variables
- **Module-specific Facades**: Clean interfaces for each subsystem
- **Runtime Validation**: Settings validated at startup with clear error reporting

## Configuration Files

### Primary Configuration
- **`.env`**: Your main configuration file (copy from `.env.example`)
- **`.env.example`**: Template with all available options and documentation

### Generated Configuration
- **`src/config/settings.py`**: Main Pydantic settings class
- **`src/config/*.py`**: Module-specific configuration facades

## Essential Configuration

### 1. Database Setup (Required)

Choose one database option:

#### Option A: Supabase (Recommended)
```bash
# In .env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
```

#### Option B: Direct PostgreSQL
```bash
DATABASE_URL=postgresql://username:password@localhost:5432/luminari_db
```

**Requirements:**
- PostgreSQL 14+ with pgvector extension
- Sufficient permissions for table creation and indexing

### 2. LLM Provider Setup (Required)

Choose one LLM provider:

#### OpenAI (Recommended)
```bash
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-openai-api-key
LLM_MODEL=gpt-4o-mini  # or gpt-4, gpt-4o, etc.
```

#### Anthropic Claude
```bash
LLM_PROVIDER=anthropic
LLM_API_KEY=your-anthropic-api-key
LLM_MODEL=claude-3-5-sonnet-20241022
```

#### Ollama (Local)
```bash
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama2:7b  # your installed model
```

### 3. Embedding Configuration (Required)

```bash
EMBEDDING_PROVIDER=openai  # or ollama
EMBEDDING_API_KEY=your-openai-api-key
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536  # matches the model
```

## Feature Configuration

### Knowledge Graph Features (Optional)

For enhanced entity recognition and relationship mapping:

```bash
# Neo4j Configuration
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j

# Enable Graph Features
ENABLE_GRAPH_SEARCH=true
ENABLE_AGENTIC_RAG=true
```

### Performance Optimization (Recommended)

```bash
# Redis Caching
REDIS_URL=redis://localhost:6379
ENABLE_REDIS_CACHE=true

# Performance Settings
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=300
RATE_LIMIT_PER_MINUTE=60
```

### Web Search Integration (Optional)

```bash
# Choose one or more providers (priority order)
JINA_API_KEY=your-jina-api-key
BRAVE_API_KEY=your-brave-api-key
SEARXNG_BASE_URL=http://localhost:8080

WEB_SEARCH_PROVIDER=jina  # or brave, searxng
```

## UI Configuration

### Interface Modes

```bash
# UI Mode: simple, standard, advanced
UI_MODE=standard

# Feature Toggles
ENABLE_CODE_EXECUTION=true
ENABLE_WEB_SEARCH=true
ENABLE_IMAGE_ANALYSIS=true
ENABLE_LONG_TERM_MEMORY=true
```

## Advanced Configuration

### Chunking and Processing

```bash
# Document Processing
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
USE_SEMANTIC_CHUNKING=true
SEMANTIC_CHUNKING_MODEL=gpt-4o-mini

# Entity Extraction
EXTRACT_ENTITIES=true
EXTRACT_RELATIONSHIPS=true
EXTRACT_FACTS=true
MAX_ENTITIES_PER_CHUNK=10
EXTRACTION_CONFIDENCE_THRESHOLD=0.7
```

### Logging and Monitoring

```bash
# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json  # json or text
ENABLE_STRUCTURED_LOGGING=true

# Metrics and Tracing
ENABLE_METRICS=true
PROMETHEUS_PORT=8000
ENABLE_TRACING=true
JAEGER_ENDPOINT=http://localhost:14268/api/traces
```

### Security Settings

```bash
# API Security
API_HOST=localhost
API_PORT=8058
CORS_ORIGINS=http://localhost:8501,http://localhost:3000

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
MAX_CONCURRENT_REQUESTS=10

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60
```

## Configuration Validation

### Automatic Validation

The system validates configuration at startup:

```bash
# Start any service to validate
make run-ui

# Or validate manually
python -c "
from src.config import get_settings
settings = get_settings()
print('✅ Configuration is valid')
"
```

### Common Validation Errors

**Database Connection:**
```
Error: Could not connect to Supabase
Solution: Check SUPABASE_URL and SUPABASE_SERVICE_KEY
```

**API Key Issues:**
```
Error: Invalid API key for OpenAI
Solution: Verify LLM_API_KEY has correct format and credits
```

**Missing Environment Variables:**
```
Error: Missing required setting: LLM_MODEL
Solution: Add missing variables to .env file
```

## Environment-Specific Configuration

### Development Environment

```bash
# .env.development
LOG_LEVEL=DEBUG
ENABLE_METRICS=false
UI_MODE=advanced
```

### Production Environment

```bash
# .env.production
LOG_LEVEL=WARNING
ENABLE_METRICS=true
UI_MODE=standard
CORS_ORIGINS=https://yourdomain.com
```

Load with:
```bash
export ENV_FILE=.env.production
make run-ui
```

## Runtime Configuration

### Accessing Settings in Code

```python
from src.config import get_settings

# Get all settings
settings = get_settings()

# Access specific values
llm_model = settings.llm.model
db_url = settings.database.url
```

### Module-Specific Facades

```python
from src.config.api import APIConfig
from src.config.agent import AgentConfig
from src.config.clients import ClientConfig

# API settings
api_config = APIConfig()
port = api_config.port

# Agent settings
agent_config = AgentConfig()
temperature = agent_config.temperature
```

## Configuration Best Practices

### 1. Use Environment Variables
Always use environment variables for sensitive data:
```bash
export SUPABASE_SERVICE_KEY="your-secret-key"
export LLM_API_KEY="your-api-key"
```

### 2. Validate Before Deployment
```bash
# Test configuration in staging
make run-ui  # Should start without errors
```

### 3. Use Consistent Naming
Follow the existing `.env.example` structure for new settings.

### 4. Document Custom Settings
If adding new configuration options, update `.env.example` with clear descriptions.

### 5. Security Considerations
- Never commit `.env` files to version control
- Use strong, unique API keys for production
- Rotate keys regularly
- Use least-privilege permissions

## Troubleshooting Configuration

### Cannot Load Settings
```bash
# Check if .env exists
ls -la .env

# Validate .env syntax
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('Environment loaded successfully')
"
```

### Database Connection Issues
```bash
# Test database connectivity
python scripts/test_supabase_connection.py

# Check network access
curl -I $SUPABASE_URL/rest/v1/
```

### API Provider Issues
```bash
# Test LLM provider
python -c "
from src.clients.llm import LLMClient
client = LLMClient()
print(client.complete('Hello'))
"
```

## Getting Help

- **[Environment Variables Reference](../4-configuration/environment.md)** - Complete list of all settings
- **[Settings System Guide](../4-configuration/settings.md)** - Technical details about the configuration system
- **[Troubleshooting Guide](../9-troubleshooting/)** - Common configuration issues

---

**Configuration Complete!** Your Luminari AI Agent is now configured for your environment.