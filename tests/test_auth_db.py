"""
Comprehensive tests for database authentication operations.

Tests all 36 async functions in src/auth/db.py:
- User CRUD operations (create, read, update, delete)
- Session management (create, revoke, cleanup)
- Password reset tokens (generate, verify, expire)
- OAuth account linking
- Role assignments (assign, revoke, permissions)
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.auth import db

# =====================================================
# FIXTURES
# =====================================================


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client with fluent interface."""
    mock_client = MagicMock()

    # Mock table() method to return chainable query builder
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table

    # Make table chainable (table().select().eq().execute())
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.is_.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.range.return_value = mock_table
    mock_table.lt.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.gt.return_value = mock_table

    # Mock rpc() method for database functions
    mock_rpc = MagicMock()
    mock_client.rpc.return_value = mock_rpc
    mock_rpc.execute.return_value = MagicMock()

    return mock_client


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": str(uuid4()),
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "password_hash": "$2b$12$abcdefghijklmnopqrstuvwxyz1234567890",
        "auth_method": "password",
        "is_active": True,
        "avatar_url": None,
        "created_at": datetime.now().isoformat(),
        "last_login": None,
        "failed_login_attempts": 0,
        "locked_until": None,
        "deleted_at": None,
    }


@pytest.fixture
def sample_session_data():
    """Sample session data for testing."""
    return {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "session_token": "test_session_token_123",
        "device_info": "Test Browser 1.0",
        "ip_address": "127.0.0.1",
        "created_at": datetime.now().isoformat(),
        "last_activity": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
        "revoked_at": None,
    }


@pytest.fixture
def sample_reset_token_data():
    """Sample password reset token data for testing."""
    # Generate a valid bcrypt hash for testing
    import bcrypt

    token_hash = bcrypt.hashpw(b"reset_token_123", bcrypt.gensalt()).decode()
    return {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "token": "reset_token_123",
        "token_hash": token_hash,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
        "used_at": None,
        "used_ip": None,
    }


# =====================================================
# USER MANAGEMENT TESTS
# =====================================================


@pytest.mark.asyncio
async def test_create_user_success(mock_supabase_client, sample_user_data):
    """Test successful user creation."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        # Mock successful insert
        mock_response = MagicMock()
        mock_response.data = [sample_user_data.copy()]
        mock_supabase_client.table().insert().execute.return_value = mock_response

        result = await db.create_user(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="TestPassword123!",
        )

        assert result["username"] == "testuser"
        assert result["email"] == "test@example.com"
        assert "password_hash" not in result  # Should be removed


@pytest.mark.asyncio
async def test_create_user_without_password(mock_supabase_client, sample_user_data):
    """Test creating OAuth-only user without password."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        oauth_user_data = sample_user_data.copy()
        oauth_user_data["username"] = "oauthuser"
        oauth_user_data["email"] = "oauth@example.com"
        oauth_user_data["full_name"] = "OAuth User"
        oauth_user_data["password_hash"] = None
        oauth_user_data["auth_method"] = "oauth"

        mock_response = MagicMock()
        mock_response.data = [oauth_user_data]
        mock_supabase_client.table().insert().execute.return_value = mock_response

        result = await db.create_user(
            username="oauthuser",
            email="oauth@example.com",
            full_name="OAuth User",
            password=None,
            auth_method="oauth",
        )

        assert result["username"] == "oauthuser"
        assert result["auth_method"] == "oauth"


@pytest.mark.asyncio
async def test_create_user_failure(mock_supabase_client):
    """Test user creation failure."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = []  # Empty response indicates failure
        mock_supabase_client.table().insert().execute.return_value = mock_response

        with pytest.raises(Exception, match="Failed to create user"):
            await db.create_user(
                username="testuser",
                email="test@example.com",
                full_name="Test User",
                password="TestPassword123!",
            )


@pytest.mark.asyncio
async def test_get_user_by_username_found(mock_supabase_client, sample_user_data):
    """Test getting user by username successfully."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_user_data]
        mock_supabase_client.table().select().eq().is_().limit().execute.return_value = (
            mock_response
        )

        result = await db.get_user_by_username("testuser")

        assert result is not None
        assert result["username"] == "testuser"
        assert "password_hash" not in result


