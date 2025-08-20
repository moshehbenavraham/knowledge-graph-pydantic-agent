# AI Agent with Pydantic AI Framework

Production-ready AI agent implementation using Pydantic AI with comprehensive tooling for document retrieval, memory management, web search, image analysis, and code execution. Supports multiple LLM providers and embedding models with flexible deployment options.

## Core Features

### Agent Capabilities
- **Document Retrieval (RAG)**: Vector similarity search with 4-document context window using pgvector
- **Long-term Memory**: Persistent conversation memory via mem0 with PostgreSQL backend
- **Web Search**: Internet search via Brave API or self-hosted SearXNG
- **Image Analysis**: Vision model integration for image content analysis
- **Code Execution**: Sandboxed Python code execution with RestrictedPython
- **SQL Query Execution**: Read-only database queries with security validation

### Technical Stack
- **Framework**: Pydantic AI 0.0.53 with async support
- **Vector Database**: Supabase with pgvector extension
- **Memory Store**: mem0ai 0.1.102 with PostgreSQL backend
- **Embedding Models**: OpenAI text-embedding-3-small (1536d) or Ollama nomic-embed-text (768d)
- **LLM Support**: OpenAI GPT models, OpenRouter providers, Ollama local models
- **UI Framework**: Streamlit 1.44.1
- **Security**: RestrictedPython 8.0 for safe code execution
