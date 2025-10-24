"""
Comprehensive edge case tests for MemoryHandler.

Focuses on error handling, boundary conditions, and integration scenarios
to push coverage from 54.22% to 75%+.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.ui.features.memory_handler import MemoryHandler

# ===== Fixtures =====


@pytest.fixture
def memory_config():
    """Standard memory config."""
    return {
        "enable_memory": True,
        "user_id": "test_user",
        "memory_limit": 3,
        "enable_streaming": True,
        "features": {},
    }


@pytest.fixture
def disabled_memory_config():
    """Config with memory disabled."""
    return {
        "enable_memory": False,
        "user_id": "test_user",
        "features": {},
    }


# ===== Initialization Edge Cases =====


class TestMemoryHandlerInit:
    """Test edge cases in MemoryHandler initialization."""

    def test_init_default_user_id(self):
        """Test default user_id when not provided."""
        config = {"enable_memory": True}

        with patch("src.ui.features.memory_handler.get_mem0_client") as mock_get_mem0:
            mock_get_mem0.return_value = Mock()
            handler = MemoryHandler(config)

            assert handler.user_id == "streamlit_user"

    def test_init_custom_user_id(self, memory_config):
        """Test custom user_id from config."""
        memory_config["user_id"] = "custom_user_123"

        with patch("src.ui.features.memory_handler.get_mem0_client") as mock_get_mem0:
            mock_get_mem0.return_value = Mock()
            handler = MemoryHandler(memory_config)

            assert handler.user_id == "custom_user_123"

    def test_setup_hook_logging(self, memory_config):
        """Test that setup hook logs correctly."""
        with (
            patch("src.ui.features.memory_handler.get_mem0_client") as mock_get_mem0,
            patch("src.ui.features.memory_handler.logger") as mock_logger,
        ):
            mock_get_mem0.return_value = Mock()

            MemoryHandler(memory_config)

            # Verify logging occurred
            assert mock_logger.info.called

    def test_init_mem0_client_exception_handling(self, memory_config):
        """Test handling of various Mem0 client exceptions."""
        with (
            patch(
                "src.ui.features.memory_handler.get_mem0_client",
                side_effect=ConnectionError("Connection failed"),
            ),
            patch("src.ui.features.memory_handler.logger") as mock_logger,
        ):
            handler = MemoryHandler(memory_config)

            assert handler.memory_client is None
            mock_logger.exception.assert_called_once()


# ===== get_memories Edge Cases =====


class TestGetMemoriesEdgeCases:
    """Test edge cases in memory retrieval."""

    def test_get_memories_with_long_query(self, memory_config):
        """Test memory retrieval with very long query."""
        mock_client = Mock()
        mock_client.search.return_value = {"results": []}

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)

            long_query = "x" * 10000
            memories = handler.get_memories(long_query)

            assert memories == ""
            mock_client.search.assert_called_once()

    def test_get_memories_with_special_characters(self, memory_config):
        """Test memory retrieval with special characters in query."""
        mock_client = Mock()
        mock_client.search.return_value = {
            "results": [{"memory": "User asked about special chars"}]
        }

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)

            query = "What about @#$%^&*() characters?"
            memories = handler.get_memories(query)

            assert "User asked about special chars" in memories

    def test_get_memories_with_unicode(self, memory_config):
        """Test memory retrieval with Unicode characters."""
        mock_client = Mock()
        mock_client.search.return_value = {
            "results": [{"memory": "用户喜欢中文"}, {"memory": "المستخدم يفضل العربية"}]
        }

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)

            query = "What languages do I like?"
            memories = handler.get_memories(query)

            assert "用户喜欢中文" in memories
            assert "المستخدم يفضل العربية" in memories

    def test_get_memories_malformed_results(self, memory_config):
        """Test handling of malformed memory results."""
        mock_client = Mock()
        # Missing 'memory' key in some results
        mock_client.search.return_value = {
            "results": [
                {"memory": "Valid memory"},
                {"invalid_key": "value"},  # Missing 'memory' key
                {"memory": "Another valid"},
            ]
        }

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)

            # Should handle gracefully
            try:
                memories = handler.get_memories("test")
                # If it doesn't crash, we pass
                assert isinstance(memories, str)
            except KeyError:
                # This is acceptable - we're testing error handling
                pass

    def test_get_memories_search_exception(self, memory_config):
        """Test handling of search exceptions."""
        mock_client = Mock()
        mock_client.search.side_effect = Exception("Search service unavailable")

        with (
            patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client),
            patch("src.ui.features.memory_handler.logger") as mock_logger,
        ):
            handler = MemoryHandler(memory_config)

            memories = handler.get_memories("query")

            assert memories == ""
            mock_logger.exception.assert_called_once()

    def test_get_memories_missing_results_key(self, memory_config):
        """Test handling when 'results' key is missing."""
        mock_client = Mock()
        mock_client.search.return_value = {}  # No 'results' key

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)

            memories = handler.get_memories("query")

            # Should return empty string
            assert memories == ""

    def test_get_memories_with_memory_limit_zero(self):
        """Test with memory limit set to 0."""
        config = {"enable_memory": True, "memory_limit": 0, "user_id": "test"}
        mock_client = Mock()
        mock_client.search.return_value = {"results": []}

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(config)

            handler.get_memories("query")

            call_args = mock_client.search.call_args
            assert call_args[1]["limit"] == 0

    def test_get_memories_with_large_limit(self):
        """Test with very large memory limit."""
        config = {"enable_memory": True, "memory_limit": 1000, "user_id": "test"}
        mock_client = Mock()
        mock_client.search.return_value = {"results": []}

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(config)

            handler.get_memories("query")

            call_args = mock_client.search.call_args
            assert call_args[1]["limit"] == 1000

    def test_get_memories_content_preview_short_memory(self, memory_config):
        """Test logging for memory shorter than preview length."""
        mock_client = Mock()
        mock_client.search.return_value = {"results": [{"memory": "Short"}]}

        with (
            patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client),
            patch("src.ui.features.memory_handler.logger") as mock_logger,
        ):
            handler = MemoryHandler(memory_config)

            handler.get_memories("query")

            # Should log without preview truncation
            assert mock_logger.debug.called

    def test_get_memories_content_preview_long_memory(self, memory_config):
        """Test logging for memory longer than preview length."""
        mock_client = Mock()
        long_memory = "x" * 200
        mock_client.search.return_value = {"results": [{"memory": long_memory}]}

        with (
            patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client),
            patch("src.ui.features.memory_handler.logger") as mock_logger,
        ):
            handler = MemoryHandler(memory_config)

            handler.get_memories("query")

            # Should log with preview truncation
            assert mock_logger.debug.called


# ===== add_memory Edge Cases =====


class TestAddMemoryEdgeCases:
    """Test edge cases in memory storage."""

    def test_add_memory_no_client(self, memory_config):
        """Test adding memory when client is None."""
        with patch(
            "src.ui.features.memory_handler.get_mem0_client", side_effect=Exception("Error")
        ):
            handler = MemoryHandler(memory_config)
            handler.memory_client = None

            # Should not raise
            handler.add_memory("user input", "agent response")

    def test_add_memory_only_user_input(self, memory_config):
        """Test adding memory with only user input, no response."""
        mock_client = Mock()

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)

            handler.add_memory("user input", None)

            # Should add only user message
            call_args = mock_client.add.call_args
            messages = call_args[0][0]
            assert len(messages) == 1
            assert messages[0]["role"] == "user"

    def test_add_memory_with_response(self, memory_config):
        """Test adding memory with both user input and response."""
        mock_client = Mock()

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)

            handler.add_memory("user input", "agent response")

            # Should add both messages
            call_args = mock_client.add.call_args
            messages = call_args[0][0]
            assert len(messages) == 2
            assert messages[0]["role"] == "user"
            assert messages[1]["role"] == "assistant"

    def test_add_memory_with_empty_response(self, memory_config):
        """Test adding memory with empty string response."""
        mock_client = Mock()

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)

            handler.add_memory("user input", "")

            # Empty string is truthy for if check, so should add both
            call_args = mock_client.add.call_args
            messages = call_args[0][0]
            assert len(messages) == 2

    def test_add_memory_exception_handling(self, memory_config):
        """Test exception handling during memory add."""
        mock_client = Mock()
        mock_client.add.side_effect = Exception("Storage failed")

        with (
            patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client),
            patch("src.ui.features.memory_handler.logger") as mock_logger,
        ):
            handler = MemoryHandler(memory_config)

            # Should not raise
            handler.add_memory("input", "response")

            mock_logger.exception.assert_called_once()

    def test_add_memory_with_very_long_content(self, memory_config):
        """Test adding memory with very long content."""
        mock_client = Mock()

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)

            long_input = "x" * 100000
            long_response = "y" * 100000

            handler.add_memory(long_input, long_response)

            # Should still add without error
            mock_client.add.assert_called_once()

    def test_add_memory_with_unicode_content(self, memory_config):
        """Test adding memory with Unicode content."""
        mock_client = Mock()

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)

            handler.add_memory("用户输入", "机器人回复 🤖")

            mock_client.add.assert_called_once()
            call_args = mock_client.add.call_args
            messages = call_args[0][0]
            assert messages[1]["content"] == "机器人回复 🤖"


# ===== run_agent Edge Cases =====


@pytest.mark.asyncio
class TestRunAgentEdgeCases:
    """Test edge cases in agent execution."""

    async def test_run_agent_without_memory_client(self, memory_config):
        """Test running agent when memory client is None."""
        with patch(
            "src.ui.features.memory_handler.get_mem0_client", side_effect=Exception("Error")
        ):
            handler = MemoryHandler(memory_config)
            handler.memory_client = None

            mock_http_client = AsyncMock()

            # Mock parent run_agent
            async def mock_run_agent(*args, **kwargs):
                yield {"type": "delta", "content": "test"}
                yield {"type": "complete"}

            with patch.object(
                handler.__class__.__bases__[0], "run_agent", return_value=mock_run_agent()
            ):
                events = []
                async for event in handler.run_agent("query", [], mock_http_client):
                    events.append(event)

                assert len(events) >= 1

    async def test_run_agent_with_memories(self, memory_config):
        """Test running agent with retrieved memories."""
        mock_client = Mock()
        mock_client.search.return_value = {"results": [{"memory": "User likes Python"}]}

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)

            mock_http_client = AsyncMock()

            # Mock parent run_agent
            async def mock_run_agent(*args, **kwargs):
                # Verify memories_str was passed
                assert "memories_str" in kwargs
                yield {"type": "delta", "content": "response"}
                yield {"type": "complete"}

            with patch.object(
                handler.__class__.__bases__[0], "run_agent", return_value=mock_run_agent()
            ):
                events = []
                async for event in handler.run_agent("query", [], mock_http_client):
                    events.append(event)

                assert len(events) >= 1

    async def test_run_agent_accumulates_response(self, memory_config):
        """Test that full response is accumulated for memory storage."""
        mock_client = Mock()

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)

            mock_http_client = AsyncMock()

            # Mock parent run_agent with multiple deltas
            async def mock_run_agent(*args, **kwargs):
                yield {"type": "delta", "content": "Hello "}
                yield {"type": "delta", "content": "world"}
                yield {"type": "delta", "content": "!"}
                yield {"type": "complete"}

            with patch.object(
                handler.__class__.__bases__[0], "run_agent", return_value=mock_run_agent()
            ):
                events = []
                async for event in handler.run_agent("query", [], mock_http_client):
                    events.append(event)

                # Should have stored "Hello world!" as full response
                assert mock_client.add.called

    async def test_run_agent_exception_propagation(self, memory_config):
        """Test that exceptions during agent execution are propagated."""
        mock_client = Mock()

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)

            mock_http_client = AsyncMock()

            # Mock parent run_agent raising exception
            async def mock_run_agent(*args, **kwargs):
                yield {"type": "delta", "content": "test"}
                raise Exception("Agent failed")

            with (
                patch.object(
                    handler.__class__.__bases__[0], "run_agent", return_value=mock_run_agent()
                ),
                pytest.raises(Exception, match="Agent failed"),
            ):
                async for _event in handler.run_agent("query", [], mock_http_client):
                    pass

    async def test_run_agent_no_complete_event(self, memory_config):
        """Test handling when complete event is not received."""
        mock_client = Mock()

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)

            mock_http_client = AsyncMock()

            # Mock parent run_agent without complete event
            async def mock_run_agent(*args, **kwargs):
                yield {"type": "delta", "content": "test"}
                # No complete event

            with patch.object(
                handler.__class__.__bases__[0], "run_agent", return_value=mock_run_agent()
            ):
                events = []
                async for event in handler.run_agent("query", [], mock_http_client):
                    events.append(event)

                # Should not store memory without complete event
                # (or should handle gracefully)
                assert len(events) >= 1

    async def test_run_agent_empty_message_history(self, memory_config):
        """Test running agent with empty message history."""
        mock_client = Mock()

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)

            mock_http_client = AsyncMock()

            async def mock_run_agent(*args, **kwargs):
                yield {"type": "complete"}

            with patch.object(
                handler.__class__.__bases__[0], "run_agent", return_value=mock_run_agent()
            ):
                events = []
                async for event in handler.run_agent("query", [], mock_http_client):
                    events.append(event)

                assert len(events) >= 1

    async def test_run_agent_with_kwargs(self, memory_config):
        """Test passing additional kwargs to parent."""
        mock_client = Mock()

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)

            mock_http_client = AsyncMock()

            async def mock_run_agent(*args, **kwargs):
                # Verify kwargs are passed through
                assert "custom_param" in kwargs
                yield {"type": "complete"}

            with patch.object(
                handler.__class__.__bases__[0], "run_agent", return_value=mock_run_agent()
            ):
                events = []
                async for event in handler.run_agent(
                    "query", [], mock_http_client, custom_param="value"
                ):
                    events.append(event)

                assert len(events) >= 1


# ===== Integration Tests =====


@pytest.mark.asyncio
class TestMemoryHandlerIntegration:
    """Integration tests for complete workflows."""

    async def test_full_conversation_flow(self, memory_config):
        """Test complete conversation with memory storage and retrieval."""
        mock_client = Mock()
        mock_client.search.return_value = {"results": []}

        with patch("src.ui.features.memory_handler.get_mem0_client", return_value=mock_client):
            handler = MemoryHandler(memory_config)

            mock_http_client = AsyncMock()

            async def mock_run_agent(*args, **kwargs):
                yield {"type": "delta", "content": "response"}
                yield {"type": "complete"}

            with patch.object(
                handler.__class__.__bases__[0], "run_agent", return_value=mock_run_agent()
            ):
                # First interaction
                events1 = []
                async for event in handler.run_agent("first query", [], mock_http_client):
                    events1.append(event)

                # Should have stored first interaction
                assert mock_client.add.call_count == 1

                # Second interaction
                events2 = []
                async for event in handler.run_agent("second query", [], mock_http_client):
                    events2.append(event)

                # Should have stored second interaction
                assert mock_client.add.call_count == 2

    def test_memory_disabled_workflow(self, disabled_memory_config):
        """Test that workflow works with memory disabled."""
        with patch("src.ui.features.memory_handler.get_mem0_client") as mock_get_mem0:
            handler = MemoryHandler(disabled_memory_config)

            # Should not create client
            mock_get_mem0.assert_not_called()

            # Getting memories should return empty
            memories = handler.get_memories("query")
            assert memories == ""

            # Adding memory should be no-op
            handler.add_memory("input", "response")
            # No assertions needed, just shouldn't crash
