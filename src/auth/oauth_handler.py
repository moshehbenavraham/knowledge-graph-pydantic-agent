"""OAuth authentication handler for Google, GitHub, Microsoft, and Apple.

Provides OAuth 2.0 authentication flow integration with support for:
- Authorization URL generation
- Callback handling and token exchange
- Token refresh logic
- User profile retrieval
- Secure token storage in database
"""

import secrets
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
import structlog
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.oauth2.rfc6749 import OAuth2Token
from cryptography.fernet import Fernet

from src.auth.db import (
    create_user,
    get_oauth_account,
    get_user_by_email,
    link_oauth_account,
    update_oauth_tokens,
)
from src.config import get_settings

logger = structlog.get_logger(__name__)

# OAuth provider configurations
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_SCOPES = ["openid", "email", "profile"]

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_SCOPES = ["read:user", "user:email"]

MICROSOFT_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MICROSOFT_USERINFO_URL = "https://graph.microsoft.com/v1.0/me"
MICROSOFT_SCOPES = ["openid", "email", "profile", "User.Read"]

APPLE_AUTH_URL = "https://appleid.apple.com/auth/authorize"
APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
APPLE_USERINFO_URL = (
    "https://appleid.apple.com/auth/token"  # Apple returns user info in token response
)
APPLE_SCOPES = ["name", "email"]


