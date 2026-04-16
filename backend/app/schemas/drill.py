from __future__ import annotations

from typing import Any
from uuid import UUID

from app.models.enums import SkillLevel
from app.schemas.base import APIBaseModel


class DrillListItemResponse(APIBaseModel):
    id: UUID
    sport_id: UUID
    drill_name: str
    description: str | None
    difficulty_level: SkillLevel
    target_metrics: dict[str, Any]


class DrillDetailResponse(APIBaseModel):
    id: UUID
    sport_id: UUID
    sport_name: str
    drill_name: str
    description: str | None
    difficulty_level: SkillLevel
    target_metrics: dict[str, Any]
    reference_payload: dict[str, Any]
    coaching_rules: dict[str, Any]
