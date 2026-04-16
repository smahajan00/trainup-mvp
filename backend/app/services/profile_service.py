from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_profile import UserProfile
from app.repositories.profile_repository import ProfileRepository
from app.repositories.sport_repository import SportRepository
from app.schemas.profile import (
    ProfileEnvelopeResponse,
    ProfileResponse,
    ProfileUpsertRequest,
    SportOptionResponse,
)


@dataclass
class ProfileService:
    db: Session
    profiles: ProfileRepository
    sports: SportRepository

    def get_profile(self, user: User) -> ProfileEnvelopeResponse:
        profile = self.profiles.get_by_user_id(user.id)
        return ProfileEnvelopeResponse(
            profile=self._to_profile_response(profile) if profile is not None else None
        )

    def upsert_profile(self, user: User, payload: ProfileUpsertRequest) -> ProfileResponse:
        sport = self.sports.get_by_id(payload.sport_id)
        if sport is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected sport was not found.",
            )

        profile = self.profiles.get_by_user_id(user.id)
        height_cm = self._to_decimal(payload.height_cm)
        weight_kg = self._to_decimal(payload.weight_kg)

        if profile is None:
            profile = self.profiles.create(
                user_id=user.id,
                sport_id=sport.id,
                height_cm=height_cm,
                weight_kg=weight_kg,
                skill_level=payload.skill_level,
                injury_notes=payload.injury_notes,
            )
        else:
            profile = self.profiles.update(
                profile,
                sport_id=sport.id,
                height_cm=height_cm,
                weight_kg=weight_kg,
                skill_level=payload.skill_level,
                injury_notes=payload.injury_notes,
            )

        self.db.commit()
        self.db.refresh(profile)
        return self._to_profile_response(profile)

    def list_sports(self) -> list[SportOptionResponse]:
        return [
            SportOptionResponse(
                id=sport.id,
                sport_name=sport.sport_name,
            )
            for sport in self.sports.list_all()
        ]

    @staticmethod
    def _to_decimal(value: float | None) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))

    def _to_profile_response(self, profile: UserProfile) -> ProfileResponse:
        sport = self.sports.get_by_id(profile.sport_id)
        return ProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            sport_id=profile.sport_id,
            sport_name=sport.sport_name,
            height_cm=float(profile.height_cm) if profile.height_cm is not None else None,
            weight_kg=float(profile.weight_kg) if profile.weight_kg is not None else None,
            skill_level=profile.skill_level,
            injury_notes=profile.injury_notes,
            created_at=profile.created_at,
        )
