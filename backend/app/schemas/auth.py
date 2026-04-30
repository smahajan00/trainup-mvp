from __future__ import annotations

from pydantic import EmailStr, Field, TypeAdapter, field_validator

from app.schemas.base import APIBaseModel
from app.schemas.user import UserResponse
from app.utils.normalization import normalize_email

DEMO_ATHLETE_EMAIL = "demo.athlete@trainup.local"
EMAIL_ADAPTER = TypeAdapter(EmailStr)


def normalize_and_validate_email(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Email is required.")
    normalized = normalize_email(value)
    if normalized == DEMO_ATHLETE_EMAIL:
        return normalized
    return str(EMAIL_ADAPTER.validate_python(normalized))


class RegisterRequest(APIBaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Full name is required.")
        return normalized

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email_value(cls, value: object) -> str:
        return normalize_and_validate_email(value)


class LoginRequest(APIBaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email_value(cls, value: object) -> str:
        return normalize_and_validate_email(value)


class TokenResponse(APIBaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthUserResponse(UserResponse):
    pass


class AuthResponse(TokenResponse):
    user: AuthUserResponse
