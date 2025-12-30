# WSL2 Local Deployment Guide

**Platform:** Windows 11 with WSL2 (Ubuntu)
**Target:** Local development with cloud services (Supabase Cloud + Neo4j Aura)
**Date:** 2025-10-08

## Overview

This guide documents the complete deployment process for Luminari Agent on WSL2 Ubuntu, using cloud services for databases to minimize local infrastructure.

## ⚠️ Resource Requirements

**IMPORTANT:** This project requires the full Agentic RAG installation including knowledge graph capabilities.

### 🧠 Full Agentic RAG Installation - **REQUIRED**

**Resources:** ~5.5GB disk, 8GB+ RAM
**Install time:** ~15 minutes (large downloads)
**What you get:**
- ✅ Vector search (Supabase pgvector)
- ✅ Knowledge graph (Neo4j + Graphiti) - **REQUIRED**
- ✅ OpenAI embeddings (via API)
- ✅ Local embeddings (sentence-transformers)
- ✅ Web search, image analysis, SQL queries
- ✅ Full chat functionality
- ✅ Entity extraction & relationship discovery
- ✅ Temporal reasoning
- ⚠️  PyTorch + CUDA libraries (3.7GB, mostly unused on CPU)

**Python packages:** 303 packages (~5.5GB total)

**Note:** The knowledge graph (Neo4j + Graphiti) is a core component of the system and cannot be skipped. All RAG dependencies must be installed.

---

## Architecture

- **Compute:** WSL2 Ubuntu (local)
- **Vector DB:** Supabase Cloud (PostgreSQL + pgvector)
- **Knowledge Graph:** Neo4j Aura Cloud
- **LLM:** OpenAI GPT-5-mini
- **Embeddings:** OpenAI text-embedding-3-small (+ optional local via sentence-transformers)
- **Web Search:** Jina.ai

## Prerequisites Installed

### System Packages (via sudo apt-get)

```bash
# Core Python tools
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv python3-dev

# Build tools (for compiling Python packages with C extensions)
sudo apt-get install -y build-essential

# PostgreSQL client + dev headers (for psycopg debugging)
sudo apt-get install -y libpq-dev postgresql-client

# Redis (optional - for caching)
sudo apt-get install -y redis-server

# Build automation
sudo apt-get install -y make

# Git (usually pre-installed)
sudo apt-get install -y git
```

**Python Version:** 3.12.3 (pre-installed in WSL2)

### Cloud Services Setup

#### 1. Supabase Cloud (PostgreSQL + pgvector)

