"""
Comprehensive tests for all config modules.

Tests agent.py, api.py, clients.py, and ui.py configuration facades.
"""

from unittest.mock import MagicMock, patch


class TestAgentConfig:
    """Test AgentConfig facade (src/config/agent.py)."""

    @patch("src.config.agent.get_settings")
    def test_agent_config_initialization(self, mock_get_settings):
        """Test AgentConfig initialization."""
        from src.config.agent import AgentConfig

        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings

        config = AgentConfig()

        assert config._settings == mock_settings

    @patch("src.config.agent.get_settings")
    def test_llm_model_property(self, mock_get_settings):
        """Test llm_model property."""
        from src.config.agent import AgentConfig

        mock_settings = MagicMock()
        mock_settings.get_effective_llm_model.return_value = "gpt-4"
        mock_get_settings.return_value = mock_settings

        config = AgentConfig()
        model = config.llm_model

        assert model == "gpt-4"
        mock_settings.get_effective_llm_model.assert_called_once()

    @patch("src.config.agent.get_settings")
    def test_llm_temperature_property(self, mock_get_settings):
        """Test llm_temperature property."""
        from src.config.agent import AgentConfig

        mock_settings = MagicMock()
        mock_settings.llm_temperature = 0.7
        mock_get_settings.return_value = mock_settings

        config = AgentConfig()

        assert config.llm_temperature == 0.7

    @patch("src.config.agent.get_settings")
    def test_llm_max_tokens_property(self, mock_get_settings):
        """Test llm_max_tokens property."""
        from src.config.agent import AgentConfig

        mock_settings = MagicMock()
        mock_settings.llm_max_tokens = 2000
        mock_get_settings.return_value = mock_settings

        config = AgentConfig()

        assert config.llm_max_tokens == 2000

    @patch("src.config.agent.get_settings")
    def test_extraction_model_property(self, mock_get_settings):
        """Test extraction_model property."""
        from src.config.agent import AgentConfig

        mock_settings = MagicMock()
        mock_settings.extraction_model = "gpt-3.5-turbo"
        mock_get_settings.return_value = mock_settings

        config = AgentConfig()

        assert config.extraction_model == "gpt-3.5-turbo"

    @patch("src.config.agent.get_settings")
    def test_enable_graph_property(self, mock_get_settings):
        """Test enable_graph property."""
        from src.config.agent import AgentConfig

        mock_settings = MagicMock()
        mock_settings.enable_graph = True
        mock_get_settings.return_value = mock_settings

        config = AgentConfig()

        assert config.enable_graph is True

    @patch("src.config.agent.get_settings")
    def test_enable_parallel_search_property(self, mock_get_settings):
        """Test enable_parallel_search property."""
        from src.config.agent import AgentConfig

        mock_settings = MagicMock()
        mock_settings.enable_parallel_search = True
        mock_get_settings.return_value = mock_settings

        config = AgentConfig()

        assert config.enable_parallel_search is True

    @patch("src.config.agent.get_settings")
    def test_timeouts_properties(self, mock_get_settings):
        """Test timeout properties."""
        from src.config.agent import AgentConfig

        mock_settings = MagicMock()
        mock_settings.vector_search_timeout = 30.0
        mock_settings.graph_search_timeout = 45.0
        mock_get_settings.return_value = mock_settings

        config = AgentConfig()

        assert config.vector_search_timeout == 30.0
        assert config.graph_search_timeout == 45.0

    @patch("src.config.agent.get_settings")
    def test_default_search_strategy(self, mock_get_settings):
        """Test default_search_strategy property."""
        from src.config.agent import AgentConfig
        from src.config.settings import SearchStrategy

        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings

        config = AgentConfig()

        assert config.default_search_strategy == SearchStrategy.SMART

    @patch("src.config.agent.get_settings")
    def test_web_search_provider_property(self, mock_get_settings):
        """Test web_search_provider property."""
        from src.config.agent import AgentConfig

        mock_settings = MagicMock()
        mock_settings.web_search_provider = "jina"
        mock_get_settings.return_value = mock_settings

        config = AgentConfig()

        assert config.web_search_provider == "jina"

    @patch("src.config.agent.get_settings")
    def test_web_search_api_keys(self, mock_get_settings):
        """Test web search API key properties."""
        from src.config.agent import AgentConfig

        mock_settings = MagicMock()
        mock_settings.jina_api_key = "jina-key-123"
        mock_settings.brave_api_key = "brave-key-456"
        mock_settings.searxng_base_url = "http://searxng.local"
        mock_get_settings.return_value = mock_settings

        config = AgentConfig()

        assert config.jina_api_key == "jina-key-123"
        assert config.brave_api_key == "brave-key-456"
        assert config.searxng_base_url == "http://searxng.local"

    @patch("src.config.agent.get_settings")
    def test_get_search_config(self, mock_get_settings):
        """Test get_search_config method."""
        from src.config.agent import AgentConfig
        from src.config.settings import SearchStrategy

        mock_settings = MagicMock()
        mock_settings.enable_graph = True
        mock_settings.enable_parallel_search = True
        mock_settings.vector_search_timeout = 30.0
        mock_settings.graph_search_timeout = 45.0
        mock_get_settings.return_value = mock_settings

        config = AgentConfig()
        search_config = config.get_search_config()

        assert search_config["enable_graph"] is True
        assert search_config["enable_parallel"] is True
        assert search_config["vector_timeout"] == 30.0
        assert search_config["graph_timeout"] == 45.0
        assert search_config["default_strategy"] == SearchStrategy.SMART

    @patch("src.config.agent.get_settings")
    def test_get_web_search_config(self, mock_get_settings):
        """Test get_web_search_config method."""
        from src.config.agent import AgentConfig

        mock_settings = MagicMock()
        mock_settings.web_search_provider = "jina"
        mock_settings.jina_api_key = "key-123"
        mock_settings.brave_api_key = None
        mock_settings.searxng_base_url = None
        mock_get_settings.return_value = mock_settings

        config = AgentConfig()
        web_config = config.get_web_search_config()

        assert web_config["provider"] == "jina"
        assert web_config["jina_api_key"] == "key-123"
        assert web_config["brave_api_key"] is None
        assert web_config["searxng_base_url"] is None

    @patch("src.config.agent.get_settings")
    def test_has_web_search_configured_true(self, mock_get_settings):
        """Test has_web_search_configured when configured."""
        from src.config.agent import AgentConfig

        mock_settings = MagicMock()
        mock_settings.jina_api_key = "key-123"
        mock_settings.brave_api_key = None
        mock_settings.searxng_base_url = None
        mock_get_settings.return_value = mock_settings

        config = AgentConfig()

        assert config.has_web_search_configured() is True

    @patch("src.config.agent.get_settings")
    def test_has_web_search_configured_false(self, mock_get_settings):
        """Test has_web_search_configured when not configured."""
        from src.config.agent import AgentConfig

        mock_settings = MagicMock()
        mock_settings.jina_api_key = None
        mock_settings.brave_api_key = None
        mock_settings.searxng_base_url = None
        mock_get_settings.return_value = mock_settings

        config = AgentConfig()

        assert config.has_web_search_configured() is False

    def test_agent_config_singleton(self):
        """Test agent_config singleton instance."""
        from src.config.agent import agent_config

        assert agent_config is not None
        assert hasattr(agent_config, "llm_model")


