# RAG Pipeline Package

Document ingestion and processing pipeline for the Knowledge Graph Pydantic Agent.

## Overview

This package handles the complete document ingestion workflow, from raw files to indexed content in PostgreSQL (vectors) and Neo4j (knowledge graph).

## Directory Structure

```
rag_pipeline/
|-- __init__.py
|-- pipeline.py          # Main pipeline orchestration
|-- adapters/            # Output adapters (database writers)
|-- common/              # Shared utilities (chunking, embedding)
|-- sources/             # Input source handlers
    |-- google_drive.py  # Google Drive integration
    |-- local_files.py   # Local file processing
```

## Pipeline Architecture

```
Documents --> Preprocessing --> Chunking --> Embedding --> Storage --> Knowledge Extraction
    |             |               |           |             |              |
1. Load    2. Clean &       3. Split     4. Generate   5. Store    6. Extract entities
   files      normalize       into        vectors      in both      & relationships
                             chunks                    DBs
```

## Usage

### Basic Ingestion

```python
from src.rag_pipeline.pipeline import ingest_documents

# Ingest from local directory
await ingest_documents(
    source_path="/path/to/documents",
    clean=False  # Set True to reset existing data
)
```

### Via Makefile

```bash
# Standard ingest (incremental)
make ingest

# Clean ingest (reset existing data)
make ingest-clean
```

## Source Adapters

### Local Files

Process documents from local filesystem:

```python
from src.rag_pipeline.sources.local_files import LocalFileSource

source = LocalFileSource("/path/to/docs")
for document in source.iterate():
    # Process document
    pass
```

**Supported Formats:**
- PDF files (.pdf)
- Text files (.txt)
- Markdown files (.md)
- Word documents (.docx)

### Google Drive

Integration with Google Drive for cloud document access:

```python
from src.rag_pipeline.sources.google_drive import GoogleDriveSource

source = GoogleDriveSource(
    folder_id="your-folder-id",
    credentials_path="/path/to/credentials.json"
)
```

## Processing Pipeline

### 1. Preprocessing

- Text extraction from various formats
- Encoding normalization (UTF-8)
- Metadata extraction

### 2. Chunking

Semantic or simple chunking strategies:

```python
from src.rag_pipeline.common.chunking import SemanticChunker

chunker = SemanticChunker(
    chunk_size=1000,
    chunk_overlap=200
)
chunks = chunker.split(document_text)
```

### 3. Embedding

Vector embedding generation:

```python
from src.rag_pipeline.common.embedding import EmbeddingGenerator

embedder = EmbeddingGenerator()
vectors = await embedder.embed_batch(chunks)
```

**Embedding Dimensions:**
- OpenAI: 1536 dimensions
- Ollama (local): 768 dimensions

### 4. Storage

Dual-database storage:

**PostgreSQL (Supabase):**
- Full document content
- Vector embeddings (pgvector)
- Document metadata

**Neo4j:**
- Extracted entities
- Relationships between entities
- Temporal facts (episodes)

### 5. Knowledge Extraction

Entity and relationship extraction via Graphiti:

- Named entity recognition
- Relationship discovery
- Temporal fact creation
- Document reference population

## Configuration

Environment variables for the pipeline:

```env
# Chunking settings
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
CHUNKING_STRATEGY=semantic  # semantic or simple

# Embedding settings
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

# Knowledge extraction
ENABLE_KNOWLEDGE_EXTRACTION=true
```

## Document Filename Convention

For optimal temporal metadata extraction, use this naming pattern:

```
YYYY QN TICKER.pdf
```

Examples:
- `2023 Q3 INTC.pdf` - Intel Q3 2023
- `2024 Q1 AAPL.pdf` - Apple Q1 2024

This enables automatic extraction of:
- Fiscal year
- Fiscal quarter
- Company/ticker

## Database Tables

### PostgreSQL

```sql
documents(id, content, metadata, embedding vector(1536))
document_metadata(id, document_id, key, value)
document_rows(id, document_id, row_data jsonb)
```

### Neo4j

```cypher
(Entity {name, type, document_refs, importance_score})
(Episode {content, fiscal_quarter, fiscal_year, numeric_facts})
(Entity)-[:RELATIONSHIP {strength}]->(Entity)
(Entity)-[:MENTIONED_IN]->(Episode)
```

## Error Handling

The pipeline includes comprehensive error handling:

- Retry logic for transient failures
- Graceful degradation if Neo4j unavailable
- Detailed logging for debugging
- Batch processing with checkpoints

## Testing

```bash
# Run pipeline tests
pytest tests/rag_pipeline/ -v

# Test specific components
pytest tests/rag_pipeline/test_chunking.py -v
pytest tests/rag_pipeline/test_embedding.py -v
```

## Related Documentation

- [Database & RAG Integration](../../docs/3-architecture/database-and-rag.md)
- [Ingestion Systems](../../docs/0-RAG/ingestion-systems.md)
- [CLAUDE.md](../../CLAUDE.md) - Pipeline commands and patterns
