from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.drill import Drill
from app.models.enums import InputType, SessionStatus
from app.models.training_session import TrainingSession


class SessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: UUID,
        drill_id: UUID,
        input_type: InputType,
        status: SessionStatus,
        start_time: datetime,
    ) -> TrainingSession:
        session = TrainingSession(
            user_id=user_id,
            drill_id=drill_id,
            input_type=input_type,
            status=status,
            start_time=start_time,
            end_time=None,
        )
        self.db.add(session)
        self.db.flush()
        self.db.refresh(session)
        return self.get_by_id_for_user(user_id=user_id, session_id=session.id) or session

    def get_by_id_for_user(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
    ) -> TrainingSession | None:
        statement = (
            select(TrainingSession)
            .options(
                selectinload(TrainingSession.drill).selectinload(Drill.sport),
            )
            .where(
                TrainingSession.id == session_id,
                TrainingSession.user_id == user_id,
            )
        )
        return self.db.scalar(statement)

    def list_recent_for_user(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> list[TrainingSession]:
        statement = (
            select(TrainingSession)
            .options(
                selectinload(TrainingSession.drill).selectinload(Drill.sport),
            )
            .where(TrainingSession.user_id == user_id)
            .order_by(TrainingSession.start_time.desc(), TrainingSession.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(statement))

    def save(self, session: TrainingSession) -> TrainingSession:
        self.db.add(session)
        self.db.flush()
        self.db.refresh(session)
        return (
            self.get_by_id_for_user(user_id=session.user_id, session_id=session.id)
            or session
        )
