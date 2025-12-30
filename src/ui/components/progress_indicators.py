"""
Progress indicators for streaming UI feedback.

Provides real-time tool execution status and streaming progress
indicators during agent query processing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import streamlit as st
import structlog

logger = structlog.get_logger(__name__)


class ToolStatus(Enum):
    """Status states for tool execution."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ToolExecutionState:
    """
    Tracks the execution state of a single tool.

    Attributes:
        tool_name: Name of the tool being executed
        status: Current execution status
        start_time: When execution started
        end_time: When execution completed (if finished)
        args: Arguments passed to the tool
        result_summary: Brief summary of results (if completed)
        error_message: Error message (if failed)
    """

    tool_name: str
    status: ToolStatus = ToolStatus.PENDING
    start_time: datetime | None = None
    end_time: datetime | None = None
    args: dict[str, Any] = field(default_factory=dict)
    result_summary: str | None = None
    error_message: str | None = None

    @property
    def elapsed_ms(self) -> float:
        """Calculate elapsed time in milliseconds."""
        if self.start_time is None:
            return 0.0

        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds() * 1000

    @property
    def elapsed_display(self) -> str:
        """Format elapsed time for display."""
        elapsed = self.elapsed_ms
        if elapsed < 1000:
            return f"{elapsed:.0f}ms"
        return f"{elapsed / 1000:.1f}s"


# Tool display configuration
TOOL_DISPLAY_NAMES: dict[str, str] = {
    "smart_search": "Smart Search",
    "retrieve_documents": "Document Retrieval",
    "comprehensive_search": "Comprehensive Search",
    "graph_traverse": "Graph Traversal",
    "web_search": "Web Search",
    "execute_sql": "SQL Query",
    "analyze_image": "Image Analysis",
    "execute_code": "Code Execution",
    "get_full_document": "Full Document",
    "list_all_documents": "Document List",
}

# Status icons (ASCII-safe)
STATUS_ICONS: dict[ToolStatus, str] = {
    ToolStatus.PENDING: "[...]",
    ToolStatus.EXECUTING: "[>>>]",
    ToolStatus.COMPLETED: "[OK]",
    ToolStatus.FAILED: "[X]",
}


def get_tool_display_name(tool_name: str) -> str:
    """
    Get user-friendly display name for a tool.

    Args:
        tool_name: Internal tool name

    Returns:
        Human-readable tool name
    """
    return TOOL_DISPLAY_NAMES.get(tool_name, tool_name.replace("_", " ").title())


def render_tool_status(
    state: ToolExecutionState,
    show_args: bool = False,
) -> None:
    """
    Render a single tool's execution status.

    Displays the tool name, status icon, and elapsed time.
    Optionally shows tool arguments.

    Args:
        state: Tool execution state to render
        show_args: Whether to show tool arguments
    """
    display_name = get_tool_display_name(state.tool_name)
    icon = STATUS_ICONS.get(state.status, "[?]")

    # Build status line
    if state.status == ToolStatus.EXECUTING:
        status_text = f"{icon} {display_name}... ({state.elapsed_display})"
    elif state.status == ToolStatus.COMPLETED:
        status_text = f"{icon} {display_name} ({state.elapsed_display})"
    elif state.status == ToolStatus.FAILED:
        status_text = f"{icon} {display_name} - failed"
    else:
        status_text = f"{icon} {display_name}"

    # Render with appropriate styling
    if state.status == ToolStatus.FAILED:
        st.markdown(f"**{status_text}**")
        if state.error_message:
            st.caption(f"Error: {state.error_message}")
    elif state.status == ToolStatus.EXECUTING:
        st.markdown(f"*{status_text}*")
    else:
        st.markdown(status_text)

    # Optionally show arguments
    if show_args and state.args:
        with st.expander("Arguments", expanded=False):
            st.json(state.args)


