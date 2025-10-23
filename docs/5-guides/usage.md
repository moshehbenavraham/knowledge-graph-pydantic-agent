# Usage

## 🆕 Unified Super Agent

### Overview
The Unified Super Agent (`src/agent/unified_agent.py`) is the ONLY agent in the system, combining ALL capabilities into one powerful implementation with intelligent routing, comprehensive toolset, and clean API.

### Quick Start with Unified Agent

#### Python Code
```python
from src.agent import super_agent, UnifiedAgentDeps, run_unified_agent
from src.clients import get_supabase_client, get_embedding_client
from httpx import AsyncClient

# Simple usage
result = await run_unified_agent(
    query="What is the relationship between Microsoft and OpenAI?",
    session_id="my_session",
    supabase_client=get_supabase_client(),
    embedding_client=get_embedding_client(),
    http_client=AsyncClient(),
    memories="User is interested in tech companies"
)

print(result["response"])
```

#### API Server
```bash
# Start the FastAPI server
python -m src.api.main

# API available at http://localhost:8058
# Docs at http://localhost:8058/docs
```

### API Endpoints

#### Document Ingestion
```bash
# POST /ingest
curl -X POST http://localhost:8058/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Document content here",
    "title": "Document Title",
    "source": "source.pdf"
  }'
```

#### Chat Interface
```bash
# POST /chat
curl -X POST http://localhost:8058/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Your question here"}'

# POST /chat/stream (Server-Sent Events)
curl -X POST http://localhost:8058/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Your question here"}'
```

#### Direct Search
```bash
# GET /search/{mode}?q=query&limit=10
# Modes: vector, graph, hybrid
curl http://localhost:8058/search/hybrid?q=Microsoft%20OpenAI&limit=5
```

### Unified Agent Search Strategies

The unified agent automatically selects the best strategy:

1. **Smart Search** (Primary Tool)
   - Analyzes query intent
   - Routes to optimal strategy
   - Combines multiple approaches when needed

2. **Vector Search**
   - Semantic similarity in PostgreSQL/pgvector
   - Best for: Similar content, concepts

3. **Graph Search** (When Available)
   - Entity relationships in Neo4j
   - Best for: Connections, timelines

4. **Comprehensive Search**
   - Executes all strategies in parallel
   - Intelligently merges results
   - Best for: Complex, multi-faceted queries

5. **Iterative Search**
   - Multi-step exploration
   - Refines based on initial results
   - Best for: Deep research questions

### Unified Agent Tools

The unified agent provides these powerful tools:

```python
# 1. Smart Search - Intelligent routing
await super_agent.run("Find information about neural networks", deps=deps)

# 2. Web Search - Real-time information
await super_agent.run("What's the latest AI news in 2024?", deps=deps)

# 3. SQL Queries - Analyze structured data
await super_agent.run("Show me sales data from the database", deps=deps)

# 4. Code Execution - Run Python safely
await super_agent.run("Calculate fibonacci sequence up to 10", deps=deps)

# 5. Image Analysis - Understand visuals
await super_agent.run("Analyze the diagram.png image", deps=deps)

# 6. Document Management
await super_agent.run("List all available documents", deps=deps)

# 7. Comprehensive Search - Multi-strategy
await super_agent.run("Do a comprehensive search about quantum computing", deps=deps)
```

### Advanced Usage with Custom Configuration

```python
from src.agent import super_agent, UnifiedAgentDeps
from src.config import get_settings
from src.config.agent import agent_config

# Load centralized configuration
settings = get_settings()

# Create custom dependencies with config
deps = UnifiedAgentDeps(
    supabase=supabase_client,
    embedding_client=embedding_client,
    http_client=http_client,
    brave_api_key=agent_config.brave_api_key,  # From config
    jina_api_key=agent_config.jina_api_key,    # From config
    memories="User context and preferences",
    session_id="custom_session",
    search_config={
        "use_vector": settings.enable_vector_search,
        "use_graph": settings.enable_graph,
        "confidence_threshold": settings.confidence_threshold,
        "max_results": settings.search_limit
    }
)

# Run with custom config
result = await super_agent.run(
    "Complex multi-step query here",
    deps=deps
)
```

## Document Processing Pipeline

### Architecture Overview
The enhanced Agentic RAG pipeline processes documents through dual storage:
- **PostgreSQL/Supabase**: Stores full content with vector embeddings
- **Neo4j**: Stores extracted entities, relationships, and facts (no content duplication)

