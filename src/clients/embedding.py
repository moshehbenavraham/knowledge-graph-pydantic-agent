import os

from openai import AsyncOpenAI


def get_embedding_client():
    """Get the embedding client for document processing and RAG."""
    base_url = os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1")
    api_key = os.getenv("EMBEDDING_API_KEY", "no-api-key-provided")

    embedding_client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    return embedding_client
