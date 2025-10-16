# Analytics Population Guide

This guide provides specific actions and prompts to populate each analytics table with sample data for testing the dashboard.

## 📊 Analytics Tables Overview

| Table | Trigger | Current Integration Status |
|-------|---------|----------------------------|
| `search_analytics` | RAG search queries | ✅ **Active** - Logs via HybridSearch |
| `tool_usage_analytics` | Agent tool calls | ⚠️ **Not Integrated** - Logger exists, no callers |
| `agent_interactions` | User-agent conversations | ⚠️ **Not Integrated** - Logger exists, no callers |
| `ingestion_analytics` | Document ingestion | ✅ **Active** - Logs during ingestion |
| `system_metrics` | System snapshots | ⚠️ **Not Integrated** - Logger exists, no callers |

---

## 1️⃣ SEARCH ANALYTICS (✅ Currently Logging)

**What it tracks:** All RAG search operations with intent detection, strategy selection, and performance metrics.

**How it's logged:** Automatically when you use RAG retrieval tools in the chat.

### Integration Point
- **File:** `src/agentic_rag/search/hybrid_search.py:516`
- **Method:** `_log_search_analytics()` called at end of every search

### Sample Prompts to Populate

**Vector-Heavy Queries** (semantic similarity):
```
What is OpenAI's funding history?
Explain how transformers work
What are the benefits of using RAG systems?
Tell me about cloud computing trends
```

**Graph-Heavy Queries** (entity relationships):
```
Who invested in Anthropic?
What companies are connected to Microsoft?
Show me relationships between OpenAI and its investors
Which executives have moved between companies?
```

**Temporal Queries** (time-based):
```
When did the AI funding boom start?
What happened in 2023 regarding AI investments?
Recent developments in AI regulation
Timeline of major AI acquisitions
```

**Entity-Focused Queries** (specific entities):
```
Tell me about Sam Altman
What is Microsoft's role in AI?
Information about Amazon and Anthropic partnership
Details on Google's AI strategy
```

**Hybrid Queries** (mixed patterns):
```
How did the AI funding landscape change after ChatGPT launched?
Compare Anthropic and OpenAI's approaches to safety
What are the key differences between cloud AI platforms?
```

### How to Execute
1. **Via UI (Streamlit):**
   ```bash
   make run-ui
   ```
   - Navigate to the Chat tab
   - Type any of the above prompts
   - Each query triggers a `SearchAnalyticsEvent`

2. **Via API:**
   ```bash
   make run-api

   # In another terminal:
   curl -X POST http://localhost:8058/api/v1/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "What is OpenAI?"}'
   ```

### Expected Data
- **Intent Distribution:** Mix of VECTOR_HEAVY, GRAPH_HEAVY, HYBRID, TEMPORAL, ENTITY_FOCUSED
- **Latency Metrics:** total_latency_ms, vector_latency_ms, graph_latency_ms
- **Result Counts:** chunks_returned, entities_found, facts_found
- **Boost Flags:** graph_boost_applied, entity_boost_applied

---

## 2️⃣ TOOL USAGE ANALYTICS (⚠️ NOT Currently Logging)

**What it tracks:** Individual tool executions (RAG retrieval, web search, SQL queries, code execution, image analysis).

**Status:** Logger exists but no integration points yet.

### Required Integration
Need to add logging to:
- `src/tools/rag.py` - retrieve_relevant_documents, list_documents, get_document_content
- `src/tools/web_search.py` - search_web
- `src/tools/sql_query.py` - execute_sql_query
- `src/tools/code_execution.py` - execute_python_code
- `src/tools/image_analysis.py` - analyze_image

### Sample Prompts (Once Integrated)
```
Search the web for latest AI news
Retrieve documents about OpenAI
Execute this Python code: print("hello")
What's in the documents table? (SQL query)
Analyze this image: [upload screenshot]
```

### Expected Data (Once Integrated)
- **Tool Names:** retrieve_relevant_documents, search_web, execute_sql_query, etc.
- **Success Rate:** Boolean success/failure
- **Execution Times:** Per-tool latency
- **Error Tracking:** error_type, error_message

---

## 3️⃣ AGENT INTERACTIONS (⚠️ NOT Currently Logging)

**What it tracks:** Complete user-agent conversation turns with tool usage, model info, and user feedback.

**Status:** Logger exists but no integration points yet.

### Required Integration
Need to add logging to:
- `src/ui/features/base_handler.py` - After agent response
- `src/ui/features/streaming_handler.py` - After streaming complete
- `src/api/endpoints/chat.py` - API chat endpoint

### Sample Actions (Once Integrated)
1. **Query Interaction:**
   - Ask: "What is OpenAI?"
   - Logs: user_message, agent_response, response_time_ms, tools_called

2. **Feedback:**
   - Click thumbs up/down on responses
   - Logs: user_feedback='thumbs_up', feedback_comment

3. **RAG Usage:**
   - Ask question that triggers RAG
   - Logs: rag_used=True, tools_called=['retrieve_relevant_documents']

4. **Memory Usage:**
   - In Advanced mode with mem0 enabled
   - Logs: memory_used=True

