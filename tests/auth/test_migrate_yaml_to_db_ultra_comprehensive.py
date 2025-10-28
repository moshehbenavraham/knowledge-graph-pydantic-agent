"""Ultra comprehensive tests for migrate_yaml_to_db.py (target: 80%+ coverage)."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml


@pytest.fixture
def temp_yaml_config():
    """Create temporary YAML config for testing."""
    config_data = {
        "credentials": {
            "usernames": {
                "admin": {
                    "email": "admin@example.com",
                    "name": "Admin User",
                    "password": "$2b$12$admin_hashed_password",
                },
                "user1": {
                    "email": "user1@example.com",
                    "name": "User One",
                    "password": "$2b$12$user1_hashed_password",
                },
            }
        },
        "cookie": {"name": "test_cookie", "key": "test_key", "expiry_days": 30},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name

    yield Path(temp_path)

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


class TestLoadYamlConfig:
    """Test load_yaml_config() function."""

    def test_load_yaml_config_success(self, temp_yaml_config):
        from src.auth.migrate_yaml_to_db import load_yaml_config

        config = load_yaml_config(temp_yaml_config)

        assert "credentials" in config
        assert "usernames" in config["credentials"]
        assert "admin" in config["credentials"]["usernames"]
        assert "user1" in config["credentials"]["usernames"]

    def test_load_yaml_config_file_not_found(self):
        from src.auth.migrate_yaml_to_db import load_yaml_config

        with pytest.raises(FileNotFoundError):
            load_yaml_config(Path("/nonexistent/config.yaml"))


class TestBackupYamlConfig:
    """Test backup_yaml_config() function."""

    def test_backup_yaml_config_success(self, temp_yaml_config):
        from src.auth.migrate_yaml_to_db import backup_yaml_config

        with patch("builtins.print"):
            backup_path = backup_yaml_config(temp_yaml_config)

        assert backup_path.exists()
        assert "backup" in backup_path.name

        # Verify content
        with open(backup_path) as f:
            backup_content = yaml.safe_load(f)
        with open(temp_yaml_config) as f:
            original_content = yaml.safe_load(f)

        assert backup_content == original_content

        # Cleanup backup
        backup_path.unlink()


@pytest.mark.asyncio
class TestMigrateUsers:
    """Test migrate_users() function."""

    async def test_migrate_users_success(self, temp_yaml_config):
        from src.auth.migrate_yaml_to_db import migrate_users

        mock_client = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_execute = Mock()

        # Mock existing user check (no existing users)
        mock_execute.data = []

        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_execute
        mock_execute.execute.return_value = mock_execute

        # Mock insert
        mock_insert = Mock()
        mock_insert.execute.return_value = Mock(data=[{"id": 123, "username": "admin"}])
        mock_table.insert.return_value = mock_insert

        with patch("src.auth.migrate_yaml_to_db.get_supabase_client") as mock_get_client:
            mock_get_client.return_value = mock_client

            with patch("src.auth.migrate_yaml_to_db.assign_role"):
                with patch("builtins.print"):
                    results = await migrate_users(temp_yaml_config, dry_run=False)

        assert results["migrated"] == 2
        assert results["skipped"] == 0
        assert results["errors"] == 0

    async def test_migrate_users_dry_run(self, temp_yaml_config):
        from src.auth.migrate_yaml_to_db import migrate_users

        with patch("builtins.print"):
            results = await migrate_users(temp_yaml_config, dry_run=True)

        assert results["migrated"] == 0
        assert results["skipped"] == 0
        assert results["errors"] == 0
        assert len(results["details"]) == 2
        assert all(d["status"] == "dry_run" for d in results["details"])

    async def test_migrate_users_skip_existing(self, temp_yaml_config):
        from src.auth.migrate_yaml_to_db import migrate_users

        mock_client = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_execute = Mock()

        # Mock existing user check (admin already exists)
        def mock_eq(field, value):
            if value == "admin":
                mock_execute.data = [{"id": 1, "username": "admin"}]
            else:
                mock_execute.data = []
            return mock_execute

        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq = mock_eq
        mock_execute.execute.return_value = mock_execute

        # Mock insert for user1
        mock_insert = Mock()
        mock_insert.execute.return_value = Mock(data=[{"id": 124, "username": "user1"}])
        mock_table.insert.return_value = mock_insert

        with patch("src.auth.migrate_yaml_to_db.get_supabase_client") as mock_get_client:
            mock_get_client.return_value = mock_client

            with patch("src.auth.migrate_yaml_to_db.assign_role"):
                with patch("builtins.print"):
                    results = await migrate_users(temp_yaml_config, dry_run=False)

        assert results["migrated"] == 1
        assert results["skipped"] == 1
        assert results["errors"] == 0

    async def test_migrate_users_empty_config(self):
        from src.auth.migrate_yaml_to_db import migrate_users

        empty_config = {
            "credentials": {"usernames": {}},
            "cookie": {"name": "test", "key": "test", "expiry_days": 30},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(empty_config, f)
            temp_path = Path(f.name)

        try:
            with patch("builtins.print"):
                results = await migrate_users(temp_path, dry_run=False)

            assert results["migrated"] == 0
            assert results["skipped"] == 0
            assert results["errors"] == 0
        finally:
            temp_path.unlink(missing_ok=True)

    async def test_migrate_users_database_error(self, temp_yaml_config):
        from src.auth.migrate_yaml_to_db import migrate_users

        mock_client = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_execute = Mock()

        # Mock no existing users
        mock_execute.data = []
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_execute
        mock_execute.execute.return_value = mock_execute

        # Mock insert failure
        mock_insert = Mock()
        mock_insert.execute.side_effect = Exception("Database connection failed")
        mock_table.insert.return_value = mock_insert

        with patch("src.auth.migrate_yaml_to_db.get_supabase_client") as mock_get_client:
            mock_get_client.return_value = mock_client

            with patch("builtins.print"):
                results = await migrate_users(temp_yaml_config, dry_run=False)

        assert results["migrated"] == 0
        assert results["errors"] == 2

    async def test_migrate_users_admin_role_assignment(self, temp_yaml_config):
        from src.auth.migrate_yaml_to_db import migrate_users

        mock_client = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_execute = Mock()

        # Mock no existing users
        mock_execute.data = []
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_execute
        mock_execute.execute.return_value = mock_execute

        # Mock insert
        insert_calls = []

        def mock_insert(data):
            insert_calls.append(data)
            mock_insert_result = Mock()
            user_id = 123 if data["username"] == "admin" else 124
            mock_insert_result.execute.return_value = Mock(
                data=[{"id": user_id, "username": data["username"]}]
            )
            return mock_insert_result

        mock_table.insert = mock_insert

        with patch("src.auth.migrate_yaml_to_db.get_supabase_client") as mock_get_client:
            mock_get_client.return_value = mock_client

            with patch("src.auth.migrate_yaml_to_db.assign_role") as mock_assign_role:
                with patch("builtins.print"):
                    await migrate_users(temp_yaml_config, dry_run=False)

                # Verify admin got admin role, user1 got user role
                role_calls = mock_assign_role.call_args_list
                assert len(role_calls) == 2

                # Find admin call
                admin_call = next((call for call in role_calls if call[0][0] == 123), None)
                assert admin_call is not None
                assert admin_call[0][1] == "admin"

                # Find user1 call
                user_call = next((call for call in role_calls if call[0][0] == 124), None)
                assert user_call is not None
                assert user_call[0][1] == "user"


@pytest.mark.asyncio
class TestMain:
    """Test main() function."""

    async def test_main_dry_run(self, temp_yaml_config):
        from src.auth.migrate_yaml_to_db import main

        with patch(
            "sys.argv",
            [
                "migrate_yaml_to_db.py",
                "--config",
                str(temp_yaml_config),
                "--dry-run",
            ],
        ):
            with patch("builtins.print"):
                exit_code = await main()

        assert exit_code == 0

    async def test_main_with_backup(self, temp_yaml_config):
        from src.auth.migrate_yaml_to_db import main

        mock_client = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_execute = Mock()

        # Mock no existing users
        mock_execute.data = []
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_execute
        mock_execute.execute.return_value = mock_execute

        # Mock successful insert
        mock_insert = Mock()
        mock_insert.execute.return_value = Mock(data=[{"id": 123, "username": "admin"}])
        mock_table.insert.return_value = mock_insert

        with patch(
            "sys.argv",
            [
                "migrate_yaml_to_db.py",
                "--config",
                str(temp_yaml_config),
            ],
        ):
            with patch("src.auth.migrate_yaml_to_db.get_supabase_client") as mock_get_client:
                mock_get_client.return_value = mock_client

                with patch("src.auth.migrate_yaml_to_db.assign_role"):
                    with patch("builtins.print"):
                        exit_code = await main()

        assert exit_code == 0

    async def test_main_no_backup(self, temp_yaml_config):
        from src.auth.migrate_yaml_to_db import main

        with patch(
            "sys.argv",
            [
                "migrate_yaml_to_db.py",
                "--config",
                str(temp_yaml_config),
                "--no-backup",
                "--dry-run",
            ],
        ):
            with patch("builtins.print"):
                with patch("src.auth.migrate_yaml_to_db.backup_yaml_config") as mock_backup:
                    exit_code = await main()

                    # Backup should not be called
                    mock_backup.assert_not_called()

        assert exit_code == 0

    async def test_main_config_not_found(self):
        from src.auth.migrate_yaml_to_db import main

        with patch(
            "sys.argv",
            [
                "migrate_yaml_to_db.py",
                "--config",
                "/nonexistent/config.yaml",
            ],
        ):
            with patch("builtins.print"):
                exit_code = await main()

        assert exit_code == 1

    async def test_main_with_errors(self, temp_yaml_config):
        from src.auth.migrate_yaml_to_db import main

        mock_client = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_execute = Mock()

        # Mock no existing users
        mock_execute.data = []
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_execute
        mock_execute.execute.return_value = mock_execute

        # Mock insert failure
        mock_insert = Mock()
        mock_insert.execute.side_effect = Exception("Database error")
        mock_table.insert.return_value = mock_insert

        with patch(
            "sys.argv",
            [
                "migrate_yaml_to_db.py",
                "--config",
                str(temp_yaml_config),
            ],
        ):
            with patch("src.auth.migrate_yaml_to_db.get_supabase_client") as mock_get_client:
                mock_get_client.return_value = mock_client

                with patch("builtins.print"):
                    exit_code = await main()

        assert exit_code == 1
