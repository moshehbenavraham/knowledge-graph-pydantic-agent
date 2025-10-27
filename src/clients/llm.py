import structlog

from src.config.clients import clients_config

logger = structlog.get_logger(__name__)

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

try:
    from pydantic_ai.models.openai import OpenAIChatModel
except ImportError:
    OpenAIChatModel = None

try:
    from pydantic_ai.providers.openai import OpenAIProvider
except ImportError:
    OpenAIProvider = None

try:
    from pydantic_ai.models.anthropic import AnthropicModel
except ImportError:
    AnthropicModel = None


def get_llm_client():
    """Get the LLM client for agent interactions."""
    logger.info(
        "Creating LLM client",
        provider=clients_config.llm_provider.value,
        model=clients_config.llm_model,
    )

    if clients_config.llm_provider.value == "anthropic":
        # For Anthropic, we don't use AsyncOpenAI client
        # The pydantic-ai AnthropicModel handles this internally
        logger.info("Using Anthropic provider, no client needed")
        return None

    llm_client = AsyncOpenAI(
        base_url=clients_config.llm_base_url, api_key=clients_config.llm_api_key
    )
    return llm_client


def get_model():
    """
    Get the configured model for the agent.

    Supports multiple LLM providers:
    - OpenAI: Direct OpenAI API
    - Anthropic: Claude models via Anthropic API
    - Ollama: Local LLMs via OpenAI-compatible API
    - OpenRouter: Multiple models via OpenRouter API (OpenAI-compatible)

    Returns:
        Configured Pydantic AI model instance
    """
    provider = clients_config.llm_provider.value
    llm = clients_config.llm_model
    api_key = clients_config.llm_api_key

    logger.info("Getting configured model", provider=provider, model=llm)

    if provider == "anthropic":
        if not AnthropicModel:
            raise ImportError("Anthropic model not available")

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

    # OpenAI, Ollama, and OpenRouter all use OpenAI-compatible API
    # Ollama exposes an OpenAI-compatible endpoint at http://localhost:11434/v1
    # OpenRouter provides OpenAI-compatible API at https://openrouter.ai/api/v1
    return OpenAIChatModel(
        llm, provider=OpenAIProvider(base_url=clients_config.llm_base_url, api_key=api_key)
    )
