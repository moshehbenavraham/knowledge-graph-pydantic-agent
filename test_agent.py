#!/usr/bin/env python3
"""Quick test script for agent capabilities."""

import asyncio
import os

from dotenv import load_dotenv

# Load environment
load_dotenv()


async def test_agent():
    """Test basic agent functionality."""
    from src.clients import get_llm_client, get_supabase_client
    from src.clients.embedding import get_embedding_client

    print("Testing connections...")

    # Test Supabase
    try:
        supabase = get_supabase_client()
        print("✓ Supabase connected")
    except Exception as e:
        print(f"✗ Supabase failed: {e}")

    # Test LLM
    try:
        llm = get_llm_client()
        if llm:  # Will be None for Anthropic
            print("✓ LLM client created")
        else:
            print("✓ Using Anthropic (no OpenAI client needed)")
    except Exception as e:
        print(f"✗ LLM failed: {e}")

    # Test Embeddings
    try:
        embed = get_embedding_client()
        response = await embed.embeddings.create(
            model=os.getenv("EMBEDDING_MODEL_CHOICE", "text-embedding-3-small"), input="test"
        )
        print(f"✓ Embeddings working (dim: {len(response.data[0].embedding)})")
    except Exception as e:
        print(f"✗ Embeddings failed: {e}")

    # Test Agent
    try:
        from httpx import AsyncClient

        from src.agent.agent import AgentDeps, agent

        deps = AgentDeps(
            supabase=supabase,
            embedding_client=embed,
            http_client=AsyncClient(),
            brave_api_key=os.getenv("BRAVE_API_KEY"),
            searxng_base_url=os.getenv("SEARXNG_BASE_URL"),
            memories="",
        )

        result = await agent.run("Say 'Hello, agent is working!'", deps=deps)
        print(f"✓ Agent response: {result.data}")
    except Exception as e:
        print(f"✗ Agent failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_agent())
