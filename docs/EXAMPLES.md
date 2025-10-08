# Usage Examples - Unified Super Agent

This document provides comprehensive examples of how to use the **Unified Super Agent** - our new all-in-one AI assistant that combines every capability into a single, powerful implementation.

## Table of Contents

- [Quick Start](#quick-start)
- [Basic Usage](#basic-usage)
- [Tool-Specific Examples](#tool-specific-examples)
- [Advanced Workflows](#advanced-workflows)
- [Search Strategies](#search-strategies)
- [Multi-Tool Orchestration](#multi-tool-orchestration)
- [Migration from Legacy Agents](#migration-from-legacy-agents)

## Quick Start

```python
from src.agent import super_agent, UnifiedAgentDeps, run_unified_agent
from src.clients import get_supabase_client, get_embedding_client
from httpx import AsyncClient

# Simplest usage
result = await run_unified_agent(
    query="What documents are available?",
    session_id="quick_start"
)
print(result["response"])
```

## Basic Usage

### Simple Chat Interface

```python
import asyncio
from src.agent import run_unified_agent

async def chat():
    while True:
        query = input("\nYou: ")
        if query.lower() == 'exit':
            break

        result = await run_unified_agent(
            query=query,
            session_id="chat_session",
            memories="User prefers concise answers"
        )

        print(f"\nAgent: {result['response']}")

asyncio.run(chat())
```

### With Full Configuration

```python
from src.agent import super_agent, UnifiedAgentDeps
import os

# Create custom dependencies
deps = UnifiedAgentDeps(
    supabase=get_supabase_client(),
    embedding_client=get_embedding_client(),
    http_client=AsyncClient(),
    brave_api_key=os.getenv("BRAVE_API_KEY"),
    jina_api_key=os.getenv("JINA_API_KEY"),
    memories="User is a data scientist interested in ML",
    session_id="advanced_session",
    search_config={
        "use_vector": True,
        "use_graph": True,
        "confidence_threshold": 0.85,
        "max_results": 30
    }
)

result = await super_agent.run(
    "Analyze the latest trends in machine learning",
    deps=deps
)
```

## Tool-Specific Examples

### 1. Smart Search (Intelligent Routing)

```python
# The agent automatically determines the best search strategy

# Relationship query → Graph search
result = await run_unified_agent(
    "What is the relationship between OpenAI and Microsoft?"
)

# Similarity query → Vector search
result = await run_unified_agent(
    "Find documents similar to neural networks"
)

# Complex query → Hybrid search
result = await run_unified_agent(
    "Explain quantum computing with examples and timeline"
)
```

### 2. Web Search

```python
# Real-time information from the internet
result = await run_unified_agent(
    "What are the latest AI developments in December 2024?"
)

# With specific provider preference
deps = UnifiedAgentDeps(
    web_search_provider="jina",  # Use Jina.ai for clean content
    jina_api_key="your_key"
)
result = await super_agent.run(
    "Get the latest news about SpaceX",
    deps=deps
)
```

### 3. SQL Query Execution

```python
# First, list available datasets
result = await run_unified_agent(
    "List all available documents and datasets"
)

# Then query specific data
result = await run_unified_agent(
    """Execute SQL:
    SELECT
        row_data->>'category' as category,
        COUNT(*) as count,
        AVG((row_data->>'price')::numeric) as avg_price
    FROM document_rows
    WHERE dataset_id = 'sales_data_2024'
    GROUP BY category
    ORDER BY count DESC
    """
)
```

### 4. Code Execution

```python
# Simple calculations
result = await run_unified_agent(
    "Write and execute Python code to calculate factorial of 10"
)

# Complex algorithms
result = await run_unified_agent(
    """Write and execute Python code to:
    1. Generate first 20 Fibonacci numbers
    2. Calculate their mean and median
    3. Create a simple ASCII chart
    """
)

# Data processing
result = await run_unified_agent(
    """Execute this Python code:
    import json
    data = [1, 2, 3, 4, 5]
    result = {
        'sum': sum(data),
        'mean': sum(data) / len(data),
        'squared': [x**2 for x in data]
    }
    print(json.dumps(result, indent=2))
    """
)
```

### 5. Image Analysis

```python
# First, list available images
result = await run_unified_agent(
    "Show me all image files in the knowledge base"
)

# Analyze specific image
result = await run_unified_agent(
    "Analyze the image 'architecture_diagram.png' and describe what it shows"
)

# Extract specific information
result = await run_unified_agent(
    "Look at 'chart.png' and extract all the data points and labels"
)
```

### 6. Document Management

```python
# Browse documents
result = await run_unified_agent(
    "List all PDF documents about machine learning"
)

# Retrieve full document
result = await run_unified_agent(
    "Get the complete content of 'ml_fundamentals.pdf'"
)

# Search within documents
result = await run_unified_agent(
    "Search for information about transformers in AI papers"
)
```

## Advanced Workflows

### Research Assistant

```python
async def research_topic(topic: str):
    """Comprehensive research on a topic."""

    # Step 1: Initial search
    overview = await run_unified_agent(
        f"Provide an overview of {topic}",
        session_id="research"
    )

    # Step 2: Find relevant documents
    docs = await run_unified_agent(
        f"Find all documents related to {topic}",
        session_id="research"
    )

    # Step 3: Get latest information
    latest = await run_unified_agent(
        f"Search the web for latest developments in {topic}",
        session_id="research"
    )

    # Step 4: Synthesize
    synthesis = await run_unified_agent(
        f"Based on our research, create a comprehensive summary of {topic}",
        session_id="research"
    )

    return {
        "overview": overview["response"],
        "documents": docs["response"],
        "latest_info": latest["response"],
        "synthesis": synthesis["response"]
    }

# Use it
research = await research_topic("quantum computing")
```

### Data Analysis Pipeline

```python
async def analyze_dataset(dataset_id: str):
    """Complete data analysis workflow."""

    # Step 1: Explore structure
    schema = await run_unified_agent(
        f"Show me the schema and sample data from {dataset_id}"
    )

    # Step 2: Statistical analysis
    stats = await run_unified_agent(
        f"""Execute SQL to get statistics:
        SELECT
            COUNT(*) as total_rows,
            COUNT(DISTINCT row_data->>'id') as unique_ids
        FROM document_rows
        WHERE dataset_id = '{dataset_id}'
        """
    )

    # Step 3: Visualization code
    viz = await run_unified_agent(
        f"""Write and execute Python code to create
        a simple histogram of the data distribution for {dataset_id}"""
    )

    # Step 4: Insights
    insights = await run_unified_agent(
        f"Based on the analysis, what insights can you provide about {dataset_id}?"
    )

    return {
        "schema": schema["response"],
        "statistics": stats["response"],
        "visualization": viz["response"],
        "insights": insights["response"]
    }
```

## Search Strategies

### Comprehensive Search

```python
# Execute all search strategies in parallel
result = await run_unified_agent(
    "Do a comprehensive search about artificial general intelligence"
)

# With custom configuration
deps = UnifiedAgentDeps(
    search_config={
        "use_vector": True,
        "use_graph": True,
        "max_results": 50
    }
)
result = await super_agent.run(
    "Find everything about neural architecture search",
    deps=deps
)
```

### Iterative Search

```python
# Multi-step exploration for complex queries
result = await run_unified_agent(
    """Investigate the evolution of transformer models:
    1. Start with the original paper
    2. Find key improvements and variants
    3. Identify current state-of-the-art
    4. Predict future directions
    """
)
```

## Multi-Tool Orchestration

### Complex Multi-Tool Query

```python
result = await run_unified_agent(
    """Help me understand BERT:
    1. Search documents for BERT architecture
    2. Find the latest BERT variants on the web
    3. Write Python code to show how attention works
    4. If there are any diagrams, analyze them
    5. Create a summary with all findings
    """
)
```

### Automated Report Generation

```python
async def generate_report(company: str):
    """Generate comprehensive company report."""

    report = []

    # Gather information
    tasks = [
        ("Overview", f"Provide overview of {company}"),
        ("Documents", f"Find all documents mentioning {company}"),
        ("Web News", f"Get latest news about {company} from the web"),
        ("Relationships", f"What companies is {company} connected to?"),
        ("Data", f"Show any data or statistics about {company}")
    ]

    for section, query in tasks:
        result = await run_unified_agent(query)
        report.append(f"## {section}\n{result['response']}\n")

    # Generate final report
    final = await run_unified_agent(
        f"Create an executive summary based on: {' '.join(report)}"
    )

    return "\n".join(report) + f"\n## Executive Summary\n{final['response']}"

# Generate report
report = await generate_report("OpenAI")
print(report)
```

## No Migration Needed!

### Clean Architecture - One Agent Only

The project now has **ONE unified agent** - no migration needed because the old agents have been removed!

**The Only Way:**
```python
from src.agent import super_agent, UnifiedAgentDeps, run_unified_agent

# Option 1: Simple usage
result = await run_unified_agent(
    query="Your question here",
    session_id="my_session"
)

# Option 2: With dependencies
deps = UnifiedAgentDeps(
    supabase=client,
    embedding_client=embed,
    http_client=http,
    memories="User context"
)
result = await super_agent.run(query, deps=deps)
```

### Why No Migration?

- ✅ Legacy agents have been **DELETED**
- ✅ Only `unified_agent.py` remains
- ✅ All code updated to use the unified agent
- ✅ No confusion - just one clean API

## Best Practices

### 1. Session Management
```python
# Maintain context across queries
session_id = "user_123_session"
for query in queries:
    result = await run_unified_agent(
        query=query,
        session_id=session_id  # Same session preserves context
    )
```

### 2. Memory Integration
```python
# Personalize responses with user context
result = await run_unified_agent(
    query="Recommend a programming language",
    memories="User is a beginner interested in web development"
)
```

### 3. Error Handling
```python
try:
    result = await run_unified_agent(query)
    if result["status"] == "success":
        print(result["response"])
    else:
        print(f"Error: {result['error']}")
except Exception as e:
    print(f"Failed to run agent: {e}")
```

### 4. Tool Selection Hints
```python
# Help the agent choose the right tool with clear queries

# ✅ Good - Clear intent
"Execute SQL: SELECT * FROM users WHERE active = true"
"Search the web for latest SpaceX launch"
"Analyze the image report_chart.png"

# ❌ Avoid - Ambiguous
"Get data about users"  # SQL or search?
"Information about SpaceX"  # Web or documents?
```

## Performance Tips

1. **Use specific tools when you know what you need:**
   ```python
   # If you specifically need web search
   result = await super_agent.run("search_web: latest AI news")
   ```

2. **Batch related queries in one session:**
   ```python
   # Good - maintains context
   session = "analysis_001"
   await run_unified_agent("Load dataset X", session_id=session)
   await run_unified_agent("Analyze patterns", session_id=session)
   await run_unified_agent("Generate insights", session_id=session)
   ```

3. **Configure search appropriately:**
   ```python
   # For simple queries - limit results
   deps.search_config["max_results"] = 5

   # For research - comprehensive search
   deps.search_config["max_results"] = 50
   deps.search_config["use_graph"] = True
   deps.search_config["use_vector"] = True
   ```

## Summary

The Unified Super Agent (`src/agent/unified_agent.py`) is your one-stop solution for:
- 🔍 Intelligent search with automatic routing
- 🌐 Web search with multiple providers
- 📊 SQL queries and data analysis
- 💻 Safe Python code execution
- 🖼️ Image analysis and understanding
- 📄 Document management and RAG
- 🧠 Memory-enhanced personalization

No more confusion between multiple agents - just use `super_agent` for everything!
