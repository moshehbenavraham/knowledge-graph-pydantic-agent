# 5-Minute Quick Start

Get Luminari AI Agent running in under 5 minutes with this streamlined setup.

## Prerequisites

- **Python 3.11+** installed
- **OpenAI API key** (get one at [platform.openai.com](https://platform.openai.com))
- **Supabase project** (create at [supabase.com](https://supabase.com))

## Step 1: Install Luminari

```bash
# Clone the repository
git clone <repository-url>
cd luminari-ai-agent

# Install with development dependencies
make setup
```

This installs the package in editable mode with all development tools.

## Step 2: Configure Environment

```bash
# Copy the example configuration
cp .env.example .env

# Edit with your credentials
nano .env
```

**Required settings in `.env`:**

```bash
# ===== CORE SERVICES =====
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key

# ===== LLM CONFIGURATION =====
LLM_PROVIDER=openai
LLM_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4o-mini

# ===== EMBEDDING CONFIGURATION =====
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=your_openai_api_key  # Can be same as LLM_API_KEY
EMBEDDING_MODEL=text-embedding-3-small
```

## Step 3: Initialize Database

```bash
# Run the database migration (one command sets up everything)
python -c "
import asyncio
from src.agentic_rag.storage.migrations.sql_runner import run_migration

async def init():
    await run_migration('src/agentic_rag/storage/migrations/sql/001_enhanced_schema.sql')

asyncio.run(init())
"
```

## Step 4: Start the Application

```bash
# Start the web interface
make run-ui
```

Open your browser to `http://localhost:8501` and start chatting with your AI agent!

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

## Optional: Add Knowledge Graph Features

For enhanced entity recognition and relationship mapping:

1. **Get Neo4j Aura** (free tier available at [neo4j.com/aura](https://neo4j.com/aura))

2. **Add to your `.env`:**
   ```bash
   NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password
   ```

3. **Initialize Neo4j:**
   ```bash
   make neo4j-init
   ```

## Optional: Enable Performance Features

For better performance with caching:

1. **Install Redis** (Docker recommended):
   ```bash
   docker run -d -p 6379:6379 redis:alpine
   ```

2. **Add to your `.env`:**
   ```bash
   REDIS_URL=redis://localhost:6379
   ENABLE_REDIS_CACHE=true
   ```

## Troubleshooting

If you encounter issues:

1. **Check the logs** - The application shows detailed error messages
2. **Verify credentials** - Ensure API keys are correct and have sufficient credits
3. **Test database connection** - Confirm Supabase is accessible
4. **See [Troubleshooting Guide](../9-troubleshooting/)** for common solutions

## Next Steps

Now that you have a working system:

- **[Configuration Guide](./configuration.md)** - Customize settings for your needs
- **[User Guides](../8-user-guides/)** - Learn about specific features
- **[Architecture Overview](../3-architecture/)** - Understand how it all works

## Getting Help

- **Documentation**: Browse all guides in the [docs](../) directory
- **Issues**: Report problems via GitHub Issues
- **Discussions**: Ask questions in GitHub Discussions

---

**🎉 Congratulations!** You now have a fully functional AI agent running locally.

**Time spent:** ~5 minutes | **Features available:** Chat, Search, Analytics Dashboard