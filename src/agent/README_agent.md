# Unified Agent Package

Central intelligence and tool orchestration for the Knowledge Graph Pydantic Agent system.

## Overview

This package contains the core unified agent implementation. Following the single-agent architecture principle, all AI capabilities are consolidated into one agent rather than multiple specialized sub-agents.

**Key Architecture Principle:** ONE unified agent handles all capabilities - no sub-agents.

## Files

| File | Purpose |
|------|---------|
| `unified_agent.py` | Main agent implementation with all tools and capabilities |
| `prompt.py` | System prompt templates and instruction sets |
| `__init__.py` | Package exports |

## Usage

```python
from src.agent.unified_agent import super_agent, UnifiedAgentDeps

# Create dependencies
deps = UnifiedAgentDeps(
    supabase_client=supabase,
    neo4j_connection=neo4j,
    # ... other dependencies
)

# Run the agent
result = await super_agent.run(
    user_prompt="Search for documents about Intel revenue",
    deps=deps,
)
```

## Agent Capabilities

The unified agent provides:

- **Intent Analysis**: Automatic query classification and routing
- **RAG Search**: Vector and graph-based document retrieval
- **Web Search**: Multi-provider web search (Jina, Brave, SearXNG)
- **SQL Queries**: Safe read-only database queries
- **Code Execution**: Sandboxed Python execution
- **Image Analysis**: Vision model integration

## Tool Registration

Tools are registered with the agent using decorators:

```python
@super_agent.tool
async def my_tool(
    ctx: RunContext[UnifiedAgentDeps],
    parameter: str
) -> dict:
    """Tool description for the agent."""
    deps = ctx.deps
    # Implementation
    return {"result": "value"}
```

## Dependencies

The `UnifiedAgentDeps` class provides dependency injection:

```python
@dataclass
class UnifiedAgentDeps:
    supabase_client: Client
    neo4j_connection: ConnectionManager
    embedding_model: EmbeddingModel
    search_service: HybridSearch
    # ... additional services
```

## Configuration

Agent behavior is controlled via centralized settings:

```python
from src.config import get_settings

settings = get_settings()
llm_provider = settings.llm_provider
llm_model = settings.llm_model
```

## Intent Routing

The agent uses 5-strategy intent routing:

| Intent | Description | Search Strategy |
|--------|-------------|-----------------|
| VECTOR_HEAVY | Semantic similarity queries | Vector search prioritized |
| GRAPH_HEAVY | Entity/relationship queries | Graph search prioritized |
| HYBRID | Mixed requirements | Parallel vector + graph |
| TEMPORAL | Time-based queries | Temporal metadata filtering |
| ENTITY_FOCUSED | Specific entity lookup | Entity-centric graph traversal |

Plus Phase 02 advanced intents:
- **MULTI_HOP**: Path traversal queries
- **TEMPORAL_TREND**: Time-series analysis
- **COMPARISON**: Cross-entity comparison

## Related Documentation

- [Architecture Overview](../../docs/3-architecture/index.md)
- [Tool Usage Patterns](../../docs/5-guides/tool-usage-patterns.md)
- [CLAUDE.md](../../CLAUDE.md) - Comprehensive project guide
