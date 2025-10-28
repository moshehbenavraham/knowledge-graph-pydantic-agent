import asyncio
import json
import tempfile
import time
import warnings
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
import structlog
from httpx import AsyncClient
from pydantic_ai.messages import ModelRequest, ModelResponse

# Filter Supabase deprecation warnings (from internal library code)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module="supabase",
    message=".*timeout.*parameter is deprecated.*",
)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module="supabase",
    message=".*verify.*parameter is deprecated.*",
)

from src.agentic_rag.analytics import initialize_analytics_logger
from src.agentic_rag.storage.connection_manager import ConnectionManager
from src.auth.streamlit_auth import (
    USE_DATABASE_AUTH,
    render_logout_button,
    require_authentication,
)
from src.auth.user_profile import render_user_profile, render_user_profile_simple
from src.config import UIMode
from src.config.ui import ui_config as config
from src.ui.features import (
    BaseHandler,
    DashboardHandler,
    MCPHandler,
    StreamingHandler,
    create_pyvis_graph,
    render_upload_section,
)
from src.ui.features.base_handler import SimpleHandler

logger = structlog.get_logger(__name__)


def make_json_safe(obj: any, max_depth: int = 10, _current_depth: int = 0) -> any:
    """
    Recursively convert an object to a JSON-serializable format.

    Handles non-serializable types by converting them to strings.
    Prevents infinite recursion with max_depth limit.

    Args:
        obj: Object to make JSON-safe
        max_depth: Maximum recursion depth
        _current_depth: Current recursion level (internal)

    Returns:
        JSON-serializable version of the object
    """
    # Prevent infinite recursion
    if _current_depth >= max_depth:
        return "<max depth reached>"

    # Handle None, bool, int, float, str - already JSON-safe
    if obj is None or isinstance(obj, bool | int | float | str):
        return obj

    # Handle lists/tuples recursively
    if isinstance(obj, list | tuple):
        return [make_json_safe(item, max_depth, _current_depth + 1) for item in obj]

    # Handle dicts recursively
    if isinstance(obj, dict):
        return {
            str(key): make_json_safe(value, max_depth, _current_depth + 1)
            for key, value in obj.items()
        }

    # For everything else, try JSON serialization
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        # Not serializable - convert to string
        try:
            return str(obj)
        except Exception:
            return f"<{type(obj).__name__} object>"


class UIConfig:
    def __init__(self):
        self.mode = config.mode
        self.features = self._get_features_for_mode(self.mode)

    @staticmethod
    def _get_features_for_mode(mode: UIMode) -> dict[str, bool]:
        if mode == UIMode.SIMPLE:
            return {
                "streaming": False,
                "memory": False,
                "mcp": False,
                "tools_visibility": False,
                "metrics": False,
            }
        if mode == UIMode.STANDARD:
            return {
                "streaming": True,
                "memory": False,
                "mcp": False,
                "tools_visibility": True,
                "metrics": False,
            }
        # ADVANCED
        return {
            "streaming": True,
            "memory": True,
            "mcp": True,
            "tools_visibility": True,
            "metrics": True,
        }

    def get_handler(self) -> BaseHandler:
        config = {
            "enable_memory": self.features["memory"],
            "enable_mcp": self.features["mcp"],
            "user_id": "streamlit_user",
            "memory_limit": 3,
        }

        if self.mode == UIMode.SIMPLE:
            return SimpleHandler(config)
        if self.mode == UIMode.STANDARD:
            return StreamingHandler(config)
        # ADVANCED
        return MCPHandler(config)


def display_message_part(part):
    if part.part_kind == "user-prompt" and part.content:
        with st.chat_message("user"):
            st.markdown(part.content)
    elif part.part_kind == "text" and part.content:
        with st.chat_message("assistant"):
            st.markdown(part.content)
    elif part.part_kind == "tool-call" and st.session_state.config.features["tools_visibility"]:
        with st.expander(f"🔧 Tool: {part.tool_name}"):
            try:
                # Get args
                args = part.args
                logger.debug(
                    f"Tool {part.tool_name} args type: {type(args)}, value preview: {str(args)[:200]}"
                )

                # Handle empty/None args
                if not args or (isinstance(args, str) and not args.strip()):
                    st.info("No arguments")
                    return

                # If string, try to parse it
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                        logger.debug("Successfully parsed args from JSON string")
                    except json.JSONDecodeError as e:
                        # Invalid JSON string - show as code
                        logger.debug(
                            f"Tool {part.tool_name} args is not valid JSON: {e!s}, displaying as text"
                        )
                        st.code(str(args))
                        return  # Exit this function since we showed the content

                # If we still have args (either original dict or successfully parsed), display it
                if args and not isinstance(args, str):
                    # Make it JSON-safe and display
                    safe_args = make_json_safe(args)
                    if safe_args != args:
                        logger.debug(f"Tool {part.tool_name} args contained non-serializable data")
                    st.json(safe_args)
                elif args and isinstance(args, str):
                    # Still a string after parse attempt - show as code
                    st.code(args)

            except Exception as e:
                # Ultimate fallback - show raw args
                logger.error(f"Failed to display tool {part.tool_name} args: {e}")
                st.code(str(part.args))
    elif part.part_kind == "tool-return" and st.session_state.config.features["tools_visibility"]:
        with st.expander(f"📥 Tool Result: {part.tool_name}", expanded=False):
            content_str = str(part.content)
            # Show preview if content is very long
            if len(content_str) > 2000:
                st.caption(f"Result length: {len(content_str)} chars (showing first 2000)")
                st.code(content_str[:2000] + "\n\n... (truncated)")
            else:
                st.code(content_str)


