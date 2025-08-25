# Configuration

## Environment Variables

All environment variables can be configured in your `.env` file. See [`.env.example`](../.env.example) for a complete template.

### Required Core Settings

#### Supabase Database
| Variable | Description | Example |
|----------|-------------|---------|
| `SUPABASE_URL` | Supabase project URL | `https://your-project.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | `eyJ...` |
| `DATABASE_URL` | Same as SUPABASE_URL (for mem0) | `${SUPABASE_URL}` |

#### LLM Provider Settings
| Variable | Options | Description | Default |
|----------|---------|-------------|---------|
| `LLM_PROVIDER` | `openai`, `openrouter`, `ollama` | Primary LLM service | `openai` |
| `LLM_BASE_URL` | URL | Service endpoint | `https://api.openai.com/v1` |
| `LLM_API_KEY` | String | Authentication key | Required |
| `LLM_CHOICE` | Model name | Model identifier | `gpt-4o-mini` |

#### Embedding Provider Settings
| Variable | Options | Description | Default |
|----------|---------|-------------|---------|
| `EMBEDDING_PROVIDER` | `openai`, `ollama` | Embedding service | `openai` |
| `EMBEDDING_BASE_URL` | URL | Service endpoint | `https://api.openai.com/v1` |
| `EMBEDDING_API_KEY` | String | Authentication key | Required |
| `EMBEDDING_MODEL_CHOICE` | Model name | Embedding model | `text-embedding-3-small` |

### Agentic RAG Settings (New)

#### Neo4j Knowledge Graph
| Variable | Description | Example |
|----------|-------------|---------|
| `NEO4J_URI` | Neo4j connection URI | `bolt://localhost:7687` |
| `NEO4J_USER` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | `your-password` |

#### Agentic RAG Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `ENABLE_GRAPH` | Enable knowledge graph features | `true` |
| `ENABLE_CACHING` | Enable result caching | `true` |
| `PARALLEL_SEARCH` | Enable parallel search execution | `true` |
| `CHUNK_SIZE` | Document chunk size in tokens | `1000` |
| `CHUNK_OVERLAP` | Chunk overlap for context | `200` |
| `MAX_ENTITIES_PER_CHUNK` | Entity extraction limit | `10` |
| `MAX_FACT_LENGTH` | Maximum fact description length | `500` |
| `EXTRACTION_MODEL` | Model for knowledge extraction | `gpt-4o-mini` |

#### Performance Settings
| Variable | Description | Default |
|----------|-------------|---------|
| `VECTOR_SEARCH_TIMEOUT` | Vector search timeout (seconds) | `2.0` |
| `GRAPH_SEARCH_TIMEOUT` | Graph search timeout (seconds) | `3.0` |
| `EMBEDDING_CACHE_SIZE` | Embedding cache size | `1000` |
| `EMBEDDING_CACHE_TTL` | Cache TTL in seconds | `3600` |
| `GRAPH_CACHE_SIZE` | Graph result cache size | `500` |
| `GRAPH_CACHE_TTL` | Graph cache TTL in seconds | `1800` |

### Optional Settings

#### Search Provider Settings
| Variable | Description | Default |
|----------|-------------|---------|
| `BRAVE_API_KEY` | Brave Search API key | Empty (uses SearXNG) |
| `SEARXNG_BASE_URL` | SearXNG instance URL | `http://localhost:8080` |

#### Agent Settings
| Variable | Description | Default |
|----------|-------------|---------|
| `AGENT_NAME` | Agent display name | `Luminari` |
| `AGENT_TEMPERATURE` | LLM temperature setting (0.0-1.0) | `0.7` |
| `VISION_LLM_CHOICE` | Vision model for image analysis | Same as `LLM_CHOICE` |

#### Feature Flags
| Variable | Options | Description | Default |
|----------|---------|-------------|---------|
| `ENABLE_CODE_EXECUTION` | `true`, `false` | Enable/disable code execution tool | `false` |
| `ENABLE_WEB_SEARCH` | `true`, `false` | Enable/disable web search functionality | `true` |
| `ENABLE_IMAGE_ANALYSIS` | `true`, `false` | Enable/disable image analysis | `true` |
| `ENABLE_LONG_TERM_MEMORY` | `true`, `false` | Enable/disable persistent memory | `true` |
| `ENABLE_RAG` | `true`, `false` | Enable/disable RAG functionality | `true` |

