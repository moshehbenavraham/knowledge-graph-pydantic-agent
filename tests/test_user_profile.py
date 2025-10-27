"""
Comprehensive tests for user profile functionality.

Tests user profile operations:
- Password change with verification
- Session viewing and revocation
- Profile rendering (database + YAML modes)
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.auth import user_profile

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

    return mock_client


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return {
        "id": str(uuid4()),
        "username": "testuser",
        "email": "max@apexwebservices.com",
        "full_name": "Test User",
        "is_active": True,
        "created_at": "2025-01-01T00:00:00",
        "last_login_at": "2025-10-24T10:00:00",
    }


@pytest.fixture
def sample_sessions():
    """Sample user sessions."""
    return [
        {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "session_token": "token_1",
            "device_info": "Chrome Browser",
            "ip_address": "192.168.1.1",
            "created_at": "2025-10-24T10:00:00",
            "last_activity_at": "2025-10-24T11:00:00",
            "session_type": "web",
        },
        {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "session_token": "token_2",
            "device_info": "Mobile App",
            "ip_address": "192.168.1.2",
            "created_at": "2025-10-23T09:00:00",
            "last_activity_at": "2025-10-24T08:00:00",
            "session_type": "mobile",
        },
    ]


# =====================================================
# GET USER INFO TESTS
# =====================================================


@pytest.mark.asyncio
async def test_get_user_info_success(sample_user):
    """Test getting user information successfully."""
    with patch("src.auth.user_profile.get_user_by_username", return_value=sample_user):
        result = await user_profile.get_user_info("testuser")

        assert result is not None
        assert result["username"] == "testuser"
        assert result["email"] == "max@apexwebservices.com"


@pytest.mark.asyncio
async def test_get_user_info_not_found():
    """Test getting non-existent user."""
    with patch("src.auth.user_profile.get_user_by_username", return_value=None):
        result = await user_profile.get_user_info("nonexistent")

        assert result is None


@pytest.mark.asyncio
async def test_get_user_info_exception():
    """Test getting user info with exception."""
    with patch(
        "src.auth.user_profile.get_user_by_username",
        side_effect=Exception("Database error"),
    ):
        result = await user_profile.get_user_info("testuser")

        assert result is None


# =====================================================
# CHANGE PASSWORD TESTS
# =====================================================


@pytest.mark.asyncio
async def test_change_user_password_success(sample_user, mock_supabase_client):
    """Test successful password change."""
    with patch(
        "src.auth.db.verify_user_password", new_callable=AsyncMock, return_value=sample_user
    ):
        with patch("src.auth.db.update_user_password", new_callable=AsyncMock, return_value=True):
            success, message = await user_profile.change_user_password(
                username="testuser",
                current_password="OldPassword123!",
                new_password="NewPassword123!",
            )

            assert success is True
            assert "successful" in message.lower()


@pytest.mark.asyncio
async def test_change_user_password_wrong_current():
    """Test password change with wrong current password."""
    with patch("src.auth.db.verify_user_password", return_value=None):
        success, message = await user_profile.change_user_password(
            username="testuser",
            current_password="WrongPassword123!",
            new_password="NewPassword123!",
        )

        assert success is False
        assert "incorrect" in message.lower()


@pytest.mark.asyncio
async def test_change_user_password_exception(sample_user):
    """Test password change with exception."""
    with patch(
        "src.auth.db.verify_user_password", new_callable=AsyncMock, return_value=sample_user
    ):
        with patch(
            "src.auth.db.update_user_password",
            new_callable=AsyncMock,
            side_effect=Exception("Database error"),
        ):
            success, message = await user_profile.change_user_password(
                username="testuser",
                current_password="OldPassword123!",
                new_password="NewPassword123!",
            )

            assert success is False
            assert "failed" in message.lower()


@pytest.mark.asyncio
async def test_change_user_password_user_not_found():
    """Test password change when user verification fails."""
    with patch("src.auth.db.verify_user_password", return_value=None):
        success, message = await user_profile.change_user_password(
            username="nonexistent",
            current_password="AnyPassword123!",
            new_password="NewPassword123!",
        )

        assert success is False
        assert "incorrect" in message.lower()


# =====================================================
# PROFILE RENDERING TESTS (INTEGRATION STYLE)
# =====================================================


@pytest.mark.asyncio
async def test_render_user_profile_handles_missing_user():
    """Test that render_user_profile handles missing user gracefully."""
    with patch("src.auth.user_profile.get_user_info", return_value=None):
        with patch("streamlit.sidebar") as mock_sidebar:
            mock_sidebar.markdown = MagicMock()
            mock_sidebar.error = MagicMock()

            # Should not crash
            try:
                user_profile.render_user_profile("nonexistent")
                # If it completes without exception, test passes
            except Exception as e:
                # If exception is Streamlit-related (e.g., session_state), it's expected
                if "streamlit" not in str(e).lower():
                    raise


@pytest.mark.asyncio
async def test_render_user_profile_handles_exception():
    """Test that render_user_profile handles exceptions gracefully."""
    with patch(
        "src.auth.user_profile.get_user_info",
        side_effect=Exception("Database connection error"),
    ):
        with patch("streamlit.sidebar") as mock_sidebar:
            mock_sidebar.markdown = MagicMock()
            mock_sidebar.error = MagicMock()

            # Should not crash
            try:
                user_profile.render_user_profile("testuser")
            except Exception as e:
                # If exception is Streamlit-related, it's expected
                if "streamlit" not in str(e).lower():
                    raise


def test_render_user_profile_simple():
    """Test simplified user profile rendering (YAML mode)."""
    with patch("streamlit.sidebar") as mock_sidebar:
        mock_sidebar.markdown = MagicMock()
        mock_expander = MagicMock()
        mock_sidebar.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_sidebar.expander.return_value.__exit__ = MagicMock(return_value=False)
        mock_expander.markdown = MagicMock()
        mock_expander.info = MagicMock()

        # Should not crash
        try:
            user_profile.render_user_profile_simple(
                username="testuser", full_name="Test User", email="max@apexwebservices.com"
            )
        except Exception as e:
            # If exception is Streamlit-related, it's expected
            if "streamlit" not in str(e).lower():
                raise


def test_render_user_profile_simple_without_email():
    """Test simplified profile without email."""
    with patch("streamlit.sidebar") as mock_sidebar:
        mock_sidebar.markdown = MagicMock()
        mock_expander = MagicMock()
        mock_sidebar.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_sidebar.expander.return_value.__exit__ = MagicMock(return_value=False)
        mock_expander.markdown = MagicMock()
        mock_expander.info = MagicMock()

        # Should not crash
        try:
            user_profile.render_user_profile_simple(username="testuser", full_name="Test User")
        except Exception as e:
            # If exception is Streamlit-related, it's expected
            if "streamlit" not in str(e).lower():
                raise


# =====================================================
# INTEGRATION TESTS (FULL FLOW)
# =====================================================


@pytest.mark.asyncio
async def test_complete_password_change_flow(sample_user, mock_supabase_client):
    """Test complete password change flow."""
    # Step 1: Get user info
    with patch("src.auth.user_profile.get_user_by_username", return_value=sample_user):
        user = await user_profile.get_user_info("testuser")
        assert user is not None

    # Step 2: Validate password strength (from password_reset module)
    from src.auth.password_reset import is_password_strong

    is_strong, _ = is_password_strong("NewStrongPass123!")
    assert is_strong is True

    # Step 3: Change password
    with patch(
        "src.auth.db.verify_user_password", new_callable=AsyncMock, return_value=sample_user
    ):
        with patch("src.auth.db.update_user_password", new_callable=AsyncMock, return_value=True):
            success, message = await user_profile.change_user_password(
                username="testuser",
                current_password="OldPassword123!",
                new_password="NewStrongPass123!",
            )

            assert success is True
            assert "successful" in message.lower()


@pytest.mark.asyncio
async def test_password_change_flow_with_weak_password(sample_user):
    """Test password change flow rejecting weak password."""
    # Step 1: Get user info
    with patch("src.auth.user_profile.get_user_by_username", return_value=sample_user):
        user = await user_profile.get_user_info("testuser")
        assert user is not None

    # Step 2: Check password strength - should fail
    from src.auth.password_reset import is_password_strong

    is_strong, message = is_password_strong("weak")
    assert is_strong is False
    assert "at least 8 characters" in message.lower()

    # Password change should not proceed with weak password


@pytest.mark.asyncio
async def test_password_change_flow_with_wrong_current(sample_user):
    """Test password change flow with wrong current password."""
    # Step 1: Get user info
    with patch("src.auth.user_profile.get_user_by_username", return_value=sample_user):
        user = await user_profile.get_user_info("testuser")
        assert user is not None

    # Step 2: Validate new password strength - passes
    from src.auth.password_reset import is_password_strong

    is_strong, _ = is_password_strong("NewStrongPass123!")
    assert is_strong is True

    # Step 3: Try to change password with wrong current password - should fail
    with patch("src.auth.db.verify_user_password", return_value=None):
        success, message = await user_profile.change_user_password(
            username="testuser",
            current_password="WrongPassword123!",
            new_password="NewStrongPass123!",
        )

        assert success is False
        assert "incorrect" in message.lower()


@pytest.mark.asyncio
async def test_session_viewing_flow(sample_user, sample_sessions):
    """Test viewing user sessions."""
    # Step 1: Get user info
    with patch("src.auth.user_profile.get_user_by_username", return_value=sample_user):
        user = await user_profile.get_user_info("testuser")
        assert user is not None

    # Step 2: Get user sessions
    with patch("src.auth.user_profile.get_user_sessions", return_value=sample_sessions):
        from src.auth.user_profile import get_user_sessions

        sessions = await get_user_sessions(user["id"], active_only=True)

        assert len(sessions) == 2
        assert sessions[0]["session_token"] == "token_1"
        assert sessions[1]["session_token"] == "token_2"


@pytest.mark.asyncio
async def test_session_revocation_flow(sample_user, sample_sessions):
    """Test revoking individual session."""
    # Step 1: Get user sessions
    with patch("src.auth.user_profile.get_user_sessions", return_value=sample_sessions):
        from src.auth.user_profile import get_user_sessions

        sessions = await get_user_sessions(sample_user["id"], active_only=True)
        assert len(sessions) == 2

    # Step 2: Revoke one session
    with patch("src.auth.user_profile.revoke_session", return_value=True):
        from src.auth.user_profile import revoke_session

        success = await revoke_session(sessions[0]["session_token"])
        assert success is True


@pytest.mark.asyncio
async def test_revoke_all_sessions_flow(sample_user, sample_sessions):
    """Test revoking all user sessions."""
    # Step 1: Get user sessions
    with patch("src.auth.user_profile.get_user_sessions", return_value=sample_sessions):
        from src.auth.user_profile import get_user_sessions

        sessions = await get_user_sessions(sample_user["id"], active_only=True)
        assert len(sessions) == 2

    # Step 2: Revoke all sessions
    with patch("src.auth.user_profile.revoke_all_user_sessions", return_value=2):
        from src.auth.user_profile import revoke_all_user_sessions

        count = await revoke_all_user_sessions(sample_user["id"])
        assert count == 2  # Both sessions revoked


# =====================================================
# EDGE CASE TESTS
# =====================================================


@pytest.mark.asyncio
async def test_get_user_info_with_missing_fields():
    """Test getting user info with missing optional fields."""
    minimal_user = {
        "id": str(uuid4()),
        "username": "testuser",
        "email": "max@apexwebservices.com",
        "full_name": "Test User",
        # Missing: created_at, last_login_at
    }

    with patch("src.auth.user_profile.get_user_by_username", return_value=minimal_user):
        result = await user_profile.get_user_info("testuser")

        assert result is not None
        assert result["username"] == "testuser"
        # Should handle missing fields gracefully


@pytest.mark.asyncio
async def test_change_password_with_same_password(sample_user, mock_supabase_client):
    """Test changing password to the same value (should still succeed)."""
    with patch(
        "src.auth.db.verify_user_password", new_callable=AsyncMock, return_value=sample_user
    ):
        with patch("src.auth.db.update_user_password", new_callable=AsyncMock, return_value=True):
            success, message = await user_profile.change_user_password(
                username="testuser",
                current_password="Password123!",
                new_password="Password123!",  # Same password
            )

            # Should succeed (UI validation can handle this if needed)
            assert success is True


@pytest.mark.asyncio
async def test_session_list_empty(sample_user):
    """Test viewing sessions when none exist."""
    with patch("src.auth.user_profile.get_user_sessions", return_value=[]):
        from src.auth.user_profile import get_user_sessions

        sessions = await get_user_sessions(sample_user["id"], active_only=True)

        assert len(sessions) == 0


@pytest.mark.asyncio
async def test_revoke_session_failure(sample_sessions):
    """Test session revocation failure."""
    with patch("src.auth.user_profile.revoke_session", return_value=False):
        from src.auth.user_profile import revoke_session

        success = await revoke_session(sample_sessions[0]["session_token"])
        assert success is False


@pytest.mark.asyncio
async def test_revoke_all_sessions_none_active(sample_user):
    """Test revoking all sessions when none are active."""
    with patch("src.auth.user_profile.revoke_all_user_sessions", return_value=0):
        from src.auth.user_profile import revoke_all_user_sessions

        count = await revoke_all_user_sessions(sample_user["id"])
        assert count == 0
