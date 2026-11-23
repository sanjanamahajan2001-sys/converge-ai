"""Tests for password security, complexity rules, and bcrypt hashing."""
import pytest
from app.core.security import (
    PasswordComplexityError,
    hash_password,
    validate_password_complexity,
    verify_password,
)


def test_password_complexity_valid():
    """Verify strong passwords meeting all criteria pass validation."""
    strong_passwords = [
        "P@ssw0rd123!",
        "Converge#2026_Secure",
        "Str0ng&ComplexKey!",
        "Aa1!bcdefghij",
    ]
    for pwd in strong_passwords:
        validate_password_complexity(pwd)  # Should not raise


def test_password_complexity_too_short():
    """Verify passwords shorter than 10 characters are rejected."""
    with pytest.raises(PasswordComplexityError, match="at least 10 characters"):
        validate_password_complexity("Aa1!bcde")  # 8 chars


def test_password_complexity_missing_uppercase():
    """Verify passwords without uppercase letters are rejected."""
    with pytest.raises(PasswordComplexityError, match="uppercase"):
        validate_password_complexity("lowercase123!@#")


def test_password_complexity_missing_lowercase():
    """Verify passwords without lowercase letters are rejected."""
    with pytest.raises(PasswordComplexityError, match="lowercase"):
        validate_password_complexity("UPPERCASE123!@#")


def test_password_complexity_missing_digits():
    """Verify passwords without digits are rejected."""
    with pytest.raises(PasswordComplexityError, match="digit"):
        validate_password_complexity("PasswordNoDigits!@#")


def test_password_complexity_missing_special_chars():
    """Verify passwords without special characters are rejected."""
    with pytest.raises(PasswordComplexityError, match="special character"):
        validate_password_complexity("PasswordWithDigits1234")


def test_hash_password_produces_bcrypt_hash():
    """Verify hash_password generates valid bcrypt hash with work factor 12."""
    pwd = "MySecurePassword123!"
    hashed = hash_password(pwd)
    assert hashed.startswith("$2b$12$")
    assert len(hashed) == 60


def test_verify_password_correct():
    """Verify verify_password returns True for matching password and hash."""
    pwd = "MySecurePassword123!"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed) is True


def test_verify_password_incorrect():
    """Verify verify_password returns False for non-matching password."""
    pwd = "MySecurePassword123!"
    hashed = hash_password(pwd)
    assert verify_password("WrongPassword123!", hashed) is False


def test_verify_password_malformed_hash():
    """Verify verify_password handles malformed/empty hashes safely without crashing."""
    assert verify_password("AnyPassword123!", "") is False
    assert verify_password("AnyPassword123!", "not_a_valid_hash") is False
    assert verify_password("", "$2b$12$fakehashfakehashfakehashfakehashfakehashfakehash") is False
