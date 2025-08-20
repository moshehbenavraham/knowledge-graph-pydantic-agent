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

**Configuration (`RAG_Pipeline/Local_Files/config.json`):**
```json
{
  "watch_directory": "/path/to/documents",
  "chunk_size": 1000,
  "chunk_overlap": 200,
  "supported_extensions": [".pdf", ".txt", ".md", ".docx", ".csv", ".xlsx"]
}
```

**Execution:**
```bash
cd RAG_Pipeline
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
python Local_Files/main.py --interval 60  # Check every 60 seconds
```

**Features:**
- Recursive directory monitoring
- Automatic file change detection
- Delta sync (only process changed files)
- Configurable check intervals

### Google Drive Pipeline

**Setup Requirements:**
1. Google Cloud Console project with Drive API enabled
2. OAuth 2.0 credentials (Desktop Application type)
3. Save credentials as `RAG_Pipeline/Google_Drive/credentials.json`

**Configuration (`RAG_Pipeline/Google_Drive/config.json`):**
```json
{
  "watch_directory": "google_drive_folder_id",
  "chunk_size": 1000,
  "chunk_overlap": 200
}
```

**Execution:**
```bash
cd RAG_Pipeline
source .venv/bin/activate
python Google_Drive/main.py --interval 60
```

**Features:**
- OAuth 2.0 authentication flow
- Folder-based monitoring
- Change detection via Drive API
- Binary file support with base64 encoding

### Pipeline Extensibility

Create custom pipelines by implementing:
- Document source connector (API client)
- File enumeration and change detection
- Integration with `RAG_Pipeline/common/` utilities

## Running the Agent

### Streamlit Web Interface

**Start the agent:**
```bash
cd base_agent
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
streamlit run src/ui/streamlit_app.py
```

**Access:** http://localhost:8501

**Features:**
- Real-time chat interface
- File upload for image analysis
- Conversation history
- Tool execution visibility

### Code Execution Options

#### Option 1: Built-in RestrictedPython (Default)
Uses RestrictedPython 8.0 for sandboxed execution with whitelisted modules:
- Core Python libraries (math, datetime, json, etc.)
- Optional: numpy, pandas, scipy (if installed)
- No file system or network access

#### Option 2: MCP Code Execution Server
Enhanced code execution via Pydantic AI MCP integration:

**Setup:**
1. Install Deno: https://github.com/denoland/deno/
2. Run MCP server:
   ```bash
   deno run -N -R=node_modules -W=node_modules --node-modules-dir=auto jsr:@pydantic/mcp-run-python sse
   ```
3. Enable in `src/agent.py`:
   ```python
   # Uncomment these lines:
   code_execution_server = MCPServerHTTP(url='http://localhost:3001/sse')
   # Add to agent: mcp_servers=[code_execution_server]
   # Comment out the built-in execute_code tool
   ```

## Agent Tools Reference

### Document Retrieval
- **`retrieve_relevant_documents`**: Vector similarity search, returns top 4 chunks
- **`list_documents`**: Enumerate all available documents with metadata
- **`get_document_content`**: Retrieve full document content (20,000 char limit)
- **`execute_sql_query`**: Query structured data with read-only SQL validation

### External Services
- **`web_search`**: Internet search via Brave API or SearXNG
- **`image_analysis`**: Vision model analysis of stored images

### Code Execution
- **`execute_code`**: Sandboxed Python execution with module restrictions

### Memory Management
- Automatic conversation memory via mem0 integration
- Persistent across sessions with PostgreSQL backend
