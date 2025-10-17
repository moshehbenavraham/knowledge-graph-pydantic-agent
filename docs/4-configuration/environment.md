# Environment Variables Reference

This document provides a complete reference for all environment variables used by Base Agent.

## Configuration Categories

### Core Services

#### Database Configuration
```bash
# ===== SUPABASE (Primary Database) =====
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_supabase_service_role_key

# Alternative: Direct PostgreSQL connection
DATABASE_URL=postgresql://user:pass@localhost:5432/db
```

**SUPABASE_URL**: Supabase project URL
- **Required**: Yes (if not using DATABASE_URL)
- **Format**: `https://your-project.supabase.co`
- **Security**: Has admin privileges

**SUPABASE_SERVICE_KEY**: Supabase service role key
- **Required**: Yes (if not using DATABASE_URL)
- **Format**: Long alphanumeric string
- **Security**: Keep secret, never commit

**DATABASE_URL**: Direct PostgreSQL connection string
- **Required**: Yes (alternative to Supabase)
- **Format**: `postgresql://user:password@host:port/database`
- **Note**: Requires PostgreSQL 14+ with pgvector

### AI Models Configuration

#### LLM Provider Settings
```bash
# ===== LLM CONFIGURATION =====
LLM_PROVIDER=openai                           # openai, anthropic, ollama, openrouter
LLM_BASE_URL=https://api.openai.com/v1        # Not used for Anthropic
LLM_API_KEY=your_api_key_here                 # Your OpenAI/Anthropic/OpenRouter API key
LLM_MODEL=gpt-4o-mini                         # Primary model name
LLM_TEMPERATURE=0.7                           # Generation temperature (0.0-2.0)
LLM_MAX_TOKENS=2000                          # Maximum response tokens
```

**LLM_PROVIDER**: Primary language model provider
- **Options**: `openai`, `anthropic`, `ollama`, `openrouter`
- **Default**: `openai`
- **Note**: Determines which client library and API to use

**LLM_BASE_URL**: Base URL for LLM API
- **Required**: For Ollama and custom OpenAI-compatible APIs
- **Default**: OpenAI's official URL
- **Format**: Full URL including `/v1`

**LLM_API_KEY**: API key for LLM provider
- **Required**: Yes
- **Security**: Keep secret, never commit to version control
- **Note**: For OpenRouter, use their API key format

**LLM_MODEL**: Model identifier to use
- **OpenAI**: `gpt-4o-mini`, `gpt-4`, `gpt-4o`, `gpt-3.5-turbo`
- **Anthropic**: `claude-3-5-sonnet-20241022`, `claude-3-haiku-20240307`
- **Ollama**: Model name as installed (e.g., `llama2:7b`)
- **Default**: `gpt-4o-mini`

**LLM_TEMPERATURE**: Response creativity/randomness
- **Range**: 0.0 (deterministic) to 2.0 (very creative)
- **Default**: 0.7
- **Use**: Lower for factual responses, higher for creative tasks

**LLM_MAX_TOKENS**: Maximum tokens per response
- **Range**: 1-4096 (varies by model)
- **Default**: 2000
- **Note**: Affects response length and API costs

#### Embedding Configuration
```bash
# ===== EMBEDDING CONFIGURATION =====
EMBEDDING_PROVIDER=openai                     # openai, anthropic, ollama
EMBEDDING_BASE_URL=https://api.openai.com/v1  # Not used for Anthropic
EMBEDDING_API_KEY=your_api_key_here           # Your embedding API key
EMBEDDING_MODEL=text-embedding-3-small        # Primary embedding model
EMBEDDING_DIMENSION=1536                      # Embedding vector dimension
EMBEDDING_BATCH_SIZE=100                      # Batch size for embedding generation
```

**EMBEDDING_PROVIDER**: Embedding model provider
- **Options**: `openai`, `ollama` (Anthropic not supported)
- **Default**: `openai`

**EMBEDDING_API_KEY**: API key for embedding service
- **Required**: Yes
- **Note**: Can be same as LLM_API_KEY for OpenAI

**EMBEDDING_MODEL**: Embedding model identifier
- **OpenAI**: `text-embedding-3-small`, `text-embedding-3-large`, `text-embedding-ada-002`
- **Ollama**: Model name as installed
- **Default**: `text-embedding-3-small`

**EMBEDDING_DIMENSION**: Vector dimension for embeddings
- **OpenAI Small**: 1536
- **OpenAI Large**: 3072
- **Ollama**: Varies by model
- **Default**: 1536

**EMBEDDING_BATCH_SIZE**: Number of texts to embed at once
- **Range**: 1-100
- **Default**: 100
- **Performance**: Larger batches are more efficient but use more memory

