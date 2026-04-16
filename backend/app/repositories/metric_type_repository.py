from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.metric_type import MetricType


class MetricTypeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_names(self, metric_names: set[str]) -> list[MetricType]:
        if not metric_names:
            return []

        statement = select(MetricType).where(MetricType.metric_name.in_(metric_names))
        return list(self.db.scalars(statement))
