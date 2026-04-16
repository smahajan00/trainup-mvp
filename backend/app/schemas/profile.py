from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.models.enums import SkillLevel
from app.schemas.base import APIBaseModel
from app.utils.normalization import normalize_optional_text


class SportOptionResponse(APIBaseModel):
    id: UUID
    sport_name: str


class ProfileUpsertRequest(APIBaseModel):
    sport_id: UUID
    height_cm: float | None = Field(default=None, gt=0)
    weight_kg: float | None = Field(default=None, gt=0)
    skill_level: SkillLevel
    injury_notes: str | None = Field(default=None, max_length=2000)

    @field_validator("injury_notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)


class ProfileResponse(APIBaseModel):
    id: UUID
    user_id: UUID
    sport_id: UUID
    sport_name: str
    height_cm: float | None
    weight_kg: float | None
    skill_level: SkillLevel
    injury_notes: str | None
    created_at: datetime


class ProfileEnvelopeResponse(APIBaseModel):
    profile: ProfileResponse | None
