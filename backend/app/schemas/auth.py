"""Authentication & Registration Data Transfer Objects (DTOs)."""
import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import validate_password_complexity

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,50}$")


class UserRegisterRequest(BaseModel):
    """Registration request payload containing new participant credentials."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Unique username containing letters, numbers, underscores, or hyphens.",
        examples=["sanjana_dev"],
    )
    email: EmailStr = Field(
        ...,
        max_length=255,
        description="Valid email address for participant communications.",
        examples=["sanjana@example.com"],
    )
    password: str = Field(
        ...,
        min_length=10,
        max_length=128,
        description="High-entropy password meeting complexity requirements.",
        examples=["P@ssw0rd123!"],
    )
    full_name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Participant's full name.",
        examples=["Sanjana Sharma"],
    )
    company_name: Optional[str] = Field(
        None,
        max_length=150,
        description="Associated organization or company name.",
        examples=["Converge AI Labs"],
    )
    job_title: Optional[str] = Field(
        None,
        max_length=120,
        description="Professional role or designation.",
        examples=["Lead AI Architect"],
    )
    phone_number: Optional[str] = Field(
        None,
        max_length=50,
        description="Optional contact telephone number.",
        examples=["+1-555-0199"],
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        clean = v.strip()
        if not USERNAME_REGEX.match(clean):
            raise ValueError(
                "Username must be 3-50 characters and contain only letters, numbers, "
                "underscores, or hyphens."
            )
        return clean

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("full_name", "company_name", "job_title", "phone_number")
    @classmethod
    def trim_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            return clean if clean else None
        return None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        validate_password_complexity(v)
        return v


class UserRegisterResponse(BaseModel):
    """Registration response returning public identity attributes without sensitive data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    full_name: str
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    is_active: bool
    is_admin: bool = False
    is_organizer: bool = False
    created_at: datetime


class UserLoginRequest(BaseModel):
    """Login request payload supporting username or email identification."""

    identifier: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Registered username or email address.",
        examples=["sanjana_dev", "sanjana@example.com"],
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Account password.",
        examples=["P@ssw0rd123!"],
    )

    @field_validator("identifier")
    @classmethod
    def trim_identifier(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Identifier cannot be empty.")
        return clean


class UserLoginResponse(BaseModel):
    """Authenticated response contract delivering verified identity and session metadata."""

    status: str = Field(
        default="authenticated",
        description="Status flag indicating successful session issuance.",
    )
    user_id: UUID = Field(
        ...,
        description="Unique identifier of verified user.",
    )
    username: str = Field(
        ...,
        description="Canonical username of verified user.",
    )
    email: EmailStr = Field(
        ...,
        description="Registered participant email address.",
    )
    expires_at: datetime = Field(
        ...,
        description="Session expiration timestamp.",
    )


class UserIdentityResponse(BaseModel):
    """Current authenticated user public identity attributes."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    full_name: str
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    is_active: bool
    is_admin: bool = False
    is_organizer: bool = False


class UserLogoutResponse(BaseModel):
    """Response contract for session revocation."""

    status: str = Field(
        default="logged_out",
        description="Status indicating session has been revoked and cleared.",
    )
    detail: str = Field(
        default="Session revoked successfully.",
        description="Human-readable confirmation message.",
    )


class SessionRotateResponse(BaseModel):
    """Response contract for session credential rotation."""

    status: str = Field(
        default="session_rotated",
        description="Status confirming new session issuance and prior credential revocation.",
    )
    expires_at: datetime = Field(
        ...,
        description="New session expiration timestamp.",
    )


class ErrorResponse(BaseModel):
    """Standardized API error response format."""

    detail: str
    error_code: Optional[str] = None
