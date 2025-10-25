"""Streamlit authentication integration.

This module provides authentication integration for the Streamlit UI using
streamlit-authenticator with support for both YAML and database backends.
Includes OAuth 2.0 support for Google and GitHub.
"""

import asyncio
import os
from pathlib import Path

import streamlit as st
import streamlit_authenticator as stauth
import structlog
import yaml

from src.auth.security import get_rate_limiter, log_auth_event

logger = structlog.get_logger(__name__)

# Authentication backend configuration
# Set USE_DATABASE_AUTH=true in .env to use database instead of YAML
USE_DATABASE_AUTH = os.getenv("USE_DATABASE_AUTH", "false").lower() == "true"

# OAuth configuration
OAUTH_ENABLED = os.getenv("OAUTH_ENABLED", "false").lower() == "true"
GOOGLE_OAUTH_ENABLED = os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET")
GITHUB_OAUTH_ENABLED = os.getenv("GITHUB_CLIENT_ID") and os.getenv("GITHUB_CLIENT_SECRET")


async def load_credentials_from_database() -> dict:
    """Load user credentials from database.

    Returns:
        Credentials dictionary in streamlit-authenticator format

    Raises:
        Exception: If database query fails
    """
    from src.auth.db import list_users

    try:
        users = await list_users(limit=1000, include_deleted=False)

        # Convert to streamlit-authenticator format
        credentials = {"usernames": {}}

        for user in users:
            if not user.get("is_active"):
                continue  # Skip inactive users

            username = user.get("username")
            # Get password_hash directly from database (without popping it)
            from src.clients.database import get_supabase_client

            client = get_supabase_client()
            user_with_hash = (
                client.table("auth_users")
                .select("password_hash")
                .eq("username", username)
                .limit(1)
                .execute()
            )

            password_hash = (
                user_with_hash.data[0].get("password_hash") if user_with_hash.data else None
            )

            credentials["usernames"][username] = {
                "email": user.get("email"),
                "name": user.get("full_name"),
                "password": password_hash,
            }

        logger.info("Loaded credentials from database", user_count=len(credentials["usernames"]))
        return credentials

    except Exception as e:
        logger.error("Failed to load credentials from database", error=str(e))
        raise


