"""
API-specific configuration facade.

Provides convenient access to API-related settings.
"""

from typing import Any

import structlog

from .settings import get_settings

logger = structlog.get_logger(__name__)


class APIConfig:
    """Facade for API-related configuration."""

    @property
    def host(self) -> str:
        """Get API host."""
        return get_settings().api_host

    @property
    def port(self) -> int:
        """Get API port."""
        return get_settings().api_port

    @property
    def cors_origins(self) -> list[str]:
        """Get CORS allowed origins."""
        return get_settings().get_cors_origins_list()

    @property
    def log_level(self) -> str:
        """Get log level."""
        return get_settings().log_level

    @property
    def debug(self) -> bool:
        """Get debug mode flag."""
        return get_settings().debug

    @property
    def hot_reload(self) -> bool:
        """Get hot reload flag."""
        return get_settings().hot_reload

    @property
    def enable_tracing(self) -> bool:
        """Get tracing flag."""
        return get_settings().enable_tracing

    @property
    def jaeger_host(self) -> str:
        """DEPRECATED/IGNORED: legacy Jaeger host (OTLP is used for tracing)."""
        return get_settings().jaeger_host

    @property
    def jaeger_port(self) -> int:
        """DEPRECATED/IGNORED: legacy Jaeger port (OTLP is used for tracing)."""
        return get_settings().jaeger_port

    @property
    def app_env(self) -> str:
        """Get application environment."""
        return get_settings().app_env

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return get_settings().app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return get_settings().app_env == "development"

    def get_uvicorn_config(self) -> dict[str, Any]:
        """Get Uvicorn server configuration."""
        logger.info("Getting Uvicorn configuration", host=self.host, port=self.port)
        return {
            "host": self.host,
            "port": self.port,
            "reload": self.hot_reload,
            "log_level": self.log_level.lower(),
            "access_log": self.debug,
        }

    def get_cors_config(self) -> dict[str, Any]:
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
