from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status

from app.repositories.drill_repository import DrillRepository
from app.repositories.sport_repository import SportRepository
from app.schemas.drill import DrillDetailResponse, DrillListItemResponse
from app.seed.drills import DRILL_DEMO_VIDEO_URLS_BY_NAME


@dataclass
class DrillService:
    drills: DrillRepository
    sports: SportRepository

    def list_drills_for_sport(self, sport_id: UUID) -> list[DrillListItemResponse]:
        sport = self.sports.get_by_id(sport_id)
        if sport is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requested sport was not found.",
            )

        return [
            DrillListItemResponse(
                id=drill.id,
                sport_id=drill.sport_id,
                drill_name=drill.drill_name,
                description=drill.description,
                target_metrics=drill.target_metrics,
            )
            for drill in self.drills.list_by_sport_id(sport_id)
        ]

    def get_drill_detail(self, drill_id: UUID) -> DrillDetailResponse:
        drill = self.drills.get_by_id(drill_id)
        if drill is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requested drill was not found.",
            )

        sport_name = drill.sport.sport_name if drill.sport is not None else ""
        return DrillDetailResponse(
            id=drill.id,
            sport_id=drill.sport_id,
            sport_name=sport_name,
            drill_name=drill.drill_name,
            description=drill.description,
            demo_video_url=DRILL_DEMO_VIDEO_URLS_BY_NAME.get(drill.drill_name),
            target_metrics=drill.target_metrics,
            reference_payload=drill.reference_payload,
            coaching_rules=drill.coaching_rules,
        )