#### Optional Integrations
| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_DRIVE_FOLDER_ID` | Google Drive folder ID for document sync | No |
| `GOOGLE_DRIVE_CREDENTIALS_PATH` | Path to Google credentials JSON | No |

## Database Schema Setup

### Required Tables

Execute these SQL scripts in your Supabase SQL Editor in order:

1. **[`sql/documents.sql`](../sql/documents.sql)** - Vector document storage
   - Creates `documents` table with pgvector extension
   - `id`: Primary key (bigserial)
   - `content`: Document text content
   - `metadata`: JSONB metadata (file_id, file_title, file_url)
   - `embedding`: Vector column (1536 for OpenAI, 768 for Ollama)
   - Includes `match_documents` function for vector search

2. **[`sql/document_metadata.sql`](../sql/document_metadata.sql)** - Document metadata
   - Creates `document_metadata` table
   - Document titles, schemas, source URLs
   - File type and processing information

3. **[`sql/document_rows.sql`](../sql/document_rows.sql)** - Structured data storage
   - Creates `document_rows` table
   - Tabular data from CSV/Excel stored as JSONB
   - `dataset_id` references document file_id

4. **[`sql/execute_sql_rpc.sql`](../sql/execute_sql_rpc.sql)** - Secure query execution
   - Creates `execute_custom_sql` RPC function
   - Read-only SQL execution with security validation
   - SQL injection protection and operation validation

### Agentic RAG Database Setup

#### PostgreSQL/Supabase Schema
Execute [`sql/agentic_rag/schema.sql`](../sql/agentic_rag/schema.sql) after the standard setup:

```sql
-- Enhanced chunks table with entity references
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536), -- Or 768 for Ollama
    chunk_index INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}', -- Includes entity_refs
    token_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for entity references
CREATE INDEX idx_chunks_entity_refs ON chunks
    USING GIN ((metadata->'entity_refs'));
```

#### Neo4j Knowledge Graph Setup

```bash
# Docker deployment
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# Or use Neo4j Aura cloud instance
# Initialize the graph
python -m EXAMPLE_agentic-rag-knowledge-graph.agent.graph_utils init
```

### Vector Dimension Configuration

**OpenAI Embeddings (default):**
```sql
embedding vector(1536)
query_embedding vector(1536)
```

**Ollama Embeddings:**
```sql
embedding vector(768)
query_embedding vector(768)
```

**Multiple Embedding Models:**
The Agentic RAG system supports multiple embedding models simultaneously:
```sql
-- Multi-model support
embedding_openai vector(1536)
embedding_nomic vector(768)
embedding_model TEXT -- Track which model was used
```

**Important:** Update vector dimensions in SQL scripts before execution for Ollama deployments. Change all instances of `vector(1536)` to `vector(768)` in the SQL files.

## Provider-Specific Configuration Examples

### OpenAI (Default)
```bash
# Core LLM
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-openai-key
LLM_CHOICE=gpt-4o-mini

# Embeddings
EMBEDDING_PROVIDER=openai
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=sk-your-openai-key
EMBEDDING_MODEL_CHOICE=text-embedding-3-small

# Vision model
VISION_LLM_CHOICE=gpt-4o-mini
```

### OpenRouter
```bash
# Core LLM
LLM_PROVIDER=openrouter
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-your-openrouter-key
LLM_CHOICE=anthropic/claude-3-sonnet

# Embeddings (still use OpenAI)
EMBEDDING_PROVIDER=openai
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=sk-your-openai-key
EMBEDDING_MODEL_CHOICE=text-embedding-3-small

# Vision model
VISION_LLM_CHOICE=anthropic/claude-3-sonnet
```

### Ollama (Local)
```bash
# Core LLM
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_CHOICE=llama3.1

# Embeddings
EMBEDDING_PROVIDER=ollama
EMBEDDING_BASE_URL=http://localhost:11434
EMBEDDING_MODEL_CHOICE=nomic-embed-text

