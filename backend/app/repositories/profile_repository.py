from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import SkillLevel
from app.models.user_profile import UserProfile


class ProfileRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_user_id(self, user_id: UUID) -> UserProfile | None:
        statement = (
            select(UserProfile)
            .options(selectinload(UserProfile.sport))
            .where(UserProfile.user_id == user_id)
        )
        return self.db.scalar(statement)

    def create(
        self,
        *,
        user_id: UUID,
        sport_id: UUID,
        height_cm: Decimal | None,
        weight_kg: Decimal | None,
        skill_level: SkillLevel,
        injury_notes: str | None,
    ) -> UserProfile:
        profile = UserProfile(
            user_id=user_id,
            sport_id=sport_id,
            height_cm=height_cm,
            weight_kg=weight_kg,
            skill_level=skill_level,
            injury_notes=injury_notes,
        )
        self.db.add(profile)
        self.db.flush()
        self.db.refresh(profile)
        return profile

    def update(
        self,
        profile: UserProfile,
        *,
        sport_id: UUID,
        height_cm: Decimal | None,
        weight_kg: Decimal | None,
        skill_level: SkillLevel,
        injury_notes: str | None,
    ) -> UserProfile:
        profile.sport_id = sport_id
        profile.height_cm = height_cm
        profile.weight_kg = weight_kg
        profile.skill_level = skill_level
        profile.injury_notes = injury_notes
        self.db.flush()
        self.db.refresh(profile)
        return profile