def get_encryption_cipher() -> Fernet:
    """Get Fernet cipher for token encryption.

    Returns:
        Fernet cipher instance

    Raises:
        ValueError: If OAUTH_ENCRYPTION_KEY not set in environment
    """
    settings = get_settings()
    if not settings.oauth_encryption_key:
        raise ValueError(
            "OAUTH_ENCRYPTION_KEY not set. Generate with: "
            "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    return Fernet(settings.oauth_encryption_key.encode())


def encrypt_token(token: str) -> str:
    """Encrypt OAuth token for secure storage.

    Args:
        token: Plain text token

    Returns:
        Encrypted token string
    """
    cipher = get_encryption_cipher()
    return cipher.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt OAuth token from storage.

    Args:
        encrypted_token: Encrypted token string

    Returns:
        Plain text token
    """
    cipher = get_encryption_cipher()
    return cipher.decrypt(encrypted_token.encode()).decode()


class OAuthHandler:
    """OAuth authentication handler for multiple providers."""

    def __init__(self, provider: str):
        """Initialize OAuth handler.

        Args:
            provider: OAuth provider name ('google', 'github', 'microsoft', or 'apple')

        Raises:
            ValueError: If provider not supported or credentials not configured
        """
        self.provider = provider.lower()

        if self.provider not in ["google", "github", "microsoft", "apple"]:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        # Get credentials from centralized settings
        settings = get_settings()

        if self.provider == "google":
            self.client_id = settings.google_client_id
            self.client_secret = settings.google_client_secret
            self.redirect_uri = settings.google_redirect_uri
        elif self.provider == "github":
            self.client_id = settings.github_client_id
            self.client_secret = settings.github_client_secret
            self.redirect_uri = settings.github_redirect_uri
        elif self.provider == "microsoft":
            self.client_id = settings.microsoft_client_id
            self.client_secret = settings.microsoft_client_secret
            self.redirect_uri = settings.microsoft_redirect_uri
        elif self.provider == "apple":
            self.client_id = settings.apple_client_id
            self.client_secret = settings.apple_client_secret
            self.redirect_uri = settings.apple_redirect_uri

        if not self.client_id or not self.client_secret:
            raise ValueError(
                f"OAuth credentials not configured for {self.provider}. "
                f"Set {self.provider.upper()}_CLIENT_ID and {self.provider.upper()}_CLIENT_SECRET in .env"
            )

        if not self.redirect_uri:
            # Default redirect URI
            self.redirect_uri = f"http://localhost:8501/oauth/callback/{self.provider}"
            logger.warning(
                f"Using default redirect URI for {self.provider}",
                redirect_uri=self.redirect_uri,
            )

        # Set provider-specific URLs and scopes
        if self.provider == "google":
            self.auth_url = GOOGLE_AUTH_URL
            self.token_url = GOOGLE_TOKEN_URL
            self.userinfo_url = GOOGLE_USERINFO_URL
            self.scopes = GOOGLE_SCOPES
        elif self.provider == "github":
            self.auth_url = GITHUB_AUTH_URL
            self.token_url = GITHUB_TOKEN_URL
            self.userinfo_url = GITHUB_USER_URL
            self.scopes = GITHUB_SCOPES
        elif self.provider == "microsoft":
            self.auth_url = MICROSOFT_AUTH_URL
            self.token_url = MICROSOFT_TOKEN_URL
            self.userinfo_url = MICROSOFT_USERINFO_URL
            self.scopes = MICROSOFT_SCOPES
        elif self.provider == "apple":
            self.auth_url = APPLE_AUTH_URL
            self.token_url = APPLE_TOKEN_URL
            self.userinfo_url = APPLE_USERINFO_URL
            self.scopes = APPLE_SCOPES

        logger.info(
            f"OAuth handler initialized for {self.provider}",
            client_id=self.client_id[:10] + "...",
            redirect_uri=self.redirect_uri,
        )

    def get_authorization_url(self, state: str | None = None) -> tuple[str, str]:
        """Generate OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection.
                   If not provided, a random state will be generated.

        Returns:
            Tuple of (authorization_url, state)
        """
        if not state:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "response_type": "code",
            "state": state,
        }

        # Provider-specific parameters
        if self.provider == "google":
            params["access_type"] = "offline"
            params["prompt"] = "consent"  # Force consent to get refresh token
        elif self.provider == "microsoft":
            params["response_mode"] = "query"
            params["prompt"] = "select_account"
        elif self.provider == "apple":
            params["response_mode"] = "form_post"  # Apple requires form_post
            # Apple requires nonce for id_token validation
            params["nonce"] = secrets.token_urlsafe(32)

        authorization_url = f"{self.auth_url}?{urlencode(params)}"

        logger.info(
            f"Generated {self.provider} authorization URL",
            state=state[:10] + "...",
        )

        return authorization_url, state

    async def exchange_code_for_token(self, code: str) -> OAuth2Token:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            OAuth2Token with access_token, refresh_token, expires_at

        Raises:
            Exception: If token exchange fails
        """
        async with AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
        ) as client:
            try:
                token = await client.fetch_token(
                    self.token_url,
                    code=code,
                    grant_type="authorization_code",
                )

                logger.info(
                    f"{self.provider} token exchange successful",
                    has_refresh_token=bool(token.get("refresh_token")),
                )

                return token

            except Exception as e:
                logger.error(
                    f"{self.provider} token exchange failed",
                    error=str(e),
                )
                raise

    async def refresh_access_token(self, refresh_token: str) -> OAuth2Token:
        """Refresh OAuth access token.

        Args:
            refresh_token: Refresh token from previous authorization

        Returns:
            New OAuth2Token with updated access_token

        Raises:
            Exception: If token refresh fails
        """
        async with AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
        ) as client:
            try:
                token = await client.refresh_token(
                    self.token_url,
                    refresh_token=refresh_token,
                )

                logger.info(f"{self.provider} token refresh successful")

                return token

            except Exception as e:
                logger.error(
                    f"{self.provider} token refresh failed",
                    error=str(e),
                )
                raise

    async def get_user_profile(self, access_token: str) -> dict[str, Any]:
        """Get user profile from OAuth provider.

        Args:
            access_token: OAuth access token

        Returns:
            User profile dictionary with standardized fields:
            - provider_user_id: Unique user ID from provider
            - email: User email address
            - name: User full name
            - avatar_url: Profile picture URL
            - raw: Raw profile data from provider

        Raises:
            Exception: If profile fetch fails
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        async with (
            httpx.AsyncClient() as client
        ):  # noqa: CONST-III-001 - HTTP client for external API
            try:
                response = await client.get(self.userinfo_url, headers=headers)
                response.raise_for_status()
                profile = response.json()

                # Standardize profile fields across providers
                if self.provider == "google":
                    standardized = {
                        "provider_user_id": profile.get("id"),
                        "email": profile.get("email"),
                        "name": profile.get("name"),
                        "avatar_url": profile.get("picture"),
                        "email_verified": profile.get("verified_email", False),
                    }
                elif self.provider == "github":
                    # GitHub may require additional API call for email
                    email = profile.get("email")
                    if not email:
                        email_response = await client.get(
                            "https://api.github.com/user/emails",
                            headers=headers,
                        )
                        if email_response.status_code == 200:
                            emails = email_response.json()
                            # Get primary verified email
                            primary_emails = [
                                e for e in emails if e.get("primary") and e.get("verified")
                            ]
                            if primary_emails:
                                email = primary_emails[0]["email"]

                    standardized = {
                        "provider_user_id": str(profile.get("id")),
                        "email": email,
                        "name": profile.get("name") or profile.get("login"),
                        "avatar_url": profile.get("avatar_url"),
                        "email_verified": bool(email),  # GitHub emails are verified
                    }
                elif self.provider == "microsoft":
                    standardized = {
                        "provider_user_id": profile.get("id"),
                        "email": profile.get("mail") or profile.get("userPrincipalName"),
                        "name": profile.get("displayName"),
                        "avatar_url": None,  # Microsoft Graph requires separate API call for photo
                        "email_verified": True,  # Microsoft emails are verified
                    }
                elif self.provider == "apple":
                    # Apple provides user info in ID token (decoded JWT)
                    # This is simplified - real implementation should decode ID token
                    standardized = {
                        "provider_user_id": profile.get("sub"),
                        "email": profile.get("email"),
                        "name": profile.get("name", {}).get("firstName", "")
                        + " "
                        + profile.get("name", {}).get("lastName", ""),
                        "avatar_url": None,  # Apple doesn't provide profile pictures
                        "email_verified": profile.get("email_verified", False),
                    }

                standardized["raw"] = profile  # Keep raw data for reference

                logger.info(
                    f"{self.provider} profile retrieved",
                    provider_user_id=standardized["provider_user_id"],
                    has_email=bool(standardized["email"]),
                )

                return standardized

            except Exception as e:
                logger.error(
                    f"{self.provider} profile fetch failed",
                    error=str(e),
                )
                raise

    async def handle_callback(self, code: str, state: str | None = None) -> dict[str, Any]:
        """Handle OAuth callback and complete authentication flow.

        This method:
        1. Exchanges authorization code for tokens
        2. Retrieves user profile from provider
        3. Creates or links user account in database
        4. Stores encrypted tokens in database

        Args:
            code: Authorization code from OAuth callback
            state: State parameter for CSRF validation (optional)

        Returns:
            Dictionary with user information:
            - user: User record from database
            - is_new_user: True if user was just created
            - oauth_account: OAuth account record

        Raises:
            Exception: If any step of the callback handling fails
        """
        try:
            # Step 1: Exchange code for tokens
            token = await self.exchange_code_for_token(code)

            # Step 2: Get user profile
            profile = await self.get_user_profile(token["access_token"])

            if not profile.get("email"):
                raise ValueError(
                    f"{self.provider} did not provide user email. "
                    "Email is required for account creation."
                )

            # Step 3: Get or create user account
            user = get_user_by_email(profile["email"])
            is_new_user = False

            if not user:
                # Create new user with OAuth authentication
                username = self._generate_username(profile)
                user = create_user(
                    username=username,
                    email=profile["email"],
                    full_name=profile["name"] or profile["email"],
                    password=None,  # OAuth-only user
                    auth_method="oauth",
                    avatar_url=profile.get("avatar_url"),
                )
                is_new_user = True

                logger.info(
                    f"Created new user from {self.provider} OAuth",
                    username=username,
                    email=profile["email"],
                )

            # Step 4: Check if OAuth account already linked
            oauth_account = get_oauth_account(
                provider=self.provider,
                provider_user_id=profile["provider_user_id"],
            )

            if oauth_account:
                # Update existing OAuth tokens
                encrypted_access_token = encrypt_token(token["access_token"])
                encrypted_refresh_token = (
                    encrypt_token(token["refresh_token"]) if token.get("refresh_token") else None
                )

                token_expires_at = None
                if token.get("expires_at"):
                    token_expires_at = datetime.fromtimestamp(token["expires_at"])
                elif token.get("expires_in"):
                    token_expires_at = datetime.now() + timedelta(seconds=token["expires_in"])

                oauth_account = await update_oauth_tokens(
                    oauth_account_id=oauth_account["id"],
                    access_token=encrypted_access_token,
                    refresh_token=encrypted_refresh_token,
                    token_expires_at=token_expires_at,
                    profile_data=profile,
                )

                logger.info(
                    f"Updated {self.provider} OAuth tokens",
                    user_id=user["id"],
                )
            else:
                # Link new OAuth account
                encrypted_access_token = encrypt_token(token["access_token"])
                encrypted_refresh_token = (
                    encrypt_token(token["refresh_token"]) if token.get("refresh_token") else None
                )

                token_expires_at = None
                if token.get("expires_at"):
                    token_expires_at = datetime.fromtimestamp(token["expires_at"])
                elif token.get("expires_in"):
                    token_expires_at = datetime.now() + timedelta(seconds=token["expires_in"])

                oauth_account = link_oauth_account(
                    user_id=user["id"],
                    provider=self.provider,
                    provider_user_id=profile["provider_user_id"],
                    access_token=encrypted_access_token,
                    refresh_token=encrypted_refresh_token,
                    token_expires_at=token_expires_at,
                    profile_data=profile,
                )

                logger.info(
                    f"Linked {self.provider} OAuth account",
                    user_id=user["id"],
                )

            return {
                "user": user,
                "is_new_user": is_new_user,
                "oauth_account": oauth_account,
            }

        except Exception as e:
            logger.error(
                f"{self.provider} callback handling failed",
                error=str(e),
            )
            raise

    def _generate_username(self, profile: dict[str, Any]) -> str:
        """Generate unique username from OAuth profile.

        Args:
            profile: User profile from OAuth provider

        Returns:
            Generated username
        """
        # Try to use email prefix first
        email = profile.get("email", "")
        if email and "@" in email:
            base_username = email.split("@")[0]
        else:
            # Fallback to provider user ID
            base_username = f"{self.provider}_user"

        # Add random suffix to ensure uniqueness
        random_suffix = secrets.token_hex(4)
        username = f"{base_username}_{random_suffix}"

        # Clean username (alphanumeric + underscore only)
        username = "".join(c if c.isalnum() or c == "_" else "_" for c in username)

        return username.lower()


async def get_oauth_handler(provider: str) -> OAuthHandler:
    """Get OAuth handler for provider.

    Args:
        provider: OAuth provider name ('google', 'github', 'microsoft', or 'apple')

    Returns:
        Configured OAuthHandler instance

    Raises:
        ValueError: If provider not supported or credentials not configured
    """
    return OAuthHandler(provider)


async def initiate_oauth_flow(provider: str) -> tuple[str, str]:
    """Initiate OAuth authentication flow.

    Args:
        provider: OAuth provider name ('google', 'github', 'microsoft', or 'apple')

    Returns:
        Tuple of (authorization_url, state)

    Raises:
        ValueError: If provider not supported or credentials not configured
    """
    handler = await get_oauth_handler(provider)
    return handler.get_authorization_url()


async def complete_oauth_flow(provider: str, code: str, state: str | None = None) -> dict[str, Any]:
    """Complete OAuth authentication flow.

    Args:
        provider: OAuth provider name ('google', 'github', 'microsoft', or 'apple')
        code: Authorization code from OAuth callback
        state: State parameter for CSRF validation (optional)

    Returns:
        Dictionary with user information (see handle_callback)

    Raises:
        ValueError: If provider not supported or credentials not configured
        Exception: If callback handling fails
    """
    handler = await get_oauth_handler(provider)
    return await handler.handle_callback(code, state)
