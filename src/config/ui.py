"""
UI-specific configuration facade.

Provides convenient access to UI-related settings.
"""

from dataclasses import dataclass

from .settings import UIMode, get_settings


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

    def __init__(self):
        """Initialize with current settings."""
        self._settings = get_settings()
        self.dashboard = DashboardConfig()

    @property
    def mode(self) -> UIMode:
        """Get UI mode."""
        return self._settings.ui_mode

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

    def get_page_config(self) -> dict:
        """Get Streamlit page configuration."""
        return {
            "page_title": f"Luminari AI Agent - {self.mode.value.title()} Mode",
            "page_icon": "🤖",
            "layout": "wide" if self.is_advanced_mode else "centered",
            "initial_sidebar_state": "expanded" if self.is_advanced_mode else "auto",
        }

    def get_mode_description(self) -> str:
        """Get description of current mode."""
        descriptions = {
            UIMode.SIMPLE: "Fast, lightweight interface with no persistence",
            UIMode.STANDARD: "Full-featured interface with conversation history",
            UIMode.ADVANCED: "Advanced interface with all features and metrics",
        }
        return descriptions.get(self.mode, "Unknown mode")


# Singleton instance
ui_config = UIConfig()
