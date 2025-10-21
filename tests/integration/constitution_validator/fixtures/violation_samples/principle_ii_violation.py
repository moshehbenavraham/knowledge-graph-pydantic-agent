"""
Example of Principle II violation: Direct environment variable access.

VIOLATION: Using os.getenv() instead of centralized configuration
"""

import os


def get_api_key() -> str:
    """
    ✗ VIOLATION: Direct os.getenv() usage

    This violates Principle II: Type-Safe Centralized Configuration
    Should use get_settings().api_key instead
    """
    return os.getenv("API_KEY", "default")


def configure_database():
    """✗ VIOLATION: Multiple direct environment variable accesses."""
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.environ["DB_NAME"]  # Also a violation

    return f"{db_host}:{db_port}/{db_name}"
