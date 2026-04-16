from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthResponse, AuthUserResponse, LoginRequest, RegisterRequest
from app.schemas.user import CurrentUserResponse
from app.utils.normalization import normalize_email


@dataclass
class AuthService:
    db: Session
    users: UserRepository

    def register(self, payload: RegisterRequest) -> AuthResponse:
        email = normalize_email(payload.email)
        existing_user = self.users.get_by_email(email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )

        user = self.users.create(
            full_name=payload.full_name.strip(),
            email=email,
            password_hash=hash_password(payload.password),
        )
        self.db.commit()
        self.db.refresh(user)
        return self._build_auth_response(user)

    def login(self, payload: LoginRequest) -> AuthResponse:
        email = normalize_email(payload.email)
        user = self.users.get_by_email(email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return self._build_auth_response(user)

    def get_current_user_response(self, user_id: UUID) -> CurrentUserResponse:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account was not found.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return CurrentUserResponse(**self._build_user_payload(user))

    def _build_auth_response(self, user) -> AuthResponse:
        access_token, expires_at = create_access_token(
            subject=str(user.id),
            email=user.email,
        )
        expires_in = max(
            int((expires_at - datetime.now(UTC)).total_seconds()),
            0,
        )
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            user=AuthUserResponse(**self._build_user_payload(user)),
        )

    @staticmethod
    def _build_user_payload(user) -> dict[str, object]:
        return {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "created_at": user.created_at,
            "has_profile": user.profile is not None,
        }
