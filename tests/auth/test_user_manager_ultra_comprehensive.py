"""Ultra comprehensive tests for user_manager.py (target: 80%+ coverage)."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing."""
    config_data = {
        "credentials": {
            "usernames": {
                "test_user": {
                    "email": "test@example.com",
                    "name": "Test User",
                    "password": "$2b$12$hashed_password_here",
                }
            }
        },
        "cookie": {"name": "test_cookie", "key": "test_key", "expiry_days": 30},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


class TestUserManagerInit:
    """Test UserManager initialization."""

    def test_user_manager_init_success(self, temp_config_file):
        from src.auth.user_manager import UserManager

        manager = UserManager(config_path=temp_config_file)
        assert manager.config_path == Path(temp_config_file)

    def test_user_manager_init_file_not_found(self):
        from src.auth.user_manager import UserManager

        with pytest.raises(FileNotFoundError):
            UserManager(config_path="/nonexistent/config.yaml")


class TestLoadConfig:
    """Test _load_config() method."""

    def test_load_config_success(self, temp_config_file):
        from src.auth.user_manager import UserManager

        manager = UserManager(config_path=temp_config_file)
        config = manager._load_config()

        assert "credentials" in config
        assert "usernames" in config["credentials"]
        assert "test_user" in config["credentials"]["usernames"]


class TestSaveConfig:
    """Test _save_config() method."""

    def test_save_config_success(self, temp_config_file):
        from src.auth.user_manager import UserManager

        manager = UserManager(config_path=temp_config_file)

        new_config = {
            "credentials": {"usernames": {"new_user": {"email": "new@example.com"}}},
            "cookie": {"name": "test", "key": "test", "expiry_days": 30},
        }

        manager._save_config(new_config)

        # Verify saved
        loaded_config = manager._load_config()
        assert "new_user" in loaded_config["credentials"]["usernames"]


class TestCreateUser:
    """Test create_user() method."""

    def test_create_user_success(self, temp_config_file):
        from src.auth.user_manager import UserManager

        manager = UserManager(config_path=temp_config_file)

        with patch("src.auth.user_manager.hash_password") as mock_hash:
            mock_hash.return_value = "$2b$12$new_hashed_password"

            with patch("builtins.print"):
                manager.create_user(
                    username="new_user",
                    email="new@example.com",
                    name="New User",
                    password="password123",
                )

            mock_hash.assert_called_once_with("password123", rounds=12)

            # Verify user was created
            config = manager._load_config()
            assert "new_user" in config["credentials"]["usernames"]
            assert config["credentials"]["usernames"]["new_user"]["email"] == "new@example.com"
            assert config["credentials"]["usernames"]["new_user"]["name"] == "New User"

    def test_create_user_duplicate(self, temp_config_file):
        from src.auth.user_manager import UserManager

        manager = UserManager(config_path=temp_config_file)

        with pytest.raises(ValueError, match="already exists"):
            manager.create_user(
                username="test_user",
                email="test@example.com",
                name="Test",
                password="password",
            )

    def test_create_user_custom_rounds(self, temp_config_file):
        from src.auth.user_manager import UserManager

        manager = UserManager(config_path=temp_config_file)

        with patch("src.auth.user_manager.hash_password") as mock_hash:
            mock_hash.return_value = "$2b$14$hashed"

            with patch("builtins.print"):
                manager.create_user(
                    username="user2",
                    email="user2@example.com",
                    name="User 2",
                    password="pass",
                    rounds=14,
                )

            mock_hash.assert_called_once_with("pass", rounds=14)


class TestUpdatePassword:
    """Test update_password() method."""

    def test_update_password_success(self, temp_config_file):
        from src.auth.user_manager import UserManager

        manager = UserManager(config_path=temp_config_file)

        with patch("src.auth.user_manager.hash_password") as mock_hash:
            mock_hash.return_value = "$2b$12$updated_hash"

            with patch("builtins.print"):
                manager.update_password("test_user", "new_password")

            mock_hash.assert_called_once_with("new_password", rounds=12)

            # Verify password was updated
            config = manager._load_config()
            assert (
                config["credentials"]["usernames"]["test_user"]["password"] == "$2b$12$updated_hash"
            )

    def test_update_password_user_not_found(self, temp_config_file):
        from src.auth.user_manager import UserManager

        manager = UserManager(config_path=temp_config_file)

        with pytest.raises(ValueError, match="not found"):
            manager.update_password("nonexistent_user", "new_password")

    def test_update_password_custom_rounds(self, temp_config_file):
        from src.auth.user_manager import UserManager

        manager = UserManager(config_path=temp_config_file)

        with patch("src.auth.user_manager.hash_password") as mock_hash:
            mock_hash.return_value = "$2b$10$hash"

            with patch("builtins.print"):
                manager.update_password("test_user", "pass", rounds=10)

            mock_hash.assert_called_once_with("pass", rounds=10)


class TestDeleteUser:
    """Test delete_user() method."""

    def test_delete_user_success(self, temp_config_file):
        from src.auth.user_manager import UserManager

        manager = UserManager(config_path=temp_config_file)

        with patch("builtins.print"):
            manager.delete_user("test_user")

        # Verify user was deleted
        config = manager._load_config()
        assert "test_user" not in config["credentials"]["usernames"]

    def test_delete_user_not_found(self, temp_config_file):
        from src.auth.user_manager import UserManager

        manager = UserManager(config_path=temp_config_file)

        with pytest.raises(ValueError, match="not found"):
            manager.delete_user("nonexistent_user")


class TestListUsers:
    """Test list_users() method."""

    def test_list_users_success(self, temp_config_file):
        from src.auth.user_manager import UserManager

        manager = UserManager(config_path=temp_config_file)

        users = manager.list_users()

        assert len(users) == 1
        assert users[0]["username"] == "test_user"
        assert users[0]["email"] == "test@example.com"
        assert users[0]["name"] == "Test User"

    def test_list_users_multiple(self, temp_config_file):
        from src.auth.user_manager import UserManager

        manager = UserManager(config_path=temp_config_file)

        # Add another user
        with patch("src.auth.user_manager.hash_password") as mock_hash:
            mock_hash.return_value = "$2b$12$hash"
            with patch("builtins.print"):
                manager.create_user("user2", "user2@example.com", "User 2", "pass")

        users = manager.list_users()

        assert len(users) == 2
        usernames = [u["username"] for u in users]
        assert "test_user" in usernames
        assert "user2" in usernames

    def test_list_users_empty_config(self):
        from src.auth.user_manager import UserManager

        empty_config = {
            "credentials": {"usernames": {}},
            "cookie": {"name": "test", "key": "test", "expiry_days": 30},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(empty_config, f)
            temp_path = f.name

        try:
            manager = UserManager(config_path=temp_path)
            users = manager.list_users()

            assert len(users) == 0
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestGetUser:
    """Test get_user() method."""

    def test_get_user_success(self, temp_config_file):
        from src.auth.user_manager import UserManager

        manager = UserManager(config_path=temp_config_file)

        user = manager.get_user("test_user")

        assert user is not None
        assert user["username"] == "test_user"
        assert user["email"] == "test@example.com"
        assert user["name"] == "Test User"

    def test_get_user_not_found(self, temp_config_file):
        from src.auth.user_manager import UserManager

        manager = UserManager(config_path=temp_config_file)

        user = manager.get_user("nonexistent_user")

        assert user is None


class TestMain:
    """Test main CLI function."""

    def test_main_create_user(self, temp_config_file):
        from src.auth.user_manager import main

        with patch(
            "sys.argv",
            [
                "user_manager.py",
                "create",
                "--username",
                "cli_user",
                "--email",
                "cli@example.com",
                "--name",
                "CLI User",
                "--password",
                "password",
                "--config",
                temp_config_file,
            ],
        ):
            with patch("src.auth.user_manager.hash_password") as mock_hash:
                mock_hash.return_value = "$2b$12$hash"

                with patch("builtins.print"):
                    main()

        # Verify user was created
        from src.auth.user_manager import UserManager

        manager = UserManager(config_path=temp_config_file)
        user = manager.get_user("cli_user")
        assert user is not None

    def test_main_list_users(self, temp_config_file):
        from src.auth.user_manager import main

        with patch(
            "sys.argv",
            [
                "user_manager.py",
                "list",
                "--config",
                temp_config_file,
            ],
        ):
            with patch("builtins.print") as mock_print:
                main()

                mock_print.assert_called()

    def test_main_get_user(self, temp_config_file):
        from src.auth.user_manager import main

        with patch(
            "sys.argv",
            [
                "user_manager.py",
                "get",
                "--username",
                "test_user",
                "--config",
                temp_config_file,
            ],
        ):
            with patch("builtins.print") as mock_print:
                main()

                mock_print.assert_called()

    def test_main_delete_user(self, temp_config_file):
        from src.auth.user_manager import main

        with patch(
            "sys.argv",
            [
                "user_manager.py",
                "delete",
                "--username",
                "test_user",
                "--config",
                temp_config_file,
            ],
        ):
            with patch("builtins.print"):
                main()

        # Verify user was deleted
        from src.auth.user_manager import UserManager

        manager = UserManager(config_path=temp_config_file)
        user = manager.get_user("test_user")
        assert user is None

    def test_main_update_password(self, temp_config_file):
        from src.auth.user_manager import main

        with patch(
            "sys.argv",
            [
                "user_manager.py",
                "update-password",
                "--username",
                "test_user",
                "--password",
                "new_password",
                "--config",
                temp_config_file,
            ],
        ):
            with patch("src.auth.user_manager.hash_password") as mock_hash:
                mock_hash.return_value = "$2b$12$new_hash"

                with patch("builtins.print"):
                    main()

    def test_main_create_missing_args(self, temp_config_file):
        from src.auth.user_manager import main

        with patch(
            "sys.argv",
            [
                "user_manager.py",
                "create",
                "--username",
                "user",
                "--config",
                temp_config_file,
            ],
        ):
            with patch("builtins.print") as mock_print:
                main()

                # Should print error about missing args
                assert any("Error" in str(call) for call in mock_print.call_args_list)

    def test_main_delete_missing_args(self, temp_config_file):
        from src.auth.user_manager import main

        with patch(
            "sys.argv",
            [
                "user_manager.py",
                "delete",
                "--config",
                temp_config_file,
            ],
        ):
            with patch("builtins.print") as mock_print:
                main()

                # Should print error
                assert any("Error" in str(call) for call in mock_print.call_args_list)
