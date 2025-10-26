# 5-Minute Quick Start

Get Luminari Agent running in under 5 minutes.

## Prerequisites

- **Python 3.11+**
- **OpenAI API key** ([platform.openai.com](https://platform.openai.com))
- **Supabase project** ([supabase.com](https://supabase.com))

## Step 1: Install Luminari Agent

```bash
git clone <repository-url>
cd base_agent
make setup
```

## Step 2: Configure Environment

```bash
cp .env.example .env
nano .env
```

**Required settings:**

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
LLM_PROVIDER=openai
LLM_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4o-mini
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=your_openai_api_key
EMBEDDING_MODEL=text-embedding-3-small
```

## Step 3: Initialize Database

```bash
python -c "
import asyncio
from src.agentic_rag.storage.migrations.sql_runner import run_migration

async def init():
    await run_migration('src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql')

asyncio.run(init())
"
```

## Step 4: Start Application

```bash
make run-ui
```

Access at `http://localhost:8501`

## What You Can Do Now

### 💬 Chat Interface
- Ask questions in natural language
- Upload documents for analysis
- Get responses with source citations

### 🔍 Basic Search
- Vector similarity search across documents
- Web search integration
- SQL query generation and execution

### 📊 Analytics Dashboard
- View search patterns and performance
- Explore the knowledge graph visualization
- Monitor system health

## Optional Enhancements

### Knowledge Graph Features
1. Get [Neo4j Aura](https://neo4j.com/aura) (free tier)
2. Add to `.env`:
   ```bash
   NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password
   ```
3. Run: `make neo4j-init`

### Performance Caching
1. Install Redis: `docker run -d -p 6379:6379 redis:alpine`
2. Add to `.env`:
   ```bash
   REDIS_URL=redis://localhost:6379
   ENABLE_REDIS_CACHE=true
   ```

## Troubleshooting

1. **Check logs** for error messages
2. **Verify credentials** - API keys and Supabase access
3. **Test database connection**
4. **See [Troubleshooting Guide](../10-troubleshooting/)**

## Next Steps

- **[Configuration Guide](./configuration.md)** - Customize settings
- **[User Guides](../5-guides/)** - Learn features
- **[Architecture Overview](../3-architecture/)** - System design

## Getting Help

- Browse [docs](../) directory
- Report issues via GitHub Issues
- Ask questions in GitHub Discussions

---

**🎉 Congratulations!** You now have a fully functional AI agent running locally.

**Time spent:** ~5 minutes | **Features available:** Chat, Search, Analytics Dashboard
