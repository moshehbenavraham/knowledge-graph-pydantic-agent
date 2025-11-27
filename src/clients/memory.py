import os
from typing import Any

import structlog
from mem0 import AsyncMemory, Memory

from src.config import clients

logger = structlog.get_logger(__name__)


def get_mem0_config() -> dict[str, Any]:
    # Get configuration from centralized settings
    # Note: Don't call get_settings() here as it may re-cache old values
    # The clients.clients_config already has the current settings

    logger.info(
        "Configuring Mem0",
        llm_provider=clients.clients_config.llm_provider.value,
        embedding_provider=clients.clients_config.embedding_provider.value,
    )

    # Initialize config dictionary
    config: dict[str, Any] = {}

    # Configure LLM based on provider
    # Use clients.clients_config to get current singleton instance (supports test reloading)
    llm_provider = clients.clients_config.llm_provider.value
    if llm_provider in ("openai", "openrouter"):
        config["llm"] = {
            "provider": "openai",
            "config": {
                "model": clients.clients_config.llm_model,
                "temperature": 0.2,
                "max_tokens": 2000,
            },
        }

        # Set API key in environment if not already set
        if llm_provider == "openai" and clients.clients_config.llm_api_key:
            os.environ["OPENAI_API_KEY"] = clients.clients_config.llm_api_key  # Constitution exception: CONST-II-001 - Mem0 library requires env vars  # fmt: skip

        # For OpenRouter, set the specific API key
        if llm_provider == "openrouter" and clients.clients_config.llm_api_key:
            os.environ["OPENROUTER_API_KEY"] = clients.clients_config.llm_api_key  # Constitution exception: CONST-II-001 - Mem0 library requires env vars  # fmt: skip

    elif llm_provider == "ollama":
        config["llm"] = {
            "provider": "ollama",
            "config": {
                "model": clients.clients_config.llm_model,
                "temperature": 0.2,
                "max_tokens": 2000,
            },
        }

        # Set base URL for Ollama if provided
        if clients.clients_config.llm_base_url:
            config["llm"]["config"]["ollama_base_url"] = (
                clients.clients_config.llm_base_url.replace("/v1", "")
            )

    # Configure embedder based on provider
    embedding_provider = clients.clients_config.embedding_provider.value
    if embedding_provider == "openai":
        config["embedder"] = {
            "provider": "openai",
            "config": {
                "model": clients.clients_config.embedding_model,
                "embedding_dims": clients.clients_config.embedding_dimension,
            },
        }

        # Set API key in environment if not already set
        if clients.clients_config.embedding_api_key:
            os.environ["OPENAI_API_KEY"] = clients.clients_config.embedding_api_key  # Constitution exception: CONST-II-001 - Mem0 library requires env vars  # fmt: skip

    elif embedding_provider == "ollama":
        config["embedder"] = {
            "provider": "ollama",
            "config": {
                "model": clients.clients_config.embedding_model,
                "embedding_dims": clients.clients_config.embedding_dimension,
            },
        }

        # Set base URL for Ollama if provided
        if clients.clients_config.embedding_base_url:
            config["embedder"]["config"]["ollama_base_url"] = (
                clients.clients_config.embedding_base_url.replace("/v1", "")
            )

    # Configure Supabase vector store (using PostgreSQL connection string)
    db_url = clients.clients_config.database_url or ""

    # WSL2 IPv6 compatibility: Keep pooler URL as-is (supports IPv4)
    # Do NOT convert pooler.supabase.com to db.*.supabase.co (IPv6-only)
    # The pooler URL provides IPv4 compatibility which is essential for WSL2 environments

    # Add SSL parameters for psycopg2 + SQLAlchemy stability
    if db_url and "sslmode" not in db_url:
        separator = "&" if "?" in db_url else "?"
        db_url = f"{db_url}{separator}sslmode=require&connect_timeout=10"

    config["vector_store"] = {
        "provider": "supabase",
        "config": {
            "connection_string": db_url,
            "collection_name": "mem0_memories",
            "embedding_model_dims": clients.clients_config.embedding_dimension,
        },
    }

    return config


def get_mem0_client() -> Memory:
    # Create and return the Memory client
    config = get_mem0_config()
    return Memory.from_config(config)


async def get_mem0_client_async() -> AsyncMemory:
    # Create and return the Memory client
    config = get_mem0_config()
    return await AsyncMemory.from_config(config)
