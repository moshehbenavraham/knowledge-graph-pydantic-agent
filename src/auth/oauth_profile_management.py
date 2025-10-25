"""
OAuth Account Management UI Component

Provides user interface for managing OAuth account linkages in user profile.
Allows users to view, link, and unlink OAuth providers (Google, GitHub, Microsoft, Apple).
"""

import asyncio
import os

import streamlit as st
import structlog

from src.auth.db import get_user_by_username, get_user_oauth_accounts, unlink_oauth_account

logger = structlog.get_logger(__name__)

# OAuth providers configuration
OAUTH_PROVIDERS = {
    "google": {
        "name": "Google",
        "icon": "🔵",
        "color": "#4285F4",
        "enabled": bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET")),
    },
    "github": {
        "name": "GitHub",
        "icon": "⚫",
        "color": "#24292e",
        "enabled": bool(os.getenv("GITHUB_CLIENT_ID") and os.getenv("GITHUB_CLIENT_SECRET")),
    },
    "microsoft": {
        "name": "Microsoft",
        "icon": "🟦",
        "color": "#0078D4",
        "enabled": bool(os.getenv("MICROSOFT_CLIENT_ID") and os.getenv("MICROSOFT_CLIENT_SECRET")),
    },
    "apple": {
        "name": "Apple",
        "icon": "",
        "color": "#000000",
        "enabled": bool(os.getenv("APPLE_CLIENT_ID") and os.getenv("APPLE_CLIENT_SECRET")),
    },
}


def get_provider_display_name(provider: str) -> str:
    """Get display name for OAuth provider."""
    return OAUTH_PROVIDERS.get(provider, {}).get("name", provider.capitalize())


def get_provider_icon(provider: str) -> str:
    """Get icon emoji for OAuth provider."""
    return OAUTH_PROVIDERS.get(provider, {}).get("icon", "🔗")


async def get_linked_oauth_accounts(username: str) -> list[dict]:
    """
    Get all linked OAuth accounts for a user.

    Args:
        username: Username

    Returns:
        List of linked OAuth account records
    """
    try:
        user = await get_user_by_username(username)
        if not user:
            return []

        accounts = await get_user_oauth_accounts(user["id"])
        return [acc for acc in accounts if acc.get("is_active", True)]

    except Exception as e:
        logger.error("Failed to get linked OAuth accounts", username=username, error=str(e))
        return []


