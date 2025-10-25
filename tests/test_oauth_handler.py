"""Tests for OAuth authentication handler.

Tests cover:
- OAuth client initialization
- Authorization URL generation
- Token exchange and refresh
- User profile retrieval
- Callback handling
- Token encryption/decryption
"""

import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from authlib.oauth2.rfc6749 import OAuth2Token
from cryptography.fernet import Fernet

from src.auth.oauth_handler import (
    OAuthHandler,
    complete_oauth_flow,
    decrypt_token,
    encrypt_token,
    get_encryption_cipher,
    get_oauth_handler,
    initiate_oauth_flow,
)


# =====================================================
# FIXTURES
# =====================================================


@pytest.fixture
def mock_env_oauth(monkeypatch):
    """Set up OAuth environment variables."""
    # Generate test encryption key
    test_key = Fernet.generate_key().decode()

    monkeypatch.setenv("OAUTH_ENCRYPTION_KEY", test_key)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test_google_client_id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test_google_client_secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:8501/oauth/callback/google")
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test_github_client_id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_github_client_secret")
    monkeypatch.setenv("GITHUB_REDIRECT_URI", "http://localhost:8501/oauth/callback/github")

    return {
        "encryption_key": test_key,
        "google_client_id": "test_google_client_id",
        "google_client_secret": "test_google_client_secret",
        "github_client_id": "test_github_client_id",
        "github_client_secret": "test_github_client_secret",
    }


@pytest.fixture
def mock_oauth_token():
    """Mock OAuth2Token response."""
    return OAuth2Token(
        {
            "access_token": "test_access_token_12345",
            "refresh_token": "test_refresh_token_67890",
            "token_type": "Bearer",
            "expires_in": 3600,
            "expires_at": int((datetime.now() + timedelta(hours=1)).timestamp()),
            "scope": "openid email profile",
        }
    )


@pytest.fixture
def mock_google_profile():
    """Mock Google user profile."""
    return {
        "id": "google_user_123456",
        "email": "testuser@gmail.com",
        "verified_email": True,
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
        "picture": "https://lh3.googleusercontent.com/a/default-user",
        "locale": "en",
    }


@pytest.fixture
def mock_github_profile():
    """Mock GitHub user profile."""
    return {
        "id": 12345678,
        "login": "testuser",
        "name": "Test User",
        "email": "testuser@users.noreply.github.com",
        "avatar_url": "https://avatars.githubusercontent.com/u/12345678",
        "bio": "Test bio",
        "public_repos": 10,
        "followers": 5,
    }


@pytest.fixture
def mock_user():
    """Mock user record from database."""
    return {
        "id": str(UUID("12345678-1234-5678-1234-567812345678")),
        "username": "testuser_abcd1234",
        "email": "testuser@gmail.com",
        "full_name": "Test User",
        "auth_method": "oauth",
        "is_active": True,
        "avatar_url": "https://lh3.googleusercontent.com/a/default-user",
        "created_at": datetime.now().isoformat(),
    }


@pytest.fixture
def mock_oauth_account():
    """Mock OAuth account record from database."""
    return {
        "id": str(UUID("87654321-4321-8765-4321-876543218765")),
        "user_id": str(UUID("12345678-1234-5678-1234-567812345678")),
        "provider": "google",
        "provider_user_id": "google_user_123456",
        "access_token": "encrypted_access_token",
        "refresh_token": "encrypted_refresh_token",
        "token_expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
        "profile_data": {
            "email": "testuser@gmail.com",
            "name": "Test User",
            "avatar_url": "https://lh3.googleusercontent.com/a/default-user",
        },
        "is_active": True,
        "created_at": datetime.now().isoformat(),
    }


# =====================================================
# TOKEN ENCRYPTION TESTS
# =====================================================


def test_get_encryption_cipher_success(mock_env_oauth):
    """Test getting encryption cipher with valid key."""
    cipher = get_encryption_cipher()
    assert isinstance(cipher, Fernet)


def test_get_encryption_cipher_no_key(monkeypatch):
    """Test getting encryption cipher without key raises error."""
    monkeypatch.delenv("OAUTH_ENCRYPTION_KEY", raising=False)

    with pytest.raises(ValueError, match="OAUTH_ENCRYPTION_KEY not set"):
        get_encryption_cipher()


