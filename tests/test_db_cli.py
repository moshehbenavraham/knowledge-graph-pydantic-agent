"""
Comprehensive tests for database CLI commands.

Tests all 8 CLI commands:
- create: Create user with role
- list: List all users
- get: Get user details with roles and sessions
- update: Update user information
- update-password: Change user password
- delete: Soft/permanent delete
- role: Assign/revoke roles
- sessions: View/revoke sessions
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.auth import db_cli

# =====================================================
# FIXTURES
# =====================================================


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return {
        "id": str(uuid4()),
        "username": "testuser",
        "email": "max@apexwebservices.com",
        "full_name": "Test User",
        "auth_method": "password",
        "is_active": True,
        "is_email_verified": False,
        "created_at": "2025-01-01T00:00:00",
        "last_login_at": "2025-10-24T10:00:00",
        "failed_login_attempts": 0,
        "locked_until": None,
    }


@pytest.fixture
def sample_roles():
    """Sample roles."""
    return [{"role_name": "user"}, {"role_name": "admin"}]


@pytest.fixture
def sample_sessions():
    """Sample sessions."""
    return [
        {
            "id": str(uuid4()),
            "session_token": "token_1",
            "device_info": "Chrome",
            "ip_address": "192.168.1.1",
            "created_at": "2025-10-24T10:00:00",
        }
    ]


# =====================================================
# CREATE COMMAND TESTS
# =====================================================


@pytest.mark.asyncio
async def test_cmd_create_success(sample_user):
    """Test successful user creation."""
    with patch("src.auth.db_cli.create_user", return_value=sample_user):
        with patch("src.auth.db_cli.assign_role", return_value=True):
            result = await db_cli.cmd_create(
                username="testuser",
                email="max@apexwebservices.com",
                full_name="Test User",
                password="Password123!",
                role="user",
            )

            assert result == 0  # Success


@pytest.mark.asyncio
async def test_cmd_create_without_password(sample_user):
    """Test creating OAuth user without password."""
    oauth_user = sample_user.copy()
    oauth_user["auth_method"] = "oauth"

    with patch("src.auth.db_cli.create_user", return_value=oauth_user):
        with patch("src.auth.db_cli.assign_role", return_value=True):
            result = await db_cli.cmd_create(
                username="oauthuser",
                email="oauth@example.com",
                full_name="OAuth User",
                password=None,
                role="user",
            )

            assert result == 0


@pytest.mark.asyncio
async def test_cmd_create_with_admin_role(sample_user):
    """Test creating user with admin role."""
    with patch("src.auth.db_cli.create_user", return_value=sample_user):
        with patch("src.auth.db_cli.assign_role", return_value=True) as mock_assign:
            result = await db_cli.cmd_create(
                username="adminuser",
                email="admin@example.com",
                full_name="Admin User",
                password="AdminPass123!",
                role="admin",
            )

            assert result == 0
            # Verify admin role was assigned
            mock_assign.assert_called_once()
            assert mock_assign.call_args[0][1] == "admin"


@pytest.mark.asyncio
async def test_cmd_create_inactive_user(sample_user):
    """Test creating inactive user."""
    inactive_user = sample_user.copy()
    inactive_user["is_active"] = False

    with patch("src.auth.db_cli.create_user", return_value=inactive_user):
        with patch("src.auth.db_cli.assign_role", return_value=True):
            result = await db_cli.cmd_create(
                username="inactive",
                email="inactive@example.com",
                full_name="Inactive User",
                password="Pass123!",
                active=False,
            )

            assert result == 0


@pytest.mark.asyncio
async def test_cmd_create_error():
    """Test user creation error."""
    with patch("src.auth.db_cli.create_user", side_effect=Exception("Database error")):
        result = await db_cli.cmd_create(
            username="testuser",
            email="max@apexwebservices.com",
            full_name="Test User",
            password="Pass123!",
        )

        assert result == 1  # Error


# =====================================================
# LIST COMMAND TESTS
# =====================================================


@pytest.mark.asyncio
async def test_cmd_list_success(sample_user):
    """Test listing users."""
    users = [sample_user, sample_user.copy()]

    with patch("src.auth.db_cli.list_users", return_value=users):
        result = await db_cli.cmd_list(limit=100)

        assert result == 0


@pytest.mark.asyncio
async def test_cmd_list_with_limit(sample_user):
    """Test listing users with custom limit."""
    users = [sample_user]

    with patch("src.auth.db_cli.list_users", return_value=users) as mock_list:
        result = await db_cli.cmd_list(limit=50)

        assert result == 0
        mock_list.assert_called_once_with(limit=50, include_deleted=False)


@pytest.mark.asyncio
async def test_cmd_list_include_deleted(sample_user):
    """Test listing users including deleted."""
    users = [sample_user]

    with patch("src.auth.db_cli.list_users", return_value=users) as mock_list:
        result = await db_cli.cmd_list(include_deleted=True)

        assert result == 0
        mock_list.assert_called_once_with(limit=100, include_deleted=True)


@pytest.mark.asyncio
async def test_cmd_list_empty():
    """Test listing when no users exist."""
    with patch("src.auth.db_cli.list_users", return_value=[]):
        result = await db_cli.cmd_list()

        assert result == 0  # Should handle gracefully


@pytest.mark.asyncio
async def test_cmd_list_error():
    """Test list command error."""
    with patch("src.auth.db_cli.list_users", side_effect=Exception("Database error")):
        result = await db_cli.cmd_list()

        assert result == 1


# =====================================================
# GET COMMAND TESTS
# =====================================================


@pytest.mark.asyncio
async def test_cmd_get_success(sample_user, sample_roles, sample_sessions):
    """Test getting user details."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.get_user_roles", return_value=sample_roles):
            with patch("src.auth.db_cli.get_user_sessions", return_value=sample_sessions):
                result = await db_cli.cmd_get("testuser")

                assert result == 0


