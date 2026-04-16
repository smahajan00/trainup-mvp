from __future__ import annotations

from sqlalchemy import select

from app.models.sport import Sport


def _register_and_get_token(client) -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Jordan Carter",
            "email": "jordan@example.com",
            "password": "strongpass123",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_profile_create_and_update_success(client, db_session) -> None:
    token = _register_and_get_token(client)
    basketball = db_session.scalar(
        select(Sport).where(Sport.sport_name == "Basketball")
    )
    football = db_session.scalar(select(Sport).where(Sport.sport_name == "Football"))
    assert basketball is not None
    assert football is not None

    create_response = client.put(
        "/api/profile",
        json={
            "sport_id": str(basketball.id),
            "height_cm": 188.5,
            "weight_kg": 84.2,
            "skill_level": "INTERMEDIATE",
            "injury_notes": "  Mild ankle soreness after long sessions.  ",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert create_response.status_code == 200
    created_payload = create_response.json()
    assert created_payload["sport_name"] == "Basketball"
    assert created_payload["skill_level"] == "INTERMEDIATE"
    assert created_payload["injury_notes"] == "Mild ankle soreness after long sessions."

    get_response = client.get(
        "/api/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.status_code == 200
    assert get_response.json()["profile"]["sport_name"] == "Basketball"

    update_response = client.put(
        "/api/profile",
        json={
            "sport_id": str(football.id),
            "height_cm": 189.0,
            "weight_kg": 82.4,
            "skill_level": "ADVANCED",
            "injury_notes": "",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert update_response.status_code == 200
    updated_payload = update_response.json()
    assert updated_payload["sport_name"] == "Football"
    assert updated_payload["skill_level"] == "ADVANCED"
    assert updated_payload["injury_notes"] is None


def test_get_profile_returns_null_when_missing(client) -> None:
    token = _register_and_get_token(client)

    response = client.get(
        "/api/profile",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"profile": None}


def test_unauthorized_profile_access_rejected(client) -> None:
    response = client.get("/api/profile")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication credentials were not provided."
