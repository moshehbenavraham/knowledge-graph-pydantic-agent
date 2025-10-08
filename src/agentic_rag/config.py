"""
Backward compatibility wrapper for Agentic RAG configuration.

This module now delegates to the centralized configuration system
while maintaining the same interface for existing code.
"""

from dataclasses import dataclass

from src.config import get_settings, reload_settings


@dataclass
class DatabaseConfig:
    """Database configuration settings (backward compatibility)."""

    def __init__(self):
        settings = get_settings()
        self.database_url = settings.database_url
        self.supabase_url = settings.supabase_url
        self.supabase_service_key = settings.supabase_service_key
        self.neo4j_uri = settings.neo4j_uri
        self.neo4j_user = settings.neo4j_user
        self.neo4j_password = settings.neo4j_password
        self.neo4j_database = settings.neo4j_database
        self.neo4j_encrypted = settings.neo4j_encrypted
        self.redis_url = settings.redis_url
        self.enable_redis_cache = settings.enable_redis_cache


@dataclass
class ConnectionPoolConfig:
    """Connection pool configuration (backward compatibility)."""

    def __init__(self):
        settings = get_settings()
        self.pg_pool_min = settings.pg_pool_min
        self.pg_pool_max = settings.pg_pool_max
        self.pg_max_queries = settings.pg_max_queries
        self.pg_max_inactive_lifetime = settings.pg_max_inactive_lifetime
        self.pg_command_timeout = settings.pg_command_timeout
        self.neo4j_pool_size = settings.neo4j_pool_size
        self.neo4j_connection_timeout = settings.neo4j_connection_timeout
        self.neo4j_max_retry_time = settings.neo4j_max_retry_time
        self.redis_pool_size = settings.redis_pool_size
        self.redis_socket_timeout = settings.redis_socket_timeout


@dataclass
class EmbeddingConfig:
    """Embedding configuration (backward compatibility)."""

    def __init__(self):
        settings = get_settings()
        self.provider = settings.embedding_provider.value
        self.base_url = settings.embedding_base_url
        self.api_key = settings.embedding_api_key
        self.model = settings.embedding_model
        self.dimension = settings.embedding_dimension
        self.batch_size = settings.embedding_batch_size


@dataclass
class LLMConfig:
    """LLM configuration (backward compatibility)."""

    def __init__(self):
        settings = get_settings()
        self.provider = settings.llm_provider.value
        self.base_url = settings.llm_base_url
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.extraction_model = settings.extraction_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens


@dataclass
class PerformanceConfig:
    """Performance and optimization settings (backward compatibility)."""

    def __init__(self):
        settings = get_settings()
        self.vector_search_timeout = settings.vector_search_timeout
        self.graph_search_timeout = settings.graph_search_timeout
        self.enable_caching = settings.enable_caching
        self.embedding_cache_size = settings.embedding_cache_size
        self.embedding_cache_ttl = settings.embedding_cache_ttl
        self.graph_cache_size = settings.graph_cache_size
        self.graph_cache_ttl = settings.graph_cache_ttl
        self.enable_graph = settings.enable_graph
        self.enable_parallel_search = settings.enable_parallel_search
        self.graph_batch_size = settings.graph_batch_size
        self.circuit_breaker_failure_threshold = settings.circuit_breaker_failure_threshold
        self.circuit_breaker_recovery_timeout = settings.circuit_breaker_recovery_timeout
        self.circuit_breaker_half_open_requests = settings.circuit_breaker_half_open_requests


@dataclass
class IngestionConfig:
    """Document ingestion settings (backward compatibility)."""

    def __init__(self):
        settings = get_settings()
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
        self.max_entities_per_chunk = settings.max_entities_per_chunk
        self.max_fact_length = settings.max_fact_length
        self.use_semantic_chunking = settings.use_semantic_chunking


@dataclass
class APIConfig:
    """API server configuration (backward compatibility)."""

    def __init__(self):
        settings = get_settings()
        self.host = settings.api_host
        self.port = settings.api_port
        self.cors_origins = settings.get_cors_origins_list()
        self.log_level = settings.log_level
        self.app_env = settings.app_env.value


@dataclass
class Config:
    """Main configuration class combining all settings (backward compatibility)."""

    def __init__(self):
        self.database = DatabaseConfig()
        self.connection_pool = ConnectionPoolConfig()
        self.embedding = EmbeddingConfig()
        self.llm = LLMConfig()
        self.performance = PerformanceConfig()
        self.ingestion = IngestionConfig()
        self.api = APIConfig()

    def validate(self) -> list[str]:
        """
        Validate configuration and return list of errors.

        Returns:
            List of validation error messages
        """
        get_settings()
        # Delegate to new validation
        try:
            # Settings validates on instantiation
            return []
        except Exception as e:
            return [str(e)]

    def dict(self) -> dict:
        """
        Convert config to dictionary.

        Returns:
            Configuration as dictionary
        """
        settings = get_settings()
        return settings.to_dict()


# Global configuration instance (backward compatibility)
config = Config()


def get_config() -> Config:
    """
    Get the global configuration instance (backward compatibility).

    Returns:
        Global configuration
    """
    return config


def reload_config():
    """Reload configuration from environment variables."""
    reload_settings()
    # Note: global config is maintained for backward compatibility
    # pylint: disable=global-statement
    global config
    config = Config()
    return config