@pytest.mark.asyncio
async def test_cmd_get_user_not_found():
    """Test getting non-existent user."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=None):
        result = await db_cli.cmd_get("nonexistent")

        assert result == 1


@pytest.mark.asyncio
async def test_cmd_get_no_roles(sample_user, sample_sessions):
    """Test getting user with no roles."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.get_user_roles", return_value=[]):
            with patch("src.auth.db_cli.get_user_sessions", return_value=sample_sessions):
                result = await db_cli.cmd_get("testuser")

                assert result == 0


@pytest.mark.asyncio
async def test_cmd_get_no_sessions(sample_user, sample_roles):
    """Test getting user with no active sessions."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.get_user_roles", return_value=sample_roles):
            with patch("src.auth.db_cli.get_user_sessions", return_value=[]):
                result = await db_cli.cmd_get("testuser")

                assert result == 0


@pytest.mark.asyncio
async def test_cmd_get_error():
    """Test get command error."""
    with patch("src.auth.db_cli.get_user_by_username", side_effect=Exception("Database error")):
        result = await db_cli.cmd_get("testuser")

        assert result == 1


# =====================================================
# UPDATE COMMAND TESTS
# =====================================================


@pytest.mark.asyncio
async def test_cmd_update_email(sample_user):
    """Test updating user email."""
    updated_user = sample_user.copy()
    updated_user["email"] = "newemail@example.com"

    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.update_user", return_value=updated_user):
            result = await db_cli.cmd_update(username="testuser", new_email="newemail@example.com")

            assert result == 0


@pytest.mark.asyncio
async def test_cmd_update_username(sample_user):
    """Test updating username."""
    updated_user = sample_user.copy()
    updated_user["username"] = "newusername"

    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.update_user", return_value=updated_user):
            result = await db_cli.cmd_update(username="testuser", new_username="newusername")

            assert result == 0


@pytest.mark.asyncio
async def test_cmd_update_name(sample_user):
    """Test updating full name."""
    updated_user = sample_user.copy()
    updated_user["full_name"] = "New Name"

    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.update_user", return_value=updated_user):
            result = await db_cli.cmd_update(username="testuser", new_name="New Name")

            assert result == 0


@pytest.mark.asyncio
async def test_cmd_update_activate(sample_user):
    """Test activating user."""
    inactive_user = sample_user.copy()
    inactive_user["is_active"] = False

    activated_user = sample_user.copy()
    activated_user["is_active"] = True

    with patch("src.auth.db_cli.get_user_by_username", return_value=inactive_user):
        with patch("src.auth.db_cli.update_user", return_value=activated_user):
            result = await db_cli.cmd_update(username="testuser", activate=True)

            assert result == 0


@pytest.mark.asyncio
async def test_cmd_update_deactivate(sample_user):
    """Test deactivating user."""
    deactivated_user = sample_user.copy()
    deactivated_user["is_active"] = False

    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.update_user", return_value=deactivated_user):
            result = await db_cli.cmd_update(username="testuser", deactivate=True)

            assert result == 0


@pytest.mark.asyncio
async def test_cmd_update_user_not_found():
    """Test updating non-existent user."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=None):
        result = await db_cli.cmd_update(username="nonexistent", new_email="new@example.com")

        assert result == 1


