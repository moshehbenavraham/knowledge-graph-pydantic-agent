"""
Comprehensive tests for src/auth/captcha.py.

Tests CAPTCHA verification to prevent automated attacks.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.auth.captcha import (
    CaptchaManager,
    get_captcha_manager,
    should_show_captcha,
    verify_captcha,
)


class TestCaptchaManagerInit:
    """Test CaptchaManager initialization."""

    def test_init_default_provider(self):
        """Test initialization with default provider."""
        manager = CaptchaManager(provider="hcaptcha", site_key="site123", secret_key="secret123")

        assert manager.provider == "hcaptcha"
        assert manager.site_key == "site123"
        assert manager.secret_key == "secret123"

    def test_init_recaptcha_v2(self):
        """Test initialization with reCAPTCHA v2."""
        manager = CaptchaManager(
            provider="recaptcha_v2", site_key="site123", secret_key="secret123"
        )

        assert manager.provider == "recaptcha_v2"

    def test_init_recaptcha_v3(self):
        """Test initialization with reCAPTCHA v3."""
        manager = CaptchaManager(
            provider="recaptcha_v3", site_key="site123", secret_key="secret123"
        )

        assert manager.provider == "recaptcha_v3"

    def test_init_case_insensitive(self):
        """Test provider is case insensitive."""
        manager = CaptchaManager(provider="HCAPTCHA", site_key="key", secret_key="secret")

        assert manager.provider == "hcaptcha"

    @patch("src.auth.captcha.get_settings")
    def test_init_without_keys_uses_settings(self, mock_get_settings):
        """Test initialization without keys uses settings."""
        mock_settings = MagicMock()
        mock_settings.hcaptcha_site_key = "site_from_settings"
        mock_settings.hcaptcha_secret_key = "secret_from_settings"
        mock_get_settings.return_value = mock_settings

        manager = CaptchaManager(provider="hcaptcha")

        assert manager.site_key == "site_from_settings"
        assert manager.secret_key == "secret_from_settings"


class TestCaptchaManagerConfiguration:
    """Test configuration checks."""

    def test_is_configured_true(self):
        """Test when properly configured."""
        manager = CaptchaManager(provider="hcaptcha", site_key="site", secret_key="secret")

        assert manager.is_configured() is True

    def test_is_configured_missing_site_key(self):
        """Test when site key missing."""
        manager = CaptchaManager(provider="hcaptcha", site_key="", secret_key="secret")

        assert manager.is_configured() is False

    def test_is_configured_missing_secret_key(self):
        """Test when secret key missing."""
        manager = CaptchaManager(provider="hcaptcha", site_key="site", secret_key="")

        assert manager.is_configured() is False

    def test_is_configured_both_missing(self):
        """Test when both keys missing."""
        manager = CaptchaManager(provider="hcaptcha", site_key="", secret_key="")

        assert manager.is_configured() is False


class TestCaptchaVerification:
    """Test CAPTCHA verification."""

    @pytest.mark.asyncio
    async def test_verify_when_not_configured(self):
        """Test verification when CAPTCHA not configured."""
        manager = CaptchaManager(provider="hcaptcha", site_key="", secret_key="")

        is_valid, error = await manager.verify_response("token")

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_verify_hcaptcha_success(self):
        """Test successful hCaptcha verification."""
        manager = CaptchaManager(provider="hcaptcha", site_key="site", secret_key="secret")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch.object(manager, "_log_challenge", new_callable=AsyncMock):
                is_valid, error = await manager.verify_response("response_token")

                assert is_valid is True
                assert error is None

    @pytest.mark.asyncio
    async def test_verify_hcaptcha_failure(self):
        """Test failed hCaptcha verification."""
        manager = CaptchaManager(provider="hcaptcha", site_key="site", secret_key="secret")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": False, "error-codes": ["invalid-input"]}
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch.object(manager, "_log_challenge", new_callable=AsyncMock):
                is_valid, error = await manager.verify_response("response_token")

                assert is_valid is False
                assert error is not None

    @pytest.mark.asyncio
    async def test_verify_recaptcha_v2_success(self):
        """Test successful reCAPTCHA v2 verification."""
        manager = CaptchaManager(provider="recaptcha_v2", site_key="site", secret_key="secret")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch.object(manager, "_log_challenge", new_callable=AsyncMock):
                is_valid, error = await manager.verify_response("response_token")

                assert is_valid is True
                assert error is None

    @pytest.mark.asyncio
    async def test_verify_recaptcha_v3_success_high_score(self):
        """Test reCAPTCHA v3 with high score."""
        manager = CaptchaManager(provider="recaptcha_v3", site_key="site", secret_key="secret")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True, "score": 0.9}
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch.object(manager, "_log_challenge", new_callable=AsyncMock):
                is_valid, error = await manager.verify_response("response_token")

                assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_recaptcha_v3_failure_low_score(self):
        """Test reCAPTCHA v3 with low score."""
        manager = CaptchaManager(provider="recaptcha_v3", site_key="site", secret_key="secret")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True, "score": 0.3}
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch.object(manager, "_log_challenge", new_callable=AsyncMock):
                is_valid, error = await manager.verify_response("response_token")

                assert is_valid is False

    @pytest.mark.asyncio
    async def test_verify_with_ip_address(self):
        """Test verification with IP address."""
        manager = CaptchaManager(provider="hcaptcha", site_key="site", secret_key="secret")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch.object(manager, "_log_challenge", new_callable=AsyncMock):
                is_valid, error = await manager.verify_response(
                    "token", username="user", ip_address="1.2.3.4"
                )

                assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_http_error(self):
        """Test verification with HTTP error."""
        manager = CaptchaManager(provider="hcaptcha", site_key="site", secret_key="secret")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch.object(manager, "_log_challenge", new_callable=AsyncMock):
                is_valid, error = await manager.verify_response("token")

                assert is_valid is False
                assert "HTTP 500" in error

    @pytest.mark.asyncio
    async def test_verify_timeout(self):
        """Test verification timeout."""
        manager = CaptchaManager(provider="hcaptcha", site_key="site", secret_key="secret")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch.object(manager, "_log_challenge", new_callable=AsyncMock):
                is_valid, error = await manager.verify_response("token")

                assert is_valid is False
                assert "timeout" in error.lower()

    @pytest.mark.asyncio
    async def test_verify_exception(self):
        """Test verification with general exception."""
        manager = CaptchaManager(provider="hcaptcha", site_key="site", secret_key="secret")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.post = AsyncMock(side_effect=Exception("Network error"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch.object(manager, "_log_challenge", new_callable=AsyncMock):
                is_valid, error = await manager.verify_response("token")

                assert is_valid is False
                assert "error" in error.lower()


class TestCaptchaWidgetHTML:
    """Test widget HTML generation."""

    def test_get_widget_html_hcaptcha(self):
        """Test hCaptcha widget HTML."""
        manager = CaptchaManager(provider="hcaptcha", site_key="site123", secret_key="secret")

        html = manager.get_widget_html()

        assert "h-captcha" in html
        assert "site123" in html
        assert "hcaptcha.com" in html

    def test_get_widget_html_recaptcha_v2(self):
        """Test reCAPTCHA v2 widget HTML."""
        manager = CaptchaManager(provider="recaptcha_v2", site_key="site123", secret_key="secret")

        html = manager.get_widget_html()

        assert "g-recaptcha" in html
        assert "site123" in html
        assert "google.com/recaptcha" in html

    def test_get_widget_html_recaptcha_v3(self):
        """Test reCAPTCHA v3 widget HTML."""
        manager = CaptchaManager(provider="recaptcha_v3", site_key="site123", secret_key="secret")

        html = manager.get_widget_html()

        assert "grecaptcha" in html
        assert "site123" in html
        assert "hidden" in html

    def test_get_widget_html_dark_theme(self):
        """Test widget HTML with dark theme."""
        manager = CaptchaManager(provider="hcaptcha", site_key="site123", secret_key="secret")

        html = manager.get_widget_html(theme="dark")

        assert "dark" in html

    def test_get_widget_html_not_configured(self):
        """Test widget HTML when not configured."""
        manager = CaptchaManager(provider="hcaptcha", site_key="", secret_key="")

        html = manager.get_widget_html()

        assert html == ""


class TestCaptchaLogging:
    """Test CAPTCHA challenge logging."""

    @pytest.mark.asyncio
    @patch("src.auth.captcha.get_supabase_client")
    async def test_log_challenge(self, mock_get_client):
        """Test logging challenge."""
        manager = CaptchaManager(provider="hcaptcha", site_key="site", secret_key="secret")

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value = None

        # Need to await get_client since it's async
        mock_get_client.return_value = mock_client
        manager.client = mock_client  # Set directly to avoid async issues

        await manager._log_challenge(
            success=True,
            response_time_ms=150,
            username="testuser",
            ip_address="1.2.3.4",
        )

        mock_table.insert.assert_called_once()
        call_args = mock_table.insert.call_args[0][0]
        assert call_args["success"] is True
        assert call_args["response_time_ms"] == 150
        assert call_args["username"] == "testuser"
        assert call_args["ip_address"] == "1.2.3.4"

    @pytest.mark.asyncio
    async def test_log_challenge_minimal(self):
        """Test logging challenge with minimal data."""
        manager = CaptchaManager(provider="hcaptcha", site_key="site", secret_key="secret")

        with patch("src.auth.captcha.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_client.table.return_value = mock_table
            mock_table.insert.return_value.execute.return_value = None
            mock_get_client.return_value = mock_client
            manager.client = mock_client

            await manager._log_challenge(success=False, response_time_ms=50)

            mock_table.insert.assert_called_once()


class TestSingletonFunction:
    """Test singleton getter function."""

    def test_get_captcha_manager(self):
        """Test getting CAPTCHA manager singleton."""
        manager1 = get_captcha_manager(site_key="key1", secret_key="secret1")
        manager2 = get_captcha_manager(site_key="key2", secret_key="secret2")

        # Should return same instance (singleton)
        assert manager1 is manager2

    @patch("src.auth.captcha.get_settings")
    def test_get_captcha_manager_uses_settings(self, mock_get_settings):
        """Test manager uses settings when no params provided."""
        mock_settings = MagicMock()
        mock_settings.captcha_provider = "recaptcha_v2"
        mock_settings.recaptcha_site_key = "site"
        mock_settings.recaptcha_secret_key = "secret"
        mock_get_settings.return_value = mock_settings

        # Reset singleton
        import src.auth.captcha as captcha_module

        captcha_module._captcha_manager = None

        manager = get_captcha_manager()

        assert manager is not None


class TestHelperFunctions:
    """Test helper functions."""

    @pytest.mark.asyncio
    @patch("src.auth.captcha.get_settings")
    async def test_should_show_captcha_below_threshold(self, mock_get_settings):
        """Test should not show below threshold."""
        mock_settings = MagicMock()
        mock_settings.captcha_threshold = 3
        mock_get_settings.return_value = mock_settings

        result = await should_show_captcha("user", failed_attempts=2)

        assert result is False

    @pytest.mark.asyncio
    @patch("src.auth.captcha.get_settings")
    async def test_should_show_captcha_at_threshold(self, mock_get_settings):
        """Test should show at threshold."""
        mock_settings = MagicMock()
        mock_settings.captcha_threshold = 3
        mock_get_settings.return_value = mock_settings

        result = await should_show_captcha("user", failed_attempts=3)

        assert result is True

    @pytest.mark.asyncio
    @patch("src.auth.captcha.get_settings")
    async def test_should_show_captcha_above_threshold(self, mock_get_settings):
        """Test should show above threshold."""
        mock_settings = MagicMock()
        mock_settings.captcha_threshold = 3
        mock_get_settings.return_value = mock_settings

        result = await should_show_captcha("user", failed_attempts=5)

        assert result is True

    @pytest.mark.asyncio
    async def test_verify_captcha_success(self):
        """Test verify_captcha helper success."""
        with patch("src.auth.captcha.get_captcha_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.verify_response = AsyncMock(return_value=(True, None))
            mock_get_manager.return_value = mock_manager

            is_valid, error = await verify_captcha("token", "user", "1.2.3.4")

            assert is_valid is True
            assert error == ""

    @pytest.mark.asyncio
    async def test_verify_captcha_failure(self):
        """Test verify_captcha helper failure."""
        with patch("src.auth.captcha.get_captcha_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.verify_response = AsyncMock(return_value=(False, "Invalid response"))
            mock_get_manager.return_value = mock_manager

            is_valid, error = await verify_captcha("token")

            assert is_valid is False
            assert error == "Invalid response"

    @pytest.mark.asyncio
    async def test_verify_captcha_no_error_message(self):
        """Test verify_captcha when no error message."""
        with patch("src.auth.captcha.get_captcha_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.verify_response = AsyncMock(return_value=(False, None))
            mock_get_manager.return_value = mock_manager

            is_valid, error = await verify_captcha("token")

            assert is_valid is False
            assert "failed" in error.lower()


class TestEdgeCases:
    """Test edge cases."""

    def test_manager_get_site_key_no_provider_attribute(self):
        """Test _get_site_key with missing settings attribute."""
        with patch("src.auth.captcha.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            # Don't set any captcha attributes
            mock_settings.hcaptcha_site_key = None
            mock_get_settings.return_value = mock_settings

            manager = CaptchaManager(provider="hcaptcha")

            # Should handle gracefully
            assert manager.site_key == "" or manager.site_key is None

    @pytest.mark.asyncio
    async def test_verify_with_empty_response_token(self):
        """Test verification with empty token."""
        manager = CaptchaManager(provider="hcaptcha", site_key="site", secret_key="secret")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": False}
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch.object(manager, "_log_challenge", new_callable=AsyncMock):
                is_valid, error = await manager.verify_response("")

                assert is_valid is False

    def test_widget_html_unknown_provider(self):
        """Test widget HTML with unknown provider."""
        manager = CaptchaManager(provider="unknown", site_key="site", secret_key="secret")

        html = manager.get_widget_html()

        # Should return empty or handle gracefully
        assert html == ""
