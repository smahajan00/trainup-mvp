from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.drill import Drill
from app.models.metric_type import MetricType
from app.models.sport import Sport
from app.seed.drills import DRILL_SEEDS_BY_SPORT
from app.seed.metrics import METRIC_TYPE_SEEDS
from app.seed.sports import SPORT_SEEDS
from app.seed.validators import SeedValidationError, validate_drill_seed


@dataclass
class SeedStats:
    inserted: int = 0
    updated: int = 0


def _get_single_sport(session: Session, sport_name: str) -> Sport | None:
    results = list(session.scalars(select(Sport).where(Sport.sport_name == sport_name)))
    if len(results) > 1:
        raise SeedValidationError(f"Duplicate sports found for lookup key '{sport_name}'.")
    return results[0] if results else None


def _get_single_metric(session: Session, metric_name: str) -> MetricType | None:
    results = list(session.scalars(select(MetricType).where(MetricType.metric_name == metric_name)))
    if len(results) > 1:
        raise SeedValidationError(f"Duplicate metric types found for lookup key '{metric_name}'.")
    return results[0] if results else None


def _get_single_drill(session: Session, sport_id, drill_name: str) -> Drill | None:
    results = list(
        session.scalars(
            select(Drill).where(
                Drill.sport_id == sport_id,
                Drill.drill_name == drill_name,
            )
        )
    )
    if len(results) > 1:
        raise SeedValidationError(
            f"Duplicate drills found for lookup key sport_id={sport_id} drill_name='{drill_name}'."
        )
    return results[0] if results else None


def seed_sports(session: Session) -> tuple[dict[str, Sport], SeedStats]:
    stats = SeedStats()
    sports_by_name: dict[str, Sport] = {}

    print("Seeding sports...")
    for definition in SPORT_SEEDS:
        sport_name = definition["sport_name"]
        sport = _get_single_sport(session, sport_name)

        if sport is None:
            sport = Sport(sport_name=sport_name)
            session.add(sport)
            session.flush()
            stats.inserted += 1
            print(f"Inserted new sport: {sport_name}")

        sports_by_name[sport_name] = sport

    return sports_by_name, stats


def seed_metric_types(session: Session) -> tuple[dict[str, MetricType], SeedStats]:
    stats = SeedStats()
    metrics_by_name: dict[str, MetricType] = {}

    print("Seeding metric types...")
    for definition in METRIC_TYPE_SEEDS:
        metric_name = definition["metric_name"]
        metric = _get_single_metric(session, metric_name)

        if metric is None:
            metric = MetricType(
                metric_name=metric_name,
                metric_unit=definition["metric_unit"],
            )
            session.add(metric)
            session.flush()
            stats.inserted += 1
            print(f"Inserted new metric type: {metric_name}")
        else:
            changed = False
            if metric.metric_unit != definition["metric_unit"]:
                metric.metric_unit = definition["metric_unit"]
                changed = True

            if changed:
                stats.updated += 1
                print(f"Updated existing metric type: {metric_name}")

        metrics_by_name[metric_name] = metric

    return metrics_by_name, stats


def seed_drills(
    session: Session,
    sports_by_name: dict[str, Sport],
    valid_metric_names: set[str],
) -> SeedStats:
    stats = SeedStats()

    print("Seeding drills...")
    for sport_name, drill_definitions in DRILL_SEEDS_BY_SPORT.items():
        sport = sports_by_name.get(sport_name)
        if sport is None:
            raise SeedValidationError(f"Sport '{sport_name}' must exist before drill seeding.")

        for definition in drill_definitions:
            validate_drill_seed(definition, valid_metric_names)

            drill = _get_single_drill(session, sport.id, definition["drill_name"])
            payload = {
                "sport_id": sport.id,
                "drill_name": definition["drill_name"],
                "description": definition["description"],
                "reference_payload": definition["reference_payload"],
                "coaching_rules": definition["coaching_rules"],
                "target_metrics": definition["target_metrics"],
            }

            if drill is None:
                session.add(Drill(**payload))
                session.flush()
                stats.inserted += 1
                print(f"Inserted new drill: {definition['drill_name']}")
                continue

            changed = False
            for field_name, value in payload.items():
                if field_name == "sport_id":
                    continue
                if getattr(drill, field_name) != value:
                    setattr(drill, field_name, value)
                    changed = True

            if changed:
                stats.updated += 1
                print(f"Updated existing drill: {definition['drill_name']}")
            else:
                print(f"No changes for drill: {definition['drill_name']}")

    return stats


def main() -> None:
    print("Starting TrainUp seed process...")

    with SessionLocal() as session:
        try:
            with session.begin():
                sports_by_name, sport_stats = seed_sports(session)
                metrics_by_name, metric_stats = seed_metric_types(session)
                drill_stats = seed_drills(session, sports_by_name, set(metrics_by_name.keys()))

            print("Seed completed successfully")
            print(f"sports inserted: {sport_stats.inserted}")
            print(f"sports updated: {sport_stats.updated}")
            print(f"metrics inserted: {metric_stats.inserted}")
            print(f"metrics updated: {metric_stats.updated}")
            print(f"drills inserted: {drill_stats.inserted}")
            print(f"drills updated: {drill_stats.updated}")
        except Exception:
            session.rollback()
            print("Seed failed; transaction rolled back")
            raise


if __name__ == "__main__":
    main()