def test_encrypt_decrypt_token(mock_env_oauth):
    """Test token encryption and decryption round trip."""
    original_token = "test_access_token_12345"

    # Encrypt
    encrypted = encrypt_token(original_token)
    assert encrypted != original_token
    assert len(encrypted) > len(original_token)

    # Decrypt
    decrypted = decrypt_token(encrypted)
    assert decrypted == original_token


def test_encrypt_token_different_each_time(mock_env_oauth):
    """Test that encrypting same token produces different ciphertext."""
    token = "test_token"

    encrypted1 = encrypt_token(token)
    encrypted2 = encrypt_token(token)

    # Different ciphertexts (Fernet includes random IV)
    assert encrypted1 != encrypted2

    # But both decrypt to same value
    assert decrypt_token(encrypted1) == token
    assert decrypt_token(encrypted2) == token


# =====================================================
# OAUTH HANDLER INITIALIZATION TESTS
# =====================================================


def test_oauth_handler_google_init(mock_env_oauth):
    """Test OAuthHandler initialization for Google."""
    handler = OAuthHandler("google")

    assert handler.provider == "google"
    assert handler.client_id == "test_google_client_id"
    assert handler.client_secret == "test_google_client_secret"
    assert handler.redirect_uri == "http://localhost:8501/oauth/callback/google"
    assert handler.scopes == ["openid", "email", "profile"]


def test_oauth_handler_github_init(mock_env_oauth):
    """Test OAuthHandler initialization for GitHub."""
    handler = OAuthHandler("github")

    assert handler.provider == "github"
    assert handler.client_id == "test_github_client_id"
    assert handler.client_secret == "test_github_client_secret"
    assert handler.redirect_uri == "http://localhost:8501/oauth/callback/github"
    assert handler.scopes == ["read:user", "user:email"]


def test_oauth_handler_unsupported_provider(mock_env_oauth):
    """Test OAuthHandler with unsupported provider raises error."""
    with pytest.raises(ValueError, match="Unsupported OAuth provider: microsoft"):
        OAuthHandler("microsoft")