# Vision model
VISION_LLM_CHOICE=llava
```

### Anthropic Claude (via API)
```bash
# Core LLM
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-your-key
LLM_CHOICE=claude-3-5-sonnet-20241022

# Use OpenAI for embeddings
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=sk-your-openai-key
EMBEDDING_MODEL_CHOICE=text-embedding-3-small
```

### Google Gemini
```bash
# Core LLM
LLM_PROVIDER=gemini
LLM_API_KEY=your-gemini-key
LLM_CHOICE=gemini-1.5-pro

# Use OpenAI for embeddings
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=sk-your-openai-key
EMBEDDING_MODEL_CHOICE=text-embedding-3-small
```

### Agentic RAG Full Configuration (Phase 3)
```bash
# PostgreSQL/Supabase (Required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
DATABASE_URL=${SUPABASE_URL}  # For mem0 compatibility

# Neo4j Knowledge Graph (Required for Agentic RAG)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# LLM Configuration (Required)
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-key
LLM_CHOICE=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_TEMPERATURE=0.7

# Extraction Model (for knowledge extraction)
EXTRACTION_MODEL=gpt-4o-mini

# Embedding Configuration (Required)
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=sk-your-key
EMBEDDING_MODEL_CHOICE=text-embedding-3-small
EMBEDDING_BASE_URL=https://api.openai.com/v1

# Vision Model Configuration
VISION_LLM_CHOICE=gpt-4o-mini

# Agent Settings
AGENT_NAME=Luminari
AGENT_TEMPERATURE=0.7

# Agentic RAG Core Settings
ENABLE_GRAPH=true
ENABLE_CACHING=true
PARALLEL_SEARCH=true
ENABLE_INTENT_ANALYSIS=true
ENABLE_SMART_ROUTING=true

# Document Processing
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_ENTITIES_PER_CHUNK=10
MAX_FACT_LENGTH=500
SEMANTIC_CHUNKING=true

# Performance Timeouts
VECTOR_SEARCH_TIMEOUT=2.0
GRAPH_SEARCH_TIMEOUT=3.0
INTENT_ANALYSIS_TIMEOUT=1.0
RESPONSE_GENERATION_TIMEOUT=5.0

# Caching Configuration
EMBEDDING_CACHE_SIZE=1000
EMBEDDING_CACHE_TTL=3600
GRAPH_CACHE_SIZE=500
GRAPH_CACHE_TTL=1800
INTENT_CACHE_SIZE=200
INTENT_CACHE_TTL=900

# Search Strategy Thresholds
VECTOR_SIMILARITY_THRESHOLD=0.7
GRAPH_CONFIDENCE_THRESHOLD=0.5
HYBRID_BOOST_FACTOR=0.2
MAX_SEARCH_RESULTS=10

# Tool Settings
ENABLE_CODE_EXECUTION=false
ENABLE_WEB_SEARCH=true
ENABLE_IMAGE_ANALYSIS=true
ENABLE_LONG_TERM_MEMORY=true
ENABLE_RAG=true
ENABLE_SQL_QUERIES=true

# Search Provider Settings
BRAVE_API_KEY=your_brave_api_key
SEARXNG_BASE_URL=http://localhost:8080

# Google Drive Integration (Optional)
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
GOOGLE_DRIVE_CREDENTIALS_PATH=config/google_credentials.json

# MCP Server Configuration (Optional)
ENABLE_MCP_CODE_EXECUTION=false
MCP_SERVER_URL=http://localhost:3000

# Logging and Monitoring
LOG_LEVEL=INFO
ENABLE_STRUCTURED_LOGGING=true
ENABLE_PERFORMANCE_METRICS=true
ENABLE_ERROR_TRACKING=true

# Development Settings
DEBUG_MODE=false
ENABLE_DEBUG_LOGGING=false
SKIP_AUTH_FOR_TESTING=false

# Important Notes:
# - For Ollama: Change vector dimensions from 1536 to 768 in SQL scripts
# - For production: Set DEBUG_MODE=false and enable authentication
# - For testing: Use separate database instances
```

## Environment File Template

Copy the example environment file and customize:
```bash
cp .env.example .env
# Edit .env with your credentials
```

The `.env.example` file contains all available configuration options with sensible defaults.
