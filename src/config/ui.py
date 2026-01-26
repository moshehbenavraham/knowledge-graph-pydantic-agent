"""
UI-specific configuration facade.

Provides convenient access to UI-related settings.
"""

from dataclasses import dataclass
from typing import Any

import structlog

from .settings import UIMode, get_settings

logger = structlog.get_logger(__name__)


@dataclass
class DashboardConfig:
    """Dashboard-specific configuration."""

    enabled: bool = True
    refresh_interval_seconds: int = 30
    max_entities_display: int = 50
    default_time_window: str = "7d"  # 24h, 7d, 30d
    enable_export: bool = True
    cache_ttl_seconds: int = 30


class UIConfig:
    """Facade for UI-related configuration."""

    def __init__(self) -> None:
        """Initialize dashboard configuration."""
        self.dashboard = DashboardConfig()

    @property
    def mode(self) -> UIMode:
        """Get UI mode."""
        return get_settings().ui_mode

    @property
    def ui_mode(self) -> str:
        """Get UI mode as string (alias for mode)."""
        return self.mode.value if hasattr(self.mode, "value") else str(self.mode)

    @property
    def ui_port(self) -> int:
        """Get UI port."""
        return getattr(get_settings(), "streamlit_port", 8502)

    @property
    def enable_memory(self) -> bool:
        """Check if memory (mem0) is enabled."""
        return getattr(get_settings(), "enable_mem0", False)

    @property
    def enable_mcp(self) -> bool:
        """Check if MCP is enabled."""
        return getattr(get_settings(), "enable_mcp", False)

    @property
    def is_simple_mode(self) -> bool:
        """Check if UI is in simple mode."""
        return self.mode == UIMode.SIMPLE

    @property
    def is_standard_mode(self) -> bool:
        """Check if UI is in standard mode."""
        return self.mode == UIMode.STANDARD

    @property
    def is_advanced_mode(self) -> bool:
        """Check if UI is in advanced mode."""
        return self.mode == UIMode.ADVANCED

    @property
    def enable_persistence(self) -> bool:
        """Check if persistence is enabled (not in simple mode)."""
        return not self.is_simple_mode

    @property
    def enable_advanced_features(self) -> bool:
        """Check if advanced features are enabled."""
        return self.is_advanced_mode

    @property
    def max_message_length(self) -> int:
        """Get maximum message length based on mode."""
        if self.is_simple_mode:
            return 1000
        if self.is_standard_mode:
            return 5000
        # Advanced
        return 10000

    @property
    def show_metrics(self) -> bool:
        """Check if metrics should be shown."""
        return self.is_advanced_mode

    @property
    def show_export(self) -> bool:
        """Check if export feature should be shown."""
        return not self.is_simple_mode

    def get_page_config(self) -> dict[str, Any]:
        """Get Streamlit page configuration."""
        logger.info("Getting page configuration", mode=self.mode.value)
        return {
            "page_title": f"Knowledge Graph Pydantic Agent - {self.mode.value.title()} Mode",
            "page_icon": "🤖",
            "layout": "wide" if self.is_advanced_mode else "centered",
            "initial_sidebar_state": "expanded" if self.is_advanced_mode else "auto",
        }

    def get_mode_description(self) -> str:
        """Get description of current mode."""
        logger.info("Getting mode description", mode=self.mode.value)
        descriptions = {
            UIMode.SIMPLE: "Fast, lightweight interface with no persistence",
            UIMode.STANDARD: "Full-featured interface with conversation history",
            UIMode.ADVANCED: "Advanced interface with all features and metrics",
        }
        return descriptions.get(self.mode, "Unknown mode")

    def get_ui_config(self) -> dict[str, Any]:
        """Get UI configuration dictionary."""
        logger.info("Getting UI configuration", mode=self.ui_mode, port=self.ui_port)
        return {
            "mode": self.ui_mode,
            "port": self.ui_port,
            "enable_memory": self.enable_memory,
            "enable_mcp": self.enable_mcp,
            "enable_persistence": self.enable_persistence,
            "enable_advanced_features": self.enable_advanced_features,
            "max_message_length": self.max_message_length,
            "show_metrics": self.show_metrics,
            "show_export": self.show_export,
        }


# Singleton instance
ui_config = UIConfig()
