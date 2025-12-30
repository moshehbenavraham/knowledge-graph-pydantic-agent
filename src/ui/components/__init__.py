"""
UI Components module for enhanced user experience.

Provides reusable Streamlit components for:
- Progress indicators with tool execution status
- Contextual loading messages based on operation type
- User-friendly error display with actionable guidance
- Response metadata display (intent badge, sources, latency)

Usage:
    from src.ui.components import (
        render_tool_status,
        render_streaming_progress,
        get_loading_message,
        render_error_display,
        render_intent_badge,
        render_response_metadata,
    )
"""

from src.ui.components.error_display import (
    ErrorDisplayConfig,
    ErrorSeverity,
    render_error_display,
    render_error_from_event,
)
from src.ui.components.loading_states import (
    LoadingContext,
    OperationType,
    get_loading_message,
    render_loading_indicator,
)
from src.ui.components.progress_indicators import (
    ToolExecutionState,
    ToolStatus,
    render_streaming_progress,
    render_tool_status,
    render_tool_timeline,
)
from src.ui.components.response_metadata import (
    ResponseMetadata,
    render_intent_badge,
    render_response_metadata,
    render_source_count,
)

__all__ = [
    "ErrorDisplayConfig",
    "ErrorSeverity",
    "LoadingContext",
    "OperationType",
    "ResponseMetadata",
    "ToolExecutionState",
    "ToolStatus",
    "get_loading_message",
    "render_error_display",
    "render_error_from_event",
    "render_intent_badge",
    "render_loading_indicator",
    "render_response_metadata",
    "render_source_count",
    "render_streaming_progress",
    "render_tool_status",
    "render_tool_timeline",
]