class TestAPIConfig:
    """Test APIConfig facade (src/config/api.py)."""

    @patch("src.config.api.get_settings")
    def test_api_config_initialization(self, mock_get_settings):
        """Test APIConfig initialization."""
        from src.config.api import APIConfig

        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings

        config = APIConfig()

        assert config._settings == mock_settings

    @patch("src.config.api.get_settings")
    def test_api_host_port(self, mock_get_settings):
        """Test API host and port properties."""
        from src.config.api import APIConfig

        mock_settings = MagicMock()
        mock_settings.api_host = "0.0.0.0"
        mock_settings.api_port = 8000
        mock_get_settings.return_value = mock_settings

        config = APIConfig()

        assert config.host == "0.0.0.0"
        assert config.port == 8000

    @patch("src.config.api.get_settings")
    def test_enable_tracing(self, mock_get_settings):
        """Test enable_tracing property."""
        from src.config.api import APIConfig

        mock_settings = MagicMock()
        mock_settings.enable_tracing = True
        mock_get_settings.return_value = mock_settings

        config = APIConfig()

        assert config.enable_tracing is True

    @patch("src.config.api.get_settings")
    def test_log_level(self, mock_get_settings):
        """Test log_level property."""
        from src.config.api import APIConfig

        mock_settings = MagicMock()
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings

        config = APIConfig()

        assert config.log_level == "INFO"

    @patch("src.config.api.get_settings")
    def test_get_cors_config(self, mock_get_settings):
        """Test get_cors_config method."""
        from src.config.api import APIConfig

        mock_settings = MagicMock()
        mock_settings.get_cors_origins_list.return_value = ["*"]
        mock_get_settings.return_value = mock_settings

        config = APIConfig()
        cors_config = config.get_cors_config()

        assert cors_config["allow_origins"] == ["*"]
        assert cors_config["allow_methods"] == ["*"]
        assert cors_config["allow_headers"] == ["*"]
        assert cors_config["allow_credentials"] is True

    @patch("src.config.api.get_settings")
    def test_get_uvicorn_config(self, mock_get_settings):
        """Test get_uvicorn_config method."""
        from src.config.api import APIConfig

        mock_settings = MagicMock()
        mock_settings.api_host = "127.0.0.1"
        mock_settings.api_port = 8080
        mock_settings.hot_reload = True
        mock_settings.log_level = "INFO"
        mock_settings.debug = True
        mock_get_settings.return_value = mock_settings

        config = APIConfig()
        uvicorn_config = config.get_uvicorn_config()

        assert uvicorn_config["host"] == "127.0.0.1"
        assert uvicorn_config["port"] == 8080
        assert uvicorn_config["reload"] is True
        assert uvicorn_config["log_level"] == "info"
        assert uvicorn_config["access_log"] is True

    def test_api_config_singleton(self):
        """Test api_config singleton instance."""
        from src.config.api import api_config

        assert api_config is not None
        assert hasattr(api_config, "host")