def initialize_session_state():
    logger.info("=" * 80)
    logger.info("initialize_session_state() called")

    # Check if this is the first initialization
    is_first_init = "handler" not in st.session_state

    # Only show loading screen on first initialization
    if is_first_init:
        loading_placeholder = st.empty()
        with loading_placeholder.container():
            st.markdown(
                """
                <style>
                .loading-container {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    padding: 4rem 2rem;
                    text-align: center;
                }
                .loading-title {
                    font-size: 2.5rem;
                    font-weight: 700;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    margin-bottom: 1rem;
                    animation: pulse 2s ease-in-out infinite;
                }
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.7; }
                }
                .loading-subtitle {
                    font-size: 1.2rem;
                    color: #666;
                    margin-bottom: 2rem;
                }
                </style>
                <div class="loading-container">
                    <div class="loading-title">🚀 AI with Apex</div>
                    <div class="loading-subtitle">Initializing Advanced RAG Agent...</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            progress_bar = st.progress(0, text="Starting initialization...")
            time.sleep(0.3)

            # Step 1: Initialize messages
            if "messages" not in st.session_state:
                progress_bar.progress(10, text="📝 Setting up message history...")
                st.session_state.messages = []
                logger.info("Session state: messages initialized (empty list)")
                time.sleep(0.2)

            # Step 2: Initialize config
            if "config" not in st.session_state:
                progress_bar.progress(25, text="⚙️ Loading configuration...")
                logger.info("Session state: config not found, creating UIConfig...")
                st.session_state.config = UIConfig()
                logger.info(
                    "Session state: config created",
                    mode=st.session_state.config.mode.value,
                    features=st.session_state.config.features,
                )
                time.sleep(0.3)

            # Step 3: Create handler
            progress_bar.progress(40, text="🔧 Creating handler components...")
            handler = st.session_state.config.get_handler()
            logger.info(
                "Session state: handler created",
                handler_type=type(handler).__name__,
            )
            time.sleep(0.4)

            # Step 4: Initialize clients
            progress_bar.progress(55, text="🔌 Connecting to services...")
            st.session_state.handler = handler
            time.sleep(0.5)

            # Step 5: Initialize handler (this is the slow part - no artificial delay needed)
            mode_name = st.session_state.config.mode.value.title()
            features = []
            if st.session_state.config.features.get("streaming"):
                features.append("Streaming")
            if st.session_state.config.features.get("memory"):
                features.append("Memory")
            if st.session_state.config.features.get("mcp"):
                features.append("MCP")

            feature_text = f" ({', '.join(features)})" if features else ""
            progress_bar.progress(70, text=f"🧠 Initializing {mode_name} mode{feature_text}...")

            logger.info("Initializing handler...")
            st.session_state.handler.initialize()
            logger.info("Handler initialization complete")

            # Step 6: Initialize analytics logger
            if "analytics_logger" not in st.session_state:
                progress_bar.progress(80, text="📊 Initializing analytics...")
                try:
                    logger.info("Initializing analytics logger...")
                    conn_mgr = ConnectionManager()
                    analytics_logger = asyncio.run(initialize_analytics_logger(conn_mgr))
                    st.session_state.analytics_logger = analytics_logger
                    st.session_state.connection_manager = conn_mgr
                    logger.info("Analytics logger initialized successfully")
                except Exception as e:
                    logger.exception("Failed to initialize analytics logger", error=str(e))
                    st.session_state.analytics_logger = None
                time.sleep(0.3)

            # Step 7: Finalize
            progress_bar.progress(90, text="✨ Finalizing setup...")
            time.sleep(0.3)

            # Step 7: Complete
            progress_bar.progress(100, text="✅ Ready to chat!")
            time.sleep(0.5)

        # Clear the loading screen
        loading_placeholder.empty()
    else:
        # Fast path for subsequent calls
        logger.debug(
            "Session state: handler already exists",
            handler_type=type(st.session_state.handler).__name__,
        )

    # Initialize remaining state
    if "messages" not in st.session_state:
        st.session_state.messages = []
        logger.info("Session state: messages initialized (empty list)")
    else:
        logger.debug(
            "Session state: messages already exists", message_count=len(st.session_state.messages)
        )

    if "config" not in st.session_state:
        logger.info("Session state: config not found, creating UIConfig...")
        st.session_state.config = UIConfig()
        logger.info(
            "Session state: config created",
            mode=st.session_state.config.mode.value,
            features=st.session_state.config.features,
        )
    else:
        logger.debug(
            "Session state: config already exists",
            mode=st.session_state.config.mode.value,
        )

    if "theme" not in st.session_state:
        st.session_state.theme = "light"
        logger.info("Session state: theme initialized to 'light'")
    else:
        logger.debug("Session state: theme already exists", theme=st.session_state.theme)

    if "current_page" not in st.session_state:
        st.session_state.current_page = "Chat"
        logger.info("Session state: current_page initialized to 'Chat'")
    else:
        logger.debug(
            "Session state: current_page already exists", page=st.session_state.current_page
        )

    logger.info(
        "Session state initialization COMPLETE",
        mode=st.session_state.config.mode.value,
        handler_type=type(st.session_state.handler).__name__,
        message_count=len(st.session_state.messages),
        current_page=st.session_state.current_page,
    )


def render_sidebar():
    with st.sidebar:
        st.title("⚙️ Settings")

        # Page Navigation (only show in Standard/Advanced mode)
        if st.session_state.config.mode != UIMode.SIMPLE:
            page = st.radio(
                "Navigation",
                options=["💬 Chat", "📊 Dashboard"],
                index=0 if st.session_state.current_page == "Chat" else 1,
                label_visibility="collapsed",
            )
            # Extract page name (remove emoji)
            selected_page = page.split(" ", 1)[1]
            if selected_page != st.session_state.current_page:
                logger.info(
                    "Page navigation triggered",
                    from_page=st.session_state.current_page,
                    to_page=selected_page,
                )
                st.session_state.current_page = selected_page
                st.rerun()

            st.divider()

        # UI Mode Selector
        st.subheader("UI Mode")
        current_mode = st.session_state.config.mode

        mode_descriptions = {
            UIMode.SIMPLE: "Basic chat interface - Fast and simple",
            UIMode.STANDARD: "Streaming with tools - Recommended",
            UIMode.ADVANCED: "All features - Memory, MCP, metrics",
        }

        selected_mode = st.radio(
            "Select mode:",
            options=list(UIMode),
            format_func=lambda x: f"{x.value.title()}",
            index=list(UIMode).index(current_mode),
            help="\n".join([f"**{m.value.title()}**: {d}" for m, d in mode_descriptions.items()]),
        )

        if selected_mode != current_mode:
            logger.info(
                "=" * 80,
            )
            logger.info(
                "UI Mode change triggered",
                from_mode=current_mode.value,
                to_mode=selected_mode.value,
            )

            st.session_state.config.mode = selected_mode
            new_features = UIConfig._get_features_for_mode(selected_mode)
            st.session_state.config.features = new_features
            logger.info("Mode features updated", new_features=new_features)

            logger.info("Creating new handler for mode change...")
            new_handler = st.session_state.config.get_handler()
            logger.info("New handler created", handler_type=type(new_handler).__name__)

            st.session_state.handler = new_handler
            logger.info("Initializing new handler...")
            st.session_state.handler.initialize()
            logger.info("Mode change complete, triggering rerun")

            st.rerun()

        st.divider()

        # Feature Toggles (for advanced mode)
        if current_mode == UIMode.ADVANCED:
            st.subheader("Advanced Features")

            features = st.session_state.config.features

            new_features = {}
            new_features["streaming"] = st.checkbox("Enable Streaming", value=features["streaming"])
            new_features["memory"] = st.checkbox("Enable Memory (Mem0)", value=features["memory"])
            new_features["mcp"] = st.checkbox("Enable MCP Servers", value=features["mcp"])
            new_features["tools_visibility"] = st.checkbox(
                "Show Tool Calls", value=features["tools_visibility"]
            )
            new_features["metrics"] = st.checkbox("Show Metrics", value=features["metrics"])

            if new_features != features:
                logger.info("=" * 80)
                logger.info(
                    "Advanced feature toggles changed",
                    old_features=features,
                    new_features=new_features,
                )

                st.session_state.config.features = new_features
                logger.info("Features updated in config")

                logger.info("Creating new handler for feature changes...")
                new_handler = st.session_state.config.get_handler()
                logger.info("New handler created", handler_type=type(new_handler).__name__)

                st.session_state.handler = new_handler
                logger.info("Initializing new handler...")
                st.session_state.handler.initialize()
                logger.info("Feature toggle complete, triggering rerun")

                st.rerun()

        st.divider()

        # Conversation Management
        st.subheader("Conversation")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Chat"):
                message_count = len(st.session_state.messages)
                logger.info("Clear chat triggered", message_count_cleared=message_count)
                st.session_state.messages = []
                st.rerun()

        with col2:
            if st.button("💾 Export Chat"):
                export_conversation()

        st.divider()

        # File Upload Section
        if hasattr(st.session_state.handler, "deps") and hasattr(
            st.session_state.handler.deps, "supabase"
        ):
            # Get clients from handler
            supabase_client = st.session_state.handler.deps.supabase
            embedding_client = st.session_state.handler.deps.embedding_client
            render_upload_section(supabase_client, embedding_client)
        else:
            # Fallback: get clients from base handler
            from src.clients.database import get_supabase_client
            from src.clients.llm import get_llm_client

            supabase_client = get_supabase_client()
            embedding_client = get_llm_client()  # Same client for embeddings
            render_upload_section(supabase_client, embedding_client)

        # Metrics Display
        if st.session_state.config.features.get("metrics"):
            st.divider()
            st.subheader("📊 Metrics")

            # Create containers for metrics that update dynamically
            metrics_container = st.container()

            with metrics_container:
                # Count actual user/assistant message pairs (not technical message objects)
                conversation_count = 0
                for msg in st.session_state.messages:
                    if isinstance(msg, ModelRequest | ModelResponse):
                        for part in msg.parts:
                            if part.part_kind in ["user-prompt", "text"] and part.content:
                                conversation_count += 1

                # Check memory status
                memory_active = (
                    hasattr(st.session_state.handler, "memory_client")
                    and st.session_state.handler.memory_client
                )

                logger.debug(
                    "Sidebar metrics calculated",
                    conversation_count=conversation_count,
                    memory_active=memory_active,
                    total_message_objects=len(st.session_state.messages),
                )

                # Display message count with visual indicator
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Messages", conversation_count, delta=None)
                with col2:
                    if memory_active:
                        st.metric("Memory", "✅ Active")
                    else:
                        st.metric("Memory", "❌ Off")

        # User Profile Section (Database mode only)
        if USE_DATABASE_AUTH:
            # Full user profile with password change, sessions, etc.
            username = st.session_state.get("username")
            if username:
                render_user_profile(username)
        else:
            # Simplified profile for YAML mode
            username = st.session_state.get("username")
            name = st.session_state.get("name")
            if username and name:
                # Try to get email from config if available
                try:
                    from src.auth.streamlit_auth import load_auth_config

                    config = load_auth_config()
                    user_data = config.get("credentials", {}).get("usernames", {}).get(username, {})
                    email = user_data.get("email")
                    render_user_profile_simple(username, name, email)
                except Exception:
                    # Fallback without email
                    render_user_profile_simple(username, name)

        # Logout Section
        st.divider()
        render_logout_button(st.session_state.authenticator, st.session_state.name)

        # About Section
        st.divider()
        st.caption(f"Mode: **{current_mode.value.title()}**")
        st.caption("Powered by Pydantic AI")


async def render_dashboard():
    """Render the GraphRAG Dashboard with analytics and visualizations."""
    st.title("📊 GraphRAG Dashboard")
    st.caption("Real-time analytics and visualization of your Agentic RAG system")

    # Use singleton connection manager to avoid creating/destroying pools on every render
    # Note: DashboardHandler has internal caching (30s TTL) so this is efficient
    from src.agentic_rag.storage.connection_manager import get_connection_manager

    # Show loading screen while initializing
    loading_placeholder = st.empty()

    try:
        with loading_placeholder.container():
            st.markdown(
                """
                <style>
                .dashboard-loading {
                    text-align: center;
                    padding: 3rem;
                }
                .dashboard-loading h3 {
                    color: #1f77b4;
                    font-size: 1.5rem;
                    margin-bottom: 1rem;
                }
                </style>
                <div class="dashboard-loading">
                    <h3>🔄 Loading Dashboard...</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )

            progress_bar = st.progress(0)
            status_text = st.empty()

            # Step 1: Initialize connection manager
            status_text.text("📡 Connecting to databases...")
            progress_bar.progress(33)
            conn_mgr = await get_connection_manager()

            # Step 2: Create dashboard handler
            status_text.text("🔧 Initializing dashboard handler...")
            progress_bar.progress(66)
            handler = DashboardHandler(conn_mgr)

            # Step 3: Ready to render
            status_text.text("✨ Loading analytics...")
            progress_bar.progress(100)

        # Clear loading screen and render dashboard
        loading_placeholder.empty()
        await _render_dashboard_content(handler)

    except Exception as e:
        loading_placeholder.empty()
        st.error(f"Failed to initialize dashboard: {e}")
        st.info("Please check your database connections (PostgreSQL and Neo4j)")
        return


