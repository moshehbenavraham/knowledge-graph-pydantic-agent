# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Luminari AI Agent system, including Phase 3 Agent Intelligence Layer components.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Phase 3 Specific Issues](#phase-3-specific-issues)
- [Installation Issues](#installation-issues)
- [Configuration Problems](#configuration-problems)
- [Runtime Errors](#runtime-errors)
- [Performance Issues](#performance-issues)
- [Database Problems](#database-problems)
- [API Integration Issues](#api-integration-issues)
- [Memory System Issues](#memory-system-issues)
- [Agentic RAG Issues](#agentic-rag-issues)
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
env | grep -E "(SUPABASE|LLM|EMBEDDING|NEO4J)"
```

## Phase 3 Specific Issues

### Intent Analysis Problems

#### 1. Poor Intent Classification Accuracy

**Error:** Intent classification below 90% accuracy threshold

**Diagnosis:**
```python
# Test intent analysis directly
from src.agentic_rag.agent.intent_analyzer import IntentAnalyzer

analyzer = IntentAnalyzer()
test_queries = [
    "What is the capital of France?",
    "How is Microsoft related to OpenAI?", 
    "When did AI research begin?",
    "Compare Python and JavaScript",
    "What are emerging AI trends?"
]

for query in test_queries:
    result = await analyzer.analyze(query)
    print(f"Query: {query}")
    print(f"Intent: {result.primary_intent}")
    print(f"Confidence: {result.confidence}")
    print("---")
```

**Solution:**
```bash
# Check intent analysis configuration
export INTENT_ANALYSIS_TIMEOUT=2.0
export CONFIDENCE_THRESHOLD=0.7

# Update intent patterns if needed
# Review src/agentic_rag/agent/intent_analyzer.py

# Retrain or adjust intent scoring weights
```

#### 2. Entity Extraction Failures

**Error:** `Entity extraction returned empty results`

**Diagnosis:**
```python
# Test entity extraction
query = "What is the relationship between Microsoft and OpenAI in 2023?"
result = await analyzer.analyze(query)

print(f"Entities found: {len(result.entities)}")
for entity in result.entities:
    print(f"  {entity.name} ({entity.type})")
    
print(f"Temporal context: {result.temporal_context}")
```

**Solution:**
```bash
# Check entity extraction model
export EXTRACTION_MODEL=gpt-4o-mini

# Verify entity patterns in configuration
# Update entity type mappings if needed
```

### Search Strategy Issues

#### 1. Poor Search Strategy Selection

**Error:** Suboptimal search strategy chosen (below 88% accuracy)

**Diagnosis:**
```python
# Test search routing
from src.agentic_rag.agent.router import SearchRouter

router = SearchRouter()
test_cases = [
    ("What is machine learning?", "vector_search"),
    ("How is Tesla related to SpaceX?", "graph_search"), 
    ("Compare AI frameworks", "hybrid_search"),
    ("AI trends in healthcare", "comprehensive_search")
]

for query, expected_strategy in test_cases:
    intent_result = await analyzer.analyze(query)
    selected_strategy = await router.route_query(query, intent_result)
    
    print(f"Query: {query}")
    print(f"Expected: {expected_strategy}")
    print(f"Selected: {selected_strategy}")
    print(f"Match: {expected_strategy == selected_strategy}")
    print("---")
```

**Solution:**
```python
# Adjust routing thresholds in configuration
ROUTING_CONFIG = {
    "complexity_threshold": 0.8,
    "relationship_confidence": 0.85,
    "temporal_confidence": 0.8,
    "comparison_confidence": 0.85
}

# Review routing logic in src/agentic_rag/agent/router.py
```

#### 2. Search Performance Below Targets

**Error:** Search latency exceeds performance targets

**Diagnosis:**
```python
# Performance test individual search strategies
import time
from src.agentic_rag.agent.tools import vector_search, graph_search, hybrid_search

async def test_search_performance():
    query = "artificial intelligence applications"
    
    # Vector search target: <150ms
    start = time.time()
    vector_result = await vector_search(query)
    vector_time = (time.time() - start) * 1000
    print(f"Vector search: {vector_time:.2f}ms (target: <150ms)")
    
    # Graph search target: <500ms  
    start = time.time()
    graph_result = await graph_search(query)
    graph_time = (time.time() - start) * 1000
    print(f"Graph search: {graph_time:.2f}ms (target: <500ms)")
    
    # Hybrid search target: <300ms
    start = time.time()
    hybrid_result = await hybrid_search(query)
    hybrid_time = (time.time() - start) * 1000
    print(f"Hybrid search: {hybrid_time:.2f}ms (target: <300ms)")

await test_search_performance()
```

**Solution:**
```bash
# Optimize database indexes
# Check pgvector index configuration
# Verify Neo4j indexes for entities and relationships

# Adjust timeout settings
export VECTOR_SEARCH_TIMEOUT=2.0
export GRAPH_SEARCH_TIMEOUT=3.0

# Enable caching
export ENABLE_CACHING=true
export GRAPH_CACHE_SIZE=500
export EMBEDDING_CACHE_SIZE=1000
```

### Knowledge Graph Integration Issues

#### 1. Neo4j Connection Problems

**Error:** `Neo4j connection failed` or `Database not available`

**Diagnosis:**
```bash
# Test Neo4j connectivity
curl http://localhost:7474/
curl -u neo4j:password http://localhost:7474/db/data/

# Test from Python
python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687', 
                             auth=('neo4j', 'password'))
with driver.session() as session:
    result = session.run('RETURN 1 as test')
    print('Neo4j connection OK:', result.single()['test'])
driver.close()
"
```

**Solution:**
```bash
# Start Neo4j if not running
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# Verify environment variables
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=password

# Initialize knowledge graph
python -m EXAMPLE_agentic-rag-knowledge-graph.agent.graph_utils init
```

#### 2. Knowledge Extraction Issues

**Error:** `Entity extraction failed` or `Relationship mapping error`

**Diagnosis:**
```python
# Test knowledge extraction pipeline
from src.agentic_rag.ingestion.knowledge_extractor import KnowledgeExtractor

extractor = KnowledgeExtractor()
test_text = "Microsoft invested $10 billion in OpenAI in 2023."

entities = await extractor.extract_entities(test_text)
relationships = await extractor.extract_relationships(test_text)
facts = await extractor.extract_facts(test_text)

print(f"Entities: {len(entities)}")
print(f"Relationships: {len(relationships)}") 
print(f"Facts: {len(facts)}")

# Verify each extraction
for entity in entities:
    print(f"Entity: {entity.name} ({entity.type})")
```

**Solution:**
```bash
# Check extraction model configuration
export EXTRACTION_MODEL=gpt-4o-mini
export MAX_ENTITIES_PER_CHUNK=10
export MAX_FACT_LENGTH=500

# Verify Graphiti integration
pip install --upgrade graphiti-ai

# Check extraction prompts and update if needed
```

### Response Generation Issues

#### 1. Missing Citations

**Error:** Response lacks required source citations (below 100% target)

**Diagnosis:**
```python
# Test response generation
from src.agentic_rag.agent.response_generator import ResponseGenerator

generator = ResponseGenerator()
query = "What is machine learning?"
mock_results = [
    {"content": "ML is a subset of AI", "source": "ai_guide.pdf", "confidence": 0.9}
]

response = await generator.generate_response(query, mock_results)

print(f"Answer: {response.answer}")
print(f"Sources: {len(response.sources)}")
print(f"Citations included: {len(response.sources) > 0}")

for source in response.sources:
    print(f"  - {source.get('source', 'NO SOURCE')}")
```

**Solution:**
```python
# Update response generation to enforce citations
# Check src/agentic_rag/agent/response_generator.py

# Ensure all search results include source metadata
# Verify citation extraction logic
```

#### 2. Poor Confidence Scoring

**Error:** Confidence scores not in expected 0.0-1.0 range or inaccurate

**Diagnosis:**
```python
# Test confidence calculation
response = await generator.generate_response(query, mock_results)

print(f"Confidence: {response.confidence}")
print(f"Type: {type(response.confidence)}")
print(f"In range [0,1]: {0.0 <= response.confidence <= 1.0}")

# Test with multiple source qualities
low_quality = [{"content": "basic info", "confidence": 0.3}]
high_quality = [{"content": "detailed info", "confidence": 0.95}]

low_response = await generator.generate_response(query, low_quality)
high_response = await generator.generate_response(query, high_quality)

print(f"Low quality confidence: {low_response.confidence}")
print(f"High quality confidence: {high_response.confidence}")
```

**Solution:**
```python
# Review confidence calculation algorithm
# Adjust confidence weighting factors
# Ensure proper source quality assessment
```

## Agentic RAG Issues

### Dual Database Sync Problems

#### 1. Content Duplication in Neo4j

**Error:** Content found in Neo4j (violates zero duplication principle)

**Diagnosis:**
```cypher
// Check for content in Neo4j nodes
MATCH (n)
WHERE EXISTS(n.content) AND length(n.content) > 100
RETURN count(n) as nodes_with_content, 
       avg(length(n.content)) as avg_content_length
```

**Solution:**
```cypher
// Remove content from Neo4j nodes  
MATCH (n)
WHERE EXISTS(n.content)
REMOVE n.content
```

#### 2. Reference ID Mismatches

**Error:** Chunk references in Neo4j don't match PostgreSQL IDs

**Diagnosis:**
```python
# Verify reference integrity
from src.agentic_rag.storage.postgres_store import PostgresStore
from src.agentic_rag.storage.neo4j_store import Neo4jStore

postgres_store = PostgresStore()
neo4j_store = Neo4jStore()

# Get sample chunk IDs from PostgreSQL
pg_chunk_ids = await postgres_store.get_chunk_ids(limit=10)

# Check if they exist in Neo4j references
for chunk_id in pg_chunk_ids:
    neo4j_refs = await neo4j_store.get_chunk_references(chunk_id)
    print(f"Chunk {chunk_id}: {len(neo4j_refs)} Neo4j references")
```

**Solution:**
```python
# Rebuild reference integrity
await neo4j_store.rebuild_chunk_references()

# Verify storage efficiency
efficiency = await calculate_storage_efficiency()
print(f"Storage efficiency: {efficiency:.1%} (target: >99%)")
```

### Search Result Merging Issues

#### 1. Poor Hybrid Search Results

**Error:** Hybrid search performs worse than individual strategies

**Diagnosis:**
```python
# Compare individual vs hybrid results
vector_results = await vector_search(query)
graph_results = await graph_search(query) 
hybrid_results = await hybrid_search(query)

print(f"Vector results: {len(vector_results.results)}")
print(f"Graph results: {len(graph_results.results)}")
print(f"Hybrid results: {len(hybrid_results.results)}")
print(f"Hybrid quality: {hybrid_results.quality_score}")
```

**Solution:**
```python
# Adjust result merging weights
MERGE_CONFIG = {
    "vector_weight": 0.6,
    "graph_weight": 0.4, 
    "boost_factor": 0.2,
    "diversity_threshold": 0.8
}

# Review merging algorithm in tools.py
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
