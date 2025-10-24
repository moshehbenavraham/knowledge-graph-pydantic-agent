"""
CLI tool for database user management.

Provides commands for creating, updating, deleting, and listing users
in the Supabase auth_users table.
"""

import argparse
import asyncio

from src.auth.db import (
    assign_role,
    create_user,
    delete_user,
    get_user_by_username,
    get_user_roles,
    get_user_sessions,
    list_users,
    revoke_all_user_sessions,
    revoke_role,
    update_user,
    update_user_password,
)


async def cmd_create(
    username: str,
    email: str,
    full_name: str,
    password: str | None = None,
    role: str = "user",
    active: bool = True,
):
    """Create a new user."""
    try:
        user = await create_user(
            username=username,
            email=email,
            full_name=full_name,
            password=password,
            auth_method="password" if password else "oauth",
            is_active=active,
        )

        # Assign role
        await assign_role(user["id"], role)

        print("\n✅ User created successfully!")
        print(f"   ID:       {user['id']}")
        print(f"   Username: {user['username']}")
        print(f"   Email:    {user['email']}")
        print(f"   Name:     {user['full_name']}")
        print(f"   Role:     {role}")
        print(f"   Active:   {user['is_active']}\n")

    except Exception as e:
        print(f"\n❌ Error creating user: {e}\n")
        return 1

    return 0


async def cmd_list(limit: int = 100, include_deleted: bool = False):
    """List all users."""
    try:
        users = await list_users(limit=limit, include_deleted=include_deleted)

        if not users:
            print("\n⚠️  No users found\n")
            return 0

        print(f"\n📋 Found {len(users)} user(s):\n")
        print(f"{'Username':<20} {'Email':<30} {'Name':<25} {'Active':<8} {'Created':<12}")
        print("-" * 100)

        for user in users:
            username = user.get("username", "")
            email = user.get("email", "")
            name = user.get("full_name", "")
            active = "✓" if user.get("is_active") else "✗"
            created = user.get("created_at", "")[:10] if user.get("created_at") else ""

            print(f"{username:<20} {email:<30} {name:<25} {active:<8} {created:<12}")

        print()

    except Exception as e:
        print(f"\n❌ Error listing users: {e}\n")
        return 1

    return 0


async def cmd_get(username: str):
    """Get detailed user information."""
    try:
        user = await get_user_by_username(username)

        if not user:
            print(f"\n❌ User not found: {username}\n")
            return 1

        # Get roles
        roles = await get_user_roles(user["id"])
        role_names = [r.get("role_name") for r in roles] if roles else []

        # Get active sessions
        sessions = await get_user_sessions(user["id"], active_only=True)

        print("\n👤 User Details:")
        print(f"   ID:           {user['id']}")
        print(f"   Username:     {user['username']}")
        print(f"   Email:        {user['email']}")
        print(f"   Name:         {user['full_name']}")
        print(f"   Auth Method:  {user.get('auth_method', 'N/A')}")
        print(f"   Active:       {user['is_active']}")
        print(f"   Verified:     {user.get('is_email_verified', False)}")
        print(f"   Roles:        {', '.join(role_names) if role_names else 'None'}")
        print(f"   Created:      {user.get('created_at', 'N/A')}")
        print(f"   Last Login:   {user.get('last_login_at', 'Never')}")
        print(f"   Failed Login: {user.get('failed_login_attempts', 0)}")
        print(f"   Locked Until: {user.get('locked_until', 'Not locked')}")
        print(f"   Sessions:     {len(sessions)} active")
        print()

    except Exception as e:
        print(f"\n❌ Error getting user: {e}\n")
        return 1

    return 0


