# Ingestion Systems Reference

## Four Systems, Different Use Cases

| System | Use Case | Mode | Database | Knowledge Extraction |
|--------|----------|------|----------|---------------------|
| **Agentic RAG Pipeline** | Batch ingestion with graph | CLI | PostgreSQL + Neo4j | Full (entities/facts/relationships) |
| **Google Drive Watcher** | Real-time Google Drive sync | Background | PostgreSQL + Neo4j | Full (entities/facts/relationships) |
| **Local File Watcher** | Real-time filesystem sync | Background | PostgreSQL + Neo4j | Full (entities/facts/relationships) |
| **Streamlit Upload** | User web uploads | Interactive | PostgreSQL | None |

---

## 1. Agentic RAG Pipeline

**Purpose**: Batch document processing with full knowledge graph extraction.

### Architecture Flow
```
Document → Chunking → Embedding → Knowledge Extraction → PostgreSQL → Neo4j Graph → Cross-Reference
```

### Key Components

**Chunking** (1000 chars, 200 overlap):
- `SimpleChunker`: Rule-based, paragraph splitting (5-10 docs/min)
- `SemanticChunker`: LLM-powered, semantic boundaries (2-5 docs/min)

**Embeddings**:
- OpenAI: 1536-dim, batch 100
- Ollama: 768-dim, local
- LRU cache (1000 embeddings)
- 3 retries with exponential backoff

**Knowledge Extraction** (parallel, max 5 chunks):
- **Entities**: Max 10/chunk, 100 char limit (company, person, technology, product, location, event, organization, concept)
- **Relationships**: Max 10/chunk (works_at, founded, invested_in, acquired, partners_with, competes_with, owns, develops, uses, located_in, part_of, related_to)
- **Facts**: Max 5/chunk, 500 char limit (brief statements, not excerpts)

**Storage**:
- PostgreSQL: Full content + embeddings (documents, chunks tables)
- Neo4j: Entity names + relationships + facts (NO content duplication)

### Usage

**CLI**:
```bash
make ingest                                    # Default: docs/example_docs
python -m src.agentic_rag.ingestion.pipeline ingest --path /path/to/docs
python -m src.agentic_rag.ingestion.pipeline ingest --rest-api --verbose
```

**Programmatic**:
```python
from src.agentic_rag.ingestion.pipeline import DocumentIngestionPipeline

async with DocumentIngestionPipeline() as pipeline:
    result = await pipeline.ingest_document(content, title, source, metadata)
    # Returns: document_id, chunks_created, entities_extracted, relationships_extracted,
    #          facts_extracted, processing_time, success, errors

    results = await pipeline.ingest_batch(documents, max_concurrent=3)
    stats = pipeline.get_stats()  # cache_hit_rate, avg_chunks_per_doc, etc.
```

### Configuration (.env)
```bash
# Chunking
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
USE_SEMANTIC_CHUNKING=false

# Embeddings
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
EMBEDDING_BATCH_SIZE=100

# Knowledge
EXTRACTION_MODEL=gpt-4o-mini
MAX_ENTITIES_PER_CHUNK=10
MAX_FACT_LENGTH=500

# Performance
ENABLE_GRAPH=true
ENABLE_CACHING=true

# Database
DATABASE_URL=postgresql://...
NEO4J_URI=neo4j+s://...
```

### Error Handling
- PostgreSQL failure → Auto-fallback to Supabase REST
- Neo4j unavailable → Logs warning, continues without graph
- Chunk extraction failure → Logs, continues
- 3 retries for embeddings

### Key Files
- `src/agentic_rag/ingestion/pipeline.py` (614 lines)
- `src/agentic_rag/ingestion/chunker.py` (660 lines)
- `src/agentic_rag/ingestion/embedder.py` (554 lines)
- `src/agentic_rag/ingestion/knowledge_extractor.py` (570 lines)

---

## 2. Google Drive Watcher

**Purpose**: Real-time sync from Google Drive folders with full Agentic RAG pipeline.

### Flow
```
Google Drive → OAuth → Poll (60s) → Change Detection → Download → Text Extract →
Agentic RAG Adapter → Chunking → Embedding → Knowledge Extraction → PostgreSQL + Neo4j
```

**Note**: As of Phase 2, Google Drive Watcher uses the full Agentic RAG pipeline via `process_file_with_agentic_rag_sync`, providing entity extraction, relationship mapping, and knowledge graph storage.

### Features

**Authentication**: OAuth 2.0, auto-refresh, WSL/headless support
**Monitoring**: Polls every 60s (configurable), tracks modifiedTime/createdTime
**Scope**: Specific folder + recursive subfolders OR entire Drive
**Google Workspace Export**:
- Docs → text/plain
- Sheets → text/csv
- Slides → text/plain