### Expected Data (Once Integrated)
- **Interaction Types:** query, feedback, correction, clarification, error
- **Performance:** response_time_ms, tokens_used
- **Context:** tools_called, rag_used, memory_used
- **Quality:** user_feedback, feedback_comment

---

## 4️⃣ INGESTION ANALYTICS (✅ Currently Logging)

**What it tracks:** Document ingestion performance (chunking, embedding, graph extraction).

**How it's logged:** Automatically during document ingestion.

### Integration Point
- **File:** `src/agentic_rag/ingestion/pipeline.py`
- **Method:** Called after each document is processed

### How to Populate

**Ingest Example Documents:**
```bash
# Full ingestion (all 21 docs)
make ingest

# OR specific documents
python -m src.agentic_rag.ingestion ingest --path docs/example_docs/doc1_openai_funding.md
python -m src.agentic_rag.ingestion ingest --path docs/example_docs/doc2_anthropic_amazon.md
```

**Clean and Re-ingest:**
```bash
make ingest-clean
```

### Expected Data
- **Processing Times:** total_processing_time_ms, chunking_time_ms, embedding_time_ms, graph_extraction_time_ms
- **Result Counts:** chunks_created, entities_extracted, relationships_extracted, facts_extracted
- **File Metadata:** file_size_bytes, file_type (markdown, pdf, txt)
- **Success/Failure:** success=True/False, error_message if failed

---

## 5️⃣ SYSTEM METRICS (⚠️ NOT Currently Logging)

**What it tracks:** Periodic snapshots of database health, cache performance, and application metrics.

**Status:** Logger exists but no periodic collection task.

### Required Integration
Create a background task to collect metrics every 60 seconds:
- PostgreSQL connection pool stats
- Neo4j driver stats
- Redis cache hit rate
- Active sessions count

### How to Populate (Once Integrated)
System metrics would auto-populate via background task. No user action needed.

### Expected Data
- **Database:** pg_active_connections, pg_avg_query_time_ms, neo4j_total_queries
- **Cache:** cache_hit_rate, cache_size_mb
- **Application:** active_sessions, requests_per_minute, avg_response_time_ms

---

## 🎯 Quick Population Script

To quickly populate search and ingestion analytics:

```bash
# 1. Start the UI
make run-ui

# 2. In the UI chat, run these queries one by one:
# (Wait 2 seconds between each to see different timestamps)

What is OpenAI's funding history?
Who invested in Anthropic?
When did the AI boom start?
Tell me about Sam Altman
Compare OpenAI and Anthropic
What are the latest AI trends?
Show me Microsoft's AI investments
Explain transformer architecture
What happened in AI regulation recently?
How has AI funding changed over time?

# 3. In another terminal, ingest documents:
make ingest

# 4. Force analytics flush (wait 5 seconds or restart UI)
# Analytics batch every 5 seconds automatically

# 5. Refresh materialized views
psql $DATABASE_URL -c "SELECT refresh_analytics_views();"

# 6. Check the dashboard
# Navigate to Dashboard tab in UI
```

---

## 🔍 Verification Queries

After populating data, verify with these SQL queries:

```sql
-- Check search analytics count
SELECT COUNT(*), detected_intent
FROM search_analytics
GROUP BY detected_intent;

-- Check ingestion analytics
SELECT COUNT(*), success
FROM ingestion_analytics
GROUP BY success;

-- Check materialized views
SELECT * FROM intent_distribution_7d;
SELECT * FROM daily_search_summary ORDER BY date DESC LIMIT 7;
SELECT * FROM tool_performance_7d LIMIT 10;
```

---

## 📈 Dashboard Expected Results

After population, the dashboard should show:

### Search Metrics
- **Total Searches:** 10+
- **Average Latency:** ~100-500ms
- **Intent Distribution:** Mix of 5 intents
- **Cache Hits:** 0 initially, will increase with repeated queries

### Performance Metrics
- **P50 Latency:** ~150ms
- **P95 Latency:** ~400ms
- **P99 Latency:** ~600ms
- **Graph Boosts:** 30-50% of queries

### Trends Over Time
- **24h Window:** Hourly aggregation
- **7d Window:** Daily aggregation
- **Chart:** Line chart showing searches over time

### Tool Usage (Once Integrated)
- **Top Tools:** retrieve_relevant_documents, search_web
- **Success Rate:** 95%+
- **Avg Execution Time:** Varies by tool

### Agent Interactions (Once Integrated)
- **Total Interactions:** Matches searches
- **RAG Usage Rate:** 80%+
- **Feedback:** Thumbs up/down counts

---

## ⚠️ Current Limitations

1. **Tool Analytics:** Not integrated - tools don't log to analytics yet
2. **Agent Interactions:** Not integrated - UI/API doesn't log interactions yet
3. **System Metrics:** Not integrated - no background collection task
4. **Agent Interactions require session_id:** Need to pass session tracking through UI/API

---

## 🔧 Next Steps for Full Analytics

To complete analytics integration:

1. **Tool Logging:** Add `log_tool_usage()` calls to all tools in `src/tools/`
2. **Interaction Logging:** Add `log_interaction()` to UI handlers and API endpoints
3. **System Metrics:** Create background task in `connection_manager.py`
4. **Session Tracking:** Pass session UUIDs through UI and API

See `docs/analytics_system.md` for detailed implementation guide.
