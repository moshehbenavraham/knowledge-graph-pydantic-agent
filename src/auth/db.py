"""
Database operations for authentication system.

Provides async functions for user management, session handling,
password reset, OAuth accounts, and role-based permissions.
"""

import secrets
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from src.auth.hash_password import hash_password, verify_password
from src.clients.supabase_client import get_supabase_client

# =====================================================
# USER MANAGEMENT
# =====================================================


async def create_user(
    username: str,
    email: str,
    full_name: str,
    password: str | None = None,
    auth_method: str = "password",
    is_active: bool = True,
    avatar_url: str | None = None,
) -> dict[str, Any]:
    """
    Create a new user in the database.

    Args:
        username: Unique username
        email: Unique email address
        full_name: User's full name
        password: Plain text password (will be hashed). None for OAuth-only users.
        auth_method: 'password', 'oauth', or 'hybrid'
        is_active: Whether user account is active
        avatar_url: Optional profile picture URL

    Returns:
        Created user record (without password_hash)

    Raises:
        Exception: If username/email already exists or database error
    """
    client = get_supabase_client()

    # Hash password if provided
    password_hash = hash_password(password) if password else None

    user_data = {
        "username": username,
        "email": email,
        "full_name": full_name,
        "password_hash": password_hash,
        "auth_method": auth_method,
        "is_active": is_active,
        "avatar_url": avatar_url,
    }

    response = client.table("auth_users").insert(user_data).execute()

    if not response.data:
        raise Exception("Failed to create user")

    # Remove password_hash from response
    user = response.data[0]
    user.pop("password_hash", None)
    return user