def render_streaming_progress(
    tool_states: list[ToolExecutionState],
    total_elapsed_ms: float | None = None,
    show_spinner: bool = True,
) -> None:
    """
    Render streaming progress with all tool execution states.

    Shows a progress indicator with each tool's status and
    overall elapsed time.

    Args:
        tool_states: List of tool execution states
        total_elapsed_ms: Total elapsed time in milliseconds
        show_spinner: Whether to show a spinner for executing tools
    """
    if not tool_states:
        return

    # Count states
    executing = sum(1 for s in tool_states if s.status == ToolStatus.EXECUTING)
    completed = sum(1 for s in tool_states if s.status == ToolStatus.COMPLETED)
    failed = sum(1 for s in tool_states if s.status == ToolStatus.FAILED)

    # Header with counts
    if executing > 0:
        header = f"Processing... ({completed} done, {executing} running)"
    else:
        header = f"Tools executed: {completed}"
        if failed > 0:
            header += f" ({failed} failed)"

    with st.container():
        st.markdown(f"**{header}**")

        # Show each tool's status
        for state in tool_states:
            if state.status == ToolStatus.EXECUTING and show_spinner:
                with st.spinner(f"Executing {get_tool_display_name(state.tool_name)}..."):
                    render_tool_status(state)
            else:
                render_tool_status(state)

        # Total elapsed time
        if total_elapsed_ms is not None:
            if total_elapsed_ms < 1000:
                elapsed_str = f"{total_elapsed_ms:.0f}ms"
            else:
                elapsed_str = f"{total_elapsed_ms / 1000:.1f}s"
            st.caption(f"Total time: {elapsed_str}")


def render_tool_timeline(
    tool_states: list[ToolExecutionState],
    show_details: bool = True,
) -> None:
    """
    Render a timeline view of tool executions.

    Shows tools in chronological order with their execution
    times and status.

    Args:
        tool_states: List of tool execution states (in order)
        show_details: Whether to show detailed timing info
    """
    if not tool_states:
        st.info("No tools were called during this query.")
        return

    # Sort by start time
    sorted_states = sorted(
        [s for s in tool_states if s.start_time],
        key=lambda s: s.start_time or datetime.min,
    )

    if not sorted_states:
        st.info("No tool timing information available.")
        return

    st.markdown("**Tool Execution Timeline**")

    # Create timeline display
    for i, state in enumerate(sorted_states, 1):
        display_name = get_tool_display_name(state.tool_name)
        icon = STATUS_ICONS.get(state.status, "[?]")

        # Timeline entry
        col1, col2, col3 = st.columns([1, 4, 2])

        with col1:
            st.markdown(f"**{i}.**")

        with col2:
            st.markdown(f"{icon} {display_name}")

        with col3:
            st.markdown(f"`{state.elapsed_display}`")

        if show_details and state.result_summary:
            st.caption(f"   {state.result_summary}")


def create_tool_state_from_event(
    tool_name: str,
    event_type: str,
    args: dict[str, Any] | None = None,
    content: Any = None,
) -> ToolExecutionState:
    """
    Create or update a tool state from a streaming event.

    Args:
        tool_name: Name of the tool
        event_type: Event type ('tool-call' or 'tool-return')
        args: Tool arguments (for tool-call)
        content: Tool result content (for tool-return)

    Returns:
        ToolExecutionState with appropriate status
    """
    if event_type == "tool-call":
        return ToolExecutionState(
            tool_name=tool_name,
            status=ToolStatus.EXECUTING,
            start_time=datetime.now(),
            args=args or {},
        )
    if event_type == "tool-return":
        # Summarize result
        result_summary = None
        if content:
            content_str = str(content)
            if len(content_str) > 100:
                result_summary = content_str[:100] + "..."
            else:
                result_summary = content_str

        return ToolExecutionState(
            tool_name=tool_name,
            status=ToolStatus.COMPLETED,
            end_time=datetime.now(),
            result_summary=result_summary,
        )
    return ToolExecutionState(tool_name=tool_name)
