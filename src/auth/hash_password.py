"""Password hashing utility for authentication system.

This module provides utilities for generating bcrypt password hashes.
"""

import bcrypt
import structlog

logger = structlog.get_logger(__name__)


def hash_password(password: str, rounds: int = 12) -> str:
    """Generate bcrypt hash for a password.

    Args:
        password: Plain text password to hash
        rounds: Number of bcrypt rounds (default: 12, higher = more secure but slower)

    Returns:
        Bcrypt hash string (includes salt)

    Example:
        >>> hash_password("mypassword")
        '$2b$12$...'
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=rounds)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash.

    Args:
        password: Plain text password to verify
        hashed: Bcrypt hash to verify against

    Returns:
        True if password matches hash, False otherwise

    Example:
        >>> hashed = hash_password("mypassword")
        >>> verify_password("mypassword", hashed)
        True
        >>> verify_password("wrongpassword", hashed)
        False
    """
    password_bytes = password.encode("utf-8")
    hashed_bytes = hashed.encode("utf-8")
    result = bcrypt.checkpw(password_bytes, hashed_bytes)
    logger.info("Password verification", success=result)
    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.auth.hash_password <password>")
        sys.exit(1)

    password = sys.argv[1]
    hashed = hash_password(password)
    print(f"Hashed password: {hashed}")