**Setup Steps:**
1. Created account at [supabase.com](https://supabase.com)
2. Created new project
3. Enabled pgvector extension: Database → Extensions → "vector" → Enable
4. Retrieved credentials from Project Settings → API:
   - `SUPABASE_URL`: Project URL
   - `SUPABASE_SERVICE_KEY`: service_role key (not anon key!)

**Configuration:**
```env
SUPABASE_URL=https://hokdgtbedrsenvldxbyx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGc...
```

#### 2. Neo4j Aura Cloud (Knowledge Graph)

**Setup Steps:**
1. Created free account at [neo4j.com/cloud/aura-free](https://neo4j.com/cloud/aura-free)
2. Created free AuraDB instance
3. Saved credentials (shown only once during setup):
   - `NEO4J_URI`: Connection URI (neo4j+s://xxxxx.databases.neo4j.io)
   - `NEO4J_USER`: Username (use **"neo4j"**, not "Aura")
   - `NEO4J_PASSWORD`: Generated password

**Configuration:**
```env
NEO4J_URI=neo4j+s://f5c57870.databases.neo4j.io
NEO4J_QUERY_API_URL=https://f5c57870.databases.neo4j.io/db/neo4j/query/v2
NEO4J_USER=neo4j  # Use "neo4j", not "Aura"
NEO4J_PASSWORD=awq1A8JYabfB2IHsUVrSiUm0v67N0MWQMoVCr2GBszk
NEO4J_DATABASE=neo4j
NEO4J_ENCRYPTED=true
```

#### 3. OpenAI API

**Setup Steps:**
1. Created account at [platform.openai.com](https://platform.openai.com)
2. Generated API key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
3. Added payment method (required for API access)

**Configuration:**
```env
LLM_PROVIDER=openai
LLM_API_KEY=sk-proj-...
LLM_MODEL=gpt-5-mini
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=sk-proj-...  # Can be same as LLM_API_KEY
EMBEDDING_MODEL=text-embedding-3-small
```

#### 4. Jina.ai (Web Search)

**Setup Steps:**
1. Created account at [jina.ai](https://jina.ai)
2. Retrieved API key from dashboard

**Configuration:**
```env
JINA_API_KEY=jina_the_whole_api_key_here
WEB_SEARCH_PROVIDER=jina
```

## Installation Steps

### Step 1: Environment Configuration ✅

Configured `.env` file with all service credentials:

```bash
cp .env.example .env
# Manually edited .env with all credentials above
```

**Verified `.env` in `.gitignore`:** ✅ Already present (line 28)

### Step 2: Create Virtual Environment ✅

**Issue Encountered:** Ubuntu's externally-managed-environment prevents system-wide pip installs

**Solution:**
```bash
# Create virtual environment
python3 -m venv .venv

# Activate it (do this for every new terminal session)
source .venv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip
```

**Result:** ✅ Virtual environment created at `.venv/` (already in `.gitignore`)

### Step 3: Install Python Dependencies ✅

**Issue Encountered:** Standard `pip install -e .[dev]` took 10+ minutes and got stuck in dependency resolution backtracking, cycling through 100+ versions of packages like `opentelemetry-semantic-conventions`, `types-redis`, `ollama`, and `pydantic-ai`.

**Root Cause:** Complex dependency tree with many packages having loose version constraints:
- `mem0ai` with many transitive dependencies
- `pydantic-ai` with multiple optional extras
- `opentelemetry-distro` with ~50 sub-packages
- `redis-om` conflicting type stub versions

**Failed Attempts:**
```bash
# Attempt 1: Standard pip install (FAILED - timeout after 10 minutes)
source .venv/bin/activate && pip install -e .[dev]

# Attempt 2: Install without deps then resolve (FAILED - same backtracking issue)
source .venv/bin/activate && pip install -e . --no-deps && pip install <deps>
```

**Working Solution - Use UV (fast pip alternative):**
```bash
# Activate virtual environment
source .venv/bin/activate

# Install UV package manager (fast Rust-based pip replacement)
pip install uv

# Install all dependencies with UV (completes in ~2 minutes!)
uv pip install -e .[dev]
```

**Result:** ✅ Successfully installed 253 packages in ~2 minutes
- Resolved 254 packages in 7.34 seconds
- Downloaded ~200MB of packages
- Installed: pydantic-ai, streamlit, mem0ai, supabase, opentelemetry, pytest, and all dependencies

**Warning from UV:** `The package 'pydantic-ai==1.0.15' does not have an extra named 'anthropic'` - this is non-critical, the anthropic package was still installed correctly.

**Key Lesson:** For projects with complex dependencies, **UV is 30-50x faster than pip** at dependency resolution.

### Step 4: Install Pre-commit Hooks (Pending)

```bash
source .venv/bin/activate
pre-commit install
```

### Step 5: Initialize Supabase Database ✅

**Only ONE SQL file needs to be executed:**

1. Go to Supabase Dashboard → **SQL Editor**
2. Click "New Query"
3. Copy contents of: `src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql`
4. Paste and click **"Run"**

**Issue Encountered & Fixed:** Original migration had `WHERE expires_at > NOW()` in an index predicate (line 149), which caused error:
```
ERROR: 42P17: functions in index predicate must be marked IMMUTABLE
```
**Fix Applied:** Removed the `WHERE` clause from `idx_search_cache_expires` index. The index still works for filtering expired cache entries in queries.

This single migration file creates:
- ✅ `documents` + `chunks` tables (with dual embeddings: 1536d OpenAI + 768d Ollama)
- ✅ `chunk_entities` (entity references from Neo4j)
- ✅ `sessions` + `messages` (conversation history)
- ✅ `graph_sync_queue` (Neo4j sync queue)
- ✅ `search_cache` (query result caching)
- ✅ `hybrid_search_enhanced()` function (vector + text + entity boosting)
- ✅ All indexes, triggers, views, and maintenance procedures

**Important Changes Made:**
- ✅ Removed outdated `sql/` directory (contained 5 separate SQL files with old schema)
- ✅ Updated all documentation to reference the correct migration file
- ✅ The migration file is more comprehensive and matches what the code actually expects
- ✅ Old schema used `documents` table with `bigserial` IDs and single embedding column
- ✅ New schema uses UUID IDs, dual embeddings (1536d + 768d), and additional tables for sessions, caching, and graph sync

### Step 6: Install RAG Required Dependencies ✅

**CRITICAL:** Neo4j and Graphiti are **REQUIRED** components for this system. They must be installed via the `[rag]` extras.

**Solution:**
```bash
source .venv/bin/activate
uv pip install -e ".[dev,rag]"
```

**⚠️ Resource Requirements:**

| Component | Size | Purpose | Used on WSL2? |
|-----------|------|---------|---------------|
| **PyTorch** | 846MB | Deep learning framework | ✅ CPU operations only |
| **NVIDIA cudnn** | 674MB | GPU neural network ops | ❌ No GPU in WSL2 |
| **NVIDIA cublas** | 567MB | GPU matrix operations | ❌ No GPU in WSL2 |
| **NVIDIA nccl** | 307MB | Multi-GPU communication | ❌ No GPU in WSL2 |
| **NVIDIA cusolver** | 255MB | GPU linear algebra | ❌ No GPU in WSL2 |
| **NVIDIA cusparse** | 275MB | GPU sparse matrices | ❌ No GPU in WSL2 |
| **NVIDIA cusparselt** | 274MB | GPU sparse tensors | ❌ No GPU in WSL2 |
| **NVIDIA cufft** | 184MB | GPU FFT | ❌ No GPU in WSL2 |
| **triton** | 148MB | GPU compiler | ❌ No GPU in WSL2 |
| **Other packages** | ~500MB | Neo4j, Graphiti, transformers, etc. | ✅ Yes |
| **TOTAL** | **~5GB** | | **~1.5GB actually used** |

**Installation time:** 5-10 minutes depending on internet speed

**Why so large?**
- PyTorch includes CUDA support by default (for GPU acceleration)
- On WSL2 without GPU passthrough, **most CUDA libraries are unused bloat**
- Alternative: Use OpenAI embeddings only (no PyTorch needed, but costs per API call)

**What actually runs:**
- ✅ PyTorch CPU operations (for local embeddings)
- ✅ sentence-transformers (converts text → vectors)
- ✅ neo4j driver (connects to Neo4j Aura)
- ✅ graphiti-core (knowledge graph intelligence)
- ✅ tiktoken (tokenizer)
- ✅ unstructured (document parsing)

**GPU Detection:**
```bash
nvidia-smi  # Check if GPU is available
```
- ✅ **With GPU (WSL2 + GPU passthrough):** All CUDA libraries are utilized, 10-50x faster embeddings
- ❌ **CPU-only (most WSL2 setups):** CUDA libraries are unused bloat (3.7GB)

**This deployment has:** NVIDIA GeForce RTX 5070 Ti (8GB) - **GPU-accelerated embeddings enabled!**

### Step 7: Initialize Neo4j Knowledge Graph (REQUIRED)

**CRITICAL:** The knowledge graph must be initialized for the system to function properly.

After RAG dependencies finish installing:

```bash
source .venv/bin/activate
make neo4j-init

# Or manually:
python -m src.agentic_rag.storage.neo4j_store init
```

**Verification:**
```bash
# Test Neo4j connection
python -c "from src.agentic_rag.storage.neo4j_store import Neo4jStore; store = Neo4jStore(); print('✅ Neo4j connected!')"
```

### Step 4: Verification (Pending)

Test the installation:

```bash
# Test basic UI
make run-ui-simple

# Test full system
make run-ui

# Test API server
make run-api
```

## WSL2-Specific Considerations

### Performance Optimization

✅ **Already optimized:** Project located in WSL2 native filesystem (`/home/aiwithapex/projects/base_agent`)

**Avoid:** Accessing Windows filesystem from WSL2 (`/mnt/c/...`) - 10x slower I/O

### Port Access

Ports accessible from Windows:
- Streamlit UI: `http://localhost:8501`
- API Server: `http://localhost:8058`
- Metrics: `http://localhost:9090`

### Redis Configuration

Redis installed locally but **optional** - system works without caching enabled.

To disable Redis caching:
```env
ENABLE_REDIS_CACHE=false
```

## Current Status

### ✅ Infrastructure & Configuration
- [x] System packages installed (make, python3-pip, python3-venv, build-essential, libpq-dev, redis-server)
- [x] Cloud services configured (Supabase, Neo4j Aura, OpenAI, Jina.ai)
- [x] Environment variables set (.env configured)
- [x] Virtual environment created (.venv/)
- [x] Python dependencies installed (253 packages via UV)
- [x] Pre-commit hooks installed
- [x] Old SQL files cleaned up (outdated `sql/` directory removed)
- [x] Documentation updated to reference correct migration file
- [x] DATABASE_URL configured with PostgreSQL connection string (URL-encoded password)

### ✅ Core Fixes (2025-10-09)
- [x] **CRITICAL FIX: ConnectionManager async initialization** (`connection_manager.py:421-429`)
  - Added async context manager support: `async with ConnectionManager() as conn_mgr`
  - Fixed circuit breaker to verify pool exists before blocking operations
  - Added clear error messages when pools aren't initialized
  - Fixed Neo4j driver config for `neo4j+s://` URIs (encryption in URI, not config)

- [x] **CRITICAL FIX: IngestionPipeline async initialization** (`pipeline.py:123-181`)
  - Added `async def initialize()` method that properly calls `await connection_manager.initialize()`
  - Split sync `__init__()` from async `initialize()`
  - Added async context manager: `async with DocumentIngestionPipeline() as pipeline`
  - Added `_initialized` flag to prevent double initialization

- [x] **CRITICAL FIX: CLI async pattern** (`__main__.py:115-196`)
  - Updated to use `async with DocumentIngestionPipeline()` pattern
  - Automatic connection cleanup via context manager
  - Proper fallback to REST API on PostgreSQL failure
  - Changed default path from `example_big_tech_docs_for_ingestion_testing` to `example_docs`

- [x] **CRITICAL FIX: Configuration masking bug** (`settings.py:516`, `config.py:161`)
  - **Root cause**: `Settings.to_dict()` was masking `neo4j_password` with `"***MASKED***"`
  - **Impact**: `ConnectionManager` received masked password, causing 100% Neo4j auth failure
  - **Solution**: Added `mask_sensitive` parameter (defaults to `True` for logging safety)
  - `Config.dict()` now uses `mask_sensitive=False` for internal use
  - Security maintained: Logging still masks credentials, internal code gets real values
  - Created diagnostic script: `scripts/test_neo4j_connection.py`

### ✅ Database & Storage
- [x] Fixed ingestion module import errors
- [x] Created CLI interface for document ingestion (`src/agentic_rag/ingestion/__main__.py`)
- [x] Fixed ConnectionManager config key case sensitivity (lowercase keys)
- [x] Diagnosed WSL2 network connectivity issue (IPv6/port blocking)
- [x] Created REST API storage backend (`src/agentic_rag/storage/supabase_rest_store.py`)
- [x] Implemented intelligent PostgreSQL → REST API fallback
- [x] Supabase database schema initialized (6 documents, 0 chunks - partial ingestion before fix)
- [x] **Fixed PostgreSQL pooler connectivity** (changed region to aws-1-us-east-2, port 5432)
- [x] **Fixed environment variable caching** (added load_dotenv override and reload_settings)
- [x] **Fixed ConnectionManager prepared statement** (schema uses embedding_1536/768, not embedding)
- [x] **Made Neo4j initialization conditional** (only loads when ENABLE_GRAPH=true)
- [x] **PostgreSQL connection confirmed working** (direct connection via asyncpg pool)
- [x] **Neo4j connection confirmed working** (authentication issue resolved via config fix)
- [x] **Neo4j schema initialized** (4 constraints, 22 indexes for Entity/Episode nodes)
- [x] **Knowledge graph ready** (Neo4j Aura Enterprise 5.27 operational)

### ✅ UI & Agent
- [x] **Fixed Makefile venv activation** (all `make run-*` commands now activate .venv and set PYTHONPATH)
- [x] **Fixed OpenAIModel deprecation** (updated to OpenAIChatModel in src/clients/llm.py)
- [x] **Fixed Prometheus metrics duplicate registration** (handles Streamlit reloads gracefully)
- [x] **Streamlit UI running successfully** (accessible at http://localhost:8501, HTTP 200 verified)
- [x] **Fixed RAG list_documents_tool** (was querying non-existent document_metadata table, now queries documents table correctly)
- [x] **Updated TESTING_GUIDE.md** (added document-specific test queries based on ingested content)
- [x] **Deployment fully operational** (UI + RAG accessible)
- [x] **GraphRAG Analytics Dashboard deployed** (v1.0.0 - 2025-10-15)

### 📊 GraphRAG Analytics Dashboard (NEW - v1.0.0)

**Deployed:** 2025-10-15
**Status:** ✅ Fully Operational

**Dependencies Installed:**
- ✅ plotly 6.3.1 (interactive visualizations)
- ✅ networkx 3.5 (graph layout algorithms)
- ✅ Dashboard modules verified working

**Features Available:**
- 🔍 **Search Analytics:** Metrics cards, strategy distribution charts
- 🎯 **Intent Analysis:** Query intent distribution visualizations
- 🕸️ **Knowledge Graph:** Interactive network visualization with up to 100 entities
- 🏷️ **Entity Explorer:** Top entities table with temporal fact timelines
- ⚡ **Performance Metrics:** Latency breakdowns, cache stats, DB health monitoring

**Access Dashboard:**
```bash
# Start UI in Standard mode (recommended)
make run-ui
# OR
source .venv/bin/activate && PYTHONPATH=$(PWD):$PYTHONPATH streamlit run src/ui/streamlit_app.py

# Navigate to: http://localhost:8501
# Click "📊 Dashboard" in the sidebar
```

**Dashboard Requirements:**
- ✅ PostgreSQL/Supabase connection (verified working)
- ✅ Neo4j Aura connection (verified working)
- ✅ Documents ingested (for meaningful analytics)
- ✅ Some searches performed (generates metrics)

**Quick Start Guide:** See `docs/DASHBOARD_QUICKSTART.md`

**WSL2-Specific Notes:**
- Dashboard accessible from Windows browser at http://localhost:8501
- Graph visualization uses CPU-only rendering (no GPU needed)
- All features work identically to Linux/Mac
- 30-second caching optimizes performance on WSL2 I/O

### ⚠️ In Progress
- [ ] **Neo4j Aura authentication** (credentials need verification/refresh - instance may be paused)
- [ ] **Neo4j knowledge graph initialization** (script created: `scripts/init_neo4j.py`)
- [ ] **Fix Prometheus metrics setup** (resolve .env duplicates, add @track_performance to tools)

### 📋 Next Steps (Priority Order)

1. **🎉 Test the new GraphRAG Dashboard** (RECOMMENDED FIRST)
   ```bash
   # Start the UI
   make run-ui

   # Open browser: http://localhost:8501
   # Click "📊 Dashboard" in sidebar
   # Explore all 5 analytics sections
   ```

2. **Verify Neo4j Aura credentials** (instance may be paused, password may need reset)
   - Login: https://neo4j.com/cloud/aura-free
   - Check instance status → Resume if paused
   - Reset password if needed → Update `.env`

3. **Run `python scripts/init_neo4j.py`** (creates constraints and indexes)

4. **Test full ingestion with graph extraction**:
   ```bash
   python -m src.agentic_rag.ingestion ingest --path docs/example_docs
   ```

5. **Complete comprehensive testing** with TESTING_GUIDE.md

## Troubleshooting

### Common WSL2 Issues

**Issue:** `make: command not found`
```bash
sudo apt-get install -y make
```

**Issue:** `externally-managed-environment` error from pip
```bash
# Don't use --break-system-packages!
# Instead, create a virtual environment:
python3 -m venv .venv
source .venv/bin/activate
```

**Issue:** `pip install -e .[dev]` takes 10+ minutes and gets stuck in dependency resolution
```bash
# Solution: Use UV instead of pip
source .venv/bin/activate
pip install uv
uv pip install -e .[dev]
# Completes in ~2 minutes vs 10+ minutes with pip
```

**Issue:** Python package build failures
```bash
sudo apt-get install -y build-essential python3-dev libpq-dev
```

**Issue:** Redis connection errors
```bash
# Option 1: Start Redis
sudo service redis-server start

# Option 2: Disable Redis caching
# Set ENABLE_REDIS_CACHE=false in .env
```

**Issue:** Port already in use (8501, 8058)
```bash
# Find process using port
netstat -ano | findstr :8501

# Kill process (from Windows PowerShell)
taskkill /PID <process_id> /F
```

**Issue:** `RuntimeError: Task attached to a different loop` in async tests (RESOLVED 2025-10-13)
```
Error: RuntimeError: Task <Task pending> got Future <Future pending> attached to a different loop
```

**Root Cause**: asyncpg connection pools bind to event loops at creation time. pytest-asyncio was creating function-scoped loops while connection pools were created in module-scoped fixtures.

**Solution**: Configure module-scoped event loops for all async tests:

1. **`pyproject.toml`**:
```toml
[tool.pytest.ini_options]
asyncio_default_fixture_loop_scope = "module"
```

2. **Test files with database operations**:
```python
@pytest.mark.asyncio(loop_scope="module")
class TestDatabaseInfrastructure:
    async def test_something(self, connection_manager):
        # Test code
```

3. **`conftest.py`** - Module-scoped fixtures:
```python
@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
```

See `docs/TESTING_GUIDE.md` for complete configuration details.

### Schema Cleanup Issues (Resolved)

**Issue:** Found conflicting SQL schemas
- Old `sql/` directory had 5 separate files with outdated table structures
- Code was using tables from `src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql`
- Mismatch between old schema (`documents` with `bigserial` ID) and code expectations (`documents` with UUID)

**Resolution:**
```bash
# Deleted outdated sql/ directory
rm -rf sql/

# Updated all documentation files:
# - docs/INSTALL.md
# - docs/DEPLOYMENT.md
# - docs/DEPLOYMENT_WSL2.md
# - docs/TROUBLESHOOTING.md
# - docs/AI_CODER_GUIDE.md
# - docs/DB_AND_RAG.md

# All now reference: src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql
```

**Key Differences:**
| Feature | Old Schema (sql/) | New Schema (migrations/) |
|---------|-------------------|--------------------------|
| Document IDs | bigserial (integer) | UUID |
| Embeddings | Single 1536d column | Dual: 1536d + 768d |
| Tables | 4 basic tables | 8 comprehensive tables |
| Functions | `match_documents()` | `hybrid_search_enhanced()` |
| Caching | None | Built-in `search_cache` |
| Sessions | None | `sessions` + `messages` |
| Graph Sync | None | `graph_sync_queue` |

### DATABASE_URL Configuration Issues (Resolved)

**Issue 1:** `DATABASE_URL` not being loaded correctly from `.env`

**Symptoms:**
- `KeyError: 'DATABASE_URL'` when initializing ConnectionManager
- Settings loading HTTPS URL instead of PostgreSQL connection string
- Environment variable cached in shell session

**Root Causes:**
1. Shell environment variable `DATABASE_URL` set to HTTPS URL (overrides .env file)
2. ConnectionManager accessing config dict with uppercase keys (should be lowercase)
3. Password with special characters (`?` and `$`) not URL-encoded

**Resolution:**

1. **URL-encode the password** in DATABASE_URL:
```bash
# Original password: xmSrN698?M9pC$CA
# URL-encoded: xmSrN698%3FM9pC%24CA
#   ? becomes %3F
#   $ becomes %24

# Correct format in .env:
DATABASE_URL=postgresql://postgres:xmSrN698%3FM9pC%24CA@db.hokdgtbedrsenvldxbyx.supabase.co:5432/postgres
```

2. **Clear shell environment variable:**
```bash
unset DATABASE_URL
# Or restart your terminal session
```

3. **Fixed ConnectionManager to use lowercase config keys:**
```python
# Changed from: self.config["DATABASE_URL"]
# To: self.config["database_url"]
```

**Files Modified:**
- `.env` - Added correct PostgreSQL connection string with URL-encoded password
- `.env.example` - Updated with placeholder format
- `src/agentic_rag/storage/connection_manager.py` - Fixed config key case (DATABASE_URL → database_url)

**Verification:**
```bash
python test_db_connection.py
# Should output: ✅ Database connected!
```

### Ingestion Pipeline Import Errors (Resolved)

**Issue:** `ImportError: cannot import name 'ChunkingConfig' from 'src.agentic_rag.ingestion.chunker'`

**Root Cause:**
- `__init__.py` tried to import non-existent classes `ChunkingConfig` and `EmbeddingConfig`
- Actual functions are `get_chunking_config()` and `get_embedding_config()`

**Resolution:**

Fixed `src/agentic_rag/ingestion/__init__.py`:
```python
# Removed invalid imports:
# from .chunker import ChunkingConfig, ChunkingStrategy
# from .embedder import EmbeddingConfig

# Added correct imports:
from .chunker import get_chunking_config
from .embedder import get_embedding_config
```

**Created CLI Interface:**

Created `src/agentic_rag/ingestion/__main__.py` to enable:
```bash
python -m src.agentic_rag.ingestion.pipeline ingest --path docs/example_big_tech_docs_for_ingestion_testing
# Or via Makefile:
make ingest
```

**Files Modified:**
- `src/agentic_rag/ingestion/__init__.py` - Fixed imports
- `src/agentic_rag/ingestion/__main__.py` - Created CLI entry point
- `test_db_connection.py` - Added helper script for testing DB connection

### WSL2 Network Connectivity Issues (Active Issue)

**Issue:** `OSError: [Errno 101] Network is unreachable` when connecting to Supabase PostgreSQL

**Symptoms:**
```
Failed to initialize PostgreSQL: [Errno 101] Network is unreachable
ping: connect: Network is unreachable
```

**Common Causes:**
1. WSL2 network adapter not initialized
2. Windows Firewall blocking WSL2
3. VPN interfering with WSL2 networking
4. DNS resolution failing in WSL2

**Solutions (try in order):**

**Option 1: Restart WSL2** (Quickest fix)
```bash
# From Windows PowerShell (as Administrator):
wsl --shutdown

# Wait 10 seconds, then reopen WSL2 terminal
# Test connectivity:
ping -c 2 8.8.8.8
```

**Option 2: Use Supabase Session Pooler (RECOMMENDED FOR WSL2) ✅**

The Session pooler (port 5432) works reliably on WSL2 and IPv4-only networks:

1. Go to **Supabase Dashboard → Settings → Database → Connection string**
2. Find **Session pooler** section (labeled "Only recommended as alternative to Direct Connection, when connecting via an IPv4 network")
3. Copy the connection string - should look like: `postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-[REGION].pooler.supabase.com:5432/postgres`
4. URL-encode your password
5. Update `.env`:
```env
# Session pooler (port 5432) - works reliably on WSL2
DATABASE_URL=postgresql://postgres.hokdgtbedrsenvldxbyx:xmSrN698%3FM9pC%24CA@aws-1-us-east-2.pooler.supabase.com:5432/postgres

# ❌ DO NOT USE Transaction pooler (port 6543) - times out on WSL2
```

**Important:**
- The region (e.g., `aws-1-us-east-2`) must match your Supabase project's actual region
- Use port **5432** (Session pooler), NOT 6543 (Transaction pooler)
- Transaction pooler will timeout on WSL2 networks

**Option 3: Fix WSL2 Networking**
```bash
# Check DNS resolution
cat /etc/resolv.conf
# Should show nameserver 8.8.8.8 or similar

# Fix DNS if needed
sudo nano /etc/wsl.conf
# Add:
[network]
generateResolvConf = false

# Then set DNS manually:
sudo rm /etc/resolv.conf
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf

# Restart WSL2 from Windows PowerShell:
wsl --shutdown
```

**Option 4: Check Windows Firewall**
```powershell
# From Windows PowerShell (as Administrator):
New-NetFirewallRule -DisplayName "WSL2" -Direction Inbound -InterfaceAlias "vEthernet (WSL)" -Action Allow
```

**Option 5: Use REST API Fallback** (RECOMMENDED - Works Immediately)

If PostgreSQL ports remain blocked, the system automatically falls back to Supabase's REST API:

```bash
# Default behavior - tries PostgreSQL, falls back to REST API
make ingest
python -m src.agentic_rag.ingestion ingest

# Or force REST API mode (skip PostgreSQL attempt)
python -m src.agentic_rag.ingestion ingest --rest-api
```

**How it works:**
1. **Primary**: System attempts direct PostgreSQL connection (optimal performance)
2. **Fallback**: On failure, automatically switches to REST API over HTTPS (port 443)
3. **Benefits**:
   - ✅ Works immediately with restrictive firewalls/VPNs
   - ✅ No network configuration needed
   - ✅ HTTPS (port 443) rarely blocked
   - ⚠️ Slightly slower than direct PostgreSQL (REST overhead)
   - ⚠️ No connection pooling

**REST API Backend:**
- Created `src/agentic_rag/storage/supabase_rest_store.py`
- Mirrors PostgreSQL interface
- Used automatically when PostgreSQL fails
- Supports all core operations (documents, chunks, embeddings)

**Test REST API connectivity:**
```bash
python test_supabase_rest.py
# Should output: ✅ Supabase REST API is working!
```

**Root Cause Analysis:**

The network issue occurs because:
1. **IPv6 Only**: Supabase direct database is IPv6-only
2. **WSL2 Limitation**: WSL2 doesn't handle IPv6 well
3. **Port Blocking**: Corporate VPNs/firewalls block PostgreSQL ports (5432/6543)
4. **HTTPS Works**: Port 443 (HTTPS) is usually allowed

**Verification:**
```bash
# Test basic connectivity
ping -c 2 8.8.8.8

# Test DNS (shows IPv6 address - this is the problem)
nslookup db.hokdgtbedrsenvldxbyx.supabase.co

# Test HTTPS (should work)
curl -I https://hokdgtbedrsenvldxbyx.supabase.co
```

### Makefile Issues (Resolved)

**Issue:** `ModuleNotFoundError: No module named 'src'` or `streamlit: not found` when running `make run-ui`

**Root Cause:**
- Makefile commands weren't activating the virtual environment
- Python couldn't find the `src` module without PYTHONPATH set

**Resolution (COMPLETED):**
Updated all Makefile `run-*` commands to:
1. Activate virtual environment: `source .venv/bin/activate`
2. Set PYTHONPATH: `PYTHONPATH=$(PWD):$$PYTHONPATH`

**Example fix applied:**
```makefile
# Before (broken)
run-ui-simple:
	UI_MODE=simple streamlit run src/ui/streamlit_app.py

# After (working)
run-ui-simple:
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH UI_MODE=simple streamlit run src/ui/streamlit_app.py"
```

**Commands fixed:**
- `make run-ui`, `make run-ui-simple`, `make run-ui-advanced`
- `make run-api`, `make run-rag`, `make run-agentic-rag`
- `make neo4j-init`, `make ingest`, `make ingest-clean`
- `make dev`

**Manual alternative** (if Makefile still fails):
```bash
source .venv/bin/activate
PYTHONPATH=/home/aiwithapex/projects/base_agent:$PYTHONPATH UI_MODE=simple streamlit run src/ui/streamlit_app.py
```

### Prometheus Metrics Duplicate Registration (Resolved)

**Issue:** `ValueError: Duplicated timeseries in CollectorRegistry: {'luminari_requests', 'luminari_requests_created', 'luminari_requests_total'}`

**Root Cause:**
- Streamlit reloads modules on each script run
- Prometheus metrics get re-registered, causing duplicate timeseries error

**Resolution (COMPLETED):**
Updated `src/utils/monitoring.py` `_get_or_create_metric()` function to:
1. Check if metric already exists before creating
2. Catch `ValueError` on duplicate registration
3. Return existing metric instead of failing

**Code change:**
```python
try:
    return metric_class(**kwargs)
except ValueError as e:
    # Metric already registered (happens with Streamlit reloads)
    if "Duplicated timeseries" in str(e):
        for collector in list(registry._collector_to_names.keys()):
            collector_name = getattr(collector, "_name", None) or getattr(collector, "name", None)
            if collector_name == name:
                return collector
    raise
```

**Result:** UI now starts cleanly without metrics errors

### RAG Tools Schema Mismatch (Resolved)

**Issue:** Agent says "I don't have any documents" despite 63 documents in database

**Root Cause:**
- `list_documents_tool` in `src/tools/rag.py` was querying non-existent `document_metadata` table
- Schema uses `documents` table with metadata as JSONB column (not separate table)

**Resolution (COMPLETED):**
Updated `src/tools/rag.py` line 72:
```python
# Before (WRONG - table doesn't exist)
result = supabase.from_("document_metadata").select("id, title, schema, url").execute()

# After (CORRECT - queries actual table)
result = supabase.from_("documents").select("id, title, source, created_at").execute()
```

**Verification:**
```bash
source .venv/bin/activate
python -c "
from src.config import get_settings
from supabase import create_client
settings = get_settings()
supabase = create_client(settings.supabase_url, settings.supabase_service_key)
result = supabase.from_('documents').select('*', count='exact').execute()
print(f'Documents: {result.count}')
"
```

**Result:** Agent now successfully lists all 63 documents when asked "What documents do you have?"

### Prometheus Metrics Not Working (Active Issue)

**Issue:** Prometheus metrics server not running, observability stack non-functional

**Symptoms:**
- No metrics endpoint accessible (http://localhost:8000/metrics returns nothing)
- Grafana dashboards can't scrape metrics
- Tool performance not being tracked

**Root Causes:**
1. **Metrics server not initialized**: Streamlit UI doesn't start the metrics server (only API server does)
2. **Configuration duplicates**: `.env` has duplicate `METRICS_PORT` definitions (line 76: `8000`, line 158: `9090`)
3. **Missing tool instrumentation**: Only `web_search.py` uses `@track_performance`, other tools lack metrics

**Resolution (In Progress):**

**Step 1: Fix .env configuration duplicates**
```bash
# Edit .env file
# Line 76: Keep this
METRICS_PORT=8000

# Line 158: Change to avoid conflict
PROMETHEUS_PORT=9090  # This is where Prometheus scraper runs

# Line 75/157: Remove duplicate ENABLE_METRICS=true (keep only one)
```

**Step 2: Start metrics server (choose ONE option):**

**Option A: Run API server** (metrics start automatically)
```bash
source .venv/bin/activate
make run-api  # API on :8058, metrics on :8000
```

**Option B: Add metrics to Streamlit** (edit `src/ui/streamlit_app.py`)
```python
# Add after imports at top of file
from src.utils.monitoring import monitor
import os

# Add in main section
if os.getenv("ENABLE_METRICS", "true").lower() == "true":
    metrics_port = int(os.getenv("METRICS_PORT", "8000"))
    monitor.start_metrics_server(metrics_port)
```

**Step 3: Add performance tracking to tools**

Update each tool file:
```python
# src/tools/rag.py
from src.utils.monitoring import track_performance

@track_performance(tool_name="rag_retrieval")
async def retrieve_relevant_documents_tool(...):
    ...

# src/tools/sql_query.py
@track_performance(tool_name="sql_query")
async def execute_sql_query_tool(...):
    ...

# src/tools/image_analysis.py
@track_performance(tool_name="image_analysis")
async def image_analysis_tool(...):
    ...
```

**Step 4: Start full monitoring stack**
```bash
# Start Prometheus + Grafana + Jaeger + exporters
docker-compose -f docker-compose.monitoring.yml up -d

# Access dashboards
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
# Jaeger: http://localhost:16686
```

**Verification:**
```bash
# Test metrics endpoint
curl http://localhost:8000/metrics

# Should see Prometheus format output like:
# luminari_tool_executions_total{tool_name="web_search", status="success"} 42
# luminari_llm_tokens_total{model="gpt-5-mini", type="input"} 15420
```

**Additional Issues Found:**
- ❌ `OpenAIModel` deprecation warning in `src/tools/image_analysis.py:48` (should use `OpenAIChatModel`)
- ❌ Supabase client deprecation warnings about `timeout` and `verify` parameters
- ❌ Direct `os.getenv()` usage in 19 files (violates centralized config pattern)

**Files to modify:**
- `.env` - Fix duplicate METRICS_PORT and ENABLE_METRICS
- `src/ui/streamlit_app.py` - Add metrics server initialization (if not using API)
- `src/tools/rag.py` - Add @track_performance decorator
- `src/tools/sql_query.py` - Add @track_performance decorator
- `src/tools/image_analysis.py` - Add @track_performance decorator + fix OpenAIModel deprecation
- `src/clients/database.py` - Fix Supabase client deprecation warnings

### Cloud Service Issues

**Supabase Connection:**
- Verify service_role key (not anon key)
- Check project isn't paused (free tier auto-pauses after inactivity)
- Verify pgvector extension enabled

**Neo4j Aura Authentication Issues (Updated 2025-10-09):**

**Symptoms:**
```
neo4j.exceptions.AuthError: {neo4j_code: Neo.ClientError.Security.Unauthorized}
{message: The client is unauthorized due to authentication failure.}
```

**Common Causes:**
1. **Instance paused** (Aura free tier auto-pauses after 3 days of inactivity)
2. **Password expired or changed**
3. **Using "Aura" instead of "neo4j" as username**

**Solution Steps:**

1. **Login to Neo4j Aura Console:**
   - Go to: https://neo4j.com/cloud/aura-free
   - Login with your account

2. **Check Instance Status:**
   - Look for your instance (e.g., `f5c57870.databases.neo4j.io`)
   - Status will show: "Running" or "Paused"
   - If **Paused**: Click "Resume" button and wait 30-60 seconds

3. **Reset Password (if needed):**
   - Click on your instance → "Reset Password"
   - Copy the new password (shown only once!)
   - Save to password manager

4. **Update `.env` file:**
   ```bash
   NEO4J_URI=neo4j+s://YOUR_INSTANCE_ID.databases.neo4j.io
   NEO4J_USER=neo4j  # MUST be "neo4j", NOT "Aura"
   NEO4J_PASSWORD=YOUR_NEW_PASSWORD  # Use plain password, no URL encoding needed
   NEO4J_DATABASE=neo4j
   NEO4J_ENCRYPTED=true  # Not actually used with neo4j+s:// URI
   ```

5. **Test Connection:**
   ```bash
   python scripts/init_neo4j.py
   ```

**Verification in Neo4j Browser:**
- Open: https://workspace-preview.neo4j.io/workspace/query
- Connect with URI, username, password
- Run query: `RETURN 1 as test`
- Should return `1` without errors

**Important Notes:**
- Use URI scheme `neo4j+s://` (not `bolt://` or `bolt+s://`)
- Username is always `neo4j` (not "Aura" or your email)
- Encryption settings are embedded in the `+s` URI scheme
- Free tier instances pause after 3 days - resume before use

**API Rate Limits:**
- OpenAI: Monitor usage at platform.openai.com
- Jina.ai: Check rate limits in dashboard

## Cost Estimates

- **Supabase:** Free tier (500MB database, 2GB bandwidth)
- **Neo4j Aura:** Free tier (1 instance, 200k nodes, 400k relationships)
- **OpenAI GPT-5-mini:** ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- **OpenAI Embeddings:** ~$0.02 per 1M tokens
- **Jina.ai:** Free tier (1000 requests/day)

**Estimated monthly cost for moderate use:** $10-30

## References

- Main deployment guide: [Deployment Guide](./general.md)
- Installation guide: [Installation Guide](../2-getting-started/installation.md)
- Project instructions: [CONVENTIONS.md](../../.spec_system/CONVENTIONS.md)