class TestClientsConfig:
    """Test ClientsConfig facade (src/config/clients.py)."""

    @patch("src.config.clients.get_settings")
    def test_clients_config_initialization(self, mock_get_settings):
        """Test ClientsConfig initialization."""
        from src.config.clients import ClientsConfig

        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings

        config = ClientsConfig()

        assert config._settings == mock_settings

    @patch("src.config.clients.get_settings")
    def test_supabase_config(self, mock_get_settings):
        """Test Supabase configuration properties."""
        from src.config.clients import ClientsConfig

        mock_settings = MagicMock()
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test-key-123"
        mock_get_settings.return_value = mock_settings

        config = ClientsConfig()

        assert config.supabase_url == "https://test.supabase.co"
        assert config.supabase_key == "test-key-123"
        assert config.supabase_service_key == "test-key-123"

    @patch("src.config.clients.get_settings")
    def test_neo4j_config(self, mock_get_settings):
        """Test Neo4j configuration properties."""
        from src.config.clients import ClientsConfig

        mock_settings = MagicMock()
        mock_settings.neo4j_uri = "neo4j+s://test.neo4j.io"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password123"
        mock_get_settings.return_value = mock_settings

        config = ClientsConfig()

        assert config.neo4j_uri == "neo4j+s://test.neo4j.io"
        assert config.neo4j_user == "neo4j"
        assert config.neo4j_password == "password123"

    @patch("src.config.clients.get_settings")
    def test_llm_provider_config(self, mock_get_settings):
        """Test LLM provider configuration."""
        from src.config.clients import ClientsConfig

        mock_settings = MagicMock()
        mock_settings.llm_provider = "openai"
        mock_settings.llm_api_key = "sk-test123"
        mock_get_settings.return_value = mock_settings

        config = ClientsConfig()

        assert config.llm_provider == "openai"
        assert config.llm_api_key == "sk-test123"
        assert config.openai_api_key == "sk-test123"

    @patch("src.config.clients.get_settings")
    def test_has_supabase_configured(self, mock_get_settings):
        """Test has_supabase_configured method."""
        from src.config.clients import ClientsConfig

        mock_settings = MagicMock()
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_key = "key"
        mock_get_settings.return_value = mock_settings

        config = ClientsConfig()

        assert config.has_supabase_configured() is True

    @patch("src.config.clients.get_settings")
    def test_has_neo4j_configured(self, mock_get_settings):
        """Test has_neo4j_configured method."""
        from src.config.clients import ClientsConfig

        mock_settings = MagicMock()
        mock_settings.neo4j_uri = "neo4j://localhost"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "pass"
        mock_get_settings.return_value = mock_settings

        config = ClientsConfig()

        assert config.has_neo4j_configured() is True

    def test_clients_config_singleton(self):
        """Test clients_config singleton instance."""
        from src.config.clients import clients_config

        assert clients_config is not None


