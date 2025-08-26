"""
LLM provider configuration for Pydantic AI.
"""

import logging
import os
from typing import Any

try:
    from openai import AsyncOpenAI, OpenAI
except ImportError:
    AsyncOpenAI = None
    OpenAI = None

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

try:
    from pydantic_ai.models.openai import OpenAIModel
except ImportError:
    OpenAIModel = None

try:
    from pydantic_ai.models.anthropic import AnthropicModel
except ImportError:
    AnthropicModel = None

try:
    from pydantic_ai.models.ollama import OllamaModel
except ImportError:
    OllamaModel = None

try:
    from pydantic_ai.models.gemini import GeminiModel
except ImportError:
    GeminiModel = None

try:
    import voyageai
except ImportError:
    voyageai = None

try:
    import cohere
except ImportError:
    cohere = None

from pydantic_ai.models import Model

logger = logging.getLogger(__name__)


def get_llm_model(provider: str | None = None, model_name: str | None = None, **kwargs) -> Model:
    """
    Get configured LLM model for Pydantic AI.

    Args:
        provider: Override provider from environment
        model_name: Override model name from environment
        **kwargs: Additional model configuration

    Returns:
        Configured Pydantic AI model
    """
    # Get configuration from environment or parameters
    provider = provider or os.getenv("LLM_PROVIDER", "openai")

    if provider == "openai":
        return _get_openai_model(model_name, **kwargs)
    if provider == "anthropic":
        return _get_anthropic_model(model_name, **kwargs)
    if provider == "ollama":
        return _get_ollama_model(model_name, **kwargs)
    if provider == "openrouter":
        return _get_openrouter_model(model_name, **kwargs)
    if provider == "gemini":
        return _get_gemini_model(model_name, **kwargs)
    raise ValueError(f"Unsupported LLM provider: {provider}")


def _get_openai_model(model_name: str | None = None, **kwargs) -> Model:
    """Configure OpenAI model."""
    if not OpenAIModel or not AsyncOpenAI:
        raise ImportError("OpenAI dependencies not available. Install with: pip install openai")

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key not found in environment")

    model_name = model_name or os.getenv("LLM_MODEL") or os.getenv("LLM_CHOICE", "gpt-4o-mini")

    # Default configuration for the model
    settings = {}
    if "temperature" in kwargs:
        settings["temperature"] = kwargs.pop("temperature")
    else:
        settings["temperature"] = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    if "max_tokens" in kwargs:
        settings["max_tokens"] = kwargs.pop("max_tokens")
    else:
        settings["max_tokens"] = int(os.getenv("LLM_MAX_TOKENS", "2000"))

    # Override with remaining kwargs
    settings.update(kwargs)

    logger.info(f"Configured OpenAI model: {model_name}")
    return OpenAIModel(model_name, api_key=api_key, **settings)


def _get_anthropic_model(model_name: str | None = None, **kwargs) -> Model:
    """Configure Anthropic model."""
    if not AnthropicModel or not AsyncAnthropic:
        raise ImportError(
            "Anthropic dependencies not available. Install with: pip install anthropic"
        )

    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        raise ValueError("Anthropic API key not found in environment")

    model_name = (
        model_name or os.getenv("LLM_MODEL") or os.getenv("LLM_CHOICE", "claude-3-sonnet-20240229")
    )

    # Default configuration for the model
    settings = {}
    if "temperature" in kwargs:
        settings["temperature"] = kwargs.pop("temperature")
    else:
        settings["temperature"] = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    if "max_tokens" in kwargs:
        settings["max_tokens"] = kwargs.pop("max_tokens")
    else:
        settings["max_tokens"] = int(os.getenv("LLM_MAX_TOKENS", "2000"))

    # Override with remaining kwargs
    settings.update(kwargs)

    logger.info(f"Configured Anthropic model: {model_name}")
    return AnthropicModel(model_name, api_key=api_key, **settings)


def _get_ollama_model(model_name: str | None = None, **kwargs) -> Model:
    """Configure Ollama model."""
    if not OllamaModel:
        raise ImportError("Ollama support requires additional dependencies") from None

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model_name = model_name or os.getenv("LLM_MODEL", "llama2")

    config = {
        "base_url": base_url,
        "model": model_name,
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
    }

    config.update(kwargs)

    logger.info(f"Configured Ollama model: {model_name} at {base_url}")
    return OllamaModel(**config)


