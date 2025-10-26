# Agent Testing Guide

**System:** Luminari Agent with Agentic RAG (Lightweight deployment)
**URL:** http://localhost:8501
**Mode:** Simple UI (basic chat, no streaming)
**Documents:** 63 AI/Big Tech articles (810 chunks)

---

## 🚀 Quick Start - 3 Minute Test

Try these queries first to verify basic functionality:

1. **"What documents do you have?"** → Tests document listing
2. **"How much did OpenAI raise in their latest funding round?"** → Tests RAG retrieval
3. **"Who is Sam Altman?"** → Tests biographical queries
4. **"What's the latest news about AI?"** → Tests web search
5. **"How many documents are in the database?"** → Tests SQL queries

---

## 🎯 Testing Checklist

### ✅ Phase 1: Basic Functionality

**1.1 Simple Chat (No Tools)**
```
Query: "Hello! Can you introduce yourself?"
Expected: Agent responds with greeting, explains capabilities
```

**1.2 Basic Knowledge**
```
Query: "What's the capital of France?"
Expected: "Paris" - tests basic LLM functionality without tools
```

**1.3 Math/Logic**
```
Query: "What is 157 * 234?"
Expected: Correct calculation (36,738)
```

---

### 📚 Phase 2: Document Retrieval & RAG

**Current database:** 63 documents, 810 chunks (Big Tech & AI industry news/analysis)

**Document Topics Include:**
- OpenAI funding and strategy
- Sam Altman profile and leadership
- Apple's AI challenges
- NVIDIA's hardware dominance
- Cloud platform competition (AWS/Azure/GCP)
- Executive moves, acquisitions, regulatory landscape
- Investment trends, competitive analysis, future predictions

---

**2.1 List Available Documents**
```
Query: "What documents do you have available?"
Expected: Lists 63 documents about AI, big tech, funding, etc.
Tool used: list_documents
Result should show: Doc titles like "Sam Altman Profile", "Apple AI Struggles", etc.
```

**2.2 Simple Fact Retrieval**
```
Query: "How much did OpenAI raise in their latest funding round?"
Expected: "$6.6 billion at $157 billion valuation"
Tool used: retrieve_relevant_documents
Source: doc1_openai_funding.md
```

**2.3 Person/Company Specific Queries**
```
Query: "Who is Sam Altman and what is his background?"
Expected: Summary of his career (Y Combinator President, OpenAI CEO, Loopt founder)
Tool used: retrieve_relevant_documents
Source: doc7_sam_altman_profile.md

Query: "What challenges is Apple facing with AI?"
Expected: Siri delays, feature quality issues, architecture problems
Source: doc10_apple_ai_struggles.md
```

**2.4 Market Data Queries**
```
Query: "What is NVIDIA's market share in AI accelerators?"
Expected: "80-95% market share" with revenue details
Tool used: retrieve_relevant_documents
Source: doc8_nvidia_dominance.md

Query: "Compare the market positions of AWS, Azure, and Google Cloud in AI"
Expected: Market share percentages and competitive positioning
Source: doc17_cloud_wars.md
```

**2.5 Complex Multi-Document Synthesis**
```
Query: "Compare OpenAI's strategy with Apple's approach to AI development"
Expected: Contrasts OpenAI's aggressive scaling with Apple's privacy-first struggles
Tool used: retrieve_relevant_documents (multiple sources)
Sources: doc1_openai_funding.md, doc10_apple_ai_struggles.md

Query: "Who are the major investors in AI companies mentioned in the documents?"
Expected: Microsoft, NVIDIA, SoftBank, Thrive Capital, Amazon, etc.
Tool used: retrieve_relevant_documents (synthesized from multiple docs)
```

**2.6 Temporal/Timeline Queries**
```
Query: "What happened with Sam Altman in November 2023?"
Expected: Board crisis, firing, employee revolt, reinstatement timeline
Tool used: retrieve_relevant_documents
Source: doc7_sam_altman_profile.md

Query: "When is Apple's improved Siri expected to launch?"
Expected: "2026 due to complete architectural redesign"
Source: doc10_apple_ai_struggles.md
```

**2.7 Specific Metrics/Numbers**
```
Query: "What is OpenAI's annual recurring revenue?"
Expected: "$3.6 billion ARR as of September 2024, projected $11.6B for 2025"
Source: doc1_openai_funding.md

Query: "How much did Microsoft spend on NVIDIA chips in 2024?"
Expected: "$31 billion for 485,000 Hopper chips"
Source: doc8_nvidia_dominance.md
```

---

### 🌐 Phase 3: Web Search

**Provider:** Jina.ai (configured)

**3.1 Current Events**
```
Query: "What are the latest news about OpenAI?"
Expected: Recent web results via Jina search
Tool used: web_search_tool
```

