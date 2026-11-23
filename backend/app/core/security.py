"""Security & Cryptographic Foundation for Converge AI.

Provides password hashing, verification, and complexity checks adhering to
OWASP standards using bcrypt with work factor 12.
"""
import re
import bcrypt

PASSWORD_MIN_LENGTH = 10
PASSWORD_SPECIAL_CHARS = r"""!@#$%^&*()_+\-=\[\]{}|;:,.<>?/~`"""
COMPLEXITY_PATTERN = re.compile(
    rf"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[{PASSWORD_SPECIAL_CHARS}]).{{{PASSWORD_MIN_LENGTH},}}$"
)


class PasswordComplexityError(ValueError):
    """Raised when password fails complexity requirements."""
    pass


def validate_password_complexity(password: str) -> None:
    """Validate password against OWASP minimum complexity requirements.

    Requirements:
    - Minimum 10 characters in length.
    - At least one lowercase ASCII character.
    - At least one uppercase ASCII character.
    - At least one numerical digit.
    - At least one special symbol.
    """
    if not password or len(password) < PASSWORD_MIN_LENGTH:
        raise PasswordComplexityError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters long."
        )

    if not COMPLEXITY_PATTERN.match(password):
        raise PasswordComplexityError(
            "Password must contain at least one uppercase letter, one lowercase letter, "
            "one digit, and one special character."
        )


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with salt rounds=12.

    Validates complexity requirements before hashing.
    """
    validate_password_complexity(password)
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash in constant time.

    Returns False if inputs are malformed or verification fails.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# Static valid bcrypt hash used to equalize computation time (~120ms) for nonexistent accounts (rounds=12)
DUMMY_BCRYPT_HASH = "$2b$12$XJ.AJwutjEI83zajWldTmOikiHAV5k6flKRdrHJbOzsl4whuLeUMe"


def verify_dummy_password(plain_password: str) -> bool:
    """Execute dummy password verification against static hash to equalize response times."""
    return verify_password(plain_password, DUMMY_BCRYPT_HASH)