async def _render_dashboard_content(handler: DashboardHandler):
    """Render dashboard content with initialized handler."""

    # Add refresh buttons
    col1, col2, col3 = st.columns([5, 1, 1])
    with col2:
        if st.button("🔄 Refresh", help="Clear cache and reload dashboard"):
            logger.info("Dashboard refresh button clicked - clearing cache and rerunning")
            handler.clear_cache()
            logger.debug("Dashboard cache cleared")
            st.rerun()
    with col3:
        if st.button("📊 Sync Views", help="Refresh materialized views with latest data"):
            logger.info("Refresh views button clicked - updating materialized views")
            with st.spinner("Refreshing analytics views..."):
                success = await handler.refresh_materialized_views()
                if success:
                    st.success("✅ Views refreshed! Dashboard will reload.", icon="✅")
                    logger.info("Materialized views refreshed successfully")
                    st.rerun()
                else:
                    st.error("❌ Failed to refresh views. Check logs for details.", icon="❌")
                    logger.error("Failed to refresh materialized views")

    st.divider()

    # Section A: Search Analytics
    st.header("🔍 Search Analytics")
    st.caption("📅 Showing metrics for the last 7 days")

    try:
        metrics = await handler.get_search_metrics()

        # Metrics cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Searches", metrics.get("total_searches", 0))
        with col2:
            st.metric("Avg Latency", f"{metrics.get('avg_latency_ms', 0):.0f}ms")
        with col3:
            st.metric("Top Strategy", metrics.get("most_used_strategy", "N/A"))
        with col4:
            st.metric("Graph Boost Rate", f"{metrics.get('boost_rate', 0):.1%}")

        # Strategy distribution chart
        if metrics.get("strategy_distribution"):
            st.subheader("Search Strategy Distribution")
            strategy_dist = metrics["strategy_distribution"]
            fig = px.bar(
                x=list(strategy_dist.keys()),
                y=list(strategy_dist.values()),
                labels={"x": "Strategy", "y": "Count"},
                title="Search Strategy Usage",
            )
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        logger.exception("Error rendering search analytics")
        st.error(f"Error loading search metrics: {e}")

    st.divider()

    # Section B: Trends Over Time (full width)
    st.header("📈 Trends Over Time")
    try:
        col1, col2 = st.columns(2)
        with col1:
            selected_window = st.selectbox(
                "Time Window", ["24h", "7d", "30d"], index=1, key="trend_window"
            )
        with col2:
            selected_metric = st.selectbox(
                "Metric",
                ["searches", "latency", "cache_hits", "graph_boosts"],
                format_func=lambda x: x.replace("_", " ").title(),
                index=0,
                key="trend_metric",
            )

        series = await handler.get_time_series_data(window=selected_window, metric=selected_metric)

        if series:
            df_series = pd.DataFrame(series)

            # Show date range and data point count
            if not df_series.empty:
                min_date = df_series["timestamp"].min()
                max_date = df_series["timestamp"].max()
                data_points = len(df_series)
                st.caption(
                    f"📅 Data range: {min_date} to {max_date} "
                    f"({data_points} data point{'s' if data_points != 1 else ''})"
                )

                # Debug logging
                logger.info(
                    f"Time series data: window={selected_window}, metric={selected_metric}, "
                    f"rows={data_points}, date_range={min_date} to {max_date}"
                )

            fig = px.line(
                df_series,
                x="timestamp",
                y=selected_metric,
                title=f"{selected_metric.replace('_', ' ').title()} Over {selected_window}",
                labels={
                    "timestamp": "Time",
                    selected_metric: selected_metric.replace("_", " ").title(),
                },
            )
            fig.update_traces(mode="lines+markers")
            st.plotly_chart(fig, use_container_width=True)

            # Note about materialized views for 7d/30d windows
            if selected_window in ["7d", "30d"]:
                st.caption(
                    "💡 Note: Daily summaries may use materialized views. "
                    "If data seems outdated, click '📊 Sync Views' button at the top to refresh."
                )
        else:
            st.info(
                f"No time-series data available for {selected_window} window. Run searches to populate analytics."
            )

    except Exception as e:
        logger.exception("Error rendering time-series data")
        st.error(f"Error loading trends: {e}")

    st.divider()

    # Section C: Intent Analysis (full width)
    st.header("🎯 Intent Analysis")
    try:
        intent_dist = await handler.get_intent_distribution()

        if intent_dist:
            fig = px.pie(
                values=list(intent_dist.values()),
                names=list(intent_dist.keys()),
                title="Query Intent Distribution",
                hole=0.3,  # Donut chart style
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No intent data available yet. Run some searches to see intent distribution.")

    except Exception as e:
        logger.exception("Error rendering intent analysis")
        st.error(f"Error loading intent data: {e}")

    st.divider()

    # Section C: Knowledge Graph (full width, Interactive pyvis visualization)
    st.header("🕸️ Knowledge Graph")
    try:
        # Controls for graph visualization
        col1, col2, col3 = st.columns([2, 2, 6])
        with col1:
            limit = st.slider("Max Entities", 10, 200, 100, step=10, key="graph_limit")
        with col2:
            layout_type = st.selectbox(
                "Layout",
                ["force_directed", "hierarchical", "circular"],
                format_func=lambda x: x.replace("_", " ").title(),
                index=0,
                key="graph_layout",
            )

        # Fetch graph data with loading indicator
        with st.spinner(f"🔍 Loading knowledge graph (up to {limit} entities)..."):
            graph_data = await handler.get_graph_data(limit=limit)
            entities = graph_data.get("entities", [])
            relationships = graph_data.get("relationships", [])

        if entities:
            # Filter out entities with None IDs
            valid_entities = [e for e in entities if e.get("id") is not None]

            # Create pyvis interactive graph
            net = create_pyvis_graph(
                entities=valid_entities,
                relationships=relationships,
                height="700px",
                width="100%",
                layout=layout_type,
            )

            # Save graph to temporary HTML file
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".html", mode="w", encoding="utf-8"
            ) as tmp_file:
                tmp_path = tmp_file.name

            # Save the graph (must be done after closing the temp file)
            net.save_graph(tmp_path)

            # Read the HTML content
            with open(tmp_path, encoding="utf-8") as f:
                html_content = f.read()

            # Clean up temporary file
            Path(tmp_path).unlink()

            # Display the interactive graph using Streamlit components
            components.html(html_content, height=750, scrolling=False)

            # Add legend for entity types
            st.markdown("---")
            st.markdown("**Entity Type Legend:**")
            entity_type_colors = {
                "person": "#4C8EDA",  # Blue
                "company": "#FF6B6B",  # Coral Red
                "organization": "#57C7E3",  # Cyan
                "location": "#FFC454",  # Yellow
                "event": "#F16667",  # Red
                "technology": "#8DCC93",  # Green
                "product": "#A78BFA",  # Purple
                "concept": "#D9A5B3",  # Pink
            }
            legend_cols = st.columns(len(entity_type_colors))
            for idx, (entity_type, color) in enumerate(entity_type_colors.items()):
                with legend_cols[idx % len(legend_cols)]:
                    st.markdown(
                        f'<span style="color: {color}; font-size: 20px;">●</span> {entity_type.capitalize()}',
                        unsafe_allow_html=True,
                    )

            # Usage instructions
            st.info(
                "💡 **Interactive Controls:** "
                "Drag nodes to reposition • Click and drag background to pan • "
                "Scroll to zoom • Hover over nodes for details • "
                "Use navigation buttons in bottom-right corner"
            )

            st.caption(
                f"Showing {len(valid_entities)} entities and {len(relationships)} relationships. "
                f"Node size indicates connection count."
            )
        else:
            st.info("No entities in knowledge graph yet. Ingest documents to build the graph.")

    except Exception as e:
        logger.exception("Error rendering knowledge graph")
        st.error(f"Error loading graph data: {e}")
        st.info("Make sure Neo4j is running and properly configured")

    st.divider()

    # Section D & E: Entity Explorer and Performance Metrics (side by side)
    col_left, col_right = st.columns(2)

    with col_left:
        st.header("🏷️ Entity Explorer")
        try:
            entities = await handler.get_top_entities(limit=20)

            if entities:
                df = pd.DataFrame(entities)
                # Select columns for display
                display_columns = [
                    "name",
                    "type",
                    "relationship_count",
                    "chunk_count",
                ]
                df_display = df[display_columns]

                # Show the dataframe
                st.dataframe(
                    df_display,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "name": st.column_config.TextColumn("Entity Name", width="medium"),
                        "type": st.column_config.TextColumn("Type", width="small"),
                        "relationship_count": st.column_config.NumberColumn(
                            "Relationships", width="small"
                        ),
                        "chunk_count": st.column_config.NumberColumn("Chunks", width="small"),
                    },
                )

                # Optional: Show details for selected entity
                if len(entities) > 0:
                    entity_names = [e["name"] for e in entities]
                    selected_entity = st.selectbox(
                        "View entity timeline:", ["Select an entity...", *entity_names]
                    )

                    if selected_entity != "Select an entity...":
                        entity_data = next(e for e in entities if e["name"] == selected_entity)
                        entity_id = entity_data["id"]

                        with st.spinner("Loading timeline..."):
                            timeline = await handler.get_entity_timeline(entity_id)

                        if timeline:
                            st.subheader(f"Timeline: {selected_entity}")
                            for fact in timeline:
                                st.write(f"- {fact.get('description', 'N/A')}")
                                if fact.get("valid_from"):
                                    st.caption(f"  From: {fact['valid_from']}")
                        else:
                            st.info("No temporal facts available for this entity")
            else:
                st.info("No entities found. Ingest documents to populate the graph.")

        except Exception as e:
            logger.exception("Error rendering entity explorer")
            st.error(f"Error loading entities: {e}")

    with col_right:
        st.header("⚡ Performance Metrics")
        try:
            perf = await handler.get_performance_metrics()

            # Latency breakdown
            if perf.get("vector_latency_ms", 0) > 0 or perf.get("graph_latency_ms", 0) > 0:
                fig = px.bar(
                    x=[
                        "Vector Search",
                        "Graph Search",
                        "Total",
                    ],
                    y=[
                        perf.get("vector_latency_ms", 0),
                        perf.get("graph_latency_ms", 0),
                        perf.get("total_latency_ms", 0),
                    ],
                    labels={"x": "Component", "y": "Latency (ms)"},
                    title="Average Query Latency Breakdown",
                )
                st.plotly_chart(fig, use_container_width=True)

            # Cache and database health
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Cache Hit Rate", f"{perf.get('cache_hit_rate', 0):.1%}")
            with col2:
                st.metric("PostgreSQL Conns", perf.get("pg_active_connections", 0))
            with col3:
                st.metric("Neo4j Conns", perf.get("neo4j_active_connections", 0))

            # Database metrics detail
            with st.expander("Database Metrics Detail"):
                st.subheader("PostgreSQL")
                pg_metrics = perf.get("pg_metrics", {})
                st.write(f"- Total Queries: {pg_metrics.get('total_queries', 0)}")
                st.write(f"- Failed Queries: {pg_metrics.get('failed_queries', 0)}")
                st.write(f"- Avg Query Time: {pg_metrics.get('avg_query_time_ms', 0):.2f}ms")

                st.subheader("Neo4j")
                neo4j_metrics = perf.get("neo4j_metrics", {})
                st.write(f"- Total Queries: {neo4j_metrics.get('total_queries', 0)}")
                st.write(f"- Failed Queries: {neo4j_metrics.get('failed_queries', 0)}")
                st.write(f"- Avg Query Time: {neo4j_metrics.get('avg_query_time_ms', 0):.2f}ms")

        except Exception as e:
            logger.exception("Error rendering performance metrics")
            st.error(f"Error loading performance data: {e}")

    st.divider()

    # Section F: Tool Usage Analytics (full width)
    st.header("🔧 Tool Usage Analytics")
    try:
        tool_metrics = await handler.get_tool_usage_metrics()

        if tool_metrics.get("total_calls", 0) > 0:
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Tool Calls", tool_metrics["total_calls"])
            with col2:
                st.metric("Unique Tools", tool_metrics["unique_tools"])
            with col3:
                st.metric("Average Success Rate", f"{tool_metrics['avg_success_rate'] * 100:.1f}%")

            # Tool performance table
            if tool_metrics.get("tools"):
                st.subheader("Tool Performance Breakdown")
                df_tools = pd.DataFrame(tool_metrics["tools"])

                # Format columns
                if "success_rate" in df_tools.columns:
                    df_tools["success_rate"] = df_tools["success_rate"].apply(
                        lambda x: f"{x * 100:.1f}%"
                    )
                if "avg_execution_time_ms" in df_tools.columns:
                    df_tools["avg_execution_time_ms"] = df_tools["avg_execution_time_ms"].apply(
                        lambda x: f"{x:.1f}ms"
                    )
                if "p95_execution_time_ms" in df_tools.columns:
                    df_tools["p95_execution_time_ms"] = df_tools["p95_execution_time_ms"].apply(
                        lambda x: f"{x:.1f}ms"
                    )

                st.dataframe(
                    df_tools,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "tool_name": st.column_config.TextColumn("Tool Name", width="medium"),
                        "total_calls": st.column_config.NumberColumn("Calls", width="small"),
                        "success_rate": st.column_config.TextColumn("Success Rate", width="small"),
                        "avg_execution_time_ms": st.column_config.TextColumn(
                            "Avg Time", width="small"
                        ),
                        "p95_execution_time_ms": st.column_config.TextColumn(
                            "P95 Time", width="small"
                        ),
                    },
                )
        else:
            st.info(
                "📊 No tool usage data available for the last 7 days. "
                "Tools are tracked automatically when used. "
                "If you've been using tools, try clicking '📊 Sync Views' button above to refresh the data."
            )

    except Exception as e:
        logger.exception("Error rendering tool analytics")
        st.error(f"Error loading tool usage analytics: {e}")

    st.divider()

    # Section G: Agent Interactions (full width)
    st.header("💬 Agent Interactions")
    try:
        agent_metrics = await handler.get_agent_interaction_metrics()

        if agent_metrics.get("total_interactions", 0) > 0:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Interactions", agent_metrics["total_interactions"])
            with col2:
                st.metric("Unique Sessions", agent_metrics["unique_sessions"])
            with col3:
                st.metric("Avg Response Time", f"{agent_metrics['avg_response_time_ms']:.0f}ms")
            with col4:
                st.metric("RAG Usage Rate", f"{agent_metrics['rag_usage_rate'] * 100:.1f}%")

            # User feedback metrics
            st.subheader("User Feedback")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("👍 Thumbs Up", agent_metrics["thumbs_up"])
            with col2:
                st.metric("👎 Thumbs Down", agent_metrics["thumbs_down"])
            with col3:
                st.metric("Feedback Rate", f"{agent_metrics['feedback_rate'] * 100:.1f}%")

            # Feedback visualization
            if agent_metrics["thumbs_up"] > 0 or agent_metrics["thumbs_down"] > 0:
                fig = px.pie(
                    values=[agent_metrics["thumbs_up"], agent_metrics["thumbs_down"]],
                    names=["Positive", "Negative"],
                    title="User Feedback Distribution",
                    color_discrete_map={"Positive": "#4CAF50", "Negative": "#F44336"},
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                "📊 No agent interaction data available for the last 7 days. "
                "Interactions are tracked automatically during conversations. "
                "If you've been using the chat, try clicking '📊 Sync Views' button above to refresh the data."
            )

    except Exception as e:
        logger.exception("Error rendering agent interaction analytics")
        st.error(f"Error loading agent interaction data: {e}")


