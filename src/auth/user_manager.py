"""User management module for authentication system.

This module provides utilities for managing users in the auth_config.yaml file.
"""

from pathlib import Path

import structlog
import yaml

from src.auth.hash_password import hash_password

logger = structlog.get_logger(__name__)


class UserManager:
    """Manages users in the authentication configuration file."""

    def __init__(self, config_path: str = "config/auth_config.yaml"):
        """Initialize UserManager.

        Args:
            config_path: Path to auth configuration file
        """
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

    def _load_config(self) -> dict:
        """Load configuration from YAML file.

        Returns:
            Configuration dictionary
        """
        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def _save_config(self, config: dict) -> None:
        """Save configuration to YAML file.

        Args:
            config: Configuration dictionary to save
        """
        with open(self.config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    def create_user(
        self, username: str, email: str, name: str, password: str, rounds: int = 12
    ) -> None:
        """Create a new user.

        Args:
            username: Unique username
            email: User email address
            name: User's full name
            password: Plain text password (will be hashed)
            rounds: Bcrypt rounds for hashing (default: 12)

        Raises:
            ValueError: If username already exists
        """
        logger.info(
            "Creating user",
            username=username,
            email=email,
            name=name,
            has_password=bool(password),
            rounds=rounds,
        )
        config = self._load_config()

        # Check if user already exists
        if username in config["credentials"]["usernames"]:
            raise ValueError(f"User '{username}' already exists")

        # Hash password
        hashed_password = hash_password(password, rounds=rounds)

        # Add user to config
        config["credentials"]["usernames"][username] = {
            "email": email,
            "name": name,
            "password": hashed_password,
        }

        # Save config
        self._save_config(config)
        print(f"✅ User '{username}' created successfully")

    def update_password(self, username: str, new_password: str, rounds: int = 12) -> None:
        """Update user's password.

        Args:
            username: Username to update
            new_password: New plain text password (will be hashed)
            rounds: Bcrypt rounds for hashing (default: 12)

        Raises:
            ValueError: If user doesn't exist
        """
        logger.info(
            "Updating password", username=username, has_password=bool(new_password), rounds=rounds
        )
        config = self._load_config()

        # Check if user exists
        if username not in config["credentials"]["usernames"]:
            raise ValueError(f"User '{username}' not found")

        # Hash new password
        hashed_password = hash_password(new_password, rounds=rounds)

        # Update password
        config["credentials"]["usernames"][username]["password"] = hashed_password

        # Save config
        self._save_config(config)
        print(f"✅ Password updated for user '{username}'")

    def delete_user(self, username: str) -> None:
        """Delete a user.

        Args:
            username: Username to delete

        Raises:
            ValueError: If user doesn't exist
        """
        logger.info("Deleting user", username=username)
        config = self._load_config()

        # Check if user exists
        if username not in config["credentials"]["usernames"]:
            raise ValueError(f"User '{username}' not found")

        # Delete user
        del config["credentials"]["usernames"][username]

        # Save config
        self._save_config(config)
        print(f"✅ User '{username}' deleted successfully")

    def list_users(self) -> list[dict[str, str]]:
        """List all users.

        Returns:
            List of user dictionaries (username, email, name)
        """
        logger.debug("Listing all users")
        config = self._load_config()
        users = []

        for username, user_data in config["credentials"]["usernames"].items():
            users.append(
                {"username": username, "email": user_data["email"], "name": user_data["name"]}
            )

        return users

    def get_user(self, username: str) -> dict[str, str] | None:
        """Get user information.

        Args:
            username: Username to retrieve

        Returns:
            User dictionary (username, email, name) or None if not found
        """
        logger.debug("Getting user", username=username)
        config = self._load_config()

        if username not in config["credentials"]["usernames"]:
            return None

        user_data = config["credentials"]["usernames"][username]
        return {"username": username, "email": user_data["email"], "name": user_data["name"]}


def main():
    """CLI interface for user management."""
    logger.info("Starting user management CLI")
    import argparse

    parser = argparse.ArgumentParser(description="Manage authentication users")
    parser.add_argument(
        "command",
        choices=["create", "update-password", "delete", "list", "get"],
        help="Command to execute",
    )
    parser.add_argument("--username", help="Username")
    parser.add_argument("--email", help="Email address")
    parser.add_argument("--name", help="Full name")
    parser.add_argument("--password", help="Password")
    parser.add_argument("--config", default="config/auth_config.yaml", help="Path to config file")

    args = parser.parse_args()

    manager = UserManager(config_path=args.config)

    if args.command == "create":
        if not all([args.username, args.email, args.name, args.password]):
            print("Error: --username, --email, --name, and --password are required")
            return
        manager.create_user(args.username, args.email, args.name, args.password)

    elif args.command == "update-password":
        if not all([args.username, args.password]):
            print("Error: --username and --password are required")
            return
        manager.update_password(args.username, args.password)

    elif args.command == "delete":
        if not args.username:
            print("Error: --username is required")
            return
        manager.delete_user(args.username)

    elif args.command == "list":
        users = manager.list_users()
        print("\nRegistered Users:")
        print("-" * 60)
        for user in users:
            print(f"Username: {user['username']}")
            print(f"  Email: {user['email']}")
            print(f"  Name: {user['name']}")
            print()

    elif args.command == "get":
        if not args.username:
            print("Error: --username is required")
            return
        user = manager.get_user(args.username)
        if user:
            print(f"\nUser: {user['username']}")
            print(f"Email: {user['email']}")
            print(f"Name: {user['name']}")
        else:
            print(f"User '{args.username}' not found")


if __name__ == "__main__":
    main()
