"""
CAPTCHA Module

This module provides CAPTCHA verification to prevent automated attacks
after failed login attempts.

Supported providers:
- hCaptcha (default, privacy-friendly)
- Google reCAPTCHA v2
- Google reCAPTCHA v3 (score-based)

Features:
- Automatic CAPTCHA trigger after failed login attempts
- Multiple provider support with fallback
- Response verification with provider APIs
- Logging of CAPTCHA challenges and results
"""

from datetime import datetime

import httpx

from src.clients.database import get_supabase_client
from src.config import get_settings
from supabase import Client

settings = get_settings()


class CaptchaManager:
    """Manages CAPTCHA challenges and verification."""

    # API endpoints
    HCAPTCHA_VERIFY_URL = "https://hcaptcha.com/siteverify"
    RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"

    # Timeouts
    VERIFY_TIMEOUT = 10.0  # seconds

    def __init__(
        self,
        provider: str = "hcaptcha",
        site_key: str | None = None,
        secret_key: str | None = None,
    ):
        """
        Initialize CAPTCHA Manager.

        Args:
            provider: CAPTCHA provider ('hcaptcha', 'recaptcha_v2', 'recaptcha_v3')
            site_key: Public site key from provider
            secret_key: Secret key from provider
        """
        self.provider = provider.lower()
        self.site_key = site_key or self._get_site_key()
        self.secret_key = secret_key or self._get_secret_key()
        self.client: Client | None = None

    def _get_site_key(self) -> str:
        """Get site key from environment based on provider."""
        if self.provider == "hcaptcha":
            return getattr(settings, "hcaptcha_site_key", "")
        if self.provider.startswith("recaptcha"):
            return getattr(settings, "recaptcha_site_key", "")
        return ""

    def _get_secret_key(self) -> str:
        """Get secret key from environment based on provider."""
        if self.provider == "hcaptcha":
            return getattr(settings, "hcaptcha_secret_key", "")
        if self.provider.startswith("recaptcha"):
            return getattr(settings, "recaptcha_secret_key", "")
        return ""

    async def _get_client(self) -> Client:
        """Get Supabase client (cached)."""
        if not self.client:
            self.client = await get_supabase_client()
        return self.client

    def is_configured(self) -> bool:
        """
        Check if CAPTCHA is properly configured.

        Returns:
            True if site_key and secret_key are set
        """
        return bool(self.site_key and self.secret_key)

    async def verify_response(
        self,
        response_token: str,
        username: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[bool, str | None]:
        """
        Verify CAPTCHA response with provider API.

        Args:
            response_token: Response token from CAPTCHA widget
            username: Optional username for logging
            ip_address: Optional IP address for verification and logging

        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if verification succeeded
            - (False, error_message) if verification failed
        """
        if not self.is_configured():
            # CAPTCHA not configured - allow through but log
            await self._log_challenge(
                username=username,
                ip_address=ip_address,
                success=True,
                response_time_ms=0,
            )
            return (True, None)

        start_time = datetime.utcnow()

        try:
            # Choose verification URL based on provider
            if self.provider == "hcaptcha":
                verify_url = self.HCAPTCHA_VERIFY_URL
                data = {
                    "secret": self.secret_key,
                    "response": response_token,
                }
                if ip_address:
                    data["remoteip"] = ip_address

            else:  # recaptcha
                verify_url = self.RECAPTCHA_VERIFY_URL
                data = {
                    "secret": self.secret_key,
                    "response": response_token,
                }
                if ip_address:
                    data["remoteip"] = ip_address

            # Send verification request
            async with httpx.AsyncClient(  # noqa: CONST-III-001 - HTTP client for external API
                timeout=self.VERIFY_TIMEOUT
            ) as client:
                response = await client.post(verify_url, data=data)

            response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            if response.status_code != 200:
                error_msg = f"CAPTCHA API error: HTTP {response.status_code}"
                await self._log_challenge(
                    username=username,
                    ip_address=ip_address,
                    success=False,
                    response_time_ms=response_time_ms,
                )
                return (False, error_msg)

            result = response.json()

            # Check verification result
            if self.provider == "hcaptcha":
                is_valid = result.get("success", False)
                error_codes = result.get("error-codes", [])

            else:  # recaptcha
                is_valid = result.get("success", False)
                error_codes = result.get("error-codes", [])

                # For reCAPTCHA v3, also check score
                if self.provider == "recaptcha_v3":
                    score = result.get("score", 0.0)
                    # Score ranges from 0.0 (bot) to 1.0 (human)
                    # Threshold: 0.5 or higher is considered human
                    if score < 0.5:
                        is_valid = False
                        error_codes.append(f"low_score_{score}")

            # Log challenge
            await self._log_challenge(
                username=username,
                ip_address=ip_address,
                success=is_valid,
                response_time_ms=response_time_ms,
            )

            if not is_valid:
                error_msg = (
                    f"CAPTCHA verification failed: {', '.join(error_codes)}"
                    if error_codes
                    else "CAPTCHA verification failed"
                )
                return (False, error_msg)

            return (True, None)

        except httpx.TimeoutException:
            response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            await self._log_challenge(
                username=username,
                ip_address=ip_address,
                success=False,
                response_time_ms=response_time_ms,
            )
            return (False, "CAPTCHA verification timeout")

        except Exception as e:
            response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            await self._log_challenge(
                username=username,
                ip_address=ip_address,
                success=False,
                response_time_ms=response_time_ms,
            )
            return (False, f"CAPTCHA verification error: {e!s}")

    def get_widget_html(self, theme: str = "light") -> str:
        """
        Get HTML code for CAPTCHA widget.

        Args:
            theme: Widget theme ('light' or 'dark')

        Returns:
            HTML string for embedding CAPTCHA widget
        """
        if not self.is_configured():
            return ""

        if self.provider == "hcaptcha":
            return f"""
            <div class="h-captcha" data-sitekey="{self.site_key}" data-theme="{theme}"></div>
            <script src="https://js.hcaptcha.com/1/api.js" async defer></script>
            """

        if self.provider == "recaptcha_v2":
            return f"""
            <div class="g-recaptcha" data-sitekey="{self.site_key}" data-theme="{theme}"></div>
            <script src="https://www.google.com/recaptcha/api.js" async defer></script>
            """

        if self.provider == "recaptcha_v3":
            # reCAPTCHA v3 runs in background (no checkbox)
            return f"""
            <script src="https://www.google.com/recaptcha/api.js?render={self.site_key}"></script>
            <script>
                grecaptcha.ready(function() {{
                    grecaptcha.execute('{self.site_key}', {{action: 'login'}}).then(function(token) {{
                        document.getElementById('g-recaptcha-response').value = token;
                    }});
                }});
            </script>
            <input type="hidden" id="g-recaptcha-response" name="g-recaptcha-response">
            """

        return ""

    async def _log_challenge(
        self,
        success: bool,
        response_time_ms: int,
        username: str | None = None,
        ip_address: str | None = None,
    ) -> None:
        """
        Log CAPTCHA challenge to database.

        Args:
            success: Whether verification succeeded
            response_time_ms: Response time in milliseconds
            username: Optional username
            ip_address: Optional IP address
        """
        client = await self._get_client()

        data = {
            "challenge_type": self.provider,
            "success": success,
            "response_time_ms": response_time_ms,
        }

        if username:
            data["username"] = username
        if ip_address:
            data["ip_address"] = ip_address

        client.table("auth_captcha_challenges").insert(data).execute()


# Singleton instance
_captcha_manager: CaptchaManager | None = None


def get_captcha_manager(
    provider: str | None = None,
    site_key: str | None = None,
    secret_key: str | None = None,
) -> CaptchaManager:
    """
    Get singleton CAPTCHA Manager instance.

    Args:
        provider: CAPTCHA provider (default from settings)
        site_key: Site key (default from settings)
        secret_key: Secret key (default from settings)

    Returns:
        CaptchaManager instance
    """
    global _captcha_manager

    if _captcha_manager is None:
        provider = provider or getattr(settings, "captcha_provider", "hcaptcha")
        _captcha_manager = CaptchaManager(
            provider=provider, site_key=site_key, secret_key=secret_key
        )

    return _captcha_manager


# Helper functions for integration with existing auth system


async def should_show_captcha(username: str, failed_attempts: int = 0) -> bool:
    """
    Determine if CAPTCHA should be shown based on failed login attempts.

    Args:
        username: Username attempting login
        failed_attempts: Number of recent failed attempts

    Returns:
        True if CAPTCHA should be shown, False otherwise
    """
    # Show CAPTCHA after 3 failed attempts
    threshold = getattr(settings, "captcha_threshold", 3)
    return failed_attempts >= threshold


async def verify_captcha(
    response_token: str,
    username: str | None = None,
    ip_address: str | None = None,
) -> tuple[bool, str]:
    """
    Verify CAPTCHA response.

    Args:
        response_token: Response token from CAPTCHA widget
        username: Optional username
        ip_address: Optional IP address

    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if valid
        - (False, error_message) if invalid
    """
    manager = get_captcha_manager()
    is_valid, error = await manager.verify_response(response_token, username, ip_address)

    if not is_valid:
        return (False, error or "CAPTCHA verification failed")

    return (True, "")
