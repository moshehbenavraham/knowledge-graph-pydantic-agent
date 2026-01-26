# Getting Started

Welcome to Knowledge Graph Pydantic Agent! This section provides everything you need to get up and running quickly.

## Quick Start Paths

Choose the path that best fits your needs:

### 🚀 5-Minute Quick Start
Perfect for trying out the system immediately.

**[Quick Start Guide](./quick-start.md)** → *Start here if you want to try the system right away*

### 🏗️ Complete Installation
For production deployments and full feature access.

**[Installation Guide](./installation.md)** → *Complete setup for all features*

### ⚙️ Configuration First
For customizing the system to your specific requirements.

**[Configuration Guide](./configuration.md)** → *Configure before running*

## What You'll Need

### Required
- **Python 3.11+** (3.12 recommended)
- **API Access** for at least one LLM provider:
  - OpenAI API key (recommended)
  - Anthropic Claude API key
  - Ollama for local models
- **Supabase Project** with pgvector enabled

### Recommended
- **Neo4j Aura** for knowledge graph features
- **Redis** for performance optimization
- **Docker** for easy deployment

## Installation Overview

```bash
# 1. Clone and setup
git clone <repository-url>
cd knowledge-graph-pydantic-agent
make setup

# 2. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 3. Initialize databases
# Run database migrations and setup

# 4. Start the application
make run-ui  # Web interface
# OR
make run-api  # API server
```

## Next Steps After Installation

1. **[First Run Guide](./first-run.md)** - Your first interaction with the agent
2. **[Configuration Reference](../4-configuration/)** - Customize for your needs
3. **[User Guides](../5-guides/)** - Learn how to use specific features

## Getting Help

- **[Troubleshooting Guide](../10-troubleshooting/)** - Common issues and solutions

---

**Ready to begin?** → **[Quick Start Guide](./quick-start.md)**
