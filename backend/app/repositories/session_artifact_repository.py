from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.session_artifact import SessionArtifact


class SessionArtifactRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_session_and_type(
        self,
        *,
        session_id: UUID,
        artifact_type: str,
    ) -> SessionArtifact | None:
        statement = select(SessionArtifact).where(
            SessionArtifact.session_id == session_id,
            SessionArtifact.artifact_type == artifact_type,
        )
        return self.db.scalar(statement)

    def list_by_session_id(self, *, session_id: UUID) -> list[SessionArtifact]:
        statement = (
            select(SessionArtifact)
            .where(SessionArtifact.session_id == session_id)
            .order_by(SessionArtifact.created_at.asc(), SessionArtifact.artifact_type.asc())
        )
        return list(self.db.scalars(statement))

    def upsert(
        self,
        *,
        session_id: UUID,
        artifact_type: str,
        payload_json: dict[str, object],
    ) -> SessionArtifact:
        artifact = self.get_by_session_and_type(
            session_id=session_id,
            artifact_type=artifact_type,
        )

        if artifact is None:
            artifact = SessionArtifact(
                session_id=session_id,
                artifact_type=artifact_type,
                payload_json=payload_json,
            )
            self.db.add(artifact)
        else:
            artifact.payload_json = payload_json

        self.db.flush()
        self.db.refresh(artifact)
        return artifact
