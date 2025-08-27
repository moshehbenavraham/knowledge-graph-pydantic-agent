from src.config.clients import clients_config

from openai import AsyncOpenAI


def get_embedding_client():
    """Get the embedding client for document processing and RAG."""
    embedding_client = AsyncOpenAI(
        base_url=clients_config.embedding_base_url,
        api_key=clients_config.embedding_api_key
    )
    return embedding_client