async def cmd_update(
    username: str,
    new_username: str | None = None,
    new_email: str | None = None,
    new_name: str | None = None,
    activate: bool = False,
    deactivate: bool = False,
):
    """Update user information."""
    try:
        # Get existing user
        user = await get_user_by_username(username)
        if not user:
            print(f"\n❌ User not found: {username}\n")
            return 1

        # Prepare updates
        updates = {}
        if new_username:
            updates["username"] = new_username
        if new_email:
            updates["email"] = new_email
        if new_name:
            updates["full_name"] = new_name
        if activate:
            updates["is_active"] = True
        if deactivate:
            updates["is_active"] = False

        if not updates:
            print("\n⚠️  No updates specified\n")
            return 1

        # Update user
        updated = await update_user(user["id"], **updates)

        print("\n✅ User updated successfully!")
        print(f"   Username: {updated['username']}")
        print(f"   Email:    {updated['email']}")
        print(f"   Name:     {updated['full_name']}")
        print(f"   Active:   {updated['is_active']}\n")

    except Exception as e:
        print(f"\n❌ Error updating user: {e}\n")
        return 1

    return 0


async def cmd_update_password(username: str, new_password: str):
    """Update user password."""
    try:
        # Get existing user
        user = await get_user_by_username(username)
        if not user:
            print(f"\n❌ User not found: {username}\n")
            return 1

        # Update password
        await update_user_password(user["id"], new_password)

        print(f"\n✅ Password updated successfully for user: {username}\n")

    except Exception as e:
        print(f"\n❌ Error updating password: {e}\n")
        return 1

    return 0


async def cmd_delete(username: str, permanent: bool = False):
    """Delete user (soft or hard delete)."""
    try:
        # Get existing user
        user = await get_user_by_username(username)
        if not user:
            print(f"\n❌ User not found: {username}\n")
            return 1

        # Confirm deletion
        delete_type = "PERMANENTLY" if permanent else "soft"
        confirm = input(
            f"\n⚠️  Are you sure you want to {delete_type} delete '{username}'? (yes/no): "
        )
        if confirm.lower() != "yes":
            print("\n❌ Deletion cancelled\n")
            return 1

        # Delete user
        await delete_user(user["id"], soft_delete=not permanent)

        print(f"\n✅ User deleted successfully: {username}\n")

    except Exception as e:
        print(f"\n❌ Error deleting user: {e}\n")
        return 1

    return 0


async def cmd_role(username: str, action: str, role_name: str):
    """Assign or revoke a role."""
    try:
        # Get existing user
        user = await get_user_by_username(username)
        if not user:
            print(f"\n❌ User not found: {username}\n")
            return 1

        if action == "assign":
            await assign_role(user["id"], role_name)
            print(f"\n✅ Role '{role_name}' assigned to user: {username}\n")
        elif action == "revoke":
            await revoke_role(user["id"], role_name)
            print(f"\n✅ Role '{role_name}' revoked from user: {username}\n")
        else:
            print(f"\n❌ Invalid action: {action} (use 'assign' or 'revoke')\n")
            return 1

    except Exception as e:
        print(f"\n❌ Error managing role: {e}\n")
        return 1

    return 0


async def cmd_sessions(username: str, revoke: bool = False):
    """List or revoke user sessions."""
    try:
        # Get existing user
        user = await get_user_by_username(username)
        if not user:
            print(f"\n❌ User not found: {username}\n")
            return 1

        if revoke:
            # Revoke all sessions
            count = await revoke_all_user_sessions(user["id"])
            print(f"\n✅ Revoked {count} session(s) for user: {username}\n")
        else:
            # List active sessions
            sessions = await get_user_sessions(user["id"], active_only=True)

            if not sessions:
                print(f"\n⚠️  No active sessions for user: {username}\n")
                return 0

            print(f"\n📋 Active sessions for {username} ({len(sessions)}):\n")
            print(f"{'Created':<20} {'Last Activity':<20} {'IP Address':<20} {'Type':<10}")
            print("-" * 75)

            for session in sessions:
                created = session.get("created_at", "")[:19] if session.get("created_at") else ""
                last_activity = (
                    session.get("last_activity_at", "")[:19]
                    if session.get("last_activity_at")
                    else ""
                )
                ip = session.get("ip_address", "N/A")
                session_type = session.get("session_type", "N/A")

                print(f"{created:<20} {last_activity:<20} {ip:<20} {session_type:<10}")

            print()

    except Exception as e:
        print(f"\n❌ Error managing sessions: {e}\n")
        return 1

    return 0


