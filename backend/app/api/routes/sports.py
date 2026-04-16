from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, get_drill_service, get_profile_service
from app.models.user import User
from app.schemas.drill import DrillListItemResponse
from app.schemas.profile import SportOptionResponse
from app.services.drill_service import DrillService
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/sports", tags=["sports"])


@router.get("", response_model=list[SportOptionResponse])
def list_sports(
    _: User = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> list[SportOptionResponse]:
    return profile_service.list_sports()


@router.get("/{sport_id}/drills", response_model=list[DrillListItemResponse])
def list_drills_for_sport(
    sport_id: UUID,
    _: User = Depends(get_current_user),
    drill_service: DrillService = Depends(get_drill_service),
) -> list[DrillListItemResponse]:
    return drill_service.list_drills_for_sport(sport_id)
