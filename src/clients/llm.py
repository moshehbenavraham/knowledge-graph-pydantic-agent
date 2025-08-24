import os

from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider


def get_llm_client():
    """Get the LLM client for agent interactions."""
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    api_key = os.getenv("LLM_API_KEY", "no-api-key-provided")

    llm_client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    return llm_client


def get_model():
    """Get the configured model for the agent."""
    llm = os.getenv("LLM_CHOICE", "gpt-4o-mini")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    api_key = os.getenv("LLM_API_KEY", "ollama")

    return OpenAIModel(llm, provider=OpenAIProvider(base_url=base_url, api_key=api_key))
