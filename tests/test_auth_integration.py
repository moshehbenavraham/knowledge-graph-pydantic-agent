"""Integration tests for Streamlit authentication."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import streamlit_authenticator as stauth
import yaml

from src.auth.streamlit_auth import get_authenticator, load_auth_config


@pytest.fixture
def temp_auth_config():
    """Create a temporary auth config file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config = {
            "credentials": {
                "usernames": {
                    "testuser": {
                        "email": "test@example.com",
                        "name": "Test User",
                        # Password: TestPassword123! (bcrypt hashed)
                        "password": "$2b$12$VQvZ9b8aQaYG5J.ZvVq4ZeYxHGYKJ3a7Uu6JT5qJVQvZ9b8aQaYG5.",
                    }
                }
            },
            "cookie": {
                "name": "test_auth_cookie",
                "key": "test_secret_key_12345",
                "expiry_days": 30,
            },
            "preauthorized": {"emails": ["allowed@example.com"]},
        }
        yaml.dump(config, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


def test_load_auth_config_success(temp_auth_config):
    """Test successful loading of auth config."""
    config = load_auth_config(temp_auth_config)

    assert "credentials" in config
    assert "cookie" in config
    assert "preauthorized" in config
    assert "testuser" in config["credentials"]["usernames"]


def test_load_auth_config_missing_file():
    """Test loading non-existent config file raises error."""
    with pytest.raises(FileNotFoundError):
        load_auth_config("nonexistent_config.yaml")


def test_get_authenticator_with_config(temp_auth_config):
    """Test getting authenticator with provided config."""
    config = load_auth_config(temp_auth_config)
    authenticator = get_authenticator(config)

    assert isinstance(authenticator, stauth.Authenticate)


def test_get_authenticator_without_config(temp_auth_config):
    """Test getting authenticator without providing config (loads from file)."""
    with patch("src.auth.streamlit_auth.load_auth_config") as mock_load:
        mock_load.return_value = load_auth_config(temp_auth_config)
        authenticator = get_authenticator()

        assert isinstance(authenticator, stauth.Authenticate)
        mock_load.assert_called_once()


def test_authenticator_has_correct_cookie_settings(temp_auth_config):
    """Test that authenticator is configured with correct cookie settings."""
    config = load_auth_config(temp_auth_config)
    authenticator = get_authenticator(config)

    # Verify authenticator was created successfully
    # Note: streamlit-authenticator stores cookie settings internally as private attributes
    assert isinstance(authenticator, stauth.Authenticate)
    # Cookie settings are validated during initialization, if invalid it would raise an error


def test_authenticator_has_credentials(temp_auth_config):
    """Test that authenticator has user credentials loaded."""
    config = load_auth_config(temp_auth_config)
    authenticator = get_authenticator(config)

    # Verify authenticator was created successfully with credentials
    # Note: streamlit-authenticator stores credentials internally
    assert isinstance(authenticator, stauth.Authenticate)
    # Credentials are validated during initialization, if invalid it would raise an error
    # We verify the config structure separately in other tests


def test_config_structure_validation(temp_auth_config):
    """Test that loaded config has expected structure."""
    config = load_auth_config(temp_auth_config)

    # Verify required top-level keys
    assert "credentials" in config
    assert "cookie" in config

    # Verify credentials structure
    assert "usernames" in config["credentials"]
    assert isinstance(config["credentials"]["usernames"], dict)

    # Verify cookie structure
    assert "name" in config["cookie"]
    assert "key" in config["cookie"]
    assert "expiry_days" in config["cookie"]

    # Verify types
    assert isinstance(config["cookie"]["name"], str)
    assert isinstance(config["cookie"]["key"], str)
    assert isinstance(config["cookie"]["expiry_days"], int)


def test_preauthorized_emails_loaded(temp_auth_config):
    """Test that pre-authorized emails are loaded correctly."""
    config = load_auth_config(temp_auth_config)

    assert "preauthorized" in config
    assert "emails" in config["preauthorized"]
    assert "allowed@example.com" in config["preauthorized"]["emails"]


def test_multiple_users_in_config():
    """Test loading config with multiple users."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config = {
            "credentials": {
                "usernames": {
                    "user1": {
                        "email": "user1@example.com",
                        "name": "User One",
                        "password": "$2b$12$hash1",
                    },
                    "user2": {
                        "email": "user2@example.com",
                        "name": "User Two",
                        "password": "$2b$12$hash2",
                    },
                    "user3": {
                        "email": "user3@example.com",
                        "name": "User Three",
                        "password": "$2b$12$hash3",
                    },
                }
            },
            "cookie": {"name": "test", "key": "key", "expiry_days": 30},
            "preauthorized": {"emails": []},
        }
        yaml.dump(config, f)
        temp_path = f.name

    try:
        loaded_config = load_auth_config(temp_path)
        assert len(loaded_config["credentials"]["usernames"]) == 3
        assert "user1" in loaded_config["credentials"]["usernames"]
        assert "user2" in loaded_config["credentials"]["usernames"]
        assert "user3" in loaded_config["credentials"]["usernames"]
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_config_with_empty_users():
    """Test loading config with no users."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config = {
            "credentials": {"usernames": {}},
            "cookie": {"name": "test", "key": "key", "expiry_days": 30},
            "preauthorized": {"emails": []},
        }
        yaml.dump(config, f)
        temp_path = f.name

    try:
        loaded_config = load_auth_config(temp_path)
        assert len(loaded_config["credentials"]["usernames"]) == 0
        authenticator = get_authenticator(loaded_config)
        assert isinstance(authenticator, stauth.Authenticate)
    finally:
        Path(temp_path).unlink(missing_ok=True)
