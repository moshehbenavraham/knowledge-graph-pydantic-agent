"""
Example usage of Phase 3 Agent Intelligence.

This script demonstrates the key capabilities of the agent intelligence layer.
"""

import asyncio
import logging
from unittest.mock import Mock

from src.agentic_rag.agent import IntentAnalyzer, QueryRouter, ResponseGenerator, load_preset

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_intent_analysis():
    """Demonstrate intent analysis capabilities."""
    print("\n" + "=" * 60)
    print("INTENT ANALYSIS DEMO")
    print("=" * 60)

    analyzer = IntentAnalyzer()

    queries = [
        "What is machine learning?",
        "How is Microsoft related to OpenAI?",
        "Show me the timeline of AI developments in 2023",
        "Compare Google and Apple's AI strategies",
        "List all companies that have invested in AI",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        result = await analyzer.analyze(query)
        print(f"  Intent: {result.primary_intent.value}")
        print(f"  Strategy: {result.search_strategy.value}")
        print(f"  Entities: {result.entities}")
        print(f"  Complexity: {result.complexity_score:.2f}")
        print(f"  Confidence: {result.confidence:.2f}")


async def demo_query_routing():
    """Demonstrate query routing capabilities."""
    print("\n" + "=" * 60)
    print("QUERY ROUTING DEMO")
    print("=" * 60)

    analyzer = IntentAnalyzer()
    router = QueryRouter()

    queries = [
        "What does OpenAI do?",
        "Show me Microsoft's partnerships",
        "When was GPT-4 released?",
    ]

    for query in queries:
        print(f"\nQuery: {query}")

        # Analyze query
        analyzed = await analyzer.analyze(query)

        # Route query
        decision = router.route(analyzed)

        print(f"  Primary Strategy: {decision.primary_strategy.value}")
        print(f"  Fallback Strategies: {[s.value for s in decision.fallback_strategies]}")
        print(f"  Recommended Tools: {decision.recommended_tools}")
        print(f"  Confidence: {decision.confidence:.2f}")
        print(f"  Reasoning: {decision.reasoning}")


async def demo_response_generation():
    """Demonstrate response generation capabilities."""
    print("\n" + "=" * 60)
    print("RESPONSE GENERATION DEMO")
    print("=" * 60)

    generator = ResponseGenerator()

    # Mock search results
    search_results = {
        "search_type": "hybrid",
        "vector_results": [
            {
                "content": "OpenAI is an AI research company founded in 2015.",
                "score": 0.92,
                "document_title": "AI Companies Overview",
                "document_id": "doc1",
                "chunk_id": "chunk1",
            },
            {
                "content": "OpenAI developed ChatGPT and the GPT series of models.",
                "score": 0.88,
                "document_title": "AI Models Guide",
                "document_id": "doc2",
                "chunk_id": "chunk2",
            },
        ],
        "graph_results": {
            "facts": [
                {
                    "fact": "OpenAI was founded by Elon Musk and Sam Altman",
                    "confidence": 0.95,
                    "source_chunk": "chunk3",
                },
                {
                    "fact": "Microsoft invested $10 billion in OpenAI in 2023",
                    "confidence": 0.90,
                    "source_chunk": "chunk4",
                },
            ]
        },
    }

    # Mock analyzed query

    analyzed_query = Mock(complexity_score=0.4, primary_intent="FACTUAL")

    # Generate response
    response = await generator.generate_response("What is OpenAI?", search_results, analyzed_query)

    print("\nGenerated Response:")
    print(f"Answer: {response.answer[:200]}...")
    print(f"\nCitations ({len(response.citations)}):")
    for i, citation in enumerate(response.citations[:3], 1):
        print(f"  {i}. {citation.document_title} (Confidence: {citation.confidence:.1%})")
    print(f"\nOverall Confidence: {response.confidence:.1%}")
    print(f"Search Strategy: {response.search_strategy_used}")
    print("\nFollow-up Questions:")
    for q in response.follow_up_questions[:3]:
        print(f"  - {q}")


async def demo_configuration():
    """Demonstrate configuration management."""
    print("\n" + "=" * 60)
    print("CONFIGURATION DEMO")
    print("=" * 60)

    # Load different presets
    configs = {
        "development": load_preset("development"),
        "production": load_preset("production"),
        "cost_optimized": load_preset("cost_optimized"),
    }

    for name, config in configs.items():
        print(f"\n{name.upper()} Configuration:")
        print(f"  LLM Model: {config.llm_model}")
        print(f"  Temperature: {config.llm_temperature}")
        print(f"  Caching: {config.enable_caching}")
        print(f"  Search Limit: {config.default_search_limit}")
        print(f"  Log Level: {config.log_level}")


async def demo_full_agent():
    """Demonstrate full agent capabilities."""
    print("\n" + "=" * 60)
    print("FULL AGENT DEMO")
    print("=" * 60)

    # Note: This requires proper environment setup with LLM API keys
    # For demo purposes, we'll show the structure

    queries = [
        "What is the relationship between Microsoft and OpenAI?",
        "Compare the AI strategies of major tech companies",
        "Show me the timeline of GPT model releases",
    ]

    print("\nAgent Query Processing:")
    for query in queries:
        print(f"\nQuery: {query}")

        # For demo, show expected structure
        print("  Expected response structure:")
        print("    - Answer with citations")
        print("    - Confidence score")
        print("    - Search strategy used")
        print("    - Follow-up questions")


async def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("PHASE 3: AGENT INTELLIGENCE DEMONSTRATION")
    print("=" * 60)

    # Run demos
    await demo_intent_analysis()
    await demo_query_routing()
    await demo_response_generation()
    await demo_configuration()
    await demo_full_agent()

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nPhase 3 Implementation Summary:")
    print("✓ Intent Analysis - Query understanding and classification")
    print("✓ Query Routing - Optimal search strategy selection")
    print("✓ Response Generation - Citation management and synthesis")
    print("✓ Configuration - Flexible preset-based configuration")
    print("✓ Full Agent - Integrated intelligent search system")


if __name__ == "__main__":
    asyncio.run(main())
