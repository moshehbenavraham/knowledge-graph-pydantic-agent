"""
Auth test fixtures and configuration.

Provides test isolation for streamlit session state and other auth-related mocks.
"""

import sys
from unittest.mock import MagicMock

import pytest


def _is_streamlit_mock():
    """Check if the current streamlit module is a mock."""
    if "streamlit" not in sys.modules:
        return False
    st = sys.modules["streamlit"]
    return isinstance(st, MagicMock) or "MagicMock" in str(type(st))


def _ensure_real_streamlit():
    """
    Ensure the real streamlit module is loaded, not a mock.

    This handles cases where other tests (like test_e2e.py) replace streamlit
    with a MagicMock. We detect this and reload the real module and any
    modules that depend on it.
    """
    if not _is_streamlit_mock():
        return  # Streamlit is real, nothing to do

    # Remove all streamlit-related modules from sys.modules
    modules_to_remove = [
        name
        for name in list(sys.modules.keys())
        if name == "streamlit" or name.startswith("streamlit.")
    ]
    for name in modules_to_remove:
        del sys.modules[name]

    # Also remove auth and ui modules that import streamlit at module level
    # so they get reloaded with the real streamlit
    dependent_modules_to_remove = [
        name
        for name in list(sys.modules.keys())
        if (
            name.startswith("src.auth.")
            or name.startswith("src.ui.")
            or name in {"src.auth", "src.ui"}
        )
    ]
    for name in dependent_modules_to_remove:
        del sys.modules[name]

    # Re-import the real streamlit
    import streamlit  # noqa: F401


@pytest.fixture(autouse=True)
def reset_streamlit_state():
    """Reset streamlit session state before and after each test.

    This fixture ensures tests don't pollute each other's session state.
    It also ensures the real streamlit module is loaded (not a mock).
    """
    # Ensure we have the real streamlit, not a mock
    _ensure_real_streamlit()

    import streamlit as st

    # Store original session_state if it exists
    original_state = getattr(st, "session_state", None)

    # Create a fresh mock session state for tests
    mock_state = MagicMock()
    mock_state.__contains__ = MagicMock(return_value=False)
    mock_state.get = MagicMock(return_value=None)
    mock_state.__getitem__ = MagicMock(side_effect=KeyError)
    mock_state.__setitem__ = MagicMock()
    mock_state.__delitem__ = MagicMock()

    yield

    # Restore original state or reset to clean state
    if original_state is not None:
        try:
            # Clear any keys that might have been added
            if hasattr(st.session_state, "clear"):
                st.session_state.clear()
        except Exception:
            pass


@pytest.fixture(autouse=True)
def mock_auth_settings(monkeypatch):
    """Provide default auth settings for tests.

    This ensures tests have consistent auth configuration.
    """
    # Set default environment variables for auth tests
    monkeypatch.setenv("USE_DATABASE_AUTH", "false")
    monkeypatch.setenv("AUTH_COOKIE_KEY", "test_cookie_key_12345")
    monkeypatch.setenv("OAUTH_ENABLED", "false")


@pytest.fixture
def mock_session_state():
    """Create a mock session state for testing.

    Returns a dict-like object that supports both dict and attribute access.
    """

    class MockSessionState(dict):
        """Mock session state that supports both dict-like and attribute access."""

        def __getattr__(self, name):
            try:
                return self[name]
            except KeyError:
                raise AttributeError(f"No attribute {name}")

        def __setattr__(self, name, value):
            self[name] = value

        def __delattr__(self, name):
            try:
                del self[name]
            except KeyError:
                raise AttributeError(f"No attribute {name}")

    return MockSessionState


@pytest.fixture
def mock_supabase_client():
    """Provide a mock Supabase client for auth tests."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.execute.return_value.data = []
    return mock_client


@pytest.fixture
def mock_authenticator():
    """Provide a mock authenticator object."""
    mock_auth = MagicMock()
    mock_auth.login.return_value = None
    mock_auth.logout.return_value = None
    mock_auth.authentication_status = None
    mock_auth.username = None
    mock_auth.name = None
    return mock_auth


@pytest.fixture
def sample_auth_config():
    """Provide a sample auth configuration."""
    return {
        "credentials": {
            "usernames": {
                "testuser": {
                    "email": "test@example.com",
                    "name": "Test User",
                    "password": "$2b$12$test_hash",
                }
            }
        },
        "cookie": {"name": "test_cookie", "key": "test_key", "expiry_days": 30},
        "preauthorized": {"emails": []},
    }
