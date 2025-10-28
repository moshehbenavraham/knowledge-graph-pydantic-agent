"""
Clients configuration facade.

Provides convenient access to database and API client settings.
"""

import structlog

from .settings import EmbeddingProvider, LLMProvider, get_settings

logger = structlog.get_logger(__name__)


class ClientsConfig:
    """Facade for client-related configuration."""

    def __init__(self):
        """Initialize with current settings."""
        self._settings = get_settings()

    # LLM Client Configuration
    @property
    def llm_provider(self) -> LLMProvider:
        """Get LLM provider."""
        return self._settings.llm_provider

    @property
    def llm_base_url(self) -> str:
        """Get LLM base URL."""
        return self._settings.llm_base_url

    @property
    def llm_api_key(self) -> str:
        """Get LLM API key."""
        return self._settings.llm_api_key

    @property
    def llm_model(self) -> str:
        """Get LLM model name."""
        return self._settings.get_effective_llm_model()

    # Embedding Client Configuration
    @property
    def embedding_provider(self) -> EmbeddingProvider:
        """Get embedding provider."""
        return self._settings.embedding_provider

    @property
    def embedding_base_url(self) -> str:
        """Get embedding base URL."""
        return self._settings.embedding_base_url

    @property
    def embedding_api_key(self) -> str:
        """Get embedding API key."""
        return self._settings.embedding_api_key

    @property
    def embedding_model(self) -> str:
        """Get embedding model name."""
        return self._settings.get_effective_embedding_model()

    @property
    def embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return self._settings.embedding_dimension

    # Database Client Configuration
    @property
    def database_url(self) -> str | None:
        """Get database URL."""
        return self._settings.database_url

    @property
    def supabase_url(self) -> str | None:
        """Get Supabase URL."""
        return self._settings.supabase_url

    @property
    def supabase_service_key(self) -> str | None:
        """Get Supabase service key."""
        return self._settings.supabase_service_key

    @property
    def supabase_key(self) -> str | None:
        """Get Supabase key (alias for supabase_service_key)."""
        return self.supabase_service_key

    @property
    def openai_api_key(self) -> str:
        """Get OpenAI API key (alias for llm_api_key when provider is OpenAI)."""
        return self.llm_api_key

    @property
    def neo4j_uri(self) -> str:
        """Get Neo4j URI."""
        return self._settings.neo4j_uri

    @property
    def neo4j_user(self) -> str:
        """Get Neo4j username."""
        return self._settings.neo4j_user

    @property
    def neo4j_password(self) -> str:
        """Get Neo4j password."""
        return self._settings.neo4j_password

    @property
    def neo4j_database(self) -> str:
        """Get Neo4j database name."""
        return self._settings.neo4j_database

    @property
    def redis_url(self) -> str | None:
        """Get Redis URL."""
        return self._settings.redis_url

    @property
    def enable_redis_cache(self) -> bool:
        """Check if Redis cache is enabled."""
        return self._settings.enable_redis_cache

    def get_llm_config(self) -> dict[str, any]:
        """Get LLM client configuration."""
        logger.info(
            "Getting LLM configuration", provider=self.llm_provider.value, model=self.llm_model
        )
        return {
            "provider": self.llm_provider,
            "base_url": self.llm_base_url,
            "api_key": self.llm_api_key,
            "model": self.llm_model,
            "temperature": self._settings.llm_temperature,
            "max_tokens": self._settings.llm_max_tokens,
        }

    def get_embedding_config(self) -> dict[str, any]:
        """Get embedding client configuration."""
        logger.info(
            "Getting embedding configuration",
            provider=self.embedding_provider.value,
            model=self.embedding_model,
        )
        return {
            "provider": self.embedding_provider,
            "base_url": self.embedding_base_url,
            "api_key": self.embedding_api_key,
            "model": self.embedding_model,
            "dimension": self.embedding_dimension,
            "batch_size": self._settings.embedding_batch_size,
        }

    def get_postgres_config(self) -> dict[str, any]:
        """Get PostgreSQL configuration."""
        logger.info("Getting PostgreSQL configuration", has_database_url=bool(self.database_url))
        return {
            "database_url": self.database_url,
            "supabase_url": self.supabase_url,
            "supabase_service_key": self.supabase_service_key,
            "pool_min": self._settings.pg_pool_min,
            "pool_max": self._settings.pg_pool_max,
            "command_timeout": self._settings.pg_command_timeout,
        }

    def get_neo4j_config(self) -> dict[str, any]:
        """Get Neo4j configuration."""
        logger.info("Getting Neo4j configuration", database=self.neo4j_database)
        return {
            "uri": self.neo4j_uri,
            "user": self.neo4j_user,
            "password": self.neo4j_password,
            "database": self.neo4j_database,
            "encrypted": self._settings.neo4j_encrypted,
            "pool_size": self._settings.neo4j_pool_size,
            "connection_timeout": self._settings.neo4j_connection_timeout,
        }

    def get_redis_config(self) -> dict[str, any]:
        """Get Redis configuration."""
        logger.info("Getting Redis configuration", enabled=self.enable_redis_cache)
        return {
            "url": self.redis_url,
            "enabled": self.enable_redis_cache,
            "pool_size": self._settings.redis_pool_size,
            "socket_timeout": self._settings.redis_socket_timeout,
        }

    def has_supabase_configured(self) -> bool:
        """Check if Supabase is configured."""
        return bool(self.supabase_url and self.supabase_service_key)

    def has_neo4j_configured(self) -> bool:
        """Check if Neo4j is configured."""
        return bool(self.neo4j_uri and self.neo4j_user and self.neo4j_password)


# Singleton instance
clients_config = ClientsConfig()