def render_oauth_account_management() -> None:
    """
    Render OAuth account management interface in user profile.

    Shows linked OAuth accounts and allows linking/unlinking.
    """
    current_username = st.session_state.get("username")
    if not current_username:
        st.error("Not authenticated")
        return

    st.markdown("### 🔗 Connected Accounts")
    st.write("Link or unlink OAuth providers to your account for easy sign-in.")

    # Check if OAuth is enabled
    oauth_enabled = os.getenv("OAUTH_ENABLED", "false").lower() == "true"
    if not oauth_enabled:
        st.info("OAuth authentication is not enabled on this server.")
        return

    # Get linked accounts
    try:
        linked_accounts = asyncio.run(get_linked_oauth_accounts(current_username))
        linked_providers = {acc["provider"]: acc for acc in linked_accounts}

        # Display all available providers
        for provider_key, provider_info in OAUTH_PROVIDERS.items():
            if not provider_info["enabled"]:
                continue  # Skip disabled providers

            provider_name = provider_info["name"]
            provider_icon = provider_info["icon"]
            is_linked = provider_key in linked_providers

            # Create provider card
            with st.container():
                col1, col2 = st.columns([3, 1])

                with col1:
                    status_icon = "✅" if is_linked else "⭕"
                    st.markdown(
                        f"**{provider_icon} {provider_name}** {status_icon}",
                        help=f"Status: {'Linked' if is_linked else 'Not linked'}",
                    )

                    if is_linked:
                        account = linked_providers[provider_key]
                        linked_email = account.get("profile_data", {}).get("email", "N/A")
                        linked_at = account.get("created_at", "N/A")
                        st.caption(f"Email: {linked_email}")
                        st.caption(f"Linked: {linked_at[:10] if linked_at != 'N/A' else 'N/A'}")

                with col2:
                    if is_linked:
                        # Unlink button
                        unlink_key = f"unlink_{provider_key}"
                        if st.button(
                            "🔓 Unlink",
                            key=unlink_key,
                            use_container_width=True,
                            type="secondary",
                        ):
                            # Show confirmation dialog
                            st.session_state[f"confirm_unlink_{provider_key}"] = True
                            st.rerun()

                        # Handle confirmation
                        if st.session_state.get(f"confirm_unlink_{provider_key}", False):
                            st.warning(
                                f"⚠️ Are you sure you want to unlink your {provider_name} account?"
                            )

                            col_yes, col_no = st.columns(2)
                            with col_yes:
                                if st.button(
                                    "Yes, Unlink",
                                    key=f"confirm_yes_{provider_key}",
                                    type="primary",
                                ):
                                    try:
                                        account = linked_providers[provider_key]
                                        success = asyncio.run(unlink_oauth_account(account["id"]))

                                        if success:
                                            st.success(
                                                f"✅ {provider_name} account unlinked successfully"
                                            )
                                            logger.info(
                                                "OAuth account unlinked",
                                                username=current_username,
                                                provider=provider_key,
                                            )
                                            st.session_state.pop(
                                                f"confirm_unlink_{provider_key}", None
                                            )
                                            st.rerun()
                                        else:
                                            st.error("Failed to unlink account")

                                    except Exception as e:
                                        logger.error(
                                            "Failed to unlink OAuth account",
                                            username=current_username,
                                            provider=provider_key,
                                            error=str(e),
                                        )
                                        st.error("An error occurred. Please try again.")

                            with col_no:
                                if st.button("Cancel", key=f"confirm_no_{provider_key}"):
                                    st.session_state.pop(f"confirm_unlink_{provider_key}", None)
                                    st.rerun()

                    else:
                        # Link button
                        link_key = f"link_{provider_key}"
                        if st.button(
                            "🔗 Link",
                            key=link_key,
                            use_container_width=True,
                            type="primary",
                        ):
                            # Initiate OAuth flow for linking
                            st.info(
                                f"Linking {provider_name} account...\n\n"
                                "You will be redirected to sign in with your "
                                f"{provider_name} account."
                            )

                            # Generate OAuth authorization URL
                            try:
                                from src.auth.oauth_handler import initiate_oauth_flow

                                auth_url, state = asyncio.run(initiate_oauth_flow(provider_key))

                                # Store state in session for verification
                                st.session_state[f"oauth_link_state_{provider_key}"] = state
                                st.session_state["oauth_linking_mode"] = True

                                # Redirect to OAuth provider
                                st.markdown(
                                    f'<meta http-equiv="refresh" content="0; url={auth_url}">',
                                    unsafe_allow_html=True,
                                )

                                logger.info(
                                    "OAuth linking initiated",
                                    username=current_username,
                                    provider=provider_key,
                                )

                            except Exception as e:
                                logger.error(
                                    "Failed to initiate OAuth linking",
                                    username=current_username,
                                    provider=provider_key,
                                    error=str(e),
                                )
                                st.error("Failed to start linking process. Please try again.")

                st.markdown("---")

        # Summary
        linked_count = len(linked_accounts)
        available_count = sum(1 for p in OAUTH_PROVIDERS.values() if p["enabled"])

        st.info(
            f"ℹ️ **Connected Accounts**: {linked_count} of {available_count} available providers\n\n"
            "Linking multiple providers gives you more sign-in options."
        )

        # Security notice
        with st.expander("🔒 Security Information"):
            st.markdown(
                """
                **Why link OAuth accounts?**
                - Sign in with your preferred provider (Google, GitHub, Microsoft, Apple)
                - No need to remember additional passwords
                - Two-factor authentication from your OAuth provider

                **Security Notes:**
                - We only access basic profile information (name, email)
                - You can unlink accounts at any time
                - Unlinking an account won't delete your Base Agent account
                - We encrypt all OAuth tokens before storing them
                """
            )

    except Exception as e:
        logger.error(
            "Failed to render OAuth account management", username=current_username, error=str(e)
        )
        st.error("Failed to load OAuth account information. Please try again.")


def render_oauth_linking_callback_handler() -> None:
    """
    Handle OAuth callback when user is linking an account.

    This should be called early in the app flow to check for OAuth callbacks.
    """
    # Check if we're in OAuth linking mode
    if not st.session_state.get("oauth_linking_mode", False):
        return

    # Check for OAuth callback parameters
    query_params = st.query_params
    code = query_params.get("code")
    state = query_params.get("state")

    if not code:
        return  # Not an OAuth callback

    # Determine which provider based on state
    provider = None
    for provider_key in OAUTH_PROVIDERS:
        stored_state = st.session_state.get(f"oauth_link_state_{provider_key}")
        if stored_state and stored_state == state:
            provider = provider_key
            break

    if not provider:
        st.error("OAuth linking failed: Invalid state parameter")
        logger.error("OAuth linking failed: Invalid state")
        st.session_state.pop("oauth_linking_mode", None)
        return

    # Complete OAuth flow and link account
    try:
        from src.auth.oauth_handler import complete_oauth_flow

        result = asyncio.run(complete_oauth_flow(provider, code, state))

        # Account should now be linked
        st.success(f"✅ {get_provider_display_name(provider)} account linked successfully!")
        logger.info(
            "OAuth account linked via profile",
            provider=provider,
            username=st.session_state.get("username"),
        )

        # Clean up session state
        st.session_state.pop("oauth_linking_mode", None)
        st.session_state.pop(f"oauth_link_state_{provider}", None)

        # Clear query params and reload
        st.query_params.clear()
        st.rerun()

    except Exception as e:
        logger.error("Failed to complete OAuth linking", provider=provider, error=str(e))
        st.error(f"Failed to link {get_provider_display_name(provider)} account: {e!s}")
        st.session_state.pop("oauth_linking_mode", None)