def load_auth_config(config_path: str = "config/auth_config.yaml") -> dict:
    """Load authentication configuration.

    If USE_DATABASE_AUTH=true, loads credentials from database.
    Otherwise, loads from YAML file.

    Args:
        config_path: Path to auth configuration file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist (YAML mode)
        Exception: If database query fails (database mode)
    """
    config_file = Path(config_path)

    # Load base config from YAML (for cookie settings, etc.)
    if not config_file.exists():
        # If database mode, we still need a minimal config
        if USE_DATABASE_AUTH:
            logger.warning(
                "Auth config not found, using defaults for database mode",
                config_path=config_path,
            )
            config = {
                "cookie": {
                    "name": "base_agent_auth_cookie",
                    "key": os.getenv(
                        "AUTH_COOKIE_KEY", "base_agent_secret_key_2025"
                    ),  # Use env var in production
                    "expiry_days": 30,
                },
                "preauthorized": {"emails": []},
                "config": {
                    "logout_button_location": "sidebar",
                    "auto_logout": True,
                    "auto_logout_minutes": 30,
                },
            }
        else:
            raise FileNotFoundError(
                f"Authentication config not found: {config_path}\n"
                "Please create config/auth_config.yaml or set USE_DATABASE_AUTH=true."
            )
    else:
        with open(config_file) as f:
            config = yaml.safe_load(f)

    # Load credentials based on backend
    if USE_DATABASE_AUTH:
        logger.info("Using database authentication backend")
        # Load credentials from database
        try:
            credentials = asyncio.run(load_credentials_from_database())
            config["credentials"] = credentials
        except Exception as e:
            logger.error("Failed to load database credentials, falling back to YAML", error=str(e))
            # Fallback to YAML if available
            if "credentials" not in config:
                raise
    else:
        logger.info("Using YAML authentication backend")
        # Credentials already in config from YAML

    return config


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

    # Get rate limiter
    rate_limiter = get_rate_limiter()

    # Remember me checkbox (before login form)
    remember_me = st.checkbox(
        "🔐 Remember me for 90 days",
        value=False,
        key="remember_me_checkbox",
        help="Keep me logged in for 90 days instead of 30",
    )

    # Store remember_me in session state for later use
    st.session_state.remember_me = remember_me

    # Check if any user in form is locked out (we check after form submission)
    # For now, render the login form
    name, authentication_status, username = authenticator.login(location="main")

    # Handle authentication status
    if authentication_status is False:
        # Failed login attempt
        if username:
            # Check if locked out
            is_locked, remaining = rate_limiter.is_locked_out(username)

            if is_locked:
                minutes = int(remaining / 60) + 1
                st.error(
                    f"🔒 Account locked due to too many failed attempts. "
                    f"Please try again in {minutes} minute(s)."
                )
                logger.error("Login attempt while locked out", username=username)
            else:
                # Record failed attempt
                rate_limiter.record_failed_attempt(username)
                remaining_attempts = rate_limiter.get_remaining_attempts(username)

                if remaining_attempts > 0:
                    st.error(
                        f"❌ Username or password is incorrect. "
                        f"{remaining_attempts} attempt(s) remaining."
                    )
                else:
                    st.error(
                        "🔒 Account locked due to too many failed attempts. "
                        "Please try again in 15 minutes."
                    )

                logger.warning(
                    "Failed login attempt",
                    username=username,
                    remaining_attempts=remaining_attempts,
                )

            # Log failed auth event
            try:
                asyncio.run(
                    log_auth_event(
                        event_type="login",
                        username=username or "unknown",
                        success=False,
                        metadata=(
                            {"locked_out": is_locked, "remaining_attempts": remaining_attempts}
                            if not is_locked
                            else {"locked_out": True}
                        ),
                    )
                )
            except Exception as e:
                logger.warning("Failed to log auth event", error=str(e))

    elif authentication_status is None:
        st.warning("👋 Please enter your username and password")

    # OAuth login buttons (only in database mode with OAuth enabled)
    if USE_DATABASE_AUTH and OAUTH_ENABLED:
        render_oauth_buttons()

    # Password reset option (only in database mode)
    if USE_DATABASE_AUTH:
        st.markdown("---")
        with st.expander("🔑 Forgot your password?"):
            st.markdown("Enter your username or email to receive a password reset link.")

            reset_input = st.text_input(
                "Username or Email",
                key="password_reset_input",
                placeholder="username or email@example.com",
            )

            if st.button("Send Reset Link", key="send_reset_button"):
                if not reset_input:
                    st.error("Please enter your username or email.")
                else:
                    # Request password reset
                    from src.auth.password_reset import request_password_reset

                    # Reset URL (use current app URL or configured URL)
                    reset_url = os.getenv(
                        "PASSWORD_RESET_URL", "http://localhost:8501/reset-password"
                    )

                    try:
                        success, message = asyncio.run(
                            request_password_reset(reset_input, reset_url)
                        )

                        if success:
                            st.success(message)
                            st.info(
                                "💡 Tip: Check your email inbox (and spam folder) for the reset link."
                            )
                        else:
                            st.error(message)

                    except Exception as e:
                        logger.error("Password reset request failed", error=str(e))
                        st.error("An error occurred. Please try again later.")

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
            username = st.session_state.get("username", "unknown")
            db_session_token = st.session_state.get("db_session_token")

            # Revoke database session (if exists)
            if db_session_token:
                try:
                    asyncio.run(revoke_db_session(db_session_token))
                except Exception as e:
                    logger.warning("Failed to revoke database session", error=str(e))

            # Logout from streamlit-authenticator
            authenticator.logout(location="unrendered")

            # Log logout event
            try:
                asyncio.run(
                    log_auth_event(
                        event_type="logout",
                        username=username,
                        success=True,
                        metadata={"name": name},
                    )
                )
            except Exception as e:
                logger.warning("Failed to log logout event", error=str(e))

            st.session_state.clear()
            logger.info("User logged out", name=name, username=username)
            st.rerun()


