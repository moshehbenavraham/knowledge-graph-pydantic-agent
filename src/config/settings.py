"""
Centralized configuration management using Pydantic Settings.

This module provides a single source of truth for all configuration values,
with automatic validation, type conversion, and environment variable loading.
"""

from enum import Enum
from functools import lru_cache
from typing import Any

import structlog
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = structlog.get_logger(__name__)


class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class UIMode(str, Enum):
    """UI display modes."""

    SIMPLE = "simple"
    STANDARD = "standard"
    ADVANCED = "advanced"


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""

    OPENAI = "openai"
    NOMIC = "nomic"
    OLLAMA = "ollama"
    COHERE = "cohere"


class WebSearchProvider(str, Enum):
    """Supported web search providers."""

    JINA = "jina"
    BRAVE = "brave"
    SEARXNG = "searxng"


class SearchStrategy(str, Enum):
    """Search strategy types."""

    VECTOR_ONLY = "vector_only"
    GRAPH_ONLY = "graph_only"
    HYBRID = "hybrid"
    ADAPTIVE = "adaptive"
    SMART = "smart"


class ChunkingStrategy(str, Enum):
    """Document chunking strategies."""

    SEMANTIC = "semantic"
    SIMPLE = "simple"
    AUTO = "auto"


class Settings(BaseSettings):
    """
    Main configuration class with all application settings.

    Loads from environment variables with automatic validation.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Environment
    app_env: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    debug: bool = Field(
        default=False,
        description="Debug mode flag",
    )
    app_version: str = Field(
        default="0.1.0",
        description="Application version",
    )

    # Database Configuration - PostgreSQL/Supabase
    database_url: str | None = Field(
        default=None,
        description="PostgreSQL database URL",
    )
    supabase_url: str | None = Field(
        default=None,
        description="Supabase project URL",
    )
    supabase_service_key: str | None = Field(
        default=None,
        description="Supabase service role key",
    )

    # Database Configuration - Neo4j
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI",
    )
    neo4j_user: str = Field(
        default="neo4j",
        description="Neo4j username",
    )
    neo4j_password: str = Field(
        default="",
        description="Neo4j password",
    )
    neo4j_database: str = Field(
        default="neo4j",
        description="Neo4j database name",
    )
    neo4j_encrypted: bool = Field(
        default=True,
        description="Use encrypted Neo4j connection",
    )

    # Database Configuration - Redis
    redis_url: str | None = Field(
        default=None,
        description="Redis connection URL",
    )
    enable_redis_cache: bool = Field(
        default=False,
        description="Enable Redis caching",
    )

    # Connection Pool Settings - PostgreSQL
    pg_pool_min: int = Field(
        default=5,
        ge=1,
        description="Minimum PostgreSQL pool size",
    )
    pg_pool_max: int = Field(
        default=20,
        ge=1,
        description="Maximum PostgreSQL pool size",
    )
    pg_max_queries: int = Field(
        default=50000,
        ge=100,
        description="Maximum queries before connection reset",
    )
    pg_max_inactive_lifetime: int = Field(
        default=300,
        ge=10,
        description="Maximum inactive connection lifetime (seconds)",
    )
    pg_command_timeout: int = Field(
        default=60,
        ge=5,
        description="PostgreSQL command timeout (seconds)",
    )

    # Connection Pool Settings - Neo4j
    neo4j_pool_size: int = Field(
        default=50,
        ge=1,
        description="Neo4j connection pool size",
    )
    neo4j_connection_timeout: float = Field(
        default=30.0,
        gt=0,
        description="Neo4j connection timeout (seconds)",
    )
    neo4j_max_retry_time: int = Field(
        default=30,
        ge=1,
        description="Neo4j maximum retry time (seconds)",
    )

    # Connection Pool Settings - Redis
    redis_pool_size: int = Field(
        default=10,
        ge=1,
        description="Redis connection pool size",
    )
    redis_socket_timeout: int = Field(
        default=5,
        ge=1,
        description="Redis socket timeout (seconds)",
    )

    # Embedding Configuration
    embedding_provider: EmbeddingProvider = Field(
        default=EmbeddingProvider.OPENAI,
        description="Embedding model provider",
    )
    embedding_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="Embedding API base URL",
    )
    embedding_api_key: str = Field(
        default="",
        description="Embedding API key",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model name",
    )
    embedding_model_choice: str | None = Field(
        default=None,
        description="Alternative embedding model choice (legacy)",
    )
    embedding_dimension: int = Field(
        default=1536,
        gt=0,
        description="Embedding vector dimension",
    )
    embedding_batch_size: int = Field(
        default=100,
        ge=1,
        le=2048,
        description="Embedding batch size",
    )

    # LLM Configuration
    llm_provider: LLMProvider = Field(
        default=LLMProvider.OPENAI,
        description="LLM provider",
    )
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="LLM API base URL",
    )
    llm_api_key: str = Field(
        default="",
        description="LLM API key",
    )
    llm_model: str = Field(
        default="gpt-4o-mini",
        description="LLM model name",
    )
    llm_choice: str | None = Field(
        default=None,
        description="Alternative LLM model choice (legacy)",
    )
    extraction_model: str = Field(
        default="gpt-4o-mini",
        description="Model for knowledge extraction",
    )
    llm_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM temperature setting",
    )
    llm_max_tokens: int = Field(
        default=2000,
        ge=1,
        le=128000,
        description="Maximum tokens for LLM response",
    )
    vision_llm_choice: str = Field(
        default="gpt-4o-mini",
        description="LLM model for vision tasks",
    )

    # Performance Settings
    vector_search_timeout: float = Field(
        default=2.0,
        gt=0,
        description="Vector search timeout (seconds)",
    )
    graph_search_timeout: float = Field(
        default=3.0,
        gt=0,
        description="Graph search timeout (seconds)",
    )
    enable_caching: bool = Field(
        default=True,
        description="Enable caching",
    )
    embedding_cache_size: int = Field(
        default=1000,
        ge=0,
        description="Embedding cache size",
    )
    embedding_cache_ttl: int = Field(
        default=3600,
        ge=0,
        description="Embedding cache TTL (seconds)",
    )
    graph_cache_size: int = Field(
        default=500,
        ge=0,
        description="Graph cache size",
    )
    graph_cache_ttl: int = Field(
        default=1800,
        ge=0,
        description="Graph cache TTL (seconds)",
    )

    # Feature Flags
    enable_graph: bool = Field(
        default=True,
        description="Enable graph database features",
    )
    enable_parallel_search: bool = Field(
        default=True,
        description="Enable parallel search execution",
    )
    enable_tracing: bool = Field(
        default=False,
        description="Enable OpenTelemetry tracing",
    )
    hot_reload: bool = Field(
        default=False,
        description="Enable hot reload for development",
    )

    # Ingestion Settings
    chunk_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Document chunk size",
    )
    chunk_overlap: int = Field(
        default=200,
        ge=0,
        description="Chunk overlap size",
    )
    max_entities_per_chunk: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum entities per chunk",
    )
    max_fact_length: int = Field(
        default=500,
        ge=50,
        le=2000,
        description="Maximum fact length",
    )
    use_semantic_chunking: bool = Field(
        default=True,
        description="Use semantic chunking",
    )
    graph_batch_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Graph operation batch size",
    )

    # API Configuration
    api_host: str = Field(
        default="0.0.0.0",  # nosec B104 - Binding to all interfaces is required for containerized deployment
        description="API server host",
    )
    api_port: int = Field(
        default=8058,
        ge=1,
        le=65535,
        description="API server port",
    )
    cors_origins: str = Field(
        default="http://localhost:3000",
        description="CORS allowed origins (comma-separated)",
    )

    # Monitoring & Health Check Configuration
    enable_metrics: bool = Field(
        default=True,
        description="Enable Prometheus metrics",
    )
    metrics_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Prometheus metrics server port",
    )
    health_check_interval: int = Field(
        default=30,
        ge=5,
        description="Health check interval (seconds)",
    )

    # UI Configuration
    ui_mode: UIMode = Field(
        default=UIMode.STANDARD,
        description="UI display mode",
    )

    # Web Search Configuration
    web_search_provider: WebSearchProvider | None = Field(
        default=None,
        description="Preferred web search provider",
    )
    jina_api_key: str | None = Field(
        default=None,
        description="Jina.ai API key",
    )
    brave_api_key: str | None = Field(
        default=None,
        description="Brave Search API key",
    )
    searxng_base_url: str | None = Field(
        default=None,
        description="SearXNG instance URL",
    )

    # Circuit Breaker Settings
    circuit_breaker_failure_threshold: int = Field(
        default=5,
        ge=1,
        description="Failures before circuit opens",
    )
    circuit_breaker_recovery_timeout: int = Field(
        default=60,
        ge=10,
        description="Circuit breaker recovery timeout (seconds)",
    )
    circuit_breaker_half_open_requests: int = Field(
        default=3,
        ge=1,
        description="Requests allowed in half-open state",
    )

    # Tracing Configuration (Jaeger)
    jaeger_host: str = Field(
        default="localhost",
        description="Jaeger agent host",
    )
    jaeger_port: int = Field(
        default=6831,
        description="Jaeger agent port",
    )

    # Authentication Configuration
    use_database_auth: bool = Field(
        default=False,
        description="Use database authentication instead of YAML",
    )
    auth_cookie_key: str | None = Field(
        default=None,
        description="Authentication cookie encryption key",
    )

    # Email Configuration
    email_enabled: bool = Field(
        default=False,
        description="Enable email functionality",
    )
    email_provider: str = Field(
        default="smtp",
        description="Email provider (smtp, sendgrid, mailgun, supabase)",
    )
    password_reset_url: str = Field(
        default="http://localhost:8501",
        description="Base URL for password reset page",
    )
    verification_url: str = Field(
        default="http://localhost:8501",
        description="Base URL for email verification page",
    )
    smtp_host: str = Field(
        default="smtp.gmail.com",
        description="SMTP server host",
    )
    smtp_port: int = Field(
        default=587,
        ge=1,
        le=65535,
        description="SMTP server port",
    )
    smtp_user: str = Field(
        default="",
        description="SMTP username",
    )
    smtp_password: str = Field(
        default="",
        description="SMTP password",
    )
    smtp_from_email: str = Field(
        default="max@aiwithapex.com",
        description="SMTP from email address",
    )

    # OAuth Configuration
    oauth_enabled: bool = Field(
        default=False,
        description="Enable OAuth authentication",
    )
    oauth_encryption_key: str | None = Field(
        default=None,
        description="OAuth token encryption key (Fernet key)",
    )

    # Google OAuth
    google_client_id: str | None = Field(
        default=None,
        description="Google OAuth client ID",
    )
    google_client_secret: str | None = Field(
        default=None,
        description="Google OAuth client secret",
    )
    google_redirect_uri: str | None = Field(
        default=None,
        description="Google OAuth redirect URI",
    )

    # GitHub OAuth
    github_client_id: str | None = Field(
        default=None,
        description="GitHub OAuth client ID",
    )
    github_client_secret: str | None = Field(
        default=None,
        description="GitHub OAuth client secret",
    )
    github_redirect_uri: str | None = Field(
        default=None,
        description="GitHub OAuth redirect URI",
    )

    # Microsoft OAuth
    microsoft_client_id: str | None = Field(
        default=None,
        description="Microsoft OAuth client ID",
    )
    microsoft_client_secret: str | None = Field(
        default=None,
        description="Microsoft OAuth client secret",
    )
    microsoft_redirect_uri: str | None = Field(
        default=None,
        description="Microsoft OAuth redirect URI",
    )

    # Apple OAuth
    apple_client_id: str | None = Field(
        default=None,
        description="Apple OAuth client ID",
    )
    apple_client_secret: str | None = Field(
        default=None,
        description="Apple OAuth client secret",
    )
    apple_redirect_uri: str | None = Field(
        default=None,
        description="Apple OAuth redirect URI",
    )

    @field_validator("llm_choice")
    @classmethod
    def sync_llm_choice(cls, v: str | None) -> str | None:
        """Sync llm_choice with llm_model for backward compatibility."""
        # Field validators in Pydantic v2 don't have access to other fields
        # This will be handled in model_validator instead
        return v

    @field_validator("embedding_model_choice")
    @classmethod
    def sync_embedding_choice(cls, v: str | None) -> str | None:
        """Sync embedding_model_choice with embedding_model for backward compatibility."""
        # Field validators in Pydantic v2 don't have access to other fields
        # This will be handled in model_validator instead
        return v

    @model_validator(mode="after")
    def sync_legacy_fields(self) -> "Settings":
        """Sync legacy field names for backward compatibility."""
        if self.llm_choice is None and self.llm_model:
            self.llm_choice = self.llm_model
        if self.embedding_model_choice is None and self.embedding_model:
            self.embedding_model_choice = self.embedding_model
        return self

    @model_validator(mode="after")
    def validate_database_config(self) -> "Settings":
        """Validate database configuration."""
        if not self.database_url and not self.supabase_url:
            if self.app_env == Environment.PRODUCTION:
                raise ValueError("Either DATABASE_URL or SUPABASE_URL must be set in production")

        if self.enable_redis_cache and not self.redis_url:
            raise ValueError("REDIS_URL is required when Redis cache is enabled")

        if self.enable_graph and not self.neo4j_password:
            if self.app_env == Environment.PRODUCTION:
                raise ValueError("NEO4J_PASSWORD is required when graph is enabled in production")

        return self

    @model_validator(mode="after")
    def validate_pool_sizes(self) -> "Settings":
        """Validate connection pool settings."""
        if self.pg_pool_min > self.pg_pool_max:
            raise ValueError("PG_POOL_MIN cannot be greater than PG_POOL_MAX")

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be less than CHUNK_SIZE")

        return self

    @model_validator(mode="after")
    def validate_api_keys(self) -> "Settings":
        """Validate required API keys for production."""
        if self.app_env == Environment.PRODUCTION:
            if not self.embedding_api_key:
                raise ValueError("EMBEDDING_API_KEY is required in production")
            if not self.llm_api_key:
                raise ValueError("LLM_API_KEY is required in production")

        return self

    def get_cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return self.cors_origins

    def get_effective_llm_model(self) -> str:
        """Get the effective LLM model name."""
        return self.llm_choice or self.llm_model

    def get_effective_embedding_model(self) -> str:
        """Get the effective embedding model name."""
        return self.embedding_model_choice or self.embedding_model

    def to_dict(self, mask_sensitive: bool = True) -> dict[str, Any]:
        """
        Convert settings to dictionary.

        Args:
            mask_sensitive: If True, mask sensitive values for logging/debugging.
                           If False, return actual values for internal use.

        Returns:
            Settings as dictionary
        """
        data = self.model_dump()

        if mask_sensitive:
            # Mask sensitive values for logging/debugging
            sensitive_keys = [
                "supabase_service_key",
                "neo4j_password",
                "embedding_api_key",
                "llm_api_key",
                "jina_api_key",
                "brave_api_key",
                "auth_cookie_key",
                "smtp_password",
                "oauth_encryption_key",
                "google_client_secret",
                "github_client_secret",
                "microsoft_client_secret",
                "apple_client_secret",
            ]
            for key in sensitive_keys:
                if data.get(key):
                    data[key] = "***MASKED***"

        return data

    def validate_for_production(self) -> list[str]:
        """
        Additional production validation.

        Returns:
            List of warning messages
        """
        warnings = []

        if self.debug:
            warnings.append("Debug mode is enabled in production")

        if self.hot_reload:
            warnings.append("Hot reload is enabled in production")

        if self.log_level == "DEBUG":
            warnings.append("Debug logging is enabled in production")

        if not self.neo4j_encrypted:
            warnings.append("Neo4j connection is not encrypted")

        if self.llm_temperature > 1.0:
            warnings.append(
                f"High LLM temperature ({self.llm_temperature}) may produce inconsistent results"
            )

        return warnings


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance (singleton pattern).

    Returns:
        Settings instance
    """
    logger.info("Getting settings (cached)")
    return Settings()


def reload_settings() -> Settings:
    """
    Force reload settings from environment.

    Returns:
        Fresh Settings instance
    """
    logger.info("Reloading settings from environment")
    get_settings.cache_clear()
    return get_settings()