def export_conversation():
    import json
    from datetime import datetime

    logger.info("=" * 80)
    logger.info(
        "Export conversation requested",
        current_message_count=len(st.session_state.messages),
        mode=st.session_state.config.mode.value,
    )

    export_data = {
        "timestamp": datetime.now().isoformat(),
        "mode": st.session_state.config.mode.value,
        "messages": [],
    }

    message_count = 0
    for msg in st.session_state.messages:
        if isinstance(msg, ModelRequest | ModelResponse):
            for part in msg.parts:
                if part.part_kind in ["user-prompt", "text"] and part.content:
                    export_data["messages"].append(
                        {
                            "role": "user" if part.part_kind == "user-prompt" else "assistant",
                            "content": part.content,
                        }
                    )
                    message_count += 1

    file_name = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    export_json = json.dumps(export_data, indent=2)
    export_size_kb = round(len(export_json) / 1024, 2)

    logger.info(
        "Conversation export prepared",
        messages_exported=message_count,
        file_name=file_name,
        export_size_kb=export_size_kb,
    )

    st.download_button(
        label="Download JSON",
        data=export_json,
        file_name=file_name,
        mime="application/json",
    )

    logger.info("Export download button displayed", file_name=file_name)


async def handle_user_input(user_input: str):
    logger.info("=" * 80)
    logger.info(
        "handle_user_input() called - USER MESSAGE RECEIVED",
        user_input_length=len(user_input),
        user_input_preview=user_input[:100] + "..." if len(user_input) > 100 else user_input,
        current_message_count=len(st.session_state.messages),
    )

    handler = st.session_state.handler
    config = st.session_state.config

    logger.info(
        "Handler and config loaded",
        handler_type=type(handler).__name__,
        mode=config.mode.value,
        streaming_enabled=config.features["streaming"],
        features=config.features,
    )

    with st.chat_message("user"):
        st.markdown(user_input)
        logger.debug("User message displayed in UI")

    with st.chat_message("assistant"):
        if not config.features["streaming"]:
            # Simple mode - no streaming
            logger.info("NON-STREAMING mode - executing SimpleHandler.run_agent()...")

            with st.spinner("Thinking..."):
                async with AsyncClient() as http_client:  # noqa: CONST-III-001 - UI context manager for request lifecycle  # fmt: skip
                    logger.debug("HTTP client created, calling handler.run_agent()...")

                    result = await handler.run_agent(
                        user_input, st.session_state.messages, http_client
                    )

                    response_length = len(result["response"]) if result.get("response") else 0
                    new_messages_count = len(result.get("new_messages", []))

                    logger.info(
                        "Agent execution complete (non-streaming)",
                        response_length=response_length,
                        new_messages_count=new_messages_count,
                    )

                    st.markdown(result["response"])
                    st.session_state.messages.extend(result["new_messages"])

                    logger.info(
                        "Messages added to session state",
                        total_message_count=len(st.session_state.messages),
                    )

                    # Set flag to update metrics on next render
                    st.session_state.needs_metrics_update = True
        else:
            # Streaming mode
            logger.info("STREAMING mode - executing streaming handler...")

            message_placeholder = st.empty()
            status_placeholder = st.empty()
            full_response = ""
            first_chunk_received = False

            # Chunk tracking
            chunk_counts = {
                "start": 0,
                "delta": 0,
                "tool_call": 0,
                "tool_return": 0,
                "complete": 0,
                "total": 0,
            }

            async with AsyncClient() as http_client:  # noqa: CONST-III-001 - UI context manager for request lifecycle  # fmt: skip
                logger.debug("HTTP client created, starting agent stream...")

                # Show thinking indicator while waiting for first chunk
                status_placeholder.status("Thinking...", state="running")

                async for chunk in handler.run_agent(
                    user_input, st.session_state.messages, http_client
                ):
                    chunk_counts["total"] += 1
                    chunk_type = chunk.get("type", "unknown")
                    if chunk_type == "start":
                        chunk_counts["start"] += 1
                        # Clear the thinking indicator once we start receiving content
                        if not first_chunk_received:
                            logger.info("First chunk received - text start")
                            status_placeholder.empty()
                            first_chunk_received = True
                        full_response = chunk["content"]
                        message_placeholder.markdown(full_response + "▌")

                        if chunk_counts["start"] == 1:
                            logger.debug(
                                "Text start chunk",
                                content_length=len(chunk["content"]),
                                content_preview=chunk["content"][:50],
                            )

                    elif chunk_type == "delta":
                        chunk_counts["delta"] += 1
                        if not first_chunk_received:
                            logger.info("First chunk received - text delta")
                            status_placeholder.empty()
                            first_chunk_received = True
                        full_response += chunk["content"]
                        message_placeholder.markdown(full_response + "▌")

                        # Log every 50 deltas to avoid spam
                        if chunk_counts["delta"] % 50 == 0:
                            logger.debug("Text streaming", delta_count=chunk_counts["delta"])

                    elif chunk_type == "tool-call":
                        chunk_counts["tool_call"] += 1
                        logger.info(
                            "Tool call chunk received",
                            tool_name=chunk.get("tool_name"),
                            args_type=type(chunk.get("args")).__name__,
                        )
                        # Display tool call in real-time
                        if config.features["tools_visibility"]:
                            with st.expander(f"🔧 Tool: {chunk['tool_name']}", expanded=True):
                                st.info(
                                    "⏳ Tool executing... (result will appear below when complete)"
                                )
                                logger.debug(
                                    f"Tool {chunk['tool_name']} executing, args will be available in final results"
                                )

                    elif chunk_type == "tool-return":
                        chunk_counts["tool_return"] += 1
                        content_str = str(chunk.get("content", ""))
                        logger.info(
                            "Tool return chunk received",
                            tool_name=chunk.get("tool_name", "unknown"),
                            content_length=len(content_str),
                        )
                        # Display tool return in real-time
                        if config.features["tools_visibility"]:
                            with st.expander("📥 Tool Result", expanded=False):
                                st.code(str(chunk["content"])[:500])

                    elif chunk_type == "complete":
                        chunk_counts["complete"] += 1
                        new_messages_count = len(chunk.get("new_messages", []))
                        logger.info(
                            "Stream COMPLETE chunk received",
                            new_messages_count=new_messages_count,
                            full_response_length=len(full_response),
                        )

                        status_placeholder.empty()
                        message_placeholder.markdown(full_response)

                        # Extract and display tool returns from completed messages (for learning)
                        if config.features["tools_visibility"]:
                            for msg in chunk.get("new_messages", []):
                                if isinstance(msg, ModelRequest | ModelResponse):
                                    for part in msg.parts:
                                        if part.part_kind == "tool-return":
                                            chunk_counts["tool_return"] += 1
                                            with st.expander(
                                                f"📥 Tool Result: {part.tool_name}", expanded=False
                                            ):
                                                content_str = str(part.content)
                                                # Show preview if content is very long
                                                if len(content_str) > 2000:
                                                    st.caption(
                                                        f"Result length: {len(content_str)} chars (showing first 2000)"
                                                    )
                                                    st.code(
                                                        content_str[:2000] + "\n\n... (truncated)"
                                                    )
                                                else:
                                                    st.code(content_str)

                        st.session_state.messages.extend(chunk["new_messages"])

                        logger.info(
                            "Messages added to session state",
                            total_message_count=len(st.session_state.messages),
                        )

                        # Set flag to update metrics on next render
                        st.session_state.needs_metrics_update = True

            logger.info(
                "handle_user_input() COMPLETE - streaming finished",
                **chunk_counts,
                final_response_length=len(full_response),
            )

    # Trigger rerun to update sidebar metrics after message is added
    # (applies to both streaming and non-streaming modes)
    if st.session_state.get("needs_metrics_update", False):
        logger.debug("Triggering rerun to update sidebar metrics")
        st.session_state.needs_metrics_update = False
        st.rerun()


