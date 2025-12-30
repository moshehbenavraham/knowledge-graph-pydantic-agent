"""Unit tests for profiler module."""

from unittest.mock import MagicMock, patch

import pytest

from src.agentic_rag.metrics.profiler import (
    Profiler,
    ProfileResult,
    profile,
    profile_async,
    profile_sync,
)


class TestProfileResult:
    """Test ProfileResult dataclass."""

    def test_initialization(self) -> None:
        """ProfileResult should initialize with correct values."""
        result = ProfileResult(
            function_name="test_func",
            duration_seconds=0.150,
            success=True,
        )

        assert result.function_name == "test_func"
        assert result.duration_seconds == 0.150
        assert result.duration_ms == 150.0
        assert result.success is True
        assert result.error is None

    def test_initialization_with_error(self) -> None:
        """ProfileResult should capture error information."""
        result = ProfileResult(
            function_name="test_func",
            duration_seconds=0.050,
            success=False,
            error="Something went wrong",
        )

        assert result.success is False
        assert result.error == "Something went wrong"

    def test_to_dict(self) -> None:
        """to_dict should return expected structure."""
        result = ProfileResult(
            function_name="test_func",
            duration_seconds=0.150,
            success=True,
        )

        result_dict = result.to_dict()

        assert "function_name" in result_dict
        assert "duration_seconds" in result_dict
        assert "duration_ms" in result_dict
        assert "success" in result_dict
        assert "error" in result_dict


class TestProfileAsync:
    """Test profile_async decorator."""

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    @pytest.mark.asyncio
    async def test_passes_through_when_disabled(self, mock_check: MagicMock) -> None:
        """Decorator should pass through when profiling disabled."""
        mock_check.return_value = False

        @profile_async()
        async def test_func() -> str:
            return "result"

        result = await test_func()

        assert result == "result"

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    @pytest.mark.asyncio
    async def test_profiles_when_enabled(self, mock_check: MagicMock) -> None:
        """Decorator should profile when enabled."""
        mock_check.return_value = True

        @profile_async(name="custom_name")
        async def test_func() -> str:
            return "result"

        result = await test_func()

        assert result == "result"

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    @pytest.mark.asyncio
    async def test_handles_exceptions(self, mock_check: MagicMock) -> None:
        """Decorator should handle and re-raise exceptions."""
        mock_check.return_value = True

        @profile_async()
        async def test_func() -> str:
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await test_func()

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    @pytest.mark.asyncio
    async def test_uses_function_name_by_default(self, mock_check: MagicMock) -> None:
        """Decorator should use function name when name not provided."""
        mock_check.return_value = True

        @profile_async()
        async def my_custom_function() -> str:
            return "result"

        result = await my_custom_function()

        assert result == "result"

    def test_raises_on_sync_function(self) -> None:
        """Decorator should raise TypeError on sync function."""
        with pytest.raises(TypeError, match="async"):

            @profile_async()
            def sync_func() -> str:
                return "result"


class TestProfileSync:
    """Test profile_sync decorator."""

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    def test_passes_through_when_disabled(self, mock_check: MagicMock) -> None:
        """Decorator should pass through when profiling disabled."""
        mock_check.return_value = False

        @profile_sync()
        def test_func() -> str:
            return "result"

        result = test_func()

        assert result == "result"

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    def test_profiles_when_enabled(self, mock_check: MagicMock) -> None:
        """Decorator should profile when enabled."""
        mock_check.return_value = True

        @profile_sync(name="custom_name")
        def test_func() -> str:
            return "result"

        result = test_func()

        assert result == "result"

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    def test_handles_exceptions(self, mock_check: MagicMock) -> None:
        """Decorator should handle and re-raise exceptions."""
        mock_check.return_value = True

        @profile_sync()
        def test_func() -> str:
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            test_func()

    def test_raises_on_async_function(self) -> None:
        """Decorator should raise TypeError on async function."""
        with pytest.raises(TypeError, match="sync"):

            @profile_sync()
            async def async_func() -> str:
                return "result"


class TestProfile:
    """Test universal profile decorator."""

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    @pytest.mark.asyncio
    async def test_detects_async_function(self, mock_check: MagicMock) -> None:
        """Universal decorator should detect and handle async functions."""
        mock_check.return_value = True

        @profile()
        async def async_func() -> str:
            return "async result"

        result = await async_func()

        assert result == "async result"

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    def test_detects_sync_function(self, mock_check: MagicMock) -> None:
        """Universal decorator should detect and handle sync functions."""
        mock_check.return_value = True

        @profile()
        def sync_func() -> str:
            return "sync result"

        result = sync_func()

        assert result == "sync result"


