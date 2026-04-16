from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.enums import SeverityLevel
from app.models.feedback import Feedback


class FeedbackRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_session_id(self, *, session_id: UUID) -> list[Feedback]:
        statement = (
            select(Feedback)
            .where(Feedback.session_id == session_id)
            .order_by(Feedback.created_at.asc(), Feedback.id.asc())
        )
        return list(self.db.scalars(statement))

    def delete_by_session_id(self, *, session_id: UUID) -> None:
        self.db.execute(delete(Feedback).where(Feedback.session_id == session_id))
        self.db.flush()

    def create(
        self,
        *,
        session_id: UUID,
        severity_level: SeverityLevel,
        technique_issue: str,
        coaching_cue: str,
        metric_snapshot: dict[str, object],
    ) -> Feedback:
        feedback = Feedback(
            session_id=session_id,
            severity_level=severity_level,
            technique_issue=technique_issue,
            coaching_cue=coaching_cue,
            metric_snapshot=metric_snapshot,
        )
        self.db.add(feedback)
        self.db.flush()
        self.db.refresh(feedback)
        return feedback