**3.2 Fact Checking**
```
Query: "Who is the current CEO of Microsoft?"
Expected: Web search returns "Satya Nadella"
```

**3.3 Combined RAG + Web**
```
Query: "What do my documents say about AI, and what's the latest news on this topic?"
Expected: Uses both retrieve_documents AND web_search
```

---

### 🗄️ Phase 4: SQL Queries

**Database:** Supabase PostgreSQL (documents, chunks tables)

**4.1 Simple Query**
```
Query: "How many documents are in the database?"
Expected: SQL query to count documents table
Tool used: sql_query_tool
Result: Should return 63 (or current count)
```

**4.2 Aggregation**
```
Query: "Show me the top 5 most recent documents"
Expected: SQL query with ORDER BY created_at DESC LIMIT 5
```

**4.3 Complex Analysis**
```
Query: "What's the average chunk size in the database?"
Expected: SQL aggregation on chunks table
```

**⚠️ Security Test**
```
Query: "DROP TABLE documents" or "DELETE FROM documents"
Expected: Should REJECT - read-only queries enforced
```

---

### 🖼️ Phase 5: Image Analysis (Optional)

**Note:** Requires image URL or upload capability

**5.1 Image Description**
```
Query: "Describe this image: [URL to an image]"
Expected: Vision model analyzes and describes image
Tool used: analyze_image
```

---

### 🧠 Phase 6: Memory & Context

**6.1 Conversation Continuity**
```
Query 1: "My favorite color is blue"
Query 2: "What's my favorite color?"
Expected: Remembers from conversation context
```

**6.2 Multi-turn Reasoning**
```
Query 1: "Find documents about Python programming"
Query 2: "Summarize the main points from those documents"
Query 3: "Can you create a simple example based on what you found?"
Expected: Maintains context across turns
```

---

### ⚙️ Phase 7: Tool Combinations

**7.1 RAG + Web Search**
```
Query: "What do my documents say about Apple's AI struggles, and what's Apple announcing today?"
Expected: retrieve_documents (historical from docs) + web_search (current news)
Verify: Distinguishes between doc info and web results

Query: "Compare OpenAI's funding in my documents to their latest news"
Expected: RAG retrieval ($6.6B) + current web search for recent announcements
```

**7.2 SQL + RAG**
```
Query: "Find the most recent document and summarize what it's about"
Expected: sql_query to find latest document, then retrieve/summarize its content

Query: "How many documents mention Sam Altman, and what do they say about him?"
Expected: SQL count + RAG retrieval of Altman-related content
```

---

### 🚨 Phase 8: Error Handling

**8.1 Nonexistent Document**
```
Query: "Show me the document titled 'ThisDoesNotExist'"
Expected: Graceful error message, suggests alternatives
```

**8.2 Invalid SQL**
```
Query: "Run this query: SELECT * FROM nonexistent_table"
Expected: SQL error handled gracefully
```

**8.3 Rate Limiting**
```
Query: Send 10+ queries rapidly
Expected: System handles load, may queue or rate limit
```

---

## 📊 What to Monitor

### In the UI
- ✅ Response time (< 5 seconds for simple queries)
- ✅ Tool calls shown (in standard/advanced UI modes)
- ✅ Answers are accurate and relevant
- ✅ Citations when using RAG
- ✅ Error messages are clear

### In WSL2 Terminal (where Streamlit is running)
Watch for:
```bash
# Check the terminal running: make run-ui-simple
# Look for:
- Tool execution logs
- Database query logs
- API call traces
- Error stack traces (if any)
```

### Check Logs Programmatically
```bash
# View recent logs
tail -f ~/.cache/streamlit/logs/streamlit.log

# Or check Python logs if structured logging enabled
grep ERROR ~/.cache/streamlit/logs/streamlit.log
```

---

## 🔍 Verification Commands

### Check Database State
```bash
# Activate environment
source .venv/bin/activate

# Run quick DB check
python -c "
from src.agentic_rag.storage.connection_manager import ConnectionManager
cm = ConnectionManager()
with cm.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM documents')
        print(f'Documents: {cur.fetchone()[0]}')
        cur.execute('SELECT COUNT(*) FROM chunks')
        print(f'Chunks: {cur.fetchone()[0]}')
"
```

### Check API Keys
```bash
# Verify environment variables loaded
source .venv/bin/activate
python -c "
from src.config import get_settings
s = get_settings()
print(f'LLM Provider: {s.llm_provider}')
print(f'LLM Model: {s.llm_model}')
print(f'Embedding Provider: {s.embedding_provider}')
print(f'Web Search: {s.web_search_provider}')
print(f'OpenAI Key: {s.llm_api_key[:20]}...')
"
```

---

## 🎯 Success Criteria

### ✅ Basic Deployment
- [ ] UI loads without errors
- [ ] Agent responds to simple queries
- [ ] LLM integration working (OpenAI GPT-5-mini)

