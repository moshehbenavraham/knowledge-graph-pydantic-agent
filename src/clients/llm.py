from openai import AsyncOpenAI
import os

def get_llm_client():
    # Embedding client setup
    base_url = os.getenv('EMBEDDING_BASE_URL', 'https://api.openai.com/v1')
    api_key = os.getenv('EMBEDDING_API_KEY', 'no-api-key-provided')
    
    embedding_client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    return embedding_client