#### Vision Model Configuration
```bash
# ===== VISION MODEL =====
VISION_LLM_CHOICE=gpt-4o-mini                  # Vision-capable model
```

**VISION_LLM_CHOICE**: Model to use for image analysis
- **Options**: Vision-capable models like `gpt-4o`, `gpt-4o-mini`
- **Default**: `gpt-4o-mini`
- **Note**: Must be a model that supports vision tasks

### Knowledge Graph Configuration

#### Neo4j Settings
```bash
# ===== NEO4J (Knowledge Graph for Agentic RAG) =====
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io  # Use bolt://localhost:7687 for local
NEO4J_QUERY_API_URL=https://xxxxx.databases.neo4j.io/db/neo4j/query/v2
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
NEO4J_DATABASE=neo4j
NEO4J_ENCRYPTED=true                          # Use encrypted connection
```

**NEO4J_URI**: Neo4j database connection URL
- **Required**: For knowledge graph features
- **Format**: `neo4j+s://` for Aura, `bolt://` for local
- **Default**: `bolt://localhost:7687`

**NEO4J_QUERY_API_URL**: Neo4j HTTP API endpoint
- **Required**: For Aura cloud instances
- **Format**: `https://your-instance.neo4j.io/db/neo4j/query/v2`

**NEO4J_USER**: Database username
- **Default**: `neo4j`

**NEO4J_PASSWORD**: Database password
- **Required**: Yes
- **Security**: Keep secret

**NEO4J_DATABASE**: Database name to use
- **Default**: `neo4j`

**NEO4J_ENCRYPTED**: Whether to use encrypted connection
- **Options**: `true`, `false`
- **Default**: `true`

### Feature Flags

#### Core Features
```bash
# ===== FEATURE FLAGS =====
ENABLE_CODE_EXECUTION=false
ENABLE_WEB_SEARCH=true
ENABLE_IMAGE_ANALYSIS=true
ENABLE_LONG_TERM_MEMORY=true
ENABLE_RAG=true
ENABLE_AGENTIC_RAG=true
ENABLE_GRAPH_SEARCH=true
```

**ENABLE_CODE_EXECUTION**: Allow Python code execution
- **Default**: `false` (security)
- **Note**: Uses RestrictedPython for safety

**ENABLE_WEB_SEARCH**: Enable web search capabilities
- **Default**: `true`
- **Note**: Requires web search provider configuration

**ENABLE_IMAGE_ANALYSIS**: Enable vision model features
- **Default**: `true`
- **Note**: Requires vision-capable LLM model

**ENABLE_LONG_TERM_MEMORY**: Enable mem0 memory system
- **Default**: `true`
- **Note**: Provides conversation context across sessions

**ENABLE_RAG**: Enable document retrieval features
- **Default**: `true`
- **Note**: Requires document ingestion

**ENABLE_AGENTIC_RAG**: Enable advanced RAG with knowledge graph
- **Default**: `true`
- **Note**: Requires Neo4j configuration

**ENABLE_GRAPH_SEARCH**: Enable knowledge graph search
- **Default**: `true`
- **Note**: Requires Neo4j configuration

### Web Search Configuration

#### Search Providers
```bash
# ===== WEB SEARCH =====
# Priority: Jina > Brave > SearXNG (configure one or more)
JINA_API_KEY=                                 # Optional: Jina.ai API key for clean web content
BRAVE_API_KEY=                                # Optional: Brave Search API key
SEARXNG_BASE_URL=http://localhost:8080        # Optional: Self-hosted SearXNG instance
WEB_SEARCH_PROVIDER=                          # Optional: Force specific provider (jina/brave/searxng)
```

**JINA_API_KEY**: Jina.ai API key for web search
- **Optional**: Alternative to Brave Search
- **Note**: Provides clean, formatted web content

**BRAVE_API_KEY**: Brave Search API key
- **Optional**: Alternative web search provider

**SEARXNG_BASE_URL**: Self-hosted SearXNG instance URL
- **Optional**: For private web search deployment
- **Format**: `http://your-searxng-instance:8080`

**WEB_SEARCH_PROVIDER**: Force specific search provider
- **Options**: `jina`, `brave`, `searxng`
- **Note**: If not set, uses priority order

### UI Configuration

#### Interface Settings
```bash
# ===== UI CONFIGURATION =====
UI_MODE=standard                              # simple, standard, advanced
```

**UI_MODE**: Streamlit interface complexity level
- **Options**: `simple`, `standard`, `advanced`
- **Default**: `standard`
- **simple**: Basic chat only
- **standard**: Chat + basic dashboard
- **advanced**: All features + memory + MCP

### Performance & Caching

#### Redis Configuration
```bash
# ===== REDIS (Optional) =====
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=                               # Optional: Redis password
ENABLE_REDIS_CACHE=true
```

