from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import TokenDecodeError, decode_access_token
from app.engines.cognition_engine.cognition_service import CognitionService
from app.engines.perception_interface.perception_service import PerceptionService
from app.models.user import User
from app.repositories.drill_repository import DrillRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.session_artifact_repository import SessionArtifactRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.sport_repository import SportRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.drill_service import DrillService
from app.services.profile_service import ProfileService
from app.services.session_service import SessionService

bearer_scheme = HTTPBearer(auto_error=False)


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_profile_repository(db: Session = Depends(get_db)) -> ProfileRepository:
    return ProfileRepository(db)


def get_drill_repository(db: Session = Depends(get_db)) -> DrillRepository:
    return DrillRepository(db)


def get_sport_repository(db: Session = Depends(get_db)) -> SportRepository:
    return SportRepository(db)


def get_session_repository(db: Session = Depends(get_db)) -> SessionRepository:
    return SessionRepository(db)


def get_session_artifact_repository(
    db: Session = Depends(get_db),
) -> SessionArtifactRepository:
    return SessionArtifactRepository(db)


def get_feedback_repository(db: Session = Depends(get_db)) -> FeedbackRepository:
    return FeedbackRepository(db)


def get_perception_service() -> PerceptionService:
    return PerceptionService()


def get_cognition_service() -> CognitionService:
    return CognitionService()


def get_auth_service(
    db: Session = Depends(get_db),
    users: UserRepository = Depends(get_user_repository),
) -> AuthService:
    return AuthService(db=db, users=users)


def get_profile_service(
    db: Session = Depends(get_db),
    profiles: ProfileRepository = Depends(get_profile_repository),
    sports: SportRepository = Depends(get_sport_repository),
) -> ProfileService:
    return ProfileService(db=db, profiles=profiles, sports=sports)


def get_drill_service(
    drills: DrillRepository = Depends(get_drill_repository),
    sports: SportRepository = Depends(get_sport_repository),
) -> DrillService:
    return DrillService(drills=drills, sports=sports)


def get_session_service(
    db: Session = Depends(get_db),
    sessions: SessionRepository = Depends(get_session_repository),
    artifacts: SessionArtifactRepository = Depends(get_session_artifact_repository),
    feedback: FeedbackRepository = Depends(get_feedback_repository),
    drills: DrillRepository = Depends(get_drill_repository),
    perception: PerceptionService = Depends(get_perception_service),
    cognition: CognitionService = Depends(get_cognition_service),
) -> SessionService:
    return SessionService(
        db=db,
        sessions=sessions,
        artifacts=artifacts,
        feedback=feedback,
        drills=drills,
        perception=perception,
        cognition=cognition,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    users: UserRepository = Depends(get_user_repository),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(str(payload["sub"]))
    except (TokenDecodeError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = users.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user was not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
