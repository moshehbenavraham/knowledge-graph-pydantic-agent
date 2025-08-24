# Usage

## Document Processing Pipeline

### Architecture Overview
The RAG pipeline monitors document sources and processes files for vector storage. Supports multiple document sources with extensible architecture for custom integrations.

### Supported File Formats
- **Text**: `.txt`, `.md`, `.py`, `.js`, `.html`, `.css`
- **Documents**: `.pdf`, `.docx`
- **Spreadsheets**: `.csv`, `.xlsx` (structured data extraction)
- **Images**: `.jpg`, `.png`, `.gif` (metadata + vision analysis)

### Local Files Pipeline

The RAG pipeline processes documents from local filesystem or Google Drive.

**Configuration:** Environment variables in `.env`:
```bash
# Text processing settings
EMBEDDING_MODEL_CHOICE=text-embedding-3-small
EMBEDDING_API_KEY=your_openai_api_key
EMBEDDING_BASE_URL=https://api.openai.com/v1

# Database settings
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
```

**Execution:**
```bash
# Run RAG pipeline
make run-rag

# Or run directly
python -m src.rag_pipeline.pipeline
```

**Processing Settings (configurable in code):**
- **Chunk Size:** 400 characters (default)
- **Chunk Overlap:** 0 characters (default)
- **Supported Formats:** PDF, DOCX, TXT, MD, CSV, XLSX, images
- **Embedding Model:** Configurable via `EMBEDDING_MODEL_CHOICE`

### Google Drive Pipeline

**Setup Requirements:**
1. Google Cloud Console project with Drive API enabled
2. OAuth 2.0 credentials (Desktop Application type)
3. Configure environment variables for Google Drive folder ID

**Configuration:** In `.env`:
```bash
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
GOOGLE_DRIVE_CREDENTIALS_PATH=config/google_credentials.json
```

**Features:**
- OAuth 2.0 authentication flow
- Folder-based document monitoring
- Automatic processing of new/changed files
- Binary file support with base64 encoding for images

### Pipeline Architecture

The RAG pipeline is located at [`src/rag_pipeline/`](../src/rag_pipeline/) with:
- [`common/db_handler.py`](../src/rag_pipeline/common/db_handler.py): Database operations
- [`common/text_processor.py`](../src/rag_pipeline/common/text_processor.py): Text processing and embeddings
- [`sources/google_drive.py`](../src/rag_pipeline/sources/google_drive.py): Google Drive integration
- [`sources/local_files.py`](../src/rag_pipeline/sources/local_files.py): Local file processing

## Running the Agent

### Streamlit Web Interface

**Start the agent:**
```bash
# Standard UI
make run-ui

# Development mode with auto-reload
make dev

# Or run directly
streamlit run src/ui/streamlit_app.py
```

**Access:** http://localhost:8501

**UI Variants:**
- [`streamlit_app.py`](../src/ui/streamlit_app.py): Full-featured UI with memory
- [`streamlit_ui_simple.py`](../src/ui/streamlit_ui_simple.py): Simplified interface
- [`streamlit_ui_streaming.py`](../src/ui/streamlit_ui_streaming.py): Streaming responses

**Features:**
- Real-time chat interface
- File upload for document processing
- Conversation history with persistent memory
- Tool execution visibility and feedback
- Multiple LLM provider selection

### Code Execution Options

#### Option 1: Built-in Custom Sandboxed Execution (Default)
Uses custom safe execution environment with whitelisted modules:
- Core Python libraries (math, datetime, json, etc.)
- Optional: numpy, pandas, scipy (if installed)
- No file system or network access
- Enabled by default in [`src/agent/agent.py`](../src/agent/agent.py:187)

#### Option 2: MCP Code Execution Server (Optional)
Enhanced code execution via Pydantic AI MCP integration:

**Setup:**
1. Install Deno: https://deno.land/
2. Run MCP server:
   ```bash
   deno run -N -R=node_modules -W=node_modules --node-modules-dir=auto jsr:@pydantic/mcp-run-python sse
   ```
3. Enable in [`src/agent/agent.py`](../src/agent/agent.py):
   ```python
   # Add MCP server configuration (see agent.py comments for details)
   # Comment out the built-in execute_code tool (lines 187-201)
   ```

**Benefits:**
- More powerful execution environment
- Better resource management
- Enhanced security features

## Agent Tools Reference

### Document Retrieval Tools
- **`retrieve_relevant_documents`**: Vector similarity search, returns top 4 most relevant chunks with metadata
- **`list_documents`**: Enumerate all available documents with metadata from `document_metadata` table
- **`get_document_content`**: Retrieve full document content by combining chunks (20,000 character limit)
- **`execute_sql_query`**: Execute read-only SQL queries on structured data in `document_rows` table

### External Service Tools
- **`web_search`**: Internet search via Brave API (primary) or SearXNG (fallback)
  - Brave API: Returns summarized results
  - SearXNG: Returns top search results with snippets
- **`image_analysis`**: Vision model analysis of images stored in the knowledge base
  - Uses configurable vision model (default: `gpt-4o-mini`)
  - Analyzes images based on provided queries

### Code Execution Tool
- **`execute_code`**: Sandboxed Python execution with RestrictedPython
  - Whitelisted modules only
  - No file system or network access
  - Results returned via print statements

### Memory Management
- **Automatic conversation memory** via mem0 integration
- **Persistent across sessions** with Supabase backend
- **User-isolated memory** with deduplication
- **Configurable via environment variables**

## Configuration Examples

### Multi-Provider Setup
```bash
# Primary LLM
LLM_PROVIDER=openai
LLM_CHOICE=gpt-4o-mini

# Vision model for images
VISION_LLM_CHOICE=gpt-4o-mini

# Embedding model
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL_CHOICE=text-embedding-3-small

# Search providers
BRAVE_API_KEY=your_brave_api_key  # Primary
SEARXNG_BASE_URL=http://localhost:8080  # Fallback
```

### Local Ollama Setup
```bash
# Use Ollama for LLM
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_CHOICE=llama3.1

# Use Ollama for embeddings
EMBEDDING_PROVIDER=ollama
EMBEDDING_BASE_URL=http://localhost:11434
EMBEDDING_MODEL_CHOICE=nomic-embed-text

# Update SQL scripts for 768-dimensional embeddings
# Change vector(1536) to vector(768) in sql/*.sql files
```
