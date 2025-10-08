#!/usr/bin/env python3
"""
Unified Super-Agent Demo
========================

This demonstrates the capabilities of our new unified agent that combines:
- Intelligent search routing
- Web search
- RAG retrieval
- SQL queries
- Image analysis
- Code execution
- And more!
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from httpx import AsyncClient

# Load environment variables
load_dotenv()

# Import our unified super-agent
from src.agent import super_agent, UnifiedAgentDeps, run_unified_agent
from src.clients import get_supabase_client, get_llm_client
from src.clients.embedding import get_embedding_client


async def demo_basic_usage():
    """Basic usage of the unified agent."""
    
    print("=" * 60)
    print("UNIFIED SUPER-AGENT DEMO")
    print("=" * 60)
    
    # Get clients
    supabase = get_supabase_client()
    embedding_client = get_embedding_client()
    http_client = AsyncClient()
    
    # Example queries to demonstrate different capabilities
    queries = [
        "What documents are available in the knowledge base?",
        "Search for information about AI and machine learning",
        "Calculate the fibonacci sequence up to 10 using Python",
        "What's the latest news about artificial intelligence?",
    ]
    
    for query in queries:
        print(f"\n📝 Query: {query}")
        print("-" * 40)
        
        result = await run_unified_agent(
            query=query,
            session_id="demo_session",
            supabase_client=supabase,
            embedding_client=embedding_client,
            http_client=http_client,
            memories="User is interested in AI and technology",
        )
        
        if result["status"] == "success":
            print(f"✅ Response: {result['response']}")
            if result["metadata"].get("tools_used"):
                print(f"🔧 Tools used: {', '.join(result['metadata']['tools_used'])}")
        else:
            print(f"❌ Error: {result['error']}")
    
    await http_client.aclose()


async def demo_advanced_features():
    """Demonstrate advanced features of the unified agent."""
    
    print("\n" + "=" * 60)
    print("ADVANCED FEATURES DEMO")
    print("=" * 60)
    
    # Get clients
    supabase = get_supabase_client()
    embedding_client = get_embedding_client()
    http_client = AsyncClient()
    
    # Create dependencies directly for more control
    deps = UnifiedAgentDeps(
        supabase=supabase,
        embedding_client=embedding_client,
        http_client=http_client,
        brave_api_key=os.getenv("BRAVE_API_KEY"),
        searxng_base_url=os.getenv("SEARXNG_BASE_URL"),
        jina_api_key=os.getenv("JINA_API_KEY"),
        web_search_provider=os.getenv("WEB_SEARCH_PROVIDER"),
        memories="User is a data scientist interested in AI research",
        session_id="advanced_demo",
        search_config={
            "use_vector": True,
            "use_graph": True,
            "confidence_threshold": 0.8,
            "max_results": 25,
        }
    )
    
    # Complex multi-tool query
    complex_query = """
    First, list all available documents. Then search for any information 
    about neural networks. Finally, write Python code to implement a 
    simple perceptron algorithm.
    """
    
    print(f"\n📝 Complex Query: {complex_query}")
    print("-" * 40)
    
    result = await super_agent.run(complex_query, deps=deps)
    print(f"✅ Response: {result.data}")
    
    # Demonstrate smart search routing
    relationship_query = "What is the relationship between OpenAI and Microsoft?"
    
    print(f"\n📝 Relationship Query: {relationship_query}")
    print("-" * 40)
    
    result = await super_agent.run(relationship_query, deps=deps)
    print(f"✅ Response: {result.data}")
    
    await http_client.aclose()


async def demo_tool_specific():
    """Demonstrate specific tool usage."""
    
    print("\n" + "=" * 60)
    print("TOOL-SPECIFIC DEMO")
    print("=" * 60)
    
    # Get clients
    supabase = get_supabase_client()
    embedding_client = get_embedding_client()
    http_client = AsyncClient()
    
    deps = UnifiedAgentDeps(
        supabase=supabase,
        embedding_client=embedding_client,
        http_client=http_client,
        session_id="tool_demo",
    )
    
    # Test each tool category
    tool_tests = [
        ("🔍 RAG Search", "Find information about machine learning algorithms"),
        ("🌐 Web Search", "What are the latest AI developments in 2024?"),
        ("💻 Code Execution", "Write and execute code to calculate prime numbers up to 50"),
        ("📊 SQL Query", "Show me how to query the document_rows table"),
        ("📄 Document Listing", "List all available documents"),
    ]
    
    for tool_name, query in tool_tests:
        print(f"\n{tool_name}")
        print(f"Query: {query}")
        print("-" * 40)
        
        try:
            result = await super_agent.run(query, deps=deps)
            print(f"✅ Success: {str(result.data)[:200]}...")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    await http_client.aclose()


async def main():
    """Run all demos."""
    
    print("\n🚀 Starting Unified Super-Agent Demonstrations\n")
    
    try:
        # Run basic demo
        await demo_basic_usage()
        
        # Run advanced demo
        await demo_advanced_features()
        
        # Run tool-specific demo
        await demo_tool_specific()
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Demo completed!")
    print("\n" + "=" * 60)
    print("The unified super-agent combines all capabilities:")
    print("- Intelligent intent-based routing")
    print("- Vector search for semantic similarity")
    print("- Graph search for relationships (coming soon)")
    print("- Web search with multiple providers")
    print("- SQL queries on structured data")
    print("- Image analysis with vision models")
    print("- Safe Python code execution")
    print("- Document management")
    print("- Memory/personalization support")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())