async def main():
    st.set_page_config(
        page_title="AI with Apex Advanced RAG Agent",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state=(
            "collapsed"
            if st.session_state.get("config", UIConfig()).mode == UIMode.SIMPLE
            else "expanded"
        ),
    )

    # Check if this is a password reset or email verification page request
    query_params = st.query_params

    # Email verification page (query params: token + action=verify)
    if "token" in query_params and query_params.get("action") == "verify":
        from src.auth.email_verification_page import render_email_verification_page

        render_email_verification_page()
        return  # Stop execution, don't load main app

    # Password reset page (query param: token only, no action)
    if "token" in query_params and "action" not in query_params:
        from src.auth.password_reset_page import render_password_reset_page

        render_password_reset_page()
        return  # Stop execution, don't load main app

    # Require authentication (Layer 2)
    user_name, authenticator = require_authentication()
    logger.info("User authenticated, loading main app", user=user_name)

    # Store authenticator in session state for logout button
    st.session_state.authenticator = authenticator

    initialize_session_state()

    # Render sidebar for configuration
    if st.session_state.config.mode != UIMode.SIMPLE:
        render_sidebar()

    # Get current page
    current_page = st.session_state.get("current_page", "Chat")

    # Render appropriate page
    if current_page == "Dashboard":
        # Dashboard page (only available in Standard/Advanced modes)
        if st.session_state.config.mode != UIMode.SIMPLE:
            await render_dashboard()
        else:
            st.warning("📊 Dashboard is only available in Standard and Advanced modes")
            st.info("Switch to Standard or Advanced mode to access the dashboard")
    else:
        # Main chat interface
        st.title("🤖 AI with Apex Advanced RAG Agent")

        # Mode indicator
        mode = st.session_state.config.mode
        mode_badge = {
            UIMode.SIMPLE: "🟢 Simple",
            UIMode.STANDARD: "🔵 Standard",
            UIMode.ADVANCED: "🟣 Advanced",
        }
        st.caption(f"Mode: {mode_badge[mode]}")

        # Display conversation history
        for msg in st.session_state.messages:
            if isinstance(msg, ModelRequest | ModelResponse):
                for part in msg.parts:
                    display_message_part(part)

        # Chat input
        user_input = st.chat_input("What do you want to do today?")

        if user_input:
            await handle_user_input(user_input)


if __name__ == "__main__":
    asyncio.run(main())
