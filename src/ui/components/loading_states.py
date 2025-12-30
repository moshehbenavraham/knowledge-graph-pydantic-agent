"""
Contextual loading states and messages.

Provides operation-specific loading messages that reflect
what the system is currently doing during query processing.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

import streamlit as st
import structlog

logger = structlog.get_logger(__name__)


class OperationType(Enum):
    """Types of operations that can display loading states."""

    # Core search operations
    VECTOR_SEARCH = "vector_search"
    GRAPH_SEARCH = "graph_search"
    HYBRID_SEARCH = "hybrid_search"

    # Advanced search operations
    MULTI_HOP = "multi_hop"
    TEMPORAL_TREND = "temporal_trend"
    COMPARISON = "comparison"

    # Other operations
    INTENT_ANALYSIS = "intent_analysis"
    DOCUMENT_RETRIEVAL = "document_retrieval"
    WEB_SEARCH = "web_search"
    IMAGE_ANALYSIS = "image_analysis"
    CODE_EXECUTION = "code_execution"
    SQL_QUERY = "sql_query"
    GENERATING_RESPONSE = "generating_response"


@dataclass
class LoadingContext:
    """
    Context for generating appropriate loading messages.

    Attributes:
        operation: Current operation type
        query: Original user query (optional)
        entity_name: Entity being searched (optional)
        tool_name: Tool being executed (optional)
        progress: Progress indicator 0-100 (optional)
    """

    operation: OperationType
    query: str | None = None
    entity_name: str | None = None
    tool_name: str | None = None
    progress: int | None = None


# Loading message templates by operation type
LOADING_MESSAGES: dict[OperationType, list[str]] = {
    OperationType.VECTOR_SEARCH: [
        "Searching document content...",
        "Finding relevant passages...",
        "Analyzing semantic similarity...",
    ],
    OperationType.GRAPH_SEARCH: [
        "Searching knowledge graph...",
        "Finding entity relationships...",
        "Traversing knowledge connections...",
    ],
    OperationType.HYBRID_SEARCH: [
        "Searching documents and knowledge graph...",
        "Combining semantic and graph results...",
        "Analyzing across multiple sources...",
    ],
    OperationType.MULTI_HOP: [
        "Discovering connection paths...",
        "Traversing entity relationships...",
        "Finding indirect connections...",
    ],
    OperationType.TEMPORAL_TREND: [
        "Analyzing temporal patterns...",
        "Building time series data...",
        "Identifying trends over time...",
    ],
    OperationType.COMPARISON: [
        "Comparing entities...",
        "Gathering comparison metrics...",
        "Building comparison analysis...",
    ],
    OperationType.INTENT_ANALYSIS: [
        "Understanding your question...",
        "Analyzing query intent...",
        "Determining search strategy...",
    ],
    OperationType.DOCUMENT_RETRIEVAL: [
        "Retrieving documents...",
        "Loading document content...",
        "Fetching relevant documents...",
    ],
    OperationType.WEB_SEARCH: [
        "Searching the web...",
        "Gathering web results...",
        "Finding online information...",
    ],
    OperationType.IMAGE_ANALYSIS: [
        "Analyzing image content...",
        "Processing visual information...",
        "Extracting image details...",
    ],
    OperationType.CODE_EXECUTION: [
        "Executing code...",
        "Running code safely...",
        "Processing code output...",
    ],
    OperationType.SQL_QUERY: [
        "Querying database...",
        "Executing SQL query...",
        "Fetching database results...",
    ],
    OperationType.GENERATING_RESPONSE: [
        "Generating response...",
        "Composing answer...",
        "Preparing response...",
    ],
}

# Intent to operation type mapping
INTENT_TO_OPERATION: dict[str, OperationType] = {
    "VECTOR_HEAVY": OperationType.VECTOR_SEARCH,
    "GRAPH_HEAVY": OperationType.GRAPH_SEARCH,
    "HYBRID": OperationType.HYBRID_SEARCH,
    "TEMPORAL": OperationType.GRAPH_SEARCH,
    "ENTITY_FOCUSED": OperationType.GRAPH_SEARCH,
    "MULTI_HOP": OperationType.MULTI_HOP,
    "TEMPORAL_TREND": OperationType.TEMPORAL_TREND,
    "COMPARISON": OperationType.COMPARISON,
}

# Tool to operation type mapping
TOOL_TO_OPERATION: dict[str, OperationType] = {
    "smart_search": OperationType.HYBRID_SEARCH,
    "retrieve_documents": OperationType.DOCUMENT_RETRIEVAL,
    "comprehensive_search": OperationType.HYBRID_SEARCH,
    "graph_traverse": OperationType.MULTI_HOP,
    "web_search": OperationType.WEB_SEARCH,
    "execute_sql": OperationType.SQL_QUERY,
    "analyze_image": OperationType.IMAGE_ANALYSIS,
    "execute_code": OperationType.CODE_EXECUTION,
    "get_full_document": OperationType.DOCUMENT_RETRIEVAL,
    "list_all_documents": OperationType.DOCUMENT_RETRIEVAL,
}


def get_loading_message(
    context: LoadingContext,
    variant: int = 0,
) -> str:
    """
    Get an appropriate loading message for the current context.

    Args:
        context: Loading context with operation type and optional details
        variant: Message variant index (for variety)

    Returns:
        User-friendly loading message
    """
    messages = LOADING_MESSAGES.get(
        context.operation,
        ["Processing..."],
    )

    # Select variant (cycle through available messages)
    message = messages[variant % len(messages)]

    # Personalize with entity name if available
    if context.entity_name and "{entity}" in message:
        message = message.replace("{entity}", context.entity_name)

    return message


def get_operation_from_intent(intent: str) -> OperationType:
    """
    Map a search intent to an operation type.

    Args:
        intent: Search intent string (e.g., 'VECTOR_HEAVY')

    Returns:
        Corresponding operation type
    """
    return INTENT_TO_OPERATION.get(intent.upper(), OperationType.HYBRID_SEARCH)


def get_operation_from_tool(tool_name: str) -> OperationType:
    """
    Map a tool name to an operation type.

    Args:
        tool_name: Tool name string

    Returns:
        Corresponding operation type
    """
    return TOOL_TO_OPERATION.get(tool_name, OperationType.GENERATING_RESPONSE)


def render_loading_indicator(
    context: LoadingContext,
    show_progress: bool = False,
) -> Any:
    """
    Render a contextual loading indicator.

    Args:
        context: Loading context with operation type
        show_progress: Whether to show progress bar (if available)

    Returns:
        Streamlit spinner context manager
    """
    message = get_loading_message(context)

    if show_progress and context.progress is not None:
        # Show progress bar with message
        st.progress(context.progress / 100, text=message)
        return None
    # Return spinner for use as context manager
    return st.spinner(message)


def render_operation_status(
    operation: OperationType,
    is_active: bool = True,
    elapsed_ms: float | None = None,
) -> None:
    """
    Render current operation status with elapsed time.

    Args:
        operation: Current operation type
        is_active: Whether operation is currently running
        elapsed_ms: Elapsed time in milliseconds
    """
    context = LoadingContext(operation=operation)
    message = get_loading_message(context)

    # Build status text
    if is_active:
        status_prefix = "[>>>]"
    else:
        status_prefix = "[OK]"

    status_text = f"{status_prefix} {message}"

    # Add elapsed time if available
    if elapsed_ms is not None:
        if elapsed_ms < 1000:
            status_text += f" ({elapsed_ms:.0f}ms)"
        else:
            status_text += f" ({elapsed_ms / 1000:.1f}s)"

    if is_active:
        st.markdown(f"*{status_text}*")
    else:
        st.markdown(status_text)
