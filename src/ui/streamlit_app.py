import asyncio
from typing import Dict, Any, Optional

import streamlit as st
from httpx import AsyncClient
from pydantic_ai.messages import ModelRequest, ModelResponse

from src.config import UIMode
from src.config.ui import ui_config as config
from src.ui.features import BaseHandler, StreamingHandler, MemoryHandler, MCPHandler
from src.ui.features.base_handler import SimpleHandler


class UIConfig:
    def __init__(self):
        self.mode = config.mode
        self.features = self._get_features_for_mode(self.mode)
    
    @staticmethod
    def _get_features_for_mode(mode: UIMode) -> Dict[str, bool]:
        if mode == UIMode.SIMPLE:
            return {
                "streaming": False,
                "memory": False,
                "mcp": False,
                "tools_visibility": False,
                "metrics": False,
            }
        elif mode == UIMode.STANDARD:
            return {
                "streaming": True,
                "memory": False,
                "mcp": False,
                "tools_visibility": True,
                "metrics": False,
            }
        else:  # ADVANCED
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
        elif self.mode == UIMode.STANDARD:
            return StreamingHandler(config)
        else:  # ADVANCED
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
            st.json(part.args)
    elif part.part_kind == "tool-return" and st.session_state.config.features["tools_visibility"]:
        with st.expander(f"📥 Tool Result"):
            st.code(str(part.content)[:500])


def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "config" not in st.session_state:
        st.session_state.config = UIConfig()
    
    if "handler" not in st.session_state:
        st.session_state.handler = st.session_state.config.get_handler()
        st.session_state.handler.initialize()
    
    if "theme" not in st.session_state:
        st.session_state.theme = "light"


def render_sidebar():
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # UI Mode Selector
        st.subheader("UI Mode")
        current_mode = st.session_state.config.mode
        
        mode_descriptions = {
            UIMode.SIMPLE: "Basic chat interface - Fast and simple",
            UIMode.STANDARD: "Streaming with tools - Recommended",
            UIMode.ADVANCED: "All features - Memory, MCP, metrics"
        }
        
        selected_mode = st.radio(
            "Select mode:",
            options=list(UIMode),
            format_func=lambda x: f"{x.value.title()}",
            index=list(UIMode).index(current_mode),
            help="\n".join([f"**{m.value.title()}**: {d}" for m, d in mode_descriptions.items()])
        )
        
        if selected_mode != current_mode:
            st.session_state.config.mode = selected_mode
            st.session_state.config.features = UIConfig._get_features_for_mode(selected_mode)
            st.session_state.handler = st.session_state.config.get_handler()
            st.session_state.handler.initialize()
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
            new_features["tools_visibility"] = st.checkbox("Show Tool Calls", value=features["tools_visibility"])
            new_features["metrics"] = st.checkbox("Show Metrics", value=features["metrics"])
            
            if new_features != features:
                st.session_state.config.features = new_features
                st.session_state.handler = st.session_state.config.get_handler()
                st.session_state.handler.initialize()
                st.rerun()
        
        st.divider()
        
        # Conversation Management
        st.subheader("Conversation")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Chat"):
                st.session_state.messages = []
                st.rerun()
        
        with col2:
            if st.button("💾 Export Chat"):
                export_conversation()
        
        # Metrics Display
        if st.session_state.config.features.get("metrics"):
            st.divider()
            st.subheader("📊 Metrics")
            st.metric("Messages", len(st.session_state.messages))
            if hasattr(st.session_state.handler, "memory_client") and st.session_state.handler.memory_client:
                st.metric("Memories", "Active")
            else:
                st.metric("Memories", "Inactive")
        
        # About Section
        st.divider()
        st.caption(f"Mode: **{current_mode.value.title()}**")
        st.caption("Powered by Pydantic AI")


def export_conversation():
    import json
    from datetime import datetime
    
    export_data = {
        "timestamp": datetime.now().isoformat(),
        "mode": st.session_state.config.mode.value,
        "messages": []
    }
    
    for msg in st.session_state.messages:
        if isinstance(msg, ModelRequest | ModelResponse):
            for part in msg.parts:
                if part.part_kind in ["user-prompt", "text"] and part.content:
                    export_data["messages"].append({
                        "role": "user" if part.part_kind == "user-prompt" else "assistant",
                        "content": part.content
                    })
    
    st.download_button(
        label="Download JSON",
        data=json.dumps(export_data, indent=2),
        file_name=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )


async def handle_user_input(user_input: str):
    handler = st.session_state.handler
    config = st.session_state.config
    
    with st.chat_message("user"):
        st.markdown(user_input)
    
    with st.chat_message("assistant"):
        if not config.features["streaming"]:
            # Simple mode - no streaming
            with st.spinner("Thinking..."):
                async with AsyncClient() as http_client:
                    result = await handler.run_agent(
                        user_input,
                        st.session_state.messages,
                        http_client
                    )
                    st.markdown(result["response"])
                    st.session_state.messages.extend(result["new_messages"])
        else:
            # Streaming mode
            message_placeholder = st.empty()
            full_response = ""
            
            async with AsyncClient() as http_client:
                async for chunk in handler.run_agent(
                    user_input,
                    st.session_state.messages,
                    http_client
                ):
                    if chunk.get("type") == "start":
                        full_response = chunk["content"]
                        message_placeholder.markdown(full_response + "▌")
                    elif chunk.get("type") == "delta":
                        full_response += chunk["content"]
                        message_placeholder.markdown(full_response + "▌")
                    elif chunk.get("type") == "complete":
                        message_placeholder.markdown(full_response)
                        st.session_state.messages.extend(chunk["new_messages"])


async def main():
    st.set_page_config(
        page_title="Pydantic AI Agent",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="collapsed" if st.session_state.get("config", UIConfig()).mode == UIMode.SIMPLE else "expanded"
    )
    
    initialize_session_state()
    
    # Render sidebar for configuration
    if st.session_state.config.mode != UIMode.SIMPLE:
        render_sidebar()
    
    # Main chat interface
    st.title("🤖 Pydantic AI Agent")
    
    # Mode indicator
    mode = st.session_state.config.mode
    mode_badge = {
        UIMode.SIMPLE: "🟢 Simple",
        UIMode.STANDARD: "🔵 Standard",
        UIMode.ADVANCED: "🟣 Advanced"
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