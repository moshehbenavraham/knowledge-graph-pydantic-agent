# Luminari AI Agent - Overview

## What is Luminari AI Agent?

Luminari AI Agent is an enterprise-grade unified artificial intelligence platform that combines multiple AI capabilities into a single, intelligent system. Built on [Pydantic AI](https://ai.pydantic.dev/), it provides a comprehensive suite of tools and services for intelligent automation, data processing, and decision support.

## Core Philosophy

**One Agent, All Tools** - Luminari consolidates traditionally separate AI capabilities into a single, intelligent agent that can:

- **Understand Intent**: Automatically route queries to the most appropriate tools
- **Execute in Parallel**: Run multiple tools simultaneously for comprehensive results
- **Learn and Adapt**: Maintain context through memory systems and knowledge graphs
- **Scale Enterprise**: Handle production workloads with monitoring and resilience features

## Key Differentiators

### Unified Architecture
Unlike fragmented AI solutions, Luminari provides a single agent (`src/agent/unified_agent.py`) that intelligently orchestrates all available tools based on query intent and context.

### Agentic Graph RAG
Combines vector search (PostgreSQL/Supabase) with knowledge graph capabilities (Neo4j + Graphiti) for superior retrieval accuracy and contextual understanding.

### Production-Ready
Enterprise features including circuit breakers, structured logging, Prometheus metrics, OpenTelemetry tracing, and comprehensive error handling.

### Multiple Interfaces
Access the same agent through:
- **Streamlit UI** - Interactive web interface with analytics dashboard
- **FastAPI** - REST API with WebSocket streaming support
- **CLI** - Command-line utilities and scripts

## Target Use Cases

### Enterprise Knowledge Management
- **Intelligent Document Search**: Find relevant information across vast document collections
- **Knowledge Graph Navigation**: Explore entity relationships and temporal facts
- **Automated Q&A**: Answer complex questions with context and evidence

### Data Analysis & Automation
- **SQL Query Generation**: Natural language to SQL conversion
- **Code Execution**: Safe Python code execution for data processing
- **Web Research**: Automated web search and content analysis

### Conversational AI
- **Long-term Memory**: Persistent conversation context
- **Multi-turn Dialogues**: Maintain context across sessions
- **Personalized Responses**: Adapt to user preferences and history

## Technology Stack

### Core Framework
- **Pydantic AI 0.1.2+** - Agent framework with type-safe tooling
- **Python 3.11+** - Modern Python with full type hints
- **Async/Await** - Full asynchronous architecture

### AI & ML Services
- **OpenAI/Anthropic APIs** - Primary LLM providers
- **Local Models** - Ollama integration for private deployments
- **Embedding Models** - Multiple provider support (OpenAI, local)
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

Choose your path based on your needs:

### Quick Start (5 minutes)
```bash
git clone <repository-url>
cd luminari-ai-agent
make setup
cp .env.example .env
# Edit .env with your credentials
make run-ui
```

### Production Deployment
```bash
# Full installation with all features
pip install -e .[dev,rag]
# Configure production settings
# Deploy with Docker/Kubernetes
```

### Development Setup
```bash
make setup          # Install development environment
make check          # Run all quality checks
make run-ui         # Start development UI
```

## Next Steps

- **[Getting Started Guide](../2-getting-started/)** - Complete setup instructions
- **[Architecture Overview](../3-architecture/)** - Technical system design
- **[Configuration Reference](../4-configuration/)** - All configuration options
- **[User Guides](../8-user-guides/)** - How to use specific features

---

**Version**: 1.0.2 | **API Version**: 0.8.0 | **License**: MIT