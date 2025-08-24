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
# Run RAG pipeline for local files
make run-rag

# Or run directly with source specification
python -m src.rag_pipeline.pipeline --source local --interval 60

# For Google Drive integration
python -m src.rag_pipeline.pipeline --source google_drive --interval 60
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

#### Built-in Custom Sandboxed Execution (Default)

The agent uses a custom safe execution environment implemented in [`src/tools/code_execution.py`](../src/tools/code_execution.py):

**Whitelisted Modules:**
- Core Python libraries: `math`, `datetime`, `json`, `csv`, `re`, `statistics`, etc.
- Data structures: `collections`, `itertools`, `functools`, `heapq`, `bisect`
- Optional packages (if installed): `numpy`, `pandas`, `scipy`

**Security Features:**
- No file system access (except temp/io)
- No network access
- Restricted import system
- Safe built-ins only
- Custom print function for output capture

**Configuration:**
- Enabled by default in [`src/agent/agent.py`](../src/agent/agent.py) (lines 187-201)
- Uses `execute_safe_code_tool` from [`src/tools/code_execution.py`](../src/tools/code_execution.py)
- Can be disabled via `ENABLE_CODE_EXECUTION=false` in `.env`

#### Alternative: MCP Code Execution Server (Optional)

For enhanced capabilities, you can use the MCP (Model Context Protocol) server:

**Setup:**
1. Install Deno: https://deno.land/
2. Run MCP server:
   ```bash
   deno run -N -R=node_modules -W=node_modules --node-modules-dir=auto jsr:@pydantic/mcp-run-python sse
   ```
3. Configure MCP in [`src/agent/agent.py`](../src/agent/agent.py) (see comments in the file)
4. Comment out the built-in `execute_code` tool

**Benefits:**
- More powerful execution environment
- Better resource management
- Enhanced security isolation

## Agent Tools Reference

### Document Retrieval Tools

#### `retrieve_relevant_documents`
- **Function**: Vector similarity search using pgvector
- **Returns**: Top 4 most relevant document chunks with metadata
- **Implementation**: [`src/tools/rag.py:retrieve_relevant_documents_tool`](../src/tools/rag.py)
- **Usage**: Automatic context retrieval for user queries

#### `list_documents`
- **Function**: Enumerate all available documents
- **Returns**: List of documents from `document_metadata` table with schemas
- **Implementation**: [`src/tools/rag.py:list_documents_tool`](../src/tools/rag.py)
- **Usage**: Discover available documents and their IDs

#### `get_document_content`
- **Function**: Retrieve full document content by combining chunks
- **Returns**: Complete document text (limited to 20,000 characters)
- **Implementation**: [`src/tools/rag.py:get_document_content_tool`](../src/tools/rag.py)
- **Usage**: Access entire document content when needed

#### `execute_sql_query`
- **Function**: Execute read-only SQL queries on structured data
- **Returns**: Query results in JSON format
- **Implementation**: [`src/tools/sql_query.py:execute_sql_query_tool`](../src/tools/sql_query.py)
- **Usage**: Query CSV/Excel data stored in `document_rows` table

### External Service Tools

#### `web_search`
- **Function**: Internet search with dual provider support
- **Primary**: Brave Search API (summarized results)
- **Fallback**: SearXNG (detailed result listings)
- **Implementation**: [`src/tools/web_search.py:web_search_tool`](../src/tools/web_search.py)
- **Configuration**: `BRAVE_API_KEY` and `SEARXNG_BASE_URL`

#### `image_analysis`
- **Function**: Vision model analysis of stored images
- **Model**: Configurable via `VISION_LLM_CHOICE` (default: `gpt-4o-mini`)
- **Implementation**: [`src/tools/image_analysis.py:image_analysis_tool`](../src/tools/image_analysis.py)
- **Usage**: Analyze images based on user queries

### Code Execution Tool

#### `execute_code`
- **Function**: Sandboxed Python code execution
- **Security**: Custom whitelist-based execution environment
- **Implementation**: [`src/tools/code_execution.py:execute_safe_code_tool`](../src/tools/code_execution.py)
- **Output**: Results captured via custom print function
- **Libraries**: Core Python + optional numpy/pandas/scipy

### Memory Management

#### Long-term Memory (mem0)
- **Integration**: Automatic conversation memory via mem0
- **Backend**: Supabase with vector similarity
- **Features**: User-isolated, deduplicated, persistent across sessions
- **Configuration**: [`src/clients/memory.py`](../src/clients/memory.py)
- **Control**: `ENABLE_LONG_TERM_MEMORY` environment variable

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
