# Architecture

## Directory Structure
```
base_agent/
├── src/                       # Core agent implementation
│   ├── agent.py               # Pydantic AI agent with tool definitions
│   ├── clients.py             # Client factories for LLM, embedding, memory services
│   ├── tools.py               # Tool implementations (web search, RAG, code execution)
│   ├── prompt.py              # System prompt configuration
│   └── ui/                    # Web interface (Streamlit)
├── RAG_Pipeline/              # Document processing pipelines
│   ├── common/                # Shared utilities
│   │   ├── db_handler.py      # Database operations for document storage
│   │   └── text_processor.py  # Text chunking and preprocessing
│   ├── Google_Drive/          # Google Drive document sync
│   └── Local_Files/           # Local filesystem document sync
├── sql/                       # Database schema definitions
│   ├── documents.sql          # Vector document storage table
│   ├── document_metadata.sql  # Document metadata table
│   ├── document_rows.sql      # Tabular data storage
│   └── execute_sql_rpc.sql    # Secure SQL execution function
├── tests/                     # Unit and integration tests

```

## Database Schema
- **documents**: Vector embeddings with pgvector (1536 or 768 dimensions)
- **document_metadata**: File metadata, schemas, and source URLs
- **document_rows**: Structured data from CSV/Excel files as JSONB
- **mem0_memories**: Long-term conversation memory storage