async def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Database User Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create user
  python -m src.auth.db_cli create --username john --email john@example.com --name "John Doe" --password "SecurePass!" --role admin

  # List users
  python -m src.auth.db_cli list

  # Get user details
  python -m src.auth.db_cli get --username john

  # Update user
  python -m src.auth.db_cli update --username john --new-email john.doe@example.com

  # Update password
  python -m src.auth.db_cli update-password --username john --new-password "NewPass!"

  # Assign role
  python -m src.auth.db_cli role --username john --action assign --role admin

  # List sessions
  python -m src.auth.db_cli sessions --username john

  # Revoke all sessions
  python -m src.auth.db_cli sessions --username john --revoke

  # Delete user (soft delete)
  python -m src.auth.db_cli delete --username john

  # Delete user (permanent)
  python -m src.auth.db_cli delete --username john --permanent
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new user")
    create_parser.add_argument("--username", required=True, help="Username")
    create_parser.add_argument("--email", required=True, help="Email address")
    create_parser.add_argument("--name", required=True, help="Full name")
    create_parser.add_argument("--password", help="Password (optional for OAuth users)")
    create_parser.add_argument(
        "--role", default="user", choices=["admin", "user", "viewer"], help="Role (default: user)"
    )
    create_parser.add_argument("--inactive", action="store_true", help="Create as inactive")

    # List command
    list_parser = subparsers.add_parser("list", help="List all users")
    list_parser.add_argument("--limit", type=int, default=100, help="Max users to list")
    list_parser.add_argument("--include-deleted", action="store_true", help="Include deleted users")

    # Get command
    get_parser = subparsers.add_parser("get", help="Get user details")
    get_parser.add_argument("--username", required=True, help="Username")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update user information")
    update_parser.add_argument("--username", required=True, help="Username")
    update_parser.add_argument("--new-username", help="New username")
    update_parser.add_argument("--new-email", help="New email")
    update_parser.add_argument("--new-name", help="New full name")
    update_parser.add_argument("--activate", action="store_true", help="Activate user")
    update_parser.add_argument("--deactivate", action="store_true", help="Deactivate user")

    # Update password command
    password_parser = subparsers.add_parser("update-password", help="Update user password")
    password_parser.add_argument("--username", required=True, help="Username")
    password_parser.add_argument("--new-password", required=True, help="New password")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete user")
    delete_parser.add_argument("--username", required=True, help="Username")
    delete_parser.add_argument(
        "--permanent", action="store_true", help="Permanent delete (default: soft delete)"
    )

    # Role command
    role_parser = subparsers.add_parser("role", help="Assign or revoke role")
    role_parser.add_argument("--username", required=True, help="Username")
    role_parser.add_argument("--action", required=True, choices=["assign", "revoke"], help="Action")
    role_parser.add_argument(
        "--role", required=True, choices=["admin", "user", "viewer"], help="Role name"
    )

    # Sessions command
    sessions_parser = subparsers.add_parser("sessions", help="List or revoke sessions")
    sessions_parser.add_argument("--username", required=True, help="Username")
    sessions_parser.add_argument("--revoke", action="store_true", help="Revoke all sessions")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    if args.command == "create":
        return await cmd_create(
            args.username,
            args.email,
            args.name,
            args.password,
            args.role,
            not args.inactive,
        )
    if args.command == "list":
        return await cmd_list(args.limit, args.include_deleted)
    if args.command == "get":
        return await cmd_get(args.username)
    if args.command == "update":
        return await cmd_update(
            args.username,
            args.new_username,
            args.new_email,
            args.new_name,
            args.activate,
            args.deactivate,
        )
    if args.command == "update-password":
        return await cmd_update_password(args.username, args.new_password)
    if args.command == "delete":
        return await cmd_delete(args.username, args.permanent)
    if args.command == "role":
        return await cmd_role(args.username, args.action, args.role)
    if args.command == "sessions":
        return await cmd_sessions(args.username, args.revoke)
    print(f"\n❌ Unknown command: {args.command}\n")
    return 1


if __name__ == "__main__":
    import sys

    exit_code = asyncio.run(main())
    sys.exit(exit_code)
