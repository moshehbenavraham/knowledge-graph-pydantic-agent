import os

from mem0 import AsyncMemory, Memory

from src.config import get_settings
from src.config.clients import clients_config


def get_mem0_config():
    # Get configuration from centralized settings
    get_settings()

    # Initialize config dictionary
    config = {}

    # Configure LLM based on provider
    llm_provider = clients_config.llm_provider.value
    if llm_provider in ("openai", "openrouter"):
        config["llm"] = {
            "provider": "openai",
            "config": {
                "model": clients_config.llm_model,
                "temperature": 0.2,
                "max_tokens": 2000,
            },
        }

        # Set API key in environment if not already set
        if llm_provider == "openai" and clients_config.llm_api_key:
            os.environ["OPENAI_API_KEY"] = clients_config.llm_api_key

        # For OpenRouter, set the specific API key
        if llm_provider == "openrouter" and clients_config.llm_api_key:
            os.environ["OPENROUTER_API_KEY"] = clients_config.llm_api_key

    elif llm_provider == "ollama":
        config["llm"] = {
            "provider": "ollama",
            "config": {
                "model": clients_config.llm_model,
                "temperature": 0.2,
                "max_tokens": 2000,
            },
        }

        # Set base URL for Ollama if provided
        if clients_config.llm_base_url:
            config["llm"]["config"]["ollama_base_url"] = clients_config.llm_base_url.replace(
                "/v1", ""
            )

    # Configure embedder based on provider
    embedding_provider = clients_config.embedding_provider.value
    if embedding_provider == "openai":
        config["embedder"] = {
            "provider": "openai",
            "config": {
                "model": clients_config.embedding_model,
                "embedding_dims": clients_config.embedding_dimension,
            },
        }

        # Set API key in environment if not already set
        if clients_config.embedding_api_key:
            os.environ["OPENAI_API_KEY"] = clients_config.embedding_api_key

    elif embedding_provider == "ollama":
        config["embedder"] = {
            "provider": "ollama",
            "config": {
                "model": clients_config.embedding_model,
                "embedding_dims": clients_config.embedding_dimension,
            },
        }

        # Set base URL for Ollama if provided
        if clients_config.embedding_base_url:
            config["embedder"]["config"]["ollama_base_url"] = (
                clients_config.embedding_base_url.replace("/v1", "")
            )

    # Configure Supabase vector store (using Supabase for everything)
    config["vector_store"] = {
        "provider": "supabase",
        "config": {
            "connection_string": clients_config.supabase_url or "",
            "collection_name": "mem0_memories",
            "embedding_model_dims": clients_config.embedding_dimension,
        },
    }

    return config


def get_mem0_client():
    # Create and return the Memory client
    config = get_mem0_config()
    return Memory.from_config(config)


async def get_mem0_client_async():
    # Create and return the Memory client
    config = get_mem0_config()
    return await AsyncMemory.from_config(config)
