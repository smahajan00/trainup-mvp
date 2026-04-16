from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, get_drill_service
from app.models.user import User
from app.schemas.drill import DrillDetailResponse
from app.services.drill_service import DrillService

router = APIRouter(prefix="/drills", tags=["drills"])


@router.get("/{drill_id}", response_model=DrillDetailResponse)
def get_drill_detail(
    drill_id: UUID,
    _: User = Depends(get_current_user),
    drill_service: DrillService = Depends(get_drill_service),
) -> DrillDetailResponse:
    return drill_service.get_drill_detail(drill_id)