async def get_user_by_username(username: str) -> dict[str, Any] | None:
    """
    Get user by username.

    Args:
        username: Username to search for

    Returns:
        User record (without password_hash) or None if not found
    """
    client = get_supabase_client()

    response = (
        client.table("auth_users")
        .select("*")
        .eq("username", username)
        .is_("deleted_at", "null")
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    user = response.data[0]
    user.pop("password_hash", None)
    return user


async def get_user_by_email(email: str) -> dict[str, Any] | None:
    """
    Get user by email.

    Args:
        email: Email address to search for

    Returns:
        User record (without password_hash) or None if not found
    """
    client = get_supabase_client()

    response = (
        client.table("auth_users")
        .select("*")
        .eq("email", email)
        .is_("deleted_at", "null")
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    user = response.data[0]
    user.pop("password_hash", None)
    return user


async def get_user_by_id(user_id: UUID | str) -> dict[str, Any] | None:
    """
    Get user by ID.

    Args:
        user_id: User UUID

    Returns:
        User record (without password_hash) or None if not found
    """
    client = get_supabase_client()

    response = (
        client.table("auth_users")
        .select("*")
        .eq("id", str(user_id))
        .is_("deleted_at", "null")
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    user = response.data[0]
    user.pop("password_hash", None)
    return user


async def verify_user_password(username: str, password: str) -> dict[str, Any] | None:
    """
    Verify user credentials and return user if valid.

    Args:
        username: Username
        password: Plain text password

    Returns:
        User record (without password_hash) if credentials valid, None otherwise
    """
    client = get_supabase_client()

    # Get user with password_hash
    response = (
        client.table("auth_users")
        .select("*")
        .eq("username", username)
        .is_("deleted_at", "null")
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    user = response.data[0]
    password_hash = user.get("password_hash")

    if not password_hash:
        return None  # OAuth-only user, no password

    # Verify password
    if not verify_password(password, password_hash):
        return None

    # Update last login
    await update_last_login(user["id"])

    user.pop("password_hash", None)
    return user


async def update_user(
    user_id: UUID | str,
    username: str | None = None,
    email: str | None = None,
    full_name: str | None = None,
    avatar_url: str | None = None,
    is_active: bool | None = None,
) -> dict[str, Any]:
    """
    Update user information.

    Args:
        user_id: User UUID
        username: New username (optional)
        email: New email (optional)
        full_name: New full name (optional)
        avatar_url: New avatar URL (optional)
        is_active: New active status (optional)

    Returns:
        Updated user record (without password_hash)

    Raises:
        Exception: If user not found or database error
    """
    client = get_supabase_client()

    update_data: dict[str, Any] = {}
    if username is not None:
        update_data["username"] = username
    if email is not None:
        update_data["email"] = email
    if full_name is not None:
        update_data["full_name"] = full_name
    if avatar_url is not None:
        update_data["avatar_url"] = avatar_url
    if is_active is not None:
        update_data["is_active"] = is_active

    if not update_data:
        raise ValueError("No fields to update")

    response = client.table("auth_users").update(update_data).eq("id", str(user_id)).execute()

    if not response.data:
        raise Exception("Failed to update user")

    user = response.data[0]
    user.pop("password_hash", None)
    return user


async def update_user_password(user_id: UUID | str, new_password: str) -> bool:
    """
    Update user password.

    Args:
        user_id: User UUID
        new_password: New plain text password

    Returns:
        True if successful

    Raises:
        Exception: If user not found or database error
    """
    client = get_supabase_client()

    password_hash = hash_password(new_password)

    response = (
        client.table("auth_users")
        .update({"password_hash": password_hash, "failed_login_attempts": 0, "locked_until": None})
        .eq("id", str(user_id))
        .execute()
    )

    if not response.data:
        raise Exception("Failed to update password")

    return True


async def delete_user(user_id: UUID | str, soft_delete: bool = True) -> bool:
    """
    Delete user (soft or hard delete).

    Args:
        user_id: User UUID
        soft_delete: If True, set deleted_at timestamp. If False, permanently delete.

    Returns:
        True if successful

    Raises:
        Exception: If user not found or database error
    """
    client = get_supabase_client()

    if soft_delete:
        response = (
            client.table("auth_users")
            .update({"deleted_at": datetime.utcnow().isoformat()})
            .eq("id", str(user_id))
            .execute()
        )
    else:
        response = client.table("auth_users").delete().eq("id", str(user_id)).execute()

    return bool(response.data)


async def list_users(
    limit: int = 100, offset: int = 0, include_deleted: bool = False
) -> list[dict[str, Any]]:
    """
    List all users.

    Args:
        limit: Maximum number of users to return
        offset: Offset for pagination
        include_deleted: Include soft-deleted users

    Returns:
        List of user records (without password_hash)
    """
    client = get_supabase_client()

    query = client.table("auth_users").select("*")

    if not include_deleted:
        query = query.is_("deleted_at", "null")

    response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

    users = response.data or []
    for user in users:
        user.pop("password_hash", None)

    return users


async def update_last_login(user_id: UUID | str, ip_address: str | None = None) -> bool:
    """
    Update user's last login timestamp and IP.

    Args:
        user_id: User UUID
        ip_address: Client IP address (optional)

    Returns:
        True if successful
    """
    client = get_supabase_client()

    update_data = {"last_login_at": datetime.utcnow().isoformat()}
    if ip_address:
        update_data["last_login_ip"] = ip_address

    response = client.table("auth_users").update(update_data).eq("id", str(user_id)).execute()

    return bool(response.data)


async def increment_failed_login(username: str) -> int:
    """
    Increment failed login attempts and lock account if needed.

    Args:
        username: Username

    Returns:
        New failed login attempts count

    Raises:
        Exception: If user not found
    """
    client = get_supabase_client()

    # Get current user
    response = (
        client.table("auth_users")
        .select("*")
        .eq("username", username)
        .is_("deleted_at", "null")
        .limit(1)
        .execute()
    )

    if not response.data:
        raise Exception("User not found")

    user = response.data[0]
    new_count = user.get("failed_login_attempts", 0) + 1

    update_data: dict[str, Any] = {"failed_login_attempts": new_count}

    # Lock account after 5 failed attempts for 15 minutes
    if new_count >= 5:
        lockout_until = datetime.utcnow() + timedelta(minutes=15)
        update_data["locked_until"] = lockout_until.isoformat()

    client.table("auth_users").update(update_data).eq("id", user["id"]).execute()

    return new_count


async def reset_failed_login(user_id: UUID | str) -> bool:
    """
    Reset failed login attempts to 0.

    Args:
        user_id: User UUID

    Returns:
        True if successful
    """
    client = get_supabase_client()

    response = (
        client.table("auth_users")
        .update({"failed_login_attempts": 0, "locked_until": None})
        .eq("id", str(user_id))
        .execute()
    )

    return bool(response.data)


# =====================================================
# SESSION MANAGEMENT
# =====================================================


async def create_session(
    user_id: UUID | str,
    expires_in_days: int = 30,
    device_info: str | None = None,
    user_agent: str | None = None,
    ip_address: str | None = None,
    session_type: str = "web",
) -> dict[str, Any]:
    """
    Create a new user session.

    Args:
        user_id: User UUID
        expires_in_days: Session validity in days
        device_info: Device information
        user_agent: User agent string
        ip_address: Client IP address
        session_type: 'web', 'api', 'mobile', or 'desktop'

    Returns:
        Session record with session_token

    Raises:
        Exception: If database error
    """
    client = get_supabase_client()

    # Generate secure session token
    session_token = secrets.token_urlsafe(32)

    session_data = {
        "user_id": str(user_id),
        "session_token": session_token,
        "device_info": device_info,
        "user_agent": user_agent,
        "ip_address": ip_address,
        "session_type": session_type,
        "expires_at": (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat(),
    }

    response = client.table("auth_sessions").insert(session_data).execute()

    if not response.data:
        raise Exception("Failed to create session")

    return response.data[0]


async def get_session(session_token: str) -> dict[str, Any] | None:
    """
    Get active session by token.

    Args:
        session_token: Session token

    Returns:
        Session record or None if not found/expired/revoked
    """
    client = get_supabase_client()

    now = datetime.utcnow().isoformat()

    response = (
        client.table("auth_sessions")
        .select("*")
        .eq("session_token", session_token)
        .is_("revoked_at", "null")
        .gt("expires_at", now)
        .limit(1)
        .execute()
    )

    return response.data[0] if response.data else None


async def update_session_activity(session_token: str) -> bool:
    """
    Update session's last activity timestamp.

    Args:
        session_token: Session token

    Returns:
        True if successful
    """
    client = get_supabase_client()

    response = (
        client.table("auth_sessions")
        .update({"last_activity_at": datetime.utcnow().isoformat()})
        .eq("session_token", session_token)
        .execute()
    )

    return bool(response.data)


async def revoke_session(session_token: str) -> bool:
    """
    Revoke a session (logout).

    Args:
        session_token: Session token

    Returns:
        True if successful
    """
    client = get_supabase_client()

    response = (
        client.table("auth_sessions")
        .update({"revoked_at": datetime.utcnow().isoformat()})
        .eq("session_token", session_token)
        .execute()
    )

    return bool(response.data)


async def revoke_all_user_sessions(user_id: UUID | str) -> int:
    """
    Revoke all sessions for a user.

    Args:
        user_id: User UUID

    Returns:
        Number of sessions revoked
    """
    client = get_supabase_client()

    response = (
        client.table("auth_sessions")
        .update({"revoked_at": datetime.utcnow().isoformat()})
        .eq("user_id", str(user_id))
        .is_("revoked_at", "null")
        .execute()
    )

    return len(response.data) if response.data else 0


async def get_user_sessions(user_id: UUID | str, active_only: bool = True) -> list[dict[str, Any]]:
    """
    Get all sessions for a user.

    Args:
        user_id: User UUID
        active_only: Only return active (non-revoked, non-expired) sessions

    Returns:
        List of session records
    """
    client = get_supabase_client()

    query = client.table("auth_sessions").select("*").eq("user_id", str(user_id))

    if active_only:
        now = datetime.utcnow().isoformat()
        query = query.is_("revoked_at", "null").gt("expires_at", now)

    response = query.order("created_at", desc=True).execute()

    return response.data or []


async def cleanup_expired_sessions() -> int:
    """
    Clean up expired sessions (calls database function).

    Returns:
        Number of sessions deleted
    """
    client = get_supabase_client()

    # Call the database function
    response = client.rpc("cleanup_expired_auth_sessions").execute()

    return response.data if response.data else 0


# =====================================================
# PASSWORD RESET
# =====================================================


async def create_reset_token(
    user_id: UUID | str, expires_in_hours: int = 1, created_ip: str | None = None
) -> str:
    """
    Create a password reset token.

    Args:
        user_id: User UUID
        expires_in_hours: Token validity in hours
        created_ip: Client IP address

    Returns:
        Plain text reset token (send this to user via email)

    Raises:
        Exception: If database error
    """
    client = get_supabase_client()

    # Generate secure token
    token = secrets.token_urlsafe(32)
    token_hash = hash_password(token)

    token_data = {
        "user_id": str(user_id),
        "token": token,
        "token_hash": token_hash,
        "expires_at": (datetime.utcnow() + timedelta(hours=expires_in_hours)).isoformat(),
        "created_ip": created_ip,
    }

    response = client.table("auth_password_reset_tokens").insert(token_data).execute()

    if not response.data:
        raise Exception("Failed to create reset token")

    return token


async def verify_reset_token(token: str) -> dict[str, Any] | None:
    """
    Verify a password reset token is valid.

    Args:
        token: Plain text reset token

    Returns:
        Token record (with user_id) if valid, None otherwise
    """
    client = get_supabase_client()

    now = datetime.utcnow().isoformat()

    # Get all unused, non-expired tokens
    response = (
        client.table("auth_password_reset_tokens")
        .select("*")
        .eq("token", token)
        .is_("used_at", "null")
        .gt("expires_at", now)
        .execute()
    )

    if not response.data:
        return None

    # Verify token hash (additional security layer)
    token_record = response.data[0]
    if not verify_password(token, token_record["token_hash"]):
        return None

    return token_record


async def use_reset_token(token: str, new_password: str, used_ip: str | None = None) -> bool:
    """
    Use a reset token to change password.

    Args:
        token: Plain text reset token
        new_password: New plain text password
        used_ip: Client IP address

    Returns:
        True if successful

    Raises:
        Exception: If token invalid or database error
    """
    # Verify token
    token_record = await verify_reset_token(token)
    if not token_record:
        raise Exception("Invalid or expired reset token")

    user_id = token_record["user_id"]

    # Update password
    await update_user_password(user_id, new_password)

    # Mark token as used
    client = get_supabase_client()
    client.table("auth_password_reset_tokens").update(
        {"used_at": datetime.utcnow().isoformat(), "used_ip": used_ip}
    ).eq("id", token_record["id"]).execute()

    return True


async def cleanup_reset_tokens() -> int:
    """
    Clean up expired/used reset tokens (calls database function).

    Returns:
        Number of tokens deleted
    """
    client = get_supabase_client()

    # Call the database function
    response = client.rpc("cleanup_auth_reset_tokens").execute()

    return response.data if response.data else 0


# =====================================================
# OAUTH ACCOUNTS
# =====================================================


async def link_oauth_account(
    user_id: UUID | str,
    provider: str,
    provider_user_id: str,
    access_token: str,
    refresh_token: str | None = None,
    token_expires_at: datetime | None = None,
    profile_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Link an OAuth account to a user.

    Args:
        user_id: User UUID
        provider: 'google', 'github', 'microsoft', or 'apple'
        provider_user_id: User ID from OAuth provider
        access_token: OAuth access token
        refresh_token: OAuth refresh token (optional)
        token_expires_at: Token expiration datetime (optional)
        profile_data: OAuth profile data (email, name, avatar, etc.)

    Returns:
        OAuth account record

    Raises:
        Exception: If database error or account already linked
    """
    client = get_supabase_client()

    oauth_data = {
        "user_id": str(user_id),
        "provider": provider,
        "provider_user_id": provider_user_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_expires_at": token_expires_at.isoformat() if token_expires_at else None,
        "profile_data": profile_data or {},
    }

    response = client.table("auth_oauth_accounts").insert(oauth_data).execute()

    if not response.data:
        raise Exception("Failed to link OAuth account")

    return response.data[0]


async def get_oauth_account(provider: str, provider_user_id: str) -> dict[str, Any] | None:
    """
    Get OAuth account by provider and provider user ID.

    Args:
        provider: OAuth provider name
        provider_user_id: User ID from OAuth provider

    Returns:
        OAuth account record or None if not found
    """
    client = get_supabase_client()

    response = (
        client.table("auth_oauth_accounts")
        .select("*")
        .eq("provider", provider)
        .eq("provider_user_id", provider_user_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )

    return response.data[0] if response.data else None


async def get_user_oauth_accounts(user_id: UUID | str) -> list[dict[str, Any]]:
    """
    Get all OAuth accounts for a user.

    Args:
        user_id: User UUID

    Returns:
        List of OAuth account records
    """
    client = get_supabase_client()

    response = (
        client.table("auth_oauth_accounts")
        .select("*")
        .eq("user_id", str(user_id))
        .eq("is_active", True)
        .execute()
    )

    return response.data or []


async def update_oauth_tokens(
    oauth_account_id: UUID | str,
    access_token: str,
    refresh_token: str | None = None,
    token_expires_at: datetime | None = None,
) -> dict[str, Any]:
    """
    Update OAuth account tokens.

    Args:
        oauth_account_id: OAuth account UUID
        access_token: New access token
        refresh_token: New refresh token (optional)
        token_expires_at: New expiration datetime (optional)

    Returns:
        Updated OAuth account record

    Raises:
        Exception: If database error
    """
    client = get_supabase_client()

    update_data: dict[str, Any] = {
        "access_token": access_token,
        "last_used_at": datetime.utcnow().isoformat(),
    }
    if refresh_token:
        update_data["refresh_token"] = refresh_token
    if token_expires_at:
        update_data["token_expires_at"] = token_expires_at.isoformat()

    response = (
        client.table("auth_oauth_accounts")
        .update(update_data)
        .eq("id", str(oauth_account_id))
        .execute()
    )

    if not response.data:
        raise Exception("Failed to update OAuth tokens")

    return response.data[0]


async def unlink_oauth_account(oauth_account_id: UUID | str) -> bool:
    """
    Unlink an OAuth account.

    Args:
        oauth_account_id: OAuth account UUID

    Returns:
        True if successful
    """
    client = get_supabase_client()

    response = (
        client.table("auth_oauth_accounts")
        .update({"is_active": False})
        .eq("id", str(oauth_account_id))
        .execute()
    )

    return bool(response.data)


# =====================================================
# ROLES & PERMISSIONS
# =====================================================


async def assign_role(
    user_id: UUID | str, role_name: str, assigned_by: UUID | str | None = None
) -> dict[str, Any]:
    """
    Assign a role to a user.

    Args:
        user_id: User UUID
        role_name: Role name ('admin', 'user', 'viewer')
        assigned_by: UUID of user who assigned the role (optional)

    Returns:
        User role record

    Raises:
        Exception: If role not found or database error
    """
    client = get_supabase_client()

    # Get role ID
    role_response = (
        client.table("auth_roles")
        .select("id")
        .eq("role_name", role_name)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )

    if not role_response.data:
        raise Exception(f"Role '{role_name}' not found")

    role_id = role_response.data[0]["id"]

    user_role_data = {
        "user_id": str(user_id),
        "role_id": role_id,
        "assigned_by": str(assigned_by) if assigned_by else None,
    }

    response = client.table("auth_user_roles").insert(user_role_data).execute()

    if not response.data:
        raise Exception("Failed to assign role")

    return response.data[0]


async def revoke_role(user_id: UUID | str, role_name: str) -> bool:
    """
    Revoke a role from a user.

    Args:
        user_id: User UUID
        role_name: Role name

    Returns:
        True if successful

    Raises:
        Exception: If role not found or database error
    """
    client = get_supabase_client()

    # Get role ID
    role_response = (
        client.table("auth_roles").select("id").eq("role_name", role_name).limit(1).execute()
    )

    if not role_response.data:
        raise Exception(f"Role '{role_name}' not found")

    role_id = role_response.data[0]["id"]

    response = (
        client.table("auth_user_roles")
        .delete()
        .eq("user_id", str(user_id))
        .eq("role_id", role_id)
        .execute()
    )

    return bool(response.data)


async def get_user_roles(user_id: UUID | str) -> list[dict[str, Any]]:
    """
    Get all roles assigned to a user (with permissions).

    Args:
        user_id: User UUID

    Returns:
        List of role records with permissions
    """
    client = get_supabase_client()

    # Call the database function
    response = client.rpc("get_user_with_roles", {"p_user_id": str(user_id)}).execute()

    if not response.data:
        return []

    user_data = response.data[0]
    return user_data.get("roles", [])


async def check_permission(user_id: UUID | str, permission: str) -> bool:
    """
    Check if user has a specific permission.

    Args:
        user_id: User UUID
        permission: Permission string (e.g., 'read', 'write', 'delete')

    Returns:
        True if user has permission
    """
    roles = await get_user_roles(user_id)

    for role in roles:
        permissions = role.get("permissions", [])
        # Check for wildcard or specific permission
        if "*" in permissions or permission in permissions:
            return True

    return False