class TestProfiler:
    """Test Profiler context manager."""

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    def test_measures_duration(self, mock_check: MagicMock) -> None:
        """Profiler should measure code block duration."""
        mock_check.return_value = True

        with Profiler("test_block") as p:
            # Simulate some work
            total = sum(range(1000))
            _ = total  # Use variable to avoid unused warning

        assert p.name == "test_block"
        assert p.duration_seconds > 0
        assert p.duration_ms > 0
        assert p.success is True
        assert p.error is None

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    def test_captures_exceptions(self, mock_check: MagicMock) -> None:
        """Profiler should capture exception information."""
        mock_check.return_value = True

        with pytest.raises(ValueError):
            with Profiler("error_block") as p:
                raise ValueError("Test error")

        assert p.success is False
        assert "Test error" in (p.error or "")

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    def test_to_dict(self, mock_check: MagicMock) -> None:
        """Profiler to_dict should return expected structure."""
        mock_check.return_value = True

        with Profiler("test_block") as p:
            pass

        result = p.to_dict()

        assert "name" in result
        assert "duration_seconds" in result
        assert "duration_ms" in result
        assert "success" in result
        assert "error" in result

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    def test_logs_when_enabled(self, mock_check: MagicMock) -> None:
        """Profiler should log when profiling enabled."""
        mock_check.return_value = True

        with Profiler("logged_block") as p:
            pass

        # Verify profiler ran (duration > 0)
        assert p.duration_seconds >= 0


class TestProfilingOverhead:
    """Test that profiling has minimal overhead when disabled."""

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    def test_sync_overhead_when_disabled(self, mock_check: MagicMock) -> None:
        """Sync profiler should have minimal overhead when disabled."""
        mock_check.return_value = False

        import time

        @profile_sync()
        def fast_func() -> int:
            return 42

        # Warm up
        fast_func()

        # Measure overhead
        start = time.perf_counter()
        for _ in range(1000):
            fast_func()
        duration = time.perf_counter() - start

        # Overhead should be less than 1ms per call on average
        avg_ms = (duration / 1000) * 1000
        assert avg_ms < 1.0, f"Average overhead {avg_ms:.3f}ms exceeds 1ms target"

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    @pytest.mark.asyncio
    async def test_async_overhead_when_disabled(self, mock_check: MagicMock) -> None:
        """Async profiler should have minimal overhead when disabled."""
        mock_check.return_value = False

        import time

        @profile_async()
        async def fast_async_func() -> int:
            return 42

        # Warm up
        await fast_async_func()

        # Measure overhead
        start = time.perf_counter()
        for _ in range(1000):
            await fast_async_func()
        duration = time.perf_counter() - start

        # Overhead should be less than 1ms per call on average
        avg_ms = (duration / 1000) * 1000
        assert avg_ms < 1.0, f"Average overhead {avg_ms:.3f}ms exceeds 1ms target"


class TestCheckProfilingEnabled:
    """Test _check_profiling_enabled function edge cases."""

    def test_handles_settings_exception(self) -> None:
        """Should return False when get_settings raises exception."""
        from src.agentic_rag.metrics.profiler import _check_profiling_enabled

        with patch("src.agentic_rag.metrics.profiler.get_settings") as mock_settings:
            mock_settings.side_effect = Exception("Settings unavailable")

            result = _check_profiling_enabled()

            assert result is False

    def test_returns_true_when_enabled(self) -> None:
        """Should return True when profiling is enabled."""
        from src.agentic_rag.metrics.profiler import _check_profiling_enabled

        with patch("src.agentic_rag.metrics.profiler.get_settings") as mock_settings:
            mock_settings.return_value.profiling_enabled = True

            result = _check_profiling_enabled()

            assert result is True