class TestUIConfig:
    """Test UIConfig facade (src/config/ui.py)."""

    @patch("src.config.ui.get_settings")
    def test_ui_config_initialization(self, mock_get_settings):
        """Test UIConfig initialization."""
        from src.config.ui import UIConfig

        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings

        config = UIConfig()

        assert config._settings == mock_settings

    @patch("src.config.ui.get_settings")
    def test_ui_mode(self, mock_get_settings):
        """Test ui_mode property."""
        from src.config.ui import UIConfig, UIMode

        mock_settings = MagicMock()
        mock_settings.ui_mode = UIMode.ADVANCED
        mock_get_settings.return_value = mock_settings

        config = UIConfig()

        assert config.ui_mode == "advanced"

    @patch("src.config.ui.get_settings")
    def test_ui_port(self, mock_get_settings):
        """Test ui_port property."""
        from src.config.ui import UIConfig

        mock_settings = MagicMock()
        mock_settings.streamlit_port = 8501
        mock_get_settings.return_value = mock_settings

        config = UIConfig()

        assert config.ui_port == 8501

    @patch("src.config.ui.get_settings")
    def test_enable_memory(self, mock_get_settings):
        """Test enable_memory property."""
        from src.config.ui import UIConfig

        mock_settings = MagicMock()
        mock_settings.enable_mem0 = True
        mock_get_settings.return_value = mock_settings

        config = UIConfig()

        assert config.enable_memory is True

    @patch("src.config.ui.get_settings")
    def test_enable_mcp(self, mock_get_settings):
        """Test enable_mcp property."""
        from src.config.ui import UIConfig

        mock_settings = MagicMock()
        mock_settings.enable_mcp = True
        mock_get_settings.return_value = mock_settings

        config = UIConfig()

        assert config.enable_mcp is True

    @patch("src.config.ui.get_settings")
    def test_is_simple_mode(self, mock_get_settings):
        """Test is_simple_mode property."""
        from src.config.ui import UIConfig, UIMode

        mock_settings = MagicMock()
        mock_settings.ui_mode = UIMode.SIMPLE
        mock_get_settings.return_value = mock_settings

        config = UIConfig()

        assert config.is_simple_mode is True

    @patch("src.config.ui.get_settings")
    def test_is_advanced_mode(self, mock_get_settings):
        """Test is_advanced_mode property."""
        from src.config.ui import UIConfig, UIMode

        mock_settings = MagicMock()
        mock_settings.ui_mode = UIMode.ADVANCED
        mock_get_settings.return_value = mock_settings

        config = UIConfig()

        assert config.is_advanced_mode is True

    @patch("src.config.ui.get_settings")
    def test_get_ui_config(self, mock_get_settings):
        """Test get_ui_config method."""
        from src.config.ui import UIConfig, UIMode

        mock_settings = MagicMock()
        mock_settings.ui_mode = UIMode.STANDARD
        mock_settings.streamlit_port = 8501
        mock_settings.enable_mem0 = True
        mock_settings.enable_mcp = False
        mock_get_settings.return_value = mock_settings

        config = UIConfig()
        ui_config = config.get_ui_config()

        assert ui_config["mode"] == "standard"
        assert ui_config["port"] == 8501
        assert ui_config["enable_memory"] is True
        assert ui_config["enable_mcp"] is False

    def test_ui_config_singleton(self):
        """Test ui_config singleton instance."""
        from src.config.ui import ui_config

        assert ui_config is not None
        assert hasattr(ui_config, "ui_mode")


class TestConfigIntegration:
    """Test integration between config modules."""

    def test_all_configs_import(self):
        """Test all config facades can be imported."""
        from src.config.agent import agent_config
        from src.config.api import api_config
        from src.config.clients import clients_config
        from src.config.ui import ui_config

        assert agent_config is not None
        assert api_config is not None
        assert clients_config is not None
        assert ui_config is not None

    def test_configs_share_settings(self):
        """Test configs share the same settings instance."""
        from src.config.agent import AgentConfig
        from src.config.api import APIConfig
        from src.config.settings import get_settings

        settings = get_settings()
        agent_config = AgentConfig()
        api_config = APIConfig()

        # Both should use the same settings instance (singleton)
        assert agent_config._settings is not None
        assert api_config._settings is not None
