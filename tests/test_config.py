"""
Tests for centralized configuration system.

Validates settings loading, validation, and facade behavior.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.config import (
    EmbeddingProvider,
    Environment,
    LLMProvider,
    Settings,
    UIMode,
    WebSearchProvider,
    get_settings,
    reload_settings,
)
from src.config.agent import agent_config
from src.config.api import api_config
from src.config.clients import clients_config
from src.config.ui import ui_config


class TestSettings:
    """Test main Settings class."""

    def test_default_settings_load(self):
        """Test that default settings load correctly."""
        settings = Settings()

        # Check defaults
        assert settings.app_env == Environment.DEVELOPMENT
        assert settings.log_level == "INFO"
        assert settings.api_port == 8058
        assert settings.chunk_size == 1000
        assert settings.chunk_overlap == 200

    def test_env_var_override(self):
        """Test that environment variables override defaults."""
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "LOG_LEVEL": "DEBUG",
                "API_PORT": "9000",
                "CHUNK_SIZE": "2000",
            },
        ):
            settings = Settings()
            assert settings.app_env == Environment.PRODUCTION
            assert settings.log_level == "DEBUG"
            assert settings.api_port == 9000
            assert settings.chunk_size == 2000

    def test_database_validation(self):
        """Test database configuration validation."""
        with patch.dict(
            os.environ,
            {"APP_ENV": "production", "DATABASE_URL": "", "SUPABASE_URL": ""},
            clear=True,
        ):
            with pytest.raises(ValidationError) as exc:
                Settings()
            assert "Either DATABASE_URL or SUPABASE_URL must be set" in str(exc.value)

    def test_redis_validation(self):
        """Test Redis configuration validation."""
        with patch.dict(os.environ, {"ENABLE_REDIS_CACHE": "true", "REDIS_URL": ""}):
            with pytest.raises(ValidationError) as exc:
                Settings()
            assert "REDIS_URL is required when Redis cache is enabled" in str(exc.value)

    def test_pool_size_validation(self):
        """Test connection pool size validation."""
        with patch.dict(os.environ, {"PG_POOL_MIN": "50", "PG_POOL_MAX": "20"}):
            with pytest.raises(ValidationError) as exc:
                Settings()
            assert "PG_POOL_MIN cannot be greater than PG_POOL_MAX" in str(exc.value)

    def test_chunk_overlap_validation(self):
        """Test chunk overlap validation."""
        with patch.dict(os.environ, {"CHUNK_SIZE": "500", "CHUNK_OVERLAP": "600"}):
            with pytest.raises(ValidationError) as exc:
                Settings()
            assert "CHUNK_OVERLAP must be less than CHUNK_SIZE" in str(exc.value)

    def test_production_api_key_validation(self):
        """Test API key requirements in production."""
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "SUPABASE_URL": "https://test.supabase.co",
                "NEO4J_PASSWORD": "password",
                "EMBEDDING_API_KEY": "",
                "LLM_API_KEY": "",
            },
            clear=True,
        ):
            with pytest.raises(ValidationError) as exc:
                Settings()
            error_msg = str(exc.value)
            assert (
                "EMBEDDING_API_KEY is required in production" in error_msg
                or "LLM_API_KEY is required in production" in error_msg
            )

    def test_cors_origins_parsing(self):
        """Test CORS origins string parsing."""
        with patch.dict(
            os.environ,
            {"CORS_ORIGINS": "http://localhost:3000,http://localhost:8080,https://app.example.com"},
        ):
            settings = Settings()
            origins = settings.get_cors_origins_list()
            assert len(origins) == 3
            assert "http://localhost:3000" in origins
            assert "http://localhost:8080" in origins
            assert "https://app.example.com" in origins

    def test_enum_values(self):
        """Test that enum values are properly loaded."""
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "UI_MODE": "advanced",
                "LLM_PROVIDER": "anthropic",
                "EMBEDDING_PROVIDER": "ollama",
                "WEB_SEARCH_PROVIDER": "brave",
            },
        ):
            settings = Settings()
            assert settings.app_env == Environment.PRODUCTION
            assert settings.ui_mode == UIMode.ADVANCED
            assert settings.llm_provider == LLMProvider.ANTHROPIC
            assert settings.embedding_provider == EmbeddingProvider.OLLAMA
            assert settings.web_search_provider == WebSearchProvider.BRAVE

    def test_masked_sensitive_values(self):
        """Test that sensitive values are masked in dict output."""
        with patch.dict(
            os.environ,
            {
                "SUPABASE_SERVICE_KEY": "secret-key",
                "NEO4J_PASSWORD": "secret-pass",
                "EMBEDDING_API_KEY": "secret-api",
                "LLM_API_KEY": "secret-llm",
                "JINA_API_KEY": "secret-jina",
                "BRAVE_API_KEY": "secret-brave",
            },
        ):
            settings = Settings()
            data = settings.to_dict()

            assert data["supabase_service_key"] == "***MASKED***"
            assert data["neo4j_password"] == "***MASKED***"
            assert data["embedding_api_key"] == "***MASKED***"
            assert data["llm_api_key"] == "***MASKED***"
            assert data["jina_api_key"] == "***MASKED***"
            assert data["brave_api_key"] == "***MASKED***"

    def test_production_warnings(self):
        """Test production validation warnings."""
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "DEBUG": "true",
                "HOT_RELOAD": "true",
                "LOG_LEVEL": "DEBUG",
                "NEO4J_ENCRYPTED": "false",
                "LLM_TEMPERATURE": "1.5",
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_SERVICE_KEY": "key",
                "EMBEDDING_API_KEY": "key",
                "LLM_API_KEY": "key",
                "NEO4J_PASSWORD": "pass",
            },
        ):
            settings = Settings()
            warnings = settings.validate_for_production()

            assert "Debug mode is enabled in production" in warnings
            assert "Hot reload is enabled in production" in warnings
            assert "Debug logging is enabled in production" in warnings
            assert "Neo4j connection is not encrypted" in warnings
            assert any("temperature" in w for w in warnings)


class TestAPIConfig:
    """Test API configuration facade."""

    def test_api_config_properties(self):
        """Test API config property access."""
        with patch.dict(
            os.environ,
            {
                "API_HOST": "127.0.0.1",
                "API_PORT": "9000",
                "LOG_LEVEL": "WARNING",
                "DEBUG": "true",
                "HOT_RELOAD": "true",
            },
        ):
            reload_settings()  # Force reload to pick up env vars

            assert api_config.host == "127.0.0.1"
            assert api_config.port == 9000
            assert api_config.log_level == "WARNING"
            assert api_config.debug is True
            assert api_config.hot_reload is True

    def test_uvicorn_config(self):
        """Test Uvicorn configuration generation."""
        with patch.dict(
            os.environ,
            {
                "API_HOST": "0.0.0.0",  # nosec B104 - test config, binding to all interfaces is intentional
                "API_PORT": "8080",
                "HOT_RELOAD": "true",
                "LOG_LEVEL": "INFO",
                "DEBUG": "true",
            },
        ):
            reload_settings()

            config = api_config.get_uvicorn_config()
            assert config["host"] == "0.0.0.0"  # nosec B104 - test assertion
            assert config["port"] == 8080
            assert config["reload"] is True
            assert config["log_level"] == "info"
            assert config["access_log"] is True

    def test_cors_config(self):
        """Test CORS configuration generation."""
        with patch.dict(os.environ, {"CORS_ORIGINS": "http://app.local,https://app.prod"}):
            reload_settings()

            config = api_config.get_cors_config()
            assert "http://app.local" in config["allow_origins"]
            assert "https://app.prod" in config["allow_origins"]
            assert config["allow_credentials"] is True
            assert config["allow_methods"] == ["*"]
            assert config["allow_headers"] == ["*"]


class TestAgentConfig:
    """Test Agent configuration facade."""

    def test_agent_config_properties(self):
        """Test agent config property access."""
        with patch.dict(
            os.environ,
            {
                "LLM_MODEL": "claude-3-opus",
                "LLM_TEMPERATURE": "0.5",
                "LLM_MAX_TOKENS": "4000",
                "EXTRACTION_MODEL": "gpt-4",
                "ENABLE_GRAPH": "false",
            },
        ):
            reload_settings()

            assert agent_config.llm_model == "claude-3-opus"
            assert agent_config.llm_temperature == 0.5
            assert agent_config.llm_max_tokens == 4000
            assert agent_config.extraction_model == "gpt-4"
            assert agent_config.enable_graph is False

    def test_web_search_config(self):
        """Test web search configuration."""
        with patch.dict(
            os.environ,
            {
                "WEB_SEARCH_PROVIDER": "jina",
                "JINA_API_KEY": "jina-key",
                "BRAVE_API_KEY": "brave-key",
                "SEARXNG_BASE_URL": "http://searxng.local",
            },
        ):
            reload_settings()

            assert agent_config.web_search_provider == WebSearchProvider.JINA
            assert agent_config.jina_api_key == "jina-key"
            assert agent_config.brave_api_key == "brave-key"
            assert agent_config.searxng_base_url == "http://searxng.local"
            assert agent_config.has_web_search_configured() is True

    def test_search_config(self):
        """Test search configuration dictionary."""
        with patch.dict(
            os.environ,
            {
                "ENABLE_GRAPH": "true",
                "ENABLE_PARALLEL_SEARCH": "false",
                "VECTOR_SEARCH_TIMEOUT": "1.5",
                "GRAPH_SEARCH_TIMEOUT": "2.5",
            },
        ):
            reload_settings()

            config = agent_config.get_search_config()
            assert config["enable_graph"] is True
            assert config["enable_parallel"] is False
            assert config["vector_timeout"] == 1.5
            assert config["graph_timeout"] == 2.5


class TestClientsConfig:
    """Test Clients configuration facade."""

    def test_llm_client_config(self):
        """Test LLM client configuration."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "openai",
                "LLM_BASE_URL": "https://api.openai.com/v1",
                "LLM_API_KEY": "sk-test",
                "LLM_MODEL": "gpt-4",
            },
        ):
            reload_settings()

            assert clients_config.llm_provider == LLMProvider.OPENAI
            assert clients_config.llm_base_url == "https://api.openai.com/v1"
            assert clients_config.llm_api_key == "sk-test"
            assert clients_config.llm_model == "gpt-4"

    def test_embedding_client_config(self):
        """Test embedding client configuration."""
        with patch.dict(
            os.environ,
            {
                "EMBEDDING_PROVIDER": "openai",
                "EMBEDDING_BASE_URL": "https://api.openai.com/v1",
                "EMBEDDING_API_KEY": "sk-embed",
                "EMBEDDING_MODEL": "text-embedding-ada-002",
                "EMBEDDING_DIMENSION": "1536",
            },
        ):
            reload_settings()

            assert clients_config.embedding_provider == EmbeddingProvider.OPENAI
            assert clients_config.embedding_base_url == "https://api.openai.com/v1"
            assert clients_config.embedding_api_key == "sk-embed"
            assert clients_config.embedding_model == "text-embedding-ada-002"
            assert clients_config.embedding_dimension == 1536

    def test_database_config(self):
        """Test database configuration."""
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql://user:pass@localhost/db",
                "SUPABASE_URL": "https://project.supabase.co",
                "SUPABASE_SERVICE_KEY": "service-key",
                "NEO4J_URI": "bolt://neo4j:7687",
                "NEO4J_USER": "neo4j_user",
                "NEO4J_PASSWORD": "neo4j_pass",
            },
        ):
            reload_settings()

            assert clients_config.database_url == "postgresql://user:pass@localhost/db"
            assert clients_config.supabase_url == "https://project.supabase.co"
            assert clients_config.supabase_service_key == "service-key"
            assert clients_config.neo4j_uri == "bolt://neo4j:7687"
            assert clients_config.neo4j_user == "neo4j_user"
            assert (
                clients_config.neo4j_password == "neo4j_pass"
            )  # nosec B105 - test data, not a real password


