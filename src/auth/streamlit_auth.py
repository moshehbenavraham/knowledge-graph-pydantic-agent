"""Streamlit authentication integration.

This module provides authentication integration for the Streamlit UI using
streamlit-authenticator.
"""

from pathlib import Path

import streamlit as st
import streamlit_authenticator as stauth
import structlog
import yaml

logger = structlog.get_logger(__name__)


def load_auth_config(config_path: str = "config/auth_config.yaml") -> dict:
    """Load authentication configuration from YAML file.

    Args:
        config_path: Path to auth configuration file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(
            f"Authentication config not found: {config_path}\n"
            "Please create config/auth_config.yaml or disable authentication."
        )

    with open(config_file) as f:
        return yaml.safe_load(f)


def get_authenticator(config: dict | None = None) -> stauth.Authenticate:
    """Get configured authenticator instance.

    Args:
        config: Optional pre-loaded configuration. If None, loads from file.

    Returns:
        Configured Authenticate instance
    """
    if config is None:
        config = load_auth_config()

    # Create authenticator instance
    authenticator = stauth.Authenticate(
        credentials=config["credentials"],
        cookie_name=config["cookie"]["name"],
        cookie_key=config["cookie"]["key"],
        cookie_expiry_days=config["cookie"]["expiry_days"],
        pre_authorized=config.get("preauthorized", {}).get("emails", []),
    )

    return authenticator


def render_login_page() -> tuple[str | None, str | None, bool | None]:
    """Render authentication login page.

    Returns:
        Tuple of (name, username, authentication_status)
    """
    # Load config
    try:
        config = load_auth_config()
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()

    # Get authenticator
    authenticator = get_authenticator(config)

    # Render login form
    st.markdown(
        """
        <style>
        .auth-container {
            max-width: 500px;
            margin: 2rem auto;
            padding: 2rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .auth-title {
            color: white;
            text-align: center;
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
        }
        .auth-subtitle {
            color: rgba(255, 255, 255, 0.9);
            text-align: center;
            margin-bottom: 2rem;
        }
        </style>
        <div class="auth-container">
            <div class="auth-title">🤖 Base Agent</div>
            <div class="auth-subtitle">Advanced RAG AI Assistant</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 🔐 Authentication Required")
    st.info("Please log in to access the Base Agent interface.")

    # Render login widget
    name, authentication_status, username = authenticator.login(location="main")

    # Handle authentication status
    if authentication_status is False:
        st.error("❌ Username or password is incorrect")
        logger.warning("Failed login attempt", username=username)

    elif authentication_status is None:
        st.warning("👋 Please enter your username and password")

    return name, username, authentication_status


def render_logout_button(authenticator: stauth.Authenticate, name: str) -> None:
    """Render logout button in sidebar.

    Args:
        authenticator: Configured authenticator instance
        name: Name of authenticated user
    """
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"**👤 Logged in as:** {name}")

        if st.button("🚪 Logout", use_container_width=True):
            authenticator.logout(location="unrendered")
            st.session_state.clear()
            logger.info("User logged out", name=name)
            st.rerun()


def require_authentication() -> tuple[str, stauth.Authenticate]:
    """Require authentication for the application.

    This function should be called at the beginning of the main() function.
    It will render the login page if the user is not authenticated.

    Returns:
        Tuple of (user's name, authenticator instance)

    Raises:
        st.stop: If user is not authenticated (stops execution)
    """
    # Initialize authentication in session state if not present
    if "authentication_status" not in st.session_state:
        st.session_state.authentication_status = None
        st.session_state.name = None
        st.session_state.username = None

    # If not authenticated, show login page
    if st.session_state.authentication_status is not True:
        logger.info("User not authenticated, showing login page")
        name, username, authentication_status = render_login_page()

        # Update session state
        st.session_state.authentication_status = authentication_status
        st.session_state.name = name
        st.session_state.username = username

        # If authenticated, rerun to load main app
        if authentication_status is True:
            logger.info("User authenticated successfully", username=username, name=name)
            st.rerun()

        # Stop execution if not authenticated
        st.stop()

    # User is authenticated
    logger.debug(
        "User authenticated",
        username=st.session_state.username,
        name=st.session_state.name,
    )

    # Get authenticator for logout functionality
    authenticator = get_authenticator()

    return st.session_state.name, authenticator