@pytest.mark.asyncio
async def test_cmd_update_error(sample_user):
    """Test update command error."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.update_user", side_effect=Exception("Database error")):
            result = await db_cli.cmd_update(username="testuser", new_email="new@example.com")

            assert result == 1


# =====================================================
# UPDATE PASSWORD COMMAND TESTS
# =====================================================


@pytest.mark.asyncio
async def test_cmd_update_password_success(sample_user):
    """Test successful password update."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.update_user_password", return_value=True):
            result = await db_cli.cmd_update_password("testuser", "NewPassword123!")

            assert result == 0


@pytest.mark.asyncio
async def test_cmd_update_password_user_not_found():
    """Test password update for non-existent user."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=None):
        result = await db_cli.cmd_update_password("nonexistent", "NewPassword123!")

        assert result == 1


@pytest.mark.asyncio
async def test_cmd_update_password_error(sample_user):
    """Test password update error."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.update_user_password", side_effect=Exception("Database error")):
            result = await db_cli.cmd_update_password("testuser", "NewPassword123!")

            assert result == 1


# =====================================================
# DELETE COMMAND TESTS
# =====================================================


@pytest.mark.asyncio
async def test_cmd_delete_soft(sample_user):
    """Test soft delete user."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.delete_user", return_value=True):
            with patch("builtins.input", return_value="yes"):
                result = await db_cli.cmd_delete("testuser", permanent=False)

                assert result == 0


@pytest.mark.asyncio
async def test_cmd_delete_permanent(sample_user):
    """Test permanent delete user."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.delete_user", return_value=True) as mock_delete:
            with patch("builtins.input", return_value="yes"):
                result = await db_cli.cmd_delete("testuser", permanent=True)

                assert result == 0
                # Verify permanent delete was called
                mock_delete.assert_called_once()
                assert mock_delete.call_args[1]["soft_delete"] is False


@pytest.mark.asyncio
async def test_cmd_delete_user_not_found():
    """Test deleting non-existent user."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=None):
        result = await db_cli.cmd_delete("nonexistent")

        assert result == 1


@pytest.mark.asyncio
async def test_cmd_delete_error(sample_user):
    """Test delete command error."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.delete_user", side_effect=Exception("Database error")):
            result = await db_cli.cmd_delete("testuser")

            assert result == 1


# =====================================================
# ROLE COMMAND TESTS
# =====================================================


@pytest.mark.asyncio
async def test_cmd_role_assign(sample_user):
    """Test assigning role to user."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.assign_role", return_value=True):
            result = await db_cli.cmd_role("testuser", action="assign", role_name="admin")

            assert result == 0


@pytest.mark.asyncio
async def test_cmd_role_revoke(sample_user):
    """Test revoking role from user."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.revoke_role", new=AsyncMock(return_value=True)):
            result = await db_cli.cmd_role("testuser", action="revoke", role_name="admin")

            assert result == 0


@pytest.mark.asyncio
async def test_cmd_role_user_not_found():
    """Test role command for non-existent user."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=None):
        result = await db_cli.cmd_role("nonexistent", action="assign", role_name="admin")

        assert result == 1


@pytest.mark.asyncio
async def test_cmd_role_invalid_action(sample_user):
    """Test role command with invalid action."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        result = await db_cli.cmd_role("testuser", action="invalid", role_name="admin")

        assert result == 1


@pytest.mark.asyncio
async def test_cmd_role_error(sample_user):
    """Test role command error."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.assign_role", side_effect=Exception("Database error")):
            result = await db_cli.cmd_role("testuser", action="assign", role_name="admin")

            assert result == 1


# =====================================================
# SESSIONS COMMAND TESTS
# =====================================================


@pytest.mark.asyncio
async def test_cmd_sessions_view(sample_user, sample_sessions):
    """Test viewing user sessions."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.get_user_sessions", return_value=sample_sessions):
            result = await db_cli.cmd_sessions("testuser", revoke=False)

            assert result == 0


