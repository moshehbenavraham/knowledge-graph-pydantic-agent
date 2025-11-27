import structlog
from openai import AsyncOpenAI

from src.config.clients import clients_config

logger = structlog.get_logger(__name__)


def get_embedding_client() -> AsyncOpenAI:
    """Get the embedding client for document processing and RAG."""
    logger.info(
        "Creating embedding client",
        provider=clients_config.embedding_provider.value,
        model=clients_config.embedding_model,
        base_url=clients_config.embedding_base_url,
    )
    embedding_client = AsyncOpenAI(
        base_url=clients_config.embedding_base_url, api_key=clients_config.embedding_api_key
    )
    return embedding_client
