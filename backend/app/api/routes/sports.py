from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, get_profile_service
from app.models.user import User
from app.schemas.profile import SportOptionResponse
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/sports", tags=["sports"])


@router.get("", response_model=list[SportOptionResponse])
def list_sports(
    _: User = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> list[SportOptionResponse]:
    return profile_service.list_sports()