**REDIS_URL**: Redis server connection URL
- **Optional**: For performance caching
- **Format**: `redis://host:port/db` or `redis://host:port`
- **Default**: `redis://localhost:6379`

**REDIS_PASSWORD**: Redis authentication password
- **Optional**: If Redis requires authentication

**ENABLE_REDIS_CACHE**: Enable Redis caching layer
- **Default**: `true` (if Redis available)
- **Note**: Improves performance for repeated queries

#### Search Configuration
```bash
# ===== SEARCH CONFIGURATION =====
DEFAULT_SEARCH_LIMIT=10
VECTOR_SEARCH_THRESHOLD=0.7
VECTOR_SEARCH_TIMEOUT=2.0
GRAPH_SEARCH_TIMEOUT=3.0
ENABLE_SEARCH_CACHE=true
SEARCH_CACHE_TTL=3600
PARALLEL_SEARCH_TIMEOUT=5
```

**DEFAULT_SEARCH_LIMIT**: Default number of results to return
- **Default**: 10
- **Range**: 1-100

**VECTOR_SEARCH_THRESHOLD**: Minimum similarity score for vector search
- **Default**: 0.7
- **Range**: 0.0-1.0

**VECTOR_SEARCH_TIMEOUT**: Vector search timeout in seconds
- **Default**: 2.0
- **Note**: Fast timeout for responsive UX

**GRAPH_SEARCH_TIMEOUT**: Graph search timeout in seconds
- **Default**: 3.0
- **Note**: Slightly longer for complex graph queries

**ENABLE_SEARCH_CACHE**: Enable search result caching
- **Default**: `true`
- **Note**: Caches frequently used queries

**SEARCH_CACHE_TTL**: Search cache time-to-live in seconds
- **Default**: 3600 (1 hour)

**PARALLEL_SEARCH_TIMEOUT**: Timeout for parallel search execution
- **Default**: 5
- **Note**: Combined vector + graph search timeout

#### Performance Settings
```bash
# ===== PERFORMANCE =====
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=300
RATE_LIMIT_PER_MINUTE=60
```

**MAX_CONCURRENT_REQUESTS**: Maximum simultaneous requests
- **Default**: 10
- **Note**: Prevents resource exhaustion

**REQUEST_TIMEOUT**: Request timeout in seconds
- **Default**: 300 (5 minutes)
- **Note**: For long-running operations

**RATE_LIMIT_PER_MINUTE**: API rate limit per minute
- **Default**: 60
- **Note**: Per-IP rate limiting

### Document Processing

#### Chunking Configuration
```bash
# ===== INGESTION & CHUNKING SETTINGS =====
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_CHUNK_SIZE=2000
MIN_CHUNK_SIZE=100
USE_SEMANTIC_CHUNKING=true
SEMANTIC_CHUNKING_MODEL=gpt-4o-mini
```

**CHUNK_SIZE**: Default text chunk size in characters
- **Default**: 1000
- **Note**: Affects retrieval granularity

**CHUNK_OVERLAP**: Overlap between chunks in characters
- **Default**: 200
- **Note**: Prevents cutting sentences/entities

**MAX_CHUNK_SIZE**: Maximum chunk size
- **Default**: 2000

**MIN_CHUNK_SIZE**: Minimum chunk size
- **Default**: 100

**USE_SEMANTIC_CHUNKING**: Use LLM for intelligent chunking
- **Default**: `true`
- **Note**: Better quality but slower processing
- **Options**: `true` for semantic, `false` for simple chunking

**SEMANTIC_CHUNKING_MODEL**: Model for semantic chunking
- **Default**: `gpt-4o-mini`
- **Note**: Used when USE_SEMANTIC_CHUNKING=true

#### Entity Extraction
```bash
# ===== EXTRACTION CONFIGURATION =====
EXTRACTION_MODEL=gpt-4o-mini
EXTRACT_ENTITIES=true
EXTRACT_RELATIONSHIPS=true
EXTRACT_FACTS=true
MAX_ENTITIES_PER_CHUNK=10
MAX_FACTS_PER_CHUNK=5
MAX_FACT_LENGTH=500
EXTRACTION_CONFIDENCE_THRESHOLD=0.7
```

**EXTRACTION_MODEL**: Model for entity/fact extraction
- **Default**: `gpt-4o-mini`
- **Note**: Must be a capable model for structured extraction

**EXTRACT_ENTITIES**: Extract named entities from text
- **Default**: `true`
- **Note**: Enables entity extraction for knowledge graph

**EXTRACT_RELATIONSHIPS**: Extract entity relationships
- **Default**: `true`
- **Note**: Enables relationship extraction between entities

**EXTRACT_FACTS**: Extract temporal facts and episodes
- **Default**: `true`
- **Note**: Enables temporal fact extraction with timestamps