class TestUIConfig:
    """Test UI configuration facade."""

    def test_ui_mode_properties(self):
        """Test UI mode properties."""
        with patch.dict(os.environ, {"UI_MODE": "simple"}):
            reload_settings()
            assert ui_config.mode == UIMode.SIMPLE
            assert ui_config.is_simple_mode is True
            assert ui_config.is_standard_mode is False
            assert ui_config.is_advanced_mode is False

        with patch.dict(os.environ, {"UI_MODE": "advanced"}):
            reload_settings()
            assert ui_config.mode == UIMode.ADVANCED
            assert ui_config.is_simple_mode is False
            assert ui_config.is_standard_mode is False
            assert ui_config.is_advanced_mode is True

    def test_feature_flags(self):
        """Test UI feature flags based on mode."""
        with patch.dict(os.environ, {"UI_MODE": "simple"}):
            reload_settings()
            assert ui_config.enable_persistence is False
            assert ui_config.enable_advanced_features is False
            assert ui_config.show_metrics is False
            assert ui_config.show_export is False

        with patch.dict(os.environ, {"UI_MODE": "advanced"}):
            reload_settings()
            assert ui_config.enable_persistence is True
            assert ui_config.enable_advanced_features is True
            assert ui_config.show_metrics is True
            assert ui_config.show_export is True

    def test_page_config(self):
        """Test Streamlit page configuration."""
        with patch.dict(os.environ, {"UI_MODE": "advanced"}):
            reload_settings()

            config = ui_config.get_page_config()
            assert "Advanced" in config["page_title"]
            assert config["page_icon"] == "🤖"
            assert config["layout"] == "wide"
            assert config["initial_sidebar_state"] == "expanded"


class TestSettingsSingleton:
    """Test settings singleton behavior."""

    def test_singleton_caching(self):
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_reload_settings(self):
        """Test settings reload functionality."""
        settings1 = get_settings()

        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}):
            settings2 = reload_settings()
            settings3 = get_settings()

            assert settings2 is not settings1
            assert settings2 is settings3
            assert settings3.log_level == "ERROR"
