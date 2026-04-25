from __future__ import annotations

from sqlalchemy import select

from app.models.drill import Drill
from app.models.sport import Sport
from app.seed.drills import DRILL_SEEDS_BY_SPORT


def _register_and_get_token(client) -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Drill Browser",
            "email": "drill-browser@example.com",
            "password": "strongpass123",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_get_drills_for_sport_success(client, db_session) -> None:
    token = _register_and_get_token(client)
    basketball = db_session.scalar(select(Sport).where(Sport.sport_name == "Basketball"))
    assert basketball is not None

    response = client.get(
        f"/api/sports/{basketball.id}/drills",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [drill["drill_name"] for drill in payload] == [
        "Defensive Stance",
        "Set Shot Form",
    ]
    assert all(
        set(drill.keys())
        == {"id", "sport_id", "drill_name", "description", "target_metrics"}
        for drill in payload
    )
    assert all("difficulty_level" not in drill for drill in payload)


def test_seeded_drills_do_not_define_fixed_skill_levels() -> None:
    for drill_definitions in DRILL_SEEDS_BY_SPORT.values():
        for drill_definition in drill_definitions:
            assert "difficulty_level" not in drill_definition


def test_get_drill_detail_success(client, db_session) -> None:
    token = _register_and_get_token(client)
    drill = db_session.scalar(select(Drill).where(Drill.drill_name == "Set Shot Form"))
    assert drill is not None

    response = client.get(
        f"/api/drills/{drill.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["drill_name"] == "Set Shot Form"
    assert payload["sport_name"] == "Basketball"
    assert "difficulty_level" not in payload
    assert payload["reference_payload"] == drill.reference_payload
    assert payload["coaching_rules"] == drill.coaching_rules
    assert payload["coaching_rules"]["thresholds"] == drill.coaching_rules["thresholds"]
    assert payload["coaching_rules"]["rule_checks"] == drill.coaching_rules["rule_checks"]
    assert set(payload["reference_payload"].keys()) == {
        "movement_type",
        "phases",
        "tracked_joints",
        "ideal_ranges",
        "stability_expectations",
        "notes",
    }
