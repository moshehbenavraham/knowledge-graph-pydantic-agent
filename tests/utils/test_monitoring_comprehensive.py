"""
Comprehensive tests for performance monitoring utilities.

Target coverage: 50% → 75%+
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
from prometheus_client import REGISTRY

from src.utils.monitoring import (
    PerformanceMonitor,
    configure_logging,
    monitor,
    track_performance,
)


class TestConfigureLogging:
    """Test logging configuration."""

    @patch("src.utils.monitoring.get_settings")
    @patch("src.utils.monitoring.structlog.configure")
    def test_configure_logging_default(self, mock_structlog, mock_settings):
        """Test logging configuration with default level."""
        mock_settings_obj = MagicMock()
        mock_settings_obj.log_level = "INFO"
        mock_settings.return_value = mock_settings_obj

        logger = configure_logging()

        assert logger is not None
        mock_structlog.assert_called_once()

    @patch("src.utils.monitoring.get_settings")
    @patch("src.utils.monitoring.structlog.configure")
    def test_configure_logging_debug(self, mock_structlog, mock_settings):
        """Test logging configuration with DEBUG level."""
        mock_settings_obj = MagicMock()
        mock_settings_obj.log_level = "DEBUG"
        mock_settings.return_value = mock_settings_obj

        logger = configure_logging()

        assert logger is not None

    @patch("src.utils.monitoring.get_settings")
    @patch("src.utils.monitoring.structlog.configure")
    def test_configure_logging_error(self, mock_structlog, mock_settings):
        """Test logging configuration with ERROR level."""
        mock_settings_obj = MagicMock()
        mock_settings_obj.log_level = "ERROR"
        mock_settings.return_value = mock_settings_obj

        logger = configure_logging()

        assert logger is not None


class TestPerformanceMonitorInit:
    """Test PerformanceMonitor initialization."""

    def test_init(self):
        """Test monitor initialization."""
        mon = PerformanceMonitor()

        assert isinstance(mon.start_time, float)
        assert isinstance(mon.active_requests, dict)
        assert mon.session_count == 0

    def test_start_metrics_server_success(self):
        """Test starting metrics server."""
        mon = PerformanceMonitor()

        with patch("src.utils.monitoring.start_http_server") as mock_start:
            mon.start_metrics_server(port=8001)
            mock_start.assert_called_once_with(8001)

    def test_start_metrics_server_error(self):
        """Test metrics server error handling."""
        mon = PerformanceMonitor()

        with patch("src.utils.monitoring.start_http_server") as mock_start:
            mock_start.side_effect = OSError("Port already in use")

            # Should not raise error
            mon.start_metrics_server(port=8000)


class TestTrackRequest:
    """Test request tracking."""

    def test_track_request_success(self):
        """Test tracking successful request."""
        mon = PerformanceMonitor()

        with patch("src.utils.monitoring.REQUEST_COUNT") as mock_count:
            with patch("src.utils.monitoring.REQUEST_DURATION") as mock_duration:
                with mon.track_request("GET", "/test", "user-123"):
                    time.sleep(0.01)

                mock_count.labels.assert_called()
                mock_duration.labels.assert_called()

    def test_track_request_error(self):
        """Test tracking failed request."""
        mon = PerformanceMonitor()

        with patch("src.utils.monitoring.REQUEST_COUNT") as mock_count:
            with patch("src.utils.monitoring.REQUEST_DURATION") as mock_duration:
                with patch("src.utils.monitoring.ERROR_COUNT") as mock_error:
                    with pytest.raises(ValueError):
                        with mon.track_request("POST", "/fail"):
                            raise ValueError("Test error")

                    # Should record error status
                    call_args = mock_count.labels.call_args[1]
                    assert call_args["status"] == "error"

    def test_track_request_timing(self):
        """Test request timing accuracy."""
        mon = PerformanceMonitor()

        with patch("src.utils.monitoring.REQUEST_COUNT"):
            with patch("src.utils.monitoring.REQUEST_DURATION") as mock_duration:
                start = time.time()
                with mon.track_request("GET", "/slow"):
                    time.sleep(0.1)
                end = time.time()

                # Verify duration was observed
                mock_duration.labels.return_value.observe.assert_called_once()
                observed_duration = mock_duration.labels.return_value.observe.call_args[0][0]
                assert 0.09 <= observed_duration <= (end - start) + 0.01

    def test_track_request_active_tracking(self):
        """Test active request tracking."""
        mon = PerformanceMonitor()

        with patch("src.utils.monitoring.REQUEST_COUNT"):
            with patch("src.utils.monitoring.REQUEST_DURATION"):
                assert len(mon.active_requests) == 0

                with mon.track_request("GET", "/test", "user-1"):
                    # Should have one active request during execution
                    assert len(mon.active_requests) == 1

                # Should be removed after completion
                assert len(mon.active_requests) == 0


class TestTrackToolExecution:
    """Test tool execution tracking."""

    @pytest.mark.asyncio
    async def test_track_tool_execution_success(self):
        """Test tracking successful tool execution."""
        mon = PerformanceMonitor()

        with patch("src.utils.monitoring.TOOL_EXECUTION_COUNT") as mock_count:
            with patch("src.utils.monitoring.TOOL_EXECUTION_DURATION") as mock_duration:
                async with mon.track_tool_execution("test_tool", "user-123"):
                    await asyncio.sleep(0.01)

                mock_count.labels.assert_called()
                mock_duration.labels.assert_called()

    @pytest.mark.asyncio
    async def test_track_tool_execution_error(self):
        """Test tracking failed tool execution."""
        mon = PerformanceMonitor()

        with patch("src.utils.monitoring.TOOL_EXECUTION_COUNT") as mock_count:
            with patch("src.utils.monitoring.TOOL_EXECUTION_DURATION") as mock_duration:
                with patch("src.utils.monitoring.ERROR_COUNT") as mock_error:
                    with pytest.raises(RuntimeError):
                        async with mon.track_tool_execution("failing_tool"):
                            raise RuntimeError("Tool failed")

                    call_args = mock_count.labels.call_args[1]
                    assert call_args["status"] == "error"

    @pytest.mark.asyncio
    async def test_track_tool_execution_timing(self):
        """Test tool execution timing."""
        mon = PerformanceMonitor()

        with patch("src.utils.monitoring.TOOL_EXECUTION_COUNT"):
            with patch("src.utils.monitoring.TOOL_EXECUTION_DURATION") as mock_duration:
                async with mon.track_tool_execution("slow_tool"):
                    await asyncio.sleep(0.1)

                observed_duration = mock_duration.labels.return_value.observe.call_args[0][0]
                assert observed_duration >= 0.1


class TestTrackDatabaseQuery:
    """Test database query tracking."""

    def test_track_database_query_success(self):
        """Test tracking successful database query."""
        mon = PerformanceMonitor()

        with patch("src.utils.monitoring.DATABASE_QUERY_COUNT") as mock_count:
            with patch("src.utils.monitoring.DATABASE_QUERY_DURATION") as mock_duration:
                with mon.track_database_query("SELECT", "users"):
                    time.sleep(0.01)

                mock_count.labels.assert_called_with(operation="SELECT", table="users", status="success")
                mock_duration.labels.assert_called()

    def test_track_database_query_error(self):
        """Test tracking failed database query."""
        mon = PerformanceMonitor()

        with patch("src.utils.monitoring.DATABASE_QUERY_COUNT") as mock_count:
            with patch("src.utils.monitoring.DATABASE_QUERY_DURATION"):
                with patch("src.utils.monitoring.ERROR_COUNT") as mock_error:
                    with pytest.raises(Exception):
                        with mon.track_database_query("INSERT", "posts"):
                            raise Exception("DB error")

                    call_args = mock_count.labels.call_args[1]
                    assert call_args["status"] == "error"

    def test_track_database_query_timing(self):
        """Test database query timing."""
        mon = PerformanceMonitor()

        with patch("src.utils.monitoring.DATABASE_QUERY_COUNT"):
            with patch("src.utils.monitoring.DATABASE_QUERY_DURATION") as mock_duration:
                with mon.track_database_query("SELECT", "documents"):
                    time.sleep(0.05)

                observed = mock_duration.labels.return_value.observe.call_args[0][0]
                assert observed >= 0.05


class TestTrackLLMTokens:
    """Test LLM token tracking."""

    def test_track_llm_tokens(self):
        """Test tracking LLM token usage."""
        mon = PerformanceMonitor()

        with patch("src.utils.monitoring.LLM_TOKEN_COUNT") as mock_count:
            mon.track_llm_tokens(
                model="gpt-4",
                input_tokens=100,
                output_tokens=50,
                user_id="user-123",
            )

            # Should be called twice (input and output)
            assert mock_count.labels.call_count == 2

            # Verify input tokens
            input_call = mock_count.labels.call_args_list[0]
            assert input_call[1]["type"] == "input"
            mock_count.labels.return_value.inc.assert_called()

    def test_track_llm_tokens_zero(self):
        """Test tracking zero tokens."""
        mon = PerformanceMonitor()

        with patch("src.utils.monitoring.LLM_TOKEN_COUNT") as mock_count:
            mon.track_llm_tokens(model="gpt-4", input_tokens=0, output_tokens=0)

            # Should still be called
            assert mock_count.labels.call_count == 2


class TestSessionCount:
    """Test session count tracking."""

    def test_update_session_count(self):
        """Test updating session count."""
        mon = PerformanceMonitor()

        with patch("src.utils.monitoring.ACTIVE_SESSIONS") as mock_gauge:
            mon.update_session_count(5)

            assert mon.session_count == 5
            mock_gauge.set.assert_called_once_with(5)

    def test_update_session_count_zero(self):
        """Test updating to zero sessions."""
        mon = PerformanceMonitor()

        with patch("src.utils.monitoring.ACTIVE_SESSIONS") as mock_gauge:
            mon.update_session_count(0)

            assert mon.session_count == 0
            mock_gauge.set.assert_called_once_with(0)


class TestSystemStats:
    """Test system statistics."""

    def test_get_system_stats_basic(self):
        """Test getting basic system stats."""
        mon = PerformanceMonitor()

        stats = mon.get_system_stats()

        assert "uptime" in stats
        assert "active_requests" in stats
        assert "active_sessions" in stats
        assert stats["uptime"] >= 0
        assert stats["active_requests"] >= 0

    @patch("src.utils.monitoring.psutil")
    def test_get_system_stats_with_psutil(self, mock_psutil):
        """Test getting stats with psutil available."""
        mock_psutil.virtual_memory.return_value = MagicMock(used=1024 * 1024 * 100)
        mock_psutil.cpu_percent.return_value = 25.5
        mock_psutil.disk_usage.return_value = MagicMock(percent=45.2)

        mon = PerformanceMonitor()

        with patch("src.utils.monitoring.MEMORY_USAGE") as mock_gauge:
            stats = mon.get_system_stats()

            assert "memory_usage" in stats
            assert "cpu_percent" in stats
            assert "disk_usage" in stats
            assert stats["memory_usage"] == 1024 * 1024 * 100
            mock_gauge.set.assert_called_once()

    def test_get_system_stats_without_psutil(self):
        """Test getting stats without psutil."""
        mon = PerformanceMonitor()

        # Temporarily set psutil to None
        with patch("src.utils.monitoring.psutil", None):
            stats = mon.get_system_stats()

            # Should only have basic stats
            assert "uptime" in stats
            assert "memory_usage" not in stats


class TestTrackPerformanceDecorator:
    """Test performance tracking decorator."""

    @pytest.mark.asyncio
    async def test_decorator_async_function(self):
        """Test decorator on async function."""

        @track_performance(tool_name="test_async_tool")
        async def async_function(user_id="test"):
            await asyncio.sleep(0.01)
            return "result"

        with patch("src.utils.monitoring.TOOL_EXECUTION_COUNT"):
            with patch("src.utils.monitoring.TOOL_EXECUTION_DURATION"):
                result = await async_function(user_id="user-123")

                assert result == "result"

    def test_decorator_sync_function(self):
        """Test decorator on sync function."""

        @track_performance(tool_name="test_sync_tool")
        def sync_function(user_id="test"):
            time.sleep(0.01)
            return "result"

        with patch("src.utils.monitoring.TOOL_EXECUTION_COUNT"):
            with patch("src.utils.monitoring.TOOL_EXECUTION_DURATION"):
                result = sync_function(user_id="user-123")

                assert result == "result"

    @pytest.mark.asyncio
    async def test_decorator_async_with_endpoint(self):
        """Test decorator with endpoint parameter."""

        @track_performance(tool_name="api_tool", endpoint="/api/test")
        async def async_endpoint_function(user_id="test"):
            await asyncio.sleep(0.01)
            return "result"

        with patch("src.utils.monitoring.REQUEST_COUNT"):
            with patch("src.utils.monitoring.REQUEST_DURATION"):
                with patch("src.utils.monitoring.TOOL_EXECUTION_COUNT"):
                    with patch("src.utils.monitoring.TOOL_EXECUTION_DURATION"):
                        result = await async_endpoint_function(user_id="user-123")
                        assert result == "result"

    def test_decorator_sync_with_endpoint(self):
        """Test decorator on sync function with endpoint."""

        @track_performance(tool_name="sync_api", endpoint="/api/sync")
        def sync_endpoint_function(user_id="test"):
            time.sleep(0.01)
            return "sync_result"

        with patch("src.utils.monitoring.REQUEST_COUNT"):
            with patch("src.utils.monitoring.REQUEST_DURATION"):
                with patch("src.utils.monitoring.TOOL_EXECUTION_COUNT"):
                    with patch("src.utils.monitoring.TOOL_EXECUTION_DURATION"):
                        result = sync_endpoint_function(user_id="user-123")
                        assert result == "sync_result"

    @pytest.mark.asyncio
    async def test_decorator_async_error(self):
        """Test decorator with async function that errors."""

        @track_performance(tool_name="error_tool")
        async def async_error_function(user_id="test"):
            raise ValueError("Test error")

        with patch("src.utils.monitoring.TOOL_EXECUTION_COUNT"):
            with patch("src.utils.monitoring.TOOL_EXECUTION_DURATION"):
                with patch("src.utils.monitoring.ERROR_COUNT") as mock_error:
                    with pytest.raises(ValueError):
                        await async_error_function()

                    mock_error.labels.assert_called()

    def test_decorator_sync_error(self):
        """Test decorator with sync function that errors."""

        @track_performance(tool_name="sync_error")
        def sync_error_function(user_id="test"):
            raise RuntimeError("Sync error")

        with patch("src.utils.monitoring.TOOL_EXECUTION_COUNT"):
            with patch("src.utils.monitoring.TOOL_EXECUTION_DURATION"):
                with patch("src.utils.monitoring.ERROR_COUNT") as mock_error:
                    with pytest.raises(RuntimeError):
                        sync_error_function()

                    mock_error.labels.assert_called()

    @pytest.mark.asyncio
    async def test_decorator_uses_function_name(self):
        """Test decorator uses function name when tool_name not provided."""

        @track_performance()
        async def my_custom_function(user_id="test"):
            return "result"

        with patch("src.utils.monitoring.TOOL_EXECUTION_COUNT") as mock_count:
            with patch("src.utils.monitoring.TOOL_EXECUTION_DURATION"):
                await my_custom_function()

                # Should use function name
                call_kwargs = mock_count.labels.call_args[1]
                assert call_kwargs["tool_name"] == "my_custom_function"


class TestGlobalMonitorInstance:
    """Test global monitor instance."""

    def test_monitor_exists(self):
        """Test that global monitor instance exists."""
        assert isinstance(monitor, PerformanceMonitor)

    def test_monitor_is_initialized(self):
        """Test that monitor is properly initialized."""
        assert hasattr(monitor, "start_time")
        assert hasattr(monitor, "active_requests")
        assert hasattr(monitor, "session_count")


class TestPrometheusMetrics:
    """Test Prometheus metrics initialization."""

    def test_metrics_exist(self):
        """Test that all monitoring metrics exist."""
        from src.utils.monitoring import (
            ACTIVE_SESSIONS,
            DATABASE_QUERY_COUNT,
            DATABASE_QUERY_DURATION,
            ERROR_COUNT,
            LLM_TOKEN_COUNT,
            MEMORY_USAGE,
            REQUEST_COUNT,
            REQUEST_DURATION,
            TOOL_EXECUTION_COUNT,
            TOOL_EXECUTION_DURATION,
        )

        # Verify all metrics are not None
        assert REQUEST_COUNT is not None
        assert REQUEST_DURATION is not None
        assert TOOL_EXECUTION_COUNT is not None
        assert TOOL_EXECUTION_DURATION is not None
        assert LLM_TOKEN_COUNT is not None
        assert DATABASE_QUERY_COUNT is not None
        assert DATABASE_QUERY_DURATION is not None
        assert MEMORY_USAGE is not None
        assert ACTIVE_SESSIONS is not None
        assert ERROR_COUNT is not None

    def test_request_metrics_labels(self):
        """Test request metrics accept correct labels."""
        from src.utils.monitoring import REQUEST_COUNT, REQUEST_DURATION

        REQUEST_COUNT.labels(method="GET", endpoint="/test", status="success", user_id="user-1")
        REQUEST_DURATION.labels(method="GET", endpoint="/test", user_id="user-1")

    def test_tool_metrics_labels(self):
        """Test tool metrics accept correct labels."""
        from src.utils.monitoring import TOOL_EXECUTION_COUNT, TOOL_EXECUTION_DURATION

        TOOL_EXECUTION_COUNT.labels(tool_name="test_tool", status="success", user_id="user-1")
        TOOL_EXECUTION_DURATION.labels(tool_name="test_tool", user_id="user-1")

    def test_error_metrics_labels(self):
        """Test error metrics accept correct labels."""
        from src.utils.monitoring import ERROR_COUNT

        ERROR_COUNT.labels(error_type="ValueError", component="api", severity="error")
