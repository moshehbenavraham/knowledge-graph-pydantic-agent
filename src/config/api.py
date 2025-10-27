"""
API-specific configuration facade.

Provides convenient access to API-related settings.
"""

import structlog

from .settings import get_settings

logger = structlog.get_logger(__name__)


class APIConfig:
    """Facade for API-related configuration."""

    def __init__(self):
        """Initialize with current settings."""
        self._settings = get_settings()

    @property
    def host(self) -> str:
        """Get API host."""
        return self._settings.api_host

    @property
    def port(self) -> int:
        """Get API port."""
        return self._settings.api_port

    @property
    def cors_origins(self) -> list[str]:
        """Get CORS allowed origins."""
        return self._settings.get_cors_origins_list()

    @property
    def log_level(self) -> str:
        """Get log level."""
        return self._settings.log_level

    @property
    def debug(self) -> bool:
        """Get debug mode flag."""
        return self._settings.debug

    @property
    def hot_reload(self) -> bool:
        """Get hot reload flag."""
        return self._settings.hot_reload

    @property
    def enable_tracing(self) -> bool:
        """Get tracing flag."""
        return self._settings.enable_tracing

    @property
    def jaeger_host(self) -> str:
        """Get Jaeger host."""
        return self._settings.jaeger_host

    @property
    def jaeger_port(self) -> int:
        """Get Jaeger port."""
        return self._settings.jaeger_port

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self._settings.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self._settings.app_env == "development"

    def get_uvicorn_config(self) -> dict:
        """Get Uvicorn server configuration."""
        logger.info("Getting Uvicorn configuration", host=self.host, port=self.port)
        return {
            "host": self.host,
            "port": self.port,
            "reload": self.hot_reload,
            "log_level": self.log_level.lower(),
            "access_log": self.debug,
        }

    def get_cors_config(self) -> dict:
        """Get CORS middleware configuration."""
        logger.info("Getting CORS configuration", origins_count=len(self.cors_origins))
        return {
            "allow_origins": self.cors_origins,
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }


# Singleton instance
api_config = APIConfig()
