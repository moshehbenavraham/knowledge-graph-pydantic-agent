# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Luminari AI Agent system.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Installation Issues](#installation-issues)
- [Configuration Problems](#configuration-problems)
- [Runtime Errors](#runtime-errors)
- [Performance Issues](#performance-issues)
- [Database Problems](#database-problems)
- [API Integration Issues](#api-integration-issues)
- [Memory System Issues](#memory-system-issues)
- [Docker Issues](#docker-issues)
- [Monitoring and Debugging](#monitoring-and-debugging)

## Quick Diagnostics

### Health Check Commands

```bash
# Check system health
curl http://localhost:8501/health

# Detailed health check (if FastAPI endpoints are running)
curl http://localhost:8000/health/detailed

# Check individual components
curl http://localhost:8000/health/components/database
curl http://localhost:8000/health/components/llm
curl http://localhost:8000/health/components/embedding
```

### Environment Validation

```bash
# Check Python version
python --version  # Should be 3.11+

# Verify virtual environment
which python
pip list | grep -E "(streamlit|pydantic-ai|supabase)"

# Check environment variables
env | grep -E "(SUPABASE|LLM|EMBEDDING)"
```

## Installation Issues

### Common Installation Problems

#### 1. Python Version Compatibility

**Error:** `Python 3.11+ required`

**Solution:**
```bash
# Install Python 3.11 or higher
pyenv install 3.11.0
pyenv local 3.11.0

# Or use conda
conda create -n luminari python=3.11
conda activate luminari
```

#### 2. Dependency Conflicts

**Error:** `pip install fails with dependency conflicts`

**Solution:**
```bash
# Clean installation
pip uninstall -y -r requirements.txt
pip cache purge
pip install -r requirements.txt

# Alternative: Use pip-tools
pip install pip-tools
pip-compile requirements.in
pip install -r requirements.txt
```

#### 3. System Dependencies Missing

**Error:** `gcc: command not found` or similar build errors

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install build-essential python3-dev

# macOS
xcode-select --install

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
sudo yum install python3-devel
```

### Installation Verification

```bash
# Run setup
make setup

# Verify installation
python -c "import streamlit, pydantic_ai, supabase; print('All imports successful')"

# Test basic functionality
python -c "from src.clients.database import get_supabase_client; print('Database client OK')"
```

## Configuration Problems

### Environment Variables

#### 1. Missing Required Variables

**Error:** `KeyError: 'SUPABASE_URL'`

**Solution:**
```bash
# Copy example configuration
cp .env.example .env

# Edit with your values
nano .env

# Verify variables are loaded
python -c "import os; print(os.getenv('SUPABASE_URL'))"
```

#### 2. Invalid API Keys

**Error:** `Authentication failed` or `Invalid API key`

**Diagnosis:**
```bash
# Test Supabase connection
python -c "
from src.clients.database import get_supabase_client
client = get_supabase_client()
result = client.table('documents').select('*').limit(1).execute()
print('Supabase OK' if result else 'Supabase Failed')
"

# Test LLM API
python -c "
import asyncio
from src.clients.llm import get_llm_client
async def test():
    client = get_llm_client()
    response = await client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{'role': 'user', 'content': 'test'}],
        max_tokens=5
    )
    print('LLM OK')
asyncio.run(test())
"
```

#### 3. Database Schema Issues

**Error:** `relation "documents" does not exist`

**Solution:**
```bash
# Run SQL setup scripts
psql -h your-supabase-host -U postgres -d postgres -f sql/documents.sql
psql -h your-supabase-host -U postgres -d postgres -f sql/document_metadata.sql
psql -h your-supabase-host -U postgres -d postgres -f sql/document_rows.sql
psql -h your-supabase-host -U postgres -d postgres -f sql/execute_sql_rpc.sql

# Or use Supabase dashboard to run the scripts
```

## Runtime Errors

### Common Runtime Issues

#### 1. Streamlit Connection Errors

**Error:** `ConnectionError: Failed to connect to Streamlit`

**Diagnosis:**
```bash
# Check if port is in use
lsof -i :8501

# Check Streamlit logs
streamlit run src/ui/streamlit_app.py --logger.level debug
```

**Solution:**
```bash
# Use different port
streamlit run src/ui/streamlit_app.py --server.port 8502

# Clear Streamlit cache
rm -rf ~/.streamlit/
```

#### 2. Import Errors

**Error:** `ModuleNotFoundError: No module named 'src'`

**Solution:**
```bash
# Install in development mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Verify Python path
python -c "import sys; print(sys.path)"
```

#### 3. Async/Await Issues

**Error:** `RuntimeError: This event loop is already running`

**Solution:**
```python
# In Jupyter notebooks, use nest_asyncio
import nest_asyncio
nest_asyncio.apply()

# Or use asyncio.create_task() instead of asyncio.run()
```

## Performance Issues

### Slow Response Times

#### 1. Database Query Optimization

**Diagnosis:**
```sql
-- Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check index usage
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE tablename = 'documents';
```

**Solution:**
```sql
-- Add indexes for common queries
CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING gin (metadata);
```

#### 2. Memory Usage Optimization

**Diagnosis:**
```bash
# Monitor memory usage
htop
# Or
ps aux | grep python | head -10

# Check Python memory usage
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

**Solution:**
```python
# In your .env file
STREAMLIT_SERVER_MAX_UPLOAD_SIZE=200
STREAMLIT_SERVER_MAX_MESSAGE_SIZE=200

# Optimize batch sizes
EMBEDDING_BATCH_SIZE=10
RAG_CHUNK_SIZE=1000
```

#### 3. API Rate Limiting

**Error:** `Rate limit exceeded`

**Solution:**
```python
# Check rate limit status
curl http://localhost:8000/health/rate-limits/your-user-id

# Adjust rate limits in configuration
# Edit src/utils/rate_limiting.py
```

## Database Problems

### Connection Issues

#### 1. Supabase Connection Timeout

**Error:** `Connection timeout`

**Diagnosis:**
```bash
# Test network connectivity
ping your-supabase-host.supabase.co

# Test database connection
psql "postgresql://postgres:password@your-host:5432/postgres" -c "SELECT 1;"
```

**Solution:**
```bash
# Check firewall settings
# Verify Supabase project is not paused
# Check connection pooling settings
```

#### 2. Vector Extension Issues

**Error:** `extension "vector" does not exist`

**Solution:**
```sql
-- Enable pgvector extension in Supabase dashboard
-- Or run in SQL editor:
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### Data Issues

#### 1. Embedding Dimension Mismatch

**Error:** `vector dimension mismatch`

**Solution:**
```sql
-- Check current dimensions
SELECT embedding <-> '[0,0,0]'::vector FROM documents LIMIT 1;

-- Update table schema if needed
ALTER TABLE documents ALTER COLUMN embedding TYPE vector(1536);

-- For Ollama (768 dimensions)
ALTER TABLE documents ALTER COLUMN embedding TYPE vector(768);
```

## API Integration Issues

### LLM Provider Issues

#### 1. OpenAI API Errors

**Error:** `Invalid API key` or `Rate limit exceeded`

**Diagnosis:**
```bash
# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Check usage
curl https://api.openai.com/v1/usage \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

#### 2. Ollama Connection Issues

**Error:** `Connection refused to localhost:11434`

**Solution:**
```bash
# Start Ollama service
ollama serve

# Check if running
curl http://localhost:11434/api/tags

# Pull required models
ollama pull llama3.1
ollama pull nomic-embed-text
```

### Web Search Issues

#### 1. Brave API Problems

**Error:** `Brave API authentication failed`

**Solution:**
```bash
# Test Brave API
curl -H "X-Subscription-Token: $BRAVE_API_KEY" \
  "https://api.search.brave.com/res/v1/web/search?q=test"

# Check API quota
# Visit Brave API dashboard
```

#### 2. SearXNG Fallback Issues

**Error:** `SearXNG instance not responding`

**Solution:**
```bash
# Test SearXNG instance
curl "$SEARXNG_BASE_URL/search?q=test&format=json"

# Start local SearXNG with Docker
docker run -d -p 8080:8080 searxng/searxng
```

## Memory System Issues

### Mem0 Integration Problems

#### 1. Memory Service Connection

**Error:** `Failed to connect to memory service`

**Diagnosis:**
```python
# Test mem0 connection
from src.clients.memory import get_mem0_client
client = get_mem0_client()
result = client.add("test memory", user_id="test")
print(result)
```

**Solution:**
```bash
# Check mem0 configuration
# Verify vector store connection
# Check embedding service
```

#### 2. Memory Retrieval Issues

**Error:** `No memories found` or `Memory search failed`

**Solution:**
```python
# Check memory storage
client = get_mem0_client()
memories = client.get_all(user_id="your-user-id")
print(f"Found {len(memories)} memories")

# Test memory search
results = client.search("test query", user_id="your-user-id")
print(results)
```

## Docker Issues

### Container Problems

#### 1. Build Failures

**Error:** `Docker build failed`

**Solution:**
```bash
# Clean Docker cache
docker system prune -a

# Rebuild with no cache
docker-compose build --no-cache

# Check Docker logs
docker-compose logs app
```

#### 2. Service Communication

**Error:** `Service unavailable` between containers

**Solution:**
```bash
# Check network connectivity
docker-compose exec app ping supabase

# Verify service names in docker-compose.yml
# Check port mappings
docker-compose ps
```

## Monitoring and Debugging

### Enable Debug Logging

```bash
# Set environment variables
export LOG_LEVEL=DEBUG
export STREAMLIT_LOGGER_LEVEL=debug

# Run with verbose logging
streamlit run src/ui/streamlit_app.py --logger.level debug
```

### Performance Monitoring

```bash
# Check metrics endpoint
curl http://localhost:8000/metrics

# Monitor system resources
htop
iotop
```

### Debug Tools

```python
# Add debugging to your code
from src.utils.monitoring import logger

logger.debug("Debug message", extra_data="value")
logger.info("Info message", user_id="123")
logger.error("Error occurred", error=str(e))
```

## Getting Help

### Log Collection

```bash
# Collect system information
python -c "
import sys, platform, pkg_resources
print(f'Python: {sys.version}')
print(f'Platform: {platform.platform()}')
print('Packages:')
for pkg in pkg_resources.working_set:
    if pkg.project_name in ['streamlit', 'pydantic-ai', 'supabase']:
        print(f'  {pkg.project_name}: {pkg.version}')
"

# Collect logs
journalctl -u your-service --since "1 hour ago" > system.log
docker-compose logs > docker.log
```

### Health Check Report

```bash
# Generate comprehensive health report
curl http://localhost:8000/health/detailed > health_report.json

# Check all components
for component in database llm embedding memory web_search; do
    echo "=== $component ==="
    curl http://localhost:8000/health/components/$component
    echo
done
```

### Support Information

When reporting issues, please include:

1. **System Information:**
   - Operating system and version
   - Python version
   - Package versions

2. **Configuration:**
   - Environment variables (sanitized)
   - Configuration files
   - Docker setup (if applicable)

3. **Error Details:**
   - Full error messages
   - Stack traces
   - Steps to reproduce

4. **Logs:**
   - Application logs
   - System logs
   - Health check results

5. **Context:**
   - What you were trying to do
   - Expected vs actual behavior
   - Recent changes to the system