**Supported MIME Types**:
```
application/pdf, text/plain, text/html, text/csv,
application/vnd.google-apps.{document,spreadsheet,presentation}
```

### Usage

**CLI**:
```bash
python -m src.rag_pipeline.pipeline --source google_drive --interval 60
```

**Setup**:
1. Create Google Cloud Project
2. Enable Google Drive API
3. Create OAuth Desktop credentials → download credentials.json
4. First run opens browser for OAuth consent → saves token.json
5. Subsequent runs auto-refresh token

**Programmatic**:
```python
from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

watcher = GoogleDriveWatcher(
    credentials_path="credentials.json",
    token_path="token.json",
    folder_id="1a2b3c4d5e6f7g8h9i"  # Optional
)
watcher.authenticate()
watcher.watch_for_changes(interval_seconds=60)  # Runs forever
```

### Metadata Structure

Files processed through Google Drive Watcher include the following metadata in PostgreSQL:
- `file_id`: Google Drive file ID
- `source_type`: "google_drive"
- `mime_type`: Original MIME type (e.g., "application/pdf", "text/plain")
- Plus all standard Agentic RAG metadata (entities, relationships, facts stored in Neo4j)

### Configuration (config.json)
```json
{
  "supported_mime_types": ["application/pdf", "text/plain", ...],
  "export_mime_types": {
    "application/vnd.google-apps.document": "text/plain"
  },
  "text_processing": {"default_chunk_size": 400, "default_chunk_overlap": 0},
  "last_check_time": "2025-01-15T10:30:00.000Z",
  "watch_folder_id": "1a2b3c4d5e6f7g8h9i"
}
```

### .env
```bash
GOOGLE_DRIVE_CREDENTIALS_PATH=credentials.json
GOOGLE_DRIVE_FOLDER_ID=1a2b3c4d5e6f7g8h9i
```

### Key Files
- `src/rag_pipeline/sources/google_drive.py` (732 lines)

---

## 3. Local File Watcher

**Purpose**: Real-time sync from local filesystem with full Agentic RAG pipeline.

### Flow
```
Local Dir → Filesystem Poll (60s) → Change Detection → Read → Text Extract →
Agentic RAG Adapter → Chunking → Embedding → Knowledge Extraction → PostgreSQL + Neo4j
```

**Note**: As of Phase 1, Local File Watcher uses the full Agentic RAG pipeline via `process_file_with_agentic_rag_sync`, providing entity extraction, relationship mapping, and knowledge graph storage.

### Features

**Monitoring**: `os.walk()` + `Path.stat()`, no external deps, cross-platform
**Detection**: Compares st_mtime/st_ctime against last_check_time
**Directory**: Default `data/` (relative to script), recursive, auto-created
**MIME Detection**: Custom extension mappings + mimetypes module fallback

### Usage

**CLI**:
```bash
python -m src.rag_pipeline.pipeline --source local --interval 60
```

**Programmatic**:
```python
from src.rag_pipeline.sources.local_files import LocalFileWatcher

watcher = LocalFileWatcher(watch_directory="my_docs")
watcher.watch_for_changes(interval_seconds=60)  # Runs forever
```

### Metadata Structure

Files processed through Local File Watcher include the following metadata in PostgreSQL:
- `file_id`: Local file path (e.g., "/path/to/file.txt")
- `source_type`: "local_file"
- `mime_type`: Detected MIME type (e.g., "application/pdf", "text/plain")
- Plus all standard Agentic RAG metadata (entities, relationships, facts stored in Neo4j)

### Configuration (config.json)
```json
{
  "supported_mime_types": ["application/pdf", "text/plain", "text/csv", ...],
  "tabular_mime_types": ["text/csv", "application/vnd.openxmlformats-..."],
  "text_processing": {"default_chunk_size": 400, "default_chunk_overlap": 0},
  "last_check_time": "2025-01-15T10:30:00.000Z",
  "watch_directory": "data"
}
```

### Key Files
- `src/rag_pipeline/sources/local_files.py` (504 lines)

---

## 4. Streamlit Upload Handler

**Purpose**: User-initiated web uploads via Streamlit UI.

### Flow
```
Streamlit Widget → File Type Detection → Async Processing → Type-Specific Handler → Supabase
```

### Three Upload Types

**Documents** (PDF/TXT/MD):
```python
1. Decode UTF-8
2. semantic_chunk(1000 chars, 200 overlap)
3. Generate embeddings (batch)
4. Insert into documents table (one per chunk)
```

**Images** (PNG/JPG/GIF/WEBP):
```python
1. Read bytes
2. Base64 encode
3. Insert into documents (metadata.image_data = base64, metadata.is_image = true)
```

**Tabular** (CSV/Excel):
```python
1. Pandas read
2. Extract schema (columns, dtypes)
3. Insert dataset metadata into documents
4. Insert rows into document_rows (with row_index)
```

