# Configuration

## Environment Variables

### LLM Provider Settings
| Variable | Options | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai`, `openrouter`, `ollama` | Primary LLM service |
| `LLM_BASE_URL` | URL | Service endpoint (e.g., `https://api.openai.com/v1`) |
| `LLM_API_KEY` | String | Authentication key |
| `LLM_CHOICE` | Model name | Model identifier (e.g., `gpt-4o-mini`) |
| `VISION_LLM_CHOICE` | Model name | Vision-capable model for image analysis |

### Embedding Provider Settings
| Variable | Options | Description |
|----------|---------|-------------|
| `EMBEDDING_PROVIDER` | `openai`, `ollama` | Embedding service |
| `EMBEDDING_BASE_URL` | URL | Service endpoint |
| `EMBEDDING_API_KEY` | String | Authentication key |
| `EMBEDDING_MODEL_CHOICE` | Model name | Embedding model (e.g., `text-embedding-3-small`) |

### Database Configuration
| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Supabase connection for mem0 (same as SUPABASE_URL) | `https://xxx.supabase.co` |
| `SUPABASE_URL` | Supabase project URL | `https://xxx.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | `eyJ...` |

### Search Provider Settings
| Variable | Description | Default |
|----------|-------------|---------|
| `BRAVE_API_KEY` | Brave Search API key | None (uses SearXNG) |
| `SEARXNG_BASE_URL` | SearXNG instance URL | `http://localhost:8080` |

## Database Schema Setup

### Required Tables

Execute these SQL scripts in your Supabase SQL Editor:

1. **`sql/documents.sql`** - Vector document storage
   - `id`: Primary key (bigserial)
   - `content`: Document text content
   - `metadata`: JSONB metadata (file_id, file_title, file_url)
   - `embedding`: Vector column (1536 for OpenAI, 768 for Ollama)

2. **`sql/document_metadata.sql`** - Document metadata
   - Document titles, schemas, source URLs
   - File type and processing information

3. **`sql/document_rows.sql`** - Structured data storage
   - Tabular data from CSV/Excel as JSONB
   - `dataset_id` references document file_id

4. **`sql/execute_sql_rpc.sql`** - Secure query execution
   - Read-only RPC function `execute_custom_sql`
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

Update vector dimensions in SQL scripts before execution for Ollama deployments.
