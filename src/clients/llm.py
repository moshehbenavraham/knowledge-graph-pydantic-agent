from src.config.clients import clients_config

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
    if clients_config.llm_provider.value == "anthropic":
        # For Anthropic, we don't use AsyncOpenAI client
        # The pydantic-ai AnthropicModel handles this internally
        return None

    llm_client = AsyncOpenAI(
        base_url=clients_config.llm_base_url, api_key=clients_config.llm_api_key
    )
    return llm_client


def get_model():
    """Get the configured model for the agent."""
    provider = clients_config.llm_provider.value
    llm = clients_config.llm_model
    api_key = clients_config.llm_api_key

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

    return OpenAIChatModel(
        llm, provider=OpenAIProvider(base_url=clients_config.llm_base_url, api_key=api_key)
    )