@pytest.mark.asyncio
async def test_cmd_sessions_revoke(sample_user, sample_sessions):
    """Test revoking all user sessions."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.get_user_sessions", return_value=sample_sessions):
            with patch("src.auth.db_cli.revoke_all_user_sessions", return_value=1):
                result = await db_cli.cmd_sessions("testuser", revoke=True)

                assert result == 0


@pytest.mark.asyncio
async def test_cmd_sessions_no_sessions(sample_user):
    """Test viewing sessions when none exist."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.get_user_sessions", return_value=[]):
            result = await db_cli.cmd_sessions("testuser", revoke=False)

            assert result == 0


@pytest.mark.asyncio
async def test_cmd_sessions_user_not_found():
    """Test sessions command for non-existent user."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=None):
        result = await db_cli.cmd_sessions("nonexistent", revoke=False)

        assert result == 1


@pytest.mark.asyncio
async def test_cmd_sessions_error(sample_user):
    """Test sessions command error."""
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.get_user_sessions", side_effect=Exception("Database error")):
            result = await db_cli.cmd_sessions("testuser", revoke=False)

            assert result == 1


# =====================================================
# INTEGRATION TESTS
# =====================================================


@pytest.mark.asyncio
async def test_complete_user_lifecycle(sample_user, sample_roles, sample_sessions):
    """Test complete user lifecycle: create → update → assign role → view → delete."""
    # Step 1: Create user
    with patch("src.auth.db_cli.create_user", return_value=sample_user):
        with patch("src.auth.db_cli.assign_role", return_value=True):
            result = await db_cli.cmd_create(
                username="testuser",
                email="max@apexwebservices.com",
                full_name="Test User",
                password="Pass123!",
                role="user",
            )
            assert result == 0

    # Step 2: Update user email
    updated_user = sample_user.copy()
    updated_user["email"] = "newemail@example.com"

    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.update_user", return_value=updated_user):
            result = await db_cli.cmd_update(username="testuser", new_email="newemail@example.com")
            assert result == 0

    # Step 3: Assign admin role
    with patch("src.auth.db_cli.get_user_by_username", return_value=updated_user):
        with patch("src.auth.db_cli.assign_role", return_value=True):
            result = await db_cli.cmd_role("testuser", action="assign", role_name="admin")
            assert result == 0

    # Step 4: View user details
    with patch("src.auth.db_cli.get_user_by_username", return_value=updated_user):
        with patch("src.auth.db_cli.get_user_roles", return_value=sample_roles):
            with patch("src.auth.db_cli.get_user_sessions", return_value=sample_sessions):
                result = await db_cli.cmd_get("testuser")
                assert result == 0

    # Step 5: Delete user
    with patch("src.auth.db_cli.get_user_by_username", return_value=updated_user):
        with patch("src.auth.db_cli.delete_user", return_value=True):
            with patch("builtins.input", return_value="yes"):
                result = await db_cli.cmd_delete("testuser", permanent=False)
                assert result == 0


@pytest.mark.asyncio
async def test_password_management_flow(sample_user):
    """Test password management: create with password → update password."""
    # Step 1: Create user with password
    with patch("src.auth.db_cli.create_user", return_value=sample_user):
        with patch("src.auth.db_cli.assign_role", return_value=True):
            result = await db_cli.cmd_create(
                username="testuser",
                email="max@apexwebservices.com",
                full_name="Test User",
                password="OldPass123!",
            )
            assert result == 0

    # Step 2: Update password
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.update_user_password", return_value=True):
            result = await db_cli.cmd_update_password("testuser", "NewPass123!")
            assert result == 0


@pytest.mark.asyncio
async def test_session_management_flow(sample_user, sample_sessions):
    """Test session management: view sessions → revoke sessions."""
    # Step 1: View sessions
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.get_user_sessions", return_value=sample_sessions):
            result = await db_cli.cmd_sessions("testuser", revoke=False)
            assert result == 0

    # Step 2: Revoke all sessions
    with patch("src.auth.db_cli.get_user_by_username", return_value=sample_user):
        with patch("src.auth.db_cli.get_user_sessions", return_value=sample_sessions):
            with patch(
                "src.auth.db_cli.revoke_all_user_sessions", return_value=len(sample_sessions)
            ):
                result = await db_cli.cmd_sessions("testuser", revoke=True)
                assert result == 0
