import os

from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider


def get_llm_client():
    """Get the LLM client for agent interactions."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()

    if provider == "anthropic":
        # For Anthropic, we don't use AsyncOpenAI client
        # The pydantic-ai AnthropicModel handles this internally
        return None
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    api_key = os.getenv("LLM_API_KEY", "no-api-key-provided")
    llm_client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    return llm_client


def get_model():
    """Get the configured model for the agent."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    llm = os.getenv("LLM_CHOICE", "gpt-4o-mini")
    api_key = os.getenv("LLM_API_KEY", "ollama")

    if provider == "anthropic":
        from pydantic_ai.models.anthropic import AnthropicModel

        # Map common model names to Anthropic's naming
        model_map = {
            "claude-4-sonnet": "claude-4-sonnet",  # Claude 4 Sonnet with 1M token support
            "claude-3-opus": "claude-3-opus-20240229",
            "claude-3-sonnet": "claude-3-5-sonnet-20241022",
            "claude-3.5-sonnet": "claude-3-5-sonnet-20241022",
            "claude-3-haiku": "claude-3-haiku-20240307",
        }
        # Use mapped name if available, otherwise use as-is
        anthropic_model = model_map.get(llm, llm)
        return AnthropicModel(anthropic_model, api_key=api_key)
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    return OpenAIModel(llm, provider=OpenAIProvider(base_url=base_url, api_key=api_key))
