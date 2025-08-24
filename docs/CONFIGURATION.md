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
VISION_LLM_CHOICE=llava:latest

# Important: Update SQL scripts to use vector(768) instead of vector(1536)
```

## Environment File Template

Copy the example environment file and customize:
```bash
cp .env.example .env
# Edit .env with your credentials
```

The `.env.example` file contains all available configuration options with sensible defaults.