### ✅ RAG Functionality
- [ ] Can list documents
- [ ] Retrieves relevant chunks for queries
- [ ] Answers based on ingested content
- [ ] Provides citations/sources

### ✅ Tool Integration
- [ ] Web search returns current results
- [ ] SQL queries execute safely (read-only)
- [ ] Tools called automatically when needed
- [ ] Multiple tools can be used in one query

### ✅ Production Readiness
- [ ] No crashes on edge cases
- [ ] Graceful error handling
- [ ] Reasonable response times (< 10s)
- [ ] Memory usage stable (< 2GB)

---

## 🐛 Common Issues & Fixes

### "No documents found"
```bash
# Re-run ingestion
make ingest
```

### "OpenAI API Error"
```bash
# Check API key
echo $LLM_API_KEY
# Verify in .env file
grep LLM_API_KEY .env
```

### "Database connection failed"
```bash
# Test connection
curl -I https://hokdgtbedrsenvldxbyx.supabase.co
# Check DATABASE_URL
grep DATABASE_URL .env
```

### UI Not Responding
```bash
# Restart UI
pkill -f streamlit
make run-ui-simple
```

---

## 📈 Advanced Testing (Optional)

### Load Testing
```bash
# Install locust
pip install locust

# Run load tests
make load-test
```

### Integration Tests
```bash
# Run full test suite
pytest tests/ -v

# Run RAG-specific tests
pytest tests/rag_pipeline/ -v

# Run Phase 1 infrastructure tests (requires real databases)
unset TESTING  # Use real environment, not test overrides
pytest tests/test_phase1_infrastructure.py -v --no-cov

# Run integration tests only
pytest tests/integration/ -v
```

### Event Loop Configuration (IMPORTANT for async tests)

**Issue Resolved (2025-10-13)**: If you encounter `RuntimeError: Task attached to a different loop` errors when running async tests, the following configuration is required:

**Required Configuration:**

1. **`pyproject.toml`** - Add these settings:
   ```toml
   [tool.pytest.ini_options]
   asyncio_default_fixture_loop_scope = "module"
   asyncio_mode = "auto"
   ```

2. **Test files with async database operations** - Use module-scoped loop:
   ```python
   @pytest.mark.asyncio(loop_scope="module")
   class TestDatabaseOperations:
       async def test_something(self):
           # Your test here
   ```

3. **`conftest.py`** - Module-scoped event loop fixture:
   ```python
   @pytest.fixture(scope="module")
   def event_loop():
       loop = asyncio.new_event_loop()
       asyncio.set_event_loop(loop)
       yield loop
       loop.close()
   ```

**Why This Matters**: asyncpg connection pools bind to the event loop at creation time. If tests run in different loops than where the pool was created, you'll get "Task attached to a different loop" errors. Module-scoped loops ensure the pool and tests share the same loop.

### Performance Profiling
```bash
# Profile API endpoints
make profile-api
```

---

## 🎓 Example Test Session

**Complete workflow to verify everything (10 minutes):**

```
1. "Hello, what can you help me with?"
   → Verifies: Basic LLM response
   → Expected: Greeting + capabilities overview

2. "What documents do you have?"
   → Verifies: RAG list_documents tool
   → Expected: List of 63 documents about AI/tech

3. "How much did OpenAI raise in their latest funding round?"
   → Verifies: RAG semantic search (factual retrieval)
   → Expected: "$6.6 billion at $157 billion valuation"

4. "Who is Sam Altman?"
   → Verifies: RAG biographical queries
   → Expected: OpenAI CEO, Y Combinator background, etc.

5. "How many documents are in the database?"
   → Verifies: SQL query tool
   → Expected: 63 documents query result

6. "What's the latest news about OpenAI today?"
   → Verifies: Web search (Jina.ai)
   → Expected: Current news results (not from docs)

7. "Compare what my documents say about Apple's AI struggles with current news"
   → Verifies: Multi-tool (RAG + Web Search)
   → Expected: Doc info + current web results combined

8. "What challenges did we discuss about Apple?"
   → Verifies: Conversation memory
   → Expected: References earlier Apple AI discussion

9. "Compare NVIDIA's market position with what Sam Altman says about AI infrastructure"
   → Verifies: Multi-document RAG synthesis
   → Expected: Combines info from multiple docs

10. "Summarize our conversation"
    → Verifies: Context tracking across queries
    → Expected: Recap of all topics discussed
```

**Expected time:** 10-15 minutes for comprehensive test

---

## 📝 Notes

- **Simple UI Mode:** No streaming, basic chat only
- **Standard UI Mode:** Run `make run-ui` for streaming + tool visibility
- **Advanced UI Mode:** Run `make run-ui-advanced MODE=advanced` for memory + MCP
- **API Mode:** Run `make run-api` to test via REST API (port 8058)

**Good luck testing! 🚀**
