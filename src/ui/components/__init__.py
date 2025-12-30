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

from src.ui.components.entity_detail import (
    EntityDetail,
    EntityFact,
    EntityRelationship,
    entity_from_dict,
    render_empty_selection_state,
    render_entity_detail_panel,
    render_loading_state,
)
from src.ui.components.error_display import (
    ErrorDisplayConfig,
    ErrorSeverity,
    render_error_display,
    render_error_from_event,
)
from src.ui.components.graph_filters import (
    DEFAULT_ENTITY_TYPES,
    DEFAULT_RELATIONSHIP_TYPES,
    GraphFilterState,
    convert_to_datetime,
    initialize_filter_state,
    render_entity_search,
    render_entity_type_filter,
    render_filter_sidebar,
    render_filter_summary,
    render_graph_options,
    render_relationship_type_filter,
    render_reset_button,
    render_strength_threshold,
    render_temporal_filter,
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
    "DEFAULT_ENTITY_TYPES",
    "DEFAULT_RELATIONSHIP_TYPES",
    "EntityDetail",
    "EntityFact",
    "EntityRelationship",
    "ErrorDisplayConfig",
    "ErrorSeverity",
    "GraphFilterState",
    "LoadingContext",
    "OperationType",
    "ResponseMetadata",
    "ToolExecutionState",
    "ToolStatus",
    "convert_to_datetime",
    "entity_from_dict",
    "get_loading_message",
    "initialize_filter_state",
    "render_empty_selection_state",
    "render_entity_detail_panel",
    "render_entity_search",
    "render_entity_type_filter",
    "render_error_display",
    "render_error_from_event",
    "render_filter_sidebar",
    "render_filter_summary",
    "render_graph_options",
    "render_intent_badge",
    "render_loading_indicator",
    "render_loading_state",
    "render_relationship_type_filter",
    "render_reset_button",
    "render_response_metadata",
    "render_source_count",
    "render_streaming_progress",
    "render_strength_threshold",
    "render_temporal_filter",
    "render_tool_status",
    "render_tool_timeline",
]
