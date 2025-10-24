"""Tests for password hashing functionality."""

import pytest

from src.auth.hash_password import hash_password, verify_password


def test_hash_password_generates_different_hashes():
    """Test that hashing the same password twice generates different hashes (salting)."""
    password = "test_password_123"
    hash1 = hash_password(password)
    hash2 = hash_password(password)

    assert hash1 != hash2  # Different salts should produce different hashes
    assert hash1.startswith("$2b$")  # Bcrypt format
    assert hash2.startswith("$2b$")


def test_hash_password_with_custom_rounds():
    """Test password hashing with custom bcrypt rounds."""
    password = "test_password_123"
    rounds = 10

    hashed = hash_password(password, rounds=rounds)

    assert hashed.startswith(f"$2b${rounds:02d}$")  # Verify rounds in hash


def test_verify_password_correct():
    """Test password verification with correct password."""
    password = "correct_password"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_incorrect():
    """Test password verification with incorrect password."""
    password = "correct_password"
    wrong_password = "wrong_password"
    hashed = hash_password(password)

    assert verify_password(wrong_password, hashed) is False


def test_verify_password_case_sensitive():
    """Test that password verification is case-sensitive."""
    password = "Password123"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True
    assert verify_password("password123", hashed) is False
    assert verify_password("PASSWORD123", hashed) is False


def test_hash_password_with_special_characters():
    """Test password hashing with special characters."""
    password = "P@ssw0rd!#$%^&*()"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_hash_password_with_unicode():
    """Test password hashing with unicode characters."""
    password = "パスワード123🔐"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_hash_password_empty_string():
    """Test password hashing with empty string."""
    password = ""
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True
    assert verify_password("a", hashed) is False


def test_verify_password_with_invalid_hash_format():
    """Test password verification with invalid hash format."""
    password = "test_password"
    invalid_hash = "not_a_valid_bcrypt_hash"

    with pytest.raises(ValueError):
        verify_password(password, invalid_hash)
