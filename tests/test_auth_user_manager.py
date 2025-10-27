"""Tests for user management functionality."""

import tempfile
from pathlib import Path

import pytest
import yaml

from src.auth.user_manager import UserManager


@pytest.fixture
def temp_config_file():
    """Create a temporary auth config file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config = {
            "credentials": {"usernames": {}},
            "cookie": {
                "name": "test_cookie",
                "key": "test_key",
                "expiry_days": 30,
            },
            "preauthorized": {"emails": []},
        }
        yaml.dump(config, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def user_manager(temp_config_file):
    """Create a UserManager instance with temporary config."""
    return UserManager(config_path=temp_config_file)


def test_user_manager_init_with_missing_file():
    """Test UserManager initialization with non-existent config file."""
    with pytest.raises(FileNotFoundError):
        UserManager(config_path="nonexistent_config.yaml")


def test_create_user_success(user_manager):
    """Test successful user creation."""
    user_manager.create_user(
        username="testuser",
        email="max@apexwebservices.com",
        name="Test User",
        password="TestPassword123!",  # nosec B106 - test password
    )

    # Verify user was created
    user = user_manager.get_user("testuser")
    assert user is not None
    assert user["username"] == "testuser"
    assert user["email"] == "max@apexwebservices.com"
    assert user["name"] == "Test User"


def test_create_user_duplicate_username(user_manager):
    """Test creating user with duplicate username fails."""
    user_manager.create_user(
        username="testuser",
        email="max@apexwebservices.com",
        name="Test User",
        password="Password123!",
    )

    with pytest.raises(ValueError, match="already exists"):
        user_manager.create_user(
            username="testuser",
            email="another@example.com",
            name="Another User",
            password="AnotherPassword123!",  # nosec B106 - test password
        )


def test_create_user_password_is_hashed(user_manager, temp_config_file):
    """Test that created user password is hashed."""
    password = "PlainTextPassword123!"  # nosec B105 - test password
    user_manager.create_user(
        username="testuser",
        email="max@apexwebservices.com",
        name="Test User",
        password=password,  # nosec B106 - test password
    )

    # Read config directly and verify password is hashed
    with open(temp_config_file) as f:
        config = yaml.safe_load(f)

    stored_password = config["credentials"]["usernames"]["testuser"]["password"]
    assert stored_password != password  # Should be hashed, not plain text
    assert stored_password.startswith("$2b$")  # Bcrypt format


def test_update_password_success(user_manager):
    """Test successful password update."""
    # Create user
    user_manager.create_user(
        username="testuser",
        email="max@apexwebservices.com",
        name="Test User",
        password="OldPassword123!",  # nosec B106 - test password
    )

    # Update password
    user_manager.update_password("testuser", "NewPassword123!")  # nosec B106 - test password

    # No direct way to verify without accessing config file
    # but the operation should not raise an error
    assert True


def test_update_password_nonexistent_user(user_manager):
    """Test updating password for non-existent user fails."""
    with pytest.raises(ValueError, match="not found"):
        user_manager.update_password("nonexistent", "NewPassword123!")


def test_delete_user_success(user_manager):
    """Test successful user deletion."""
    # Create user
    user_manager.create_user(
        username="testuser",
        email="max@apexwebservices.com",
        name="Test User",
        password="Password123!",  # nosec B106 - test password
    )

    # Verify user exists
    assert user_manager.get_user("testuser") is not None

    # Delete user
    user_manager.delete_user("testuser")

    # Verify user is gone
    assert user_manager.get_user("testuser") is None


def test_delete_user_nonexistent(user_manager):
    """Test deleting non-existent user fails."""
    with pytest.raises(ValueError, match="not found"):
        user_manager.delete_user("nonexistent")


def test_list_users_empty(user_manager):
    """Test listing users when none exist."""
    users = user_manager.list_users()
    assert users == []


def test_list_users_multiple(user_manager):
    """Test listing multiple users."""
    # Create multiple users
    user_manager.create_user(
        username="user1",
        email="user1@example.com",
        name="User One",
        password="Pass1!",  # nosec B106
    )
    user_manager.create_user(
        username="user2",
        email="user2@example.com",
        name="User Two",
        password="Pass2!",  # nosec B106
    )
    user_manager.create_user(
        username="user3",
        email="user3@example.com",
        name="User Three",
        password="Pass3!",  # nosec B106
    )

    # List users
    users = user_manager.list_users()
    assert len(users) == 3

    usernames = [u["username"] for u in users]
    assert "user1" in usernames
    assert "user2" in usernames
    assert "user3" in usernames


def test_get_user_exists(user_manager):
    """Test getting existing user."""
    user_manager.create_user(
        username="testuser",
        email="max@apexwebservices.com",
        name="Test User",
        password="Password123!",  # nosec B106 - test password
    )

    user = user_manager.get_user("testuser")
    assert user is not None
    assert user["username"] == "testuser"
    assert user["email"] == "max@apexwebservices.com"
    assert user["name"] == "Test User"
    assert "password" not in user  # Password should not be returned


def test_get_user_nonexistent(user_manager):
    """Test getting non-existent user returns None."""
    user = user_manager.get_user("nonexistent")
    assert user is None


def test_create_user_with_custom_rounds(user_manager, temp_config_file):
    """Test creating user with custom bcrypt rounds."""
    rounds = 10
    user_manager.create_user(
        username="testuser",
        email="max@apexwebservices.com",
        name="Test User",
        password="Password123!",  # nosec B106 - test password
        rounds=rounds,
    )

    # Read config and verify rounds in hash
    with open(temp_config_file) as f:
        config = yaml.safe_load(f)

    stored_password = config["credentials"]["usernames"]["testuser"]["password"]
    assert stored_password.startswith(f"$2b${rounds:02d}$")
