# Performance Optimization Guide

This guide provides strategies and best practices for optimizing the performance of your Luminari AI Agent system.

## Table of Contents

- [Performance Monitoring](#performance-monitoring)
- [Database Optimization](#database-optimization)
- [LLM and API Optimization](#llm-and-api-optimization)
- [Memory System Optimization](#memory-system-optimization)
- [Caching Strategies](#caching-strategies)
- [Resource Management](#resource-management)
- [Scaling Considerations](#scaling-considerations)
- [Benchmarking and Testing](#benchmarking-and-testing)

## Performance Monitoring

### Key Metrics to Track

```python
# Enable monitoring
export ENABLE_METRICS=true
export METRICS_PORT=8000

# Key metrics to monitor:
# - Response time (p50, p95, p99)
# - Request rate (requests/second)
# - Error rate (%)
# - Resource usage (CPU, memory, disk)
# - Database query performance
# - LLM token usage and costs
```

### Monitoring Setup

```bash
# Start metrics server
python -c "from src.utils.monitoring import monitor; monitor.start_metrics_server(8000)"

# View metrics
curl http://localhost:8000/metrics

# Grafana dashboard (optional)
docker run -d -p 3000:3000 grafana/grafana
```

### Performance Baselines

**Target Performance Metrics:**
- Simple queries: < 2 seconds
- Complex RAG queries: < 5 seconds
- Document processing: < 30 seconds per MB
- Memory retrieval: < 500ms
- Database queries: < 100ms

## Database Optimization

### Vector Search Optimization

```sql
-- Optimize vector indexes
CREATE INDEX CONCURRENTLY idx_documents_embedding_ivfflat
ON documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- For better recall, use HNSW (if available)
CREATE INDEX CONCURRENTLY idx_documents_embedding_hnsw
ON documents USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Analyze table statistics
ANALYZE documents;
```

### Query Optimization

```sql
-- Optimize common queries
EXPLAIN ANALYZE SELECT * FROM documents
WHERE embedding <-> $1 < 0.8
ORDER BY embedding <-> $1
LIMIT 10;

-- Add metadata indexes
CREATE INDEX CONCURRENTLY idx_documents_metadata_gin
ON documents USING gin (metadata);

-- Optimize text search
CREATE INDEX CONCURRENTLY idx_documents_content_fts
ON documents USING gin (to_tsvector('english', content));
```

### Connection Pooling

```python
# Configure connection pooling
SUPABASE_POOL_SIZE=20
SUPABASE_MAX_OVERFLOW=30
SUPABASE_POOL_TIMEOUT=30

# Use connection pooling in production
from sqlalchemy.pool import QueuePool
```

### Database Configuration

```sql
-- Optimize PostgreSQL settings
-- In postgresql.conf:
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
```

## LLM and API Optimization

### Request Optimization

```python
# Optimize LLM requests
LLM_MAX_TOKENS=2000  # Reduce for faster responses
LLM_TEMPERATURE=0.1  # Lower for more consistent responses
LLM_BATCH_SIZE=5     # Batch requests when possible

# Use streaming for better UX
async def stream_response():
    async for chunk in llm_stream:
        yield chunk
```

### Model Selection

```python
# Choose appropriate models for tasks
FAST_MODEL="gpt-4o-mini"      # For simple queries
SMART_MODEL="gpt-4o"          # For complex reasoning
EMBEDDING_MODEL="text-embedding-3-small"  # Balanced performance/cost

# Use model routing based on complexity
def select_model(query_complexity):
    if query_complexity < 0.5:
        return FAST_MODEL
    return SMART_MODEL
```

### API Rate Limiting

```python
# Configure rate limits
USER_RATE_LIMITS = {
    "free": {"requests": 10, "window": 60},
    "premium": {"requests": 100, "window": 60},
    "enterprise": {"requests": 1000, "window": 60}
}

API_RATE_LIMITS = {
    "openai": {"requests": 60, "window": 60},
    "brave": {"requests": 100, "window": 3600}
}
```

### Caching LLM Responses

```python
# Implement response caching
import hashlib
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_llm_response(query_hash, model):
    # Cache based on query hash and model
    return llm_response

# Use Redis for distributed caching
import redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_response(query, response, ttl=3600):
    key = f"llm:{hashlib.md5(query.encode()).hexdigest()}"
    redis_client.setex(key, ttl, response)
```

## Memory System Optimization

### Memory Configuration

```python
# Optimize mem0 configuration
MEM0_CONFIG = {
    "vector_store": {
        "provider": "supabase",
        "config": {
            "collection_name": "mem0_memories",
            "embedding_model_dims": 1536,
            "distance_metric": "cosine"
        }
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-small",
            "batch_size": 100  # Batch embeddings
        }
    }
}
```

### Memory Retrieval Optimization

```python
# Optimize memory search
async def optimized_memory_search(query, user_id, limit=5):
    # Use semantic search with filters
    results = memory_client.search(
        query=query,
        user_id=user_id,
        limit=limit,
        filters={"timestamp": {"$gte": "2024-01-01"}}  # Recent memories
    )
    return results

# Implement memory hierarchy
def get_relevant_memories(query, user_id):
    # Recent memories (high weight)
    recent = memory_client.search(query, user_id, limit=3,
                                 filters={"days_ago": {"$lte": 7}})

    # Important memories (medium weight)
    important = memory_client.search(query, user_id, limit=2,
                                   filters={"importance": {"$gte": 0.8}})

    return combine_memories(recent, important)
```

## Caching Strategies

### Multi-Level Caching

```python
# Application-level caching
from functools import lru_cache
import asyncio

# In-memory cache for frequent queries
@lru_cache(maxsize=500)
def cache_document_chunks(doc_id):
    return get_document_chunks(doc_id)

# Redis cache for shared data
async def cached_rag_search(query, ttl=1800):
    cache_key = f"rag:{hashlib.md5(query.encode()).hexdigest()}"

    # Try cache first
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Compute and cache
    result = await rag_search(query)
    await redis_client.setex(cache_key, ttl, json.dumps(result))
    return result
```

### Streamlit Caching

```python
# Optimize Streamlit caching
@st.cache_resource
def get_expensive_resource():
    return load_large_model()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_processed_data(data_hash):
    return process_large_dataset()

# Clear cache when needed
if st.button("Clear Cache"):
    st.cache_data.clear()
    st.cache_resource.clear()
```

## Resource Management

### Memory Management

```python
# Monitor memory usage
import psutil
import gc

def monitor_memory():
    process = psutil.Process()
    memory_info = process.memory_info()

    if memory_info.rss > 1024 * 1024 * 1024:  # 1GB
        gc.collect()  # Force garbage collection

    return memory_info.rss / 1024 / 1024  # MB

# Optimize large data processing
def process_large_file(file_path, chunk_size=1024*1024):
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            yield process_chunk(chunk)
            gc.collect()  # Clean up after each chunk
```

### CPU Optimization

```python
# Use async/await for I/O bound operations
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def parallel_processing(tasks):
    # Use thread pool for CPU-bound tasks
    with ThreadPoolExecutor(max_workers=4) as executor:
        loop = asyncio.get_event_loop()
        futures = [
            loop.run_in_executor(executor, cpu_bound_task, task)
            for task in tasks
        ]
        return await asyncio.gather(*futures)

# Optimize vector operations
import numpy as np
from numba import jit

@jit(nopython=True)
def fast_cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
```

### Disk I/O Optimization

```python
# Use async file operations
import aiofiles

async def async_file_processing(file_paths):
    tasks = []
    for path in file_paths:
        tasks.append(process_file_async(path))

    return await asyncio.gather(*tasks)

async def process_file_async(file_path):
    async with aiofiles.open(file_path, 'r') as f:
        content = await f.read()
        return process_content(content)
```

## Scaling Considerations

### Horizontal Scaling

```yaml
# Docker Compose scaling
version: '3.8'
services:
  app:
    build: .
    deploy:
      replicas: 3
    environment:
      - WORKER_ID=${HOSTNAME}

  nginx:
    image: nginx
    ports:
      - "80:80"
    depends_on:
      - app
```

### Load Balancing

```nginx
# Nginx configuration
upstream app_servers {
    server app1:8501;
    server app2:8501;
    server app3:8501;
}

server {
    listen 80;
    location / {
        proxy_pass http://app_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Database Scaling

```python
# Read replicas for scaling
DATABASE_CONFIG = {
    "write": "postgresql://user:pass@primary:5432/db",
    "read": [
        "postgresql://user:pass@replica1:5432/db",
        "postgresql://user:pass@replica2:5432/db"
    ]
}

def get_db_connection(operation="read"):
    if operation == "write":
        return connect(DATABASE_CONFIG["write"])
    else:
        # Round-robin read replicas
        replica = random.choice(DATABASE_CONFIG["read"])
        return connect(replica)
```

## Benchmarking and Testing

### Performance Testing

```python
# Load testing with locust
from locust import HttpUser, task, between

class AgentUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def simple_query(self):
        self.client.post("/chat", json={
            "message": "What is machine learning?",
            "user_id": "test_user"
        })

    @task(3)  # 3x weight
    def complex_query(self):
        self.client.post("/chat", json={
            "message": "Analyze the financial data and create visualizations",
            "user_id": "test_user"
        })

# Run load test
# locust -f performance_test.py --host=http://localhost:8501
```

### Benchmarking Scripts

```python
# Benchmark different components
import time
import asyncio
from statistics import mean, median

async def benchmark_rag_search(queries, iterations=10):
    results = []

    for query in queries:
        times = []
        for _ in range(iterations):
            start = time.time()
            await rag_search(query)
            times.append(time.time() - start)

        results.append({
            "query": query,
            "mean_time": mean(times),
            "median_time": median(times),
            "min_time": min(times),
            "max_time": max(times)
        })

    return results

# Database query benchmarks
def benchmark_database_queries():
    queries = [
        "SELECT * FROM documents LIMIT 10",
        "SELECT * FROM documents WHERE embedding <-> $1 < 0.8 LIMIT 5",
        "SELECT COUNT(*) FROM documents WHERE metadata->>'type' = 'pdf'"
    ]

    for query in queries:
        start = time.time()
        execute_query(query)
        print(f"Query: {query[:50]}... Time: {time.time() - start:.3f}s")
```

### Performance Profiling

```python
# Profile Python code
import cProfile
import pstats

def profile_function(func, *args, **kwargs):
    profiler = cProfile.Profile()
    profiler.enable()

    result = func(*args, **kwargs)

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions

    return result

# Memory profiling
from memory_profiler import profile

@profile
def memory_intensive_function():
    # Your function here
    pass
```

## Best Practices Summary

### Development
- Use async/await for I/O operations
- Implement proper caching at multiple levels
- Monitor performance metrics continuously
- Profile code regularly to identify bottlenecks

### Production
- Use connection pooling for databases
- Implement proper rate limiting
- Set up monitoring and alerting
- Use CDN for static assets
- Implement graceful degradation

### Scaling
- Design for horizontal scaling from the start
- Use load balancers and reverse proxies
- Implement database read replicas
- Consider microservices architecture for large deployments

### Monitoring
- Track key performance indicators (KPIs)
- Set up alerts for performance degradation
- Use distributed tracing for complex workflows
- Regularly review and optimize based on metrics