async def create_db_session(username: str, remember_me: bool = False) -> str | None:
    """Create database session for authenticated user.

    Args:
        username: Authenticated username
        remember_me: If True, extends session duration to 90 days instead of 30

    Returns:
        Session token or None if failed
    """
    if not USE_DATABASE_AUTH:
        return None  # Only create DB sessions in database mode

    try:
        from src.auth.db import create_session, get_user_by_username

        # Get user ID
        user = await get_user_by_username(username)
        if not user:
            logger.error("User not found for session creation", username=username)
            return None

        # Determine session duration based on remember_me
        expires_in_days = 90 if remember_me else 30

        # Create session
        session = await create_session(
            user_id=user["id"],
            expires_in_days=expires_in_days,
            session_type="web",
            user_agent=st.context.headers.get("User-Agent") if hasattr(st, "context") else None,
        )

        logger.info(
            "Database session created",
            username=username,
            session_id=session["id"],
            remember_me=remember_me,
            expires_in_days=expires_in_days,
        )
        return session["session_token"]

    except Exception as e:
        logger.error("Failed to create database session", username=username, error=str(e))
        return None


async def revoke_db_session(session_token: str | None) -> bool:
    """Revoke database session.

    Args:
        session_token: Session token to revoke

    Returns:
        True if successful
    """
    if not USE_DATABASE_AUTH or not session_token:
        return False

    try:
        from src.auth.db import revoke_session

        success = await revoke_session(session_token)
        logger.info("Database session revoked", success=success)
        return success

    except Exception as e:
        logger.error("Failed to revoke database session", error=str(e))
        return False


async def handle_oauth_callback(provider: str, code: str, state: str | None = None) -> dict | None:
    """Handle OAuth callback and authenticate user.

    Args:
        provider: OAuth provider name ('google' or 'github')
        code: Authorization code from OAuth callback
        state: State parameter for CSRF validation

    Returns:
        User data dictionary or None if failed
    """
    try:
        from src.auth.oauth_handler import complete_oauth_flow

        # Complete OAuth flow
        result = await complete_oauth_flow(provider, code, state)

        user = result["user"]
        is_new_user = result["is_new_user"]

        logger.info(
            f"OAuth authentication successful for {provider}",
            username=user["username"],
            is_new_user=is_new_user,
        )

        # Log auth event
        await log_auth_event(
            event_type="login",
            username=user["username"],
            success=True,
            metadata={
                "provider": provider,
                "is_new_user": is_new_user,
                "auth_method": "oauth",
            },
        )

        return user

    except Exception as e:
        logger.error(f"OAuth callback handling failed for {provider}", error=str(e))
        # Log failed auth event
        try:
            await log_auth_event(
                event_type="login",
                username="unknown",
                success=False,
                metadata={
                    "provider": provider,
                    "error": str(e),
                    "auth_method": "oauth",
                },
            )
        except Exception as log_error:
            logger.warning("Failed to log OAuth error event", error=str(log_error))

        return None


def initiate_oauth_login(provider: str) -> None:
    """Initiate OAuth login flow.

    Args:
        provider: OAuth provider name ('google' or 'github')
    """
    try:
        from src.auth.oauth_handler import initiate_oauth_flow

        # Generate authorization URL with state
        auth_url, state = asyncio.run(initiate_oauth_flow(provider))

        # Store state in session for CSRF validation
        st.session_state[f"oauth_state_{provider}"] = state

        logger.info(f"Initiating OAuth login for {provider}", provider=provider)

        # Redirect to OAuth provider
        st.markdown(
            f'<meta http-equiv="refresh" content="0;url={auth_url}">',
            unsafe_allow_html=True,
        )
        st.stop()

    except Exception as e:
        logger.error(f"Failed to initiate OAuth login for {provider}", error=str(e))
        st.error(f"OAuth login failed: {e!s}")


