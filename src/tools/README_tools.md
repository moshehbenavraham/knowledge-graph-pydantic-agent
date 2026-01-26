# Tools Package

Specialized capabilities and integrations for the Knowledge Graph Pydantic Agent.

## Overview

This package contains all tools available to the unified agent. Each tool is an async function that follows dependency injection patterns and provides specific capabilities.

## Available Tools

| Tool | File | Description |
|------|------|-------------|
| RAG Tools | `rag.py` | Document retrieval and similarity search |
| SQL Query | `sql_query.py` | Read-only database queries via Supabase RPC |
| Web Search | `web_search.py` | Multi-provider web search integration |
| Code Execution | `code_execution.py` | Sandboxed Python execution |
| Image Analysis | `image_analysis.py` | Vision model integration (OCR, object detection) |

## Tool Development Rules

All tools must follow these patterns:

1. **Async Functions**: All tools must be async
2. **Dependency Injection**: Use `RunContext[UnifiedAgentDeps]` for dependencies
3. **Error Handling**: Comprehensive error handling with informative messages
4. **Security Validation**: Validate all inputs (especially SQL/code)
5. **Clear Docstrings**: Include usage examples

## Tool Structure

```python
from pydantic_ai import RunContext
from src.agent.unified_agent import UnifiedAgentDeps

async def tool_name(
    ctx: RunContext[UnifiedAgentDeps],
    parameter: str,
    optional_param: int = 10
) -> dict:
    """
    Clear description of what this tool does.

    Args:
        ctx: Agent runtime context with dependencies
        parameter: Description of parameter
        optional_param: Optional parameter with default

    Returns:
        Result dictionary with structured data

    Example:
        result = await tool_name(ctx, "query", optional_param=20)
    """
    deps = ctx.deps

    # Input validation
    if not parameter:
        return {"error": "Parameter is required"}

    # Implementation with proper error handling
    try:
        result = await deps.some_service.execute(parameter)
        return {"success": True, "data": result}
    except Exception as e:
        return {"error": str(e)}
```

## RAG Tools (rag.py)

Primary document retrieval tools:

```python
# Retrieve relevant document chunks
result = await retrieve_documents(ctx, query="Intel revenue 2023", limit=10)

# List all available documents
docs = await list_all_documents(ctx)

# Get full document content
content = await get_full_document(ctx, document_id="doc-123")

# Smart search with intent routing
result = await smart_search(ctx, query="Compare Intel vs AMD revenue")
```

### Smart Search Intent Routing

The `smart_search` tool automatically routes to the appropriate search strategy:

| Query Type | Routed To |
|------------|-----------|
| Semantic queries | Vector search |
| Entity queries | Graph search |
| Temporal queries | Temporal filtering |
| Multi-hop queries | Graph traversal |
| Comparison queries | Entity comparison |

## SQL Query Tool (sql_query.py)

Read-only SQL queries via Supabase RPC:

```python
result = await sql_query(
    ctx,
    query="SELECT * FROM documents WHERE company = 'Intel' LIMIT 10"
)
```

**Security Features:**
- Read-only queries only (SELECT)
- Parameterized statements
- Automatic semicolon stripping (Supabase RPC requirement)
- Query validation

## Web Search Tool (web_search.py)

Multi-provider web search with fallback:

```python
result = await web_search(ctx, query="latest AI news", max_results=5)
```

**Provider Priority:**
1. Jina (primary)
2. Brave Search (fallback)
3. SearXNG (secondary fallback)

## Code Execution Tool (code_execution.py)

Sandboxed Python execution:

```python
result = await execute_code(
    ctx,
    code="print(sum([1, 2, 3, 4, 5]))"
)
```

**Security Features:**
- RestrictedPython sandbox
- Whitelisted modules only
- Execution timeout
- Resource limits

## Image Analysis Tool (image_analysis.py)

Vision model integration:

```python
result = await analyze_image(
    ctx,
    image_path="/path/to/image.png",
    analysis_type="ocr"  # ocr, objects, scene, describe
)
```

**Capabilities:**
- OCR (text extraction)
- Object detection
- Scene analysis
- General description

Uses gpt-4o-mini for analysis.

## Adding New Tools

1. Create tool function in appropriate file (or new file)
2. Register with agent in `unified_agent.py`:

```python
from src.tools.my_tool import my_new_tool

super_agent.tool(my_new_tool)
```

3. Add tests in `tests/tools/`
4. Update this README

## Testing

```bash
# Run tool tests
pytest tests/tools/ -v

# Run specific tool tests
pytest tests/tools/test_rag_tools.py -v
pytest tests/tools/test_sql_query.py -v
```

## Related Documentation

- [Tool Usage Patterns](../../docs/5-guides/tool-usage-patterns.md)
- [Security Guide](../../docs/9-security/security.md)
- [CLAUDE.md](../../CLAUDE.md) - Tool development rules
