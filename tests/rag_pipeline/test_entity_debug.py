#!/usr/bin/env python
"""Debug entity extraction issue."""
import asyncio
import logging
import sys
import traceback

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s", stream=sys.stdout)

from src.agentic_rag.ingestion.knowledge_extractor import KnowledgeExtractor


async def test_entity_extraction():
    """Test entity extraction with detailed debugging."""
    extractor = KnowledgeExtractor()
    text = """OpenAI raised $6.6 billion at a $157 billion valuation in October 2024.
    The round was led by Thrive Capital and included Microsoft, NVIDIA, and SoftBank."""

    print("\n=== Step 1: Pattern-based extraction ===")
    pattern_entities = extractor._extract_entities_by_pattern(text)
    print(f"Pattern entities: {len(pattern_entities)}")
    for e in pattern_entities:
        print(f"  - {e.name} ({e.type.value})")

    print("\n=== Step 2: Building LLM prompt ===")
    prompt = """
    Extract entities from this text.
    Return ONLY the entity name and type.
    Do NOT include descriptions or content.

    Valid types: company, person, technology, product, location, event, organization

    Format each entity as:
    {{"name": "...", "type": "...", "confidence": 0.0-1.0}}

    Return as JSON array. Maximum 10 entities.

    Text: {text}
    """
    formatted_prompt = prompt.format(text=text[:2000])
    print(f"Prompt length: {len(formatted_prompt)} chars")

    print("\n=== Step 3: Calling LLM ===")
    try:
        response = await extractor.llm_agent.run(formatted_prompt)
        print(f"Response type: {type(response)}")
        print(f"Response attributes: {dir(response)}")

        print("\n=== Step 4: Accessing response.output ===")
        try:
            output = response.output
            print(f"Output type: {type(output)}")
            print(f"Output content: {repr(output)[:500]}")
        except Exception as e:
            print(f"ERROR accessing response.output: {e}")
            print(f"Exception type: {type(e).__name__}")
            traceback.print_exc()
            return []

        print("\n=== Step 5: Parsing output ===")
        if isinstance(output, str):
            print("Output is string, parsing JSON...")
            import json

            try:
                entity_data = json.loads(output)
                print(f"Parsed JSON type: {type(entity_data)}")
                print(f"Parsed JSON: {entity_data}")
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"Raw output: {output!r}")
                return []
        else:
            print(f"Output is already parsed: {type(output)}")
            entity_data = output

        print(
            f"\n=== Success! Got {len(entity_data) if isinstance(entity_data, list) else 1} entities ==="
        )
        return entity_data

    except Exception as e:
        print(f"\n=== ERROR in LLM call: {e} ===")
        print(f"Exception type: {type(e).__name__}")
        traceback.print_exc()
        return []


if __name__ == "__main__":
    asyncio.run(test_entity_extraction())