def _get_openrouter_model(model_name: str | None = None, **kwargs) -> Model:
    """Configure OpenRouter model."""
    if not OpenAIModel:
        raise ImportError(
            "OpenRouter support requires OpenAI model. Install with: pip install openai"
        )

    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        raise ValueError("OpenRouter API key not found in environment")

    model_name = model_name or os.getenv("LLM_MODEL", "openai/gpt-4-turbo")

    config = {
        "api_key": api_key,
        "base_url": "https://openrouter.ai/api/v1",
        "model": model_name,
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "2000")),
    }

    config.update(kwargs)

    logger.info(f"Configured OpenRouter model: {model_name}")
    return OpenAIModel(**config)


def _get_gemini_model(model_name: str | None = None, **kwargs) -> Model:
    """Configure Google Gemini model."""
    if GeminiModel:
        # Use native Gemini model if available
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key not found in environment")

        model_name = model_name or os.getenv("LLM_MODEL", "gemini-pro")
        logger.info(f"Configured Gemini model: {model_name}")
        return GeminiModel(model_name, api_key=api_key)

    if OpenAIModel and AsyncOpenAI:
        # Fall back to OpenAI-compatible interface if available
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key not found in environment") from None

        model_name = model_name or os.getenv("LLM_MODEL") or os.getenv("LLM_CHOICE", "gemini-pro")

        settings = {}
        if "temperature" in kwargs:
            settings["temperature"] = kwargs.pop("temperature")
        else:
            settings["temperature"] = float(os.getenv("LLM_TEMPERATURE", "0.7"))

        settings.update(kwargs)

        logger.info(f"Configured Gemini model (via OpenAI interface): {model_name}")
        return OpenAIModel(
            model_name,
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta",
            **settings,
        )

    raise ImportError("Gemini support requires either google-ai or openai dependencies")


def get_embedding_model(provider: str | None = None) -> Any:
    """
    Get configured embedding model.

    This is separate from the LLM model as embeddings often use different providers.
    """
    provider = provider or os.getenv("EMBEDDING_PROVIDER", "openai")

    if provider == "openai":
        if not OpenAI:
            raise ImportError("OpenAI not available. Install with: pip install openai")

        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("EMBEDDING_API_KEY")
        model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        return OpenAI(api_key=api_key), model

    if provider == "voyage":
        if not voyageai:
            raise ImportError("VoyageAI not available. Install with: pip install voyageai")

        api_key = os.getenv("VOYAGE_API_KEY") or os.getenv("EMBEDDING_API_KEY")
        model = os.getenv("EMBEDDING_MODEL", "voyage-2")
        voyageai.api_key = api_key
        return voyageai, model

    if provider == "cohere":
        if not cohere:
            raise ImportError("Cohere not available. Install with: pip install cohere")

        api_key = os.getenv("COHERE_API_KEY") or os.getenv("EMBEDDING_API_KEY")
        model = os.getenv("EMBEDDING_MODEL", "embed-english-v3.0")
        client = cohere.Client(api_key)
        return client, model

    raise ValueError(f"Unsupported embedding provider: {provider}")


# Model capability metadata
MODEL_CAPABILITIES = {
    "gpt-4o": {
        "max_tokens": 128000,
        "supports_vision": True,
        "supports_function_calling": True,
        "supports_streaming": True,
    },
    "gpt-4o-mini": {
        "max_tokens": 128000,
        "supports_vision": True,
        "supports_function_calling": True,
        "supports_streaming": True,
    },
    "gpt-4-turbo": {
        "max_tokens": 128000,
        "supports_vision": True,
        "supports_function_calling": True,
        "supports_streaming": True,
    },
    "claude-3-opus-20240229": {
        "max_tokens": 200000,
        "supports_vision": True,
        "supports_function_calling": True,
        "supports_streaming": True,
    },
    "claude-3-sonnet-20240229": {
        "max_tokens": 200000,
        "supports_vision": True,
        "supports_function_calling": True,
        "supports_streaming": True,
    },
    "gemini-pro": {
        "max_tokens": 30720,
        "supports_vision": False,
        "supports_function_calling": True,
        "supports_streaming": True,
    },
    "gemini-pro-vision": {
        "max_tokens": 30720,
        "supports_vision": True,
        "supports_function_calling": True,
        "supports_streaming": True,
    },
}


def get_model_capabilities(model_name: str) -> dict[str, Any]:
    """Get capabilities for a specific model."""
    # Handle model name variations
    base_model = model_name.split("/")[-1]  # Handle OpenRouter format

    return MODEL_CAPABILITIES.get(
        base_model,
        {
            "max_tokens": 4096,
            "supports_vision": False,
            "supports_function_calling": True,
            "supports_streaming": False,
        },
    )