### Usage

**In streamlit_app.py**:
```python
from src.ui.features.upload_handler import render_upload_section

render_upload_section(supabase_client, embedding_client)
```

**UI Flow**:
1. Select file type (Documents/Images/Data)
2. Upload widget appears with appropriate extensions
3. Click "Upload" → Spinner
4. Success/error message

### Async Handling
```python
import nest_asyncio
nest_asyncio.apply()  # Enable nested loops for Streamlit

result = asyncio.run(process_document_upload(file, supabase, embedding))
# Fallback: loop.run_until_complete() on RuntimeError
```

### Key Files
- `src/ui/features/upload_handler.py` (427 lines)

---

## Decision Matrix

**Use Agentic RAG (CLI) when**: Batch ingestion, initial data load, need control over processing order
**Use Google Drive when**: Docs in Drive, team collaboration, Google Workspace files, real-time sync with full knowledge extraction
**Use Local Files when**: Local/network filesystem, file-drop workflows, no cloud dependencies, real-time sync with full knowledge extraction
**Use Streamlit when**: End users upload directly, interactive UI, images/tabular data, simpler/faster processing without graph

**Note**: Both Google Drive and Local File watchers now provide the same knowledge extraction capabilities as the CLI Agentic RAG pipeline.

---

## Performance

| System | Speed | Bottleneck | Notes |
|--------|-------|-----------|-------|
| Agentic RAG | 2-10 docs/min | Embedding API, LLM extraction | CLI batch processing |
| Google Drive | 8-15s/file | Knowledge extraction, Neo4j writes | Now uses full Agentic RAG (Phase 2) |
| Local Files | 8-15s/file | Knowledge extraction, Neo4j writes | Now uses full Agentic RAG (Phase 1) |
| Streamlit | 2-30s/file | Embedding API, network | Basic RAG only (no graph) |

**Performance Change (Watchers)**: Watchers now use Agentic RAG pipeline, increasing processing time from legacy 2-5s to 8-15s per file due to entity extraction, relationship mapping, and Neo4j graph storage. This tradeoff provides richer knowledge representation and better search quality.

**Optimization**:
- Agentic RAG (CLI): Enable caching (50-80% hit rate), use Ollama, skip graph (2x faster)
- Google Drive: Increase interval for large folders, set `ENABLE_GRAPH=false` to skip graph (2x faster), use service account
- Local Files: Increase interval for large dirs (300s), set `ENABLE_GRAPH=false` to skip graph (2x faster), use subdirs
- Streamlit: Batch uploads, increase maxUploadSize

**Note**: Watchers respect global `ENABLE_GRAPH` and `USE_SEMANTIC_CHUNKING` settings. Disabling graph storage significantly improves processing speed but reduces search quality.

---

## Troubleshooting

**Agentic RAG**:
- Hangs on embedding → Check API quota, reduce batch size, try Ollama
- Neo4j fails → Verify credentials, set ENABLE_GRAPH=false temporarily
- Low cache hit → Normal first run, improves on re-ingestion

**Google Drive**:
- OAuth redirect mismatch → Add http://localhost:* to authorized URIs
- No changes detected → Reset last_check_time to 1970-01-01T00:00:00.000Z
- Download fails → Check sharing permissions, add MIME type to config

**Local Files**:
- No new files → Verify watch_directory path, reset last_check_time
- High CPU → Increase interval (300s), split into subdirs

**Streamlit**:
- File too large → Increase server.maxUploadSize in .streamlit/config.toml
- No chunks created → Check UTF-8 encoding, verify non-empty file
- Excel parse fails → Install openpyxl, try CSV instead

---

## Configuration Summary

**Shared (.env)**:
```bash
DATABASE_URL=postgresql://...
SUPABASE_URL=https://...
SUPABASE_SERVICE_KEY=...
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=sk-...
```

**Agentic RAG only**:
```bash
NEO4J_URI=neo4j+s://...
ENABLE_GRAPH=true
LLM_API_KEY=sk-...
EXTRACTION_MODEL=gpt-4o-mini
USE_SEMANTIC_CHUNKING=false
CHUNK_SIZE=1000
```

**Google Drive only**:
```bash
GOOGLE_DRIVE_CREDENTIALS_PATH=credentials.json
GOOGLE_DRIVE_FOLDER_ID=...  # Optional
```

**Watchers (Google Drive & Local Files)**:
- Use global Agentic RAG settings: `ENABLE_GRAPH`, `USE_SEMANTIC_CHUNKING`, `CHUNK_SIZE`, `CHUNK_OVERLAP`
- Use config.json for MIME types, text processing fallback, last_check_time
- Files processed through watchers get same knowledge extraction as CLI pipeline