def test_oauth_handler_missing_credentials(monkeypatch):
    """Test OAuthHandler without credentials raises error."""
    monkeypatch.setenv("OAUTH_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)

    with pytest.raises(ValueError, match="OAuth credentials not configured"):
        OAuthHandler("google")


def test_oauth_handler_default_redirect_uri(monkeypatch):
    """Test OAuthHandler uses default redirect URI if not specified."""
    monkeypatch.setenv("OAUTH_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test_client_secret")
    monkeypatch.delenv("GOOGLE_REDIRECT_URI", raising=False)

    handler = OAuthHandler("google")
    assert handler.redirect_uri == "http://localhost:8501/oauth/callback/google"


# =====================================================
# AUTHORIZATION URL GENERATION TESTS
# =====================================================


def test_get_authorization_url_google(mock_env_oauth):
    """Test generating Google authorization URL."""
    handler = OAuthHandler("google")
    auth_url, state = handler.get_authorization_url()

    assert "accounts.google.com/o/oauth2/v2/auth" in auth_url
    assert f"client_id={handler.client_id}" in auth_url
    assert f"redirect_uri={handler.redirect_uri}" in auth_url
    assert "scope=openid+email+profile" in auth_url
    assert "response_type=code" in auth_url
    assert "access_type=offline" in auth_url  # Google-specific
    assert "prompt=consent" in auth_url  # Google-specific
    assert f"state={state}" in auth_url
    assert len(state) > 20  # Should be random token


def test_get_authorization_url_github(mock_env_oauth):
    """Test generating GitHub authorization URL."""
    handler = OAuthHandler("github")
    auth_url, state = handler.get_authorization_url()

    assert "github.com/login/oauth/authorize" in auth_url
    assert f"client_id={handler.client_id}" in auth_url
    assert f"redirect_uri={handler.redirect_uri}" in auth_url
    assert "scope=read%3Auser+user%3Aemail" in auth_url or "scope=read:user+user:email" in auth_url
    assert "response_type=code" in auth_url
    assert f"state={state}" in auth_url


def test_get_authorization_url_custom_state(mock_env_oauth):
    """Test generating authorization URL with custom state."""
    handler = OAuthHandler("google")
    custom_state = "my_custom_state_12345"

    auth_url, state = handler.get_authorization_url(state=custom_state)

    assert state == custom_state
    assert f"state={custom_state}" in auth_url


def test_get_authorization_url_different_states(mock_env_oauth):
    """Test that different calls generate different state tokens."""
    handler = OAuthHandler("google")

    _, state1 = handler.get_authorization_url()
    _, state2 = handler.get_authorization_url()

    assert state1 != state2


# =====================================================
# TOKEN EXCHANGE TESTS
# =====================================================


@pytest.mark.asyncio
async def test_exchange_code_for_token_success(mock_env_oauth, mock_oauth_token):
    """Test exchanging authorization code for token."""
    handler = OAuthHandler("google")

    with patch("src.auth.oauth_handler.AsyncOAuth2Client") as mock_client:
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.fetch_token = AsyncMock(return_value=mock_oauth_token)
        mock_client.return_value = mock_instance

        token = await handler.exchange_code_for_token("test_auth_code")

        assert token["access_token"] == "test_access_token_12345"
        assert token["refresh_token"] == "test_refresh_token_67890"
        assert token["token_type"] == "Bearer"

        mock_instance.fetch_token.assert_called_once_with(
            handler.token_url,
            code="test_auth_code",
            grant_type="authorization_code",
        )


@pytest.mark.asyncio
async def test_exchange_code_for_token_failure(mock_env_oauth):
    """Test token exchange failure raises exception."""
    handler = OAuthHandler("google")

    with patch("src.auth.oauth_handler.AsyncOAuth2Client") as mock_client:
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.fetch_token = AsyncMock(side_effect=Exception("Invalid code"))
        mock_client.return_value = mock_instance

        with pytest.raises(Exception, match="Invalid code"):
            await handler.exchange_code_for_token("invalid_code")


# =====================================================
# TOKEN REFRESH TESTS
# =====================================================


@pytest.mark.asyncio
async def test_refresh_access_token_success(mock_env_oauth, mock_oauth_token):
    """Test refreshing OAuth access token."""
    handler = OAuthHandler("google")

    new_token = OAuth2Token(
        {
            "access_token": "new_access_token_99999",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
    )

    with patch("src.auth.oauth_handler.AsyncOAuth2Client") as mock_client:
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.refresh_token = AsyncMock(return_value=new_token)
        mock_client.return_value = mock_instance

        refreshed = await handler.refresh_access_token("test_refresh_token")

        assert refreshed["access_token"] == "new_access_token_99999"

        mock_instance.refresh_token.assert_called_once_with(
            handler.token_url,
            refresh_token="test_refresh_token",
        )


@pytest.mark.asyncio
async def test_refresh_access_token_failure(mock_env_oauth):
    """Test token refresh failure raises exception."""
    handler = OAuthHandler("google")

    with patch("src.auth.oauth_handler.AsyncOAuth2Client") as mock_client:
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.refresh_token = AsyncMock(side_effect=Exception("Invalid refresh token"))
        mock_client.return_value = mock_instance

        with pytest.raises(Exception, match="Invalid refresh token"):
            await handler.refresh_access_token("invalid_refresh_token")


# =====================================================
# USER PROFILE TESTS
# =====================================================


@pytest.mark.asyncio
async def test_get_user_profile_google(mock_env_oauth, mock_google_profile):
    """Test getting Google user profile."""
    handler = OAuthHandler("google")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_google_profile
        mock_response.raise_for_status = MagicMock()
        mock_instance.get = AsyncMock(return_value=mock_response)

        mock_client.return_value = mock_instance

        profile = await handler.get_user_profile("test_access_token")

        assert profile["provider_user_id"] == "google_user_123456"
        assert profile["email"] == "testuser@gmail.com"
        assert profile["name"] == "Test User"
        assert profile["avatar_url"] == "https://lh3.googleusercontent.com/a/default-user"
        assert profile["email_verified"] is True
        assert profile["raw"] == mock_google_profile


@pytest.mark.asyncio
async def test_get_user_profile_github(mock_env_oauth, mock_github_profile):
    """Test getting GitHub user profile."""
    handler = OAuthHandler("github")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_github_profile
        mock_response.raise_for_status = MagicMock()
        mock_instance.get = AsyncMock(return_value=mock_response)

        mock_client.return_value = mock_instance

        profile = await handler.get_user_profile("test_access_token")

        assert profile["provider_user_id"] == "12345678"
        assert profile["email"] == "testuser@users.noreply.github.com"
        assert profile["name"] == "Test User"
        assert profile["avatar_url"] == "https://avatars.githubusercontent.com/u/12345678"
        assert profile["email_verified"] is True


@pytest.mark.asyncio
async def test_get_user_profile_github_no_email(mock_env_oauth):
    """Test GitHub profile without email fetches from separate endpoint."""
    handler = OAuthHandler("github")

    # Profile without email
    profile_no_email = {
        "id": 12345678,
        "login": "testuser",
        "name": "Test User",
        "email": None,  # No email in profile
        "avatar_url": "https://avatars.githubusercontent.com/u/12345678",
    }

    # Email response
    email_response_data = [
        {"email": "testuser@gmail.com", "primary": True, "verified": True},
        {"email": "other@gmail.com", "primary": False, "verified": True},
    ]

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()

        # Mock profile response
        mock_profile_response = MagicMock()
        mock_profile_response.status_code = 200
        mock_profile_response.json.return_value = profile_no_email
        mock_profile_response.raise_for_status = MagicMock()

        # Mock email response
        mock_email_response = MagicMock()
        mock_email_response.status_code = 200
        mock_email_response.json.return_value = email_response_data

        # First call returns profile, second call returns emails
        mock_instance.get = AsyncMock(side_effect=[mock_profile_response, mock_email_response])

        mock_client.return_value = mock_instance

        profile = await handler.get_user_profile("test_access_token")

        assert profile["email"] == "testuser@gmail.com"  # Primary email fetched
        assert mock_instance.get.call_count == 2  # Profile + emails


@pytest.mark.asyncio
async def test_get_user_profile_failure(mock_env_oauth):
    """Test profile fetch failure raises exception."""
    handler = OAuthHandler("google")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock_instance.get = AsyncMock(side_effect=Exception("API error"))

        mock_client.return_value = mock_instance

        with pytest.raises(Exception, match="API error"):
            await handler.get_user_profile("invalid_token")


# =====================================================
# CALLBACK HANDLING TESTS
# =====================================================


@pytest.mark.asyncio
async def test_handle_callback_new_user(
    mock_env_oauth, mock_oauth_token, mock_google_profile, mock_user, mock_oauth_account
):
    """Test OAuth callback creates new user."""
    handler = OAuthHandler("google")

    with (
        patch.object(handler, "exchange_code_for_token", return_value=mock_oauth_token),
        patch.object(handler, "get_user_profile") as mock_get_profile,
        patch("src.auth.oauth_handler.get_user_by_email", return_value=None),  # No existing user
        patch("src.auth.oauth_handler.create_user", return_value=mock_user),
        patch("src.auth.oauth_handler.get_oauth_account", return_value=None),  # No existing OAuth account
        patch("src.auth.oauth_handler.link_oauth_account", return_value=mock_oauth_account),
        patch("src.auth.oauth_handler.encrypt_token", side_effect=lambda x: f"encrypted_{x}"),
    ):
        # Mock profile
        mock_get_profile.return_value = {
            "provider_user_id": "google_user_123456",
            "email": "testuser@gmail.com",
            "name": "Test User",
            "avatar_url": "https://lh3.googleusercontent.com/a/default-user",
            "email_verified": True,
        }

        result = await handler.handle_callback("test_auth_code", "test_state")

        assert result["user"] == mock_user
        assert result["is_new_user"] is True
        assert result["oauth_account"] == mock_oauth_account


@pytest.mark.asyncio
async def test_handle_callback_existing_user(
    mock_env_oauth, mock_oauth_token, mock_google_profile, mock_user, mock_oauth_account
):
    """Test OAuth callback with existing user updates tokens."""
    handler = OAuthHandler("google")

    with (
        patch.object(handler, "exchange_code_for_token", return_value=mock_oauth_token),
        patch.object(handler, "get_user_profile") as mock_get_profile,
        patch("src.auth.oauth_handler.get_user_by_email", return_value=mock_user),  # Existing user
        patch(
            "src.auth.oauth_handler.get_oauth_account", return_value=mock_oauth_account
        ),  # Existing OAuth account
        patch("src.auth.oauth_handler.update_oauth_tokens", return_value=mock_oauth_account),
        patch("src.auth.oauth_handler.encrypt_token", side_effect=lambda x: f"encrypted_{x}"),
    ):
        mock_get_profile.return_value = {
            "provider_user_id": "google_user_123456",
            "email": "testuser@gmail.com",
            "name": "Test User",
            "avatar_url": "https://lh3.googleusercontent.com/a/default-user",
            "email_verified": True,
        }

        result = await handler.handle_callback("test_auth_code", "test_state")

        assert result["user"] == mock_user
        assert result["is_new_user"] is False
        assert result["oauth_account"] == mock_oauth_account


@pytest.mark.asyncio
async def test_handle_callback_no_email(mock_env_oauth, mock_oauth_token):
    """Test OAuth callback without email raises error."""
    handler = OAuthHandler("google")

    with (
        patch.object(handler, "exchange_code_for_token", return_value=mock_oauth_token),
        patch.object(handler, "get_user_profile") as mock_get_profile,
    ):
        # Profile without email
        mock_get_profile.return_value = {
            "provider_user_id": "google_user_123456",
            "email": None,  # No email provided
            "name": "Test User",
        }

        with pytest.raises(ValueError, match="did not provide user email"):
            await handler.handle_callback("test_auth_code", "test_state")


# =====================================================
# HELPER FUNCTIONS TESTS
# =====================================================


@pytest.mark.asyncio
async def test_get_oauth_handler(mock_env_oauth):
    """Test getting OAuth handler."""
    handler = await get_oauth_handler("google")
    assert isinstance(handler, OAuthHandler)
    assert handler.provider == "google"


@pytest.mark.asyncio
async def test_initiate_oauth_flow(mock_env_oauth):
    """Test initiating OAuth flow."""
    auth_url, state = await initiate_oauth_flow("google")

    assert "accounts.google.com/o/oauth2/v2/auth" in auth_url
    assert len(state) > 20


@pytest.mark.asyncio
async def test_complete_oauth_flow(
    mock_env_oauth, mock_oauth_token, mock_google_profile, mock_user, mock_oauth_account
):
    """Test completing OAuth flow."""
    with (
        patch("src.auth.oauth_handler.OAuthHandler") as mock_handler_class,
        patch("src.auth.oauth_handler.get_user_by_email", return_value=mock_user),
        patch("src.auth.oauth_handler.get_oauth_account", return_value=mock_oauth_account),
        patch("src.auth.oauth_handler.update_oauth_tokens", return_value=mock_oauth_account),
        patch("src.auth.oauth_handler.encrypt_token", side_effect=lambda x: f"encrypted_{x}"),
    ):
        mock_handler = MagicMock()
        mock_handler.handle_callback = AsyncMock(
            return_value={
                "user": mock_user,
                "is_new_user": False,
                "oauth_account": mock_oauth_account,
            }
        )
        mock_handler_class.return_value = mock_handler

        result = await complete_oauth_flow("google", "test_code", "test_state")

        assert result["user"] == mock_user
        assert result["is_new_user"] is False


# =====================================================
# USERNAME GENERATION TESTS
# =====================================================


def test_generate_username_from_email(mock_env_oauth):
    """Test username generation from email."""
    handler = OAuthHandler("google")

    profile = {"email": "testuser@gmail.com"}
    username = handler._generate_username(profile)

    assert username.startswith("testuser_")
    assert len(username) > len("testuser_")


def test_generate_username_fallback(mock_env_oauth):
    """Test username generation fallback without email."""
    handler = OAuthHandler("google")

    profile = {"email": None}
    username = handler._generate_username(profile)

    assert username.startswith("google_user_")


def test_generate_username_special_characters(mock_env_oauth):
    """Test username generation cleans special characters."""
    handler = OAuthHandler("google")

    profile = {"email": "test.user+tag@gmail.com"}
    username = handler._generate_username(profile)

    # Special characters replaced with underscores
    assert "_" in username
    assert "." not in username
    assert "+" not in username
    assert "@" not in username


def test_generate_username_unique(mock_env_oauth):
    """Test username generation produces unique usernames."""
    handler = OAuthHandler("google")

    profile = {"email": "testuser@gmail.com"}

    username1 = handler._generate_username(profile)
    username2 = handler._generate_username(profile)

    # Should be different due to random suffix
    assert username1 != username2
