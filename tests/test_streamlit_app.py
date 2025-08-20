import pytest
import os
import sys
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, call

# Mock Streamlit functions before importing the app
sys.modules['streamlit'] = MagicMock()
sys.modules['streamlit.runtime.scriptrunner.script_run_context'] = MagicMock()
sys.modules['streamlit.runtime.caching'] = MagicMock()
sys.modules['streamlit.session_state'] = MagicMock()
sys.modules['streamlit.elements.empty'] = MagicMock()
sys.modules['streamlit.elements.markdown'] = MagicMock()
sys.modules['streamlit.elements.chat'] = MagicMock()


# Add src directory to path to import the module
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from ui.streamlit_app import (
    get_agent_deps,
    initialize_mem0,
    display_message_part,
    run_agent_with_streaming,
    main as streamlit_main # Rename to avoid conflict with pytest main
)
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart, PartDeltaEvent, PartStartEvent, TextPartDelta
from agent.agent import AgentDeps # Import AgentDeps for mocking


class TestStreamlitApp:
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        # Reset Streamlit mocks before each test
        sys.modules['streamlit'].reset_mock()
        sys.modules['streamlit.session_state'].reset_mock()
        sys.modules['streamlit.session_state'].messages = [] # Ensure messages is empty for each test

        # Mock external dependencies
        with patch('ui.streamlit_app.get_agent_clients') as mock_get_agent_clients,
             patch('ui.streamlit_app.get_mem0_client') as mock_get_mem0_client,
             patch('ui.streamlit_app.agent') as mock_agent,
             patch('ui.streamlit_app.AsyncClient') as MockAsyncClient,
             patch('ui.streamlit_app.os.getenv') as mock_getenv:
            
            # Configure get_agent_clients mock
            mock_embedding_client = MagicMock()
            mock_supabase_client = MagicMock()
            mock_get_agent_clients.return_value = (mock_embedding_client, mock_supabase_client)

            # Configure get_mem0_client mock
            mock_mem0_client = MagicMock()
            mock_mem0_client.search.return_value = {"results": []} # Default no memories
            mock_mem0_client.add.return_value = None
            mock_get_mem0_client.return_value = mock_mem0_client

            # Configure agent mock
            mock_agent_run_mcp_servers = AsyncMock()
            mock_agent.run_mcp_servers.return_value.__aenter__.return_value = mock_agent_run_mcp_servers
            mock_agent.run_mcp_servers.return_value.__aexit__.return_value = None

            mock_agent_iter = AsyncMock()
            mock_agent.iter.return_value.__aenter__.return_value = mock_agent_iter
            mock_agent.iter.return_value.__aexit__.return_value = None
            mock_agent_iter.result = MagicMock()
            mock_agent_iter.result.new_messages.return_value = [] # Default no new messages

            # Configure AsyncClient mock
            mock_http_client = AsyncMock()
            MockAsyncClient.return_value.__aenter__.return_value = mock_http_client
            MockAsyncClient.return_value.__aexit__.return_value = None

            # Configure os.getenv mock
            mock_getenv.side_effect = lambda key, default=None: {
                "BRAVE_API_KEY": "test_brave_key",
                "SEARXNG_BASE_URL": "test_searxng_url"
            }.get(key, default)

            self.mock_get_agent_clients = mock_get_agent_clients
            self.mock_get_mem0_client = mock_get_mem0_client
            self.mock_agent = mock_agent
            self.MockAsyncClient = MockAsyncClient
            self.mock_getenv = mock_getenv
            self.mock_mem0_client = mock_mem0_client
            self.mock_agent_iter = mock_agent_iter
            self.mock_http_client = mock_http_client

            yield

    def test_get_agent_deps(self):
        deps = get_agent_deps()
        self.mock_get_agent_clients.assert_called_once()
        assert deps == self.mock_get_agent_clients.return_value

    def test_initialize_mem0(self):
        mem0 = initialize_mem0()
        self.mock_get_mem0_client.assert_called_once()
        assert mem0 == self.mock_get_mem0_client.return_value

    def test_display_message_part_user_prompt(self):
        mock_st = sys.modules['streamlit']
        part = UserPromptPart(content="Hello user")
        display_message_part(part)
        mock_st.chat_message.assert_called_once_with("user")
        mock_st.markdown.assert_called_once_with("Hello user")

    def test_display_message_part_text(self):
        mock_st = sys.modules['streamlit']
        part = TextPart(content="Hello assistant")
        display_message_part(part)
        mock_st.chat_message.assert_called_once_with("assistant")
        mock_st.markdown.assert_called_once_with("Hello assistant")

    @pytest.mark.asyncio
    async def test_run_agent_with_streaming_basic_flow(self):
        mock_st = sys.modules['streamlit']
        user_input = "test query"
        
        # Mock agent.iter to yield some events
        async def mock_agent_iter_yield():
            yield MagicMock(spec=Agent, is_model_request_node=lambda x: True, stream=AsyncMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(
                __aiter__=AsyncMock(return_value=[
                    PartStartEvent(part=TextPart(content="Hello")),
                    PartDeltaEvent(delta=TextPartDelta(content_delta=" world")),
                    PartDeltaEvent(delta=TextPartDelta(content_delta="!"))
                ])
            ))))) # Corrected: Removed unnecessary backslashes before newlines and quotes
            
        self.mock_agent_iter.__aiter__.return_value = mock_agent_iter_yield() # Corrected: Removed unnecessary backslashes before newlines and quotes
        
        # Mock new_messages to return some messages
        self.mock_agent_iter.result.new_messages.return_value = [TextPart(content="Full response")]

        # Run the streaming function
        generator = run_agent_with_streaming(user_input)
        full_response = ""
        async for message_chunk in generator:
            full_response += message_chunk
        
        # Assertions
        self.mock_mem0_client.search.assert_called_once_with(query=user_input, user_id="streamlit_user", limit=3)
        self.mock_get_agent_clients.assert_called_once()
        self.MockAsyncClient.assert_called_once()
        self.mock_agent.run_mcp_servers.assert_called_once()
        self.mock_agent.iter.assert_called_once()
        
        assert full_response == "Hello world!"
        assert mock_st.session_state.messages == [TextPart(content="Full response")]
        self.mock_mem0_client.add.assert_called_once_with([{"role": "user", "content": user_input}], user_id="streamlit_user")

    @pytest.mark.asyncio
    async def test_main_function_flow(self):
        mock_st = sys.modules['streamlit']
        mock_st.chat_input.return_value = "User input test"
        mock_st.empty.return_value = MagicMock()
        
        # Mock the streaming generator
        async def mock_streaming_generator():
            yield "chunk1"
            yield "chunk2"
        
        with patch('ui.streamlit_app.run_agent_with_streaming', return_value=mock_streaming_generator()) as mock_run_agent_with_streaming:
            await streamlit_main()
            
            # Assertions
            assert mock_st.session_state.messages == [] # Initialized
            mock_st.title.assert_called_once_with("Pydantic AI Agent")
            mock_st.chat_input.assert_called_once_with("What do you want to do today?")
            
            # User message displayed
            mock_st.chat_message.assert_any_call("user")
            mock_st.markdown.assert_any_call("User input test")
            
            # Assistant message streaming
            mock_st.chat_message.assert_any_call("assistant")
            mock_st.empty.return_value.markdown.assert_has_calls([
                call("chunk1▌"),
                call("chunk1chunk2▌"),
                call("chunk1chunk2")
            ])
            mock_run_agent_with_streaming.assert_called_once_with("User input test")