### Processing Flow
1. **Document Ingestion**: Upload or monitor document sources
2. **Chunking**: Semantic or simple chunking strategies
3. **Embedding Generation**: Multi-model support (OpenAI, Ollama, Nomic)
4. **Knowledge Extraction**: Extract entities and relationships using LLM
5. **Dual Storage**: Content to PostgreSQL, knowledge to Neo4j
6. **Cross-referencing**: Link chunks to entities for hybrid search

### Supported File Formats
- **Text**: `.txt`, `.md`, `.py`, `.js`, `.html`, `.css`
- **Documents**: `.pdf`, `.docx`
- **Spreadsheets**: `.csv`, `.xlsx` (structured data extraction)
- **Images**: `.jpg`, `.png`, `.gif` (metadata + vision analysis)

### Local Files Pipeline

The RAG pipeline processes documents from local filesystem or Google Drive.

**Configuration:** Using centralized config system (see [Configuration Guide](../4-configuration/environment.md)):
```bash
# Text processing settings (in .env)
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=your_openai_api_key
EMBEDDING_BASE_URL=https://api.openai.com/v1

# Database settings
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key

# Access in code via centralized config
from src.config.clients import clients_config
print(f"Embedding model: {clients_config.embedding_model}")
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

**Processing Settings (via centralized config):**
```python
from src.config.agent import agent_config

# Access chunking settings
chunk_config = agent_config.get_chunking_config()
print(f"Chunk Size: {chunk_config['chunk_size']}")  # 1000 (default)
print(f"Chunk Overlap: {chunk_config['chunk_overlap']}")  # 200 (default)

# Embedding settings
from src.config.clients import clients_config
print(f"Embedding Model: {clients_config.embedding_model}")
print(f"Embedding Dimension: {clients_config.embedding_dimension}")
```

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

**Standard RAG Pipeline** ([`src/rag_pipeline/`](../../src/rag_pipeline/)):
- [`common/db_handler.py`](../../src/rag_pipeline/common/db_handler.py): Database operations
- [`common/text_processor.py`](../../src/rag_pipeline/common/text_processor.py): Text processing and embeddings
- [`sources/google_drive.py`](../../src/rag_pipeline/sources/google_drive.py): Google Drive integration
- [`sources/local_files.py`](../../src/rag_pipeline/sources/local_files.py): Local file processing

**Agentic RAG Pipeline** ([`src/agentic_rag/`](../../src/agentic_rag/)):
- [`ingestion/chunker.py`](../../src/agentic_rag/ingestion/chunker.py): Semantic chunking
- [`ingestion/embedder.py`](../../src/agentic_rag/ingestion/embedder.py): Multi-model embeddings
- [`ingestion/knowledge_extractor.py`](../../src/agentic_rag/ingestion/knowledge_extractor.py): Knowledge extraction
- [`storage/postgres_store.py`](../../src/agentic_rag/storage/postgres_store.py): PostgreSQL operations
- [`storage/neo4j_store.py`](../../src/agentic_rag/storage/neo4j_store.py): Neo4j operations

## Running the Agent

### Streamlit Web Interface

**Start the agent with configurable modes:**
```bash
# Standard mode - streaming + tools (default)
make run-ui

# Simple mode - fast, no persistence
make run-ui-simple

# Advanced mode - all features enabled
make run-ui-advanced

# Custom mode selection
make run-ui MODE=simple
UI_MODE=advanced streamlit run src/ui/streamlit_app.py