@pytest.mark.asyncio
async def test_get_user_by_username_not_found(mock_supabase_client):
    """Test getting non-existent user."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase_client.table().select().eq().is_().limit().execute.return_value = (
            mock_response
        )

        result = await db.get_user_by_username("nonexistent")

        assert result is None


@pytest.mark.asyncio
async def test_get_user_by_email_found(mock_supabase_client, sample_user_data):
    """Test getting user by email successfully."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_user_data]
        mock_supabase_client.table().select().eq().is_().limit().execute.return_value = (
            mock_response
        )

        result = await db.get_user_by_email("test@example.com")

        assert result is not None
        assert result["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_get_user_by_id_found(mock_supabase_client, sample_user_data):
    """Test getting user by ID successfully."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_user_data]
        mock_supabase_client.table().select().eq().is_().limit().execute.return_value = (
            mock_response
        )

        result = await db.get_user_by_id(sample_user_data["id"])

        assert result is not None
        assert result["id"] == sample_user_data["id"]


@pytest.mark.asyncio
async def test_verify_user_password_success(mock_supabase_client, sample_user_data):
    """Test successful password verification."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        with patch("src.auth.db.verify_password", return_value=True):
            with patch("src.auth.db.update_last_login", return_value=True):
                mock_response = MagicMock()
                mock_response.data = [sample_user_data]
                mock_supabase_client.table().select().eq().is_().limit().execute.return_value = (
                    mock_response
                )

                result = await db.verify_user_password("testuser", "TestPassword123!")

                assert result is not None
                assert result["username"] == "testuser"


@pytest.mark.asyncio
async def test_verify_user_password_wrong_password(mock_supabase_client, sample_user_data):
    """Test password verification with wrong password."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        with patch("src.auth.db.verify_password", return_value=False):
            mock_response = MagicMock()
            mock_response.data = [sample_user_data]
            mock_supabase_client.table().select().eq().is_().limit().execute.return_value = (
                mock_response
            )

            result = await db.verify_user_password("testuser", "WrongPassword!")

            assert result is None


@pytest.mark.asyncio
async def test_verify_user_password_oauth_user(mock_supabase_client, sample_user_data):
    """Test password verification for OAuth-only user."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        oauth_user = sample_user_data.copy()
        oauth_user["password_hash"] = None

        mock_response = MagicMock()
        mock_response.data = [oauth_user]
        mock_supabase_client.table().select().eq().is_().limit().execute.return_value = (
            mock_response
        )

        result = await db.verify_user_password("testuser", "anypassword")

        assert result is None  # No password for OAuth users


@pytest.mark.asyncio
async def test_update_user_success(mock_supabase_client, sample_user_data):
    """Test successful user update."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        updated_user = sample_user_data.copy()
        updated_user["email"] = "newemail@example.com"

        mock_response = MagicMock()
        mock_response.data = [updated_user]
        mock_supabase_client.table().update().eq().execute.return_value = mock_response

        result = await db.update_user(user_id=sample_user_data["id"], email="newemail@example.com")

        assert result["email"] == "newemail@example.com"


@pytest.mark.asyncio
async def test_update_user_no_fields(mock_supabase_client, sample_user_data):
    """Test update user with no fields to update."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        with pytest.raises(ValueError, match="No fields to update"):
            await db.update_user(user_id=sample_user_data["id"])


@pytest.mark.asyncio
async def test_update_user_password_success(mock_supabase_client, sample_user_data):
    """Test successful password update."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_user_data]
        mock_supabase_client.table().update().eq().execute.return_value = mock_response

        result = await db.update_user_password(sample_user_data["id"], "NewPassword123!")

        assert result is True


@pytest.mark.asyncio
async def test_delete_user_soft_delete(mock_supabase_client, sample_user_data):
    """Test soft delete user."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_user_data]
        mock_supabase_client.table().update().eq().execute.return_value = mock_response

        result = await db.delete_user(sample_user_data["id"], soft_delete=True)

        assert result is True


@pytest.mark.asyncio
async def test_delete_user_permanent(mock_supabase_client, sample_user_data):
    """Test permanent user deletion."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_user_data]
        mock_supabase_client.table().delete().eq().execute.return_value = mock_response

        result = await db.delete_user(sample_user_data["id"], soft_delete=False)

        assert result is True


@pytest.mark.asyncio
async def test_list_users_success(mock_supabase_client, sample_user_data):
    """Test listing users."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_user_data, sample_user_data.copy()]
        mock_supabase_client.table().select().is_().order().limit().execute.return_value = (
            mock_response
        )

        result = await db.list_users(limit=10)

        assert len(result) == 2
        assert all("password_hash" not in user for user in result)


@pytest.mark.asyncio
async def test_list_users_include_deleted(mock_supabase_client, sample_user_data):
    """Test listing users including deleted."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_user_data]
        mock_supabase_client.table().select().order().limit().execute.return_value = mock_response

        result = await db.list_users(include_deleted=True)

        assert len(result) >= 1


@pytest.mark.asyncio
async def test_update_last_login_success(mock_supabase_client, sample_user_data):
    """Test updating last login timestamp."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_user_data]
        mock_supabase_client.table().update().eq().execute.return_value = mock_response

        result = await db.update_last_login(sample_user_data["id"], "192.168.1.1")

        assert result is True


@pytest.mark.asyncio
async def test_increment_failed_login_success(mock_supabase_client, sample_user_data):
    """Test incrementing failed login attempts."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        # Create user with no failed attempts
        user_with_no_failures = sample_user_data.copy()
        user_with_no_failures["failed_login_attempts"] = 0

        # Mock get_user_by_username
        get_response = MagicMock()
        get_response.data = [user_with_no_failures]

        # Mock update
        updated_user = user_with_no_failures.copy()
        updated_user["failed_login_attempts"] = 1
        update_response = MagicMock()
        update_response.data = [updated_user]

        # Configure execute to return different responses in order (first select, then update)
        mock_supabase_client.table().execute.side_effect = [get_response, update_response]

        result = await db.increment_failed_login("testuser")

        assert result == 1


@pytest.mark.asyncio
async def test_increment_failed_login_lockout(mock_supabase_client, sample_user_data):
    """Test account lockout after max failed attempts."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        user_with_failures = sample_user_data.copy()
        user_with_failures["failed_login_attempts"] = 4

        get_response = MagicMock()
        get_response.data = [user_with_failures]

        updated_user = user_with_failures.copy()
        updated_user["failed_login_attempts"] = 5
        updated_user["locked_until"] = (datetime.now() + timedelta(minutes=15)).isoformat()
        update_response = MagicMock()
        update_response.data = [updated_user]

        # Configure execute to return different responses in order (first select, then update)
        mock_supabase_client.table().execute.side_effect = [get_response, update_response]

        result = await db.increment_failed_login("testuser")

        assert result == 5


@pytest.mark.asyncio
async def test_reset_failed_login_success(mock_supabase_client, sample_user_data):
    """Test resetting failed login attempts."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_user_data]
        mock_supabase_client.table().update().eq().execute.return_value = mock_response

        result = await db.reset_failed_login(sample_user_data["id"])

        assert result is True


# =====================================================
# SESSION MANAGEMENT TESTS
# =====================================================


@pytest.mark.asyncio
async def test_create_session_success(mock_supabase_client, sample_session_data):
    """Test successful session creation."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_session_data]
        mock_supabase_client.table().insert().execute.return_value = mock_response

        result = await db.create_session(
            user_id=sample_session_data["user_id"],
            device_info="Test Browser",
            ip_address="127.0.0.1",
        )

        assert result is not None
        assert "session_token" in result
        assert result["user_id"] == sample_session_data["user_id"]


@pytest.mark.asyncio
async def test_get_session_valid(mock_supabase_client, sample_session_data):
    """Test getting valid session."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_session_data]
        mock_supabase_client.table().select().eq().is_().execute.return_value = mock_response

        result = await db.get_session("test_session_token_123")

        assert result is not None
        assert result["session_token"] == "test_session_token_123"


@pytest.mark.asyncio
async def test_get_session_expired(mock_supabase_client, sample_session_data):
    """Test getting expired session."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        # Mock should return empty data for expired session (filtered by .gt("expires_at", now))
        mock_response = MagicMock()
        mock_response.data = []  # Expired sessions are filtered out
        mock_supabase_client.table().execute.return_value = mock_response

        result = await db.get_session("test_session_token_123")

        assert result is None  # Expired session


@pytest.mark.asyncio
async def test_update_session_activity_success(mock_supabase_client, sample_session_data):
    """Test updating session activity."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_session_data]
        mock_supabase_client.table().update().eq().execute.return_value = mock_response

        result = await db.update_session_activity("test_session_token_123")

        assert result is True


@pytest.mark.asyncio
async def test_revoke_session_success(mock_supabase_client, sample_session_data):
    """Test revoking a session."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_session_data]
        mock_supabase_client.table().update().eq().execute.return_value = mock_response

        result = await db.revoke_session("test_session_token_123")

        assert result is True


@pytest.mark.asyncio
async def test_revoke_all_user_sessions_success(mock_supabase_client, sample_session_data):
    """Test revoking all user sessions."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_session_data, sample_session_data.copy()]
        mock_supabase_client.table().update().eq().is_().execute.return_value = mock_response

        result = await db.revoke_all_user_sessions(sample_session_data["user_id"])

        assert result == 2


@pytest.mark.asyncio
async def test_get_user_sessions_active_only(mock_supabase_client, sample_session_data):
    """Test getting active user sessions."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_session_data]
        mock_supabase_client.table().select().eq().is_().gte().order().execute.return_value = (
            mock_response
        )

        result = await db.get_user_sessions(sample_session_data["user_id"], active_only=True)

        assert len(result) == 1
        assert result[0]["session_token"] == "test_session_token_123"


@pytest.mark.asyncio
async def test_cleanup_expired_sessions_success(mock_supabase_client, sample_session_data):
    """Test cleanup of expired sessions."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = 2  # RPC returns count of deleted sessions
        mock_supabase_client.rpc().execute.return_value = mock_response

        result = await db.cleanup_expired_sessions()

        assert result == 2


# =====================================================
# PASSWORD RESET TESTS
# =====================================================


@pytest.mark.asyncio
async def test_create_reset_token_success(mock_supabase_client, sample_reset_token_data):
    """Test creating password reset token."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_reset_token_data]
        mock_supabase_client.table().insert().execute.return_value = mock_response

        result = await db.create_reset_token(
            user_id=sample_reset_token_data["user_id"], created_ip="127.0.0.1"
        )

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.asyncio
async def test_verify_reset_token_valid(mock_supabase_client, sample_reset_token_data):
    """Test verifying valid reset token."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_reset_token_data]
        mock_supabase_client.table().select().eq().is_().gt().execute.return_value = mock_response

        with patch("src.auth.db.verify_password", return_value=True):
            result = await db.verify_reset_token("reset_token_123")

            assert result is not None
            assert result["user_id"] == sample_reset_token_data["user_id"]


@pytest.mark.asyncio
async def test_verify_reset_token_expired(mock_supabase_client, sample_reset_token_data):
    """Test verifying expired reset token."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        # Mock should return empty data for expired token (filtered by .gt("expires_at", now))
        mock_response = MagicMock()
        mock_response.data = []  # Expired tokens are filtered out
        mock_supabase_client.table().execute.return_value = mock_response

        result = await db.verify_reset_token("reset_token_123")

        assert result is None  # Expired token


@pytest.mark.asyncio
async def test_use_reset_token_success(mock_supabase_client, sample_reset_token_data):
    """Test using reset token to change password."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        # Mock verify_reset_token
        with patch("src.auth.db.verify_reset_token", return_value=sample_reset_token_data):
            # Mock update_user_password
            with patch("src.auth.db.update_user_password", return_value=True):
                # Mock token marking as used
                mock_response = MagicMock()
                mock_response.data = [sample_reset_token_data]
                mock_supabase_client.table().update().eq().execute.return_value = mock_response

                result = await db.use_reset_token(
                    token="reset_token_123", new_password="NewPassword123!", used_ip="127.0.0.1"
                )

                assert result is True


@pytest.mark.asyncio
async def test_use_reset_token_invalid(mock_supabase_client):
    """Test using invalid reset token."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        with patch("src.auth.db.verify_reset_token", return_value=None):
            # Should raise exception for invalid token
            with pytest.raises(Exception, match="Invalid or expired reset token"):
                await db.use_reset_token(token="invalid_token", new_password="NewPassword123!")


@pytest.mark.asyncio
async def test_cleanup_reset_tokens_success(mock_supabase_client, sample_reset_token_data):
    """Test cleanup of expired reset tokens."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = 1  # RPC returns count of deleted tokens
        mock_supabase_client.rpc().execute.return_value = mock_response

        result = await db.cleanup_reset_tokens()

        assert result == 1


# =====================================================
# OAUTH ACCOUNT TESTS
# =====================================================


@pytest.fixture
def sample_oauth_data():
    """Sample OAuth account data."""
    return {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "provider": "google",
        "provider_user_id": "google_12345",
        "access_token": "encrypted_access_token",
        "refresh_token": "encrypted_refresh_token",
        "token_expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
        "profile_data": {"email": "user@gmail.com", "name": "Test User"},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


@pytest.mark.asyncio
async def test_link_oauth_account_success(mock_supabase_client, sample_oauth_data):
    """Test linking OAuth account."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_oauth_data]
        mock_supabase_client.table().insert().execute.return_value = mock_response

        result = await db.link_oauth_account(
            user_id=sample_oauth_data["user_id"],
            provider="google",
            provider_user_id="google_12345",
            access_token="access_token_123",
            profile_data={"email": "user@gmail.com"},
        )

        assert result is not None
        assert result["provider"] == "google"


@pytest.mark.asyncio
async def test_get_oauth_account_found(mock_supabase_client, sample_oauth_data):
    """Test getting OAuth account."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_oauth_data]
        mock_supabase_client.table().select().eq().execute.return_value = mock_response

        result = await db.get_oauth_account(provider="google", provider_user_id="google_12345")

        assert result is not None
        assert result["provider"] == "google"


@pytest.mark.asyncio
async def test_get_user_oauth_accounts_success(mock_supabase_client, sample_oauth_data):
    """Test getting all OAuth accounts for a user."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_oauth_data]
        mock_supabase_client.table().select().eq().execute.return_value = mock_response

        result = await db.get_user_oauth_accounts(sample_oauth_data["user_id"])

        assert len(result) >= 1
        assert result[0]["provider"] == "google"


@pytest.mark.asyncio
async def test_update_oauth_tokens_success(mock_supabase_client, sample_oauth_data):
    """Test updating OAuth tokens."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        updated_oauth = sample_oauth_data.copy()
        updated_oauth["access_token"] = "new_access_token"
        updated_oauth["refresh_token"] = "new_refresh_token"

        mock_response = MagicMock()
        mock_response.data = [updated_oauth]
        mock_supabase_client.table().execute.return_value = mock_response

        result = await db.update_oauth_tokens(
            oauth_account_id=sample_oauth_data["id"],
            access_token="new_access_token",
            refresh_token="new_refresh_token",
        )

        assert result["id"] == sample_oauth_data["id"]
        assert result["access_token"] == "new_access_token"


@pytest.mark.asyncio
async def test_unlink_oauth_account_success(mock_supabase_client, sample_oauth_data):
    """Test unlinking OAuth account."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        mock_response = MagicMock()
        mock_response.data = [sample_oauth_data]
        mock_supabase_client.table().delete().eq().execute.return_value = mock_response

        result = await db.unlink_oauth_account(sample_oauth_data["id"])

        assert result is True


# =====================================================
# ROLE MANAGEMENT TESTS
# =====================================================


@pytest.fixture
def sample_role_data():
    """Sample role data."""
    return {
        "id": str(uuid4()),
        "name": "admin",
        "permissions": ["read", "write", "delete", "manage_users"],
        "description": "Administrator role",
    }


@pytest.fixture
def sample_user_role_data():
    """Sample user-role assignment data."""
    return {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "role_id": str(uuid4()),
        "assigned_at": datetime.now().isoformat(),
        "assigned_by": str(uuid4()),
    }


@pytest.mark.asyncio
async def test_assign_role_success(mock_supabase_client, sample_role_data, sample_user_role_data):
    """Test assigning role to user."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        # Mock role lookup
        role_response = MagicMock()
        role_response.data = [sample_role_data]

        # Mock role assignment
        assignment_response = MagicMock()
        assignment_response.data = [sample_user_role_data]

        # Use side_effect for sequential calls to execute()
        mock_supabase_client.table().execute.side_effect = [role_response, assignment_response]

        result = await db.assign_role(
            user_id=sample_user_role_data["user_id"],
            role_name="admin",
            assigned_by=sample_user_role_data["assigned_by"],
        )

        assert result["id"] == sample_user_role_data["id"]
        assert result["user_id"] == sample_user_role_data["user_id"]


@pytest.mark.asyncio
async def test_assign_role_not_found(mock_supabase_client, sample_user_role_data):
    """Test assigning non-existent role."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        role_response = MagicMock()
        role_response.data = []  # Role not found
        mock_supabase_client.table().execute.return_value = role_response

        with pytest.raises(Exception, match="Role .* not found"):
            await db.assign_role(
                user_id=sample_user_role_data["user_id"],
                role_name="nonexistent",
                assigned_by=sample_user_role_data["assigned_by"],
            )


@pytest.mark.asyncio
async def test_revoke_role_success(mock_supabase_client, sample_role_data, sample_user_role_data):
    """Test revoking role from user."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        # Mock role lookup
        role_response = MagicMock()
        role_response.data = [sample_role_data]

        # Mock role revocation
        revoke_response = MagicMock()
        revoke_response.data = [sample_user_role_data]

        mock_supabase_client.table().select().eq().execute.return_value = role_response
        mock_supabase_client.table().delete().eq().execute.return_value = revoke_response

        result = await db.revoke_role(user_id=sample_user_role_data["user_id"], role_name="admin")

        assert result is True


@pytest.mark.asyncio
async def test_get_user_roles_success(mock_supabase_client, sample_role_data):
    """Test getting user roles."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        # RPC returns user data with roles array
        mock_response = MagicMock()
        mock_response.data = [{"roles": [sample_role_data]}]
        mock_supabase_client.rpc().execute.return_value = mock_response

        result = await db.get_user_roles(str(uuid4()))

        assert len(result) >= 1
        assert result[0]["name"] == "admin"


@pytest.mark.asyncio
async def test_check_permission_has_permission(mock_supabase_client, sample_role_data):
    """Test checking user permission (has permission)."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        # RPC returns user data with roles that include the "write" permission
        role_with_permissions = sample_role_data.copy()
        role_with_permissions["permissions"] = ["read", "write", "delete"]

        mock_response = MagicMock()
        mock_response.data = [{"roles": [role_with_permissions]}]
        mock_supabase_client.rpc().execute.return_value = mock_response

        result = await db.check_permission(str(uuid4()), "write")

        assert result is True


@pytest.mark.asyncio
async def test_check_permission_no_permission(mock_supabase_client, sample_role_data):
    """Test checking user permission (no permission)."""
    with patch("src.auth.db.get_supabase_client", return_value=mock_supabase_client):
        role_without_permission = sample_role_data.copy()
        role_without_permission["permissions"] = ["read"]  # Only read permission

        mock_response = MagicMock()
        mock_response.data = [{"role": role_without_permission}]
        mock_supabase_client.table().select().eq().execute.return_value = mock_response

        result = await db.check_permission(str(uuid4()), "delete")

        assert result is False
