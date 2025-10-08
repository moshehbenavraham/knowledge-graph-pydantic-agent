#!/usr/bin/env python3
"""Quick test script to verify web search tools are working."""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from httpx import AsyncClient

load_dotenv()

from src.tools.web_search import web_search_tool


async def test_web_search():
    """Test the web search tool directly."""
    print("=" * 70)
    print("Testing Web Search Tool")
    print("=" * 70)

    # Read API keys from environment
    jina_api_key = os.getenv("JINA_API_KEY")
    brave_api_key = os.getenv("BRAVE_API_KEY")
    searxng_base_url = os.getenv("SEARXNG_BASE_URL")

    print(f"\nJina API Key: {'✓ Configured' if jina_api_key else '✗ Not set'}")
    print(f"Brave API Key: {'✓ Configured' if brave_api_key else '✗ Not set'}")
    print(f"SearXNG URL: {'✓ Configured' if searxng_base_url else '✗ Not set'}")

    query = "latest AI developments December 2024"
    print(f"\nQuery: {query}")
    print("\nSearching...\n")

    async with AsyncClient() as http_client:
        try:
            result = await web_search_tool(
                query=query,
                http_client=http_client,
                brave_api_key=brave_api_key,
                searxng_base_url=searxng_base_url,
                jina_api_key=jina_api_key,
                search_provider=None,  # Auto-select
            )

            print("=" * 70)
            print("RESULTS:")
            print("=" * 70)
            print(result[:1000])  # First 1000 chars
            print("\n✅ Web search tool is WORKING!")

        except Exception as e:
            print("=" * 70)
            print("ERROR:")
            print("=" * 70)
            print(f"❌ Web search failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    return True


if __name__ == "__main__":
    success = asyncio.run(test_web_search())
    sys.exit(0 if success else 1)
