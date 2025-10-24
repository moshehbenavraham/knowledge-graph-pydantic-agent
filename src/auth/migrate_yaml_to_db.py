"""
Migration script to move users from YAML config to database.

Reads existing auth_config.yaml users and inserts them into
the Supabase auth_users table.
"""

import argparse
import asyncio
import shutil
from datetime import datetime
from pathlib import Path

import yaml

from src.auth.db import assign_role
from src.clients.database import get_supabase_client


def load_yaml_config(config_path: Path) -> dict:
    """Load YAML configuration file."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def backup_yaml_config(config_path: Path) -> Path:
    """Create backup of YAML config."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = config_path.parent / f"{config_path.stem}_backup_{timestamp}.yaml"
    shutil.copy2(config_path, backup_path)
    print(f"✅ Created backup: {backup_path}")
    return backup_path


async def migrate_users(config_path: Path, dry_run: bool = False) -> dict:
    """
    Migrate users from YAML to database.

    Args:
        config_path: Path to auth_config.yaml
        dry_run: If True, only show what would be migrated without making changes

    Returns:
        Migration results dictionary
    """
    # Load YAML config
    config = load_yaml_config(config_path)
    yaml_users = config.get("credentials", {}).get("usernames", {})

    if not yaml_users:
        print("⚠️  No users found in YAML config")
        return {"migrated": 0, "skipped": 0, "errors": 0}

    print(f"\n📋 Found {len(yaml_users)} user(s) in YAML config\n")

    # Migration results
    results = {"migrated": 0, "skipped": 0, "errors": 0, "details": []}

    # Migrate each user
    for username, user_data in yaml_users.items():
        email = user_data.get("email")
        full_name = user_data.get("name", username)
        password_hash = user_data.get("password")  # Already bcrypt hashed

        print(f"🔄 Processing: {username} ({email})")

        if dry_run:
            print(f"   [DRY RUN] Would create user: {username}")
            results["details"].append(
                {"username": username, "action": "would_create", "status": "dry_run"}
            )
            continue

        try:
            # Check if user already exists
            client = get_supabase_client()
            existing = (
                client.table("auth_users").select("id, username").eq("username", username).execute()
            )

            if existing.data:
                print("   ⏭️  User already exists in database, skipping")
                results["skipped"] += 1
                results["details"].append(
                    {"username": username, "action": "skip", "status": "exists"}
                )
                continue

            # Create user in database
            # Note: password_hash is already bcrypt hashed in YAML,
            # so we insert it directly instead of calling hash_password()
            user_data_insert = {
                "username": username,
                "email": email,
                "full_name": full_name,
                "password_hash": password_hash,
                "auth_method": "password",
                "is_active": True,
            }

            response = client.table("auth_users").insert(user_data_insert).execute()

            if not response.data:
                raise Exception("Failed to create user in database")

            created_user = response.data[0]
            user_id = created_user["id"]

            # Assign default role (admin for 'admin' username, user for others)
            default_role = "admin" if username == "admin" else "user"
            await assign_role(user_id, default_role)

            print(f"   ✅ Created user with role '{default_role}'")
            results["migrated"] += 1
            results["details"].append(
                {
                    "username": username,
                    "action": "create",
                    "status": "success",
                    "role": default_role,
                }
            )

        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["errors"] += 1
            results["details"].append(
                {"username": username, "action": "create", "status": "error", "error": str(e)}
            )

    return results


async def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description="Migrate users from YAML config to database")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/auth_config.yaml"),
        help="Path to auth_config.yaml (default: config/auth_config.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode: show what would be migrated without making changes",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup of YAML config",
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("🔄 YAML to Database User Migration")
    print("=" * 60)

    if not args.config.exists():
        print(f"\n❌ Error: Config file not found: {args.config}")
        return 1

    # Create backup (unless dry run or --no-backup)
    if not args.dry_run and not args.no_backup:
        backup_yaml_config(args.config)

    # Run migration
    results = await migrate_users(args.config, dry_run=args.dry_run)

    # Print summary
    print("\n" + "=" * 60)
    print("📊 Migration Summary")
    print("=" * 60)
    print(f"✅ Migrated:  {results['migrated']}")
    print(f"⏭️  Skipped:   {results['skipped']}")
    print(f"❌ Errors:    {results['errors']}")
    print("=" * 60)

    if args.dry_run:
        print("\n💡 This was a dry run. No changes were made.")
        print("   Run without --dry-run to perform actual migration.\n")
    elif results["migrated"] > 0:
        print("\n✨ Migration complete!")
        print(
            "\n📝 Next steps:"
            "\n   1. Verify users in database: python -m src.auth.db_cli list"
            "\n   2. Update streamlit_auth.py to use database authentication"
            "\n   3. Test login with migrated users"
            "\n   4. Keep YAML backup for rollback if needed\n"
        )

    return 0 if results["errors"] == 0 else 1


if __name__ == "__main__":
    import sys

    exit_code = asyncio.run(main())
    sys.exit(exit_code)