**MAX_ENTITIES_PER_CHUNK**: Maximum entities per chunk
- **Default**: 10
- **Range**: 1-50
- **Note**: Limits entity extraction per document chunk

**MAX_FACTS_PER_CHUNK**: Maximum facts per chunk
- **Default**: 5
- **Range**: 1-20
- **Note**: Limits fact extraction per chunk

**MAX_FACT_LENGTH**: Maximum fact length in characters
- **Default**: 500
- **Range**: 100-1000
- **Note**: Brief facts for Neo4j storage

**EXTRACTION_CONFIDENCE_THRESHOLD**: Minimum confidence for extraction
- **Range**: 0.0-1.0
- **Default**: 0.7
- **Note**: Filters low-confidence extractions

### API Configuration

#### Server Settings
```bash
# ===== API SETTINGS =====
API_HOST=localhost
API_PORT=8058
CORS_ORIGINS=http://localhost:8501
```

**API_HOST**: API server bind address
- **Default**: `localhost`
- **Note**: Use `0.0.0.0` for container networking

**API_PORT**: API server port
- **Default**: 8058

**CORS_ORIGINS**: Allowed origins for CORS
- **Default**: `http://localhost:8501`
- **Format**: Comma-separated URLs

### Monitoring & Observability

#### Logging Configuration
```bash
# ===== LOGGING =====
LOG_LEVEL=INFO
LOG_FORMAT=json
ENABLE_STRUCTURED_LOGGING=true
```

**LOG_LEVEL**: Minimum log level
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- **Default**: `INFO`

**LOG_FORMAT**: Log output format
- **Options**: `json`, `text`
- **Default**: `json` (structured logging)

**ENABLE_STRUCTURED_LOGGING**: Enable structured (JSON) logging
- **Default**: `true`

#### Metrics and Tracing
```bash
# ===== MONITORING =====
ENABLE_METRICS=true
METRICS_PORT=8000
HEALTH_CHECK_INTERVAL=30
```

**ENABLE_METRICS**: Enable Prometheus metrics collection
- **Default**: `true`

**METRICS_PORT**: Port for metrics endpoint
- **Default**: 8000

**HEALTH_CHECK_INTERVAL**: Health check interval in seconds
- **Default**: 30

### Development Settings

#### MCP Server Configuration
```bash
# ===== MCP SERVER =====
MCP_SERVER_PORT=3000
MCP_SERVER_HOST=localhost
```

**MCP_SERVER_PORT**: Model Context Protocol server port
- **Default**: 3000

**MCP_SERVER_HOST**: MCP server bind address
- **Default**: `localhost`

### Security Settings

#### Sensitive Data Masking
```bash
# ===== SECURITY =====
MASK_SENSITIVE=true                           # Mask sensitive data in logs
```

**MASK_SENSITIVE**: Mask sensitive information in logs
- **Default**: `true`
- **Note**: Masks API keys, passwords, and tokens in log output
- **Applies to**: Structured logging, error messages, debug output

#### Circuit Breaker
```bash
# ===== CIRCUIT BREAKER =====
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60
CIRCUIT_BREAKER_HALF_OPEN_REQUESTS=3
```

**CIRCUIT_BREAKER_FAILURE_THRESHOLD**: Failures before opening circuit
- **Default**: 5
- **Range**: 1-100
- **Note**: Number of consecutive failures before circuit opens

**CIRCUIT_BREAKER_RECOVERY_TIMEOUT**: Seconds before retrying
- **Default**: 60
- **Range**: 10-300
- **Note**: Wait time before attempting recovery

**CIRCUIT_BREAKER_HALF_OPEN_REQUESTS**: Requests allowed in half-open state
- **Default**: 3
- **Range**: 1-10
- **Note**: Test requests before fully closing circuit

### Integration Settings

#### Google Drive (Optional)
```bash
# ===== GOOGLE DRIVE (Optional) =====
GOOGLE_DRIVE_FOLDER_ID=
GOOGLE_DRIVE_CREDENTIALS_PATH=config/google_credentials.json
```

**GOOGLE_DRIVE_FOLDER_ID**: Google Drive folder to monitor
- **Optional**: For automatic document ingestion

**GOOGLE_DRIVE_CREDENTIALS_PATH**: Path to Google service account credentials
- **Default**: `config/google_credentials.json`

## Validation

All settings are validated at startup. Invalid values will cause the application to exit with clear error messages.

## Security Notes

- Never commit `.env` files containing real credentials
- Use strong, unique API keys for production
- Rotate keys regularly
- Monitor access logs for unusual activity
- Use least-privilege permissions where possible

## Troubleshooting

See the [Troubleshooting Guide](../10-troubleshooting/) for solutions to common configuration issues.

---

**Environment Variables Reference Complete** | All configuration options documented