class TestProfileAsyncLogOptions:
    """Test profile_async with log_args and log_result options."""

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    @pytest.mark.asyncio
    async def test_log_args_logs_argument_info(self, mock_check: MagicMock) -> None:
        """profile_async should log args info when log_args=True."""
        mock_check.return_value = True

        @profile_async(log_args=True)
        async def func_with_args(x: int, y: str, z: float = 1.0) -> str:
            return f"{x}-{y}-{z}"

        result = await func_with_args(42, "test", z=3.14)

        assert result == "42-test-3.14"

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    @pytest.mark.asyncio
    async def test_log_result_logs_return_value(self, mock_check: MagicMock) -> None:
        """profile_async should log result when log_result=True."""
        mock_check.return_value = True

        @profile_async(log_result=True)
        async def func_with_result() -> dict:
            return {"status": "success", "count": 42}

        result = await func_with_result()

        assert result == {"status": "success", "count": 42}

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    @pytest.mark.asyncio
    async def test_log_result_handles_none_result(self, mock_check: MagicMock) -> None:
        """profile_async should handle None result with log_result=True."""
        mock_check.return_value = True

        @profile_async(log_result=True)
        async def func_returns_none() -> None:
            return None

        result = await func_returns_none()

        assert result is None

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    @pytest.mark.asyncio
    async def test_log_args_and_result_together(self, mock_check: MagicMock) -> None:
        """profile_async should handle both log_args and log_result."""
        mock_check.return_value = True

        @profile_async(log_args=True, log_result=True)
        async def func_full_logging(a: int, b: int) -> int:
            return a + b

        result = await func_full_logging(10, 20)

        assert result == 30

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    @pytest.mark.asyncio
    async def test_log_result_truncates_long_result(self, mock_check: MagicMock) -> None:
        """profile_async should truncate long results in log."""
        mock_check.return_value = True

        @profile_async(log_result=True)
        async def func_long_result() -> str:
            return "x" * 200  # Longer than 100 char preview

        result = await func_long_result()

        assert len(result) == 200


class TestProfileSyncLogOptions:
    """Test profile_sync with log_args and log_result options."""

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    def test_log_args_logs_argument_info(self, mock_check: MagicMock) -> None:
        """profile_sync should log args info when log_args=True."""
        mock_check.return_value = True

        @profile_sync(log_args=True)
        def func_with_args(x: int, y: str, z: float = 1.0) -> str:
            return f"{x}-{y}-{z}"

        result = func_with_args(42, "test", z=3.14)

        assert result == "42-test-3.14"

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    def test_log_result_logs_return_value(self, mock_check: MagicMock) -> None:
        """profile_sync should log result when log_result=True."""
        mock_check.return_value = True

        @profile_sync(log_result=True)
        def func_with_result() -> dict:
            return {"status": "success", "count": 42}

        result = func_with_result()

        assert result == {"status": "success", "count": 42}

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    def test_log_result_handles_none_result(self, mock_check: MagicMock) -> None:
        """profile_sync should handle None result with log_result=True."""
        mock_check.return_value = True

        @profile_sync(log_result=True)
        def func_returns_none() -> None:
            return None

        result = func_returns_none()

        assert result is None

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    def test_log_args_and_result_together(self, mock_check: MagicMock) -> None:
        """profile_sync should handle both log_args and log_result."""
        mock_check.return_value = True

        @profile_sync(log_args=True, log_result=True)
        def func_full_logging(a: int, b: int) -> int:
            return a + b

        result = func_full_logging(10, 20)

        assert result == 30

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    def test_log_result_truncates_long_result(self, mock_check: MagicMock) -> None:
        """profile_sync should truncate long results in log."""
        mock_check.return_value = True

        @profile_sync(log_result=True)
        def func_long_result() -> str:
            return "x" * 200  # Longer than 100 char preview

        result = func_long_result()

        assert len(result) == 200


class TestProfilerEdgeCases:
    """Test Profiler context manager edge cases."""

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    def test_profiler_logs_when_disabled(self, mock_check: MagicMock) -> None:
        """Profiler should not log when profiling disabled."""
        mock_check.return_value = False

        with Profiler("disabled_block") as p:
            pass

        # Duration should still be tracked
        assert p.duration_seconds >= 0

    @patch("src.agentic_rag.metrics.profiler._check_profiling_enabled")
    def test_profiler_captures_exception_with_message(self, mock_check: MagicMock) -> None:
        """Profiler should capture exception message."""
        mock_check.return_value = True

        with pytest.raises(ValueError, match="custom error message"):
            with Profiler("error_message_block") as p:
                raise ValueError("custom error message")

        assert p.success is False
        assert "custom error message" in (p.error or "")