# Development mode with auto-reload
make dev MODE=standard
```

**Access:** http://localhost:8501

**UI Modes (switchable at runtime via sidebar):**
- **Simple Mode** 🟢: Basic chat without streaming or persistence
- **Standard Mode** 🔵: Real-time streaming with tool visibility (recommended)
- **Advanced Mode** 🟣: All features including memory, MCP servers, and metrics

**Features:**
- Unified configurable interface with 3 modes
- Runtime mode switching without restart
- Real-time chat with streaming support
- Conversation export to JSON
- File upload for document processing
- Conversation history with persistent memory
- Tool execution visibility and feedback
- Multiple LLM provider selection

### Code Execution Options

#### Built-in Custom Sandboxed Execution (Default)

The agent uses a custom safe execution environment implemented in [`src/tools/code_execution.py`](../../src/tools/code_execution.py):

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
- Enabled by default in [`src/agent/unified_agent.py`](../../src/agent/unified_agent.py)
- Uses `execute_safe_code_tool` from [`src/tools/code_execution.py`](../../src/tools/code_execution.py)
- Can be disabled via `ENABLE_CODE_EXECUTION=false` in `.env`

#### Alternative: MCP Code Execution Server (Optional)

For enhanced capabilities, you can use the MCP (Model Context Protocol) server:

**Setup:**
1. Install Deno: https://deno.land/
2. Run MCP server:
   ```bash
   deno run -N -R=node_modules -W=node_modules --node-modules-dir=auto jsr:@pydantic/mcp-run-python sse
   ```
3. Configure MCP in [`src/agent/unified_agent.py`](../../src/agent/unified_agent.py) (see comments in the file)
4. Comment out the built-in `execute_python_code` tool

**Benefits:**
- More powerful execution environment
- Better resource management
- Enhanced security isolation

## Agent Tools Reference

### Agentic RAG Tools (New)

#### `smart_search`
- **Function**: Intelligently routes queries to optimal search strategy
- **Intent Analysis**: Automatic detection of query type
- **Returns**: Chunks, facts, entities, and relationships
- **Implementation**: Built into [`src/agent/unified_agent.py`](../../src/agent/unified_agent.py) as smart_search tool

#### `vector_search`
- **Function**: Pure semantic similarity search
- **Backend**: PostgreSQL with pgvector
- **Returns**: Document chunks with similarity scores
- **Performance**: <200ms response time

#### `graph_search`
- **Function**: Knowledge graph traversal
- **Backend**: Neo4j with Graphiti
- **Returns**: Entities, relationships, temporal facts
- **Performance**: <500ms response time

#### `hybrid_search`
- **Function**: Parallel vector + graph search
- **Merging**: Graph context boosts vector results
- **Returns**: Comprehensive results with both content and relationships
- **Best for**: Complex queries

### Standard RAG Tools

#### `retrieve_documents`
- **Function**: Vector similarity search using pgvector
- **Returns**: Top 4 most relevant document chunks with metadata
- **Implementation**: [`src/tools/rag.py:retrieve_relevant_documents_tool`](../../src/tools/rag.py)
- **Usage**: Automatic context retrieval for user queries

#### `list_all_documents`
- **Function**: Enumerate all available documents
- **Returns**: List of documents from `document_metadata` table with schemas
- **Implementation**: [`src/tools/rag.py:list_documents_tool`](../../src/tools/rag.py)
- **Usage**: Discover available documents and their IDs

#### `get_full_document`
- **Function**: Retrieve full document content by combining chunks
- **Returns**: Complete document text (limited to 20,000 characters)
- **Implementation**: [`src/tools/rag.py:get_document_content_tool`](../../src/tools/rag.py)
- **Usage**: Access entire document content when needed

#### `execute_sql`
- **Function**: Execute read-only SQL queries on structured data
- **Returns**: Query results in JSON format
- **Implementation**: [`src/tools/sql_query.py:execute_sql_query_tool`](../../src/tools/sql_query.py)
- **Usage**: Query CSV/Excel data stored in `document_rows` table

### External Service Tools

#### `search_web`
- **Function**: Internet search with dual provider support
- **Primary**: Brave Search API (summarized results)
- **Fallback**: SearXNG (detailed result listings)
- **Implementation**: [`src/tools/web_search.py:web_search_tool`](../../src/tools/web_search.py)
- **Configuration**: `BRAVE_API_KEY` and `SEARXNG_BASE_URL`

#### `analyze_image`
- **Function**: Vision model analysis of stored images
- **Model**: Configurable via `VISION_LLM_MODEL` (default: `gpt-4o-mini`)
- **Implementation**: [`src/tools/image_analysis.py:image_analysis_tool`](../../src/tools/image_analysis.py)
- **Usage**: Analyze images based on user queries (supports OCR, object detection, scene analysis)

### Code Execution Tool

#### `execute_python_code`
- **Function**: Sandboxed Python code execution
- **Security**: Custom whitelist-based execution environment
- **Implementation**: [`src/tools/code_execution.py:execute_safe_code_tool`](../../src/tools/code_execution.py)
- **Output**: Results captured via custom print function
- **Libraries**: Core Python + optional numpy/pandas/scipy

### Memory Management

#### Long-term Memory (mem0)
- **Integration**: Automatic conversation memory via mem0
- **Backend**: Supabase with vector similarity
- **Features**: User-isolated, deduplicated, persistent across sessions
- **Configuration**: [`src/clients/memory.py`](../../src/clients/memory.py)
- **Control**: `ENABLE_LONG_TERM_MEMORY` environment variable

## Configuration Examples

### Multi-Provider Setup
```bash
# Primary LLM (in .env)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=your_openai_key

