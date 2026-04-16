from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.schemas.base import APIBaseModel


class UserResponse(APIBaseModel):
    id: UUID
    full_name: str
    email: str
    created_at: datetime
    has_profile: bool


class CurrentUserResponse(UserResponse):
    pass
