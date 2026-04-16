from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, get_profile_service
from app.models.user import User
from app.schemas.profile import ProfileEnvelopeResponse, ProfileResponse, ProfileUpsertRequest
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileEnvelopeResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ProfileEnvelopeResponse:
    return profile_service.get_profile(current_user)


@router.put("", response_model=ProfileResponse)
def upsert_profile(
    payload: ProfileUpsertRequest,
    current_user: User = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    return profile_service.upsert_profile(current_user, payload)