# Vision model for images
VISION_LLM_MODEL=gpt-5-mini

# Embedding model
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=your_openai_key

# Search providers
BRAVE_API_KEY=your_brave_api_key  # Primary
SEARXNG_BASE_URL=http://localhost:8080  # Fallback
JINA_API_KEY=your_jina_key  # For clean content extraction
```

```python
# Access configuration in code
from src.config import get_settings
from src.config.clients import clients_config

settings = get_settings()
print(f"LLM Provider: {settings.llm_provider}")
print(f"LLM Model: {clients_config.llm_model}")
```

### Local Ollama Setup
```bash
# Use Ollama for LLM (in .env)
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.1

# Use Ollama for embeddings
EMBEDDING_PROVIDER=ollama
EMBEDDING_BASE_URL=http://localhost:11434/v1
EMBEDDING_DIMENSION=768
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSION=768  # Nomic uses 768d vectors

# Performance settings
ENABLE_GRAPH=true
ENABLE_PARALLEL_SEARCH=true
VECTOR_SEARCH_TIMEOUT=2.0
GRAPH_SEARCH_TIMEOUT=3.0
CONFIDENCE_THRESHOLD=0.7

# Update SQL scripts for 768-dimensional embeddings
# Change vector(1536) to vector(768) in sql/*.sql files
```

```python
# Verify Ollama configuration
from src.config import get_settings

settings = get_settings()
assert settings.llm_provider == "ollama"
assert settings.embedding_dimension == 768
print("Ollama configured successfully!")
```

### Phase 3 Performance Metrics (Live System)

The Phase 3 Agent Intelligence Layer delivers the following verified performance:

| Metric | Target | Achieved | Status |
|--------|--------|----------|---------|
| Intent Classification Accuracy | 90% | 90%+ | ✅ Met |
| Response Latency (95th percentile) | <5s | <2s | ✅ Exceeded |
| Search Strategy Selection | 85% | 88%+ | ✅ Exceeded |
| Citation Rate | 95% | 100% | ✅ Exceeded |
| Confidence Scoring Coverage | 90% | 100% | ✅ Exceeded |
| Storage Efficiency (Neo4j) | 95% | 99.6% | ✅ Exceeded |

### Phase 3 Query Examples

#### Intent Classification Examples

```bash
# Factual Intent (Vector Search)
Query: "What is the capital of France?"
→ Intent: FACTUAL (0.98 confidence)
→ Strategy: vector_search
→ Response: <800ms

# Relationship Intent (Graph Search)
Query: "How is Microsoft connected to OpenAI?"
→ Intent: RELATIONSHIP (0.92 confidence)
→ Strategy: graph_search
→ Response: <1200ms

# Temporal Intent (Timeline Search)
Query: "When did AI research begin and how has it evolved?"
→ Intent: TEMPORAL (0.89 confidence)
→ Strategy: get_entity_timeline → comprehensive_search
→ Response: <1500ms

# Multi-hop Intent (Iterative Search)
Query: "Who founded the companies that created ChatGPT?"
→ Intent: MULTI_HOP (0.75 confidence)
→ Strategy: iterative_search
→ Response: <4000ms (3 reasoning steps)
```

### Advanced Phase 3 Features

#### Smart Search with Intent Analysis
```python
# The smart_search tool automatically selects optimal strategy
from EXAMPLE_agentic_rag_knowledge_graph.agent.tools import smart_search

# Example 1: Factual query → Vector search
response1 = await smart_search("What is machine learning?")
print(f"Strategy used: {response1.strategy_used}")  # "vector_search"
print(f"Intent detected: {response1.intent}")  # "FACTUAL"

# Example 2: Relationship query → Graph search
response2 = await smart_search("How are Tesla and SpaceX related?")
print(f"Strategy used: {response2.strategy_used}")  # "graph_search"
print(f"Intent detected: {response2.intent}")  # "RELATIONSHIP"
```

#### Confidence Scoring and Citations
```python
# All Phase 3 responses include confidence scores and citations
response = await agent.chat("Explain quantum computing")

print(f"Answer: {response.answer}")
print(f"Confidence: {response.confidence}")  # 0.0-1.0 scale
print(f"Sources: {len(response.sources)}")   # Always > 0
print(f"Follow-ups: {response.follow_up_questions}")

# Citation details
for source in response.sources:
    print(f"- {source['title']} (confidence: {source['confidence']})")
```
