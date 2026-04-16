from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sport import Sport


class SportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, sport_id: UUID) -> Sport | None:
        statement = select(Sport).where(Sport.id == sport_id)
        return self.db.scalar(statement)

    def list_all(self) -> list[Sport]:
        statement = select(Sport).order_by(Sport.sport_name.asc())
        return list(self.db.scalars(statement))
