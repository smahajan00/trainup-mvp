from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.drill import Drill


class DrillRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_sport_id(self, sport_id: UUID) -> list[Drill]:
        statement = (
            select(Drill)
            .options(selectinload(Drill.sport))
            .where(Drill.sport_id == sport_id)
            .order_by(Drill.drill_name.asc())
        )
        return list(self.db.scalars(statement))

    def get_by_id(self, drill_id: UUID) -> Drill | None:
        statement = (
            select(Drill)
            .options(selectinload(Drill.sport))
            .where(Drill.id == drill_id)
        )
        return self.db.scalar(statement)