def render_oauth_buttons() -> None:
    """Render OAuth login buttons for enabled providers."""
    if not OAUTH_ENABLED or not USE_DATABASE_AUTH:
        return  # OAuth only supported in database mode

    st.markdown("---")
    st.markdown("### Or sign in with")

    col1, col2 = st.columns(2)

    with col1:
        if GOOGLE_OAUTH_ENABLED:
            if st.button("🔵 Google", use_container_width=True, key="google_oauth"):
                initiate_oauth_login("google")

    with col2:
        if GITHUB_OAUTH_ENABLED:
            if st.button("⚫ GitHub", use_container_width=True, key="github_oauth"):
                initiate_oauth_login("github")


def check_oauth_callback() -> tuple[str | None, str | None]:
    """Check for OAuth callback parameters in URL.

    Returns:
        Tuple of (username, name) if OAuth callback successful, else (None, None)
    """
    if not OAUTH_ENABLED or not USE_DATABASE_AUTH:
        return None, None

    # Check for OAuth callback parameters
    query_params = st.query_params

    # Check for 'code' parameter (OAuth callback)
    code = query_params.get("code")
    state = query_params.get("state")

    if not code:
        return None, None

    # Determine provider from state or URL path
    provider = None
    if "google" in str(query_params):
        provider = "google"
    elif "github" in str(query_params):
        provider = "github"

    # Fallback: check session state for stored OAuth state
    if not provider:
        for prov in ["google", "github"]:
            stored_state = st.session_state.get(f"oauth_state_{prov}")
            if stored_state == state:
                provider = prov
                break

    if not provider:
        logger.warning("Could not determine OAuth provider from callback")
        st.error("OAuth error: Invalid provider")
        st.query_params.clear()
        return None, None

    # Validate state (CSRF protection)
    stored_state = st.session_state.get(f"oauth_state_{provider}")
    if stored_state and stored_state != state:
        logger.warning(
            f"OAuth state mismatch for {provider}", stored_state=stored_state, received_state=state
        )
        st.error("OAuth error: Invalid state parameter (CSRF protection)")
        st.query_params.clear()
        return None, None

    # Handle OAuth callback
    try:
        user = asyncio.run(handle_oauth_callback(provider, code, state))

        if user:
            # Clear OAuth state from session
            st.session_state.pop(f"oauth_state_{provider}", None)

            # Clear query parameters
            st.query_params.clear()

            # Return user info
            return user["username"], user.get("full_name")
        st.error(f"{provider.capitalize()} login failed. Please try again.")
        st.query_params.clear()
        return None, None

    except Exception as e:
        logger.error(f"OAuth callback error for {provider}", error=str(e))
        st.error(f"OAuth error: {e!s}")
        st.query_params.clear()
        return None, None


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
        st.session_state.db_session_token = None

    # Check for OAuth callback first (before showing login page)
    if st.session_state.authentication_status is not True:
        oauth_username, oauth_name = check_oauth_callback()

        if oauth_username and oauth_name:
            # OAuth authentication successful
            logger.info("OAuth authentication successful", username=oauth_username, name=oauth_name)

            # Update session state
            st.session_state.authentication_status = True
            st.session_state.name = oauth_name
            st.session_state.username = oauth_username

            # Create database session
            if USE_DATABASE_AUTH:
                try:
                    session_token = asyncio.run(create_db_session(oauth_username))
                    st.session_state.db_session_token = session_token
                except Exception as e:
                    logger.warning("Failed to create database session for OAuth user", error=str(e))

            # Rerun to load main app
            st.rerun()

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

            # Record successful login in rate limiter
            rate_limiter = get_rate_limiter()
            rate_limiter.record_successful_login(username)

            # Create database session (if database mode)
            if USE_DATABASE_AUTH:
                try:
                    # Get remember_me preference from session state
                    remember_me = st.session_state.get("remember_me", False)
                    session_token = asyncio.run(create_db_session(username, remember_me=remember_me))
                    st.session_state.db_session_token = session_token
                except Exception as e:
                    logger.warning("Failed to create database session", error=str(e))

            # Log successful auth event
            try:
                asyncio.run(
                    log_auth_event(
                        event_type="login",
                        username=username,
                        success=True,
                        metadata={"name": name},
                    )
                )
            except Exception as e:
                logger.warning("Failed to log successful auth event", error=str(e))

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
