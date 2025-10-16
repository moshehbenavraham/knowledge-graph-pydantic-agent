# Base Agent - Overview

## What is Base Agent?

Enterprise-grade unified AI platform built on [Pydantic AI](https://ai.pydantic.dev/). Consolidates multiple AI capabilities into a single intelligent agent with intelligent routing, parallel execution, and enterprise-grade resilience.

## Core Philosophy

**One Agent, All Tools** - Single agent (`src/agent/unified_agent.py`) that:
- Routes queries intelligently to optimal tools
- Executes tools in parallel for comprehensive results
- Maintains context via memory systems and knowledge graphs
- Scales for production workloads with monitoring and resilience

## Key Differentiators

### Unified Architecture
Single agent intelligently orchestrates all tools based on query intent and context.

### Agentic Graph RAG
Combines vector search (PostgreSQL/Supabase) with knowledge graph (Neo4j + Graphiti) for superior accuracy and understanding.

### Production-Ready
Circuit breakers, structured logging, Prometheus metrics, OpenTelemetry tracing, comprehensive error handling.

### Multiple Interfaces
Access via Streamlit UI (interactive dashboard), FastAPI (REST + WebSocket), and CLI utilities.

## Target Use Cases

### Enterprise Knowledge Management
- Intelligent document search across large collections
- Knowledge graph navigation with entity relationships
- Automated Q&A with contextual evidence

### Data Analysis & Automation
- Natural language to SQL conversion
- Safe Python code execution for data processing
- Automated web research and content analysis

### Conversational AI
- Persistent conversation context across sessions
- Multi-turn dialogues with personalization

## Technology Stack

### Core Framework
- **Pydantic AI 0.1.2+** - Agent framework with type-safe tooling
- **Python 3.11+** - Modern Python with full async architecture

### AI & ML Services
- **OpenAI/Anthropic APIs** - Primary LLM providers
- **Local Models** - Ollama for private deployments
- **Multi-Provider Embeddings** - OpenAI and local models
- **Vision Models** - Image analysis capabilities

### Data Storage
- **PostgreSQL/Supabase** - Vector storage with pgvector
- **Neo4j Aura** - Knowledge graph with Graphiti
- **Redis** - Caching and performance optimization
- **mem0** - Long-term memory management

### Infrastructure & Operations
- **FastAPI** - Production REST API with streaming
- **Streamlit** - Interactive web interface
- **Docker** - Containerization and deployment
- **Prometheus/Grafana** - Monitoring and observability

## Getting Started

### Quick Start (5 minutes)
```bash
git clone <repository-url>
cd base_agent
make setup
cp .env.example .env
# Edit .env with your credentials
make run-ui
```

### Production Deployment
```bash
pip install -e .[dev,rag]  # Full installation
# Configure production settings
# Deploy with Docker/Kubernetes
```

### Development Setup
```bash
make setup    # Install environment
make check    # Run quality checks
make run-ui   # Start development UI
```

## Next Steps

- **[Getting Started Guide](../2-getting-started/)** - Complete setup
- **[Architecture Overview](../3-architecture/)** - Technical design
- **[Configuration Reference](../4-configuration/)** - All options

---

**Version**: 1.1.0 | **API Version**: 0.8.0 | **License**: MIT
