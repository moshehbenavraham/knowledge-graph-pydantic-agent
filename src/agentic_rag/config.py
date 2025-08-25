"""
Configuration management for Agentic RAG system.

Centralized configuration for database connections, API settings, and performance tuning.
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    # PostgreSQL/Supabase
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", ""))
    supabase_url: str | None = field(default_factory=lambda: os.getenv("SUPABASE_URL"))
    supabase_service_key: str | None = field(
        default_factory=lambda: os.getenv("SUPABASE_SERVICE_KEY")
    )

    # Neo4j
    neo4j_uri: str = field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    neo4j_user: str = field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    neo4j_password: str = field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", ""))
    neo4j_database: str = field(default_factory=lambda: os.getenv("NEO4J_DATABASE", "neo4j"))
    neo4j_encrypted: bool = field(
        default_factory=lambda: os.getenv("NEO4J_ENCRYPTED", "true").lower() == "true"
    )

    # Redis (optional)
    redis_url: str | None = field(default_factory=lambda: os.getenv("REDIS_URL"))
    enable_redis_cache: bool = field(
        default_factory=lambda: os.getenv("ENABLE_REDIS_CACHE", "false").lower() == "true"
    )


@dataclass
class ConnectionPoolConfig:
    """Connection pool configuration."""

    # PostgreSQL pool settings
    pg_pool_min: int = field(default_factory=lambda: int(os.getenv("PG_POOL_MIN", "5")))
    pg_pool_max: int = field(default_factory=lambda: int(os.getenv("PG_POOL_MAX", "20")))
    pg_max_queries: int = field(default_factory=lambda: int(os.getenv("PG_MAX_QUERIES", "50000")))
    pg_max_inactive_lifetime: int = field(
        default_factory=lambda: int(os.getenv("PG_MAX_INACTIVE_LIFETIME", "300"))
    )
    pg_command_timeout: int = field(
        default_factory=lambda: int(os.getenv("PG_COMMAND_TIMEOUT", "60"))
    )

    # Neo4j pool settings
    neo4j_pool_size: int = field(default_factory=lambda: int(os.getenv("NEO4J_POOL_SIZE", "50")))
    neo4j_connection_timeout: float = field(
        default_factory=lambda: float(os.getenv("NEO4J_CONNECTION_TIMEOUT", "30.0"))
    )
    neo4j_max_retry_time: int = field(
        default_factory=lambda: int(os.getenv("NEO4J_MAX_RETRY_TIME", "30"))
    )

    # Redis pool settings
    redis_pool_size: int = field(default_factory=lambda: int(os.getenv("REDIS_POOL_SIZE", "10")))
    redis_socket_timeout: int = field(
        default_factory=lambda: int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))
    )


@dataclass
class EmbeddingConfig:
    """Embedding configuration."""

    provider: str = field(default_factory=lambda: os.getenv("EMBEDDING_PROVIDER", "openai"))
    base_url: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1")
    )
    api_key: str = field(default_factory=lambda: os.getenv("EMBEDDING_API_KEY", ""))
    model: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    )
    dimension: int = field(default_factory=lambda: int(os.getenv("EMBEDDING_DIMENSION", "1536")))
    batch_size: int = field(default_factory=lambda: int(os.getenv("EMBEDDING_BATCH_SIZE", "100")))


@dataclass
class LLMConfig:
    """LLM configuration."""

    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai"))
    base_url: str = field(
        default_factory=lambda: os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    )
    api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))
    extraction_model: str = field(
        default_factory=lambda: os.getenv("EXTRACTION_MODEL", "gpt-4o-mini")
    )
    temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.7")))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "2000")))


@dataclass
class PerformanceConfig:
    """Performance and optimization settings."""

    # Search timeouts
    vector_search_timeout: float = field(
        default_factory=lambda: float(os.getenv("VECTOR_SEARCH_TIMEOUT", "2.0"))
    )
    graph_search_timeout: float = field(
        default_factory=lambda: float(os.getenv("GRAPH_SEARCH_TIMEOUT", "3.0"))
    )

    # Caching
    enable_caching: bool = field(
        default_factory=lambda: os.getenv("ENABLE_CACHING", "true").lower() == "true"
    )
    embedding_cache_size: int = field(
        default_factory=lambda: int(os.getenv("EMBEDDING_CACHE_SIZE", "1000"))
    )
    embedding_cache_ttl: int = field(
        default_factory=lambda: int(os.getenv("EMBEDDING_CACHE_TTL", "3600"))
    )
    graph_cache_size: int = field(default_factory=lambda: int(os.getenv("GRAPH_CACHE_SIZE", "500")))
    graph_cache_ttl: int = field(default_factory=lambda: int(os.getenv("GRAPH_CACHE_TTL", "1800")))

    # Feature flags
    enable_graph: bool = field(
        default_factory=lambda: os.getenv("ENABLE_GRAPH", "true").lower() == "true"
    )
    enable_parallel_search: bool = field(
        default_factory=lambda: os.getenv("ENABLE_PARALLEL_SEARCH", "true").lower() == "true"
    )

    # Batching
    graph_batch_size: int = field(default_factory=lambda: int(os.getenv("GRAPH_BATCH_SIZE", "10")))

    # Circuit breaker
    circuit_breaker_failure_threshold: int = field(
        default_factory=lambda: int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5"))
    )
    circuit_breaker_recovery_timeout: int = field(
        default_factory=lambda: int(os.getenv("CIRCUIT_BREAKER_RECOVERY_TIMEOUT", "60"))
    )
    circuit_breaker_half_open_requests: int = field(
        default_factory=lambda: int(os.getenv("CIRCUIT_BREAKER_HALF_OPEN_REQUESTS", "3"))
    )


@dataclass
class IngestionConfig:
    """Document ingestion settings."""

    chunk_size: int = field(default_factory=lambda: int(os.getenv("CHUNK_SIZE", "1000")))
    chunk_overlap: int = field(default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "200")))
    max_entities_per_chunk: int = field(
        default_factory=lambda: int(os.getenv("MAX_ENTITIES_PER_CHUNK", "10"))
    )
    max_fact_length: int = field(default_factory=lambda: int(os.getenv("MAX_FACT_LENGTH", "500")))
    use_semantic_chunking: bool = field(
        default_factory=lambda: os.getenv("USE_SEMANTIC_CHUNKING", "true").lower() == "true"
    )


@dataclass
class APIConfig:
    """API server configuration."""

    host: str = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8058")))
    cors_origins: list[str] = field(
        default_factory=lambda: os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    )
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))


@dataclass
class Config:
    """Main configuration class combining all settings."""

    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    connection_pool: ConnectionPoolConfig = field(default_factory=ConnectionPoolConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)
    api: APIConfig = field(default_factory=APIConfig)

    def validate(self) -> list[str]:
        """
        Validate configuration and return list of errors.

        Returns:
            List of validation error messages
        """
        errors = []

        # Validate required database settings
        if not self.database.database_url and not self.database.supabase_url:
            errors.append("Either DATABASE_URL or SUPABASE_URL must be set")

        if self.performance.enable_graph and not self.database.neo4j_password:
            errors.append("NEO4J_PASSWORD is required when graph is enabled")

        # Validate embedding settings
        if not self.embedding.api_key:
            errors.append("EMBEDDING_API_KEY is required")

        # Validate LLM settings
        if not self.llm.api_key:
            errors.append("LLM_API_KEY is required")

        # Validate pool sizes
        if self.connection_pool.pg_pool_min > self.connection_pool.pg_pool_max:
            errors.append("PG_POOL_MIN cannot be greater than PG_POOL_MAX")

        # Validate cache settings
        if self.database.enable_redis_cache and not self.database.redis_url:
            errors.append("REDIS_URL is required when Redis cache is enabled")

        return errors

    def dict(self) -> dict:
        """
        Convert config to dictionary.

        Returns:
            Configuration as dictionary
        """
        return {
            "DATABASE_URL": self.database.database_url,
            "SUPABASE_URL": self.database.supabase_url,
            "SUPABASE_SERVICE_KEY": self.database.supabase_service_key,
            "NEO4J_URI": self.database.neo4j_uri,
            "NEO4J_USER": self.database.neo4j_user,
            "NEO4J_PASSWORD": self.database.neo4j_password,
            "NEO4J_DATABASE": self.database.neo4j_database,
            "NEO4J_ENCRYPTED": self.database.neo4j_encrypted,
            "REDIS_URL": self.database.redis_url,
            "ENABLE_REDIS_CACHE": self.database.enable_redis_cache,
            "PG_POOL_MIN": self.connection_pool.pg_pool_min,
            "PG_POOL_MAX": self.connection_pool.pg_pool_max,
            "NEO4J_POOL_SIZE": self.connection_pool.neo4j_pool_size,
            "REDIS_POOL_SIZE": self.connection_pool.redis_pool_size,
            "ENABLE_GRAPH": self.performance.enable_graph,
            "ENABLE_CACHING": self.performance.enable_caching,
            "ENABLE_PARALLEL_SEARCH": self.performance.enable_parallel_search,
        }


# Global configuration instance
config = Config()

# Validate on import
validation_errors = config.validate()
if validation_errors and config.api.app_env == "production":
    import warnings

    for error in validation_errors:
        warnings.warn(f"Configuration warning: {error}")


def get_config() -> Config:
    """
    Get the global configuration instance.

    Returns:
        Global configuration
    """
    return config


def reload_config():
    """Reload configuration from environment variables."""
    global config
    load_dotenv(override=True)
    config = Config()
    return config
