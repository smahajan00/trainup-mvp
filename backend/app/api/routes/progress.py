from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user, get_progress_service
from app.models.user import User
from app.schemas.progress import RecentProgressResponse
from app.services.progress_service import ProgressService

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/recent", response_model=RecentProgressResponse)
def get_recent_progress(
    session_limit: int = Query(default=5, ge=1, le=10),
    metric_limit: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    progress_service: ProgressService = Depends(get_progress_service),
) -> RecentProgressResponse:
    return progress_service.get_recent_progress(
        user_id=current_user.id,
        session_limit=session_limit,
        metric_limit=metric_limit,
    )
