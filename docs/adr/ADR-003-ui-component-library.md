# ADR-003: UI Component Library

**Status**: Accepted
**Date**: 2025-12-30
**Phase**: 03 - Production Readiness & User Experience
**Session**: 03 - UI/UX Enhancements

---

## Context

The Streamlit UI had grown organically with inline component logic scattered throughout `streamlit_app.py` and handler files. This led to:
- Inconsistent user experience (different error displays, loading states)
- Code duplication (similar progress indicators in multiple places)
- Difficult maintenance (changes required updates in multiple files)
- No standardization for common patterns

We needed a component library that provided consistent, reusable UI elements while maintaining the handler-based architecture established in the project.

## Decision

We created a **modular component library** in `src/ui/components/` with specialized components for common UI patterns:

### 1. Progress Indicators (`progress_indicators.py`)

Components for tool execution visibility:
- `render_tool_status()` - Display current tool execution state
- `render_streaming_progress()` - Show streaming response progress
- `render_tool_timeline()` - Timeline view of tool executions

Data models:
- `ToolStatus` enum (PENDING, RUNNING, COMPLETE, ERROR)
- `ToolExecutionState` dataclass for tracking tool state

### 2. Loading States (`loading_states.py`)

Operation-specific loading messages:
- `OperationType` enum covering all system operations
- `LoadingContext` dataclass for message generation
- `get_loading_message()` returns contextual messages
- `render_loading_indicator()` displays spinners with context

Mappings provided:
- `INTENT_TO_OPERATION` - Maps search intents to operation types
- `TOOL_TO_OPERATION` - Maps tool names to operation types

### 3. Error Display (`error_display.py`)

User-friendly error presentation:
- `ErrorSeverity` enum (INFO, WARNING, ERROR, CRITICAL)
- `ErrorDisplayConfig` for customizing display
- `render_error_display()` shows formatted error with guidance
- `render_error_from_event()` handles analytics error events

Design principles:
- Never expose stack traces to users
- Provide actionable guidance
- Distinguish severity levels visually

### 4. Response Metadata (`response_metadata.py`)

Post-response information display:
- `render_intent_badge()` - Shows detected search intent
- `render_source_count()` - Displays number of sources used
- `render_response_metadata()` - Combined metadata display

`ResponseMetadata` dataclass captures:
- Intent type
- Source count
- Query latency
- Confidence score

### 5. Graph Visualization Components

For the Graph Explorer dashboard:
- `entity_detail.py` - Entity detail panel with facts and relationships
- `graph_filters.py` - Interactive filter sidebar

## Consequences

### Positive

- **Consistency**: All UI elements follow same patterns
- **Reusability**: Components used across handlers and pages
- **Maintainability**: Single location for each component type
- **Type safety**: Pydantic/dataclass models for component props
- **Documentation**: Clear `__init__.py` exports with docstrings

### Negative

- **Import overhead**: Components imported from submodules
- **Learning curve**: Developers must learn component API
- **Abstraction cost**: Simple uses may feel over-engineered

### Trade-offs

We chose Streamlit-native components over React/custom because:
1. Streamlit handles state management
2. No build step required
3. Consistent with existing codebase
4. Faster development iteration

## Implementation

**Directory Structure**:
```
src/ui/components/
    __init__.py           # Public exports
    progress_indicators.py # Tool execution status
    loading_states.py      # Contextual loading messages
    error_display.py       # User-friendly errors
    response_metadata.py   # Intent/source/latency display
    entity_detail.py       # Graph entity sidebar
    graph_filters.py       # Interactive filters
```

**Usage Example**:
```python
from src.ui.components import (
    render_tool_status,
    get_loading_message,
    render_error_display,
    render_intent_badge,
    LoadingContext,
    OperationType,
)

# Show loading state
context = LoadingContext(operation=OperationType.HYBRID_SEARCH)
with render_loading_indicator(context):
    results = await search(query)

# Show error with guidance
if error:
    render_error_display(
        title="Search Failed",
        message=str(error),
        severity=ErrorSeverity.ERROR,
        suggestions=["Check database connection", "Retry in a moment"],
    )

# Show response metadata
render_intent_badge(intent="HYBRID")
```

## Related Decisions

- Handler-based architecture (existing) - Components used by handlers
- ADR-001: Error handling provides error context for display
- ADR-004: Graph visualization uses entity_detail and graph_filters

---

**Last Updated**: 2025-12-30
